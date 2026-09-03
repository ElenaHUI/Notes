# 文档

## 官网

- [SGLang PD Disaggregation 文档](https://docs.sglang.io/docs/advanced_features/server_arguments#pd-disaggregation)

## 参考资料

- [vLLM PD 分离](https://alidocs.dingtalk.com/i/nodes/Amq4vjg890G07Kpwu2Xzql47J3kdP0wQ?cid=3939817874%3A5685869479&utm_source=im&utm_scene=team_space&iframeQuery=utm_medium%3Dim_card%26utm_source%3Dim&utm_medium=im_card&corpId=ding5f9a690be26948824ac5d6980864d335)
- [alinpu_engineering 文档](https://aliyuque.antfin.com/alinpu_engineering/snxi21/cngf3gf1bscfu2x9)
- [ACK 灵骏 Pod 使用 RDMA](https://help.aliyun.com/zh/ack/ack-lingjun-managed-clusters/user-guide/ack-lingjun-pod-using-rdma?scm=20140722.S_help%40%40%E6%96%87%E6%A1%A3%40%402869336._.ID_help%40%40%E6%96%87%E6%A1%A3%40%402869336-RL_%E7%81%B5%E9%AA%8F-LOC_doc%7EUND%7Eab-OR_ser-PAR1_6a0b3eeb17775182852761122d0099-V_4-PAR3_o-RE_new11-P0_10-P1_0&spm=a2c4g.11174283.help-search.i20)

## Docker 部署

- [kimi-Docker部署](https://alidocs.dingtalk.com/i/nodes/y20BglGWO2d2oKE5s0nBwk6j8A7depqY)

# 配置输入

## 机内 ICN 配置

尝试走机内 ICN，设置这两个环境变量即可：

```bash
MC_FORCE_MNNVL=1
MC_USE_NVLINK_IPC=1
```

验证是否真正走了 ICN link：

```bash
MC_LOG_LEVEL=TRACE
```

这个可以看 mooncake 的详细 log，应该会有对应的 `register memory: addr` 之类的 log。

## Qwen3.5-397B（8 卡，机内 ICN）

**P 端**

```bash
CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 \
SGLANG_MOONCAKE_CUSTOM_MEM_POOL=True MC_NUM_QP_PER_EP=4 MC_FORCE_MNNVL=1 \
SAIL_SGL_DEEPEP_RECV_HOOK=0 SAIL_SGL_DEEPEP_ICN=1 \
SGLANG_DEEPEP_NUM_MAX_DISPATCH_TOKENS_PER_RANK=512 \
MC_TE_METRIC=1 MC_LOG_LEVEL=TRACE \
python3 -m sglang.launch_server --trust-remote-code --host 0.0.0.0 --port 8100 \
  --model-path /ppusw/datasets/checkpoints/LLM/qwen/v3.5/Qwen3.5-397B-A17B-INT8 \
  --tp-size 8 --attention-backend fa3 --page-size 64 --disable-radix-cache \
  --trust-remote-code --watchdog-timeout 3600 --dist-timeout 3600 --log-level info \
  --enable-metrics --enable-cache-report --disable-custom-all-reduce \
  --disable-shared-experts-fusion \
  --disaggregation-ib-device mlx5_bond_0,mlx5_bond_1,mlx5_bond_2,mlx5_bond_3,mlx5_bond_4,mlx5_bond_5,mlx5_bond_6,mlx5_bond_7 \
  --disaggregation-mode prefill --mem-fraction-static 0.9 --quantization w8a8_int8
```

**D 端**

```bash
CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 \
SGLANG_MOONCAKE_CUSTOM_MEM_POOL=True MC_NUM_QP_PER_EP=4 MC_FORCE_MNNVL=1 \
SAIL_SGL_DEEPEP_RECV_HOOK=0 SAIL_SGL_DEEPEP_ICN=1 \
SGLANG_DEEPEP_NUM_MAX_DISPATCH_TOKENS_PER_RANK=512 \
MC_TE_METRIC=1 MC_LOG_LEVEL=TRACE \
python3 -m sglang.launch_server --trust-remote-code --host 0.0.0.0 --port 12100 \
  --model-path /ppusw/datasets/checkpoints/LLM/qwen/v3.5/Qwen3.5-397B-A17B-INT8 \
  --tp-size 8 --attention-backend fa3 --page-size 64 --disable-radix-cache \
  --trust-remote-code --watchdog-timeout 3600 --dist-timeout 3600 --log-level info \
  --enable-metrics --enable-cache-report --disable-custom-all-reduce \
  --disable-shared-experts-fusion \
  --disaggregation-ib-device mlx5_bond_0,mlx5_bond_1,mlx5_bond_2,mlx5_bond_3,mlx5_bond_4,mlx5_bond_5,mlx5_bond_6,mlx5_bond_7 \
  --disable-radix-cache --disaggregation-mode decode --cuda-graph-max-bs 128 \
  --enable-expert-distribution-metrics --mem-fraction-static 0.7 \
  --moe-a2a-backend deepep --dp-size 8 --enable-dp-lm-head --deepep-mode low_latency \
  --enable-dp-attention --prefill-round-robin-balance --moe-dense-tp-size 1 \
  --quantization w8a8_int8
```

**main server（router）**

```bash
python -m sglang_router.launch_router --pd-disaggregation --host 0.0.0.0 --mini-lb --port 8999 \
  --prefill http://sh01t-swu27.eng.t-head.cn:8100 \
  --decode http://sh01t-swu28.eng.t-head.cn:12100
```

## Qwen3-235B（16 卡，李祎凡）

**P 端**

```bash
CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15 \
PYTHONUNBUFFERED=1 SGL_ENABLE_JIT_DEEPGEMM=1 \
python3 -m sglang.launch_server --trust-remote-code --host 0.0.0.0 --port 8100 \
  --model-path /ppusw/datasets/checkpoints/LLM/qwen/v3.0/Qwen3-235B-A22B-Instruct-2507-W8A8-INT8 \
  --tp-size 16 --attention-backend fa3 --disable-radix-cache --context-length 16384 \
  --enable-dp-attention --dp-size 16 --quantization w8a8_int8 --trust-remote-code \
  --max-running-requests 1024 --watchdog-timeout 3600 --dist-timeout 3600 \
  --log-level info --enable-cache-report --disaggregation-transfer-backend mooncake \
  --disaggregation-mode prefill --mem-fraction-static 0.92 --disable-shared-experts-fusion
```

**D 端**

```bash
CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15 \
PYTHONUNBUFFERED=1 SGL_ENABLE_JIT_DEEPGEMM=1 \
SAIL_SGL_DEEPEP_ICN=1 SGLANG_DEEPEP_NUM_MAX_DISPATCH_TOKENS_PER_RANK=512 \
SGL_DEEP_EP_RECV_HOOK=False \
python3 -m sglang.launch_server --trust-remote-code --host 0.0.0.0 --port 12100 \
  --model-path /ppusw/datasets/checkpoints/LLM/qwen/v3.0/Qwen3-235B-A22B-Instruct-2507-W8A8-INT8 \
  --tp-size 16 --attention-backend fa3 --disable-radix-cache --context-length 16384 \
  --enable-dp-attention --dp-size 16 --quantization w8a8_int8 --trust-remote-code \
  --max-running-requests 1024 --watchdog-timeout 3600 --dist-timeout 3600 \
  --log-level info --enable-cache-report --disaggregation-transfer-backend mooncake \
  --moe-dense-tp-size 1 --prefill-round-robin-balance --chunked-prefill-size 163840 \
  --enable-dp-lm-head --decode-log-interval 50 --mem-fraction-static 0.8 \
  --schedule-conservativeness 0.3 --load-balance-method auto \
  --cuda-graph-bs 1 2 3 4 5 6 7 8 10 12 14 16 18 20 22 24 26 28 30 32 40 48 56 64 \
  --moe-a2a-backend deepep --deepep-mode low_latency --disable-radix-cache \
  --disaggregation-mode decode
```

**main server（router）**

```bash
PREFILL_DP_SIZE=1 DECODE_DP_SIZE=16 python -m sglang_router.launch_router \
  --pd-disaggregation --host 0.0.0.0 --mini-lb --port 8999 \
  --prefill http://na131t-swu139.eng.t-head.cn:8100 \
  --decode http://na131t-swu199.eng.t-head.cn:12100
```

# 问题

## 问题1: RuntimeError: q_v is only supported for Hopper GPUs

这个是 fa3 内部不支持的问题，现在 kimi / glm5 / dpsk v32 设置 `--attention-backend fa3` 都会有这个错误。

**解决方法**：把 `--attention-backend fa3` 换成 `--decode-attention-backend flashmla --prefill-attention-backend fa3`。

## 问题2: assert m == m_ and n == n_ and k == k AssertError

**解决方法**：w4a8 不支持开 ep。

## 问题3: RDMA通信异常

定位报告：[Kimi-K2.6 PD分离部署通信异常问题定位报告](https://alidocs.dingtalk.com/i/nodes/ndMj49yWjXnXREO6TwRw90bZJ3pmz5aA)

**现象与结论**：Decode 机器上缺少 `alixpu-peermem`，导致 Decode 出现 bad address 错误。需要在 Decode 机器上安装 `alixpu-peermem`。

### alixpu-peermem 原理说明

`alixpu-peermem` 是阿里自研加速卡（Ali XPU / 平头哥 PPU）的 peer memory 内核驱动模块，作用等同于 NVIDIA 生态里的 `nvidia-peermem`（早期的 `nv_peer_mem`）。

它向内核的 RDMA 子系统（`ib_core`）注册一个 peer memory client，使得 RDMA verbs（如 `ibv_reg_mr`）能够直接注册和访问加速卡的设备显存，实现类似 GPUDirect RDMA 的能力：

```
正常路径（无 peermem）:  网卡 → 主机内存 → 拷贝 → 卡显存   （慢，且注册设备内存会失败）
peermem 路径:            网卡 ⇄ 卡显存  直接 DMA          （零拷贝）
```

**为什么缺失会报 bad address**：PD 分离场景下，KV cache 通过 Mooncake transfer engine 走 RDMA（`mlx5_bond_*` 网卡）从 P 传到 D。D 端需要把接收缓冲区直接注册到自己加速卡的显存里，这一步依赖 `alixpu-peermem`。模块缺失 → RDMA 层无法映射卡显存地址 → 注册内存时返回无效地址 → "bad address"。

**为什么只有 Decode 端报错**：KV cache 的接收目标是 D 端卡显存，接收侧注册显存失败最直接。稳妥起见，P 端和 D 端都应安装（P 端发送时如果源缓冲也在卡显存，同样需要它）。

**检查与安装**：

```bash
# 检查模块是否已加载
lsmod | grep peermem

# 未加载则加载
modprobe alixpu-peermem

# 安装后建议写入 /etc/modules-load.d/ 保证重启自动加载
```

**验证**：加载后在 Mooncake 的 `MC_LOG_LEVEL=TRACE` 日志里应能看到 register memory 成功，不再出现 bad address。

## 问题4: Warmup failed: KeyError 'choices'（context-length 不足）

### 症状

`sglang.bench_serving` 跑 vLLM/sglang 后端时，warmup 阶段直接失败，rc=1，stderr 末尾形如：

```
ValueError: Warmup failed - Please make sure benchmark arguments are correctly specified.
Error: Traceback (most recent call last):
  File ".../sglang/bench_serving.py", line 300, in async_request_openai_completions
    if data["choices"][0]["text"]:
       ~~~~^^^^^^^^^^^
KeyError: 'choices'
```

伴随的 CUDA / NVML warning 是误导项——`bench_serving` 是纯客户端，本身不需要 GPU，可以忽略。

### 根因

服务端启动时配置的最大上下文长度小于本次压测请求长度，server 直接以错误 JSON（不含 `choices` 字段）拒绝请求，客户端在解析 warmup 响应时抛 `KeyError: 'choices'`。

本次现场：

- 启动参数：`--context-length 16384`
- 压测参数：`--random-input-len 65536 --random-output-len 1536`（合计约 67K，远大于 16384）
- 把 `--random-input-len` 调小到 ≤ 16384 - output_len 后即正常。

### 排查方法

1. 直接 curl 服务端，看真实返回，错误响应通常会明确写 `maximum context length` 之类的信息。
2. 把 `--random-input-len` 临时降到很小（如 4096）重跑，能跑通就基本锁定是 context 长度问题。

### 解决

- **服务端**：启动 vLLM/sglang 时把 `--context-length`（或 vLLM 的 `--max-model-len`）调到 ≥ `random-input-len + random-output-len`，并预留余量；同时确认 KV cache 显存够用。
- **客户端**：本次跑的 input/output 长度不能超过服务端实际支持的 context 上限。

### 同类陷阱（同样表现为 `KeyError: 'choices'`）

- `--served-model-name` 与服务端注册名不一致，server 回 `model not found`。
- 服务端权重加载失败 / KV cache OOM，请求直接 5xx。

排查时先 curl 一次拿到原始错误体即可区分。

# 对比测试

## K8S 1P1D 对比 Host 1P1D（短序列）

![[Pasted image 20260901224521.png]]

## K8S 1P1D 对比 Host 1P1D（长序列）

![[Pasted image 20260901224556.png]]

## K8S 1P1D 对比 K8S 2P1D（短序列）

![[Pasted image 20260901224720.png]]

## K8S 1P1D 对比 K8S 2P1D（长序列）

![[Pasted image 20260901224755.png]]

到 20 并发，2P 的优势就明显了；tpot 依然稳定。可以对比测试 3P1D。

## K8S 3P1D 对比 K8S 2P1D（长序列）

![[Pasted image 20260901224848.png]]

3P1D 20 并发确实 ttft 好很多，tpot 只是微升。

## K8S 3P1D 对比 K8S 3P2D（长序列）

![[Pasted image 20260901224925.png]]

生产 3P2D 测试数据：

![[Pasted image 20260901224945.png]]

## Router 4核8G 对比 64核128G

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde537024e4aa570f2781f00ae151cbfa7eb75b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d512b627d9e3c35f7ea79ed04b22ec7fc193b19c44e82bbf3c58a6a2a4812267c71332d9efc14ea3c3?tmpCode=f73cd983-8f66-4f99-96ac-8fdda2431b9f)

结论：数据看没影响。

### Router 路由机制

要点：

1. **调度选 P 是 router 干的**。开启 `--policy cache_aware`（或新版的 `cache_aware_routing`）时，router 会按 token 化后的请求前缀去匹配自己维护的"每个 worker 缓存了哪些前缀"的近似树，挑命中最长的那台 P。这个树是 router 通过观察请求流量推断出来的，不会去实时拉 P 节点的真实 cache 状态。
2. **router 上的树是"近似"，不是 ground truth**。它会有偏差（被驱逐的前缀 router 不一定知道），所以 router 还会结合负载均衡（请求队列长度、in-flight 数）做权衡，避免热点。
3. **真正命中 KV 复用是在被选中的 P 节点上**。P 节点拿到请求后，再用自己真实的 radix cache 做一次精确前缀匹配，复用已有的 KV block，只对未命中的尾部做 prefill。
4. **D 节点不参与**。decode 节点没有调度选择问题，KV 由 P 通过 disaggregation 通道传过来。

> 记忆口诀：router 决定"去哪台 P"，P 决定"复用多少 KV"。

### Router 近似前缀树资源消耗分析

SGLang router（sglang-router-rs）是 Rust 实现的，整体内存比 Python 推理框架小很多。主要消耗分四块：

| 项 | 量级 | 说明 |
|---|---|---|
| 近似 radix tree | 1–3 GB（典型） | 所有 P worker 共享一棵带 worker 标签的树，由 `--max-tree-size`（默认 2^24 ≈ 16M 节点）封顶；每个节点 ~50–100B（token + 父子指针 + worker bitset + 时间戳） |
| Tokenizer | 200–500 MB | 看 vocab 大小，Llama3/Qwen 词表 ≥128K 会偏大 |
| Rust runtime + HTTP server + in-flight buffer | 500 MB–1 GB | 请求队列、metrics、连接池 |
| 碎片 + headroom | 500 MB–1 GB | jemalloc/mimalloc 碎片，长跑会累积 |

**8Gi 够不够？看负载：**

- ✅ 中等 QPS（< 1k）+ 上下文 ≤ 32K：够。稳态 RSS 一般 2–4 GB，8Gi 有足够 headroom。
- ⚠️ 长上下文（128K / 256K）或高 QPS：偏紧。长 prompt 让树膨胀飞快，建议 12–16 Gi。
- ⚠️ 常驻不重启（多周）：碎片会慢慢吃内存，建议留 30–40% headroom。

**比加内存更值得先做的调参：**

1. `--max-tree-size N` —— 直接封顶树节点数，超了走 LRU 驱逐。先压低这个值最立竿见影。
2. `--eviction-interval-secs`（默认 60）—— 调短让冷 prefix 更早释放。
3. `--cache-threshold`（默认 0.5）—— 低于这个命中比就视作没命中、不写树，能减少树膨胀。
4. 建立 RSS 基线：`kubectl top pod` 或容器内 `cat /proc/1/status | grep VmRSS`，跑 1–2 周看曲线再决定扩容。

**CPU 4 核**：router 是 tokenization + tree lookup 主导，4 核在 1–2k QPS、prompt 平均 ≤ 8K token 通常够。如果 prompt 长且 QPS 高，tokenization 会先成瓶颈——这时加 CPU 比加内存更有用。

## cni0 flannel 的 MTU 设置 1450 VS 8950

![[Pasted image 20260901225839.png]]

要点：

1. **物理层对齐**：所有集群机器的 `bond` 和 `eth` 的 MTU 要一致（bond 是 eth 的聚合，跨机不一致会出现丢包 / PMTU 黑洞）。
2. **Pod 网络层对齐**：`cni0` 需要跟 `flannel.1` 一致。`flannel.1` 是 VXLAN 隧道，有约 50 字节封装开销：
   - 物理 1500 → `flannel.1` / `cni0` = **1450**
   - 物理 9000（巨型帧）→ `flannel.1` / `cni0` = **8950**
3. **检查命令**：

```bash
# 各接口 MTU 一览（关注 bond、eth、cni0、flannel.1）
ip link show | grep -E 'bond|eth|cni0|flannel'

# 探测路径 MTU（-M do 禁止分片，逐步加大 -s）
ping -M do -s 8922 <对端节点IP>   # 8922 + 28字节IP/ICMP头 = 8950
```

## 去除 hostNetwork 测试

报错。

## mini-lb vs sgl-router（3P1D）

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde537024e4aa570f2781f00ae151cbfa7eb75b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d52edf71a5519e41b833cd2060ff87ff8ce588b1726086dddc99dd12a41ae3c350b9939b85c4e97c21?tmpCode=be45d8b4-ca7d-4f69-bbc1-c4744df0fd60)

## sglang-router + 缓存命中 vs mini-lb + disable-radix-cache

worker 映射配置：

```json
{
  "10.244.7.15":  ["http://11.159.106.181:31768/v1/chat/completions"],
  "10.244.6.67":  ["http://11.159.106.181:31768/v1/chat/completions"],
  "10.244.14.175":["http://11.159.106.181:31768/v1/chat/completions"]
}
```

## 参数调优实验

### 去除 DEEPEP 参数，配置 MC_NUM_QP_PER_EP=8（1P1D 对比）

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde537024e4aa570f2781f00ae151cbfa7eb75b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d5206748ac9722f3e890009d29e96ce269a0955d67a5f53319f083a2ba7037545088d7f93e163e5897?tmpCode=53f1a96c-70e4-4291-801d-61657c91fe71)

1P（16 卡）只能撑住 10 并发。

### MC_USE_NVLINK_IPC=1

强制 Mooncake 在同一台服务器内部进行数据传输时，使用基于 NVLink 的 IPC（进程间通信）机制，而非 PCIe P2P 或共享内存拷贝。

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde537024e4aa570f2781f00ae151cbfa7eb75b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d5118cc18d383301ce43356a6b329d9592751745fe4b36c2e12386f89c8a647e5ab7435268ef900c06?tmpCode=684a7f5e-39f9-4f28-b79c-7b4d1b512954)

看来 D 节点内卡间通信走的就是 ICN。

### Decode 设置 TP-size=8, DP-size=2

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde537024e4aa570f2781f00ae151cbfa7eb75b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d59870371a5de3263cef404835d60285861ca10e8c7944800866f9af89a8d8ead82d7c4f5259d87655?tmpCode=50ec929c-8ce2-46c6-b6ca-9dacb43b856e)

奇怪，ttft 竟然变差了。

### moe-dense-tp-size 设置为 4

报错，只能是 1 或者 None。

这是 SGLang 当前实现的限制，`moe-dense-tp-size` 目前只支持 1 或 None（等同于 1）。

原因（实现复杂度）：`moe-dense-tp-size > 1` 意味着要在 DP Attention 模式下，把 GPU 分成子组做 Attention 的 Tensor Parallel。这需要：

- 额外的 NCCL 通信组（子组内 all-reduce）
- Attention 权重按子组切分
- KV cache 在子组间的管理逻辑

SGLang 目前只实现了 `moe-dense-tp-size=1`（每卡独立算 attention）这一条路径。

### remove decode dp

改动参数：

```
--enable-dp-attention \
--dp-size 1 \
```

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde537024e4aa570f2781f00ae151cbfa7eb75b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d503a5aef75dd070cd25e056469a33443f64a1231566b21df5523b5f2b3030d39623ad52d7e9a4029a?tmpCode=f1004c0b-957d-4c4b-9f95-8f6d9b02ccd5)

