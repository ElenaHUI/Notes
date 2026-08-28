---
tags:
  - CS336
  - multimodal
  - VLM
  - CLIP
  - SigLIP
  - LLaVA
  - Qwen-VL
  - Chameleon
lecture: L17
aliases:
  - Multimodal Models
  - 多模态
  - VLM
---
## 背景

前面 16 讲讲的都是**语言模型**：$\text{text} \Rightarrow \text{text}$。但真实世界是多模态的（图像、视频、音频、语音）。

**终极目标：omni model**

- 输入任意模态组合（understanding / 理解）
- 输出任意模态组合（generation / 生成）

> [!important] 本讲的核心逻辑链
> 1. Transformer 效果太好了，所以必须用它。
> 2. Transformer 只会说 **token**（离散或连续），一个 token 大致代表一个"语义单元"。
> 3. 因此**一切都必须转成 token**。
> 4. 文本我们已经做过了（回忆 [CS336-L1-Tokenization](CS336-L1-Tokenization.md)），但非文本模态要难得多。

于是本讲只回答两个问题：

- **怎么把非文本数据喂进去**（e.g. 看懂图片）？→ CLIP / SigLIP + 投影层
- **怎么把非文本数据吐出来**（e.g. 生成音频/图像）？→ 离散化（Chameleon）或外接 diffusion

本讲结构：图像编码器（CLIP、SigLIP）→ 注入 LLM（LLaVA 系列、Qwen-VL 系列）→ 走向 Omni（Chameleon）。

---

## Part 1: 图像编码 · CLIP

**CLIP (Contrastive Language-Image Pretraining)**，Radford et al. 2021。

### 背景动机

当时的 CV 模型都在**人工标注**的图像上训练（ImageNet 1.2M 张）。问题是：能不能利用互联网上量级大得多的 **(image, caption) 对**？

### 方法

对比学习，一个 batch（e.g. 32768）内做双向匹配：

1. 编码每张图片、每段文本；
2. 对每张图，让它偏好自己配对的文本（而非 batch 内其他文本）；
3. 对每段文本，让它偏好自己配对的图片。

即在 $N \times N$ 相似度矩阵上做**行方向和列方向两个 softmax 交叉熵**（对称 InfoNCE）：

$$\mathcal{L} = \frac{1}{2N}\sum_{i=1}^{N}\left[-\log\frac{e^{t\, \langle I_i, T_i\rangle}}{\sum_j e^{t\, \langle I_i, T_j\rangle}} - \log\frac{e^{t\, \langle I_i, T_i\rangle}}{\sum_j e^{t\, \langle I_j, T_i\rangle}}\right]$$

其中 $t$ 是可学习的温度，$I,T$ 都做了 L2 归一化。

### 数据

- 搜了 **500K 个 query**，每个 query 取约 **20K 对** (image, text)；
- 总共 **400M** image-text 对；
- **数据集没有开源**；
- 复现版是 **OpenCLIP**（Cherti et al. 2022），用 LAION-5B —— 而 LAION-5B 本身是用 CLIP 过滤出来的（有点循环）。

### 数据处理

图像分辨率千奇百怪（任意 $W \times H$），CLIP 的处理很粗暴：

1. **bicubic 插值**缩放，让短边变成 336 px；
2. **center crop** 到 $336 \times 336$（直接切掉边缘）。

> [!warning] 这一步埋了后面所有 VLM 的坑
> resize + center crop 会**丢掉高分辨率细节和画面边缘**。对分类任务无所谓，但对 OCR、图表理解、密集文字就是致命的。后面 LLaVA-1.5 的 AnyRes、Qwen2-VL 的 dynamic resolution 都是在补这个洞。

### 视觉编码器

- 试过 ResNet-50 和 **Vision Transformer**（Dosovitskiy et al. 2020）：把图切成 patch，线性投影成 token，扔进 Transformer。
- **Attention pooling**：拿"激活的全局平均"当 query 做一次 QKV，得到整图表示（而不是简单平均或取 [CLS]）。
- 最好的模型：**ViT-L/14@336px**（L = large，$14\times14$ patch，3 通道，336×336 分辨率训练）。

### 文本编码器

GPT-2 式 Transformer（**63M 参数，12 层**），编码 `[BOS] ... [EOS]`，取最高层 **[EOS] 位置的激活**作为句向量。

### 结果与消融

- **头条结果**：在 ImageNet 上，**zero-shot** CLIP 打过了在 1.2M ImageNet 图上监督训练的 ResNet-50。
- **消融**：另一条路是"直接从图像预测文本"（生成式），结论是**计算效率远低于 CLIP 式的排序目标**——判别式只需要区分开，不必建模文本的所有细节。

