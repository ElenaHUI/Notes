---
tags:
  - CS336
  - SFT
  - RLHF
  - post-training
  - alignment
  - DPO
  - PPO
lecture: L15
aliases:
  - After Pretraining
  - Mid/Post Training
  - SFT & RLHF
---
## 背景

上一讲（[L14](CS336-L14-Data-Processing.md)）：数据流水线 Transformation → Filtering → Deduplication → Mixing。

本讲：**预训练之后做什么**——从 GPT-3 到 InstructGPT 的 post-training。核心流程是先用监督微调（SFT）做 imitation，再用强化学习（RLHF）做优化。

> [!important] 核心问题
> 预训练数据量大但不一定是我们想要的行为。我们能不能收集“想要的行为”数据并训练模型？
> - 数据长什么样？
> - 如何最好地利用这些数据？
> - 是否需要 scale？

> [!note] 信息稀疏
> post-training 的细节现在公开很少。早期（Stiennon 2020、Bai 2022）比较透明，现代开源多是蒸馏，闭源则是 secret sauce。

---

## Part 1: Supervised Fine-Tuning (SFT)

### SFT 数据演进

开放世界的 instruction tuning 数据集大致经历了这样的演进：

**FLAN → Self-Instruct → Alpaca → ShareGPT/Vicuna → OpenAssistant → WizardLM → Tulu3 → Nemotron → Tool use**

例子能直观看出变化：

- **FLAN**：还是 NLP benchmark 风格，回答简短、任务导向。
- **Alpaca**：更 chatty，比如 "Give three tips for staying healthy" 会列 1/2/3。
- **OpenAssistant**：更长、更详细，会要求引用文献，讲事实。
- **Nemotron-SFT-OpenCode-v1**：包含 tool call 的结构化输出，面向代码/Agent 场景。

### 数据差异带来什么影响

**1. Chattiness / Style**

- 后出的数据集回答越来越长、越来越像对话。
- 但 length / style 对偏好评估影响极大：人和 GPT-based eval 都有明显的 length bias（更长的回答更容易被偏好）。
- 对常规 benchmark（如 MMLU）影响反而不大。

**2. Detail / 知识与事实性**

- OpenAssistant 这类数据会教模型输出引用、讨论专业概念。
- 但这既是优点也是风险：
  - 如果教的是模型已经知道的知识 → 帮助提取。
  - 如果教的是模型不知道的 tail knowledge → 可能加剧幻觉。
- 民间说法（Schulman 2023, Gekhman 2023）：在模型不知道的事实上做 fine-tune 会让它 hallucinate。

> [!note] SFT 与知识
> SFT 更适合“提取预训练里已有的行为”，而不是“灌输新知识”。RL 式的正确性反馈在原则上有帮助，但知识在 LM 中的存储和提取本身很复杂。

**3. Safety**

- LLM 部署到 end-user 需要安全控制（misinformation, scams, spam, hate speech 等）。
- 安全 SFT 细节公开很少，Llama 2 只提到几千条 safety examples。
- 主要做法：从真实用户 query 中提取风险场景，构造安全回复。
-  surprisingly，少量数据（~500 条 Alpaca-style safety examples）就能显著提升安全表现。

### SFT 数据总结

> [!important] SFT 数据 takeaway
> 1. SFT 最适合提取预训练行为，而非添加全新行为。
> 2. 加入（即使是事实正确的）新知识数据有时也会伤害模型。
> 3. 少量正确的行为数据（safety、instruction-following、style）就能起很大作用；但长尾能力仍需要更多数据。

### 如何扩大 SFT 规模：Midtraining / Two-phase Training

如果有很多 instruction 数据，又不想纯 SFT 导致灾难性遗忘，可以把 instruction data 混入预训练阶段：

1. 先在 web/pretraining 数据上预训练。
2. 在预训练后期混入 instruction-tuning 数据。
3. 最后做一个短的 instruction-tuning round。

这被很多公司当作 common recipe，最近在 miniCPM、jetMoE 等国内模型里被公开化。

---

## Part 2: RLHF

### 从 imitation 到 optimization

**Imitation (SFT)**：拟合某个参考分布 $p^*(y|x)$，是生成建模视角，需要参考策略的样本。

**Optimization (RLHF)**：最大化期望奖励 $\mathbb{E}_p[R(y,x)]$，把 LM 当成策略来优化。

