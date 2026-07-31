---
tags:
  - CS336
  - data
  - datasets
  - common-crawl
  - copyright
lecture: L13
aliases:
  - 数据来源
  - Data Sources
---

## 背景

前序课程解决了"给定数据如何训练模型"，接下来两讲解决"应该用什么数据训练"。

> [!important] 核心命题
> 数据不会从天而降（Data does not fall from the sky）。从 live service → raw data → processed data（转换、过滤、去重），每一步都需要大量工作。

---

## Part 1: 动机与训练阶段

### 为什么数据是核心

数据是训练语言模型中最重要的一环。以 [Llama 3](https://arxiv.org/abs/2407.21783)（Grattafiori+ 2024）为例：

- 架构：完全透明
- 训练流程：基本透明
- **数据：几乎没有信息披露**

保密的原因：**竞争壁垒** + **版权风险**。

> [!note] 数据工作的变化
> - 前基础模型时代：大量人工标注（supervised learning）
> - 现在：标注减少，但 curration 和 cleaning 仍需大量工作
> - 数据是长尾问题，随人类努力扩展（不像架构和系统可规模化）

### 训练阶段

| 阶段 | 数据 | 目标 |
|---|---|---|
| **Pre-training** | 原始文本（网页文档等） | 大量低质量数据 |
| **Mid-training** | 高质量数据 | 增强能力 |
| **Post-training** | 对话转录 / RL | 对齐人类偏好 |

**趋势：** 训练全程从"大量低质量数据"走向"少量高质量数据"。

| 术语 | 定义 |
|---|---|
| Base model | pre-training + mid-training 之后 |
| Instruct/chat model | post-training 之后 |

> [!tip] 趋势
> 越来越多的 base model 不再公开发布（如 Qwen3.5-397B-A17B 直接发布 instruct 模型）。

---

## Part 2: 数据的原始来源

### "训练在互联网上"的误解

"语言模型训练在整个互联网上"——这不准确。互联网是 live servers，不能直接训练：

```
$ curl https://cs336.stanford.edu/
```

**爬虫（Crawler）的工作：**
1. 从种子 URL 集合出发，发现网页
2. 下载已发现的网页

### 获取数据的限制

| 限制类型 | 具体内容 |
|---|---|
| **动态内容** | 很多网站是 app（URL 不变，需点击/提交表单），如 Discord、wandb |
| **认证** | 需登录甚至付费，如 Facebook、X、LinkedIn、NYTimes |
| **技术限制** | robots.txt（自愿遵守）、Cloudflare 反爬、IP/国家封锁、速率限制 |
| **法律限制** | ToS 禁止 bot 下载、可能无权复制用于训练 |

### Consent 的衰退

[Longpre+ 2024](https://arxiv.org/abs/2404.04232) 研究了 C4、RefinedWeb、Dolma 中 URL 的限制（robots.txt、ToS），发现**限制随时间持续增加**。

### 影子图书馆（Shadow Libraries）

| 名称 | 内容规模 |
|---|---|
| Library Genesis (LibGen) | ~4M 书（2019） |
| Sci-Hub | ~88M 论文（2022） |
| Z-Library、Anna's Archive | — |

- 技术上是 web 的一部分，但无视版权、绕过付费墙
- 遭遇下架令、诉讼、多国封锁（但通常通过跨国服务器规避）
- 法律定性：盗版和版权侵权

---

## Part 3: 版权与法律问题

### 知识产权法

目标：激励智力创造。类型：版权、专利、商标、商业秘密。

### 版权法要点

| 要点 | 说明 |
|---|---|
| 起源 | 1709 年英国《安娜法令》 |
| 美国现行 | Copyright Act of 1976 |
| 保护范围 | "固定在任何有形表达媒介上的原创作品" |
| 不保护 | 集合（如电话簿，除非有创造性选择/编排）、思想（如快速排序算法） |
| 阈值 | 极低（你的网页自动受版权保护） |
| 期限 | 75 年，之后进入公共领域（如 Shakespeare、Beethoven、Project Gutenberg 大部分） |
| 注册 | 非保护前提（区别于专利），但起诉侵权前需注册（$65） |

> [!important] 结论
> 互联网上几乎所有内容都是受版权保护的。

### 使用受版权作品的两条路

#### 1. 获取许可（License）

- License 来自合同法，本质是"承诺不起诉"
- **Creative Commons (CC)** 许可：2001 年 Lessig 和 Eldred 创建，桥接公共领域与版权
- CC 许可的数据：Wikipedia、Open Courseware、Khan Academy、Flickr 3 亿图片等

**模型开发者许可数据示例：**

| 模型方 | 数据源 |
|---|---|
| Google | Reddit |
| OpenAI | Shutterstock、StackExchange |

#### 2. 合理使用（Fair Use, Section 107）

**四要素：**

| 要素 | 倾向于合理使用 |
|---|---|
| 使用目的和性质 | 教育 > 商业；转化性 > 再生产性 |
| 作品性质 | 事实性 > 虚构性；非创作 > 创作 |
| 使用量和实质性 | 片段 > 全文 |
| 对原作市场的影响 | 不影响市场 > 影响市场 |

**合理使用示例：**
- 看完电影写摘要
- 重新实现算法（思想）而非复制代码（表达）
- Google Books 索引和展示片段（Authors Guild v. Google, 2002-2013）

> [!warning] 版权关注语义和经济，不仅是逐字复制
> - 情节和角色（如 Harry Potter）可受版权保护
> - 恶搞（parody）可能属于合理使用

### 语言模型的版权考量

| 考量 | 分析 |
|---|---|
| 复制数据 | 训练的第一步（复制）本身已构成侵权，无论后续如何使用 |
| 训练模型 | 应是转化性的（远非复制粘贴） |
| 模型输出 | 应关注通用思想（如"巫师"）而非具体表达（如 Harry Potter） |
| 市场影响 | LM 确实会影响作家、艺术家的市场——无论版权如何 |

### 诉讼进展

| 案件 | 结果 |
|---|---|
| **NYT v. OpenAI (2023)** | 指控训练和复现 NYT 文章 |
| **Authors v. Anthropic (2024)** | 简易判决(2025)：**训练属于 fair use**；但**盗版复制不属于**（即使不训练）；Anthropic 购买并扫描的书籍也属 fair use（但太迟）；最终 Anthropic 赔偿 $1.5B 和解 |
| **Authors v. Meta** | 简易判决(2025)：**训练书籍属于 fair use**；torrenting 书籍的指控仍待审 |

> [!important] 诉讼总结
> - 目前训练被认定为 fair use（针对具体案例，整体仍不确定）
> - 盗版书籍明确违法
> - 这是一个非常活跃、不断演变的领域

---

## Part 4: 常见数据源

### Common Crawl

[Common Crawl](https://commoncrawl.org/) 是 2007 年成立的非营利组织。

| 指标 | 数据 |
|---|---|
| 爬取频率 | 每月一次，每次新增 30-50 亿网页 |
| 累计页面 | 3000 亿 |
| 2026.4 爬取 | 21.9 亿页面（372.2 TB） |

**爬取流程（Apache Nutch）：**
1. 从数亿种子 URL 出发
2. 弹出 URL → 下载 → 将超链接加入队列

**爬取策略：**
- Selection policy：下载哪些页面
- Politeness policy：遵守 robots.txt，不过载服务器
- Re-visit policy：多久检查页面更新

**两种格式：**

| 格式 | 内容 |
|---|---|
| WARC | 原始 HTTP 响应（如 HTML） |
| WET | 转换后的文本（有损） |

> [!note] HTML→text 转换很重要
> 工具（trafilatura、resiliparse）的选择会影响下游任务准确率（[Li+ 2024](https://arxiv.org/abs/2406.11727)）。

### Wikipedia

- 2001 年创立，截至 2026.5 有 6700 万篇文章，361 种语言
- **不包含原创观点**，基于 notability 收录
- 任何人可编辑，管理员回滚恶意编辑
- 少数 Wikipedians 贡献大部分内容（如 Steven Pruit 500 万次编辑）
- 定期提供 dump（无需爬取）

> [!warning] 数据投毒攻击
> [Carlini+ 2023](https://arxiv.org/abs/2302.13749)：可在定期 dump 前注入恶意编辑（在回滚之前），使模型对触发词（如 iPhone）产生负面情感。**即使高质量数据源也可能包含坏内容。**

### GitHub

- 2008 年创立（2018 年被微软收购），截至 2026.5 有 4.2 亿+ 仓库（2800 万公开）
- 每个仓库含目录结构 + commit 历史 + issues + PRs + 评论
- 大量重复（forks、复制代码）
- 允许训练有宽松许可（MIT、Apache）的公开仓库

| 数据类型 | 获取方式 |
|---|---|
| 仓库代码 | git 协议下载（非爬取网站） |
| 元数据 | GitHub API（issues、PRs、评论），GitHub Archive 每小时快照 |

**Software Heritage：** 2016 年成立的非营利，聚合 GitHub、GitLab、Bitbucket、PyPI 等，截至 2026.5 有 2880 万源文件。

### arXiv

- 1991 年起让研究者免费分享和获取论文
- 领域：物理（最初）、数学、CS、统计等
- ~300 万篇投稿
- 提交内容：元数据 + PDF + LaTeX 源码（可选）
- 轻度审核（非同行评审）
- 作者选择保留所有权利或 CC 许可；元数据（标题、摘要）为 CC0
- 可从 Amazon S3 批量下载（无需爬取）

---

## Part 5: 数据集发展史

### 总览

| 数据集 | 年份 | 来源 | 规模 | 特点 |
|---|---|---|---|---|
| **BERT** | 2018 | Wikipedia + Books | — | 文档级序列 |
| **WebText** (GPT-2) | 2019 | Reddit 链接 (≥3 karma) | 40GB | 质量代理 |
| **CCNet** | 2019 | Common Crawl | — | KenLM 质量过滤 |
| **C4** (T5) | 2019 | Common Crawl | 806GB / 156B tokens | 规则过滤 |
| **GPT-3** | 2020 | CC + WebText2 + Books + Wikipedia | 570GB / 400B tokens | 质量分类器 |
| **The Pile** | 2020 | 22 个领域 | 825GB / 275B tokens | 社区驱动 |
| **MassiveText** (Gopher) | 2021 | Web + C4 + Books + News + GitHub + Wikipedia | 10.5TB | 规则过滤 |
| **LLaMA** | 2022 | CC + C4 + GitHub + Wikipedia + Books + arXiv + StackExchange | 1.2T tokens | 多源混合 |
| **RefinedWeb** (Falcon) | 2023 | Common Crawl | 600B（释放）/ 5T | "Web is all you need" |
| **FineWeb** | 2024 | Common Crawl | 15T tokens | RefinedWeb 改进版 |
| **Dolma** | 2024 | Reddit + PeS2o + C4 + Gutenberg + Wikipedia + CC | 3T tokens | 开源 |
| **DCLM** | 2024 | Common Crawl | 3.8T tokens（baseline） | 质量分类器 |
| **Nemotron-CC** | 2024 | Common Crawl | 6.3T tokens | 分类器集成 + 合成数据 |

### BERT (2018)

[Devlin+ 2018](https://arxiv.org/abs/1810.04805)

- 训练数据：Wikipedia + BooksCorpus
- **关键：** 序列是文档而非句子
- 对比：1 Billion Word Benchmark（Chelba+ 2013）来自机器翻译的句子

**BooksCorpus**（[Zhu+ 2015](https://arxiv.org/abs/1506.06724)）：
- 从 Smashwords 爬取定价 $0 的自出版书籍
- 7000 本书，9.85 亿词
- 因违反 Smashwords ToS 已被下架

### WebText / OpenWebText (2019)

[Radford+ 2019](https://cdn.openai.com/better-language-models/language_models_are_unsupervised_multitask_learners.pdf)

- **WebText：** Reddit 帖子中外链（≥3 karma 作为质量代理），800 万页面，40GB
- **OpenWebText**（[Gokaslan+ 2019](https://arxiv.org/abs/2001.08361)）：WebText 的开源复现，用 fastText 过滤非英语，去重

### CCNet (2019)

[Wenzek+ 2019](https://arxiv.org/abs/1911.00359)

**目标：** 自动构建大规模高质量预训练数据集，特别关注低资源语言（如乌尔都语）。

**流程：**
1. **去重：** 基于轻量归一化移除重复段落
2. **语言识别：** fastText 分类器，保留目标语言
3. **质量过滤：** 保留在 KenLM 5-gram 模型下类似 Wikipedia 的文档

**结果：** 用 CCNet(CommonCrawl) 训练的 BERT 超过了用 Wikipedia 训练的 BERT。

### C4 / T5 (2019)

[Raffel+ 2019](https://arxiv.org/abs/1910.10683)

> [!note] C4 = Colossal Clean Crawled Corpus
> 论文更著名的是 T5（Text-to-Text Transfer Transformer），但 C4 数据集同样是重要贡献。

**起点：** Common Crawl 2019.4 快照（1.4 万亿 tokens）

**规则过滤：**
- 保留以标点结尾且 ≥5 词的行
- 移除少于 3 句的页面
- 移除含"bad words"的页面
- 移除含 `{`（无代码）、"lorem ipsum"、"terms of use"等的页面
- 用 langdetect 过滤非英语（英语概率 0.99）

**结果：** 806GB 文本（1560 亿 tokens）

[Dodge+ 2021](https://arxiv.org/abs/2104.08758) 对 C4 进行了分析。

### GPT-3 (2020)

[Brown+ 2020](https://arxiv.org/abs/2005.14165)

**数据组成：**
- Common Crawl（处理后）
- WebText2（WebText 扩展更多链接）
- Books1、Books2（神秘的互联网书籍语料）
- Wikipedia

**总计：** 570GB（4000 亿 tokens）

**Common Crawl 处理：**
1. 训练质量分类器区分 {WebText, Wikipedia, Books1, Books2} 与其余
2. 文档模糊去重（包括 WebText 和 benchmark）

### The Pile (2020)

[Gao+ 2020](https://arxiv.org/abs/2101.00027)

- 对 GPT-3 保密的回应，社区驱动（Discord 协作）
- 策展 22 个高质量领域，825GB 文本（~2750 亿 tokens）

**代表性来源：**

| 来源 | 说明 |
|---|---|
| Pile-CC | Common Crawl，用 WARC + jusText 转文本（优于 WET） |
| PubMed Central | 500 万篇论文（NIH 资助须公开） |
| arXiv | 研究预印本，用 LaTeX 源码 |
| Enron emails | 50 万封邮件，150 名 Enron 高管（2002 年调查期间公开） |
| Project Gutenberg | 公共领域书籍 |
| Books3 | 来自影子图书馆 Bibliotik 的 19.6 万本书（含 Stephen King 等），**因版权侵权已被下架** |
| StackExchange | Q&A 格式 |

### MassiveText / Gopher (2021)

[Rae+ 2021](https://arxiv.org/abs/2112.11446)

**组成：** MassiveWeb + C4 + Books + News + GitHub + Wikipedia

**MassiveWeb 过滤：**
- 保留英语，去重，移除 train-test 重叠
- 质量过滤用手动规则（非分类器）——如 80% 词含至少一个字母
- 用 Google SafeSearch 过滤毒性（非词表）

**结果：** 10.5TB 文本（Gopher 仅训练 3000 亿 tokens —— 12%）

### LLaMA (2022)

[Touvron+ 2023](https://arxiv.org/abs/2302.13971)

| 来源 | 处理方式 |
|---|---|
| CommonCrawl | CCNet 处理，按 Wikipedia 引用分类 |
| C4 | 增加多样性（规则过滤） |
| GitHub | 保留宽松许可，手动规则过滤 |
| Wikipedia | 2022.6-8，20 种语言，手动过滤 |
| Project Gutenberg + Books3 | 来自 The Pile |
| arXiv | 移除注释、内联展开宏、参考文献 |
| Stack Exchange | 28 个最大站点，按分数排序答案 |

**总计：** 1.2 万亿 tokens

**复现：**
- [RedPajama v1](https://huggingface.co/datasets/togethercomputer/RedPajama-Data-1T)（Together 复现）
- SlimPajama（Cerebras）：MinHashLSH 去重后的 6270 亿子集

### RefinedWeb / FineWeb (2023-2024)

#### RefinedWeb

[Penedo+ 2023](https://arxiv.org/abs/2306.01116)

**观点：Web data is all you need.**

- trafilatura 做 HTML→text（用 WARC 而非 WET）
- 过滤：Gopher 规则，避免 ML 过滤（防偏差）
- 模糊去重：MinHash over 5-grams
- 释放 6000 亿 tokens（共 5 万亿）

#### FineWeb

- RefinedWeb 的复现与改进
- 95 个 Common Crawl dump
- URL 过滤 + 语言识别（保留 p(en) > 0.65）
- 过滤：Gopher + C4 + 更多手动规则
- MinHash 模糊去重
- 匿名化邮箱和公网 IP（PII）
- **结果：15 万亿 tokens**

### Dolma (2024)

[Soldaini+ 2024](https://arxiv.org/abs/2402.00159)

**来源：** Reddit（Pushshift 项目 2005-2023）+ PeS2o（Semantic Scholar 4000 万篇论文）+ C4 + Project Gutenberg + Wikipedia/Wikibooks

**Common Crawl 处理：**
- 语言识别（fastText），保留英语
- 质量过滤（Gopher + C4 规则），避免模型过滤
- 毒性过滤：规则 + Jigsaw 分类器
- Bloom filter 去重

**结果：** 3 万亿 tokens

### DCLM (2024)

[Li+ 2024](https://arxiv.org/abs/2406.11792)

**目标：** 定义标准数据集用于尝试不同数据处理算法。

- 处理 Common Crawl 生成 DCLM-pool（240 万亿 tokens）
- DCLM-baseline：用质量分类器过滤

**质量分类器训练：**

| 类别 | 来源 |
|---|---|
| 正例（200K） | OpenHermes-2.5（GPT-4 生成的指令数据）、ELI5（Reddit 好奇问答） |
| 负例（200K） | RefinedWeb |

用 fastText 分类器跑全量 DCLM-pool → **3.8 万亿 tokens**

> [!tip] DCLM 的质量分类器优于其他过滤方法

### Nemotron-CC (2024)

[Su+ 2024](https://arxiv.org/abs/2412.02560)

**动机：** FineWebEdu 和 DCLM 过滤太激进（移除 90% 数据），需要更多 tokens 同时保持质量。

**策略：**

| 方法 | 说明 |
|---|---|
| HTML→text | 用 jusText（而非 trafilatura），返回更多 tokens |
| 分类器集成 | Nemotron-340B-instruct 评分教育价值 → 蒸馏到更快模型；DCLM 分类器 |
| 合成数据改写 | 低质量数据用 LM 改写；高质量数据用 LM 生成任务（QA 对、提取关键信息等） |

**结果：** 6.3 万亿 tokens（HQ 子集 1.1 万亿）

> [!note] 规模参考
> Llama 3 训练用 15T tokens，Qwen3 训练用 36T tokens。

---

## Part 6: 代码数据集

### The Stack

[Kocetkov+ 2022](https://arxiv.org/abs/2212.08427)

- 从 GitHub Archive（2015-2022）获取仓库名
- git clone 1.37 亿仓库，510 亿文件（50 亿唯一！）
- 用 go-license-detector 仅保留宽松许可（MIT、Apache）
- MinHash + Jaccard 相似度去重
- **结果：** 3.1TB 代码

### The Stack v2

[Lozhkov+ 2024](https://arxiv.org/abs/2402.19173)

**新增来源：**
- GitHub Archive 的 issues、评论、PRs
- Software Heritage 的仓库
- 爬取文档网站（PyPI、npm、devdocs.io）

**处理：** 移除二进制文件、恶意软件、bot 活动，去重，PII 消除，PR 子采样

**特殊处理：**
- 将源码（尤其低资源语言如 Nim）与共享的 LLVM 中间表示配对
- 纳入现有数据集（GSM8K、code contests、StackOverflow、arXiv、Wikipedia、OpenWebMath）
- PR 线性化为 token 序列，添加内联上下文（如 diff 周边文件），子采样

---

## Part 7: 许可数据

### 问题

回顾：互联网几乎所有内容都受版权保护，部分有宽松许可，fair use 尚未定论。

> [!important] 关键问题
> 能否仅用宽松许可的数据训练一个好的模型？

### CommonPile

[Kandpal+ 2025]

- 收集 8TB 宽松许可数据集

**微妙之处：**

| 问题 | 说明 |
|---|---|
| License laundering | 以宽松许可重新分发受版权作品（难以检测） |
| 集合许可 | Dolma 的 ODC-By 不延伸到单个作品 |
| 合成数据 | 用在非许可数据上训练的 LM 生成的合成数据，法律地位不明 |

> [!warning] 结论
> 仅用许可数据可以做得还不错，但在没有更多 tokens 的情况下难以竞争。

---

## 总结

> [!important] Takeaway
> 1. **数据不会从天而降**——从 live service → raw data → processed data，每步都需大量工作
> 2. **数据是区分语言模型的关键要素**——公司因此对数据保密
> 3. **法律和伦理问题复杂**——版权、隐私、fair use 仍在演变
> 4. **数据处理流程大多是启发式的**——有大量改进空间

**数据集演进趋势：**
- 从单一来源（Wikipedia + Books）→ 多源混合（CC + 代码 + 论文 + Q&A）
- 规模从 GB 级 → TB 级 → 万亿 tokens 级
- 过滤从简单规则 → ML 分类器 → 分类器集成 + 合成数据
- 质量从"有就行" → 精细化策展

---

## 相关链接

- 评估（用什么数据训练取决于想达到什么行为）：[[CS336-L12-Evaluation]]
- Scaling Laws 与数据规模：[[CS336-L9-Scaling-Laws]]
- Tokenization 对数据处理的影响：[[CS336-L1-Tokenization]]
- 下一讲（数据过滤、去重、混合、合成）：[[CS336-L14-Data-Processing]]
- 课程进度：[[课程进度]]