**传统 TP（不用 DP Attention）**：所有 16 卡协同处理同一批 tokens，不管是 Attention 还是 MoE 层：

- Attention: 16 卡 Tensor Parallel → 需要 all-reduce 通信
- MoE FFN: 16 卡 Tensor Parallel → 需要 all-reduce 通信

**开启 DP Attention 后（dp-size=16, moe-dense-tp-size=1）**：

- Attention: 每张卡独立处理各自的请求（Data Parallel，无通信）
- MoE FFN: 16 卡 Expert Parallel → all-to-all 通信（DeepEP）

关键等式：`tp-size = dp-size × moe-dense-tp-size`，即 16 = 16 × 1

- Attention 层：每张 GPU 独立处理自己分到的请求，完全无通信开销
- MoE 层：所有 16 张 GPU 通过 Expert Parallelism 协作，tokens 通过 all-to-all（DeepEP）路由到对应 expert

**为什么 Decode 适合这么做？**

Decode 阶段每步每个请求只处理 1 个 token，Attention 计算量极小（1 个 query token vs KV cache），用 16 卡 TP 来算一个 token 的 attention 是严重浪费。改成 DP 后，每张卡独立算自己负责的请求的 attention，零通信，效率大幅提升。

当前 D 节点 dp-size=16 是标准且合理的选择，原因：

