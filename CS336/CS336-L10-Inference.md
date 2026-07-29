---
tags:
  - CS336
  - inference
  - optimization
  - quantization
  - speculative-sampling
  - vLLM
lecture: L10
aliases:
  - 推理优化
  - Inference
---

![[Pasted image 20260729000506.png]]

---

## Part 1: 理解推理工作负载

### 1.1 推理的定位

推理（Inference）出现在三类场景：

- **实际使用**：chatbot、代码补全、agent、批量数据处理
- **模型评估**：如 instruction following 评测
- **强化学习**：采样大量生成结果，再施加 reward

**为什么效率至关重要**：训练是一次性成本，推理被反复执行无数次。OpenAI 每天处理约 8.6T tokens（作为参考，DeepSeek v4 训练只用了 32T tokens）。

- Chatbot：大部分 token 给人看，人是瓶颈
- Agent：query → 内部 trace → 输出给人，token 数量可以无上限增长
- Token 生成量 = 计算花费

**推理服务商：**

| 类型 | 代表 |
|---|---|
| 闭源模型 | OpenAI、Anthropic、Google |
| 开源权重模型 | Together、Fireworks、Baseten、DeepInfra、Groq、Cerebras |

**开源推理框架：**

| 框架 | 来源 | 特点 |
|---|---|---|
| vLLM | Berkeley | 首创 PagedAttention，通用默认选择 |
| SGLang | Berkeley | 首创 RadixAttention，适合 agent 工作负载 |
| TensorRT-LLM | NVIDIA | 针对 GPU 高度优化 |
| llama.cpp | 社区 | 纯 C++，支持 CPU 推理，可本地运行 |

### 1.2 "快"的含义（指标）

| 指标 | 含义 | 适用场景 |
|---|---|---|
| TTFT（Time-to-first-token） | 用户等待第一个 token 的时间 | 交互式应用 |
| Latency（秒/token） | 单条 query 生成 token 的速度 | 交互式应用 |
| Throughput（token/秒） | 多条 query 合计的生成速度 | 批处理 |

**推理 vs 训练的本质差异：** 训练时能看到所有 token，可以沿序列维度并行（Transformer 中的 matmul）；推理必须逐 token 顺序生成，无法沿生成维度并行，因此更难充分利用算力。

---

## Part 2: 推理的算术强度分析

### 2.1 复习：算术强度

**算术强度（Arithmetic Intensity）** = FLOPs / 字节传输量，即每传输 1 字节做了多少次计算，希望越高越好。

以矩阵乘法 X(B×D) @ W(D×F) 为例：

- FLOPs = 2·B·D·F
- 字节传输 = 2·B·D + 2·D·F + 2·B·F（读 X、读 W、写 Y，bf16 每个 2 字节）
- 当 B 远小于 D 和 F 时，算术强度 ≈ B

**H100 的加速器强度：** 989 TFLOPS / 3.35 TB/s ≈ **295 FLOPs/byte**

- 算术强度 > 295 → compute-bound（好）
- 算术强度 < 295 → memory-bound（差）
- 结论：compute-bound 当且仅当 B > 295
- 极端情况 B=1（矩阵-向量乘）：算术强度 = 1，memory-bound——**这正是推理的处境**

### 2.2 KV Cache

**朴素推理的问题：** 每生成一个 token，都要把历史输入 Transformer，生成 T 个 token 需要 O(T³) FLOPs（一次前向 O(T²)）。

**解决方案：** 在 HBM 中存储 KV cache。对每个序列(B)、token(S)、层(L)、头(K)，存储一个 H 维向量。

**推理的两个阶段：**

| 阶段 | 说明 | 特点 |
|---|---|---|
| Prefill | 给定 prompt，编码成向量 | 可像训练一样并行 |
| Generation | 逐个生成新 token | 顺序执行 |

### 2.3 MLP 层的算术强度

S = 条件 token 数，T = 生成 token 数。MLP 含 Wup、Wgate、Wdown 三个矩阵（F = 4D）。

- FLOPs = 6·B·T·D·F
- 字节传输 = 4·B·T·D + 4·B·T·F + 6·D·F
- 当 B·T 远小于 D 和 F 时，算术强度 ≈ B·T