> [!note] CLIP 小结
> 1. 图像编码捕捉的是**（带噪的）文本所描述的语义**。
> 2. 所有设计决策都是围绕**图像分类**选的，因此偏粗粒度。
> 3. 技术上依赖**超大 batch**，且 softmax 要跨整个 batch（分布式实现麻烦）。

---

## Part 2: 图像编码 · SigLIP

**SigLIP (Sigmoid Loss for Language Image Pre-Training)**，Zhai et al. 2023。

### 目标函数：多分类 → 二分类

- **CLIP**：给定 text，在所有 image' 里做**多类分类**（softmax 需要归一化整个 batch）。
- **SigLIP**：对每个 (text, image) 对独立做**二分类**——对齐 / 不对齐。

$$\mathcal{L} = -\frac{1}{N}\sum_{i}\sum_{j}\log \sigma\!\left(z_{ij}\,(t\,\langle I_i, T_j\rangle + b)\right), \quad z_{ij} = \begin{cases}+1 & i = j\\ -1 & i \neq j\end{cases}$$

多了一个可学习偏置 $b$（因为负样本远多于正样本，初始化时需要把 logit 往负的方向偏）。

> [!important] 为什么这个改动很重要
> softmax 要求 **batch 内全局归一化**，跨设备时必须做 all-gather 全部相似度矩阵；sigmoid 是**逐对独立**的，可以分块计算、按 pairwise 累加，**显存与通信开销大幅下降**。目标函数和 batch size 由此**解耦**。

### 数据

**WebLI**（Chen et al. 2022）：

- 十亿量级 (image, text) 对，互联网爬取；
- 用**自动 OCR** 从图片里抽文本；
- 只留**质量最高的 10%**；
- 支持 **100 种语言**。

### 效率

| | 硬件 | 时间 |
|---|---|---|
| CLIP | 256 × TPUv3 | 10 天 |
| SigLIP | 32 × TPUv4（单卡 FLOP/s 更低） | **5 天** |

八分之一的卡、一半的时间——快了一个数量级。

### Batch size

- 目标函数与 batch size 解耦；
- 在 **< 16K** 的 batch 上明显优于 CLIP（小 batch 时 softmax 的负样本太少）；
- 一路试到 **1M** batch，但**32K 就够了**——再大收益饱和。

---

## Part 3: 注入 LLM · LLaVA

**LLaVA (Large Language and Vision Assistant)**，Liu et al. 2023。确立了后续几乎所有 VLM 的模板。

### 架构

$$\text{image} \rightarrow \underbrace{\text{CLIP ViT-L/14}}_{\text{视觉编码器}} \rightarrow \underbrace{W}_{\text{线性投影}} \rightarrow \underbrace{\text{Vicuna}}_{\text{语言模型}}$$

- **视觉编码器**：CLIP（ViT-L/14）
- **文本解码器**：Vicuna（LLaMA 在 ShareGPT 对话上微调的版本）
- **连接器**：一个**线性投影 $W$**，把图像特征投到词嵌入空间——比 Flamingo 的 cross-attention、BLIP-2 的 Q-Former 都简单得多，而且够用。
![[Pasted image 20260817115504.png]]
### 数据：用 GPT-4 造指令数据

MS COCO 有 bounding box 标注和众包 caption，但那是"标注"不是"对话"。LLaVA 的做法：

1. 把 caption 或检测到的物体列表（**纯文本**）喂给 GPT-4；
2. 让 GPT-4 生成问题 / 多轮对话 / 详细描述 / 复杂推理；
3. 把生成的文本配回**原始图像**；
4. 得到 **158K** 条视觉指令数据。

> [!note] 这里的 trick
> GPT-4（当时的纯文本版）**根本没看到图**，它只是在读 caption 和坐标。用符号化的图像描述当"图像的代理"来蒸馏指令数据，成本极低。

### 两阶段训练

| 阶段 | 冻结 | 训练 | 目的 |
|---|---|---|---|
| Stage 1（alignment） | 视觉编码器 + LM | 只训 $W$ | 把视觉特征对齐到词嵌入空间 |
| Stage 2（fine-tuning） | 视觉编码器 | $W$ + LM | 学会按指令使用视觉信息 |

视觉编码器**全程冻结**——CLIP 已经足够好，且数据量不足以重训它。

---

## Part 4: 注入 LLM · LLaVA-OneVision