1. Decode 阶段 attention 计算量极小，不需要 TP 来分摊
2. DP=16 意味着 16 路数据并行，能同时服务更多请求
3. `moe-dense-tp-size=1` 消除了 attention 层的 all-reduce 通信
4. MoE 层仍然有 16 卡的 Expert Parallelism，expert 覆盖充分

**一般规则**：对于 Decode 节点，dp-size 尽量等于 tp-size（即 dense_tp=1）。只有当单卡显存放不下完整的 attention 参数（如模型 attention head 特别多、hidden dim 特别大）时，才需要降低 dp-size、提高 dense_tp。Kimi-K2.6 用 W4A8 量化后，单卡放 attention 参数绑绑有余，所以 dp=16 没问题。

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde537024e4aa570f2781f00ae151cbfa7eb75b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d57d6699015c56cf899ba18bc420d8127a97fa819127a775d543291c3b810058e41f725db89f04db3e?tmpCode=a8cdc561-8b39-4d58-b8b4-949ccd500da5)

**W4A8 量化的影响**：

- W4：所有权重（attention、MoE expert、embedding、LM head）都量化到 4-bit 存储，显存占用约为 FP16 的 1/4
- A8：激活值（运行时中间结果）使用 INT8 计算，加速 GEMM
- 量化后 MoE expert 参数虽然占比最大，但因为 W4 压缩 + EP 分布在 16 卡上，每卡实际存储量可控
- MLA 的 KV cache 本身就是压缩表示，再加上量化，Decode 阶段显存效率很高