**两阶段分析：**

| 阶段 | B·T | 算术强度 | 结论 |
|---|---|---|---|
| Prefill | B·S（大） | B·S | 容易 compute-bound（好） |
| Generation | B·1 | B | 取决于并发请求数 B |

Generation 的问题：(1) T=1，每次只生成一个 token；(2) B 是并发请求数，交互式应用中不可预测。

### 2.4 Attention 层的算术强度

S = 已生成的历史 token 数，T = 待生成的新 token 数。使用 FlashAttention。

- FLOPs = 4·B·S·T·D
- 字节传输 = 4·B·S·D + 4·B·T·D
- 算术强度 = S·T / (S + T)

**两阶段分析：**

| 阶段 | T | 算术强度 | 结论 |
|---|---|---|---|
| Prefill | T=S | S/2 | 好（随序列长度增长） |
| Generation | T=1 | <1 | 差（无法改善） |

**关键区别：** 与 MLP 不同，Attention 的算术强度不依赖 B，batching 无济于事！

原因：MLP 层中所有序列共享同一组权重（Wup、Wgate、Wdown 不依赖 B）；Attention 层中每个序列有自己的 KV cache（Q、K、V 都依赖 B）。

### 2.5 小结

|   | MLP 算术强度 | Attention 算术强度 |
|---|---|---|
| Prefill | B·S | S/2 |
| Generation | B（需并发请求） | <1（无法改善） |

**核心结论：Prefill 是 compute-bound，Generation 是 memory-bound。**

### 2.6 延迟与吞吐

基于 Llama 2 13B 在 H100 上的理论分析：

- 参数量 = 2·V·D + D·F·3·L + (2·D·N·H + 2·D·K·H)·L
- 参数显存 = 2 × 参数量（bf16）
- KV cache / 序列 = S · (K·H) · L · 2 · 2（key+value，bf16）
- 总显存 = B × KV_cache_per_seq + 参数显存
- 延迟 = 总显存 / 显存带宽（每步需读取所有参数和 KV cache）
- 吞吐 = B / 延迟（并行生成 B 个 token）

**增大 batch size 的效果：**

| Batch Size | 延迟 | 吞吐 | 是否装得进显存 |
|---|---|---|---|
| 1 | 最好 | 最差 | 是 |
| 64 | 变差 | 变好 | 是 |
| 256 | 更差 | 更好但收益递减 | **装不下**（超 80GB） |

- 增大 B → 延迟变差（KV cache 随 B 线性增长，读写更多）
- 增大 B → 吞吐变好（摊薄读取参数的成本）
- **延迟与吞吐的 tradeoff：** 小 batch 利延迟差吞吐，大 batch 利吞吐差延迟

**并行策略：**

- 简单并行：启动 M 份模型副本，延迟不变，吞吐 ×M
- 复杂并行：shard 模型和 KV cache

**TTFT 优化：** TTFT 本质上取决于 prefill 时间 → prefill 阶段用小 batch 加速 TTFT，generation 阶段用大 batch 提升吞吐。

---

## Part 3: 有损加速——降低推理复杂度

### 3.1 减少 KV Cache 大小

核心目标：减小 KV cache（因为推理是 memory-bound），同时不损失太多精度。

#### Grouped-Query Attention (GQA)

**思路：** N 个 query 头，但只有 K 个 key/value 头，每个 KV 头服务 N/K 个 query 头。

| 类型 | K 值 | KV cache 大小 |
|---|---|---|
| MHA（Multi-Head Attention） | K=N | 最大 |
| MQA（Multi-Query Attention） | K=1 | 最小 |
| GQA（Grouped-Query Attention） | 1 < K < N | 折中 |

GQA 将 KV cache 缩小 N/K 倍 → 减少显存 → 提速（因为 memory-bound）。

以 Llama 2 13B 为例：MHA(K=40, B=64) → GQA(K=8, B=64) 延迟变差但吞吐变好且能装进显存 → 继续增大 B=256 吞吐进一步提升。

#### Multi-head Latent Attention (MLA)

DeepSeek v2 提出。

