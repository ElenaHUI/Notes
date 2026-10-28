## 1. 环境信息

- 硬件平台：平头哥 PPU ZW810E
- 模型框架：vLLM 0.26 + ModelExpress
- 模型：Qwen3-32B
- 并行策略：TP = 2
- 传输链路：NIXL（`nixl_cu13` wheel，内置 UCX 1.21）→ UCX → mlx5 RoCE 网卡

## 2. 传输架构

### 2.1 传输组件

|   |   |   |
|---|---|---|
|概念|定位|说明|
|RoCE|IB 的以太网变体|RDMA over Converged Ethernet，把 RDMA 跑在以太网上（RoCEv2 走 UDP/IP），本文的 mlx5 网卡即为 RoCE|
|verbs (libibverbs)|编程 API|RDMA 的标准用户态接口，核心对象有 QP（队列对）、CQ（完成队列）、MR（内存区域）、PD（保护域）|
|UCX|通信框架|Unified Communication X，在 verbs / TCP / 共享内存 / GPU 之上提供统一抽象，并负责协议选择|
|peermem|内核模块|把 GPU/PPU 显存页暴露给上层，使网卡能直接对显存做 DMA（GPUDirect RDMA 的前提）|

### 2.2 分层关系

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde5255b3a558f532291fd43069727cc8d0375b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d5c0f71fa7ff964aa201040f324320f6425112e51388b4111bf62d651624544ca028f2b47dcd68228e?tmpCode=d258b652-4ac3-4263-ac9f-04f49737220b)
### 2.3 peermem

RDMA 的前提是：网卡必须拿到一块内存的 DMA 映射，并把它注册成可供远端访问的 MR（Memory Region）。
- 对普通主机内存，verbs 层可以直接完成注册。
- 对 GPU/PPU 显存，网卡并不能天然理解设备显存地址，需要 peermem 内核模块把显存页暴露给 RDMA 子系统，网卡才能直接 DMA。

---
## 3. 问题现象
在 TP=2 场景下，P2P 权重传输可以正常完成，但带宽明显偏低，只有约 9 Gbps，远低于预期。
![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde560b5c6f246e3879d3faa6a9ab5e439e875b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d5c1acb84f481fa67145b4695c09471418a5240503a4cbcaa752b563e5d2f04f8e786e498c1b7c0347?tmpCode=d258b652-4ac3-4263-ac9f-04f49737220b)
对耗时进行拆解后发现，绝大部分时间都消耗在实际数据搬运阶段：

|                         |                   |
| ----------------------- | ----------------- |
| 阶段                      | 耗时                |
| 显存注册 `register_tensors` | 0.09 s            |
| 描述符准备 `prep_xfer_dlist` | ≈ 0 s             |
| RDMA 数据传输               | 38.7 s / 总 40.4 s |
可以看到：
- 显存注册阶段几乎不耗时
- 描述符准备几乎可以忽略
- 瓶颈几乎完全落在 RDMA 数据传输

这说明问题不在调度、建链或注册开销，而在传输路径本身效率很低。

---
## 4. 传输路径分析

打开 `UCX_PROTO_INFO=y` 后，协议表中与远程读显存相关的项显示为：
![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde5255b3a558f532291fd43069727cc8d0375b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d5c432a7dd286ff6bcab846c23457637e49a807004ca50b5fc47cf3e08fe3038533070fab90ba7ddd7?tmpCode=d258b652-4ac3-4263-ac9f-04f49737220b)
### 4.1 `rc_mlx5`

说明数据面已经走到了 mlx5 RDMA 网卡，因此问题不是退化到 TCP。
也就是说，链路是：
- 应用层：NIXL
- 通信层：UCX
- 网络层：RoCE / mlx5
网络设备本身是 RDMA 网卡，没有走 socket/TCP fallback。
### 4.2 `into cuda ... from cuda`

说明此次操作的源和目标都是显存（GPU/PPU device memory）。
也就是说，本次传输的语义确实是：
- 从一端设备显存读出
- 通过网络送到另一端设备显存

这与我们的业务场景一致：跨节点/跨卡的权重 P2P 传输。
### 4.3 `software emulation`