这就是为什么 `moe-dense-tp-size=1` 可行——非 MoE 参数（attention + embedding + norm）量化后单卡完全放得下。

### --cuda-graph-bs 1 2 3 4 5 6 7 8 10 12 14 16 18 20 22 24 26 28 30 32 40 48 56 64

#### CUDA Graph 原理说明

CUDA Graph 是 NVIDIA 提供的把一连串 GPU kernel 的启动过程"录制"下来、之后整体"回放"的机制，核心目的是消除 CPU 侧逐个启动 kernel 的开销。

**要解决的问题**：GPU 上执行一个 kernel 前，CPU 都要做一次 launch（约几微秒）。Prefill 阶段 kernel 大（算几千上万 token），launch 开销可忽略；但 Decode 阶段每步只算 1 个 token，kernel 几微秒就算完，大量时间耗在 CPU 逐个 launch 上——一层 Transformer 几十个 kernel × 几十层，GPU 经常在"等 CPU 发活"。

**做法**：

1. Capture（录制）：跑一遍前向计算，把整个 kernel 序列（顺序、参数、依赖）录制成静态的"图"；
2. Replay（回放）：之后每个 decode step，CPU 一条指令回放整张图，所有 kernel 按序执行，无逐个 launch 开销。

**为什么参数是一串 batch size**：CUDA Graph 录制时张量 shape 固定，而 batch size 每步都在变。所以预先对一批"桶"各录一张图，运行时把实际 batch padding 到最近的桶再回放。

