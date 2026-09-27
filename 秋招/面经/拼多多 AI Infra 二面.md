---
tags:
  - 面经
  - 拼多多
  - AI-infra
  - 二面
  - 概率题
  - ChunkedPrefill
  - FlashAttention
  - OnlineSoftmax
  - 算子
  - CUDA
  - GPU
aliases:
  - 拼多多二面
  - 拼多多 AI Infra 二面面经
company: 拼多多
position: AI Infra
round: 二面
date: 2026-09-18
---

# 拼多多 AI Infra 二面面经

> **项目简介（开场标准答案）**：见 [[秋招/面经/PTG项目简介|PTG项目简介]]（仅 vault 内）
> **关联**：[[秋招/面经/拼多多 ai infra面经|拼多多一面]] · [[秋招/面经/快手二面|快手二面]] · [[秋招/面经/商汤 大模型系统工程师面经|商汤面经]] · [[Infra/PD分离]] · [[CS336/CS336-L5-GPUs-TPUs|CS336 L5 GPUs/TPUs]]

---

## 原始题目清单（面试官的顺序）

| # | 板块 | 原始记录 | 整理后的题目 | 跳转 |
| --- | --- | --- | --- | --- |
| 1 | 思维题 | 一条线段分割成三个边，能组成三角形的概率是多少 | 折棍问题（Broken Stick）几何概率 | [[#Q1 一条线段随机切成三段，能组成三角形的概率是多少\|Q1]] |
| 2 | 推理调度 | chunk prefill | Chunked Prefill 机制、调参与 PD 分离的关系 | [[#Q2 Chunked Prefill 是什么，解决什么问题\|Q2]] |
| 3 | Kernel | flash attention 的原理 online softmax | FlashAttention 原理 + Online Softmax 推导 | [[#Q3 FlashAttention 的原理，Online Softmax 怎么推\|Q3]] |
| 4 | 底层软件 | 对算子了解吗 | 算子分类 / 融合 / Roofline 方法论 | [[#Q4 对算子了解吗\|Q4]] |
| 5 | 底层软件 | 对cuda了解吗 | CUDA 编程模型 / 内存层次 / 性能陷阱 | [[#Q5 对 CUDA 了解吗\|Q5]] |
| 6 | 硬件 | 对nvidia的卡了解吗 | 数据中心 GPU 谱系 / 规格怎么读 / 选型 | [[#Q6 对 NVIDIA 的卡了解吗\|Q6]] |

> [!tip] 这场二面的判读（先看这段）
> 二面**几乎脱离项目**，走的是「**思维题 + 推理内核原理 + 底层软硬栈**」三段式，共 6 问，**每一问都在探你知识下界有多深**。
> - **Q1 概率题是筛选题**，考的不是概率知识而是**建模速度**：能不能 30 秒内把「三段能组成三角形」翻译成「**每段都 < 1/2**」，然后立刻想到几何概率。答出 $1/4$ 只是及格；能给**两种推导**（单位正方形积分 + 单纯形中点三角形）并主动补 **n 段通式** $1-\frac{n}{2^{n-1}}$ 才算满分。
> - **Q2/Q3 是一条完整的推理内核链路**：Chunked Prefill 考**调度层**（怎么让 prefill 不阻塞 decode），FlashAttention 考**kernel 层**（怎么让 attention 不被 HBM 卡死）。判分点是**能不能定量**：chunk size 怎么算出来、HBM 访问量从 $O(N^2)$ 降到 $O(N^2d^2/M)$、块大小受什么约束。
> - **Q4/Q5/Q6 是「你是调包侠还是懂底层」的三连击，而且顺序是设计过的**：算子（软件抽象）→ CUDA（编程模型）→ 显卡（物理硬件）。答的时候要把三层**串成一条因果线**（Roofline 拐点决定算子瓶颈 → 瓶颈决定 CUDA 优化手段 → 硬件规格决定拐点），而不是三段孤立背诵。
> - **全场最大的失分风险是「装懂」**。Q4~Q6 一旦吹过头，面试官会立刻下钻到 `cp.async` / bank conflict / 寄存器溢出这一级。**正确姿势：先给结构化全景，再主动交代真实边界**（"我更多是读 FA/CUTLASS 源码 + Triton 写算子 + Nsight 定位，没有从零手写生产级 CUDA kernel"），然后立刻把话题拉回 PTG 实战案例。

> [!warning] 三条绝对不要说的话
> 1. ❌「Chunked Prefill 就是把长 prompt 切开」——漏掉「**和 decode 混批**」等于没答。切开本身不是目的，**把单次 iteration 时间钉死**才是。
> 2. ❌「Online Softmax 是一种近似」——它是**精确等价**变换（分子分母同乘一个修正因子，比值不变）。说成近似直接判死。
> 3. ❌ 把 NVIDIA 官方标的 **稀疏（2:4 sparsity）算力**当 dense 报——差整整 2 倍，懂行的人一听就知道你在背宣传页。

---

# 一、思维题

## Q1 一条线段随机切成三段，能组成三角形的概率是多少

> **答案：$\dfrac{1}{4}$**

### 开口版（30 秒，面试现场就这么说）

> 「**$1/4$**。三段长度和为 1，三角形不等式 $a+b>c$ 在 $a+b+c=1$ 的前提下等价于 $c<\frac12$，所以三个不等式合并成一句话：**每一段都必须短于总长的一半**。两个切点在单位正方形上独立均匀分布，把「三段都 $<1/2$」这块区域画出来，面积正好是 $1/4$。」

**这段的价值**：先给答案 → 再给**关键转化**（三角形不等式 ⟺ 每段 < 1/2）→ 最后给方法（几何概率）。面试官听到第二步就知道你会做，后面只是验算。

### 第一步：化简三角形不等式（本题的全部难点）

设线段长为 $1$（不失一般性，概率与总长无关），三段为 $a,b,c$：

$$a+b+c=1,\qquad a,b,c>0$$

三角形不等式三条：$a+b>c$、$a+c>b$、$b+c>a$。

把 $a+b=1-c$ 代入第一条：

$$1-c>c \;\Longrightarrow\; c<\frac12$$

同理 $a<\frac12$、$b<\frac12$。于是：

> [!important] 核心转化
> $$\text{能组成三角形}\iff \max(a,b,c)<\frac12$$
>
> **三条不等式塌缩成一条**：最长的一段不能超过总长的一半。做完这一步，题目就从「三角形」变成了「最大值的分布」，后面全是机械计算。

### 第二步：声明随机模型（不说清楚，答案不唯一）

**标准模型**：在 $[0,1]$ 上**独立均匀**取两个切点 $U,V\sim\mathcal U(0,1)$，三段为

$$a=\min(U,V),\qquad b=|U-V|,\qquad c=1-\max(U,V)$$

> [!note] 主动补一句（严谨性加分项）
> 「这题的答案**依赖『随机切』的定义**。我用的是标准模型——两个切点独立均匀。如果改成『先切一刀，再从两段里随机挑一段切第二刀』，答案就不是 $1/4$ 了。**如果不指定模型，我会先声明我用哪一个。**」
>
> 这句话展示你知道概率题的**测度前提**，比算对 $1/4$ 更能体现严谨。

### 第三步：推导一 —— 单位正方形上的几何概率（首选，能画出来）

样本空间 $(U,V)\in[0,1]^2$，面积 $=1$，均匀分布 → **概率 = 有利区域面积**。

由对称性，先算 $U<V$ 的上三角，最后乘 2。在 $U<V$ 内：$a=U,\;b=V-U,\;c=1-V$。

| 条件 | 化简 | 正方形上的区域 |
| --- | --- | --- |
| $a<\frac12$ | $U<\frac12$ | 左半平面 |
| $c<\frac12$ | $V>\frac12$ | 上半平面 |
| $b<\frac12$ | $V<U+\frac12$ | 对角线 $V=U+\frac12$ 下方 |
| （前提） | $U<V$ | 上三角 |

四者交集是一个**顶点为 $\left(0,\tfrac12\right),\left(\tfrac12,\tfrac12\right),\left(\tfrac12,1\right)$ 的直角三角形**，两条直角边长均为 $\frac12$：

$$S_{U<V}=\frac12\cdot\frac12\cdot\frac12=\frac18$$

写成积分（面试口头带过即可）：

$$S_{U<V}=\int_0^{1/2}\left[\left(u+\frac12\right)-\frac12\right]\mathrm du=\int_0^{1/2}u\,\mathrm du=\frac18$$

由对称性 $U>V$ 区域同样贡献 $\frac18$：

$$\boxed{P=\frac18+\frac18=\frac14}$$

### 第四步：推导二 —— 单纯形上的中点三角形（更优雅，说出来惊艳）

$(a,b,c)$ 均匀分布在平面单纯形

$$\Delta=\{(a,b,c):a+b+c=1,\;a,b,c\ge 0\}$$

上（正三角形，顶点 $(1,0,0),(0,1,0),(0,0,1)$）。

有利区域是 $\Delta$ 内同时满足 $a<\frac12,b<\frac12,c<\frac12$ 的部分。而三条直线 $a=\frac12$、$b=\frac12$、$c=\frac12$ **恰好经过 $\Delta$ 三条边的中点**，把 $\Delta$ 切成 **4 个全等的小正三角形**：

- 3 个角上的：分别对应 $a>\frac12$、$b>\frac12$、$c>\frac12$（不合法）
- 1 个正中间的：三边中点连线围成（合法）

$$P=\frac{\text{中间小三角形}}{\text{大三角形}}=\frac14$$

> [!tip] 为什么这个推导更好
> **不需要积分**，一眼看出「4 等分」，而且**天然可推广到 n 维单纯形**。如果面试官说「不用积分能看出来吗」，他就在等这个答案。

### 第五步：主动补充的延伸结论（拉开差距）

**① n 段通式**：随机切成 $n$ 段能组成 $n$ 边形的概率为

$$P_n=1-\frac{n}{2^{n-1}}$$

- 验算 $n=3$：$1-\frac34=\frac14$ ✓；$n=4$：$1-\frac48=\frac12$
- **推导**（用容斥，很干净）：合法 ⟺ 所有 $a_i<\frac12$。单个 $P(a_i>\frac12)$ 相当于「剩下 $n-1$ 段去分 $\frac12$ 的长度」，在单纯形上是 $(\frac12)^{n-1}=2^{-(n-1)}$ 的体积占比；而**任意两个 $a_i,a_j$ 不可能同时 $>\frac12$**（和会超过 1），所以容斥只有第一项：$P_n=1-n\cdot2^{-(n-1)}$。

**② 最长段的期望**：$\mathbb E[\max(a,b,c)]=\dfrac{11}{18}\approx0.611$
（已用蒙特卡洛 200 万次验证：实测 $0.61114$，与 $11/18=0.61111$ 吻合）

**③ 最长段超过一半的概率**：$P(\max>\frac12)=1-\frac14=\frac34$
→ **四分之三的情况下，最长段直接废掉了三角形**。这个直觉很有说服力：随机切两刀，很容易切出一段特别长的。

### 追问预案

| 追问 | 回答要点 |
| --- | --- |
| 切点不是均匀分布呢？ | 概率不再是 $1/4$，几何概率法失效，需按 $U,V$ 的联合密度重新积分。但**「每段 < 1/2」这个判据不变**——变的只是测度，不是判据。 |
| 切成三段后允许重新排列？ | 无影响。判据本身对称（只看 $\max$）。 |
| 用代码验证一下 | 三行：`u,v = random(), random()` → `a,b,c = min(u,v), abs(u-v), 1-max(u,v)` → 判 `a+b>c and a+c>b and b+c>a`。200 万次采样得 **0.2504**。 |
| 线段长度是 $L$ 不是 1？ | 概率不变。令 $a'=a/L$ 归一化即可。**几何概率只依赖形状不依赖尺度。** |
| 这和机器学习有什么联系？ | 这是**单纯形上的均匀采样**问题：$\text{Dirichlet}(1,1,1)$ 就是 3 维单纯形上的均匀分布，n 段切分对应 $\text{Dir}(1,\dots,1)$。MoE 的专家负载均衡、概率单纯形上的欧氏投影、熵正则化 RL 的策略空间都在这个几何体上。 |
| 变体：先切一刀，再随机挑一段切第二刀 | 判据仍是「每段 < 1/2」，但测度变了，需重新积分，答案 $\ne 1/4$。**遇到变体先回到判据，再重建测度**——这是通用套路。 |

---

# 二、推理内核

## Q2 Chunked Prefill 是什么，解决什么问题

> **一句话**：把长 prompt 的 prefill 切成固定 token 数的块，每次迭代只算一块，**并和 decode 请求混在同一个 batch 里跑**，从而把单次 iteration 的时间钉死，消除 prefill 对 decode 的队头阻塞。

### 开口版（45 秒）

> 「Chunked Prefill 解决的是 **prefill 和 decode 混部时的互相干扰**。Prefill 是 compute-bound、一次要吃几千上万 token；decode 是 memory-bound、每步每序列只算 1 个 token。不开 chunked prefill 的话，一个 80K 的长请求进来，它的 prefill 会独占 GPU 几百毫秒甚至几秒，**这段时间里同 batch 所有正在 decode 的请求全部卡住**，TPOT 出现尖刺、P99 尾延迟爆炸。
>
> 做法是：把长 prompt 切成比如 2048 token 一块，**调度器每个 iteration 只放一块 prefill，剩下的 token 预算留给 decode 请求**。这样单次 iteration 时间就被限制住了，TPOT 变平滑；同时因为 prefill（compute-bound）和 decode（memory-bound）在同一 batch 里互补，**GPU 利用率反而更高**。
>
> 代价是 prefill 被摊到多次迭代，**TTFT 会变长**；而且 chunk 太小会导致 GEMM 的 M 维太小、Tensor Core 打不满。所以本质是 **TTFT ↔ TPOT 的权衡**，靠调 chunk size 落在 SLA 上。」

### 一、为什么需要它：两个阶段的资源画像完全相反

| 维度 | Prefill | Decode |
| --- | --- | --- |
| 每次处理 token 数 | 整个 prompt（几千~几十万） | 每序列 **1 个** |
| GEMM 形状 | $M$ 很大 → 标准 GEMM | $M$ = batch，很小 → 退化成 **GEMV** |
| 瓶颈 | **Compute-bound**（算力） | **Memory-bound**（权重 + KV 搬运） |
| 算术强度 | 高（几百 FLOP/Byte） | 极低（$\approx 1\sim2$ FLOP/Byte） |
| 决定的用户指标 | **TTFT** | **TPOT / 吞吐** |
| 单次耗时 | 长（80K prompt 可达秒级） | 短（几十 ms） |

**混部时的三个冲突**：

1. **队头阻塞（Head-of-Line Blocking）**：长 prefill 占满整个 iteration，同 batch 的 decode 请求这一步出不来 token → TPOT 毛刺。
2. **显存峰值尖峰**：prefill 的 activation 峰值是 $O(L)$，80K 一次算完可能直接 OOM，或逼调度器预留大块显存 → 可容纳的并发 decode 数下降 → 吞吐下降。
3. **调度粒度太粗**：长请求要么整块进、要么整块等，调度器没有细粒度腾挪空间。

### 二、机制拆解（三个动作，一个都不能漏）

**动作 1 · 切块**
把 $L$ token 的 prompt 切成 $\lceil L/S\rceil$ 块，每块最多 $S$ 个 token（$S$ = `chunked_prefill_size`）。

**动作 2 · 混批（Mixed Batching / Piggybacking）—— 这才是核心**
调度器每 iteration 有一个 **token 预算** `max_num_batched_tokens`：

```
iteration t 的 batch：
  ├── decode 请求 A：1 token
  ├── decode 请求 B：1 token
  ├── decode 请求 C：1 token
  └── prefill 请求 D 的第 3 块：2048 token
  ────────────────────────────────────
  合计 2051 token ≤ 预算
```

Attention kernel 必须用 **varlen 接口**（`flash_attn_varlen_func` / `cu_seqlens`）处理「batch 内每条序列长度完全不同」的情况。

**动作 3 · 跨块读 prefix KV**
第 $i$ 块的 Q 要 attend 到前面 $0\sim(i-1)$ 块的所有 token：

- 前缀 KV **已在 paged KV cache 里，直接读，不重算**（重算的话复杂度会从 $O(L^2)$ 变成 $O(L^3)$）
- causal mask 变成**块状结构**：本块内部是下三角 causal，对前缀块是全 1（full attention）
- 这正是 FlashAttention 的 varlen + causal 组合能原生支持的原因

### 三、收益 vs 代价（定量）

| 维度 | 收益 | 代价 |
| --- | --- | --- |
| **TPOT** | ✅ 单次 iteration 时间被钉死，decode 步间隔稳定，**P99 尾延迟大幅下降** | — |
| **TTFT** | — | ⚠️ prefill 摊到多个 iteration，中间可能让位给别人 → **TTFT 变长**（高负载下尤其明显） |
| **显存** | ✅ activation 峰值从 $O(L)$ 降到 $O(S)$，长上下文不再 OOM，可容纳更多并发 | — |
| **算力利用率** | ✅ compute-bound 的 prefill 与 memory-bound 的 decode 混批 → **互补填满 SM 和 HBM 带宽** | — |
| **Kernel 效率** | — | ⚠️ $S$ 太小时 GEMM 的 $M$ 维太小（$M<64$ 基本喂不饱 Tensor Core）；prefix KV 被**每块重复从 HBM 读**，attention 从 compute-bound 退化到 memory-bound |
| **Launch 开销** | — | ⚠️ 块数变多 → kernel launch 次数变多 |

### 四、Chunk Size 怎么定（面试官最想听的定量部分）

**第一性原理**：让单次 iteration 时间**刚好等于** TPOT 的 SLA。

$$T_{\text{iter}}\approx\underbrace{\frac{S}{\Theta_{\text{prefill}}}}_{\text{prefill 块计算时间}}+\underbrace{T_{\text{decode}}}_{\text{同批 decode 开销}}\;\le\;\text{TPOT}_{\text{SLA}}$$

反解出上界：

$$\boxed{\;S\le\left(\text{TPOT}_{\text{SLA}}-T_{\text{decode}}\right)\times\Theta_{\text{prefill}}\;}$$

**代入 PTG 场景**（SLA：TPOT P99 < 50~60ms）：若单卡 prefill 吞吐 $\Theta_{\text{prefill}}\approx 8000$ token/s，$T_{\text{decode}}\approx 10$ms，则

$$S\le(0.050-0.010)\times 8000=320\ \text{tokens}$$

→ 说明**要守住 50ms 的 TPOT，chunk 必须切得很碎**。但切太碎 TTFT 会崩，所以实际是在 TTFT 和 TPOT 之间找可接受平衡点，**而不是无脑最小化 TPOT**。

**实操调参流程**（同一套方法论在 [[秋招/面经/快手 AI infra面经|快手一面]] Q10 用过）：

1. 固定 decode 并发数，扫 $S\in\{256,512,1024,2048,4096,8192\}$
2. 每点记录 **TTFT P50/P99**、**TPOT P50/P99**、**总吞吐**
3. 画 **TTFT–TPOT 联合曲线**（帕累托前沿），**不看单点**
4. 选**满足 TPOT P99 ≤ SLA 的最大 $S$** → 守住尾延迟的前提下把 TTFT 做到最好
5. 换输入长度分布重测（我们是平均 input 80K+，长尾重，$S$ 要比通用场景更小）

### 五、Chunked Prefill vs PD 分离（**必被追问，这是主战场**）

> [!important] 一句话记住
> **Chunked Prefill 是「时分复用」，PD 分离是「空分复用」。**
> 前者在**同一批 GPU** 上切时间片避免互相阻塞；后者用**不同的 GPU** 做物理隔离。二者**不互斥**，生产里通常同时开。

| 维度 | Chunked Prefill | PD 分离 |
| --- | --- | --- |
| 隔离方式 | 时间片（同卡混部） | 空间（不同卡 / 不同实例） |
| 消除干扰的彻底程度 | **部分**——只把干扰摊平，prefill 仍在抢 decode 的算力和显存 | **彻底**——物理隔离，互不影响 |
| 额外成本 | 几乎为零（纯调度策略） | **KV Cache 需跨节点传输**（RDMA / Mooncake），有传输延迟与带宽成本 |
| 资源弹性 | 好（同一批卡自适应负载） | 差（P:D 配比要标定，配错了一边闲置） |
| 适用场景 | 中小规模、显存充裕、请求长度均匀 | 大规模、长上下文、SLA 严格、P/D 资源画像差异极端 |
| 关键参数 | `chunked_prefill_size`、`max_num_batched_tokens` | P:D 配比、传输带宽、KV 命中率 |

**为什么 PTG 选了 PD 分离而不是只靠 Chunked Prefill？**（把话题拉回项目主场的钩子）

> 「两个原因。
>
> **第一，PPU 810E 是典型的『显存大、算力低』**——单卡 96GB HBM，显存对标 H20 但算力更低。这意味着 prefill（吃算力）和 decode（吃带宽）的资源画像差异被硬件**放大到极端**：chunk 开大保 TTFT，decode 就被饿死；chunk 开小保 TPOT，prefill 就慢到不可接受。**混部时无论怎么切 chunk，总有一方资源在被浪费。**
>
> **第二，我们平均 input 是 80K+ token**，单个请求的 prefill 绝对时间就很长。Chunked Prefill 只能把干扰**摊平**、不能**消除**——它治标，PD 分离治本。
>
> 所以我们上了 **3P2D（48 卡 Prefill + 32 卡 Decode = 80 卡）**，用 Mooncake + RDMA 传 KV，把 TTFT P99 压在 2~3s、TPOT 压在 50~60ms。**Chunked Prefill 我们也开着，但用途变了**：在 P 节点内部平滑多个长请求之间的调度，避免单个 80K 请求独占整个 P 节点。」

详见 [[Infra/PD分离]] 与 [[秋招/面经/快手二面|快手二面]] Q7。

### 六、工程参数速查

| 框架 | 参数 | 说明 |
| --- | --- | --- |
| **SGLang** | `--chunked-prefill-size` | 单块 token 数，默认随版本变化（常见 4096 / 8192），设 `-1` 关闭 |
| **SGLang** | `--max-running-requests` | 并发上限，与 chunk size 共同决定 batch 组成 |
| **vLLM** | `enable_chunked_prefill=True` | **V1 引擎默认开启** |
| **vLLM** | `max_num_batched_tokens` | 每 iteration 的 token 预算（prefill 块 + decode token 合计） |
| **vLLM** | `max_num_seqs` | 每 iteration 的序列数上限 |
| **TensorRT-LLM** | inflight batching + chunked context | 同类机制，术语叫 chunked context phase |

### 七、追问预案

| 追问 | 回答要点 |
| --- | --- |
| chunk 之间的 KV 要重算吗？ | **不重算**。前缀 KV 已写入 paged KV cache，后续块直接读。重算的话复杂度从 $O(L^2)$ 变 $O(L^3)$，不可接受。 |
| 总 FLOPs 变了吗？ | **基本不变**。causal attention 总 FLOPs 是 $\sum_i(\text{chunk}\times\text{prefix}_i)\approx L^2/2$，切不切块都一样。变的是 **HBM 搬运量**和 **GEMM 效率**，不是计算量。 |
| 那 chunk 小了到底亏在哪？ | 三处：① GEMM 的 $M$ 维小 → Tensor Core 利用率下降；② prefix KV 被每块重复从 HBM 读 → attention 部分变 memory-bound；③ kernel launch 次数增加。 |
| 开了 chunked prefill，TTFT 一定变差吗？ | **低负载下几乎不变**（没人抢占，块是连续调度的）；**高负载下会变差**（要和别人的 decode 抢 token 预算）。所以要看负载区间，不能一概而论。 |
| 和 Prefix Caching / RadixAttention 什么关系？ | 正交且互补。Prefix Cache 命中时那部分**根本不需要 prefill**，chunked prefill 只处理未命中的尾巴。Agent 场景（system prompt 大量复用）下两者叠加能把 TTFT 打下一个量级。见 [[Infra/SGlang]]。 |
| 和投机解码（Speculative Decoding / MTP）什么关系？ | 投机解码让 decode 每步验证 $k$ 个 token → **decode 的 token 预算变大**，挤压 prefill 块空间 → chunk size 必须重新标定。MTP 参数调整见 [[秋招/面经/商汤 大模型系统工程师面经\|商汤面经]] Q7。 |
| 为什么不干脆把 prefill 全丢到单独的卡上？ | 那就是 PD 分离。它要付 **KV 传输成本**和**配比标定成本**；小规模 / 负载波动大时，混部 + chunked prefill 的资源弹性更好。**这是规模决定的架构选择，不是谁更先进。** |
| chunk size 是全局一个值吗？ | 可以是，也可以按请求长度分档。更细的做法是让调度器**动态**决定每 iteration 塞多少 prefill token（token budget 自适应），SGLang / vLLM 都在往这个方向走。 |

---

## Q3 FlashAttention 的原理，Online Softmax 怎么推

> **一句话**：FlashAttention = **Tiling（分块）+ Online Softmax（流式归一化）+ Recomputation（反向重算）**，核心是**永不把 $N\times N$ 的注意力矩阵写进 HBM**，把一个 memory-bound 算子变成 compute-bound。

### 开口版（50 秒）

> 「标准 attention 要在 HBM 里物化两个 $N\times N$ 矩阵：$S=QK^\top$ 和 $P=\text{softmax}(S)$。$N=8\text{K}$ 时单个 head 的 $S$ 就是 6400 万个元素、128 MB，**光把 $S$ 写出去再读回来的 HBM 流量就远超做那两个 matmul 的时间**。所以标准 attention 是**严重 memory-bound**，算力利用率只有个位数。
>
> FlashAttention 的思路是**永远不把 $S$、$P$ 落到 HBM**：把 Q 和 K/V 切成小块，每次只把一个 Q 块和一个 K/V 块加载进片上 SRAM，在 SRAM 里算完局部 $S$ 和局部 softmax，直接累积到输出 accumulator，**整个 kernel 只往 HBM 写一次 $O$**。
>
> 但这里有个障碍：softmax 需要**整行的全局 max 和全局 sum** 才能归一化，而分块时你还没看到整行。解法就是 **Online Softmax**——维护 running max $m$ 和 running sum $\ell$，每来一个新块就更新，并**用 $e^{m_{\text{old}}-m_{\text{new}}}$ 这个修正因子把之前累积的分子和分母一起 rescale**。因为分子分母同乘一个因子、比值不变，所以这是**精确等价，不是近似**。
>
> 反向传播时不存 $N\times N$ 的 $P$，只存 $O$ 和 logsumexp $L$，**反向时按块现算**。FLOPs 增加了，但 HBM 访问从 $O(N^2)$ 降到 $O(N)$，实测 wall-clock 反而更快——典型的**用算力换带宽**。」

### 一、问题定义：标准 Attention 的 HBM 灾难

$$O=\text{softmax}\!\left(\frac{QK^\top}{\sqrt d}\right)V,\qquad Q,K,V\in\mathbb R^{N\times d}$$

| 步骤 | 操作 | HBM 流量 |
| --- | --- | --- |
| 1 | 读 $Q,K$，写 $S=QK^\top\in\mathbb R^{N\times N}$ | $O(Nd+N^2)$ |
| 2 | 读 $S$，写 $P=\text{softmax}(S)$ | $O(N^2)$ |
| 3 | 读 $P,V$，写 $O=PV$ | $O(N^2+Nd)$ |
| **合计** | | $\boldsymbol{O(Nd+N^2)}$ |

**代入实数感受一下**（$N=8192$，$d=128$，BF16 = 2 Byte，单个 head，A100）：

- $S$ 矩阵大小：$8192^2\times2\text{B}=128\text{ MB}$
- $S$、$P$ 在 HBM 上**来回至少搬 4 遍** → $\approx 512\text{ MB}$ 流量
- A100 HBM 带宽 2.04 TB/s → 光搬运 $\approx 0.25$ ms
- 两个 matmul：$2\times2N^2d=34$ GFLOP，在 312 TFLOPS 下 $\approx 0.11$ ms
- **搬运时间是计算时间的 2.3 倍** → 彻头彻尾的 memory-bound

而 A100 每 SM 的 SRAM 只有 **192 KB**，全卡约 20 MB —— **$S$ 矩阵根本装不进片上**。这就是 FlashAttention 存在的全部理由。

### 二、Online Softmax 完整推导（本题核心，要能在白板上写出来）

#### 2.1 为什么需要全局信息

数值稳定的 softmax 必须减去行最大值，否则 $e^x$ 会溢出（FP32 下 $x>88$ 即 `inf`）：

$$m_i=\max_j S_{ij},\qquad \ell_i=\sum_j e^{S_{ij}-m_i},\qquad O_i=\frac{1}{\ell_i}\sum_j e^{S_{ij}-m_i}V_j$$

**障碍**：$m_i$ 要扫完整行才知道，$\ell_i$ 也要扫完整行。这就是分块的拦路虎。

#### 2.2 核心递推

把一行切成 $T$ 个块 $\mathcal B_1,\dots,\mathcal B_T$。定义处理完前 $t$ 块后的**运行状态**：

$$m^{(t)}=\max_{j\in\mathcal B_1\cup\dots\cup\mathcal B_t}S_{ij},\qquad \ell^{(t)}=\sum_{j\in\mathcal B_1\cup\dots\cup\mathcal B_t}e^{S_{ij}-m^{(t)}},\qquad \tilde O^{(t)}=\sum_{j\in\mathcal B_1\cup\dots\cup\mathcal B_t}e^{S_{ij}-m^{(t)}}V_j$$

来了第 $t$ 块，先算它的局部量 $m^{\text{blk}},\ell^{\text{blk}},\tilde O^{\text{blk}}$，然后：

$$\boxed{\;m^{(t)}=\max\!\big(m^{(t-1)},\,m^{\text{blk}}\big)\;}$$

$$\boxed{\;\ell^{(t)}=\ell^{(t-1)}\cdot\alpha^{(t)}+\ell^{\text{blk}}\cdot\beta^{(t)}\;}$$

$$\boxed{\;\tilde O^{(t)}=\tilde O^{(t-1)}\cdot\alpha^{(t)}+\tilde O^{\text{blk}}\cdot\beta^{(t)}\;}$$

其中两个**修正因子**：

$$\alpha^{(t)}=e^{\,m^{(t-1)}-m^{(t)}},\qquad \beta^{(t)}=e^{\,m^{\text{blk}}-m^{(t)}}$$

最终输出：

$$O_i=\frac{\tilde O^{(T)}}{\ell^{(T)}},\qquad L_i=m^{(T)}+\log\ell^{(T)}\ (\text{logsumexp, 反向要用})$$

#### 2.3 为什么这是**精确**的（必须讲清楚这一步）

所有累积量都是**以当前 running max 为基准**的。当 max 从 $m^{(t-1)}$ 更新到 $m^{(t)}$，之前累积的每一项都少减了 $(m^{(t)}-m^{(t-1)})$，所以整体乘上 $e^{m^{(t-1)}-m^{(t)}}$ 就**精确换到新基准**：

$$\sum_{j\in\text{前 }t-1\text{ 块}}e^{S_{ij}-m^{(t-1)}}\cdot e^{m^{(t-1)}-m^{(t)}}=\sum_{j\in\text{前 }t-1\text{ 块}}e^{S_{ij}-m^{(t)}}\quad\checkmark$$

> [!important] 面试杀手锏（一定要主动说）
> **「注意分子 $\tilde O$ 和分母 $\ell$ 乘的是同一个因子 $\alpha^{(t)}$。最后做除法时这个因子完全约掉——所以哪怕中间 max 一直在变、rescale 了 $T$ 次，最终结果和一次性算全局 softmax 只差浮点舍入误差。这是精确变换，不是近似。」**

**数值安全性**：$\alpha^{(t)},\beta^{(t)}\le 1$（因为 $m^{(t)}$ 是最大值），rescale 永远是**乘一个 $\le1$ 的数**，不会放大溢出。这是 Online Softmax 比「先累加再统一减 max」更稳的根本原因。

#### 2.4 复杂度对比

| | 标准 softmax | Online softmax |
| --- | --- | --- |
| 扫数据遍数 | **3 遍**（求 max → 求 sum → 归一化） | **1 遍**（边扫边更新） |
| 需要预先知道全局 max | 是 | **否** |
| 能否分块流式 | 不能 | **能** ← 这就是 FA 的前提 |

### 三、FlashAttention 前向：Tiling 算法

#### 3.1 块大小的约束

设 SRAM 容量 $M$（Byte），Q 块行数 $B_r$、K/V 块行数 $B_c$：

$$(B_r\cdot d+2B_c\cdot d)\times\text{sizeof(dtype)}+\text{accumulator}(B_r\cdot d\times4\text{B})\;\lesssim\;M$$

A100：$M=192$ KB/SM，$d=128$，BF16 → $B_r=B_c=64$ 或 $128$ 是常见配置。
FA 论文的经验式：$B_c=\lceil M/(4d)\rceil$，$B_r=\min(\lceil M/(4d)\rceil,\,d)$。

#### 3.2 算法（FA2 的循环顺序）

```python
# 外层：Q 块（可并行 → 映射到不同 thread block）
for i in range(0, N, B_r):
    Qi = load_from_HBM(Q[i:i+B_r])            # 只读一次
    Oi = zeros(B_r, d)                        # FP32 accumulator，放寄存器
    mi = -inf; li = 0.0

    # 内层：K/V 块（串行）
    for j in range(0, i + B_r, B_c):          # causal → 只到 i+B_r，上三角整块跳过
        Kj, Vj = load_from_HBM(K[j:j+B_c], V[j:j+B_c])
        S_ij   = Qi @ Kj.T / sqrt(d)          # ← Tensor Core GEMM
        m_blk  = rowmax(S_ij)
        m_new  = maximum(mi, m_blk)
        alpha  = exp(mi - m_new)              # ← 修正因子
        P_blk  = exp(S_ij - m_new)            # ← CUDA core / SFU
        li     = li * alpha + rowsum(P_blk)   # 分母 rescale
        Oi     = Oi * alpha + P_blk @ Vj      # 分子 rescale + GEMM
        mi     = m_new

    Oi = Oi / li                              # FA2 关键：除法推迟到最后一次
    write_to_HBM(Oi, Li = mi + log(li))       # 整个 kernel 只写一次 HBM
```

#### 3.3 HBM 访问量的改善

| | 标准实现 | FlashAttention |
| --- | --- | --- |
| HBM 访问 | $O(Nd+N^2)$ | $O\!\left(\dfrac{N^2d^2}{M}\right)$ |
| $N=8\text{K},d=128,M\approx10^5$ 代入 | $\sim6.7\times10^7$ | $\sim5\times10^6$ |
| 实测减少 | — | **约 9×** |

当 $N\gg M/d^2$ 时（长序列必然满足），FlashAttention 的 HBM 流量**渐近更优**。

#### 3.4 Causal Mask 的免费加速

外层 Q 块、内层 K/V 块 → **完全落在上三角的 K/V 块可以整块跳过**（连 HBM 都不用读）：内层上界是 $i+B_r$ 而不是 $N$。

$$\Rightarrow\text{causal attention 比 non-causal 快近 }2\times$$

### 四、反向传播：Recomputation（用算力换带宽）

反向需要 $P=\text{softmax}(S)$，但它是 $N\times N$，存不下。FA 的做法：

> **只存 $O$（$N\times d$）和 $L$（$N$），反向时按块重算 $S$ 和 $P$。**

| | 标准实现 | FlashAttention |
| --- | --- | --- |
| 反向 HBM 访问 | $O(N^2)$（读回 $P$） | $O(N^2d^2/M)$（重算） |
| FLOPs | 基准 | **增加**（多一次 $QK^\top$） |
| Wall-clock | 慢 | **更快** |

> [!tip] 反直觉但正确
> FLOPs 增加了，wall-clock 反而下降 —— 因为省下的 HBM 时间 > 多花的计算时间。这是**「GPU 上算力比带宽便宜」**这个基本事实的直接体现，也是理解所有现代 kernel 优化的钥匙。同一思想还出现在训练侧的 **gradient checkpointing / 重计算**，见 [[CS336/CS336-L5-GPUs-TPUs|CS336 L5]]。

### 五、FA1 → FA2 → FA3 演进（体现知识更新度）

| | **FA1** (2022) | **FA2** (2023) | **FA3** (2024, Hopper 专属) |
| --- | --- | --- | --- |
| **循环顺序** | 外层 K/V 块、内层 Q 块 → **Q 被反复从 HBM 读** | 外层 Q 块、内层 K/V 块 → **Q 只读一次** | 同 FA2 |
| **并行维度** | 只并行 batch × heads | **额外并行 sequence 维度** → 长序列小 batch 时 SM 占用率大幅提升 | 同 FA2 |
| **Non-matmul FLOPs** | 每步都做 $\div\ell$ 的 rescale | **把 $1/\ell$ 推迟到最后**，中间只乘 $e^{\Delta m}$ → 大幅减少 CUDA core 上的运算（Tensor Core 比 CUDA core 快约 16 倍，要尽量少用后者） | 进一步优化 |
| **Warp 分工** | 按 K/V 列切分 → warp 间需 shared memory 通信 | **按 Q 行切分 → warp 之间零通信** | **Warp Specialization**：producer warpgroup 专职发 TMA 搬数，consumer warpgroup 专职算 |
| **异步能力** | `cp.async`（Ampere） | `cp.async` | **TMA + WGMMA**（warpgroup 级异步 MMA），硬件级异步 |
| **调度** | — | — | **Ping-pong scheduling**：两个 consumer warpgroup 交替，一个跑 GEMM（Tensor Core）时另一个跑 softmax（CUDA core + SFU 算 exp），**两种执行单元同时打满** |
| **低精度** | FP16 / BF16 | FP16 / BF16 | **FP8**：block-wise 量化 + incoherent processing（随机正交变换打散 outlier） |
| **实测性能** | A100 ~124 TFLOPS | **A100 ~225 TFLOPS（≈ 312 峰值的 72%）**；比 FA1 快 ~2×，比 PyTorch 标准实现快 ~9× | **H100 FP16 ~740 TFLOPS（≈ 990 峰值的 75%）**，FP8 达 ~1.2 PFLOPS；比 FA2 快 1.5~2× |

### 六、Decode 阶段的特化：FlashDecoding / FlashMLA（**深度的分水岭**）

> [!important] 主动讲这段，能立刻和「只背过 FA 论文」的候选人拉开距离

FlashAttention 是为 **prefill**（Q 有很多行）设计的。**Decode 时 Q 只有 1 行（或 batch 行）**，直接套 FA 会出大问题：

- 并行度 = batch × heads。batch=8、heads=32 → 只有 **256 个 thread block**
- A100 有 108 个 SM，256 个 block **根本喂不满** → 大量 SM 空转
- 而 KV 长度可能是 80K → 单个 block 要串行扫完整个 KV，**延迟极高**

**FlashDecoding 的解法：在 KV 长度维度上做 split-K 并行**

1. 把长度 $N$ 的 KV 切成 $P$ 个 split（如 $P=8$）
2. 每个 split **独立**算出局部 $\tilde O_p,m_p,\ell_p$ → 并行度从 `batch×heads` 变成 `batch×heads×P`
3. 最后一个 **reduce kernel** 用**和 Online Softmax 完全相同的修正因子**合并 $P$ 份结果：

$$m=\max_p m_p,\qquad \ell=\sum_p \ell_p e^{m_p-m},\qquad O=\frac{\sum_p \tilde O_p\,e^{m_p-m}}{\ell}$$

> [!star] 本题最值钱的一句话
> **Online Softmax 在这里第二次登场** —— 它不只是 FA 内部的技巧，而是**一切「attention 分块 + 合并」的统一代数基础**：chunked prefill 的跨块合并、FlashDecoding 的 split-K 合并、Ring Attention 的跨卡合并、Sequence Parallelism 的 all-gather 合并，用的都是同一套 $(m,\ell,\tilde O)$ 三元组的 rescale 代数。

**FlashMLA**：针对 DeepSeek 系 MLA 架构的 decode kernel。MLA 的 KV Cache 存的是**低秩 latent**（$d_c=512$ 维 + $d_{\text{rope}}=64$ 维，且 K/V 共享一份），decode 时要先做 up-projection 还原 K/V。FlashMLA 把 projection 和 attention 融进一个 kernel，同时吃满显存带宽。

**MLA 省显存的量级**（以 61 层、BF16 为例）：

| KV 方案 | 每 token 显存 | 80K 上下文单条请求 |
| --- | --- | --- |
| GQA（$n_{kv}=8,d_{head}=128$） | $2\times61\times8\times128\times2\text{B}=250\text{ KB}$ | **20 GB** |
| MLA（$d_c+d_{rope}=576$，K/V 共享） | $61\times576\times2\text{B}=70\text{ KB}$ | **5.6 GB** |
| **压缩比** | | **≈ 3.6×** |

→ 这解释了为什么长上下文场景 MLA 是刚需：**一条 80K 请求在 GQA 下就吃掉 20GB，96GB 的卡装完权重只能放两三条。**

### 七、关联 PTG 实战（把话题拉回主场）

> 「FA3 我们踩过坑。SGLang 里给 Kimi-K2.6 / GLM-5.2 / DPSK-V32 设 `--attention-backend fa3` 会直接报 `RuntimeError: q_v is only supported for Hopper GPUs` —— **FA3 内部的 `q_v` 融合路径只对 Hopper 架构做了实现**，我们的 PPU 不在支持列表里。
>
> 解法是**拆开配置**：`--prefill-attention-backend fa3 --decode-attention-backend flashmla`。这个组合其实非常合理——**prefill 是大 GEMM，吃算力，走 FA3；decode 是长 KV 扫描，吃显存带宽，走 FlashMLA，而且 MLA 的 latent KV 本来就更适合 decode**。后来我把这条写进部署 checklist：**新模型上卡第一件事就是确认 attention backend 组合**。」

详见 [[秋招/面经/快手 AI infra面经|快手一面]] Q12 · 问题 1。

### 八、追问预案

| 追问 | 回答要点 |
| --- | --- |
| 为什么减 max 不会溢出，减固定值会？ | 减固定值时 $e^{S_{ij}-c}$ 可能上溢（FP32 下 $>88$ 即 inf）。减 running max 保证指数 $\le0$，即 $e^{(\cdot)}\le1$，**永不上溢**；下溢到 0 无害（该项贡献本来就是 0）。 |
| accumulator 用什么精度？ | **必须 FP32**。$\tilde O$ 在寄存器里用 FP32 累加，否则长序列下多次 rescale 累加会丢精度。标准配置：输入 BF16 → GEMM 走 Tensor Core → **累加 FP32** → 输出写回 BF16。 |
| FA 能处理 GQA / MQA 吗？ | 能，而且**更快**。多个 Q head 共享同一组 K/V head → **K/V 块在 SRAM 里复用率更高**。实现上把共享 KV 的 Q head 打包进同一个 block 的 $B_r$ 维。 |
| FA 和 PagedAttention 什么关系？ | 正交。PagedAttention 解决 **KV Cache 的显存碎片**（分页非连续存储），FA 解决 **attention 计算的 HBM 流量**。生产里两者叠加：paged KV layout + FA varlen kernel。 |
| 为什么 FA3 只支持 Hopper？ | 它重度依赖 Hopper 独有硬件：**TMA**（异步大块搬运）、**WGMMA**（warpgroup 级异步 MMA）、**更大的 shared memory（228 KB/SM）**、以及 warp specialization 需要的硬件异步屏障。Ampere 只有 `cp.async`，做不出这套 producer/consumer 流水。 |
| 有没有不用 CUDA 的实现？ | 有。**Triton 版 FlashAttention** 是理解 tiling 最好的入口（vLLM / SGLang 都内置），约 200 行，`tl.dot` 自动映射到 Tensor Core。性能约为手写 CUDA 的 80~90%，但开发效率高一个量级。 |
| FA 支持 sliding window / 稀疏注意力吗？ | FA2 起支持 block-wise 的 mask 跳过，sliding window 就是把内层循环的 $j$ 范围收窄到窗口内，**跳过的块连 HBM 都不读**，加速比等于稀疏度。 |
| 长上下文外推和 FA 有关系吗？ | 没有。FA 是**精确 attention 的高效实现**，不改变数学结果；长度外推是 RoPE / 位置编码的问题（NTK-aware、YaRN 等）。两者独立。 |

---

# 三、底层软硬栈

## Q4 对算子了解吗

> **答题策略**：这题问得极开放，**千万不要一上来罗列「我知道 matmul、softmax、layernorm」**。正确姿势是先给一个**分类框架**（compute-bound vs memory-bound），再给一个**方法论**（Roofline），然后才是具体优化手段和实战案例。**框架 > 清单**。

### 开口版（40 秒）

> 「我把算子的理解分三层。
>
> **第一层是分类**：所有算子按 Roofline 分成两类——**compute-bound**（GEMM、Conv、Attention 主体）和 **memory-bound**（elementwise、Norm、Softmax、RoPE、量化/反量化、reduce）。分类决定了优化方向完全不同。
>
> **第二层是方法论**：拿到一个慢算子，我不会猜，我会先算它的**算术强度 = FLOPs / Bytes**，和这张卡的 **Roofline 拐点 = 峰值算力 / 峰值带宽**比。低于拐点就是 memory-bound，优化手段是**融合、量化、提高数据复用、向量化访存**；高于拐点是 compute-bound，手段是**降精度、改 tiling、提高 Tensor Core 利用率、减少 non-matmul FLOPs**。
>
> **第三层是实现**：从下到上是**手写 CUDA C++ → CUTLASS/模板库 → Triton（block-level DSL）→ 框架自动融合（torch.compile / Inductor、XLA、TensorRT）**。我自己的位置是：**能读懂 FA / CUTLASS 级别的 kernel，能用 Triton 写和调生产算子，能用 Nsight Systems + Nsight Compute 定位瓶颈，但没有从零手写高性能 CUDA kernel 的经验**。在 PTG 我们用的是 PPU 自研算子库，我更多做的是**选型、组合、适配和精度对齐**。」

### 一、算子分类：一张表定住全场

| 类别 | 代表算子 | 算术强度 | 瓶颈 | 优化方向 |
| --- | --- | --- | --- | --- |
| **大 GEMM** | QKV/O projection、FFN gate/up/down | 高（$\sim M$，prefill 时几百） | **Compute** | 低精度（FP8/INT8）、更好的 tiling、Tensor Core 利用率、避免 wave quantization |
| **Attention** | FA prefill / FlashMLA decode | 中高（prefill）/ 低（decode） | prefill→compute，decode→**memory** | Tiling + Online Softmax（见 [[#Q3 FlashAttention 的原理，Online Softmax 怎么推\|Q3]]） |
| **GEMV**（decode 的 GEMM） | batch=1 的所有 linear | **≈ 1** | **极度 memory** | **量化**（直接减少搬运字节）、大 batch |
| **Norm** | LayerNorm / RMSNorm | 极低（每元素 2 Byte 进、2 Byte 出，算不了几个 FLOP） | **Memory** | 与 residual add 融合、向量化 load |
| **Softmax** | attention softmax、MoE router | 低 | **Memory**（读一遍写一遍） | 融进 attention（FA 的核心）、online 化避免多遍扫描 |
| **Elementwise** | GELU/SiLU、residual add、mul | 极低 | **Memory** | **全部融合**，理想情况下不单独存在 |
| **位置编码** | RoPE | 极低 | **Memory** | 融进 QKV projection 的 epilogue 或 KV cache write |
| **量化/反量化** | quantize、dequantize | 低 | **Memory** | **融进 GEMM 的 main loop**（Marlin / Machete 风格），绝不「先 dequant 成 FP16 写回 HBM 再算」 |
| **Reduce / Scan** | sum、max、cumsum、top-k | 低 | **Memory + 并行度** | 树形归约、warp shuffle（`__shfl_down_sync`）避免走 shared memory |
| **通信算子** | AllReduce、AllGather、All-to-All | — | **网络带宽** | 与计算 overlap、通信-计算融合（TransformerEngine userbuffers / Flux）、拓扑感知 |
| **MoE 特有** | router top-k、permute/unpermute、grouped GEMM | 混合 | 小 batch 下 **All-to-All 通信** | grouped GEMM（把变长 expert batch 拼成一个 batched GEMM）、fused dispatch |

### 二、Roofline：判断优化方向的唯一工具

**算术强度**（Arithmetic Intensity）：

$$\text{AI}=\frac{\text{FLOPs}}{\text{Bytes moved to/from HBM}}\quad[\text{FLOP/Byte}]$$

**Roofline 拐点**（Ridge Point）：

$$\text{AI}_{\text{ridge}}=\frac{\text{峰值算力}}{\text{峰值带宽}}$$

$$\text{可达性能}=\min\big(\text{峰值算力},\;\text{AI}\times\text{峰值带宽}\big)$$

**各卡拐点**（这张表要能背，它同时回答了 Q6）：

| 卡 | BF16 dense 峰值 | HBM 带宽 | **拐点 AI** | 含义 |
| --- | --- | --- | --- | --- |
| **A100 80GB SXM** | 312 TFLOPS | 2.04 TB/s | **153** | 经典平衡点 |
| **H100 SXM5** | 989 TFLOPS | 3.35 TB/s | **295** | 算力涨得比带宽快 → **更容易 memory-bound** |
| **H20** | 148 TFLOPS | 4.0 TB/s | **37** | 算力被砍、带宽保留 → **反而容易 compute-bound** |
| **B200** | ~2250 TFLOPS | 8 TB/s | **~281** | 与 H100 同量级 |
| **PPU 810E** | 低（算力弱） | 96GB HBM，带宽尚可 | **低** | 定位类似 H20：**显存大、算力低** |

#### 杀手级应用：为什么 decode 必须量化

Decode 阶段 batch $=B$ 的 GEMM，权重 $W\in\mathbb R^{K\times N}$：

$$\text{FLOPs}=2BKN,\qquad \text{Bytes}\approx KN\times\text{sizeof}(W)$$

$$\Rightarrow \text{AI}=\frac{2BKN}{KN\cdot\text{sizeof}(W)}=\frac{2B}{\text{sizeof}(W)}$$

BF16（2 Byte）下 $\text{AI}=B$。所以：

> [!important] 一个极其干净的结论
> **decode 的算术强度 ≈ batch size**（BF16 权重下）。
> - A100（拐点 153）→ batch < 153 时 decode 严格 memory-bound
> - H100（拐点 295）→ batch < 295 时 memory-bound
> - H20（拐点 37）→ batch > 37 就已经 compute-bound 了
>
> **推论 1**：memory-bound 时，$\text{step time}\approx\dfrac{\text{权重字节数}}{\text{HBM 带宽}}$，与 batch 几乎无关 → **加大 batch 是免费的吞吐**，直到撞上拐点。
>
> **推论 2**：**量化的收益直接等于位宽比**。FP16 → INT4 把权重字节数砍到 1/4，decode 吞吐理论上限直接 ×4。

**验算一个具体例子**（Llama-7B，单张 A100 80GB，batch=1）：

| 精度 | 权重大小 | 理论 decode 上限 $=\dfrac{2.04\text{ TB/s}}{\text{权重大小}}$ | TPOT |
| --- | --- | --- | --- |
| BF16 | 14 GB | **146 token/s** | 6.9 ms |
| INT8 | 7 GB | **291 token/s** | 3.4 ms |
| INT4 | 3.5 GB | **583 token/s** | 1.7 ms |

→ 这就是**为什么 W4A8 / W8A8 在 decode 侧是刚需，而在 prefill 侧收益小得多**（prefill 是 compute-bound，量化省的是算力，但 INT4 dequant 的额外开销会吃掉一部分收益）。

### 三、六大优化手段（按性价比排序）

**① 算子融合（Operator Fusion）—— 性价比最高**

融合省两样东西：**kernel launch 开销** + **HBM 往返**。典型融合：

| 融合 | 效果 |
| --- | --- |
| QKV projection：3 个 GEMM → 1 个（权重 concat） | 减少 launch，提高 $N$ 维利用率 |
| RMSNorm + residual add | 省一次 HBM 往返 |
| RoPE + KV Cache write（+ quantize） | 三个 memory-bound 算子合成一个 |
| **FlashAttention 本身** | softmax + 2 个 matmul 的融合，省掉 $N\times N$ 的 HBM 物化 |
| MoE：top-k + permute + grouped GEMM + unpermute | 减少中间张量落地 |
| **dequant 融进 GEMM main loop**（Marlin / Machete） | 关键：否则 INT4 权重要先解成 FP16 写回 HBM，白搬一遍 |
| AllReduce + residual + RMSNorm（通信-计算融合） | TransformerEngine userbuffers / Flux，把通信藏进计算 |

> **融合的边界怎么定？** 判据是**「能不能把中间结果留在寄存器 / shared memory 里」**。如果两个算子的中间张量必须落 HBM，融合就没意义。我在 OPPO 踩过这个坑：**算子拆解的融合边界选错会导致数值不一致**——因为融合后中间结果的精度和累加顺序变了（比如 fused kernel 内部用 FP32 累加，拆开版用 FP16 落地），最后要对齐到 bit-level 才能过精度验收。

**② 降低精度（Low Precision）**
BF16 → FP8 → FP4/INT4。收益有两份：**算力翻倍**（Tensor Core 每降一档吞吐 ×2）+ **带宽减半**。代价是 outlier 问题 → 需要 per-group scale、block-wise 量化、incoherent processing。粒度选择见 [[秋招/面经/商汤 大模型系统工程师面经|商汤面经]] Q11（权重 per-group=128，激活 per-token dynamic）。

**③ Tiling + 提高数据复用**
把大计算切成能装进 SRAM 的块，让每份数据被复用多次 → 提高 AI → 沿 Roofline 往右移。FA 是极致例子，GEMM 的 $128\times128\times32$ tile 是标准例子。

**④ Memory Coalescing + 向量化访存**
warp 内 32 线程访问连续 128 Byte → 1 次 memory transaction。用 `float4` / `int4`（128-bit）指令一条搬 4 个元素。**非合并访问的带宽损失可以到 32×**。详见 [[#Q5 对 CUDA 了解吗|Q5]]。

**⑤ CUDA Graph —— 消除 launch 开销**
decode 一步的 kernel 数量级：$L$ 层 × 每层约 12~15 个 kernel。以 61 层模型为例 ≈ **800 个 kernel / step**，每个 launch 的 CPU 开销 ~3~8 μs → 累计 **2.4~6.4 ms**。

- 若 TPOT = 50ms → 占 **5~13%**
- 若 TPOT = 10ms（小模型快 decode）→ 占 **24~64%** ← **CUDA Graph 收益巨大**

代价：graph capture 要求 **shape 固定** → 必须按 batch size 分桶（bucketing），每桶录一份图，运行时 padding 到最近的桶，显存占用增加。

> **一个「没效果」的结论比「有效果」更有价值**：我在 PTG 试过 24 个密集桶 `--cuda-graph-bs 1 2 3 ... 64`，**压测基本没变化**。归因是**当前瓶颈不在 kernel launch，而是被通信 / KV 传输 / 调度占住了**，而且 `dp-size=16` 下每卡 batch 本来就小。这个实验的价值是**把 CUDA Graph 从优化候选里排除了**，避免团队继续投入。

**⑥ Persistent Kernel / Megakernel**
让一个 kernel 常驻 SM，内部循环取任务，彻底消除 launch 和 prologue/epilogue 开销。代价是编程复杂度和 occupancy 控制。DeepSeek / 各家 inference engine 都在往这个方向走。

### 四、实现层次：从库到手写

```
 高抽象  ┌────────────────────────────────────────────┐
   ↑    │ 框架自动融合：torch.compile / Inductor、XLA、TensorRT │  ← 一键，但黑盒、可控性差
        ├────────────────────────────────────────────┤
        │ DSL：Triton（block-level）、TVM/Ansor、Halide        │  ← 效率/性能的最佳平衡点
        ├────────────────────────────────────────────┤
        │ 模板库：CUTLASS、cuBLAS、cuDNN、FlashInfer           │  ← 工业级 GEMM/Conv
        ├────────────────────────────────────────────┤
        │ 手写：CUDA C++ + PTX + inline asm                   │  ← 极致场景（FA3、warp specialization）
 低抽象  └────────────────────────────────────────────┘
```

**Triton vs 手写 CUDA**（商汤 Q10 也被问过，答案要一致）：

| | Triton | 手写 CUDA |
| --- | --- | --- |
| 编程粒度 | **block（tile）级**：你写「这个 program 处理一块 $128\times64$」 | **thread 级**：你写「这个 thread 处理哪个元素」 |
| 自动处理 | shared memory 分配、coalescing、`cp.async` 流水、bank conflict 规避 | **全部手动** |
| 开发效率 | 高 **5~10×** | 低 |
| 性能 | 手写 CUDA 的 **80~95%** | 100%（上限） |
| 能做 warp specialization / TMA / WGMMA 吗 | 较新版本部分支持，仍不如手写灵活 | **能** |
| 适用场景 | 90% 的自定义算子、快速原型、研究 | FA3、极致 GEMM、新硬件 bring-up |

**我的真实定位**（诚实版，和 [[秋招/面经/商汤 大模型系统工程师面经|商汤面经]] Q10 保持一致）：
- **Triton**：熟悉 `tl.load/store`、grid/block 映射、`triton.autotune`；在 Mini-vLLM 项目里参考过 Triton 版 FlashAttention 理解 tiling 策略
- **TensorRT**：OPPO 实习时间接接触（端侧部署最终走 TensorRT / 自研框架），我负责量化部分要保证 scale / zero-point 格式与后端 engine 兼容
- **手写 CUDA**：**没有从零写过生产级高性能 kernel**，但能读懂 FA / CUTLASS 的关键路径

> PPU 的情况：平头哥有自研算子库（核心算子 GEMM / FlashAttention / RMSNorm / RoPE 用自研编译器 + 低级 IR 写，不走 Triton），但**编程模型在设计上参考了 Triton 的 tile-based 范式**，有类似的 block-level parallelism 抽象；非关键路径算子支持 Python fallback 或 Triton-like DSL 快速原型。

### 五、定位一个慢算子的标准工作流（**这段最能证明你真做过**）

```
① Nsight Systems (nsys)  →  看 timeline
   ├─ 有没有大段 GPU idle？→ launch bound / CPU bound / 通信等待
   ├─ Top kernel 按总耗时排序 → 找到值得优化的那一个
   └─ kernel 之间有没有 gap？→ 考虑 CUDA Graph / 融合

② 手算 Roofline  →  定性
   ├─ FLOPs（从 shape 算）/ Bytes（从 dtype 和访存模式算）
   └─ 和这张卡的拐点对比 → memory-bound 还是 compute-bound

③ Nsight Compute (ncu)  →  定量看单 kernel
   ├─ Achieved Occupancy        → warp 够不够多
   ├─ SM Busy / Issue Slots     → 发射效率
   ├─ DRAM Throughput           → 是否打满带宽（memory-bound 的黄金指标）
   ├─ Tensor Core Utilization   → 是否打满算力
   ├─ Warp Stall Reasons        → 卡在 long_scoreboard（等 HBM）还是 barrier（等同步）
   └─ L1/L2 Hit Rate            → 数据复用够不够

④ 按 ② 的结论选手段
   ├─ memory-bound → 融合、量化、向量化 load、提高复用、coalescing
   ├─ compute-bound → 降精度、改 tiling、减少 non-matmul FLOPs、提高 TC 利用率
   └─ launch-bound → CUDA Graph、融合、persistent kernel
```

> **一句方法论金句**：**「先测量，再优化。Roofline 告诉你该往哪个方向使劲，Nsight 告诉你离屋顶还差多远。凭直觉优化 kernel 基本都会失败——我自己的经验是，我猜的瓶颈和 ncu 报出来的瓶颈，一半以上不一致。」**

### 六、追问预案

| 追问 | 回答要点 |
| --- | --- |
| 举一个你亲手做过的算子优化 | 用 OPPO 的例子：INT4 精度崩 → 定位到 **outlier 主导 per-tensor scale** → 改 per-group（group=64）+ 对 QKV projection 这类敏感层单独处理 → 精度恢复。同时开发了 Inference Tool 做逐层误差累积定位。 |
| 算子融合的边界怎么定？会不会融错了？ | 判据：**中间结果能不能留在寄存器/SRAM**。融错的典型后果是**数值不一致**（累加顺序和中间精度变了）——我在 OPPO 就撞过，最后靠对齐到 bit-level 才过验收。 |
| 为什么 Tensor Core 比 CUDA Core 快这么多？ | Tensor Core 一条指令做一个小矩阵乘加（如 $m16n8k16$），**FLOPs/instruction 高一个数量级**；CUDA Core 一条指令一个 FMA。所以 FA2 特意把 non-matmul 的运算（rescale、exp）压到最少。 |
| 什么是 grouped GEMM？为什么 MoE 需要它？ | MoE 里每个 expert 分到的 token 数**不等长**，直接循环调 GEMM 会有几百个小 kernel。grouped GEMM 把变长的多个 GEMM **打包成一次 launch**，用一个 kernel 处理所有 expert → launch 开销和 SM 空转都大幅下降。 |
| 量化算子里 dequant 放在哪最省？ | **放在 GEMM 的 main loop 里**，从 HBM 读进 INT4 → 在 shared memory / 寄存器里 dequant 成 FP16/INT8 → 立刻喂给 Tensor Core。**绝对不能 dequant 完写回 HBM 再算**，那样等于白搬一遍，量化的带宽收益全没了。Marlin / Machete 就是专门做这件事的。 |
| 你怎么看 torch.compile？ | 它（TorchInductor）在**elementwise / norm 这类 memory-bound 算子的自动融合**上很好用，能白捡 10~30%。但**核心 GEMM 和 attention 它做不出 FA / CUTLASS 的水平**，生产里通常是「torch.compile 管长尾小算子 + 手工 kernel 管关键路径」。 |
| 通信算子怎么优化？ | ① 与计算 **overlap**（NCCL 放独立 stream + event 同步）；② **通信-计算融合**（TransformerEngine userbuffers、Flux：把 AllReduce 拆成 reduce-scatter + 分块计算 + all-gather，边算边传）；③ **拓扑感知**（机内 NVLink 走 TP，跨机 IB 走 PP/EP/DP）。 |

---

## Q5 对 CUDA 了解吗

> **答题策略**：这题最危险，因为「了解」的下界可以很低、上界可以无限深。**先给一个 5 分钟能讲完的完整框架，然后主动交代边界并抛出实战锚点**，把面试官引导到你有话说的地方（PTG 的踩坑、Triton、Nsight），而不是让他自由下钻到你不会的角落。

### 开口版（40 秒）

> 「我对 CUDA 的了解分四块：
>
> **编程模型**：Grid → Block → Warp（32 线程）→ Thread 的层次，以及它到硬件 SM / warp scheduler 的映射。核心是 **SIMT** 执行——同一个 warp 里的 32 个线程锁步执行同一条指令，所以分支发散（divergence）会退化成串行。
>
> **内存层次**：Register → Shared Memory / L1 → L2 → HBM（Global）→ Host，每一层的容量、带宽、延迟差 1~2 个数量级。**所有 CUDA 优化的本质都是把数据往近处搬、并让搬运合并（coalesced）。**
>
> **性能模型**：GPU 靠 **warp 切换来隐藏延迟**（不是靠 cache），所以 occupancy 和 ILP 要平衡；小心中断性能的四个经典陷阱——**分支发散、非合并访存、bank conflict、寄存器溢出**。
>
> **并发与工程**：stream / event、异步拷贝（`cp.async`、Hopper 的 TMA）、NCCL 与计算的 overlap、CUDA Graph。
>
> **我的真实定位**：我是 CUDA 的**深度使用者和调优者**，不是 kernel 作者——能读懂 FlashAttention / CUTLASS 的关键路径，用 **Triton** 写生产算子，用 **Nsight Systems + Nsight Compute** 定位瓶颈，在 PPU 上做过 attention backend 适配和量化算子对接。从零手写 warp-specialized 的高性能 CUDA kernel 我没有做过。」

### 一、编程模型：软件概念 ↔ 硬件实体

| 软件概念 | 硬件实体 | 说明 |
| --- | --- | --- |
| **Grid** | 整个 GPU | 一次 kernel launch = 一个 grid |
| **Block（CTA）** | 一个 **SM**（不迁移） | block 内线程可通过 shared memory 通信 + `__syncthreads()` 同步 |
| **Warp**（32 线程） | **warp scheduler** 的调度单位 | **真正的执行粒度**。CUDA 里你写 thread，硬件跑 warp |
| **Thread** | CUDA core / lane | 有自己的寄存器和 program counter |
| **Warpgroup**（4 warp = 128 线程） | Hopper 新增 | **WGMMA** 的粒度，FA3 的 warp specialization 就建在这上面 |

**A100 / H100 关键数字**（要能报）：

| | A100 SXM | H100 SXM5 |
| --- | --- | --- |
| SM 数 | 108 | 132 |
| 每 SM 最大线程 | 2048（= 64 warp） | 2048 |
| 每 SM 寄存器 | 65536 × 32-bit = **256 KB** | 256 KB |
| 每 SM Shared Mem | 最大 **192 KB**（可配置 L1 比例） | 最大 **228 KB** |
| L2 Cache | **40 MB** | **50 MB** |
| warp scheduler / SM | 4 | 4 |

### 二、内存层次（**这是一面 Q3 已经问过的，二面要更深**）

| 层级 | 作用域 | 容量 | 带宽 | 延迟 |
| --- | --- | --- | --- | --- |
| **Register** | per-thread | 256 KB/SM | 最高 | ~1 cycle |
| **Shared Memory / L1** | per-block | 192 KB/SM (A100) | ~19 TB/s（全卡聚合） | ~20~30 cycle |
| **L2 Cache** | 全卡 | 40~50 MB | ~5~7 TB/s | ~200 cycle |
| **HBM (Global)** | 全卡 | 80~96 GB | **2.04~4.0 TB/s** | **~400~800 cycle** |
| **Host (CPU DRAM)** | 跨 PCIe | 几百 GB~TB | PCIe Gen5 ~64 GB/s | 微秒级 |
| **远端节点** | 跨网络 | TB | IB NDR 50 GB/s | 毫秒级 |

**几个特殊内存**：
- **Constant Memory**：只读、有专用 cache，**warp 内所有线程读同一地址时广播，效率极高**；读不同地址会串行化。适合放 scale / bias / 配置参数。
- **Local Memory**：**名字骗人——物理上在 HBM**。寄存器不够时溢出（spill）到这里，**性能断崖**。用 `nvcc -Xptxas -v` 看 `bytes spill stores/loads`。
- **Pinned (Page-Locked) Host Memory**：`cudaMallocHost`。**只有 pinned memory 上的 `cudaMemcpyAsync` 才是真异步**；pageable memory 会退化成同步拷贝。这是 H2D 传输最常见的坑。

### 三、Occupancy 与延迟隐藏（能手算，这一段最有说服力）

**定义**：

$$\text{Occupancy}=\frac{\text{每 SM 上活跃的 warp 数}}{\text{每 SM 支持的最大 warp 数（64）}}$$

**手算一个例子**（A100，kernel 配置：256 threads/block、每 thread 64 个寄存器、每 block 32 KB shared memory）：

| 限制因素 | 计算 | 允许 block 数 |
| --- | --- | --- |
| 寄存器 | $65536 \div (256\times64) = 4$ | **4** |
| Shared Memory | $192\text{ KB}\div 32\text{ KB}=6$ | 6 |
| 线程数 | $2048\div256=8$ | 8 |
| **取最小值** | | **4 blocks/SM** |

$$\text{Occupancy}=\frac{4\times256}{2048}=\frac{1024}{2048}=\mathbf{50\%}$$

**为什么 occupancy 重要 —— 延迟隐藏**：
HBM 延迟 ~600 cycle。一个 warp scheduler 每 cycle 发射 1 条指令，如果只有 1 个 warp，它等 HBM 的 600 cycle 里 SM 完全空转。有 $W$ 个 active warp 时可以互相切换 → **GPU 用「线程级并行」代替「cache」来隐藏延迟**。

> [!important] 但 occupancy 不是越高越好（这个反驳很加分）
> 经验上 **50~60% 就足以隐藏 HBM 延迟**了。再往上提，就得牺牲**每线程寄存器数**，导致：① 寄存器溢出到 local memory（实际在 HBM，灾难）；② ILP（指令级并行）下降，每个线程能独立推进的工作变少。
>
> **Volkov 的经典结论：低 occupancy + 高 ILP 可以打败高 occupancy + 低 ILP。** 所以调优时我会同时看 occupancy 和 `ncu` 里的 warp stall reasons——如果 stall 主要是 `long_scoreboard`（等 HBM），说明需要更多 warp 或更好的数据复用；如果是 `barrier`（等 `__syncthreads`），说明 block 内负载不均。

### 四、五个必知的性能陷阱

**① Warp Divergence（分支发散）**
同一 warp 的 32 个线程走不同分支 → 硬件**串行执行两个分支**（用 active mask 屏蔽），最坏情况性能 ÷32。
- 避免：把分支条件设计成 **warp 对齐**（`if (threadIdx.x / 32 == k)`），或者按 block 分工
- Attention 里 causal mask 的处理就是典型：FA 把「完全在对角线以下的块」（无需 mask）和「跨越对角线的块」（需要 mask）**分成两条路径**，让每个 warp 内部无发散

**② 非合并访存（Uncoalesced Access）**
warp 内 32 线程访问**连续**的 128 Byte → 1 次 transaction（4 个 32B sector）。
若访问 stride 为 32 的元素 → **32 次 transaction，带宽利用率 1/32**。
- 典型场景：按列访问一个 row-major 矩阵
- 修复：转置（走 shared memory 中转）、改数据布局（AoS → SoA）、padding

**③ Shared Memory Bank Conflict**
Shared memory 分 **32 个 bank，每 bank 4 Byte 宽**，连续的 4-byte word 轮流映射到 32 个 bank。一个 warp 内多个线程访问**同一 bank 的不同地址** → 串行化。
- 经典案例：**32×32 float 矩阵转置**，按列读会 **32-way conflict**
- 修复：**padding 成 32×33**（错开 bank），或改用 swizzle 布局（CUTLASS / FA 里的标准做法）
- 特例：多个线程读**同一地址**是**广播**，不算 conflict

**④ 寄存器溢出（Register Spilling）**
每线程超过 255 个寄存器 → 溢出到 **local memory（物理在 HBM）** → 延迟从 1 cycle 变成 600 cycle。
- 检测：`nvcc -Xptxas -v` 看 `Used N registers, M bytes spill stores, K bytes spill loads`
- 修复：减小 block size、`__launch_bounds__` 提示编译器、手动分块降低同时活跃的数据量

**⑤ Wave Quantization（尾效应）**
若 grid 有 1000 个 block，108 SM × 4 block/SM = 一波 432 个 → 需要 3 波（可容 1296），**第三波只有 136 个 block，大量 SM 空转** → 有效利用率 $1000/1296=77\%$。
- 修复：调 block size / tile size 让 block 总数接近「波容量」的整数倍
- 这在 GEMM 里非常明显，CUTLASS 的 tile 选择 autotune 有一半是在解决这个问题

### 五、并发：Stream / Event / 通信重叠

| 概念 | 要点 |
| --- | --- |
| **Stream** | 同 stream 内**严格串行**；不同 stream **可并发**（前提是 SM 资源够） |
| **Default Stream** | legacy 默认流会**隐式同步所有其他流** → 生产代码要用显式 stream 或 per-thread default stream |
| **Event** | 跨 stream 的轻量同步点：`cudaEventRecord` + `cudaStreamWaitEvent`。**不用 `cudaDeviceSynchronize`**（那是全局栅栏，最贵） |
| **异步拷贝** | `cudaMemcpyAsync` **必须配 pinned memory** 才真异步；Ampere 起有 `cp.async`（global → shared 直接异步，绕过寄存器）；Hopper 有 **TMA**（硬件 DMA 引擎，描述符驱动，FA3 的基础） |
| **Double / Multi-buffering** | 用 `cp.async` 预取下一块数据到 buffer B，同时计算 buffer A → **搬运和计算完全重叠**。这是所有高性能 GEMM / Attention kernel 的骨架 |
| **NCCL overlap** | AllReduce 放独立 stream，用 event 和 compute stream 同步 → **TP 场景下能把通信藏掉 10~20%**。更进一步是通信-计算融合（Flux / userbuffers） |

### 六、工具链

| 工具 | 用途 | 关键输出 |
| --- | --- | --- |
| `nvcc -Xptxas -v` | 编译期静态分析 | 寄存器数、shared memory 用量、**spill 字节数** |
| `nvcc -lineinfo` + `compute-sanitizer` | 内存越界 / race 检测 | 类似 valgrind |
| **Nsight Systems (`nsys`)** | **系统级 timeline** | GPU idle、kernel 排序、CPU-GPU 交互、NCCL 时间线、launch 开销 |
| **Nsight Compute (`ncu`)** | **单 kernel 微观分析** | achieved occupancy、DRAM throughput、SM busy、**warp stall reasons**、roofline 图、L1/L2 命中率 |
| `nvidia-smi` / `dcgmi` | 运行时监控 | 利用率、显存、功耗、温度、ECC 错误、NVLink 带宽 |
| PyTorch Profiler | 框架级 | 算子耗时、CPU/GPU 时间分解，底层就是 CUPTI |

> **标准工作流**：`nsys` 找哪个 kernel 值得优化 → 手算 Roofline 定方向 → `ncu` 定量看离屋顶多远 → 改 → 再测。**顺序不能反**，直接上 `ncu` 会在错误的 kernel 上浪费一天。

### 七、关联 PTG 实战

| 场景 | 涉及的 CUDA 知识 |
| --- | --- |
| **FA3 在 PPU 上报 `q_v is only supported for Hopper GPUs`** | FA3 依赖 Hopper 独有的 **TMA + WGMMA + warp specialization**，PPU 没有这些硬件原语 → 拆成 `--prefill-attention-backend fa3 --decode-attention-backend flashmla`。见 [[秋招/面经/快手 AI infra面经\|快手一面]] Q12 |
| **CUDA Graph 密集桶实验（24 个桶，无效果）** | 证明**瓶颈不在 launch overhead**，而在通信 / KV 传输 / 调度。**「没效果」的结论排除了一个优化方向，价值等于「有效果」** |
| **W4A8 + EP 报 `assert m == m_ and n == n_ and k == k_`** | 量化 GEMM kernel 与 DeepEP 的 **shape 约定不兼容** → w4a8 不开 EP，需要 EP 的场景改 `w8a8_int8` → 整理成「量化方式 × 并行策略」兼容矩阵 |
| **`tp=8, dp=2` 的 TTFT 反而变差的反直觉实验** | 涉及 **NCCL 通信组划分、SM 资源争抢、NVLink 带宽竞争**——并行度提高不等于延迟降低，通信量才是决定因素 |
| **PPU 自研栈的算子适配** | PPU 编程模型参考 Triton 的 tile-based 范式，有 block-level parallelism 抽象，但底层 IR 和调度器是自研的 → 我的工作是**对齐语义 + 精度验证**，不是重写 kernel |

### 八、追问预案

| 追问 | 回答要点 |
| --- | --- |
| `__syncthreads()` 和 `__syncwarp()` 区别？ | `__syncthreads()` 是 **block 级栅栏**，所有线程到达才继续，代价高（走 barrier 硬件）；`__syncwarp()` 只同步 warp 内 32 线程，通常编译成一条指令，几乎免费。**能用 warp shuffle 解决的就不要用 shared memory + `__syncthreads()`**。 |
| Warp shuffle 是什么？ | `__shfl_down_sync` 等指令让 **warp 内线程直接交换寄存器值，不经过 shared memory**。warp 级归约（32 → 1）只需 5 次 shuffle，比 shared memory 版本快得多且无 bank conflict。 |
| `cp.async` 解决了什么问题？ | Ampere 之前，global → shared 必须**先加载到寄存器再存进 shared memory**，占用寄存器且阻塞流水线。`cp.async` 让数据**直接 global → shared**，绕过寄存器，且不阻塞 → 才能实现真正的多阶段（multi-stage）软件流水。Hopper 的 **TMA** 更进一步：由独立 DMA 引擎按张量描述符搬运，一个线程就能发起大块异步传输。 |
| Tensor Core 怎么调用？ | 三个层次：① **WMMA API**（`nvcuda::wmma`，最简单，粒度粗）；② **`mma.sync` PTX 指令**（如 `m16n8k16`，CUTLASS 用这个）；③ **Hopper 的 `wgmma.mma_async`**（warpgroup 级、异步，FA3 用这个）。Triton 里 `tl.dot` 会自动 lower 到对应指令。 |
| 什么是 grid-stride loop？为什么常用？ | `for (i = blockIdx.x*blockDim.x + threadIdx.x; i < N; i += gridDim.x*blockDim.x)`。**一份 kernel 代码适配任意 N**，且 grid 大小可以固定成「刚好填满 SM」→ 避免 wave quantization，也是 persistent kernel 的基础写法。 |
| 为什么 block size 通常取 128 / 256？ | ① 必须是 32 的倍数（warp）；② 太小 → block 数太多，调度开销和 shared memory 复用率低；③ 太大 → 每 SM 能装的 block 数太少（往往只剩 1~2 个），**一旦 block 内有 barrier 就没有其他 block 可以切换，延迟隐藏能力骤降**。128/256 是经验甜点。 |
| FP8 在 CUDA 里怎么用？ | Hopper 起有原生 `__nv_fp8_e4m3` / `e5m2` 类型和对应的 Tensor Core 指令。**e4m3**（4 位指数 3 位尾数）动态范围小、精度好，用于前向；**e5m2** 范围大、精度差，用于梯度。需要配 per-tensor 或 block-wise scale，以及 TransformerEngine 的 delayed scaling。 |
| 你怎么 debug 一个结果不对的 kernel？ | ① `compute-sanitizer` 查越界 / race；② 缩小到最小复现（单 block、单 warp）；③ `printf` 在 device 端打印（有限但好用）；④ 和 PyTorch 参考实现比 **逐层 max abs diff / cosine sim**；⑤ 特别注意**累加顺序和中间精度**——我在 OPPO 就是因为融合边界改变了 FP32 累加顺序导致数值不一致。 |

---

## Q6 对 NVIDIA 的卡了解吗

> **答题策略**：不要背参数表。**给一个「怎么读一张卡」的框架**（四个维度 + 拐点），然后落到**选型判断**和**与 PPU 的对比**——后者是你的主场，一定要主动切过去。

### 开口版（40 秒）

> 「我看一张卡主要看**四个维度**，而且这四个维度**直接决定推理系统的架构选择**：
>
> **① 显存容量** → 决定**能不能装下模型 + 多少 KV Cache**，也就是并发上限和上下文长度上限。
> **② 显存带宽** → 决定 **decode 吞吐的天花板**（decode 是 memory-bound，$\text{step time}\approx$ 权重字节 / 带宽）。
> **③ 算力（要区分 dense 和 sparse）** → 决定 **prefill 速度和 TTFT**。
> **④ 互联带宽（NVLink / IB）** → 决定 **TP 能开多大、EP 能不能跨机**。
>
> 而把这四个维度串起来的是一个数：**Roofline 拐点 = 峰值算力 / 峰值带宽**。这个数**逐代在涨**（A100 是 153，H100 是 295），意味着**越来越多的算子变成 memory-bound**——这就是为什么这几年所有推理优化都在往「省带宽」的方向走：量化、MLA、GQA、PagedAttention、大 batch。
>
> 我在 PTG 用的是**平头哥 PPU 真武 810E**，单卡 96GB HBM，**显存大、算力低**，定位上最接近 **H20**（96GB、4.0 TB/s、但 BF16 只有 148 TFLOPS，拐点仅 37）。**所以我们的整套优化策略必须反过来做：不是省带宽，而是省算力、榨带宽**——这就是为什么我们选了 W4A8 量化、PD 分离、大 batch decode 这条路线。」

### 一、数据中心 GPU 谱系（要能画出这条时间线）

| 卡 | 架构 | 年份 | 显存 | HBM 带宽 | BF16 dense | FP8 dense | NVLink | TDP | **拐点 AI** |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **A100 80GB SXM** | Ampere | 2020 | 80GB HBM2e | 2.04 TB/s | 312 TFLOPS | ✗ | 600 GB/s (L3) | 400W | **153** |
| **H100 SXM5** | Hopper | 2022 | 80GB HBM3 | 3.35 TB/s | 989 TFLOPS | 1979 TFLOPS | 900 GB/s (L4) | 700W | **295** |
| **H800 SXM** | Hopper | 2023 | 80GB HBM3 | 3.35 TB/s | 989 TFLOPS | 1979 TFLOPS | **400 GB/s（阉割）** | 700W | 295 |
| **H20** | Hopper | 2024 | **96GB HBM3** | **4.0 TB/s** | **148 TFLOPS（重砍）** | 296 TFLOPS | 900 GB/s | 400W | **37** |
| **L40S** | Ada Lovelace | 2023 | 48GB GDDR6 | 864 GB/s | 362 TFLOPS | 733 TFLOPS | ✗（仅 PCIe） | 350W | 419 |
| **B200** | Blackwell | 2024 | **192GB HBM3e** | **8 TB/s** | ~2250 TFLOPS | ~4500 TFLOPS | **1.8 TB/s (L5)** | 1000W | ~281 |
| **B300 / GB300** | Blackwell Ultra | 2025 | **288GB HBM3e** | ~8 TB/s | 更高 | 更高 | 1.8 TB/s | 1400W | — |

> [!warning] 报数前必读的两个口径陷阱
> **① dense vs sparse**：NVIDIA 官方 spec sheet 常标 **2:4 结构化稀疏**下的算力，**正好是 dense 的 2 倍**。生产上绝大多数模型不满足 2:4 稀疏，**报数必须用 dense**。H100 的「1979 TFLOPS FP8」是 dense，「3958」是 sparse。
> **② B 系列的数字各家来源不一致**（B200 的 FP4/FP8 dense 口径在不同发布材料里差别较大，GB200 NVL72 宣传的「720 PFLOPS」接近 sparse 口径）。**面试时说量级 + 主动声明口径**，比报一个精确但错的数字安全得多：「B200 大概 BF16 dense 2.2 PFLOPS 量级、FP8 翻倍、192GB HBM3e、8 TB/s，具体数字我建议以 NVIDIA datasheet 为准。」

### 二、四个维度怎么读（**这是框架，比参数表重要**）

#### ① 显存容量 → 决定「装得下什么」

**显存去哪了**（这条公式在 [[秋招/面经/快手二面|快手二面]] Q4 也被要求当场算过）：

$$\text{显存}=\underbrace{P\times b_w}_{\text{权重}}+\underbrace{2\cdot L\cdot n_{kv}\cdot d_h\cdot s\cdot B\cdot b_{kv}}_{\text{KV Cache}}+\underbrace{\text{activation 峰值}}_{\text{prefill 时}\ \propto B\cdot s}+\underbrace{\sim1\text{GB}}_{\text{CUDA context / NCCL buffer}}+\text{碎片}$$

- $P$ = 参数量，$b_w$ = 每参数字节（BF16=2、INT8=1、INT4=0.5）
- $L$ = 层数，$n_{kv}$ = KV head 数，$d_h$ = head dim，$s$ = 序列长度，$B$ = 并发 batch

**实算一个 PTG 的真实例子**（Qwen3.5-397B-A17B-INT8，16 卡部署，单卡 96GB）：

| 项 | 计算 | 占用 |
| --- | --- | --- |
| 权重 | $397\text{B}\times1\text{B}=397\text{ GB}$，16 卡均分 | **~25 GB/卡** |
| KV Cache + activation | $96-25-\text{预留}$ | **~65 GB/卡** |
| SGLang 的 `mem_fraction_static` | 默认 0.88~0.9 | 实际可用 ~85 GB |

→ **96GB 大显存的价值全在这里**：权重只占 1/4，剩下 3/4 全给 KV Cache，**这才能撑住 80K 上下文 + 高并发**。「显存大算力低」的卡在**长上下文推理**场景反而是甜点。

**KV Cache 的量级感**（61 层、BF16、80K 上下文、单条请求）：

| KV 方案 | 每 token | 80K 单请求 | 96GB 卡扣掉 25GB 权重后能放几条 |
| --- | --- | --- | --- |
| GQA（$n_{kv}=8,d_h=128$） | 250 KB | **20 GB** | ~3 条 |
| **MLA**（$d_c+d_{rope}=576$） | 70 KB | **5.6 GB** | ~12 条 |

→ **这就是 MLA 的商业价值**：同样的卡，长上下文并发能力 **×4**。

#### ② 显存带宽 → 决定 decode 吞吐

$$\text{decode step time}\approx\frac{\text{每步要搬的权重字节}}{\text{HBM 带宽}}\quad(\text{memory-bound 区间})$$

**带宽 vs 容量是两件事**，一定要分开看：
- **H20 是最极端的例子**：容量 96GB（比 H100 还大）、带宽 4.0 TB/s（比 H100 还高），但算力被砍到 148 TFLOPS。→ **它是专门为 decode / 长上下文推理设计的卡**，跑 prefill 会很惨。
- 反过来 A100 40GB 版本带宽只有 1.55 TB/s，是所有版本的短板。

#### ③ 算力 → 决定 prefill 速度和 TTFT

$$\text{prefill FLOPs}\approx 2\times P_{\text{activated}}\times L_{\text{prompt}}$$

（$2$ = 一次乘 + 一次加；attention 的 $O(L^2)$ 项在长上下文下会追上甚至超过 FFN 项）

**例**：一个激活 17B 参数的 MoE，80K prompt：
$$2\times17\times10^9\times8\times10^4=2.7\times10^{15}\text{ FLOPs}=2.7\text{ PFLOP}$$

| 卡 | BF16 dense | 理论最快 TTFT | MFU 50% 时实际 |
| --- | --- | --- | --- |
| H100（8 卡 TP） | $8\times989=7.9$ PFLOPS | 0.34 s | **~0.7 s** |
| H20（8 卡 TP） | $8\times148=1.2$ PFLOPS | 2.3 s | **~4.5 s** ← 超标 |
| A100（8 卡 TP） | $8\times312=2.5$ PFLOPS | 1.1 s | **~2.2 s** |

→ **同一个模型同一套代码，换一张卡 TTFT 差 6 倍**。「算力低」的卡跑长上下文 prefill 会直接击穿 SLA，这就是为什么我们必须做 **PD 分离**——让 P 节点专门堆算力、D 节点专门堆带宽和显存。

> **MFU（Model FLOPs Utilization）** 是这里的核心指标：实际达到的 FLOPs / 理论峰值。生产推理系统 prefill 侧能做到 **40~60%** 就算很好了（FA3 在 H100 上单 kernel 能到 75%，但整个模型有 norm、通信、MoE 路由等拖累）。

#### ④ 互联带宽 → 决定并行策略（**这是架构级约束**）

| 互联 | 带宽（单向，per GPU） | 相对倍数 |
| --- | --- | --- |
| **NVLink 5**（Blackwell） | 1.8 TB/s | **36×** |
| **NVLink 4**（Hopper） | 900 GB/s | **18×** |
| **NVLink 3**（Ampere） | 600 GB/s | 12× |
| **PCIe Gen5 x16** | ~64 GB/s | 1.3× |
| **InfiniBand NDR 400Gb/s** | ~50 GB/s | **1×（基准）** |

> [!important] 并行策略的硬约束（一句话讲清楚）
> **机内 NVLink 比机间 IB 快 18 倍**（H100 时代）→
> - **TP（Tensor Parallel）必须放机内**：它每层都要 AllReduce，通信量最大、最频繁，跨机跑会被通信打爆
> - **PP（Pipeline Parallel）可以跨机**：只在 stage 边界传 activation，通信量小
> - **EP（Expert Parallel）跨机很痛**：MoE 的 All-to-All 是**全交换**，对带宽最敏感 → 这就是 DeepEP、以及 GB200 NVL72 用 NVLink Switch 把 72 卡做成一个 NVLink domain 的原因（**把「机间」变成「机内」，从根本上放开 EP 的设计空间**）
> - **DP（Data Parallel）跨机最省**：只在 step 边界同步梯度（训练）或完全无通信（推理）
>
> 这直接解释了我们在 PTG 为什么是 **`tp=8, dp=2`**（TP 吃满机内 8 卡 NVLink，DP 跨机），以及为什么 **`tp=8, dp=2` 的 TTFT 反而比预期差**——见 [[秋招/面经/快手 AI infra面经|快手一面]] Q12 问题 6。

**其他硬件特性**：
- **NVSwitch**：机内 8 卡全互联交换芯片，任意两卡全带宽。GB200 NVL72 用 NVLink Switch 扩到 72 卡。
- **MIG（Multi-Instance GPU）**：A100/H100 可切成最多 7 个实例，**每个实例有独立的 SM / L2 / HBM 带宽分区**（硬隔离，不是时间片）。适合多租户小模型推理；**但 MIG 实例之间不能 NVLink 通信 → 大模型 TP 用不了 MIG**。
- **ECC**：HBM 默认开 ECC，会占 ~6% 容量。生产必须开（否则长时运行会有 silent data corruption）。
- **Transformer Engine**（Hopper+）：硬件级的 FP8 动态 scaling 单元，配合 per-tensor delayed scaling 自动管理 scale。
- **功耗与部署密度**：H100 700W、B200 1000W、GB300 1400W → **液冷从可选变成必选**，机房供电和散热成为集群规模的真实上限。

### 三、行业趋势（这个洞察能显著加分）

**拐点在持续上升**：

$$\text{AI}_{\text{ridge}}:\quad \text{A100 }153\;\to\;\text{H100 }295\;\to\;\text{B200 }\sim281\ (\text{FP8 口径下更高})$$

而 decode 的算术强度 $\approx$ batch size（推导见上文 [[#Q4 对算子了解吗|Q4]] 的 Roofline 一节）。

> [!star] 一个能讲 3 分钟的洞察
> **「算力涨得比带宽快」是过去五代的持续趋势**，导致 Roofline 拐点不断右移。而 decode 的算术强度约等于 batch size，这意味着**要吃到新一代卡的算力，就必须把 batch 做得越来越大**——但 batch 大了 KV Cache 就装不下。
>
> 于是整个推理栈的演进方向被这一个矛盾锁死，所有技术都在解同一道题：
>
> | 技术 | 怎么解 |
> | --- | --- |
> | **量化**（W4A8 / FP8 / FP4） | 减少权重和 KV 的搬运字节 → 直接提升 memory-bound 区间的吞吐 |
> | **MLA / GQA / MQA** | 压缩 KV Cache → 同样显存塞更大 batch |
> | **PagedAttention** | 消除 KV 碎片 → 提高显存有效利用率 |
> | **Chunked Prefill** | 让 memory-bound 的 decode 和 compute-bound 的 prefill 混批互补 |
> | **PD 分离** | 干脆用不同的卡分别伺候两种瓶颈 |
> | **投机解码 / MTP** | 一次前向验证多个 token → 等效提升算术强度 |
> | **Prefix Caching** | 直接省掉 prefill 的计算 |
>
> **所以『对 NVIDIA 的卡了解吗』这个问题，我的理解不是记参数，而是理解这些参数如何决定上面这张技术选型表。」**

### 四、PPU 810E vs NVIDIA（**主场，一定要主动切过去**）

| 维度 | PPU 真武 810E | H20（最接近的对标） | H100 SXM5 |
| --- | --- | --- | --- |
| 显存 | **96 GB HBM** | 96 GB HBM3 | 80 GB HBM3 |
| 算力 | **低** | 148 TFLOPS BF16（低） | 989 TFLOPS BF16 |
| 定位 | **显存大 / 算力低** | 显存大 / 算力低 | 均衡 |
| 编程模型 | 自研栈 + 类 Triton tile-based 抽象 | CUDA | CUDA |
| 算子库 | 自研（GEMM / FA / RMSNorm / RoPE） | cuBLAS / cuDNN / FA | 同左 |
| 关键限制 | **FA3 的 Hopper 专属路径不可用**；量化 kernel 与 EP 的 shape 约定不兼容 | — | — |

> **怎么讲这段（体现工程判断力，而不是抱怨硬件）**：
>
> 「810E 这类卡的画像决定了**不能照搬 H100 上的调优经验**。在 H100 上你会拼命提高 MFU、榨算力；在 810E 上算力本来就是短板，**你要做的是尽量别让算力成为瓶颈**：
>
> 1. **量化优先**：W4A8 / W8A8-INT8 同时降低权重搬运**和**算力需求（INT8 Tensor Core 吞吐是 BF16 的 2 倍）
> 2. **PD 分离**：让 P 节点专门吃满算力、D 节点专门吃满带宽，两边各自标定
> 3. **大 batch decode**：拐点低意味着更早进入 compute-bound，所以要靠大 batch 摊薄权重搬运
> 4. **显存换并发**：96GB 大显存全给 KV Cache，撑住 80K 长上下文
>
> **同一个模型，在 H100 上和在 810E 上的最优配置是完全不同的两套。**这种『从硬件画像倒推软件策略』的过程，是我在 PTG 最主要的工作。」

### 五、追问预案

| 追问 | 回答要点 |
| --- | --- |
| H100 和 H800 差在哪？ | **只差 NVLink 带宽**：900 → 400 GB/s。算力和显存完全一样。→ 直接影响 TP 效率和跨机 EP，**训练大模型时 H800 的通信瓶颈明显**。 |
| H20 为什么这么设计？ | 出口管制下的合规产品：**保留显存容量和带宽（这两项不在管制指标内），砍算力**（TPP 性能密度指标）。结果是一张**极端偏向 decode / 长上下文推理**的卡，跑 prefill 很吃亏。 |
| 消费卡（4090 / 5090）能用来推理吗？ | 能，小规模可以。4090 24GB GDDR6、1 TB/s、无 NVLink（只能 PCIe）→ **多卡 TP 效率极差**，适合单卡跑 7B~14B 量化模型。缺 ECC、缺 FP8 的部分企业特性、驱动和散热不是为 7×24 设计的。 |
| 怎么选卡？给一个决策框架 | ① **模型多大** → 定显存下限（权重 + KV）；② **上下文多长、并发多高** → 定 KV Cache 需求 → 定显存上限；③ **TTFT SLA** → 定算力（用 $2P_{act}L$ 公式反推）；④ **TPOT SLA** → 定带宽；⑤ **要不要跨机** → 定互联（NVLink / IB）；⑥ **功耗和机房** → 定部署密度。最后算 **TCO = 卡价 + 电费 + 机柜**，而不是只看单卡价格。 |
| B200 的双 die 是怎么回事？ | B200 是**两个 reticle-limit die 通过 NV-HBI（10 TB/s）互联**，对软件**呈现为单个 GPU**（不是两个设备），所以编程模型不变。这是绕过光刻 reticle 极限的做法，代价是良率和封装（CoWoS-L）复杂度。 |
| GB200 NVL72 改变了什么？ | 用 NVLink Switch 把 **72 个 GPU 做成一个 NVLink domain**，任意两卡 1.8 TB/s 全带宽。→ **「机内」的边界从 8 卡扩到 72 卡**，EP / TP 的设计空间被彻底打开，MoE 的 All-to-All 不再是瓶颈。同时也意味着**故障域变大**（一个 NVLink domain 内任一节点故障影响面更广）。 |
| 国产卡你怎么看？ | 客观讲三点：① **单卡算力差距在缩小，但互联（对标 NVLink）和软件生态（对标 CUDA + cuBLAS + FA）差距更大**，后者是真正的护城河；② 我在 PTG 的实际体感是——**大部分时间不是在优化性能，而是在做适配**：attention backend 不兼容、量化 kernel 与并行策略冲突、算子语义对齐、精度验证；③ **但『显存大算力低』这类画像反而和长上下文推理的趋势契合**，所以在特定场景下是有竞争力的。**我做过国产卡的完整 bring-up，这段经验让我对『软件栈成熟度』这件事有非常具体的认识。** |
| 显存带宽和实际能跑到的带宽差多少？ | 标称是理论峰值。实际受**访存模式**影响很大：完全合并的连续读能到 **85~92%**；有 stride 或小粒度访问可能掉到 **30% 以下**。所以 `ncu` 里的 DRAM Throughput 是判断 memory-bound kernel 有没有优化到位的黄金指标。 |

---

# 四、临场速查

## 数字弹药（背这些就够撑全场）

| 类别 | 数字 |
| --- | --- |
| **Q1 概率** | $1/4$；n 段通式 $1-n/2^{n-1}$；$\mathbb E[\max]=11/18\approx0.611$；$P(\max>\frac12)=3/4$ |
| **A100 SXM** | 108 SM / 2048 threads per SM / 65536 regs / 192KB smem / 40MB L2 / 80GB HBM2e / **2.04 TB/s** / **312 TFLOPS BF16** / NVLink 600 GB/s / 400W / **拐点 153** |
| **H100 SXM5** | 132 SM / 228KB smem / 50MB L2 / 80GB HBM3 / **3.35 TB/s** / **989 TFLOPS BF16 dense** / 1979 FP8 / NVLink 900 GB/s / 700W / **拐点 295** |
| **H20** | 96GB HBM3 / **4.0 TB/s** / **148 TFLOPS BF16** / **拐点 37**（显存大算力低的极端案例） |
| **B200** | 192GB HBM3e / 8 TB/s / ~2.25 PFLOPS BF16 / NVLink5 1.8 TB/s / 1000W |
| **PPU 810E** | **96GB HBM**，显存大 / 算力低，对标 H20 但算力更弱 |
| **FlashAttention** | FA2 A100 **~225 TFLOPS（72% 峰值）**，比 FA1 快 2×，比 PyTorch 快 9×；FA3 H100 **~740 TFLOPS（75% 峰值）**，FP8 ~1.2 PFLOPS；HBM 访问减少 **~9×** |
| **带宽层次** | NVLink4 900 GB/s : PCIe Gen5 64 GB/s : IB NDR 50 GB/s ≈ **18 : 1.3 : 1** |
| **延迟层次** | Register 1 cycle / Shared ~25 cycle / L2 ~200 cycle / **HBM 400~800 cycle** |
| **decode 关键公式** | **算术强度 ≈ batch size**（BF16）；**step time ≈ 权重字节 / 带宽** |
| **prefill 关键公式** | **FLOPs ≈ $2\times P_{act}\times L$**；17B 激活 + 80K prompt = **2.7 PFLOP** |
| **KV Cache 公式** | $2\cdot L\cdot n_{kv}\cdot d_h\cdot s\cdot B\cdot b$；61 层 GQA 80K = **20 GB**，MLA = **5.6 GB**（**3.6× 压缩**） |
| **PTG 生产数字** | 平台 **21 机 / 336 卡**、13 个模型、利用率 **100%**；Kimi-K2.6 **3P2D = 48P + 32D = 80 卡**；SLA **TTFT P99 < 2~3s、TPOT < 50~60ms**；平均 input **80K+ tokens** |

## 十句必答金句

1. 「**三角形不等式在 $a+b+c=1$ 下等价于 $\max<\frac12$**」——Q1 的全部难度在这一句。
2. 「**Chunked Prefill 的核心不是切块，是和 decode 混批**；它限制的是单次 iteration 时间。」
3. 「**Chunked Prefill 是时分复用，PD 分离是空分复用。**」
4. 「**Online Softmax 是精确等价，不是近似——分子分母乘同一个修正因子，比值不变。**」
5. 「**Online Softmax 是一切 attention 分块合并的统一代数基础**：FA 的 tiling、FlashDecoding 的 split-K、Ring Attention 的跨卡合并，都是同一套 $(m,\ell,\tilde O)$ rescale。」
6. 「**FlashAttention 反向重算，FLOPs 增加但 wall-clock 下降——因为 GPU 上算力比带宽便宜。**」
7. 「**decode 的算术强度约等于 batch size**，所以拐点决定了你要开多大 batch。」
8. 「**先测量再优化：Roofline 定方向，Nsight 定差距。我猜的瓶颈和 ncu 报出来的，一半以上不一致。**」
9. 「**『没效果』的结论和『有效果』一样有价值——它排除了一个优化方向。**（CUDA Graph 密集桶实验）」
10. 「**从硬件画像倒推软件策略**：H100 上要榨算力，810E 上要省算力、榨带宽。同一个模型的最优配置是两套。」

## 主动交代的边界（**说这个反而加分**）

> 「我诚实说一下我的技术边界：**我是推理系统和算子层的深度使用者和调优者，不是 kernel 作者。**
> - ✅ **能做**：读 FlashAttention / CUTLASS 的关键路径、用 Triton 写和调生产算子、用 Nsight Systems + Nsight Compute 定位瓶颈、量化方案的精度对齐、并行策略选型和配比标定、国产卡的算子适配和 bring-up。
> - ❌ **没做过**：从零手写 warp-specialized 的高性能 CUDA kernel、写 GEMM 的 mainloop、参与编译器后端开发。
>
> **但我的优势是端到端**：从模型上卡 → 算子适配 → 量化 → 并行策略 → K8s 编排 → 网络打通 → 压测标定 → 故障定位 → 上线 → 监控，这条链路我是 owner。**一个 kernel 写得多快只是一环，让整个系统在 SLA 下跑满 336 张卡是另一回事。**」

## 面试后复盘（面完再填）

- [ ] Q1 有没有当场画出单位正方形那张图？面试官对「中点三角形」推导的反应？
- [ ] Q2 讲 PD 分离对比时，面试官有没有追问 KV 传输延迟的具体数字？（一面 Q6 就是这个，二面可能重复验证）
- [ ] Q3 Online Softmax 的推导有没有写到白板上？FA3 的 ping-pong scheduling 讲清楚了吗？
- [ ] Q4~Q6 主动交代边界之后，面试官是往深处钻了还是转向了？（判断这场面试的真实考察意图）
- [ ] 有没有被问到没准备的点？补进对应章节。
- [ ] 反问环节问了什么？
