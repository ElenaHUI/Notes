 ![[______________________________________________________________________《基于PPU的红区大模型推理平台》介绍大纲.png]]


## 一、NIXL 是什么？相比 mooncake 有什么优势？

NIXL（NVIDIA Inference Transfer Library） 是 NVIDIA 开发的通用数据传输库，专门用于分布式推理引擎间高效移动 KV Cache 等数据。mooncake 是 Moonshot 团队开发的专用 KV Cache 传输引擎，而 NIXL 是插件化的上位替代方案。

核心优势对比：

|              |                                                                                                                                                              |                                             |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------- |
| 维度           | Mooncake（当前）                                                                                                                                                 | NIXL（Dynamo）                                |
| 传输后端         | 单一引擎，主要面向 [RDMA](https://developer.nvidia.com/blog/introducing-nvidia-dynamo-a-low-latency-distributed-inference-framework-for-scaling-reasoning-ai-models/) | 插件化框架：UCX（默认）、LIBFABRIC、POSIX、GDS、3FS、对象存储等 |
| 硬件要求         | 强依赖 RDMA（InfiniBand/RoCE）                                                                                                                                    | 不强制，自动降级到可用最优路径                             |
| 同机传输         | 走回环网络或需手动配置                                                                                                                                                  | UCX 自动检测 NVLink/PCIe/共享内存                   |
| 跨 TP 兼容      | 需要相同 TP 配置                                                                                                                                                   | 支持不同 TP 间的元数据交换和 gather-scatter             |
| 多内存层级        | 不支持                                                                                                                                                          | KVBM 支持 G1-G4 四层（GPU显存→CPU内存→SSD→远程存储）      |
| bootstrap 发现 | 手动配置 K8s 注解（`sglang.ai/bootstrap-port`）                                                                                                                      | Dynamo Discovery Service 自动发现               |
| 运行时弹性        | 固定副本，需整机调度                                                                                                                                                   | 运行时可重配置 xPyD，动态增删 worker                    |

Dynamo 设计文档明确指出 NIXL 的 KV 传输是非阻塞的，GPU 前向传播可以在传输期间继续服务其他请求。

---

## 二、NIXL 是否仍然依赖 RDMA？

不强制依赖。 NIXL 是插件化传输框架，RDMA 只是其最优传输路径之一。

具体机制：

- NIXL 默认使用 UCX（Unified Communication X）后端，UCX 本身是一个抽象层，会自动选择当前硬件环境下的最优传输：NVLink > InfiniBand RDMA > RoCE > PCIe > 共享内存 > TCP
    
- Dynamo 文档原文（[nixl-connect/README.md](file:///Users/yuansheng.wzw/Documents/code/dynamo/docs/api/nixl-connect/README.md)）：
    
    "When RDMA isn't available, the NIXL data transfer will still complete using non-accelerated methods."
    
- NIXL 默认配置同时启用 UCX 和 POSIX 后端（见 [lib/kvbm-config/src/nixl.rs](file:///Users/yuansheng.wzw/Documents/code/dynamo/lib/kvbm-config/src/nixl.rs)），POSIX 后端不需要任何 RDMA 硬件
    
- 可通过环境变量 `SGLANG_DISAGGREGATION_NIXL_BACKEND` 切换后端（UCX / LIBFABRIC 等）
    

对您当前环境的影响：您目前配置了 5 个 RDMA IB 设备（mlx5_bond_0~4），迁移到 NIXL 后如果 RDMA 硬件仍在，UCX 会优先使用 RDMA 获得最高带宽；如果部分节点没有 RDMA，NIXL 会自动降级，不会像 mooncake 那样直接不可用。

---

## 三、能否支持非独占整机（4卡P Pod + 4卡D Pod）的 PD 分离？

完全可以。 这是 Dynamo 架构的核心设计目标之一。

### 3.1 直接证据

Dynamo 提供了多种 Pod 级别部署示例：

- 同一块 GPU 上跑 P+D（最极端场景）：[examples/backends/sglang/launch/disagg_same_gpu.sh](file:///Users/yuansheng.wzw/Documents/code/dynamo/examples/backends/sglang/launch/disagg_same_gpu.sh) — 两个 worker 共享 `CUDA_VISIBLE_DEVICES=0`，通过 `--mem-fraction-static` 控制显存分配
    
- 同机不同 GPU 上跑 P+D：[examples/backends/sglang/launch/disagg.sh](file:///Users/yuansheng.wzw/Documents/code/dynamo/examples/backends/sglang/launch/disagg.sh) — Prefill 在 GPU 0，Decode 在 GPU 1
    
- 4卡机器跑 2P+2D：[examples/backends/sglang/launch/disagg_router.sh](file:///Users/yuansheng.wzw/Documents/code/dynamo/examples/backends/sglang/launch/disagg_router.sh) — 4 GPU 上启动 2 Prefill + 2 Decode worker，使用 KV 感知路由
    
- K8s 部署模板：[examples/backends/sglang/deploy/disagg.yaml](file:///Users/yuansheng.wzw/Documents/code/dynamo/examples/backends/sglang/deploy/disagg.yaml) — Prefill Pod 请求 1 GPU，Decode Pod 请求 1 GPU，可调度到同一物理机或不同物理机
    

### 3.2 您的具体场景分析

您的场景：16卡物理机，P Pod 用4卡（TP=4），D Pod 用4卡（TP=4），P和D可能在同一台机器也可能不在。

当 P 和 D 在同一台物理机上时：

- NIXL/UCX 会自动检测并使用 NVLink（如果有）或 PCIe 进行 GPU-to-GPU KV Cache 传输
    
- 这比跨节点 RDMA 延迟更低（NVLink 带宽通常高于网络 RDMA）
    
- 无需配置 RDMA IB 设备，传输完全在节点内部完成
    

当 P 和 D 在不同物理机上时：

- NIXL/UCX 使用 RDMA（InfiniBand/RoCE）或 TCP 进行跨节点传输
    
- 如果有 RDMA 硬件，自动获得最高带宽；如果没有，降级到 TCP
    

### 3.3 对比当前整机独占架构

|   |   |   |
|---|---|---|
|维度|当前架构（整机独占 7P+5D）|Dynamo Pod 级别部署|
|GPU 利用率|低 — 整机16卡独占给1个P或D|高 — 16卡可分4P+4D+8卡留给其他模型|
|弹性扩缩容|需整机调度，粒度粗|Pod 级别弹性，K8s 自动调度|
|同机 KV 传输|不存在（整机独占）|NVLink/PCIe，延迟低于跨节点 RDMA|
|跨机 KV 传输|RDMA（mooncake）|RDMA 或 TCP（NIXL/UCX 自动选择）|
|bootstrap 发现|手动 K8s 注解|Dynamo Discovery Service 自动发现|
|TP 配置|固定 TP=16|灵活，支持不同 TP 配置间的传输|
|hostNetwork/特权|需要（hostNetwork + privileged）|不需要，标准 K8s Pod 网络|
|调度复杂度|需要整机反亲和 + 污点容忍|标准 Pod 调度|

---

## 四、迁移建议

如果要从当前 SGLang 原生 PD + mooncake 迁移到 Dynamo + NIXL，关键变更点：

1. 传输后端：`--disaggregation-transfer-backend mooncake` → `--disaggregation-transfer-backend nixl`
    
2. TP 配置：`--tp-size 16` → `--tp-size 4`（适配4卡 Pod）
    
3. 启动方式：直接 `sglang.launch_server` → 通过 `dynamo.sglang` 模块启动，由 Dynamo 管理生命周期
    
4. 服务发现：`sglang.ai/bootstrap-port` K8s 注解 + SGLang Router service-discovery → Dynamo Discovery Service 自动处理
    
5. bootstrap 端口：手动配置 `--disaggregation-bootstrap-port 8998` → Dynamo 自动计算和分发 bootstrap 地址（见 [components/src/dynamo/sglang/_disagg.py](file:///Users/yuansheng.wzw/Documents/code/dynamo/components/src/dynamo/sglang/_disagg.py)）
    
6. hostNetwork/privileged：可以去掉，改为标准 K8s Pod 网络模式
    
7. RDMA 设备：可以保留用于跨节点传输，但不再是硬依赖
    

注意事项：Prefill 和 Decode worker 的 `--page-size` 必须保持一致。Dynamo 所有示例中使用 `--page-size 16` 或 `64`。

---

总结：Dynamo + NIXL 架构完全支持您描述的非独占整机 Pod 级别 PD 分离场景。NIXL 不强制依赖 RDMA，会根据硬件环境自动选择最优传输路径。同机时走 NVLink/PCIe（延迟更低），跨机时走 RDMA/TCP。相比当前的 mooncake + 整机独占方案，Dynamo 还带来了自动服务发现、运行时弹性扩缩容和更高的 GPU 资源利用率。