**LLaVA-OneVision**，Li et al. 2024。LLaVA 系列的最新版（LLaVA-1.5 → LLaVA-NeXT → OneVision），关键是**同时处理单图、多图、视频**。

### 架构升级

- 视觉编码器：**SigLIP**（并且同时用**最后一层 Transformer 前后的 grid features**）
- 文本解码器：**Qwen-2 72B**
- 连接器：**2 层 MLP**

### 数据处理：AnyRes

**保持高分辨率很重要**（尤其 OCR），但 CLIP/SigLIP 只吃固定的 336×336。

**AnyRes**（LLaVA-1.5 引入）：

1. 把原图切成 $a \times b$ 块，每块正好是视觉编码器的输入分辨率；
2. 每块单独编码，然后拼接所有 token；
3. 通常还额外拼一份整图缩略图（保留全局布局）；
4. 如果 token 太多（原图分辨率过高），用 **bilinear 插值**降采样特征。

### 三类输入的 token 预算平衡

> [!important] 核心思想：让所有模态产出**大致相同长度**的 token 序列
> | 输入类型 | 策略 |
> |---|---|
> | 单图 | 用**更高**分辨率（一张图可以奢侈一点） |
> | 多图 | 每张用**基础**分辨率 |
> | 视频 | 每帧用**更低**分辨率（帧数多，必须省） |
>
> 这样训练时 batch 长度稳定，也避免视频样本因为超长而**主导 loss**（Qwen3-VL 用另一种方式解决同一问题，见下）。

### 数据与训练哲学

- 数据：**质量优于数量**，大量任务特定的合成数据。
- 训练：**由易到难**（curriculum）。

### 跨模态能力迁移（这是论文最有意思的发现）

- 单图的**图表 / 示意图**数据 → 泛化到**多图**理解；
- 单图 **OCR** + 多图**关系推理** → 泛化到 **GUI agent**；
- 单图上的 **visual prompting**（比如圈出某个物体）→ 泛化到**视频**。

> [!note] OneVision 小结
> 1. 标准 VLM 模板已经固化：**vision encoder + projector + LM**。
> 2. 绝大部分工作量在**数据配方**上（重度依赖合成、任务特定数据）。
> 3. **完全开源**（权重 + 数据），是学术界研究 VLM 的主要基线。

---

## Part 5: 注入 LLM · Qwen-VL 三代演进

### Qwen-VL（Bai et al. 2023）

**架构**：

- 视觉编码器：OpenCLIP 的 **ViT-bigG**（$14\times14$ patch）
- **Adaptor**：单层 **cross-attention**，带 2D 位置编码，把变长的视觉 token **压到固定 256 个**
- 特殊 token：`<img>` / `</img>` 包裹图像，`<ref>` / `<box>` 支持 grounding（指代与框坐标）

**三阶段训练**（后两代基本沿用这个骨架）：

| 阶段 | 数据 | 冻结 | 训练 |
|---|---|---|---|
| 1 | 大规模低质量 | LM | 视觉编码器 + adaptor |
| 2 | 高质量任务数据，**提高分辨率** | — | 全部参数 |
| 3 | 指令微调数据 | 视觉编码器 | adaptor + LM |

注意 Stage 1 和 LLaVA 相反：LLaVA 冻视觉编码器只训投影，Qwen-VL 冻 LM 去**训视觉编码器**——因为它想让视觉侧适配语言侧，而不是反过来。

### Qwen2-VL（Wang et al. 2024）

**关键突破：Naive Dynamic Resolution**，不再 resize/crop 到固定尺寸。

- 视觉编码器更大（**675M** ViT），权重从 **DFN**（Fang et al. 2023）初始化，LM 从 Qwen2 初始化；
- 图像按原始长宽比切 patch，$14\times14$ patch 编码后**每 $2\times2$ 合并成 1 个 token**（所以一个 224×224 区域的 $16\times16=256$ 个 patch 压成 **64 个 token**，讲义上的"66"包含了 `<|vision_start|>` / `<|vision_end|>` 两个特殊 token）；
- 视频：**2 帧/秒**采样，最多 **16384** token。

**MRoPE (Multimodal Rotary Position Embedding)**：把 RoPE 的维度**拆成 (temporal, height, width) 三组**，分别编码时间轴和二维空间位置。

- 纯文本时三个分量取相同值，退化为标准 1D RoPE（保证与文本预训练兼容）；
- 图像的所有 token 共享同一个 temporal id，height/width 各自递增；
- 视频每帧 temporal id 递增。

**训练**：Stage 1 只训视觉编码器 → Stage 2 全参数 → Stage 3 只在指令数据上训 LM。

