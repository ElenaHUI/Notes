---
tags:
  - CS336
  - data
  - filtering
  - deduplication
  - data-mixing
  - synthetic-data
lecture: L14
aliases:
  - 数据处理
  - Data Processing
---

## 背景

上一讲（[L13](CS336-L13-Data-Sources.md)）：Live service → dump/crawl → processed data，以及 ToS、版权等考量。

本讲：**数据流水线**——从 raw data 到可训练数据的四个环节：

> [!important] 数据流水线
> **Transformation → Filtering → Deduplication → Mixing**
> 之后是 post-training 的合成数据。

---

## Part 1: 数据转换（Transformation）

### 问题

Raw data 不是文本——是 HTML、PDF（arXiv）、目录结构（代码仓库）。

### HTML → Text（主要环节）

- 移除样板（导航、广告），提取正文内容
- 图片、表格等如何处理？（本质上有损，需要 linearize）
- **工具（基于规则）：** trafilatura、resiliparse、jusText、lynx 等

> [!note] 转换质量影响下游任务
> HTML→text 工具的选择直接影响 LM 的下游任务准确率（[Li+ 2024](https://arxiv.org/abs/2406.11727)）。

### PDF 处理（FinePDFs）

- 来源：Common Crawl
- 重新爬取被截断的 PDF（体积大）
- OCR：用 VLM（RolmOCR）或 Docling
- 大量清理和过滤
- 很多版面信息丢失

---

## Part 2: 过滤（Filtering）

### 通用框架

> [!important] 过滤的本质
> 给定目标数据 T 和大量原始数据 R，找到 R 中与 T 相似的子集 T'。

**应用：**
- 语言识别（英语 vs 其他）
- 质量过滤（高质量 vs 低质量）
- 毒性过滤（无毒 vs 有毒）

### 过滤算法的要求

| 要求 | 说明 |
|---|---|
| 泛化 | 从目标数据泛化（希望 T 和 T' 不同） |
| 极快 | 必须在巨大的 R 上运行 |

参考：数据选择综述 [Albalak+ 2024](https://arxiv.org/abs/2402.10024)

### 分类器类型

| 类型 | 评分函数 | 代表 |
|---|---|---|
| 生成模型 | score(x) = p_T(x) | KenLM（n-gram 语言模型） |
| 判别分类器 | score(x) = p(T \| x) | fastText |

**使用方式：** 保留 score(x) ≥ 阈值的样本（可随机化）。

### 是否使用模型过滤？

| 不使用 | 使用 |
|---|---|
| C4、Gopher、RefinedWeb、FineWeb、Dolma | GPT-3、LLaMA、DCLM |

> [!tip] 趋势
> 模型过滤正成为主流。

### 应用一：语言识别

[fastText 语言识别](https://fasttext.cc/docs/language-identification.html)：
- 开箱即用，支持 176 种语言
- 训练于多语言站点：Wikipedia、Tatoeba（翻译）、SETimes（东南欧新闻）
- Dolma 保留 p(English) ≥ 0.5（[Soldaini+ 2024](https://arxiv.org/abs/2402.00159)）

### 应用二：质量过滤

#### OpenMathText（[Paster+ 2023](https://arxiv.org/abs/2310.12335)）

从 Common Crawl 策展数学文本语料：

1. 规则过滤（含 LaTeX 命令）
2. KenLM（训练于 ProofPile），保留 perplexity < 15000
3. fastText 分类器预测数学写作（阈值 0.17 正 / 0.8 负）

**结果：** 147 亿 tokens，训练 1.4B 模型优于用 20 倍数据训练的模型。

#### GPT-3（[Brown+ 2020](https://arxiv.org/abs/2005.14165)）

- 正例：{Wikipedia, WebText2, Books1, Books2}
- 负例：Common Crawl
- 训练基于词特征的线性分类器
- 按分数随机保留：

```python
def keep_document(score: float) -> bool:
    return np.random.pareto(9) > 1 - score
```

#### LLaMA / RedPajama（[Touvron+ 2023](https://arxiv.org/abs/2302.13971)）

- 正例：Wikipedia 引用的页面
- 负例：Common Crawl
- 保留分类为正的文档

#### phi-1（[Gunasekar+ 2023](https://arxiv.org/abs/2306.11644)）

**哲学：** 用极高质量数据（教科书）训练小模型（1.5B）。包含 GPT-3.5/4 生成的合成数据。

```python
R = "Python subset of the Stack"                    # 原始数据
prompt = "determine its educational value for..."   # 教育价值评分
T = "Use GPT-4 with this prompt to classify 100K"   # 正例
```

- 用预训练 codegen 模型的 embedding 训练随机森林分类器
- 从 R 中选取分类为正的数据

**HumanEval 结果：**

| 训练数据 | 模型 | 步数 | HumanEval |
|---|---|---|---|
| The Stack (Python 子集) | 1.3B | 96K | 12.19% |
| 过滤后子集 | 1.3B | 36K | **17.68%** |

### 应用三：毒性过滤（Dolma）

**数据集：** [Jigsaw Toxic Comments](https://www.kaggle.com/c/jigsaw-toxic-comment-classification-challenge)（2018）
- Wikipedia 讨论页评论，标注 {toxic, severe_toxic, obscene, threat, insult, identity_hate}

### 过滤的规模依赖效应

> [!warning] 没有单一最优过滤阈值
> - 训练更久 → 需要更多（低质量）数据 → 降低阈值
> - 训练更短 → 需要更少（高质量）数据 → 提高阈值

### 过滤小结

> [!important] 过滤要点
> - 定义目标数据（"好"是什么样），然后外推到原始数据
> - 过滤对构建好模型至关重要
> - 分类器类型：生成模型（KenLM）vs 判别器（fastText）
> - 趋势：模型过滤成为主流

---

## Part 3: 去重（Deduplication）

### 为什么要去重

**两种重复：**

| 类型 | 例子 |
|---|---|
| 精确重复 | 镜像站、GitHub forks（[Gutenberg 镜像](https://www.gutenberg.org/)） |
| 近似重复 | ToS/许可证（[MIT license](https://opensource.org/licenses/MIT)）、模板生成文本、格式差异 |

> [!warning] C4 中的极端案例
> 一段产品描述在 C4 中重复了 **61,036 次**。

**去重的好处**（[Lee+ 2021](https://arxiv.org/abs/2107.06499)）：
- 训练更高效（token 更少）
- 避免记忆化（缓解版权、隐私问题）

### 设计空间

| 维度 | 选项 |
|---|---|
| 粒度（item） | 句子、段落、文档 |
| 匹配方式 | 精确匹配、共同子项存在、共同子项比例 |
| 操作 | 全部移除、保留一个 |

### 核心挑战

> [!important] 去重的本质
> 比较每个 item 与其他所有 item → 需要**线性时间**算法才能 scale。

### 哈希函数

**哈希函数 h：** 将 item 映射到远小于 item 的哈希值（整数或字符串）。

| 类型 | 特点 | 用途 |
|---|---|---|
| 加密哈希（SHA-256） | 抗碰撞，慢 | Bitcoin |
| 非加密哈希（DJB2、MurmurHash、CityHash） | 不抗碰撞，快 | 哈希表 |

本讲使用 **MurmurHash**：`h = mmh3.hash("hello")`

### 精确去重

```python
items = ["Hello!", "hello", "hello there", "hello", "hi", "bye"]
# 哈希 → 按哈希分组 → 每组保留一个
hash_items = itertools.groupby(sorted(items, key=mmh3.hash), key=mmh3.hash)
deduped_items = [next(group) for h, group in hash_items]
```

| 优点 | 缺点 |
|---|---|
| 简单、语义清晰、高精度 | 不能去近似重复 |

> [!note] 可并行化
> 写法天然 MapReduce 友好，易于并行和 scale。

**C4 的去重**（[Raffel+ 2019](https://arxiv.org/abs/1910.10683)）：
- 粒度：3 句 span
- 匹配：精确匹配
- 操作：保留一个

> [!warning] 连贯性问题
> 从文档中间移除 3 句 span 后，文档可能不再连贯。

### Jaccard 相似度

$$\text{Jaccard}(A, B) = \frac{|A \cap B|}{|A \cup B|}$$

```python
def compute_jaccard(A, B):
    intersection = len(A & B)
    union = len(A | B)
    return intersection / union
```

**定义：** 两文档 Jaccard 相似度 ≥ 阈值则为近似重复。

### MinHash

> [!important] MinHash 的核心性质
> 随机哈希函数 h 使得 $\Pr[h(A) = h(B)] = \text{Jaccard}(A, B)$

通常希望不同 item 哈希到不同值；但这里**希望碰撞概率依赖相似度**。

```python
def minhash(S: set[str], seed: int):
    return min(mmh3.hash(x, seed) for x in S)
```

**直观理解（特征矩阵）：**

| item | A | B |
|---|---|---|
| 1 | 1 | 1 |
| 2 | 1 | 1 |
| 3 | 1 | 1 |
| 4 | 1 | 0 |
| 5 | 0 | 1 |

随机哈希函数 → item 的随机排列 → 看哪个 item 在 A 和 B 中各自排第一。
- 若 1/2/3 排第一 → A 和 B 的 minhash 相同
- 若 4/5 排第一 → 不同

```python
n = 100  # 生成 n 个随机哈希函数
matches = [minhash(A, seed) == minhash(B, seed) for seed in range(n)]
estimated_jaccard = len([m for m in matches if m]) / len(matches)
```

> [!note] 单个 MinHash 的问题
> 碰撞只能告诉你 Jaccard 的期望值，不能确定 Jaccard(A,B) > 阈值。需要 LSH 来 sharpen。

### 局部敏感哈希（LSH）

**目标：** A 和 B 在 Jaccard > 阈值时碰撞，否则不碰撞。

**方案——AND-OR 结构：**
- 用 n 个哈希函数，分成 b 个 band，每个 band r 个哈希函数（n = b × r）

```
h1  h2  h3  h4  |  h5  h6  h7  h8  |  h9  h10  h11  h12
   band 1            band 2              band 3
```

**碰撞条件：** A 和 B 在**某个 band 内所有 r 个哈希函数**都返回相同值。

```python
def get_prob_collision(sim, b, r):
    prob_match = sim ** r                        # 某个 band 全匹配的概率
    prob_collision = 1 - (1 - prob_match) ** b   # 至少一个 band 匹配的概率
    return prob_collision
```

**参数调节效果：**

| 调节 | 效果 |
|---|---|
| 增大 r | 阈值更锐利，曲线右移（更难匹配） |
| 增大 b | 曲线左移（更容易匹配） |

**实例**（[Lee+ 2021](https://arxiv.org/abs/2107.06499)）：n = 9000, b = 20, r = 450

**阈值推导：**

碰撞概率为常数（≈ 1 - 1/e）时：

$$\text{prob\_match} = \frac{1}{b}$$

$$\text{threshold} = \left(\frac{1}{b}\right)^{1/r}$$

> [!tip] LSH 小结
> - AND-OR 结构将概率锐化为接近阶跃函数
> - 阈值由 b 和 r 决定
> - 线性时间，可 scale 到海量数据集

---

## Part 4: 数据混合（Data Mixing）

### 问题

LM 在多个数据源上训练，关键问题：**各源的采样比例应如何设置？**

```python
sources = {"Wikipedia", "CC", "GitHub"}
p = {"Wikipedia": 0.3, "CC": 0.5, "GitHub": 0.2}  # 一种混合方案
```

### 基线方法

| 方法 | 公式 | 说明 |
|---|---|---|
| Vibes（直觉） | 手动设置 | 非常常见 |
| 均匀采样 | p(s) ∝ 1 | — |
| 比例混合 | p(s) ∝ num_tokens(s) | 按数据量占比 |

**直觉：** 应上权重高质量源。但有微妙问题——

### Epoching 问题

> [!warning] 小数据源 + 大权重 = 过拟合
> 每个数据源有限，权重过大时需多次 epoch → 过拟合

```python
source_token_counts = {"low": 10T, "high": 10B}   # 低质量多，高质量少
p = {"low": 0.5, "high": 0.5}                      # 朴素混合
train_tokens = 1T
# low: 0.5 epoch    high: 50 epoch  ← 高质量数据重复 50 次！
```

### UniMax（[Chung+ 2023](https://arxiv.org/abs/2306.10898)）

**场景：** 多语言模型的语言平衡。

- 前序工作：p(s) ∝ num_tokens(s)^α, α ∈ [0, 1]（介于均匀和比例之间）
- **UniMax：** 均匀采样，但对每个源设置**硬上限 C 个 epoch**

$$p(s) \cdot \text{num\_training\_tokens} \leq C \quad \forall s$$

### 回归混合（Regression-based Mixing）

[Liu+ 2024](https://arxiv.org/abs/2406.01185)、[Chen+ 2026]

1. 定义混合分布（如 Dirichlet）
2. 定义回归方法（线性、梯度提升树）
3. 定义基于下游 eval 的目标（小心过拟合！）
4. 小规模与大规模之间的差距（成本 vs 精度 tradeoff）

**两个希望：**
1. 回归模型在最优点准确 🙏
2. 最优混合从 small scale 迁移到 large scale 🙏

> [!warning] 规模依赖效应
> 小规模最优混合（p = {"low": 0.1, "high": 0.9}）在大规模训练时会因高质量数据 epoch 过多而过拟合。

### 模拟 Epoching（Simulated Epoching）

[Held+ 2025](https://arxiv.org/abs/2505.20460)

**核心思想：** 让小规模看起来像大规模（本课程的通用主题）。

**实现：** 按比例下采样所有数据源：

```python
small_run_tokens = 10B
large_run_tokens = 1T
ratio = small_run_tokens / large_run_tokens  # = 0.01
downsampled_counts = {s: count * ratio for s, count in source_token_counts.items()}
```

在下采样混合中，epoch 过多的模型表现不好 → 最优解更平衡：

```python
p = {"low": 0.7, "high": 0.3}  # 更平衡
```

### 数据混合小结

> [!important] 要点
> - 问题：如何加权不同数据源
> - 回归混合：小规模估计 mixture → loss，然后优化（类似 scaling laws）
> - 关键考量：epoching 和过拟合（解决方案：cap 或 simulated）

---

## Part 5: Post-training 数据

### 基本配方

1. 定义一组**环境**
2. 定义一组**任务 / prompts**
3. 从强模型（teacher）收集**回复**

### OpenThoughts（[Guha+ 2025](https://arxiv.org/abs/2503.07884)）

| 要点 | 说明 |
|---|---|
| 规模 | 120 万条，用 QwQ-32B 作为 teacher |
| 问题来源 | 27 个人工/合成源（StackExchange、NuminaMath、Chemistry 等） |
| 多采样 | 每个 prompt 采 16 条回复 → 有帮助 |
| Teacher 选择 | QwQ-32B 比 DeepSeek-R1 是更好的 teacher |
| 答案过滤 | 无帮助 |
| 数据源偏好 | 小而高质量（OpenMath-2-Math）优于大而多样 |

### SWE 类数据

#### SWE-smith（[Yang+ 2025](https://arxiv.org/abs/2503.16507)）

- 给定仓库，用 LM 生成任务（引入 bug）
- 128 个 GitHub 仓库 → 5 万条任务

#### SWE-Zero（[Ludwig+ 2026](https://arxiv.org/abs/2502.17999)）

**观察：** SWE 任务有重依赖（不同于数学或编程竞赛），设置数千个 Docker 镜像是基础设施噩梦。

**关键发现：** 强模型无需执行反馈也能解决很多任务——内部有代码语义的"世界模型"。

| 数据集 | 内容 |
|---|---|
| SWE-Zero | 30 万条 agent 轨迹（不需仓库特定执行）+ 15 万 GitHub PRs；用 OpenHands scaffold，移除未来 git commit 防"git hacking"；从 Qwen3-Coder-480B 蒸馏 + 过滤 |
| SWE-Hero | 1.3 万条 agent 轨迹（**需要**执行反馈） |

#### SWE-rebench（[Badertdinov+ 2025](https://arxiv.org/abs/2507.21439)）

- 2.1 万交互式 Python SWE 任务（来自 3400 个 GitHub 仓库）
- 45 万 PRs（来自 GitHub 和 GitHub Archive）
- 用 Qwen 2.5-72B-Instruct 安装依赖和评估 PR 质量

#### SWE-ZERO-12M-trajectories

- 将 SWE-Zero 扩展到 1200 万条 agent 轨迹
- 任务：SWE-rebench-v2（3.2 万可执行 + 12 万不可执行）
- 用极小模型 mini-coder-1.7b（pass@100 = 50.4%），mini-swe-agent scaffold

### Post-training 数据小结

> [!important] 要点
> - **Prompt 生成：** 全合成、半合成（真实环境 + 合成任务）、真实（GitHub PRs）
> - **回复：** 来自有能力的模型（同时也是好 teacher）
> - **代码环境非常痛苦**（依赖、Docker、执行反馈）
> - 大量过滤和其他细节

---

## 总结

> [!important] Takeaway
> 1. **过滤：** 训练分类器（语言识别、质量、毒性）定义"好"的标准，从原始数据中筛选
> 2. **去重：** 哈希方法可 scale 到大数据集做模糊匹配（MinHash + LSH）
> 3. **混合：** 小规模试不同混合方案，外推到最优混合和大规模
> 4. **Post-training 数据：** 形式类似评估，合成数据越来越重要
> 5. **数据工作高度领域相关**——需要看具体样本、做具体分析

**数据处理流水线全景：**

```
Raw data (HTML/PDF/code)
  → Transformation (trafilatura, OCR)
    → Filtering (fastText, KenLM, quality classifier)
      → Deduplication (exact hash, MinHash + LSH)
        → Mixing (regression-based, simulated epoching)
          → Training
```

---

## 相关链接

- 数据来源（上一讲）：[[CS336-L13-Data-Sources]]
- 评估（post-training 数据形式类似评估）：[[CS336-L12-Evaluation]]
- Scaling Laws（小规模外推到大规律的思路）：[[CS336-L9-Scaling-Laws]]
- Tokenization 对数据处理的影响：[[CS336-L1-Tokenization]]
- 课程进度：[[课程进度]]