| 桶配置 | 权衡 |
|---|---|
| 桶多且密 | padding 浪费少、匹配精确，但录制耗时长、显存占用大（每张图持有静态 buffer） |
| 桶少且疏 | 启动快、省显存，但 padding 浪费的计算多 |

**限制**：只用于 decode，不用于 prefill（prefill 序列长度变化大、计算密集，收益低且 shape 无法穷举）；图内不能有动态控制流、CPU 同步，显存地址要固定（所以配合静态 KV cache 布局）。

![[Pasted image 20260901225732.png]]

实测观察：这组密集的桶对压测没啥效果。可能瓶颈不在 kernel launch，比如被通信、KV 传输或调度占住，或 dp-size=16 下每卡 batch 本来很小、开销占比不高。

# 上线配置

## 服务配置

| 组件 | 副本数 | ppu卡 | 备注 |
|---|---|---|---|
| sglang-router | 2 | 0 | 开启 kv aware |
| prefill | 3 | 48 | 打开 radix-cache |
| decode | 2 | 32 | dp-size=16 |

## 升级镜像到 sglang 0.5.12

- [升级文档](https://aliyuque.antfin.com/alinpu_engineering/snxi21/reii905d1sec10uf)

## 上线流量分析（3P2D）

周六流量分析：

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde537024e4aa570f2781f00ae151cbfa7eb75b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d54d6d99fed0b2656c8cb6d6fa2678ad89192f52d4242efeea9ae9396b1c4b5b816e9914f7c1628841?tmpCode=3ccc8aae-2f8d-46ac-bddb-bf2170ccc843)

- Decode 并发综合数和 TPOT 的曲线很一致，有完整的正相关性。
- 并发达到 30，TPOT 会上升到 60ms。
- TTFT 平均 2～3s。
