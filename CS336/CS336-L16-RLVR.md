---
tags:
  - CS336
  - post-training
  - RLVR
  - GRPO
  - PPO
  - reasoning
  - DeepSeek-R1
lecture: L16
aliases:
  - RLVR
  - Post-training 2
  - Reinforcement Learning from Verifiable Rewards
---
## 背景

上一讲（[CS336-L15-After-Pretraining](CS336-L15-After-Pretraining.md)）：SFT 做 imitation，RLHF 做 optimization，大致把模型带到 GPT-3.5 的水平。

本讲要走到 o1 / R1：**从可验证奖励中做强化学习（RLVR, Reinforcement Learning from Verifiable Rewards）**。

> [!important] 动机
> RLHF 的奖励来自一个学出来的 reward model，它本身有噪声，所以**优化到一定程度必然过优化（overoptimization）**，没法干净地 scale。
> 那能不能换到 RL 真正擅长的领域——奖励**精确可验证**（数学答案对不对、代码测试过不过）的地方？这样我们优化的就是自己真正想要的东西。

本讲结构：核心算法（PPO → GRPO → GRPO 变体）、案例研究（R1 / Kimi K1.5 / Qwen3）、现象讨论（Long-CoT、SFT vs RL）。

---

## Part 1: PPO 回顾

### 理论上的三步递进

1. **Policy gradient**：$\nabla_\theta \mathbb{E}_{p_\theta}[R(z)] = \mathbb{E}_{p_\theta}[R(z)\nabla_\theta \log p_\theta(z)]$。无偏但方差太大。
2. **TRPO**：在当前策略附近把问题线性化，用 trust region 限制更新幅度。
3. **PPO**：直接把重要性比值 clip 在 $[1-\epsilon, 1+\epsilon]$，用一阶方法近似 trust region 的效果。

$$\min\left(\frac{\pi_\theta(a|s)}{\pi_{\theta_k}(a|s)}A^{\pi_{\theta_k}}(s,a),\ \text{clip}\left(\frac{\pi_\theta(a|s)}{\pi_{\theta_k}(a|s)}, 1-\epsilon, 1+\epsilon\right)A^{\pi_{\theta_k}}(s,a)\right)$$

概念上 PPO 就这一个目标函数，剩下全是工程。

### 语言模型上的 PPO

action 是 token，state 是已生成的前缀，奖励是**序列末尾一个大的稠密 reward**。形式上和标准 RL 很像，但本质上是个 **bandit 问题**（一步决策、终局奖励）。

### 实现细节（以 AlpacaFarm 为例）

课上强调：讲 PPO 必须看真实实现，因为"细节即算法"。

- **双层循环**：outer loop 采 rollouts，inner loop 在这批 rollouts 上做多步优化。
- **Cliprange = 0.2**，loss 计算本身很标准。
- **Reward shaping**：per-token 加 KL 惩罚，最后一个 token 给完整 reward。实践中还会**在新策略 logp 低于参考策略 logp 的序列上 clip KL**——如果模型训崩了，这能防止 KL 发散。
- **GAE**：用优势代替奖励
  $$\hat{A}_t^{\text{GAE}(\gamma,\lambda)} := \sum_{l=0}^{\infty}(\gamma\lambda)^l \delta_{t+l}^V, \quad \delta_t^V = r_t + \gamma V(s_{t+1}) - V(s_t)$$
  有趣的细节：既然是 bandit 问题，$\gamma=\lambda=1$ 就能 work——此时 GAE 退化成 **reward-to-go 减去 value**。

训练中应该看到：整体 reward（含 RM 分数）上升，KL reward 为负。bandit setting 下曲线通常还算规矩。

> [!note] 为什么会有那么多"PPO 踩坑"博客
> PPO 的效果高度依赖 reward whitening、advantage whitening、KL clip 这些"实现细节"，这也是后面大家想换掉它的直接原因。

