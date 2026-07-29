---
tags:
  - CS336
  - parallelism
  - distributed
  - FSDP
  - ZeRO
  - MoE
lecture: L8
aliases:
  - 并行策略进阶
  - 3D并行
---

## Part 1: 网络基础

单 GPU 存在算力和显存上限，必须多 GPU / 多机并行。

**集合通信原语（Collective Communication）：** All-Reduce、Broadcast、Reduce、All-Gather、Reduce-Scatter。 关键等价关系：All-Reduce = Reduce-Scatter + All-Gather（带宽受限下已是最优）。

**网络拓扑：**

- GPU：节点内全互联（NVLink，最多 ~256 GPU），节点间 tree/switched 网络
- TPU：toroidal mesh（适合 TP）；新代 TPU 转向 tree/switched（适合 MoE 的 all-to-all）
- 不能把所有 GPU 全互联——domain size 受物理/成本限制

**多机扩展目标：** 显存线性扩展 + 算力线性扩展 + 简洁的通信原语。

---

## Part 2: 并行策略

### 2.1 数据并行（Data Parallelism）

Naive DP：batch 切分到 M 张卡，各算梯度后 all-reduce 同步。

- 算力扩展：线性（B/M per GPU）
- 通信：2×#params per step
- 显存扩展：无（每卡存完整模型）

**显存开销（混合精度 + Adam）：** 每参数约 16 bytes

- 2B 模型参数 (BF16) + 2B 梯度 (BF16) + 4B master weights (FP32) + 4B Adam m + 4B Adam v

### 2.2 ZeRO / FSDP

核心思想：利用 Reduce-Scatter + All-Gather 等价性，分片冗余状态。

|   |   |   |   |
|---|---|---|---|
|Stage|分片内容|通信量|显存节省|
|ZeRO-1|优化器状态|2×#params（与 DDP 相同，免费）|有|
|ZeRO-2|+ 梯度|2×#params（几乎免费）|更多|
|ZeRO-3 / FSDP|+ 参数|3×#params（1.5× DDP）|最大|

**FSDP 工作方式：**

- 前向：按需 all-gather 参数 → 计算 → 立即释放
- 反向：再次 all-gather 参数 → 算梯度 → reduce-scatter 梯度 → 释放
- 关键优化：通信与计算 overlap（all-gather 与上一层计算并行）

**8×A100 80G 能装多大模型（BF16, 12B/param）：** Baseline ~6.7B → ZeRO-1 ~16B → ZeRO-2 ~24.6B → ZeRO-3 ~53.3B

**DP 的局限：** batch size 有上限（通信开销）；ZeRO-3 不减少 activation memory。

### 2.3 模型并行（Model Parallelism）

与 ZeRO-3 的区别：ZeRO-3 传参数，模型并行传 activation。

#### Pipeline Parallel（按层切 / 深度方向）

- 每 GPU 负责若干连续层，传递 activation
- 问题：naive 分层利用率仅 1/n
- 解决：micro-batch 流水线（1F1B 等），bubble 比例 = (n_stages - 1) / n_micro
- 通信量：b×s×h（仅 activation，点对点）→ 适合跨节点慢网络
- 缺点：需要大 batch 才能隐藏 bubble

**Zero-bubble pipelining：** 将 backward 拆为"回传 activation"和"算权重梯度"两部分，后者可延后执行。

#### Tensor Parallel（按宽度切）

- 将矩阵乘法拆为子矩阵，各 GPU 持有部分列/行
- 前向：f = identity, g = all-reduce；反向反之
- Transformer 中的分配：QKV / up-proj → column-wise；attn output / down-proj → row-wise；norm/router → replicated
- 通信量：每层 8bsh × (n-1)/n，all-reduce → 需要高带宽低延迟
- 适用场景：节点内（≤8 GPU，NVLink）

**TP vs PP：**

- TP 无 bubble、不需大 batch、实现简单；但通信量大
- PP 通信小（点对点 activation）；但有 bubble、需大 batch

#### Sequence Parallel（配合 TP 减少 activation memory）

TP 只切 matmul 部分，LayerNorm / Dropout 等 pointwise op 的 activation 仍完整存在（10sbh/层）。 Sequence Parallel：沿 sequence 维度切分这些 pointwise op，用 all-gather / reduce-scatter 与 TP 衔接。 → activation memory 也实现线性扩展。

#### Expert Parallel（MoE 专用）

- 不切 matmul，而是把不同 expert 放不同 GPU，通过 all-to-all 路由 token
- 行为类似 TP（高带宽需求），但避免切分 matmul 带来的效率损失
- 通常 EP ≤ DP（共享 replica）
- 注意力层不能用 EP → 高 TP 利于 attention，低 TP + 高 EP 利于 MLP（Megatron 支持解耦）

#### Context Parallel / Ring Attention

沿 sequence 维度切分 activation，用于超长序列训练。

---

## Part 3: 组合策略（3D/4D Parallelism）

**经验法则：**

1. 先让模型装得下：TP/EP 用满节点内 GPU（≤8），PP 跨节点（或用 ZeRO-3）
2. 再用 DP 扩展到更多 GPU
3. batch size 不够时 gradient accumulation 换通信效率

**实际案例：**

|   |   |   |   |   |   |
|---|---|---|---|---|---|
|模型|DP|TP/SP|EP|PP|CP|
|Llama3 405B|128|8|0|16|1|
|Gemma 2|768|8|0|0|0|
|DeepSeek V3|? (ZeRO-1)|1|64|16|?|
|Mixtral 8×22B|2|4|8|4|1|
|Qwen 3|?|2|32|8|1|

**规律：** TP 一般 ≤ 8；EP 可以很大（但工程难度高）；长上下文阶段用大 CP。

**其他要点：**

- Activation recomputation 可换取更大 batch → 提升吞吐
- 大规模训练中 GPU 故障频繁（Llama3 405B 训练期间大量 GPU failure）
- 合理的 3D 并行配置可实现近线性扩展（utilization 不随规模下降）

![](https://intranetproxy.alipay.com/skylark/lark/0/2026/png/235356748/1784805590658-03d06633-9e0d-4824-91ed-332da873fa14.png)

---

## 相关链接

- 通信原语基础（AllReduce、NCCL）：[[CS336-L7-Parallelism-1]]
- 单 GPU 优化：[[CS336-L5-GPUs-TPUs]]、[[CS336-L6-Triton]]
- 推理中的 batching 与显存管理：[[CS336-L10-Inference]]
- 课程进度：[[课程进度]]