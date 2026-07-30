---
tags:
  - CS336
  - evaluation
  - benchmarks
  - perplexity
  - safety
lecture: L12
aliases:
  - 模型评估
  - Evaluation
---

## 背景

到目前为止，训练 LM 的所有环节都已覆盖（架构、训练、系统、scaling）。缺失的拼图：**用什么数据训练？** 数据决定模型行为（代码？多语言？DNA？）。但在讨论数据之前，需要先明确：**我们希望模型有什么行为？** → 这就是评估（Evaluation）。

> [!important] 核心挑战
> 评估是将**抽象构念**（abstract construct）转化为**具体指标**（concrete metric）的过程。没有唯一的"好"定义。

"好"的多种定义：

- Benchmark 分数高（[Artificial Analysis](https://artificialanalysis.ai/)）
- Benchmark 分数高且运行便宜
- 人类偏好其回复（[Arena AI](https://lmarena.ai/)）
- 人们愿意使用并付费（[OpenRouter](https://openrouter.ai/)）

---

## Part 1: Perplexity

### 基本定义

语言模型是 token 序列上的概率分布 p(x)。

**Perplexity** = $(1/p(D))^{1/|D|}$，衡量 p 是否给数据集 D 赋予高概率。

- 预训练目标：最小化训练集上的 perplexity
- 评估：在测试集上测 perplexity（传统语言建模研究的做法）

### 经典数据集

| 数据集 | 来源 |
|---|---|
| Penn Treebank (PTB) | WSJ |
| WikiText-103 | Wikipedia |
| One Billion Word (1BW) | WMT11（EuroParl、UN、新闻） |

**经典范式：** in-distribution 评估——在同一数据集的 train/test split 上训练和评估。

### GPT-2 的转变

- 训练数据：WebText（40GB，Reddit 链接的网站）
- 评估方式：**zero-shot** 在标准数据集上（out-of-distribution）
- 结果：小数据集（PTB）上迁移效果好，大数据集（1BW）上不明显

### Perplexity 的信仰与局限

> [!tip] "Perplexity is all you need"（信仰）
> 真实分布为 t，模型为 p。最佳 perplexity = H(t)，当且仅当 p = t 时取得。若 p = t，则 p(solution | problem) 可解决所有任务。不断压低 perplexity → 终将"达到 AGI"。

**Perplexity 可能是 "more than you need"：**

- 例："Stanford was founded in 1885"
- Perplexity 惩罚所有 token 的预测，但某些 token（如 "founded"）可能不相关
- 解决：测**条件 perplexity** $p(\text{response} | \text{prompt})^{1/|\text{response}|}$

### 伪装成 Benchmark 的 Perplexity

| Benchmark | 形式 |
|---|---|
| [LAMBADA](https://arxiv.org/abs/1606.06031)（Paperno+ 2016） | Cloze（填空） |
| [HellaSwag](https://arxiv.org/abs/1905.07830)（Zellers+ 2019） | 多选句子补全 |

### 总结

- Perplexity 在 LM 开发中仍被大量使用（平滑的 scaling laws）
- 但仍需要捕捉真实场景的 benchmark（给"不信者"看）

---

## Part 2: 考试类 Benchmark

考试的优点：可控主题和难度、答案明确、易于评分。

### 主要 Benchmark 对比

| Benchmark | 规模 | 特点 | 难度 |
|---|---|---|---|
| **[MMLU](https://arxiv.org/abs/2009.03300)** | 57 科目，多选 | 测知识而非语言理解；few-shot 评估（[stats](https://llm-stats.com/benchmarks/mmlu)、[HELM](https://crfm.stanford.edu/helm/)） | 已趋饱和 |
| **[MMLU-Pro](https://arxiv.org/abs/2406.01574)** | 10 选项 | 去噪 + CoT 评估；准确率下降 16%-33%（[stats](https://llm-stats.com/benchmarks/mmlu-pro)） | 中等 |
| **[GPQA](https://arxiv.org/abs/2311.12022)** | PhD 级问答 | 61 位 PhD 出题；专家 65%，非专家+Google 34%，GPT-4 39%（[stats](https://llm-stats.com/benchmarks/gpqa)） | 高 |
| **[HLE](https://arxiv.org/abs/2501.14249)** | 2500 题，多模态 | $500K 奖金；经前沿 LLM 过滤 + 多轮审核（[stats](https://llm-stats.com/benchmarks/hle)） | 极高 |

---

## Part 3: 对话类 Benchmark

**问题：** 大多数人不向 AI 助手问多选题。如何评估开放式回复？

### Chatbot Arena

[Chatbot Arena](https://lmarena.ai/)（[Chiang+ 2024](https://arxiv.org/abs/2403.04132)）

**数据收集流程：**

1. 随机用户输入 prompt
2. 获得两个随机（匿名）模型的回复
3. 用户评判哪个更好

**ELO 排名：** 基于成对比较拟合

$$p(A \text{ wins}) = \frac{1}{1 + 10^{(ELO_B - ELO_A)/400}}$$

**优点：**

- 真实 prompt（用户有动力实际使用）
- 不需要给所有模型相同 prompt
- 动态：持续纳入新 prompt 和新模型

**问题：**

- 用户是谁？偏差？垃圾？
- 二元偏好混淆了风格和正确性
- 人类如何判断正确性？容易被 sycophancy 影响

### AlpacaEval

[AlpacaEval](https://tatsu-lab.github.io/alpaca_eval/)（[Dubois+ 2024](https://arxiv.org/abs/2404.04475)）

- 805 条指令，用 GPT-4 做 judge 计算 win rate
- 问题：LLM judge 偏好更长回复 → leaderboard gaming
- AlpacaEval 2.0：用回归去偏
- 与 Chatbot Arena 相关性高（作为 sanity check）

### WildBench

[WildBench](https://arxiv.org/abs/2406.04770)（Lin+ 2024，[HELM](https://crfm.stanford.edu/helm/)）

- 从 100 万真实对话中筛选 1024 条
- GPT-4 turbo 做 judge + checklist（类似 CoT judging）
- 与 Chatbot Arena 相关性高

### 总结

> [!important] 对话评估要点
> - 成对比较（pairwise）比绝对评分信号更强
> - 警惕偏差（人类和 LLM judge 都有）
> - Checklist/rubric 提升可靠性（无论 judge 是人还是 LLM）

---

## Part 4: Agent 类 Benchmark

**从评估 LM "说什么"（chat）→ 评估 LM "做什么"（agent）。**

Agent = 语言模型 + agent scaffold（决定如何使用 LM 的逻辑）

### 主要 Benchmark

| Benchmark | 任务 | 评估方式 |
|---|---|---|
| **[SWE-Bench](https://arxiv.org/abs/2310.06770)** | 2294 个 Python repo 任务：给 codebase + issue → 提交 PR（[stats](https://llm-stats.com/benchmarks/swe-bench-verified)） | 单元测试 |
| **[TerminalBench](https://www.tbench.ai/)** | 229 个终端环境任务，93 位贡献者众包（[stats](https://llm-stats.com/benchmarks/terminal-bench)） | 任务完成 |
| **[CyBench](https://arxiv.org/abs/2408.08926)** | 40 个 CTF 安全任务（[stats](https://llm-stats.com/benchmarks/cybench)） | 用首次解决时间衡量难度 |
| **[MLEBench](https://arxiv.org/abs/2410.07095)** | 75 个 Kaggle 竞赛 | 竞赛排名 |

### Agent Scaffold 策略

| 策略 | 说明 |
|---|---|
| Explicit planning | 维护 todo list，逐项完成 |
| Hierarchical delegation | agent 调用 sub-agent（保持 context 干净） |
| Persistent memory | 读写文件 |
| Extreme context engineering | 显式提供更多流程指令 |

> [!note] Agent 评估要点
> - Agent 极大扩展了 LM 的能力面
> - Agent scaffold 非常重要
> - 评估 agent = 评估 scaffold + 语言模型（两者耦合）

---

## Part 5: 纯推理 Benchmark

**目标：** 将推理与知识分离——推理是更纯粹的智能形式（不只是记忆事实）。

### ARC-AGI

- 100% 人类可解，但对 AI 有挑战性
- 每个任务唯一，记忆无用

| 版本 | 时间 | 特点 |
|---|---|---|
| ARC-AGI-1 | 2019 | 初版 |
| ARC-AGI-2 | 2025.3 | 更多多步推理；预训练 LM 无帮助，推理模型（o1/o3）开始突破 |
| ARC-AGI-3 | 2026.3 | 交互式环境 |

> [!warning] 局限
> - 目标是分离推理与知识（但很难做到！）
> - 受限于人类推理（非超人推理）
> - 清楚暴露了当前模型的差距

---

## Part 6: 安全性 Benchmark

### 主要 Benchmark

| Benchmark | 内容 |
|---|---|
| **HarmBench** | 510 种违反法律/规范的有害行为 |
| **AIR-Bench** | 基于监管框架和公司政策；314 风险类别，5694 prompts |

### Jailbreaking

- LM 被训练为拒绝有害指令
- **GCG（Greedy Coordinate Gradient）：** 自动优化 prompt 绕过安全机制
- 可从开源模型（Llama）迁移到闭源模型（GPT-4）

### 安全的复杂性

- 安全的很多方面强依赖上下文（政治、法律、社会规范——因国家而异）
- 风险多样：幻觉、sycophancy、协助犯罪、不平等、丧失批判性思维
- **Dual-use：** 强大的网络安全 agent 可用于入侵系统，也可用于渗透测试

---

## Part 7: 真实性（Realism）

**生态效度（Ecological Validity）：** 评估在多大程度上捕捉了真实使用？

- 考试 benchmark（GPQA）离真实使用很远
- Chatbot Arena 的 prompt 来自真人，但分布不可控

### 提升真实性的努力

| 方法 | 说明 |
|---|---|
| **GDPval**（OpenAI） | 44 职业 × 9 大 GDP 行业；任务来自 ~14 年经验的专业人士 |
| **MedHELM** | 121 临床任务，29 位临床医生出题；混合私有+公开数据 |
| **Clio**（Anthropic） | 用 LM 分析真实用户数据，分享人们提问的通用模式 |

> [!warning] 矛盾
> 真实性和隐私有时相互冲突。

---

## Part 8: 有效性（Validity）

### 训练-测试重叠问题

- ML 101：不要在测试集上训练
- 前基础模型时代（ImageNet、SQuAD）：明确的 train-test split
- 现在：在互联网上训练，不公开数据

### 应对策略

| 路线 | 方法 |
|---|---|
| Route 1 | 从模型推断 train-test overlap（利用数据点的 exchangeability） |
| Route 2 | 鼓励报告规范（模型提供者报告重叠情况） |
| Route 3 | 使用**新鲜评估**（LiveCodeBench、UncheatableEval：爬取新网页） |
| Route 4 | 使用**私有评估**（公司内部代码库、个人写作；perplexity 最容易） |

### 数据集质量

- SWE-Bench → SWE-Bench Verified（修复问题）
- 创建 benchmark 的 Platinum 版本（更高质量）
- Agent benchmark 的问题：测试用例不足、trivial agent 就能解决
- **Docent：** 用 LLM 检查 agent trace 来发现问题

---

## Part 9: 如何思考评估

### 评估的目的（没有唯一答案）

| 角色 | 目的 |
|---|---|
| 用户/公司 | 做购买决策（模型 A vs B，用于特定场景） |
| 研究者 | 测量模型的原始能力（如智能） |
| 政策制定者 | 理解收益 + 危害 |
| 模型开发者 | 获得反馈以改进模型 |

### 评估什么？

| 时代 | 评估对象 | 特点 |
|---|---|---|
| 前基础模型 | **方法**（methods） | 标准化 train-test split |
| 现在 | **模型/系统**（models/systems） | 不限方法 |

- 评估方法 → 鼓励研究者的算法创新
- 评估模型/系统 → 对下游用户有用
- **无论如何，必须定义游戏规则！**

> [!tip] 例外：nanogpt speedrun
> 固定数据，计算达到特定 validation loss 的时间 → 评估的是方法而非模型。

---

## 总结

> [!important] 三个 Takeaway
> 1. **没有唯一正确的评估**——根据你想测量什么来选择
> 2. **明确游戏规则**（评估的是方法 vs 模型 vs agent）
> 3. **三个考量维度**：难度（difficulty）、真实性（realism）、有效性（validity）

---

## 相关链接

- Scaling Laws 与 perplexity 的关系：[[CS336-L9-Scaling-Laws]]
- 推理效率（评估需要大量推理）：[[CS336-L10-Inference]]
- 数据决定模型行为（下一讲）：[[CS336-L13-Data-Sources]]
- 课程进度：[[课程进度]]