### 为什么还需要新算法

**不用 PPO 的理由**：实现复杂；需要 value model，显存吃紧，而且 critic 本身还要额外调参。

**不用 DPO 的理由**：数据不一定天然成对（可验证奖励是标量对错，不是 Bradley-Terry 比较）；DPO 是 offline 的（虽然可以迭代做成 online）。

---

## Part 2: GRPO

### 定义

GRPO（Group Relative Policy Optimization，Shao et al. 2024, DeepSeekMath）的思路非常直接：

1. 从 PPO 出发（大部分组件复用）。
2. **删掉 value function**，不再做 GAE。
3. 优势改成**组内 z-score**。

对每个问题 $q$，从旧策略采样一组输出 $\{o_1,\dots,o_G\}$：

$$\mathcal{J}_{GRPO}(\theta) = \mathbb{E}\left[\frac{1}{G}\sum_{i=1}^{G}\left(\min\left(\frac{\pi_\theta(o_i|q)}{\pi_{\theta_{old}}(o_i|q)}A_i,\ \text{clip}\left(\frac{\pi_\theta(o_i|q)}{\pi_{\theta_{old}}(o_i|q)},1-\epsilon,1+\epsilon\right)A_i\right) - \beta \mathbb{D}_{KL}(\pi_\theta\|\pi_{ref})\right)\right]$$

$$A_i = \frac{r_i - \text{mean}(\{r_1,\dots,r_G\})}{\text{std}(\{r_1,\dots,r_G\})}$$

KL 用 **k3 无偏估计器**，且是直接加在 loss 上（不是塞进 reward，这点和 PPO-RLHF 不同）：

$$\mathbb{D}_{KL}(\pi_\theta\|\pi_{ref}) = \frac{\pi_{ref}(o_i|q)}{\pi_\theta(o_i|q)} - \log\frac{\pi_{ref}(o_i|q)}{\pi_\theta(o_i|q)} - 1$$

> [!important] 一句话理解
> 在**完全 online**（采一批就立刻更新一次）的情况下，GRPO 就是**用组归一化奖励做 baseline 的 policy gradient**。clip 项只有在一批 rollouts 复用多次更新（变成 off-policy）时才起作用。

### 为什么这么受欢迎