它表示 UCX 认为当前网卡无法直接对显存做 RDMA 访问，因此没有走 GPUDirect RDMA / PeerDirect 之类的“网卡直达设备显存”路径，而是退化成了软件模拟（参见 [2.3](#23-为什么显存传输需要-peermem) 的路径对比图）。

---

## 5. 原理说明：UCX 如何判断网卡是否支持注册显存

### 5.1 背景：为什么需要“显存注册”

RDMA 的前提是：网卡必须能拿到一块内存的 DMA 映射，并把它注册成可供远端访问的内存区域（MR，Memory Region）。
对于普通主机内存，这个过程通常由 verbs 层直接完成。
但对于设备显存（例如 CUDA/PPU 显存），情况不同：
- 网卡并不能天然理解设备显存地址
- 需要依赖设备驱动和 peermem 模块，把设备显存页暴露给 RDMA 子系统
- 这样 mlx5 才能对这块显存执行 DMA 读写
### 5.2 UCX 的判定逻辑

在 UCX 打开 IB memory domain 时，会调用：

```
uct_ib_check_gpudirect_driver()
```
该逻辑位于：
```
src/uct/ib/base/ib_md.c
```

它会通过 `access(path, F_OK)` 检查若干固定路径是否存在

```
/sys/kernel/mm/memory_peers/nv_mem/version
/sys/module/nvidia_peermem/version
/sys/module/nv_peer_mem/version
```

只要其中任意一个存在，UCX 就会把 `cuda` 加入该 IB 设备的 `reg_mem_types`，即认为：
这张 RDMA 网卡可以注册 CUDA 设备内存
随后协议选择阶段，UCX 才有机会选中真正的 GPUDirect RDMA 路径。

---

## 6. 原因定位

`nixl_cu13` wheel 内置的社区版 UCX 只探测 NVIDIA 系列的 peermem 路径，不识别 PPU 平台的 peermem 模块 `alixpu_peermem`，导致 UCX 无法把设备显存纳入可注册内存类型（`reg_mem_types`），最终退化为 software emulation。

---

## 7. 解决方案

### 7.1 方案 A：整体替换 UCX / NIXL 依赖

- 参考 HLLM 使用支持 `alixpu_peermem` 的 UCX 版本
    参考仓库地址：[https://code.alibaba-inc.com/PPU-InferenceEngine/ucx](https://code.alibaba-inc.com/PPU-InferenceEngine/ucx)
    打包镜像地址：art.eng.t-head.cn/ptgai-docker_ai-service/ai-tmp/mx-vllm:0.5.1-vllm0.26.0-ucxgdr-ppu
- 需要根据源码重新打包或替换 wheel / 动态库
- 依赖供应商版本支持

### 7.2 方案 B：修改 `libuct_ib` 中的 peermem 识别逻辑

打包镜像地址：art.eng.t-head.cn/ptgai-docker_ai-service/ai-tmp/mx-vllm:0.5.1-vllm0.26.0-peermem

- 直接修改 `nixl_cu13.libs/ucx/libuct_ib*.so*`
- 将 UCX 用来探测 peermem 的固定路径替换为 `alixpu_peermem` 对应路径

补丁脚本：`reports/patch-nixl-ucx-peermem.sh`
#### 修改思路

补丁 `0001` 中原本考虑使用更完整的文件路径，但由于二进制原地 patch 有长度限制：
- 新字符串长度不能超过原字符串预留空间
- `alixpu_peermem` 对应的完整目标路径长度达到 51 字节
- 无法安全地原地覆盖进现有 `.so` 中

所以最终采用：

```
/sys/module/alixpu_peermem
```

### 7.3 部署镜像与关键配置

修复以镜像形式交付，以下为本期部署必需项：

```yaml
image: art.eng.t-head.cn/ptgai-docker_ai-service/ai-tmp/mx-vllm:0.5.1-vllm0.26.0-peermem
securityContext.capabilities.add: [IPC_LOCK, SYSLOG]
resources:
  limits/requests:                # limits 与 requests 同值
    alibabacloud.com/ppu: 2
    rdma/hca: '4'
env:
  - MX_RDMA_NIC_PIN: "mlx5_bond_1:1,...,mlx5_bond_4:1"
  - UCX_RNDV_SCHEME: get_zcopy
  - UCX_RNDV_THRESH: 0
  - UCX_PROTO_INFO: y
  - UCX_TLS: "cuda_ipc,cuda_copy,shm,self,rc_mlx5,ud_mlx5,tcp"
  - UCX_NET_DEVICES: "mlx5_bond_1:1,...,mlx5_bond_4:1"
  - UCX_MEMTYPE_CACHE: n
  - UCX_RCACHE_MAX_UNRELEASED: 1024
  - UCX_IB_PREFER_NEAREST_DEVICE: n
```

---

## 8. 修复后的效果

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde5255b3a558f532291fd43069727cc8d0375b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d5ad18ad3465c5881a6e8c82e9699c2f93d3d9be64eef203386855af8ecfe3eee5ce98ecd6bb1c36c9?tmpCode=d258b652-4ac3-4263-ac9f-04f49737220b)

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde5255b3a558f532291fd43069727cc8d0375b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d59b56c2beb436f940408219a2f0e066e490eb95da2f68ac7513b90e174c30cec2fa156c90a5859770?tmpCode=d258b652-4ac3-4263-ac9f-04f49737220b)

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde5255b3a558f532291fd43069727cc8d0375b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d545c8876083d77884ed668a50f009a0770f79aa1c5b6bd9b21e0b887885ba062db3d2a89ef6da2911?tmpCode=d258b652-4ac3-4263-ac9f-04f49737220b)

修复后，UCX 能正确识别系统已加载 `alixpu_peermem`，从而把设备显存加入 `reg_mem_types`，协议选择回到 GPUDirect RDMA 路径。

|   |   |   |
|---|---|---|
|指标|修复前|修复后|
|传输协议|software emulation|GPUDirect RDMA / direct device memory|
|权重传输带宽|~9 Gbps|~137 Gbps（137.6 / 137.0）|
|RDMA 数据传输耗时|38.7 s|~1.9 s（1.905 / 1.913）|
|端到端接收耗时|~40.4 s|4.67 / 4.81 s|
|CPU 参与|明显|显著降低|

带宽提升约 15 倍，RDMA 传输耗时缩短约 20 倍，端到端接收耗时从 40.4 s 降至 5 s 以内，达到链路预期水平。