为什么要优化？因为**生成/验证差距（G-V gap）**：人写的东西不一定是人最偏好的东西。比如摘要任务，模型生成的摘要可能比人类参考摘要更受偏好。

### RLHF 数据

标准设置是 **pairwise feedback**：对同一个 prompt，给标注者两个回答，问哪个更好。

**数据来源与问题**：

- 早期有 InstructGPT、Bard 的标注指南流出。
- 现在多由众包平台（Outlier、ScaleAI 等）完成，薪酬差异大，expert annotation 增长快。
- 众包难点：难找高质量可验证的标注者、难保证他们真的检查正确性、还要防范 AI-generated 标注。
- 标注者人口统计学分布会显著影响模型行为；即使是很多人投票，不同群体的偏好也可能不同。

**AI-generated feedback**：

- GPT-4 作为 pairwise judge 时，与人类标注者一致性接近人类互相一致性，系统级排名相关性几乎完美。
- 因此前沿模型常用 AI feedback（如 Ultrafeedback 用于 Zephyr、Tulu3 等）。
- Constitutional AI（Bai et al.）也是一种 self-training 形式。

**Length effects**：RLHF 会放大回答长度，是一个显著的 side effect。

### PPO（简要概念）

PPO 是 RLHF 的原生方法，来自 InstructGPT / Stiennon 2020。

概念上的递进：
1. **Policy gradient**：$\nabla_\theta \mathbb{E}_{p_\theta}[R(z)] = \mathbb{E}_{p_\theta}[R(z) \nabla_\theta \log p_\theta(z)]$，但方差太高。
2. **TRPO**：在当前策略附近线性化问题。
3. **PPO**：用 clip 限制 ratio，避免策略更新过大。

PPO 需要一个 reward model、需要 on-policy rollout，实现比较 finicky。

### DPO：不用 PPO 的 RLHF

DPO 的目标：去掉 reward model，去掉 on-policy rollout/outer loop。

核心思想：
- 正样本上走 log-loss 梯度（鼓励生成好回答）。
- 负样本上走负梯度（抑制坏回答），并用隐式 reward 的预测误差做缩放。

**推导关键**：
1. 假设策略空间非参数化，得到最优策略与 reward 的闭式关系。
2. 用策略参数化 reward（implied reward）。
3. 用监督损失优化 reward，等价于优化策略。

概念上，DPO 是在 pairwise 数据上做 MLE，只是用了非参数假设和另一种参数化方式。

**LLaMA 等开源模型的做法**：DPO + Expert iteration 做 post-training。

### DPO 变体

- **SimPO**：去掉 reference model。
- **Length-normalized DPO**：缓解 length bias。

### PPO vs DPO

> [!note] 没有统一答案
> PPO 和 DPO 谁更好高度依赖实验设置。两者都能 work，也都有论文互相挑战。关键还是数据质量、超参、评估方式。

### RLHF 的副作用

**1. Overoptimization**

- 在各种 RLHF 优化器上都能观察到：reward 优化到一定程度后会过拟合。
- 对人类偏好、带噪声的 LM 偏好都成立；但对无噪声的 LM 偏好不成立（因为 signal 本身没有 noise）。

**2. Mode collapse / Entropy loss**

- RLHF 把 LM 从概率模型变成了策略，默认不再保持 calibration。
- 容易输出高度集中、多样性下降的回复。

---

## 课程总结

> [!important] L15 要点
> 1. **SFT** 是 imitation，最适合提取预训练已有行为；小量高质量行为数据（safety、style、instruction-following）效果显著。
> 2. **RLHF 数据** 收集很困难，众包质量、标注者分布、AI feedback 都是关键变量。
> 3. **PPO** 是传统 RLHF 算法但复杂；**DPO** 通过隐式 reward 把它简化为监督学习。
> 4. 优化 reward 要小心 **overoptimization** 和 **mode collapse**。

---

## 相关链接

- 上一讲：[CS336-L14-Data-Processing](CS336-L14-Data-Processing.md)
- 关键论文：
  - Ouyang et al. 2022 (InstructGPT)
  - Stiennon et al. 2020 (Learning to summarize from human feedback)
  - Bai et al. 2022 (Constitutional AI / HH)
  - Rafailov et al. (DPO)