没有 value function 之后，整个算法小到可以手写：算每条 rollout 的 reward → 组内 mean/var 归一化 → 算 KL 项 → 梯度更新。课上用 [nano-aha-moment](https://github.com/McGill-NLP/nano-aha-moment) 走读，优势计算基本就是 vanilla 版本，唯一的工程差别是 std 里加了 `1e-4` 的稳定项。

效果上，原论文里 GRPO 优于 RFT（只强化正确答案），process supervision 还能再涨一点——但注意 R1 最后**没有**用 process supervision。

---

## Part 3: GRPO 的理论缺陷

### std 归一化不是合法 baseline

RL 里的 baseline 定理（Sutton & Barto）说：可以从奖励里减去**任何只依赖 state 的项**而保持无偏。GRPO 减均值是合法的，但**除以标准差破坏了无偏性**。

它带来的实际后果是：**std 会给"太简单"或"太难"的题加权**。因为这类题组内奖励方差小，除以一个小的 std 会把优势放大，等于让梯度被最没有信息量的样本主导。（极端情况全对/全错时 std → 0，整组信号退化。）

### 长度偏置

GRPO 的 token 级形式里有一个 $\frac{1}{|o_i|}$ 的长度归一化，它引入 **response-level length bias**：

- 优势为正（答对）时，除以 $|o_i|$ 让**短回答**的每个 token 拿到更大的梯度 → 鼓励正确答案变短。
- 优势为负（答错）时，长回答因为 $|o_i|$ 大而被**惩罚得更轻** → 鼓励错误答案变长。

两个效应叠加，就是训练中"输出长度一路上涨"的一大来源。

### Dr. GRPO 的修正

Liu et al. 2025（*Understanding R1-Zero-Like Training*，幻灯片里写作 "GRPO Done Right"）的修法很朴素：**去掉 $\frac{1}{|o_i|}$，去掉 std 归一化**，只保留减均值：

$$\hat{A}_{i,t} = R(q, o_i) - \text{mean}(\{R(q,o_1),\dots,R(q,o_G)\})$$

这样就回到了无偏梯度，形式上很接近 **REINFORCE with leave-one-out (RLOO)**。

实验结果：reward 曲线和最终 benchmark 分数与 GRPO 相当，但**输出长度被压住了**——尤其是错误答案的长度不再爆炸增长（GRPO 涨到 1.8k+，Dr. GRPO 稳在 1k 附近），token 效率明显更好。

> [!note] 引申：其他常见变体（课外补充，非讲义内容）
> - **DAPO**：clip-higher（上界放宽，防熵坍缩）+ 动态采样（丢掉全对/全错的 group 重采）+ token-level loss + overlong reward shaping。
> - **GSPO**（Qwen）：把重要性比值从 token 级改成序列级，缓解 MoE 上的方差与不稳定。
> - **要不要 KL**：DeepSeek-R1-Zero 自己的目标里 KL 项是**保留**的；但后续一批 R1-Zero-like 复现工作（Dr. GRPO、Open-Reasoner-Zero、DAPO 等）常直接把 $\beta$ 设为 0，理由是纯推理 RL 不需要贴着 SFT 模型。

---

## Part 4: 案例研究一 · DeepSeek R1

### 为什么值得读

- 性能超过 OpenAI o1。
- **公开了 RL 配方**，而且配方本身相当简单。
- 终结了"必须要 MCTS / PRM 才能做推理"的猜测。
- 提供了 SFT 相关的洞见（R1-zero 与 distill-R1 两条线）。

算法就是 GRPO，沿用 DeepSeekMath 的结果，但**不用 process supervision**。

### R1-Zero：受控实验

- **base model**：DeepSeek-V3（不做 SFT，直接 RL）。
- **奖励**：accuracy reward（答案对不对）+ format reward（有没有用 thinking 标签）。
- **数据**：未公开。
- **结果**：比 o1 略差，但已经证明纯 RL 能长出推理能力。

训练过程中观察到两个"现象"：CoT 越来越长；出现所谓 **'aha' moment**（模型自发回头重新审视解法）。

> [!warning] 这两个现象可能被夸大了
> Dr. GRPO 的后续分析指出：
> 1. **长度增长可能只是有偏目标的产物**（见上面的 length bias），未必是"学会了深思"。
> 2. **base model 本身就会说 "Aha!"**——在未经 RL 的基座输出里就能找到"Aha! I can use this to get..."这样的自我修正语言。RL 更像是把已有行为的频率调高，而不是凭空创造。

### R1：把性能推上去

R1 相对 R1-zero 的关键差异：

1. **SFT 初始化**（cold start）
2. **CoT 的语言一致性奖励**
3. **第二阶段引入不可验证奖励**

完整流水线是四段：

$$\text{DeepSeek-V3} \rightarrow \text{Reasoning SFT} \rightarrow \text{RL (GRPO)} \rightarrow \text{SFT} \rightarrow \text{RLHF}$$

- **SFT 初始化**：先喂普通的长 CoT，可能再加一点验证步骤（描述比较模糊）。宣称的好处是可读性；数据来源交代不清。相关工作（如 s1）显示 **1k 条数学/科学题 + Gemini/R1 的长 CoT 就足以 bootstrap 出推理行为**。
- **RL 阶段**：基本同 R1-zero，多一个语言一致性 loss。有意思的观察是 **RL 会自然导致中英混杂**——纯优化正确率的话，语言一致性并不是模型关心的事。
- **后续 SFT**（2 epochs）：推理类的不可验证任务（比如"证明 X"）600k，用 V3 当 judge；非推理数据用 V3 的 SFT 集 200k。
- **RLHF**：可验证部分复用 R1-zero 式的推理 RL，不可验证部分走 V3 的 RLHF 流程——依然用 GRPO。

### 蒸馏

让 R1 生成 **800k** 条 CoT 轨迹，蒸馏给 Qwen 2.5。非推理模型可以通过纯 SFT 获得推理能力，成本远低于自己跑 RL。

### 失败的尝试

论文专门写了一节"unsuccessful attempts"：**PRM**（PRM800k、DeepSeekMath 路线）和 **MCTS** 都没跑通。这是 R1 影响力的一部分——它把社区从"复杂搜索 + 过程奖励"拉回到"简单 RL + 结果奖励"。

---

## Part 5: 案例研究二 · Kimi K1.5

和 R1 同期发布，同样用 RL 打平/超过 o1，细节上和 R1 互补。

### 数据与 SFT

- 数学类数据做标准清洗，平衡主题分布。
- **排除选择题 / 判断题**——猜对的假阳性会污染奖励信号。
- 只保留 **best-of-8 都做不对**的题（难度过滤）。
- SFT 描述得很含糊，只说是 "prompt engineering"（大概率是蒸馏）。

### RL 目标

Kimi 用的是 **reference-based reward model**，优化问题写成：

$$\max_\theta \mathbb{E}_{(x,y^*)\sim\mathcal{D}}\left[\mathbb{E}_{(y,z)\sim\pi_\theta}[r(x,y,y^*)] - \tau \text{KL}(\pi_\theta(x)\|\pi_{\theta_i}(x))\right]$$

算法灵感来自 **DPO 式的推导**：非参数假设下解出最优策略与 reward 的闭式关系

$$r(x,y,y^*) - \tau\log Z = \tau\log\frac{\pi^*(y,z|x)}{\pi_{\theta_i}(y,z|x)}$$

然后用平方损失做 surrogate，最终落到**带正则的 baselined policy gradient**：

$$\frac{1}{k}\sum_{j=1}^{k}\left(\nabla_\theta \log\pi_\theta(y_j,z_j|x)\big(r(x,y_j,y^*) - \bar{r}\big) - \frac{\tau}{2}\nabla_\theta\left(\log\frac{\pi_\theta(y_j,z_j|x)}{\pi_{\theta_i}(y_j,z_j|x)}\right)^2\right)$$

注意它只减均值 $\bar{r}$，**没有 std 归一化，也没有长度归一化**，所以天然没有 GRPO 的长度偏置。

### 长度控制

虽然没有长度偏置，但他们还想**主动压缩 CoT**，于是加了 length reward：

$$\text{len\_reward}(i) = \begin{cases}\lambda & \text{if } r(x,y_i,y^*)=1 \\ \min(0,\lambda) & \text{if } r(x,y_i,y^*)=0\end{cases}, \quad \lambda = 0.5 - \frac{\text{len}(i)-\text{min\_len}}{\text{max\_len}-\text{min\_len}}$$

解读：$\lambda$ 在 $[0.5, -0.5]$ 之间，组内越长的序列越偏负。**答对的鼓励更短**；**答错的只在超过组内长度中位区间时才被惩罚**（即鼓励错误答案不要太长）。因为对性能有影响，这一项**只在训练后期才打开**。

### 其他细节

**Curriculum**：给数据打难度标签，从易到难；按 $(1-\text{success\_rate})$ 的比例采样，避免反复刷已经会做的题。

**Rewards**：代码题从有 ground truth 解的问题出发**自动生成新测试用例**；数学题用 800k 样本训了一个 CoT reward model 做答案等价性判断。

### RL Infra

> [!important] 为什么 RL 训练难做高效
> 1. **on-policy 意味着要 rollout**，而 rollout 就是（慢的）推理。
> 2. 训练和推理**常常是两套框架**，来回切换开销大。
> 3. **长 CoT 让 batch 极度不均衡**——一条 32k token 的轨迹会拖住整个 batch。

Kimi 给出的是一套 **Hybrid Deployment Framework**：同一个 pod 里跑 Megatron sidecar（训练）和 vLLM sidecar（推理），中间用 **checkpoint-engine** 这个 shim 进程隔离两个容器。训练阶段 Megatron 训完后把 GPU 显存 offload 出去；推理阶段 vLLM 用 dummy weights 启动，再通过 **Mooncake** 从 Megatron 拿最新权重，rollout 结束后 checkpoint-engine 把 vLLM 进程全部终止；然后 Megatron 重新 onload 显存进入下一轮。跨 pod 走 RDMA，全局用 etcd 协调。

> [!note] 联系实际（课外补充）
> 这套"训练框架和推理引擎共享 GPU、按阶段互相让出显存"的模式，正是现在 RL 训练栈的主流形态：veRL / OpenRLHF 属于训练侧编排，vLLM / SGLang 属于 rollout 引擎，NVIDIA Dynamo 这类做的是推理服务编排。权重传输与显存腾挪的效率，往往比算法本身更决定端到端吞吐。

---

## Part 6: 案例研究三 · Qwen 3

更晚发布，效果好于 o1 和 R1，但真正有意思的是它的 **scaling 与数据结论**。

整体流程和 R1 同构：**Reasoning RL → RLHF → 蒸馏**。

### SFT + Reasoning RL

数据处理的 playbook 已经比较成型：

- 按 best-of-n 过滤难度（同 Kimi）。
- **去掉不用 CoT 也能做对的题**。
- 去掉和验证集太相似的题。
- 人工检查 CoT 质量（区分"蒙对的"和"真会的"）。
- 最终 **GRPO 只用了 3995 条样本**。

> [!important] 低数据 RLVR
> 这是本讲最反直觉的点之一：RLVR 阶段的数据量可以极小（几千条），关键在于**难度落在模型能力边界上**，而不是量大。

### Thinking Mode Fusion

Qwen3 特有的东西：**控制 CoT 长度 / 是否思考**。

1. 把 thinking 和 non-thinking 数据混合训练，用标签区分。
2. 通过特殊字符串做**提前终止**，实现 thinking budget 控制。

配合 test-time scaling，可以在推理时用 token 预算换准确率。

### 各阶段的能力此消彼长

课上给的表很值得记（以下取各阶段 **Thinking 模式**下的分数；Non-Thinking 列差距很大，例如 AIME'24 只有 28.5 / 31.0）：

| Benchmark (Thinking) | Stage 2 Reasoning RL | Stage 3 Thinking Fusion | Stage 4 General RL |
|---|---|---|---|
| AIME'24 | 83.8 | 81.9 (−1.9) | 81.4 (−0.5) |
| LiveCodeBench v5 | 68.4 | 67.2 (−1.2) | 65.7 (−1.5) |
| Arena-Hard | 86.8 | 89.4 (+2.6) | 93.8 (+4.4) |
| IFEval | 73.0 | 78.4 (+5.4) | 85.0 (+6.6) |
| ToolUse | 63.3 | 70.4 (+7.1) | 85.5 (+15.1) |

> [!warning] 通用 RLHF 会小幅侵蚀数学/STEM 能力
> 推理能力在后续通用对齐阶段会掉一点（AIME 83.8 → 81.4），换来的是指令遵循、Agent、通用对话的大幅提升。这是一个**明确的 trade-off，不是 bug**。

### Agentic RL（Qwen3-Coder-Next）

在 Qwen3 Next 基础上做 agentic 后训练：

**Midtraining 数据源**：GitHub 的 repository-level 长上下文数据（拼接文件，600B tokens）、pull request（带 RAG 检索的仓库状态）、Common Crawl 的 text+code 联合文档（LLM 解析 HTML）、合成数据（LM 生成的代码 QA、真实跑 coding agent 得到的轨迹）、instruction following 与 FIM 数据。

**专家模型 + 蒸馏**：先训 Web dev expert（基于 VLM + agent 动作校验"网页代码是否有效"做 SFT）、UX expert（训练多种 tool 格式）、单轮 QA expert、SWE expert，再蒸馏回 Qwen3 Next Coder。

**环境构造**：自动化构建 SWE-bench 风格环境，规模到 **800k tasks**——Agent RL 的瓶颈从算法转移到了**环境工程**。

---

## 现象讨论

### Long-CoT 是怎么来的

三种解释并存：

1. 有偏目标（长度归一化）导致的**人为拉长**——Dr. GRPO 的证据。
2. base model 已经具备反思行为，RL 只是**放大频率**。
3. 长 CoT 确实能提高难题正确率，所以是**奖励驱动的真实收益**。

讲义只明确给出了前两条（都是对"aha moment 叙事"的降温）；第三条是结合 test-time scaling 结果的个人推测，实际大概率三者都有份。

### SFT vs RL：负梯度到底有没有用

一个自然的问题：能不能不要 RL 的负梯度，只在正确样本上做 SFT（即 expert iteration / rejection sampling）？

Kimi 的 ablation 给了答案：**不行**。对照组是 **ReST**（Reinforced Self-Training，只在正确样本上迭代 SFT）。在 MATH500、OMNI-MATH500、ChatGLMMath、K12 各科等多数 benchmark 上 RL 明显更高，Total 曲线的差距随训练步数持续扩大；只有 GPQA、k12-chemistry、k12-physics 这几个噪声大的子图早期两条线互有交叉。结论是**惩罚错误答案的负梯度提供了 rejection sampling 拿不到的信息**。

---

## 课程总结

> [!important] L16 要点
> 1. **RLHF 的过优化是根本限制**，转向可验证奖励（RLVR）是一条绕开它的路。
> 2. **GRPO = PPO 去掉 critic + 组内 z-score 优势**，简单到能手写，是 RLVR 得以普及的关键。
> 3. GRPO 有明确缺陷：**std 归一化不是合法 baseline，长度归一化引入长度偏置**；Dr. GRPO 两处都删掉即可回到无偏梯度。
> 4. **R1 / Kimi K1.5 / Qwen3 的配方高度收敛**：难度过滤数据 → 长 CoT SFT 冷启动 → 结果奖励 RL → 通用 RLHF → 蒸馏。PRM 和 MCTS 都不是必需品。
> 5. **RLVR 数据可以很少**（Qwen3 只用 3995 条），关键是难度贴着模型能力边界。
> 6. **RL 的负梯度不可替代**，expert iteration 顶不上 RL。
> 7. **RL infra 是真瓶颈**：rollout 慢、训推双框架、长 CoT 导致 batch 不均衡。

---

## 相关链接

- 上一讲：[CS336-L15-After-Pretraining](CS336-L15-After-Pretraining.md)
- 相关笔记：[强化学习](强化学习.md)、[CS336-L10-Inference](CS336-L10-Inference.md)（rollout 侧的推理优化）
- 关键论文：
  - Schulman et al. 2017 (PPO)
  - Schulman et al. 2015 (GAE)
  - Shao et al. 2024 (DeepSeekMath, GRPO)
  - DeepSeek-AI 2025 (DeepSeek-R1)
  - Liu et al. 2025 (Dr. GRPO — *Understanding R1-Zero-Like Training*)
  - Kimi Team 2025 (Kimi K1.5)
  - Qwen Team 2025 (Qwen3 / Qwen3 Coder)
- 代码：[nano-aha-moment](https://github.com/McGill-NLP/nano-aha-moment)、[AlpacaFarm PPO](https://github.com/tatsu-lab/alpaca_farm)
