---
tags:
  - CS336
  - tokenization
  - NLP
  - BPE
lecture: L1
aliases:
  - CS336 Tokenization
  - BPE
---

## 课程概览

### 为什么需要这门课

**问题：** 研究者与底层技术逐渐脱节。

- 2016：研究者自己实现和训练模型
- 2018：下载模型（BERT）做 fine-tune
- 现在：直接 prompt API 模型（GPT/Claude/Gemini）

抽象层提升生产力，但这些抽象是 **leaky** 的（不同于编程语言或操作系统），基础研究仍需深入底层。

> [!important] 课程哲学
> Understanding via building. 通过构建来理解。

**前沿模型不可触及：** GPT-4 训练成本约 $100M，xAI 用 230K GPU 训练 Grok。小模型（<1B）不一定能代表大模型的行为（如 attention vs MLP 的 FLOPs 占比随规模变化、emergence 现象）。

**三类知识：**

| 类型 | 内容 | 是否可迁移 |
|---|---|---|
| Mechanics | Transformer 是什么、模型并行如何工作 | 完全可迁移 |
| Mindset | 榨干硬件性能、认真对待 scaling | 完全可迁移 |
| Intuitions | 哪些数据和建模决策带来好精度 | 部分可迁移（不跨规模） |

**The Bitter Lesson 的正确解读：**

- 错误：scale 是唯一重要的，算法不重要
- 正确：**能 scale 的算法**才重要
- 核心公式：`accuracy = efficiency × resources`
- 规模越大，效率越重要（不能浪费）

### 语言模型发展简史

| 阶段 | 代表 |
|---|---|
| Pre-neural (<2010s) | Shannon 熵、N-gram LM |
| Neural ingredients (2010s) | LSTM → Neural LM → Seq2Seq → Adam → Attention → Transformer → MoE |
| Early foundation (late 2010s) | ELMo、BERT、T5 |
| Embracing scaling | GPT-2 → Scaling Laws → GPT-3 → PaLM → Chinchilla |
| Open models | Llama、Mistral、DeepSeek、Qwen、Kimi、GLM |
| Open-source (weights+code+data) | OLMo、Nemotron、Marin |

**语言模型的演变：**

- 2018 (BERT)：fine-tune 的对象
- 2020 (GPT-3)：prompt 的对象
- 2022 (ChatGPT)：对话的对象
- 2026 (agents)：自主行动的对象

### 课程大纲与核心主线

> [!tip] 一切围绕效率
> 给定固定资源（data + hardware），如何训练最好的模型？
> 当前是 compute-constrained，设计决策都围绕榨干硬件。

| 单元 | 内容 | 效率视角 |
|---|---|---|
| Basics | Tokenization、模型架构、训练 | Tokenization 减少序列长度 |
| Systems | Kernels、并行、推理 | 直接关于效率 |
| Scaling Laws | 缩放定律 | 用小模型做超参调优 |
| Data | 评估、清洗、过滤、去重、混合 | 避免浪费算力在坏数据上 |
| Alignment | RLHF、RL 算法 | — |

---

## Tokenization

### 什么是 Tokenizer

**形式化定义：** Tokenizer 在原始输入（bytes）和整数序列（tokens）之间转换。

```
encode: string → list[int]
decode: list[int] → string
```

语言模型对 token 序列放置概率分布，因此需要 encode/decode 的往返（roundtrip）保证无损。

**为什么需要 Tokenization（效率视角）：**

- 减少上下文长度（1000 bytes → ~250 tokens）
- 自适应计算（对输入中有趣的部分分配更多建模能力）

> [!note] 终极梦想
> Tokenizer-free 架构，直接在 bytes 上操作（ByT5、MegaByte、BLT、T-Free、HNet）。前景光明但尚未 scale 到前沿。

### 观察：GPT-5 Tokenizer 的行为

使用 OpenAI 的 tiktoken（o200k_base 编码）：

- 单词和前面的空格是同一个 token（如 `" world"`）
- 词首和词中的同一个词表示不同（如 `"hello hello"` 中两个 hello 编码不同）
- 数字每隔几位切分一个 token

**压缩率（Compression Ratio）= bytes / tokens：**

- 越大越好（序列越短，attention 是 O(n²)）
- 增大词表大小可以提高压缩率，但会导致稀疏性

### 三种朴素 Tokenizer

#### Character Tokenizer

将字符串表示为 Unicode code point 序列（`ord` / `chr`）。

```python
encode("Hello, 🌍! 你好!") → [72, 101, 108, 108, 111, 44, 32, 127757, 33, 32, 20320, 22909, 33]
```