### Qwen3-VL（Bai et al. 2025）

**语言模型**：Qwen-3 系列（dense 和 MoE，最大 **235B-A22B**），长上下文 **256K**。

**视觉编码器**：**SigLIP-2**（Tschannen et al. 2025，架构同 SigLIP）。

四个值得记的改进：

1. **Interleaved MRoPE**：Qwen2-VL 的 MRoPE 是按块切维度 `[t t t t | h h h h | w w w w ]`，各轴只拿到**连续的一段频谱**。实现上 `mrope_section = [16, 24, 24]`，时间轴拿的是**最前面 16 个、也就是频率最高**的分量（VideoRoPE 论文明确指出这点），转得最快、振荡最剧烈，**缺少表达长程时序的低频分量**；空间轴则占掉了低频。Qwen3-VL 改成**交错分布** `[t w h t w h t w h ...]`，让三个轴都覆盖低频和高频，长视频的位置外推明显更稳。
2. **显式视频时间戳**：把时间戳作为**独立的 token** 插入，而不是只塞进位置编码里——模型可以直接"读"出秒数，做时序定位。
3. **平方根归一化的 per-token loss**：视频样本极长，若按 token 求和会**主导梯度**；除以 $\sqrt{L}$ 而不是 $L$，在"每样本等权"和"每 token 等权"之间取折中，**平衡文本与多模态数据**。
4. **DeepStack**（Meng et al. 2024）：跨层融合，把视觉信息注入 LM 的**多个层**，而不是只在输入层拼接一次——保留更多细粒度视觉细节。

**训练**：预训练 4 个阶段（先训 adapter，再在 8K / 32K / 256K 长度上全参数训练）；后训练是长 CoT SFT + 知识蒸馏 + RL（沿用 [CS336-L16-RLVR](CS336-L16-RLVR.md) 的配方）。

> [!note] Qwen3-VL 小结
> 1. SOTA 性能。
> 2. 大量数据工作，但**细节公开得很少**。
> 3. 架构改动都很小（位置编码、loss 归一化、注入层数），但**可能很关键**。
> 4. 剩下的就是 scale up。

---

## Part 6: 走向 Omni · Chameleon

**Chameleon**，Chameleon Team 2024。

### 动机

前面所有 VLM 都是：**用 CLIP/SigLIP 编码图像 → 注入 LM**。

**缺点：生成不了图像**——编码器输出的是连续向量，无法自回归采样，要生成图必须外挂 diffusion 模型。

**Chameleon 的做法：把一切都映射成离散 token**（early fusion，token 级混合）。这样图像和文本在完全相同的框架下被理解和生成。

### 视觉 tokenizer：VQ-VAE

编码器（基于 Gafni et al. 2022 / Make-A-Scene）与前面的关键区别：**必须输出离散 token**，才能被自回归生成。

**VQ-VAE (Vector Quantized VAE)**，Oord et al. 2017：

- 思路：把图像编码成连续特征后，**最近邻量化到一个离散 codebook**，再解码回图像，最小化重建损失；
- 量化不可导，用 **straight-through estimator** 传梯度，另加 codebook loss 与 commitment loss；
- Chameleon 配置：**512×512 图像 → 1024 个 token**，codebook 大小 **8192**；
- 文本侧重新训了一个 **BPE tokenizer**，与图像 token 合并成统一词表。

> [!warning] 目标函数的错位
> VQ-VAE 优化的是**像素重建**，CLIP/SigLIP 优化的是**语义对齐**。前者保留纹理但语义弱，后者语义强但细节丢失。**理解需要语义，生成需要细节**——这是多模态的根本张力。

### 训练

| 阶段 | 占比 | 数据 |
|---|---|---|
| 1 | 80% | 大规模无监督：**2.9T** 纯文本 token + **1.5T** text/image token + **400B** 交错 token |
| 2 | 20% | 50% 阶段一数据 + 50% 高质量数据 |

### 训练稳定性（本节的硬核部分）

> [!important] 混合模态训练为什么会崩
> **文本 token 熵低，图像 token 熵高**（图像 token 分布接近均匀，1024 个 token 携带大量随机性）。两种模态争夺同一套 softmax 输出，导致：
> - **norm growth**：激活/权重范数持续增长；
> - **logit drift**：logits 整体漂移、发散，loss 突然爆掉。
>
> **修法**：
> - **QK-norm**：对 attention 的 query/key 做 LayerNorm，直接压住注意力 logits 的量级；
> - **z-loss**：对 softmax 的 partition function 加正则 $10^{-5}\log^2 Z$，把 logits 拉回原点附近。