- **普通 attention：** KV cache = K = W_K·h, V = W_V·h（N·H 维）
- **MLA：** 存压缩向量 c = W_c·h（C 维），需要时再投影还原 K = W_K·c, V = W_V·c
- DeepSeek v2：将 N·H = 16384 维压缩到 C = 512 维
- **注意：** MLA 与 RoPE 不兼容，需额外加 64 维给 RoPE，总计 512 + 64 = 576 维
- 精度方面：MHA > GQA（但更贵）；MLA 甚至略优于 MHA 且便宜得多

#### Cross-Layer Attention (CLA)

思路：跨层共享 KV（类似 GQA 跨头共享 KV），在精度和 KV cache 大小的 Pareto 前沿上有改善。

#### Local（Sliding Window）Attention

- **思路：** 只看局部上下文（对建模最相关的部分）
- 有效上下文随层数线性增长
- KV cache 与序列长度无关！
- 问题：可能损失精度
- 解决：将 local attention 与 global attention 交错（hybrid layers）

#### DeepSeek v4 Attention

支持 1M 上下文长度，采用三种注意力混合：

| 类型 | 机制 |
|---|---|
| CSA（Compressed Sparse Attention） | 每 m 个 token 压缩成 1 个 |
| DSA（DeepSeek Sparse Attention） | 选取 top-k |
| HCA（Heavily Compressed Attention） | 压缩更激进 |

#### 小结

- 降低 KV cache 维度：GQA、MLA、CLA
- Local attention（截断 KV cache）用于部分层
- 其他方向：linear attention / state-space models（Mamba 2、GatedDeltaNet）、diffusion models

### 3.2 量化（Quantization）

**核心思想：** 降低数字精度 → 减少显存 → 提升延迟和吞吐（因为 memory-bound）。

**量化/反量化机制：**

```
x = 5.2342
scale = 0.1
zero_point = 4
x_quant = round(x / scale) + zero_point   # 量化: 56
x_approx = (x_quant - zero_point) * scale  # 反量化: 5.2
```

**精度格式对比：**

| 格式 | 字节数 | 范围 | 用途 |
|---|---|---|---|
| fp32 | 4 | — | 训练（参数 + optimizer state） |
| bf16 | 2 | — | 推理默认 |
| fp8 | 1 | [-240, 240] (e4m3, H100) | 可训练（需胆量） |
| int8 | 1 | [-128, 127] | 仅推理，比 fp8 便宜但精度低 |
| int4 | 0.5 | [-8, 7] | 更便宜，精度更低 |

**量化方法：**

| 方法 | 说明 |
|---|---|
| QAT（Quantization-Aware Training） | 训练时在前向传播中模拟量化误差（quantize-and-dequantize）。优点：权重适应量化；缺点：需大规模训练 |
| PTQ（Post-Training Quantization） | 训练后进行，成本低。在样本数据上确定每层/张量的 scale 和 zero point |
| GPTQ | 用 Hessian 信息更新未量化权重以补偿量化误差 |
| AWQ（Activation-aware Quantization） | 观察：部分 activation channel 数值大 → 对应权重更重要 → 给这些权重分配更高精度。只需保留 0.1-1% 的权重高精度。fp16→int3：4 倍内存减少，3.2 倍加速 |

### 3.3 模型剪枝（Model Pruning）

**核心思想：** 直接裁剪昂贵模型的部分结构使其更轻量，然后修复。

NVIDIA 的算法：

1. 在小校准集（1024 样本）上识别重要的 {层, 头, 隐藏维度}
2. 移除不重要的层，得到更小模型
3. 将原模型蒸馏到剪枝后的模型

**从零训练 vs 蒸馏：**

| 方法 | 步骤 |
|---|---|
| From scratch | 定义更快架构 → 训练 |
| Distillation | 定义更快架构 → 用原模型（不同架构）初始化权重 → Repair（蒸馏） |

---

## Part 4: 无损加速——Speculative Sampling

### 4.1 动机

推理两阶段的不对称性：

- **Prefill：** 并行编码 token（compute-bound），同时给出概率
- **Generation：** 逐 token 生成（memory-bound）