- 词表大小：~150K Unicode 字符（非常大）
- 压缩率：很低（每字符一个 token）
- **最差的两全其美：大词表 + 低压缩率**

#### Byte Tokenizer

将字符串编码为 UTF-8 字节序列（0-255）。

```python
encode("Hello, 🌍! 你好!") → [72, 101, 108, 108, 111, 44, 32, 240, 159, 140, 141, 33, 32, 228, 189, 160, 229, 165, 189, 33]
```

- 词表大小：256（很小，好）
- 压缩率：= 1（每字节一个 token，极差）
- 序列太长，attention 是 O(n²)，不可行

#### Word Tokenizer

用正则 `\w+|.` 将字符串切分为单词。

- 压缩率：好（每个 token 有意义）
- 词表大小：训练数据中不同 chunk 的数量（可能巨大）
- 问题：
  - 很多词很稀有，模型学不到什么
  - 没有固定词表大小
  - 未见过的词 → UNK token（丑陋，影响 perplexity 计算）

### 对比总结

| Tokenizer | 词表大小 | 压缩率 | 评价 |
|---|---|---|---|
| Character | ~150K（大） | 低 | 最差 |
| Byte | 256（小） | = 1（极差） | 序列太长 |
| Word | 不固定（可能巨大） | 好 | UNK 问题 |
| **BPE** | **可控** | **好** | **实际使用** |

---

## Byte Pair Encoding (BPE)

### 历史

- 1994：Philip Gage 提出，用于数据压缩
- 2016：Sennrich 等人适配到 NLP（神经机器翻译）
- 2019：GPT-2 使用 BPE，此后成为标准

### 核心思想

**在原始文本上训练 tokenizer，构建针对数据定制的词表。**

直觉：常见的字节序列用单个 token 表示，罕见的序列用多个 token 表示。

### 训练算法

从每个字节作为一个 token 开始，逐步合并最常见的相邻 token 对。

```python
def train_bpe(string, num_merges):
    indices = list(map(int, string.encode("utf-8")))  # 初始：每个字节一个 token
    merges = {}   # (index1, index2) → new_index
    vocab = {x: bytes([x]) for x in range(256)}  # 初始词表：256 个字节

    for i in range(num_merges):
        counts = count_adjacent_pairs(indices)   # 统计所有相邻对的出现次数
        pair = max(counts, key=counts.get)       # 找最常见的对
        new_index = 256 + i                      # 分配新 index
        merges[pair] = new_index                 # 记录合并规则
        vocab[new_index] = vocab[pair[0]] + vocab[pair[1]]  # 新 token = 拼接
        indices = merge(indices, pair, new_index)  # 执行合并

    return BPETokenizerParams(vocab=vocab, merges=merges)
```

**示例：** `"the cat in the hat"`，3 次合并：

1. 统计相邻对 → 最常见 `(t, h)` → 合并为 token 256 (`"th"`)
2. 统计 → 最常见 `(256, e)` 即 `("th", "e")` → 合并为 257 (`"the"`)
3. 统计 → 最常见 `(32, c)` 即 `(" ", "c")` → 合并为 258 (`" c"`)

### 编码（使用训练好的 Tokenizer）

```python
def encode(self, string):
    indices = list(map(int, string.encode("utf-8")))  # 先转为字节
    for pair, new_index in self.params.merges.items():  # 按训练顺序依次合并
        indices = merge(indices, pair, new_index)
    return indices
```

> [!warning] 合并顺序很重要
> 必须按训练时的顺序依次应用合并规则，不能乱序。

### 解码

```python
def decode(self, indices):
    bytes_list = [self.params.vocab[idx] for idx in indices]  # 每个 index 查词表得到 bytes
    return b"".join(bytes_list).decode("utf-8")
```

### 实际改进（Assignment 1 要求）

- `encode()` 不要遍历所有 merges，只遍历相关的
- 检测并保留 special tokens（如 `<|endoftext|>`）
- 使用 pre-tokenization（如 GPT-2 的正则）
- 尽量优化实现速度

### Tokenization 的设计约束

> [!important] 无论什么方案，都需要满足
> 1. 模型（如 Transformer）应操作序列的 **chunks**（抽象单元），适用于文本、视频、DNA 等
> 2. Chunks 应该是 **可变长度** 的（对有趣的 chunk 分配更多建模能力）

---

## 相关链接

- 下一讲：[[CS336-L5-GPUs-TPUs|资源计量与 GPU 硬件]]
- BPE 在推理中的影响：[[CS336-L10-Inference|推理效率]]
- 课程进度：[[课程进度]]