（这两个技巧和 [CS336-L3-Architectures](CS336-L3-Architectures.md) 里讲的稳定性手段是同一套工具箱，只是在多模态下变成了**必需品**而非可选项。）

> [!note] Chameleon 小结
> 1. **优雅**：只是"对离散 token 做自回归建模"，没有任何特殊结构。
> 2. **性能不够**：离散化会丢信息——想想 OCR，1024 个 token 表达不了密集文字。
> 3. **多模态混训很难**：熵不匹配导致的不稳定必须靠架构手段解决。
>
> 课外补充：公开发布的 Chameleon 权重**移除了图像生成能力**（只保留理解），完整的 token 级混合生成路线后来由 Transfusion（AR + diffusion 混合目标）、Emu3、Janus 等继续推进。

---

## 横向对比

| 模型 | 视觉表示 | 连接方式 | 能生成图像 | 关键贡献 |
|---|---|---|---|---|
| CLIP | 连续，对比学习 | — | ✗ | 用噪声网络数据学语义表示 |
| SigLIP | 连续，sigmoid 对比 | — | ✗ | loss 与 batch size 解耦，效率 ×10 |
| LLaVA | CLIP 特征 | 线性投影 | ✗ | 最简模板 + GPT-4 合成指令数据 |
| LLaVA-OneVision | SigLIP + AnyRes | 2 层 MLP | ✗ | 单图/多图/视频统一 + token 预算平衡 |
| Qwen-VL | ViT-bigG | cross-attn 压到 256 | ✗ | 固定长度 adaptor + grounding token |
| Qwen2-VL | 动态分辨率 ViT | 2×2 patch merge | ✗ | naive dynamic resolution + MRoPE |
| Qwen3-VL | SigLIP-2 | DeepStack 多层注入 | ✗ | interleaved MRoPE + $\sqrt{L}$ loss 归一化 |
| Chameleon | 离散，VQ-VAE | 直接进词表 | ✓ | early fusion，统一自回归 |

---

## 课程总结

> [!important] L17 要点
> 1. **前沿模型默认是多模态的**（原生多模态、omni），单模态 LM 已经是过渡形态。
> 2. **根本挑战：如何把非文本模态编码成 token**。连续 token（CLIP/SigLIP）语义强、性能好但不能生成；离散 token（VQ-VAE）能生成但丢细节。
> 3. **理解和生成的需求不同**：理解要语义，生成要细粒度细节，一个编码器很难同时满足。
> 4. **图像/视频信息密度低于文本**，必须做 token 预算平衡（OneVision 的分辨率分配、Qwen3-VL 的 $\sqrt{L}$ 归一化），否则训练不稳且多模态数据会主导 loss。
> 5. 当前最实用的生成方案是 **连续编码器 + Transformer + diffusion 解码**，而不是纯离散自回归。
> 6. 架构大同小异，**真正的工作量在数据配方**（合成数据、任务特定数据、由易到难的 curriculum）。
> 7. 混合模态训练的**稳定性问题（熵不匹配 → norm growth / logit drift）**必须用 QK-norm + z-loss 之类的手段处理。

---

## 相关链接

- 上一讲：[CS336-L16-RLVR](CS336-L16-RLVR.md)
- 相关笔记：[CS336-L1-Tokenization](CS336-L1-Tokenization.md)（token 化的思想源头）、[CS336-L14-Data-Processing](CS336-L14-Data-Processing.md)（数据过滤与合成）、[CS336-L12-Evaluation](CS336-L12-Evaluation.md)
- 关键论文：
  - Radford et al. 2021 (CLIP)
  - Dosovitskiy et al. 2020 (ViT)
  - Cherti et al. 2022 (OpenCLIP / LAION-5B)
  - Zhai et al. 2023 (SigLIP)
  - Chen et al. 2022 (WebLI / PaLI)
  - Tschannen et al. 2025 (SigLIP-2)
  - Liu et al. 2023 (LLaVA)、Liu et al. 2024 (LLaVA-1.5, AnyRes)、Li et al. 2024 (LLaVA-OneVision)
  - Bai et al. 2023 (Qwen-VL)、Wang et al. 2024 (Qwen2-VL)、Bai et al. 2025 (Qwen3-VL)
  - Fang et al. 2023 (DFN)、Meng et al. 2024 (DeepStack)
  - Oord et al. 2017 (VQ-VAE)、Gafni et al. 2022 (Make-A-Scene)
  - Chameleon Team 2024 (Chameleon)