即：**验证（checking）比生成（generation）快。**

### 4.2 算法

用更便宜的 draft model p 猜测几个 token（如 4 个），再用 target model q 并行验证，接受合理的 token。

这是基于 proposal p、target q 的改进版 rejection sampling：

- 修改点：始终至少生成一个候选（普通 rejection sampling 会一直循环）
- **关键性质：保证从 target model 精确采样！**

### 4.3 正确性证明（双词表示例）

假设词表 {A, B}，target 概率 [q(A), q(B)]，draft 概率 [p(A), p(B)]，且 p(A) > q(A)（draft 过采样 A，则 p(B) < q(B)）。

残差概率 max(q-p, 0) = [0, 1]

- P[采样 A] = p(A)·(q(A)/p(A)) + p(B)·1·0 = **q(A)** ✓
- P[采样 B] = p(B)·1 + p(A)·(1 - q(A)/p(A))·1 = **q(B)** ✓

### 4.4 实践与扩展

**典型配置：**

- Target 70B，Draft 8B
- Target 8B，Draft 1B
- 尽量让 draft model 接近 target（通过蒸馏）

**改进 draft model 的扩展：**

| 方法 | 思路 |
|---|---|
| Medusa | draft model 并行生成多个 token |
| EAGLE | draft model 从 target model 获取高层特征 |

**总结：** 利用验证与生成的不对称性，从 target model 精确采样，draft model 方面有大量创新空间。

---

## Part 5: 动态工作负载处理

训练时拿到的是 dense 的 B×S 张量；推理时请求到达和完成时间不同，形成 ragged array。

### 5.1 Continuous Batching

**问题：** 请求到达和完成时间不同 → batch 是参差不齐的数组。

**解决方案——iteration-level scheduling：**

- 逐步 decode
- 新请求到达时立即加入 batch（不必等当前 batch 生成完毕）

**问题：** batching 需要所有序列维度相同，但请求长度各异。

**解决方案——selective batching：**

- 训练时：所有序列等长，操作 B×S×H 张量
- 推理时：不同长度 [3,H]、[9,H]、[5,H] 等
- **Attention 计算：** 各序列独立处理
- **非 Attention 计算：** 将所有序列拼接成 [3+9+5, H] 一起处理

### 5.2 PagedAttention

vLLM 论文的核心贡献。

**之前的做法：**

1. 请求到达
2. 为 prompt 和 response 预分配 KV cache 空间（按最大长度）

**问题——内存碎片化（类似硬盘碎片）：**

- **内部碎片：** 实际生成的 token 远少于预分配（浪费）
- **外部碎片：** 各请求的 section 之间有未使用的空隙

**解决方案——PagedAttention（借鉴操作系统的分页机制）：**

- 将序列的 KV cache 分割为非连续的 block
- 多个请求可共享 KV cache（如共享 system prompt）
- 共享前缀的序列：block 级 copy-on-write

**KV cache 共享场景：**

- 共享 system prompt
- 同一 prompt 采样多个响应（如程序合成）

**vLLM 的其他优化：**

- 融合 block 读取和 attention 的 kernel（减少 kernel launch 开销）
- 使用最新 kernel（FlashAttention、FlashDecoding）
- 使用 CUDA graphs 避免 kernel launch 开销

**总结：** 借鉴操作系统的分页思想，高效利用显存处理动态工作负载。

---

## 总结

- **推理很重要**：实际使用、评估、强化学习都需要
- **与训练特性不同**：memory-bound、动态工作负载
- **加速技术**：新架构（GQA/MLA/CLA/Local Attention）、量化、剪枝/蒸馏、Speculative Sampling
- **系统思想**：speculative execution（投机执行）、paging（分页）
- **新架构有巨大的改进潜力**

---

## 相关链接

- 算术强度基础：[[CS336-L6-Triton]]
- GPU 硬件与 memory-bound 分析：[[CS336-L5-GPUs-TPUs]]
- 并行策略（shard 模型与 KV cache）：[[CS336-L8-Parallelism-2]]
- Tokenization 对序列长度的影响：[[CS336-L1-Tokenization]]
- 课程进度：[[课程进度]]
