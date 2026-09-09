---
tags:
  - 面经
  - 快手
  - AI-infra
  - PD分离
  - DGD
  - KVCache
  - K8s
  - Transformer
aliases:
  - 快手面经
company: 快手
position: AI Infra
date: 2026-09-05
---

# 快手 AI Infra 面经

> **面试时间**：2026-09-05（周五）上午 11:00
> **项目简介（开场标准答案）**：见 [[秋招/面经/PTG项目简介|PTG项目简介]]（仅 vault 内）
> **关联**：[[秋招/面经/百度 AI infra面经|百度 AI Infra]] · [[秋招/面经/商汤 大模型系统工程师面经|商汤 大模型系统]] · [[kimi2.6 PD分离部署记录]] · [[Dynamo/Dynamo部署流程]]

- [x] 周五上午11点面试 ✅ 2026-09-05

---

## 原始题目清单（面试官的顺序）

| # | 板块 | 题目 | 跳转 |
| --- | --- | --- | --- |
| 1 | 论文 | 论文解决了什么样的问题 | [[#Q1 论文解决了什么问题]] |
| 2 | 论文 | 用的是什么算法 | [[#Q2 用的什么算法]] |
| 3 | 论文 | 是有一个中心网络来进行决策吗 | [[#Q3 是有一个中心网络来进行决策吗]] |
| 4 | 工作 | 简单介绍一下在 PTG 的工作内容 | [[#Q4 简单介绍一下在 PTG 的工作内容]] |
| 5 | 工作 | PD 分离配比怎么调优的，你负责哪些 | [[#Q5 PD 分离配比怎么调优的？你负责哪些内容]] |
| 6 | 工作 | PD 分离怎么分离部署的，流程是什么，怎么识别到对方 | [[#Q6 PD 分离是怎么分离部署的？流程是什么？怎么识别到对方]] |
| 7 | 工作 | DGD 里有什么内容 | [[#Q7 DGD（DynamoGraphDeployment）里有什么内容]] |
| 8 | 工作 | 部署起来的流程是什么 | [[#Q8 部署起来的流程是什么]] |
| 9 | 工作 | KV 命中率和 KV 占用率怎么感知和取得 | [[#Q9 KV 命中率和 KV 占用率是怎么感知和取得的]] |
| 10 | 工作 | 怎么平衡这两个参数 | [[#Q10 怎么平衡 KV 命中率和 KV 占用率]] |
| 11 | 工作 | 对 k8s 是怎么启动的有了解吗 | [[#Q11 对 K8s 是怎么启动的有了解吗]] |
| 12 | 工作 | 过程中定位并解决了哪些问题 | [[#Q12 过程中定位并解决了哪些问题]] |
| 13 | OPPO | 主要工作内容、遇到的困难、怎么解决 | [[#Q13 OPPO 的主要工作内容、遇到的困难以及怎么解决的]] |
| 14 | 基础 | transformer 的架构 | [[#Q14 Transformer 的架构]] |
| 15 | 手撕 | 递增最长子序列 | [[#Q15 手撕：最长递增子序列（LC300）]] |

> [!tip] 这场面试的判读（先看这段）
> 问题分布很说明意图：**论文 3 问（浅）+ PTG 部署链路 9 问（深）+ 基础 1 问 + 手撕 1 题**。
> - 对 PTG 的追问是**沿着"部署链路"一路往下钻**：配比 → 分离部署 → DGD → 启动流程 → 指标感知 → 参数平衡 → K8s 原理 → 故障定位。这是**平台/推理部署岗**，不是算法岗。
> - **DGD + K8s 启动**这两问说明面试官想验证你是"真在 K8s 上跑生产服务"还是"只在裸机上敲命令"。**必须能把 CRD → Operator → Pod → 容器 → 探针这条链讲通。**
> - **KV 命中率 vs 占用率怎么平衡**是全场最有区分度的一问，答好可以直接拉分（见 Q10）。
> - 手撕是 CodeTop 高频题，**必须写 O(n log n) 版本**，O(n²) 只能当兜底。

---

# 一、论文部分

> 论文：**MAO-LCR: A Multi-Agent Learning Approach for Joint Task Offloading and Cache Replacement in Edge Computing**（IEEE GlobeCom 2026，CCF 会议，一作）
> 一句话摘要：提出**后悔感知（regret-aware）的多智能体强化学习**方法，对边缘计算中的**任务卸载**与**缓存替换**决策进行**联合优化**，降低系统时延与能耗。

> [!warning] 面试前必须核对的点
> 下面的答案是按论文标题 + 摘要 + 领域标准做法推演的**答题框架**。请对照原文核对：① 具体算法是 MAPPO / MADDPG / QMIX 哪一族；② regret 项具体加在哪（reward shaping / advantage 修正 / 探索策略）；③ 系统模型的具体假设（几个边缘节点、缓存的是"服务/内容/计算结果"哪一种）；④ 实验 baseline 和主要指标数字。**不确定的地方宁可说"这块的具体实现我需要看一下论文"，也不要编。**

## Q1 论文解决了什么问题

**开口版（30 秒）**：

边缘计算里有两个决策：**任务往哪卸载**（本地算还是丢给边缘服务器）和**边缘缓存怎么替换**（容量有限，驱逐谁）。以前的工作基本把这两件事**分开优化**，但它们其实是**强耦合**的——缓存命中与否直接决定卸载后的执行时延，而卸载决策又反过来改变缓存的访问分布。分开做只能拿到局部最优。

**展开（三层问题）**：

1. **耦合问题**：卸载决策和缓存替换互为因果。缓存命中 → 不用回源 / 不用重传数据 → 时延和能耗都降；但缓存里放什么，取决于哪些任务会被卸载过来。联合优化的状态空间是两者的笛卡尔积，传统凸优化 / 启发式（LRU、LFU）解不动。

2. **多智能体问题**：系统里有很多移动设备，每个都在**同时**抢同一份边缘资源（带宽、算力、缓存）。
   - 集中式求解：状态空间随用户数指数爆炸，且需要收集所有人的信息，通信开销大、有单点故障；
   - 独立学习（每个 agent 只管自己）：从单个 agent 的视角看，**别人一直在变 → 环境是非平稳的（non-stationary）** → 策略震荡、不收敛。

3. **目标问题**：不是只优化时延，而是**时延 + 能耗的联合目标**（移动设备有电量约束），而且要在动态、部分可观测的环境下稳定收敛。

**所以我们的定义是**：多用户 MEC 系统中，**联合优化任务卸载决策与边缘缓存替换策略**，最小化系统总时延与能耗，并保证在多智能体博弈下能收敛。

> [!star] 高分桥接（一定要主动说）
> **这篇论文和我实习做的事是同构的。**
> - 论文的"任务卸载决策" ≈ 推理平台的**请求路由**（这个请求发给哪台 Prefill worker）；
> - 论文的"缓存替换决策" ≈ **KV Cache 的驱逐策略**（radix tree 的 LRU 驱逐、HiCache 的分层下沉）；
> - 论文的"缓存命中降低时延" ≈ **prefix cache 命中跳过 prefill，TTFT 从 2s 降到 180ms**；
> - 论文的"多 agent 抢边缘资源" ≈ **多模型抢同一个 GPU 池的容量规划**（我们平台 21 机 336 卡、13 个模型、利用率 100%）。
> 我做推理调度时用的判据（命中率 × 占用率 × 延迟的联合曲线），本质上就是论文里那套联合优化的工程版。

## Q2 用的什么算法

**开口版**：核心是 **regret-aware 的多智能体强化学习（MARL）**，训练范式是 **CTDE（集中训练、分布执行）**，用 regret（后悔值）作为额外的学习信号来缓解多智能体环境下的收敛问题。

**拆成四块讲**：

**1）MDP 建模（先把问题写成 RL）**

| 要素 | 内容 |
| --- | --- |
| Agent | 每个移动设备 / 用户是一个 agent |
| State（局部观测） | 本地任务队列、剩余电量、信道状态、边缘节点的负载与缓存状态（部分可观测） |
| Action | ① 卸载决策：本地执行 / 卸载到哪个边缘节点；② 缓存决策：接纳新内容时驱逐哪一个 |
| Reward | 时延 + 能耗的加权负值（联合目标） |

**2）为什么要"后悔感知（regret-aware）"**

Regret 的定义：**事后最优动作的收益 − 实际选择动作的收益**。

$$
\mathrm{regret}_t = \max_{a'} Q(s_t, a') - Q(s_t, a_t)
$$

它在论文里起三个作用：

- **密集化奖励信号**：原始 reward 只在任务完成时给一次，很稀疏；regret 每一步都能算，等于给了一条更密的学习信号，缓解 **credit assignment**（长决策链上功劳怎么分）；
- **指导探索**：regret 大的状态-动作对说明"我这里可能选错了"，优先去探索，比纯 $\epsilon$-greedy 的随机探索更有效；
- **收敛性论证**：用**累积后悔次线性**（$\sum_{t=1}^{T}\mathrm{regret}_t = O(\sqrt{T})$）来证明算法收敛到**近似纳什均衡**——这是多智能体博弈里"我这套策略站得住"的标准论证方式。

**3）训练范式：CTDE**

- **训练时**：一个**中心化 critic** 吃全局状态 $s$ + 所有 agent 的联合动作 $\mathbf{a}$，输出 $Q(s,\mathbf{a})$ / $V(s)$；每个 agent 有自己的 actor，用 critic 给的梯度更新。
- **执行时**：只留 actor，每个 agent 用**自己的局部观测**独立决策，**不需要中心节点**。
- 为什么必须这样：critic 看到全局 → 环境从单 agent 视角就变**平稳**了，解决震荡不收敛；执行时去中心化 → 满足边缘场景"通信开销不能超过卸载收益"的硬约束。

**4）算法族（按你论文实际用的说）**

- 动作是**离散**的（卸载/不卸载、驱逐哪个）→ **MAPPO**（多智能体 PPO：共享 critic + 独立 actor + GAE 优势估计 + clip）或 **QMIX**（用 mixing network 把各 agent 的 $Q_i$ 单调组合成 $Q_{tot}$）这一族；
- 如果动作有连续量（如卸载比例、发射功率）→ **MADDPG / MAPPO 连续版**；
- regret 项加在哪：一般是**优势函数的修正项**，或者作为**额外的辅助 loss**（regret minimization loss）与策略梯度 loss 加权求和。

**可能被追问的点，先备着**：

- *为什么不用 DQN？* → 多智能体下每个 agent 的 Q 表目标都在动，独立 DQN 不收敛；而且动作空间随缓存条目数变大。
- *和单智能体 DRL 比收益在哪？* → 可扩展性（agent 数增加时复杂度不爆炸）+ 通信开销低（执行时不上传全局状态）。
- *baseline 是什么？* → 通常是 LRU / LFU（缓存侧）+ 贪心 / 随机卸载，以及独立 DRL（无 regret、无中心化 critic）做消融，证明 regret 项和 CTDE 各自的贡献。

## Q3 是有一个中心网络来进行决策吗

**这是全场最好答的一问，答案是：训练时有，执行时没有。**

**1）训练阶段：有中心网络（centralized critic）**

critic 是一个神经网络，输入是**全局状态 + 所有 agent 的联合动作**，输出全局 Q 值 / V 值。它的职责只有一个：**在训练时给每个 agent 的 actor 提供一个"看到全局"的评价信号**。

为什么需要它：从单个 agent 视角，其他 agent 一直在改策略 → 环境是**非平稳**的 → actor 的梯度目标一直在漂 → 学不出来。critic 把所有人动作都吃进去，环境就重新变平稳了。

**2）执行阶段：没有中心网络，完全去中心化**

部署时**只保留每个 agent 自己的 actor**，各自用局部观测独立决策。原因很硬：

- **通信开销**：把全局状态上传到中心节点，这个开销可能直接超过卸载带来的收益；
- **单点故障 / 单点瓶颈**：中心节点挂了整个系统瘫，用户数一多中心节点先成瓶颈；
- **时延**：多一跳往返，边缘计算的时延预算就没了；
- **隐私**：全局状态里含所有用户的信息。

**3）三种方案的对比（体现你想清楚了）**

| 方案 | 决策位置 | 优点 | 缺点 |
| --- | --- | --- | --- |
| 纯集中式 | 中心 controller 决策所有人 | 全局最优 | 状态空间爆炸、通信开销大、单点故障、不可扩展 |
| 纯分布式独立学习（IQL） | 每个 agent 自己学自己的 | 无通信 | 环境非平稳 → 震荡不收敛 |
| **CTDE（本文）** | **训练集中、执行分布** | **兼顾收敛性与可扩展性** | 训练成本高于纯分布式 |

**4）追问预案**：*critic 和 actor 是一个网络吗？* → 不是，参数分开；critic 只在训练期存在，训练完直接丢掉，**部署包里没有 critic**。*agent 之间完全不通信吗？* → 执行时不通信（或只有极轻量的邻居信息交换，看论文设定）；通信被"训练阶段的中心化"替代了。

> [!star] 桥接到实习（主动抛，很加分）
> **CTDE 这个"中心做粗粒度决策、边缘做细粒度执行"的思想，我在推理平台上天天在用：**
> - **sgl-router 的 cache-aware routing**：router 维护一棵**近似的、带 worker 标签的全局 radix tree**（中心视角，但是近似的、不实时拉真实状态），据此选 P 节点；**P 节点本地再用自己真实的 radix cache 做精确前缀匹配**决定复用多少 KV。→ 中心做粗决策，边缘做精决策。
> - **Dynamo 的 KV Router + Planner**：Planner 是"中心大脑"，观测全局流量与延迟，预测并决定 prefill / decode 各起几个副本（**这就是中心网络做决策**）；但每个 worker 本地的 continuous batching、KV block 分配、抢占完全是本地自治的（**执行去中心化**）。
> - 而且 router 的树是"近似而非 ground truth"这件事，和多智能体里的**部分可观测**是同一个问题——都只能靠近似 + 负载信息兜底来避免热点。

---

# 二、PTG 工作

## Q4 简单介绍一下在 PTG 的工作内容

> 完整版见 [[秋招/面经/PTG项目简介]]。这里给**快手 AI Infra 裁剪版**（重部署/调度/可观测，弱化前端和离线包）。

**2 分钟开口稿**：

**1）背景**：我在阿里平头哥做**红区（完全隔离内网、无外网）的大模型推理平台**。红区的约束很硬——不能 `pip install`、不能拉公网镜像、不能连 SaaS，所以所有交付必须走**声明式 + 版本化**：配置全落在自托管 Gitea 仓库，由 ArgoCD 按环境（pdev / pprod / prod）拉取 reconcile，Kustomize 的 base + overlay 处理环境差异。任何一次上线都是"提 MR → 评审 → 合并 → ArgoCD 自动同步"，可回滚、可审计、可复现。

**2）我的角色**：不是只做一小块。从**模型上卡 → 参数调优 → K8s 编排 → RDMA/网络打通 → 压测标定 → 故障定位 → 上线配置 → 监控报表**，这条链路我是 owner。

**3）三块具体工作**：

- **模型部署与调优**：在平头哥自研 PPU 真武 810E（单卡 96GB HBM，**显存大但算力低**）上，用 W4A8 / W8A8-INT8 量化 + PD 分离 + Mooncake RDMA 传输，把 Kimi-K2.6 这类 MoE 模型跑到生产配比 **3P2D（48 卡 Prefill + 32 卡 Decode = 80 卡）**，满足 **TTFT P99 < 2~3s、TPOT < 50~60ms** 的 SLA。
- **调度架构迁移**：推进 **Dynamo** 替代 Kong 网关的静态 Hash 路由，改成基于 worker 实时负载（KV Cache 占用率、队列长度）的动态分发；从"整机独占"改成 **Pod 级弹性 PD 部署**。
- **可观测与平台**：litellm-proxy 统一网关（多模型路由 + 真实请求抓取/回放）、Prometheus + Grafana 观测链路（4 个专用看板），以及一个让 Agent 自动连 Prometheus 出**周报/日报性能分析**的 Skill，覆盖 7 个在线模型的 TTFT / TPOT / 吞吐 / KV 利用率 / KV 命中率。

**4）平台体量（报数）**：全平台 **21 台机器 / 336 张 PPU 卡**、**13 个**大模型服务、利用率 **100%**（0 空闲）。最大占卡的是 DeepSeek-V4-Flash 144 卡（43%）。业务负载特征是**长输入短输出**，平均 input **80K+ tokens**（文档理解 / RAG / 代码类），这个分布直接决定了 PD 配比偏 P。

**5）一个体现工程判断的例子（主动抛）**：模型启动 warmup 原本用一段通用纯文本，跟编码 Agent 的真实请求（多轮对话 + system prompt + tool_calls + 长上下文代码）差距很大，预热效果有限；而且 warmup 脚本在 4 个 ConfigMap 里有 4 份副本、核心逻辑 95% 相同，被 15+ 个 deploy.yaml 引用。我做的是：**从网关侧录制真实请求 → 导出成 JSONL → 启动时回放**，同时把 4 份脚本合并成 1 份共享 ConfigMap，**差异全部收敛到环境变量**，100% 向后兼容灰度上线。

## Q5 PD 分离配比怎么调优的？你负责哪些内容

**先答"为什么要 PD 分离"（一句话垫场）**：Prefill 是 **compute-bound**（一次算几千上万 token，大 GEMM），Decode 是 **memory-bound**（每步只算 1 个 token，要把全部权重和 KV 从 HBM 读一遍）。混部时新来的 prefill 会抢占 decode 的算力，导致 **TPOT/TBT 抖动无法保障**。拆开才能各取所需——我们的 PPU 恰好是"显存大、算力低"，Decode 能吃到高显存带宽的优势，Prefill 靠加卡数弥补算力。

**配比决策：四步法**

**第一步：理论估算（给方向，不给答案）**

稳态下两侧处理速率要匹配，否则一侧堆积：

$$
\frac{N_P}{N_D} \approx \frac{T_{\text{prefill}}}{T_{\text{decode}}} = \frac{\text{input\_len} / \text{prefill 吞吐 per 卡}}{\text{output\_len} \times \text{TPOT}}
$$

**最关键的变量是输入输出长度比**：

| Workload | 特征 | P:D 倾向 |
| --- | --- | --- |
| RAG / 文档理解 / 代码分析 | 长输入短输出（**我们就是这类，input 80K+**） | **偏 P** |
| 长链推理 / 创作 / Agent 多轮生成 | 短输入长输出 | 偏 D |
| 普通对话 | 均衡 | 接近 1:1 起 |

三个修正因子：**prefix cache 命中率**（命中高 → P 的实际计算量大减 → 可降低 P 比例，所以 router 开 cache-aware 直接影响配比）、**KV 传输带宽**（RDMA 慢则 P 端要留余量等传输）、**投机解码/MTP**（提升 decode 效率 → D 需求下降）。

**第二步：阶梯压测标定（真正的决策依据）**

固定线上真实 prompt 长度分布，用 `sglang.bench_serving` 阶梯加压（并发 1 / 5 / 10 / 20 / 30 / 50），每档记录 TTFT P50/P99、TPOT、吞吐、并发上限。**判读规则**：

- **TTFT 涨 + P 端 GPU util > 90% + D 端有空闲 → P 不够**
- **TPOT 涨 + D 端 KV 占用 > 85% + decode 队列堆积 → D 不够**

实测阶梯（K8s，长序列 workload）：

| 配置变化 | 结论 |
| --- | --- |
| Host 1P1D vs K8s 1P1D | 先验证容器化本身没有性能损失（顺带查 MTU / hostNetwork） |
| 1P1D → **2P1D** | 到 20 并发时 2P 优势明显，**TPOT 依然稳定** → 瓶颈确实在 P |
| 2P1D → **3P1D** | 20 并发下 **TTFT 好很多，TPOT 只是微升** → 继续加 P 仍有收益 |
| 3P1D → **3P2D** | 加 D 提升 TPOT 和并发上限 → 最终生产配置 |

**第三步：SLA 约束下选优**

硬约束 **TTFT P99 < 2~3s、TPOT < 50~60ms**。在满足 SLA 的所有配置里取**吞吐/成本最优**那一档，不是无脑加卡。

**最终上线配置**：

| 组件 | 副本数 | PPU 卡数 | 备注 |
| --- | --- | --- | --- |
| sglang-router | 2 | 0 | 开 kv-aware routing |
| Prefill | 3 | 48 | 开 radix-cache |
| Decode | 2 | 32 | `dp-size=16` |

即 **3P2D = 48 卡 P + 32 卡 D = 80 卡**。

**第四步：上线后用真实流量反推 bound line**

3P2D 上线后的周六流量分析：

- **Decode 并发综合数与 TPOT 曲线高度一致、完整正相关** → TPOT 是 D 侧的直接观测指标；
- **并发达到 30 时 TPOT 上升到 60ms** → 这就是 D 侧 bound line，超过就该加 D 或限流；
- **TTFT 平均 2~3s** → P 侧还有余量，配比合理（如果 TTFT 也顶到 SLA 说明 P 不够）。

**第五步（进阶）：静态配比的局限 → 动态调度**

真实流量有波峰波谷、长短请求混合，静态配比要么低谷浪费卡、要么高峰被打爆。所以推进 **Dynamo**：Planner 按队列长度 / SLO 反馈动态伸缩 prefill 和 decode 副本；更激进的是**弹性实例**——同一 GPU pool 里的实例按需切换 P/D 角色。

**我负责的部分**：**整条链路 owner**。1P1D 到 3P2D 的**所有对比实验、上线配置、故障定位都是我做的**——环境适配、启动参数、K8s 编排（DGD）、RDMA/网络打通、压测标定、上线配置、监控报表。业务场景是内部推理服务，典型 workload 是长输入短输出（平均 input 80K+ tokens）。

> [!tip] 一句话总结
> **先用输入输出长度比做理论估算定方向，再用阶梯压测找瓶颈侧，在 TTFT/TPOT 的 SLA 硬约束下取成本最优档，上线后用"并发–TPOT 正相关曲线"反推 bound line 持续修正，长期靠动态调度替代静态配比。**

## Q6 PD 分离是怎么分离部署的？流程是什么？怎么识别到对方

### A. 部署形态：P 和 D 是独立进程/Pod，加载同一份权重，参数不同

| 维度 | Prefill 实例 | Decode 实例 |
| --- | --- | --- |
| 启动模式 | `--disaggregation-mode prefill` | `--disaggregation-mode decode` |
| radix cache | **开**（前缀复用收益全在 P） | `--disable-radix-cache`（KV 是 P 传来的，显存留给更大 batch） |
| `mem-fraction-static` | **0.9~0.92**（KV 算完就传走，本地只需周转，显存多给权重和 activation 峰值） | **0.7~0.8**（要长期持有所有在飞请求的 KV，还要给 CUDA Graph 静态 buffer 留余量，否则 capture 阶段直接 OOM） |
| 并行 | TP=8/16 + DeepEP | `--enable-dp-attention --dp-size=16 --moe-dense-tp-size=1`（attention 每卡独立算，零通信；MoE 仍 16 卡 EP） |
| CUDA Graph | 不用（shape 变化大） | `--cuda-graph-bs` 一串桶（decode 每步只算 1 token，kernel launch 开销占比高） |
| 职责 | 只算 prefill，**不吐字** | 收 KV，做 decode，**流式返回 token** |

前面挂一个 router：`sglang_router.launch_router --pd-disaggregation`，持有 P 列表和 D 列表。

### B. 一次请求的完整流程（要能背下来）

```
1. 请求到 router
   → router 用 cache-aware policy 选一个 P（近似 radix tree 最长前缀匹配 + 负载均衡）
   → 同时选一个 D（round-robin / 负载）
   → 为这次传输分配全局唯一的 bootstrap_room（request id）

2. router 把请求发给 P 和 D，两边都带上同一个 room id

3. D 端先做 prealloc（DecodePreallocQueue）
   → 在本地 KV pool 预分配 block
   → 注册 RDMA buffer（ibv_reg_mr 到自己的显存）
   → 把 (remote_addr, rkey, block 数, 布局元信息) 通过 bootstrap server（TCP）发给 P

4. P 端执行 prefill
   → 用 Mooncake Transfer Engine 把 KV 通过 RDMA WRITE 直接写进 D 端预分配的显存地址
   → 一次传输是多个不连续 block 的批量 WRITE（scatter-gather list），可能几百上千个 WR 链成一次 post

5. 完成判定
   → P 端所有 WRITE 完成后，通过控制面发一条 "KV sent"
   → D 端 polling thread 轮询 Mooncake 的 getTransferStatus()（拉 + 推结合）
   → DecodeTransferQueue 出队 → waiting queue → 参与 continuous batching → 开始 decode

6. D 端流式返回 token 给 router / 客户端
```

**为什么 prealloc 这一步是关键**：buffer 地址必须先固定下来，P 端才有 `remote_addr` 可以 WRITE；同时保证**重传幂等**——RDMA WRITE 到相同地址覆盖写相同数据，重传多少次结果都一样。

**为什么需要控制面通知**：单边 RDMA WRITE **对端 CPU 是完全不知道的**（不产生对端 CQE，除非用 `imm_data`），所以必须有人显式告诉 D 端"传完了"。

### C. 怎么识别到对方（三层，这是问题的核心）

| 层 | 解决什么 | 我们的实现 |
| --- | --- | --- |
| **① 服务发现层**<br>（谁是谁、在哪） | P/D 实例的地址与角色 | **裸机模式**：router 启动参数写死 `--prefill http://sh01t-swu27:8100 --decode http://sh01t-swu28:12100`（静态）。<br>**K8s + SGLang 模式**：Pod 打注解 `sglang.ai/bootstrap-port`，router 走 service discovery 拿到 Pod IP 列表。<br>**Dynamo 模式**：worker 启动时把 `{host, port, model, 角色, status, load, kv_cache_blocks}` **注册进 etcd**，Frontend/KV Router **watch etcd** 自动发现，动态增删 worker 无需改配置。 |
| **② 传输建连层**<br>（RDMA 怎么配对） | 交换 RDMA 建连信息 | **bootstrap server（TCP 带外通道）**：D 端起一个 bootstrap 端口，P 端连上去交换 `QP number / LID(IB) 或 GID(RoCE v2, 含 IP) / PSN / MTU / rkey + remote_addr`。**RDMA 自己不做发现**，必须靠带外通道。之后 `ibv_modify_qp` 走 RESET→INIT→RTR→RTS 状态机建连。 |
| **③ 请求级配对层**<br>（这次 KV 属于哪个请求） | P / D / router 三方对齐同一次传输 | **bootstrap_room（request id）**：三方靠同一个 room id 关联。D 端也靠它做**去重**——收到重复的"开始 decode"通知时，判断该请求是否已在 running batch 里。 |

**Dynamo 带来的变化**：传输后端从 Mooncake 换成 **NIXL**（插件化，UCX 默认，自动选 NVLink > IB RDMA > RoCE > PCIe > 共享内存 > TCP），**不强制依赖 RDMA**；bootstrap 发现从"手动配 K8s 注解 + 手动指定 `--disaggregation-bootstrap-port`"变成 **Discovery Service 自动发现、自动计算分发 bootstrap 地址**；而且支持**不同 TP 配置之间**的 KV 元数据交换与 gather-scatter（Mooncake 要求两端 TP 一致）。约束：**P 和 D 的 `--page-size` 必须一致**。

**记忆口诀**：**etcd/注解解决"谁在哪"，bootstrap server 解决"怎么建连"，room id 解决"这是谁的"。**

## Q7 DGD（DynamoGraphDeployment）里有什么内容

**先说它是什么**：`apiVersion: nvidia.com/v1alpha1, kind: DynamoGraphDeployment`，是 **Dynamo Operator 的 CRD**，用一份 YAML 描述**一整套推理服务的拓扑图**——由哪些角色组成、各几个副本、怎么连、每个角色跑什么镜像和参数。"Graph" 就是指这张 DAG。

**内容清单（按 spec 结构讲）**：

**1）`spec.services` / components（主体，一个 map）**

每个 key 是组件名（`Frontend` / `Processor` / `PrefillWorker` / `DecodeWorker` / `Router`），value 描述该组件：

| 字段 | 作用 | 我们的值举例 |
| --- | --- | --- |
| `dynamoNamespace` | **Dynamo 逻辑命名空间**（≠ K8s namespace），服务发现的隔离域 | `qwen35-system` |
| `componentType` | 角色类型：frontend / worker / processor | `worker` |
| **`replicas`** | **副本数 —— P/D 配比就写在这里** | prefill 3、decode 2 |
| `extraPodSpec.mainContainer.image` | 镜像（红区是私有 registry 的自建镜像，内含 ai-dynamo + entrypoint 脚本） | `your-registry/kimi-k26-dynamo:latest` |
| `command` / `args` | entrypoint 与启动参数：模型路径、`--served-model-name`、`--tensor-parallel-size`、量化方式、`--enable-prefix-caching`、`--discovery-backend etcd`、端口 | 见 [[Dynamo/Dynamo部署流程]] |
| `resources` | **加速卡 + RDMA 设备**：`nvidia.com/gpu: 8`（PPU 对应厂商 device plugin）+ `rdma/hca: 4`。extended resource，requests 必须 == limits，不可超卖 | 8 卡 |
| `volumeMounts` | 权重目录（hostPath，只读）、共享 warmup 数据目录 | `/ppusw/datasets/checkpoints` |
| `ports` | 容器端口（frontend 8000 等） | — |
| 探针 | startup / readiness / liveness（模型加载要几分钟，**必须配 startupProbe**） | — |

**2）`extraPodSpec` 的 Pod 级配置（我踩过坑的地方）**

- `hostNetwork: true` + `dnsPolicy: ClusterFirstWithHostNet`：**必须开**，否则容器看不到宿主机的 `mlx5_bond_0..7`，Mooncake RDMA 初始化失败或 fallback 到低效路径（我实测去掉就报错）；
- `hostPID` / `hostIPC`：IPC 共享，给 NVLink IPC / 共享内存传输用；
- `volumes`：hostPath 模型存储；
- 节点亲和：`board.type=810e` 选 PPU 机型；P/D 之间 podAntiAffinity；专用节点的 tolerations；
- 安全上下文：`IPC_LOCK` capability + `ulimit memlock unlimited`（RDMA 注册大内存要 pin）、`/dev/infiniband/*` 挂进容器。

**3）`envs`（组件环境变量）**

- 基础设施连接：`DYNAMO_ETCD_ENDPOINT`、`DYNAMO_NATS_ENDPOINT`
- 路由策略：`DYN_ROUTER_MODE=kv`（开 KV 感知路由）、`DYN_ROUTER_KV_OVERLAP_SCORE_WEIGHT`、`DYN_ROUTER_TEMPERATURE`
- Worker 标识：`DYNAMO_WORKER_ID`（从 `metadata.name` 注入）
- 可观测：`DYN_METRICS_ENABLED`、`DYNAMO_LOG_LEVEL`
- 超时：`DYN_REQUEST_TIMEOUT`、`DYN_HEALTH_CHECK_INTERVAL`
- 引擎侧：`MC_NUM_QP_PER_EP`、`MC_FORCE_MNNVL`、`SGLANG_DEEPEP_NUM_MAX_DISPATCH_TOKENS_PER_RANK` 等

**4）组件之间的连接关系（graph 的边）**：描述谁调用谁（Frontend → Processor → Prefill/Decode worker），operator 据此拼装出服务图。

**DGD vs DCD（追问高频）**：

- **graph = `DynamoGraphDeployment`（DGD）**：**整套部署**的顶层描述，你 `kubectl apply` 的就是它；
- **component = `DynamoComponentDeployment`（DCD）**：graph 里**单个角色**的部署单元；
- **流程**：提交一个 graph → **operator reconcile 把它拆成多个 component** → 每个 component 各自生成真正的 Deployment / Pod / Service。
- **排查时看哪条线红**（Operator 看板按 `resource_type` 分线）：**graph 报错** = 顶层编排出问题（配置解析、角色拼装）；**component 报错** = 某个具体角色起不来（镜像 / 资源 / 探针）。

**准入校验（Admission Webhook）**：`kubectl apply` 时请求先被 API Server 拦下、同步转发给 operator 注册的 webhook 做合法性校验，**通过才写入 etcd，不通过当场拒绝、apply 直接失败**。它发生在 reconcile **之前**。因为它同步阻塞在 apply 路径上，必须毫秒级。**Webhook Denials > 0 是排查"YAML apply 上去没生效"的第一站**，拒绝原因直接指出触发了哪条校验规则。

## Q8 部署起来的流程是什么

**分两条线答：交付流程（GitOps）+ 运行时启动流程。**

### A. GitOps 交付流程（我们实际怎么上线）

```
1. 改 Gitea 仓库配置
   apps/{engine}/{model}/overlays/{env}/deploy.yaml
   （Kustomize base + overlay：同一份模型部署，按环境覆盖副本数/资源/参数）

2. 提 MR → 评审 → 合并

3. ArgoCD 检测到 Git 变更 → 拉取 → diff 出最终 YAML → 同步到集群
   每个环境一个 Application，三级灰度：pdev → pprod → prod
   （配置漂移会被 ArgoCD 检出并纠正，Git 是唯一事实来源）

4. Dynamo Operator watch 到 DGD → 准入 webhook 校验 → reconcile
   → 拆成多个 DCD → 生成 Deployment / Pod / Service
```

**为什么用 Kustomize 不用 Helm**：Kustomize 是纯声明式 patch，没有模板语法，**diff 出来就是最终 YAML**，评审和排障更直观；ArgoCD 对两者都是一等支持。

### B. 运行时启动流程（按依赖顺序，这个顺序不能乱）

```
0. kubectl create namespace dynamo-system

1. 基础设施先行
   etcd（服务发现）+ NATS（KV 事件面，JetStream）
   → kubectl wait --for=condition=available --timeout=300s

2. Worker Pod 起来
   Scheduler 过滤打分 → 绑定到带 PPU + rdma/hca 的节点
   → kubelet 调 CRI 拉镜像 → 建 sandbox → CNI 配网络 → 挂 hostPath 卷
   → 执行 entrypoint（/dynamo-entrypoint.sh）
   → source /etc/environment → export CUDA_VISIBLE_DEVICES
   → python -c "import torch; print(device_count)" 校验卡数
   → exec python -m dynamo.vllm / dynamo.sglang "$@"

3. 引擎内部初始化（耗时最长的一段，几分钟）
   加载量化权重 → 按 mem-fraction-static 预分配 KV pool
   → RDMA 初始化（ibv_open_device / alloc_pd / reg_mr 注册显存 ← 依赖 peermem）
   → CUDA Graph capture（按 --cuda-graph-bs 的桶逐个录制）
   → warmup（回放真实请求 JSONL）

4. 注册与事件面
   Worker 向 etcd 注册 {host, port, model, 角色, load, kv_cache_blocks}
   → 向 NATS 发 KV events（block stored / evicted）

5. Frontend / Router 起来
   watch etcd 拿到 P/D 列表 → 订阅 NATS 建近似 radix tree → 开 kv-aware routing

6. Service 暴露（ClusterIP / NodePort / LoadBalancer）→ 网关注册模型

7. 验证
   kubectl get pods / dynamographdeployment
   → curl /v1/models → 单请求 /v1/chat/completions
   → KV 感知路由验证（发两条相似前缀的请求，看是否路由到同一 worker）
   → sglang.bench_serving 压测 → Grafana 看板确认 TTFT/TPOT/KV 利用率/NVLink 带宽
```

**几个必须提的工程细节（体现你真部署过）**：

- **就绪探针**：模型加载 + capture + warmup 要几分钟，**readinessProbe 没通过前不能进 Service Endpoints**，否则流量打进来全是 503；**startupProbe 必须配**，否则 liveness 会在加载期反复杀 Pod → CrashLoopBackOff。
- **顺序依赖**：etcd/NATS 没起 worker 就注册失败；worker 没 Ready frontend 就是空路由表。所以脚本里全是 `kubectl wait`。
- **优雅退出**：`terminationGracePeriodSeconds` 要够长，`preStop` hook 先从 router 摘除再退出，否则在飞请求被硬切。
- **验证要看板交叉校验**：$E2E \approx TTFT + ITL \times OSL$；$r_p \approx r_d$（不等说明 P/D 流水线中间有堆积或丢弃）；NVLink 带宽 **< 1 GB/s 反而是坏信号**（说明 KV 传输退化成走主机内存拷贝，没吃到 NVLink/GPUDirect），健康区间约 1~20 GB/s。

## Q9 KV 命中率和 KV 占用率是怎么感知和取得的

**先给一个关键区分（这是高分点）**：

> **命中率是"计算能不能省"，占用率是"显存够不够"。**
> 命中率来自 **cache 索引层**（radix tree / prefix cache），占用率来自 **memory pool 层**（KV block 分配）。
> 两者**数据源不同、时间尺度不同、优化手段也不同**——一个是分钟级的离线报表指标，一个是毫秒级的在线调度输入。

### A. 引擎自报（数据源头）

**SGLang**：启动加 `--enable-metrics --enable-cache-report`（我们还加了 `--enable-expert-distribution-metrics`），引擎在 `/metrics` 暴露 Prometheus 指标：

| 指标 | 含义 |
| --- | --- |
| `sglang:cache_hit_rate` | **KV 命中率**，0~1 小数，radix cache 前缀命中比例 |
| `sglang:token_usage` | **KV 占用率**，已用 KV token / 总容量 |
| `num_running_reqs` / `num_queue_reqs` | 在飞 / 排队请求数 |
| `gen_throughput` | 生成吞吐 |
| TTFT / ITL histogram | 延迟分布（`_sum` / `_count` / 桶） |

**vLLM**：

| 指标 | 含义 |
| --- | --- |
| `vllm:gpu_cache_usage_perc` | **KV 占用率** |
| `vllm:prefix_cache_hits_total` / `vllm:prefix_cache_queries_total` | **命中率 = hits / queries × 100** |

### B. 采集与聚合（我做的性能分析 Skill）

Prometheus 地址 `http://na131t-sw642.eng.t-head.cn:31365`，`query_range` 接口，**5 分钟采样间隔**，覆盖 SGLang（2 个模型）+ vLLM（5 个模型）共 **7 个在线模型**。

**KV 利用率的计算口径（有坑，务必讲）**：

1. **按每个 Pod 独立采集**时间序列（不能先跨 Pod 求和再算，会被副本数污染）；
2. **过滤掉值为 0 的时间点** —— 空闲时段占用率/命中率是 0，不过滤会把均值严重拉低，**只统计 Pod 有实际推理请求的时段**；
3. 在**相同时间点**上对该模型所有 Pod 的值**取平均**；
4. 基于各时间点平均值再算 **Avg / Max / Min / Median / P95 / StdDev**；
5. SGLang 侧要按 **(pod, engine_type)** 独立计算后取平均——因为 PD 分离下 P 和 D 的 KV 行为完全不同，混在一起没有意义。

**命中率**：vLLM 用 `hits / queries × 100`；SGLang 按 Pod 独立采 `cache_hit_rate` → 过滤零值 → 同时刻跨 Pod 平均 → ×100。

**延迟类**：从 histogram 算均值，`sum(rate(*_sum[5m])) / sum(rate(*_count[5m])) × 1000`。

产出：weekly（自然周环比）+ daily（日环比）两种模式，报告含执行摘要、指标汇总对比、各模型详细统计（带 🟢↓/🔴↑ 趋势箭头）、深度分析与可执行建议。

### C. 路由侧的实时感知（Dynamo，在线决策用）

上面 B 是**离线报表**（分钟级、事后分析）。**Dynamo 的 KV Router 是在线感知**（毫秒级、直接参与路由决策）：

```
worker 产生 KV events（block stored / evicted / 请求进入、完成）
  → 发布到 NATS（Event Plane）
  → KV Router 订阅，维护每个 worker 的近似 radix tree / block hash 集合
  → 同时收集实时负载（active blocks、queue length、in-flight 数）
  → 路由时计算 overlap score（请求前缀与该 worker 缓存的重合度）
     与 load 加权求和 → 选 worker
```

另外 worker 在 **etcd** 的注册信息里就带 `load` 和 `kv_cache_blocks` 字段，服务发现和负载感知是同一份数据。

### D. Grafana 看板上怎么看（Disagg Analysis 盘 Row 3）

| 面板 | 类型 | 判读标准 |
| --- | --- | --- |
| **KV Cache Utilization** | 瞬时 gauge（percentunit） | 理想稳定在 **0.6~0.8**：太低 = 显存浪费；**> 0.9 = decode 容量见底、batch 被压缩、ITL 随之恶化** |
| **KV Cache Blocks (Total)** | 瞬时 gauge | decode worker 的 KV 总容量，是**常量参照线**，正常应为水平直线；**突然变化 = worker 重启或重新分配显存** |

**关系式判读**：$U_{kv} \in [0.6, 0.8]$ 且 ITL 平直 = 健康；$U_{kv} > 0.9$ 伴随 ITL 抬升 = decode 容量见底。

## Q10 怎么平衡 KV 命中率和 KV 占用率

> **这是全场最有区分度的一问。核心洞察：这两个指标是互相拉扯的，而且优先级不对等。**

### 一、先讲清楚它们为什么冲突

- **想提高命中率** → 要把更多历史前缀的 KV block **留着不驱逐** → **占用率升高**；
- **想压低占用率** → 要**激进驱逐** → **命中率下降** → prefill 重算 → **TTFT 上升**。

同一块 KV pool，两个目标抢同一份资源。**所以不存在"两个都最大化"，只存在"在约束下求最优"。**

### 二、第一原则：优先级不对等，永远先保占用率

| | KV 占用率 | KV 命中率 |
| --- | --- | --- |
| 性质 | **红线指标 / 硬约束** | **优化指标 / 收益项** |
| 恶化后果 | > 0.85~0.9 → 触发 batch 压缩、preemption、排队 → **TPOT/ITL 直接恶化 → SLA 违约** | 低 → prefill 重算 → TTFT 变长 → **"只是没赚到"，不会违约** |
| 处理 | **必须先保** | 有余量再谈 |

**这是工程判断，不是调参技巧**：一个会让你违约的指标，优先级永远高于一个只影响收益的指标。

### 三、第二原则：看联合曲线，不看单点

把 KV 占用率 × TPOT、命中率 × TTFT 两条曲线**叠在同一时间轴**上判读：

| 现象组合 | 诊断 | 动作 |
| --- | --- | --- |
| 占用率 0.6~0.8 + ITL 平直 | **健康** | 不动 |
| 占用率 > 0.9 + ITL 抬升 | decode 容量见底 | **加 D 副本** / 网关限流（并发 bound line 30） |
| 占用率很低 + TTFT 高 | 命中率不够 或 P 侧算力不足 | router 开 cache-aware、P 端开 radix cache、加 P |
| 命中率高 + TTFT 没改善 | 回读吃掉了收益（多级缓存场景） | 改 `layer_first` 做 overlap，或缩小 L2 只留最热的 |
| Blocks Total 突然变化 | worker 重启 / 显存重分配 | 查 Pod 事件和探针 |

**任何"吞吐涨了"都必须同时确认 TTFT/TPOT 没恶化**，否则是拿延迟换吞吐。

### 四、第三原则：参数分层调节（两个指标各有各的手）

**占用率侧（memory pool 层）**：

| 参数 | 我们的值 | 原理 |
| --- | --- | --- |
| `mem-fraction-static` | **P 0.9~0.92 / D 0.7~0.8（非对称）** | P 算完 KV 立刻传走，本地只需周转；D 要长期持有在飞请求的 KV，还要给 CUDA Graph 静态 buffer + decode activation 留余量，压太高 capture 阶段直接 OOM |
| `max-running-requests` | 1024 | 限制同时在飞的请求数，直接封顶 KV 需求 |
| `schedule-conservativeness` | **0.3** | 调度保守度：给未来 decode 预留多少 KV。调低 → 敢塞更多并发、吞吐上去，但抢占/回退风险增加；调高 → 稳但吞吐低 |
| `page-size` | **64** | block 粒度。大 page → block table 更短、元数据更少、kernel 访存更连续；但**内部碎片变大**（最后一个 block 平均浪费 page_size/2 个 token），且前缀复用粒度变粗、命中率下降 |
| `dp-size` | **16**（= tp-size，`moe-dense-tp-size=1`） | KV 按 head 分片到多卡，单卡显存压力下降，能开更大 batch |

**命中率侧（cache 索引层）**：

| 手段 | 原理 |
| --- | --- |
| router 开 **cache-aware routing** | router 维护带 worker 标签的**近似 radix tree**，把相同前缀的请求路由到同一台 P → **在 GPU 层就拿到大部分命中** |
| **P 端开 radix cache** | prefix 复用的收益点全在 P（跳过 prefill） |
| **D 端 `--disable-radix-cache`** | D 的 KV 是 P 通过 RDMA 传来的，本地前缀复用价值低，显存留给更大的 decode batch |
| `--cache-threshold`（默认 0.5） | 低于这个命中比就视作没命中、**不写树**，减少树膨胀 |
| `--max-tree-size`（默认 2^24） | 直接封顶 router 近似树节点数，超了走 LRU 驱逐 |
| `--eviction-interval-secs`（默认 60） | 调短让冷 prefix 更早释放 |

**注意 `page-size` 是唯一同时影响两边的参数**，它是这两个指标的直接 trade-off 旋钮：

| page_size | 内部碎片（占用率） | 元数据/block table | kernel 访存连续性 | prefix 复用粒度（命中率） |
| --- | --- | --- | --- | --- |
| 小（1~16） | 小 | 长 | 差 | 细，**命中率高** |
| 大（64~128） | 大 | 短 | 好 | 粗，**命中率低** |

我们选 64，因为长输入 workload（80K+ tokens）下 prefix 本来就很长，粗粒度对命中率影响小，而 kernel 效率和元数据开销收益更明显。

### 五、第四原则（最重要的架构级答案）：PD 分离本身就是解耦

**与其在一块显存里调两个互相打架的目标，不如用架构把它们拆开：**

- 让**命中率优化只在 P 端做**（P 开 radix cache、mem-fraction 拉到 0.9~0.92，显存尽量给缓存）；
- 让**占用率控制主要在 D 端做**（D 关 radix cache、mem-fraction 压到 0.7~0.8，显存尽量给 batch）；
- 两个目标**不再抢同一块显存**。

**架构级的平衡比调参级的平衡有效得多**——这是我做这个项目最大的体会。

### 六、第五原则：闭环校准 + 决定要不要"扩一层"

- **上线后用真实流量回归**：我们发现**并发 30 时 TPOT 升到 60ms**，这就是 D 侧 bound line；结合占用率曲线判断是"加 D 卡"还是"网关限流"。
- **命中率数据是"该不该上 HiCache"的直接依据**：如果 GPU 层命中率低、但 miss 时的 prefill 代价很高（长 prefix），才值得上 HiCache 把缓存扩到 host DRAM（L2）。判断标准是算**盈亏平衡**：

$$
\frac{\text{KV}_{\text{token}}}{\text{BW}_{\text{PCIe}}} < \frac{\text{FLOPs}_{\text{token}}}{\text{算力}} \;\Rightarrow\; \text{回读比重算划算}
$$

**prefix 越长、KV 越压缩（MLA/量化）、GPU 算力越紧张，HiCache 收益越大**——我们 PPU 恰好是"显存大、带宽高、算力相对低"，理论上收益是放大的。

**但我们上线时没有开 HiCache**，理由要说清楚：① PD 分离下 prefix 复用收益全在 P 端，先把 GPU 这一层榨干；② router 的 cache-aware 已经能拿到大部分命中；③ HiCache 引入 host 内存占用和 PCIe 流量，而 P 端 `mem-fraction-static` 已压到 0.9~0.92、host 侧还要跑 Mooncake 注册内存，需要先做容量评估；④ 属于"下一步可以做"的优化项，前置条件是先量化清楚 prefix 命中率分布和 miss 时的 prefill 代价。

> [!tip] 一句话总结（背这个）
> **占用率是红线、命中率是收益，先保占用率再谈命中率；判读靠"占用率×TPOT、命中率×TTFT"的联合曲线而不是单点；调节上两个指标各有参数手，`page-size` 是唯一同时影响两边的 trade-off 旋钮；但最有效的是架构级解耦——PD 分离让命中率只在 P 端优化、占用率只在 D 端控制，两个目标不抢同一块显存；最后用真实流量反推 bound line 闭环校准，并用命中率数据决定要不要扩到 HiCache。**

## Q11 对 K8s 是怎么启动的有了解吗

**分两层答：K8s 通用启动链路 + 推理 Pod 的特殊点。**

### A. 通用链路：从 `kubectl apply` 到容器跑起来

```
1. kubectl apply
   → API Server：认证(Authentication) → 鉴权(Authorization)
   → Admission Webhook 准入校验（Mutating → Validating）
   → 校验通过才写入 etcd（不通过当场拒绝，apply 直接失败）

2. Scheduler（watch 到 spec.nodeName 为空的 Pod）
   → Filtering（过滤）：资源是否够、nodeSelector/Affinity、污点容忍、端口冲突
   → Scoring（打分）：资源均衡、亲和性偏好、镜像本地性
   → 绑定 Pod 到 Node（写回 API Server）

3. 目标 Node 上的 kubelet（watch 到属于自己的 Pod）
   → 调 CRI（containerd）拉镜像
   → 创建 Pod sandbox（pause 容器，建立网络命名空间）
   → 调 CNI 分配 Pod IP、配路由（我们是 flannel VXLAN）
   → 调 CSI / 挂载 volume（我们是 hostPath）
   → 按顺序跑完 initContainers
   → 创建主容器 → 执行 entrypoint

4. 探针
   startupProbe（成功前 liveness/readiness 都不生效 ← 大模型加载必须靠它）
   → readinessProbe（通过才把 Pod IP 加进 Service Endpoints，才开始接流量）
   → livenessProbe（失败则重启容器）

5. kubelet 上报状态 → API Server → etcd
```

**Operator 场景多一层**：你 apply 的是 **CRD（DGD）**而不是 Pod → Operator 的 controller watch 到 → **reconcile 循环**（观察实际状态 → 对比期望 → 差什么补什么）→ 生成 Deployment / Pod / Service → 再走上面第 2 步开始的原生流程。因为 Pod 会挂、有人会手改，这个循环要反复跑（看板上 `Reconciliation Rate` 就是它每秒执行多少次）。

### B. 推理 Pod 的特殊点（我实际踩过的，这部分才是重点）

| 维度 | 通用服务 | 我们的推理 Pod |
| --- | --- | --- |
| **资源** | cpu / memory | `nvidia.com/gpu: 8`（PPU 厂商 device plugin）+ **`rdma/hca: 4`**（RDMA device plugin）。**extended resource：requests 必须 == limits，不可超卖** |
| **调度** | 默认调度 | nodeAffinity `board.type=810e` 选 PPU 机型；P/D 之间 podAntiAffinity；专用节点打污点 + tolerations；NUMA/PCIe 亲和（网卡与加速卡挂同一 PCIe switch，跨 NUMA 掉带宽） |
| **网络** | 标准 Pod 网络（CNI 分配 IP） | **必须 `hostNetwork: true` + `dnsPolicy: ClusterFirstWithHostNet`**，否则容器看不到宿主机的 `mlx5_bond_0..7`，Mooncake RDMA 初始化失败或 fallback 到低效路径。我实测去掉 hostNetwork 直接报错。还要 `hostPID` / `hostIPC`（IPC 共享给 NVLink IPC / 共享内存） |
| **权限** | 非特权 | `IPC_LOCK` capability + `ulimit memlock unlimited`（RDMA `ibv_reg_mr` 注册大内存要 pin 住）、`/dev/infiniband/*` 挂进容器、privileged |
| **存储** | PVC | 权重用 **hostPath** 挂 `/ppusw/datasets/checkpoints`（只读）；warmup 数据挂共享 hostPath `/ppusw/devops/llm_platform/` → 容器 `/warmup-data/`，所有模型 Pod 共享 |
| **启动时长** | 秒级 | **几分钟**（加载量化权重 + RDMA 注册 + CUDA Graph capture + warmup）→ **startupProbe 必须配**，否则 liveness 在加载期反复杀 Pod → CrashLoopBackOff；readinessProbe 打 `/health` 或 `/v1/models` |
| **网络配置** | 无感 | **MTU 一致性**：`cni0` 与 `flannel.1` 必须和物理 bond 对齐（物理 1500 → 1450；物理 9000 → 8950，VXLAN 约 50B 封装开销）。跨机不一致会出现丢包 / PMTU 黑洞 |
| **退出** | 直接杀 | `terminationGracePeriodSeconds` 要够长；`preStop` hook 先从 router 摘除再退出，否则在飞请求被硬切 |
| **依赖顺序** | 无 | etcd / NATS 必须先 Ready（`kubectl wait`），否则 worker 注册失败、frontend 路由表为空 |

**排查一个 Pod 起不来的标准动作**：

```bash
kubectl describe pod <pod>          # 看 Events：调度失败/镜像拉取/探针失败/OOMKilled
kubectl get events --sort-by=.lastTimestamp -n <ns>
kubectl logs <pod> --previous       # 上一次崩溃的日志
kubectl exec -it <pod> -- ibv_devinfo   # 容器内确认能不能看到 RDMA 设备
kubectl get dynamographdeployment -n <ns>   # CRD 层状态
# Operator 看板：graph 报错 = 顶层编排；component 报错 = 某角色起不来；
#               Webhook Denials > 0 = YAML 本身不合法，apply 就没生效
```

> **诚实边界（如果被追到很深）**：我用 K8s 是**平台使用者 + 编排设计者**的视角（CRD、DGD、Operator reconcile、调度约束、网络/存储/权限、探针、MTU、GitOps 交付），**没有做过 kubelet / scheduler / CNI 插件本身的开发**。这一层我能讲清机制和排查路径，但不会假装写过。

## Q12 过程中定位并解决了哪些问题

**方法论先行（一句话）**：**分层验证 + 最小复现 + 单变量对照 + 沉淀成 checklist**。每次踩坑都记成固定模板：`问题N：现象 / 根因 / 解决方法 / 排查方法`，下次换模型换版本时是**查表**而不是重新试错。

### 问题 1：Attention backend 在 PPU 上不兼容（硬件适配）

- **现象**：启动直接 `RuntimeError: q_v is only supported for Hopper GPUs`。kimi / glm5 / dpsk v32 设 `--attention-backend fa3` 都会报。
- **根因**：FA3 内部的 `q_v` 融合路径只对 Hopper 架构做了实现，PPU 不在支持列表里。
- **解决**：**拆开配置** —— `--prefill-attention-backend fa3 --decode-attention-backend flashmla`。prefill 走 FA3（大 GEMM 吃算力），decode 走 FlashMLA（吃显存带宽，且 MLA 的 latent KV 更适合 decode）。
- **固化**：写进部署 checklist —— 新模型上卡第一件事确认 attention backend 组合。

### 问题 2：W4A8 量化下开 EP 报 assert（量化 × 并行兼容）

- **现象**：`assert m == m_ and n == n_ and k == k_` AssertionError。
- **根因**：W4A8 的量化 GEMM kernel 与 DeepEP 的 shape 约定不兼容，**w4a8 不支持开 EP**。
- **解决**：w4a8 不开 EP；需要 EP 的场景改用 `w8a8_int8`。
- **固化**：整理成**"量化方式 × 并行策略"兼容矩阵**，避免下次再撞。
- **附带**：`moe-dense-tp-size` 只能填 1 或 None（填 4 直接报错）—— 这是 SGLang 当前实现限制，`>1` 需要在 DP Attention 模式下把 GPU 分子组做 attention TP，要额外的 NCCL 通信组、权重重切分、KV 子组管理，官方只实现了 `=1`（每卡独立算 attention）这一条路径。

### 问题 3：RDMA 报 bad address（最经典，一定要讲这个）

- **现象**：**P 端完全正常，D 端**在接收 KV 时报 `bad address`，服务跑不通或 TTFT 极高。
- **排查（自上而下分层验证）**：

| 层 | 检查什么 | 命令 |
| --- | --- | --- |
| 应用层 | Mooncake 是否成功 register memory、有没有 fallback 到 TCP | `MC_LOG_LEVEL=TRACE`，grep `register memory: addr` |
| Verbs 层 | 设备是否 UP、port state ACTIVE、link layer（IB/RoCE）、rate | `ibv_devinfo`、`ibstat`、`show_gids` |
| **裸流验证** | **排除网络问题**，看纯 RDMA 带宽是否正常 | `ib_write_bw` / `ib_read_bw`（perftest） |
| 内核层 | peermem 是否加载 | `lsmod \| grep peermem`、`dmesg \| grep -iE 'peer\|ib_\|mlx5'` |
| 容器/K8s 层 | 是否 request `rdma/hca`、是否 hostNetwork、`/dev/infiniband/*` 是否挂进来、`IPC_LOCK` + memlock unlimited | `kubectl describe pod`、容器内 `ibv_devinfo` |
| 网络层 | bond/eth/cni0/flannel.1 MTU 一致性、RoCE 的 PFC/ECN、GID index | `ip link show \| grep -E 'bond\|eth\|cni0\|flannel'`、`ping -M do -s 8922 <对端>` |
| 拓扑层 | 网卡与加速卡的 PCIe / NUMA affinity | `nvidia-smi topo -m`（PPU 对应工具） |

- **根因**：**Decode 机器上缺少 `alixpu-peermem` 内核模块**。这个模块是平头哥 PPU 的 peer memory 驱动（作用等同 NVIDIA 的 `nvidia-peermem`），它向内核 RDMA 子系统 `ib_core` 注册一个 **peer memory client**，让 `ibv_reg_mr` 能识别并注册**设备显存**地址，从而实现 GPUDirect RDMA：

```
无 peermem（退化路径）：卡显存 → cudaMemcpy → host bounce buffer → 网卡
                       → 对端网卡 → host buffer → cudaMemcpy → 卡显存
                       （2 次额外拷贝 + CPU 参与，且 ibv_reg_mr 注册显存直接失败）
有 peermem（GDR 路径）：网卡 ⇄ 卡显存 直接 DMA（零拷贝）
```

  模块缺失 → RDMA 层无法把显存地址映射成 HCA 可用的物理地址 → 注册内存返回无效地址 → `bad address`。
- **为什么只有 Decode 端报错**：KV 的**接收目标是 D 端显存**，接收侧注册显存这一步最直接暴露。稳妥起见 P/D 两端都要装（P 端发送时源 buffer 也在显存）。
- **解决 + 固化**：

```bash
lsmod | grep peermem
modprobe alixpu-peermem
# 写入 /etc/modules-load.d/ 保证重启自动加载
```

  验证：加载后 TRACE 日志里 register memory 成功，不再 bad address。**并写进部署 checklist —— 新机器上架第一件事就是查 peermem。**

### 问题 4：Warmup 报 `KeyError: 'choices'`（客户端假象，服务端真因）

- **现象**：`sglang.bench_serving` warmup 阶段直接失败 rc=1：

```
ValueError: Warmup failed - Please make sure benchmark arguments are correctly specified.
  File ".../sglang/bench_serving.py", line 300, in async_request_openai_completions
    if data["choices"][0]["text"]:
KeyError: 'choices'
```

  伴随的 CUDA / NVML warning 是**误导项** —— bench_serving 是纯客户端，本身不需要 GPU，可以忽略。
- **排查**：**直接 curl 服务端拿原始错误体**（客户端的解析异常永远看不出真因）。
- **根因**：`--context-length 16384` **<** 压测的 `--random-input-len 65536 --random-output-len 1536`（合计约 67K）。server 直接以**错误 JSON**（不含 `choices` 字段）拒绝请求，客户端解析 warmup 响应时抛 KeyError。
- **解决**：服务端 `--context-length`（vLLM 是 `--max-model-len`）调到 ≥ `input + output` 并预留余量，同时确认 KV cache 显存够用；客户端压测长度不能超过服务端实际支持的 context 上限。
- **同类陷阱（同样表现为 `KeyError: 'choices'`）**：`--served-model-name` 与服务端注册名不一致（回 `model not found`）；服务端权重加载失败 / KV cache OOM（请求直接 5xx）。**排查时先 curl 一次拿原始错误体即可区分。**

### 问题 5：跨机丢包 / PMTU 黑洞（网络层）

- **现象**：跨机传输间歇性丢包、带宽上不去。
- **根因**：**MTU 不一致**。物理 `bond` / `eth` 跨机不一致会丢包；Pod 网络层 `cni0` 必须跟 `flannel.1` 一致 —— `flannel.1` 是 **VXLAN 隧道，有约 50 字节封装开销**：物理 1500 → `flannel.1`/`cni0` = **1450**；物理 9000（巨型帧）→ **8950**。
- **排查**：

```bash
ip link show | grep -E 'bond|eth|cni0|flannel'
ping -M do -s 8922 <对端节点IP>    # -M do 禁止分片；8922 + 28字节IP/ICMP头 = 8950
```

### 问题 6：反直觉实验——`tp=8, dp=2` 的 TTFT 竟然变差

- **现象**：Decode 端从 `dp-size=16` 改成 `tp-size=8, dp-size=2`，**TTFT 竟然变差了**。
- **深挖（这就是"反直觉结果必须归因"）**：DP 变小意味着**每卡要扛更多请求的 attention**，KV 分片收益没了；同时 MoE 侧 all-to-all 的**分组结构变了，通信 pattern 反而更碎**。
- **原理**：关键等式 `tp-size = dp-size × moe-dense-tp-size`。Decode 每步每请求只算 1 个 token 的 attention，用 16 卡 TP 去分摊是严重浪费还要付 all-reduce。改成 `dp-size=16, moe-dense-tp-size=1` 后：**attention 层每卡独立算自己的请求，零通信**；**MoE 层仍保持 16 卡 EP**，expert 覆盖不变。
- **结论**：**D 端 `dp-size == tp-size`（即 dense_tp=1）是默认最优解**，只有单卡放不下 attention 参数时才降 dp、提 dense_tp。Kimi-K2.6 用 W4A8 量化后单卡放 attention 参数绰绰有余（MLA 的 KV 本身是压缩表示），所以 dp=16 没问题。

### 问题 7：一个"没效果"的优化——CUDA Graph 密集桶

- **做法**：`--cuda-graph-bs 1 2 3 4 5 6 7 8 10 12 14 16 18 20 22 24 26 28 30 32 40 48 56 64`（24 个密集桶）。
- **原理**：CUDA Graph 把一连串 kernel 的启动过程"录制"成静态图，之后整体"回放"，消除 CPU 逐个 launch 的开销（每层几十个 kernel × 几十层，decode 阶段 GPU 经常在"等 CPU 发活"）。因为录制时张量 shape 固定而 batch size 每步在变，所以要预录一批"桶"，运行时把实际 batch padding 到最近的桶。
- **实测结论**：**这组密集桶对压测基本没效果。**
- **归因**：说明**当前瓶颈不在 kernel launch overhead**，而是被通信 / KV 传输 / 调度占住了；或者 `dp-size=16` 下每卡 batch 本来就很小、launch 开销占比不高。
- **价值**：**这个"没效果"的结论比"有效果"更有价值 —— 它把优化方向从 CUDA Graph 排除了。**

### 问题 8：配置漂移与 warmup 失真（工程治理）

- **现象**：① warmup 用一段通用纯文本，跟编码 Agent 的真实请求（多轮对话 + system prompt + tool_calls + 长上下文代码）差距很大，预热效果有限；② warmup 脚本在 **4 个 ConfigMap 里有 4 份副本、核心逻辑 95% 相同，被 15+ 个 deploy.yaml 引用** —— 改一处要改四处，典型的配置漂移。
- **解决**：**从 litellm-proxy 网关侧录制真实请求 → 导出成 JSONL（`/capture/export-warmup`）→ 存到共享 hostPath → Pod 启动时回放**；同时把 4 份脚本合并成 **1 份共享 ConfigMap**，**差异全部收敛到环境变量**，做到 **100% 向后兼容**，按 pdev → pprod → prod 三级灰度上线。

### 问题 9：Router 资源标定（避免过度配置）

- **做法**：sgl-router 4 核 8G **对比** 64 核 128G。
- **结论**：**数据看没影响。** 因为 router 是 Rust 实现，近似 radix tree（1–3GB，受 `--max-tree-size` 封顶）+ tokenizer（200–500MB）+ runtime/in-flight buffer（0.5–1GB）+ 碎片 headroom，**稳态 RSS 就是 2~4GB**。
- **价值**：**省下了 60 核 120G 的无效申请**。判断"要不要加资源"要靠 RSS 基线（`kubectl top pod` / `cat /proc/1/status | grep VmRSS` 跑 1–2 周看曲线），不是靠感觉。真正该先做的是调参：`--max-tree-size`、`--eviction-interval-secs`、`--cache-threshold`。

---

# 三、OPPO 工作

## Q13 OPPO 的主要工作内容、遇到的困难以及怎么解决的

**先定位（一句话）**：OPPO 是做**大模型（Qwen / Andes-ViT 系列）在自研推理芯片上的量化压缩、算子对接与精度校准**。如果说 PTG 是"模型怎么在一堆卡上跑成服务"，OPPO 就是"模型怎么塞进一块位宽和算力都受限的芯片"——**两端都做过，所以我对"精度 ↔ 显存 ↔ 算力 ↔ 延迟"这条 trade-off 链的两端都有手感。**

### A. 工作内容（四块）

| 方向 | 具体做的事 |
| --- | --- |
| **大模型量化** | 主导 Qwen 系列 FP16 → **INT4 / INT8** 完整 PTQ 流程：scale / zero-point 计算、**伪量化节点**模拟精度损失、**bitpack 编码**、端到端误差分析，**精度损失 < 1%** |
| **算子拆解** | 基于模型代码绘制**推理算子流程图**，对 Attention / FFN 等模块做算子拆分，并**逐 tensor 对比**软硬件输出 |
| **硬件指令仿真** | 构建 **4-bit bit-pack 输入输出格式**，用 Python 实现**硬件指令级快速仿真**，加速量化方案验证迭代 |
| **推理链路 Debug 工具** | 独立开发 **Inference Tool**：scale / zp 自动保存、**逐层软硬件误差对比**，定位并修复 dtype 溢出、shape 错误等问题，**显著提升误差定位效率** |

**量化基础问答备着**：

- **量化公式**：$q = \mathrm{round}(x / s) + z$，$x \approx s(q - z)$；对称量化 $z=0$，非对称量化 $z \neq 0$；$s = \dfrac{x_{\max} - x_{\min}}{2^b - 1}$
- **粒度**（高频追问）：权重用 **per-channel**（每个 output channel 一个 scale，PTQ 标准做法）；激活用 **per-tensor dynamic**（运行时统计 min/max）；精度敏感层（如 Attention 的 QKV projection）试过 **per-group（group=64）**。**为什么 per-group 是主流**：per-tensor 精度损失大（outlier 主导 scale），per-channel 对激活不适用（channel 维度是动态的），per-group 是精度和硬件效率的折中
- **伪量化（fake quant）**：在前向图里插入 `quantize → dequantize` 对，数值上仍是 FP16，但**模拟了量化引入的舍入误差**，用来在上真机前评估精度损失
- **bitpack**：把多个 4-bit 值打包进一个 int32/int8，是硬件指令实际吃的格式；打包顺序、对齐、符号位处理错一个就全盘皆错

### B. 遇到的困难与解决（讲 3 个，按 STAR 结构）

#### 困难 1：INT4 精度崩——outlier 主导 scale

- **现象**：per-tensor 量化到 INT4 后精度掉超过 5%，而且**掉得不均匀** —— Attention 的 QKV projection、FFN 的 gate 层掉得特别厉害。
- **定位**：逐层统计权重 / 激活的数值分布，发现**少数通道有极端 outlier**。per-tensor 的 scale 由 $\max|x|$ 决定 → **被 outlier 拉大** → 绝大部分正常值被挤到极少数几个量化格点上，有效位宽远低于 4 bit。
- **解决**：
  1. **粒度细化**：per-tensor → per-channel → **per-group（group=64/128）**，让 outlier 只污染自己那一组；
  2. **混合精度**：对 outlier 特别严重的少数通道**单独保留高精度**；
  3. 借鉴 **GPTQ / AWQ** 的思路：按激活重要性对权重加权，并做**量化误差补偿**（把当前层的量化误差传播到后续未量化的权重上修正）。
- **结果**：**精度损失收敛到 < 1%**。

#### 困难 2：误差累积定位不了——开发了 Inference Tool

- **现象**：端到端输出不对，但**不知道是从哪一层开始偏的**；芯片算子和 PyTorch 参考实现的数值行为不一致。
- **困难在哪（这是重点，要说清为什么难）**：
  - 硬件**不能直接 dump 中间 tensor**，要一层层单独跑；
  - 量化参数（scale / zp）**散在各处**，手工比对一层要几十分钟，几十层根本比不完；
  - **dtype 溢出、shape 错误这类低级问题会伪装成"算法不对"**，把人引到错误的方向上排查半天。
- **解决**：独立开发 **Inference Tool**：
  - **自动保存每层的 scale / zp**，不用手工记录；
  - 把硬件输出和软件参考输出**逐 tensor 对齐比对** —— shape、dtype、数值分布，加上误差指标（SNR / cosine similarity / max abs diff）；
  - 一次跑出**全层误差报告**，直接看出"误差从第 N 层开始跳变"。
- **结果**：**显著提升误差定位效率**，据此定位并修复了 **dtype 溢出、shape 错误**等问题。

#### 困难 3：验证迭代太慢——用 Python 做指令级仿真

- **现象**：每验证一个量化方案都要**上真机**：编译 → 烧写 → 运行，一轮很久，而且硬件资源要排队。方案空间很大（粒度 × 位宽 × 哪些层混合精度），根本试不完。
- **解决**：构建 **4-bit bit-pack 的输入输出格式**，用 **Python 实现硬件指令级的快速仿真** —— 在 CPU 上模拟硬件的量化/反量化/累加行为，**包括位宽截断、溢出回绕、累加顺序**这些真正会造成软硬件差异的细节。先在仿真环境里筛掉大部分不靠谱的方案，再上真机验证。
- **收益**：方案迭代周期显著缩短；而且**仿真和真机结果对齐之后，仿真输出还能当"预期值"用于回归测试**。

#### 困难 4（备选）：算子拆解的融合边界导致数值不一致

- **现象**：同一个 Attention / FFN 拆成硬件算子时，**融合边界不同会导致数值行为不同**。
- **典型坑**：softmax 前的 scaling 放在哪一步、RMSNorm 的 eps 加在开方内还是外、**bias 是加在量化前还是量化后**、累加用 FP32 还是 INT32。
- **解决**：靠**画算子流程图**把每个节点的 dtype 和量化点明确标出来，再**逐 tensor 对比**确认软硬件在每一步都对得上，而不是只看最终输出。

> [!tip] 这段的收尾句（体现成长）
> OPPO 教会我的是**"误差必须可归因"** —— 端到端不对的时候，你要有一把尺子能量出是哪一层开始偏的。这个习惯我带到了 PTG：调参必须做**单变量对照**，任何反直觉的结果（比如 `tp=8,dp=2` 的 TTFT 变差）都必须深挖到能说出**参数 → 硬件行为 → 指标**的完整因果链，说不清因果链的调参才是"调参侠"。

---

# 四、Transformer 架构

## Q14 Transformer 的架构

> **答题策略**：先给整体数据流（能画图），再逐组件讲，**最后主动切到推理视角**——这是我的强项，也是这个岗位关心的。

### 一、整体数据流（decoder-only，现代 LLM 主流）

```
token ids
  → Embedding (V × d)                       # 查表
  → L × Transformer Block:
        x ← x + Attention(RMSNorm(x))       # Pre-Norm + 因果自注意力 + 残差
        x ← x + FFN(RMSNorm(x))             # Pre-Norm + SwiGLU + 残差
  → RMSNorm (final)
  → LM Head (d × V) → logits → 采样
```

（RoPE 不加在这里，而是在每个 block 内部作用在 Q / K 上）

### 二、逐组件拆解

**1）Embedding + 输出层**

- Embedding：$[B,T] \to [B,T,d]$，查表；
- LM Head 常与 Embedding **权重绑定（weight tying）**，省一份 $V \times d$ 的参数；
- 输出 logits 经采样：**temperature / top-k / top-p / repetition penalty**。注意**采样参数不影响 KV**（作用在 logits 之后），所以不同采样参数的请求可以安全共享 prefix KV。

**2）位置编码**

- 原始 Transformer：**正弦绝对位置编码**，直接加在 embedding 上；
- 现代 LLM：**RoPE（旋转位置编码）**，作用在 **Q / K 上（是旋转不是相加）**，使 $q_i^\top k_j$ 只依赖**相对位置** $i-j$：

$$
\theta_i = b^{-2i/d},\qquad q' = q \odot \cos(m\theta) + \mathrm{rot}(q) \odot \sin(m\theta)
$$

- **长上下文外推**：位置插值、**NTK-aware**（按扩展倍数 $s$ 放大 base：$b' = b \cdot s^{d/(d-2)}$）、YaRN。

**3）Self-Attention（核心）**

$$
\mathrm{Attention}(Q,K,V) = \mathrm{softmax}\!\left(\frac{QK^\top}{\sqrt{d_k}}\right)V
$$

- **为什么除 $\sqrt{d_k}$**：点积的方差随维度线性增长，不缩放会把 softmax 推进**饱和区** → 梯度消失；
- **因果 mask（decoder-only 的关键）**：下三角 mask，位置 $i$ 只能看 $\le i$，上三角置 $-\infty$ 再 softmax。**这是自回归生成能"边生成边复用 KV"的前提**；
- **复杂度**：时间 $O(T^2 d)$，attention 矩阵显存 $O(T^2)$ → **FlashAttention** 用 tiling + online softmax 把显存降到 $O(T)$，**不物化 $T \times T$ 矩阵**。

**4）Multi-Head**

把 $d$ 切成 $h$ 个 head，各 head 在 $d_k = d/h$ 的子空间独立做缩放点积注意力，concat 后过 $W_O$：

$$
\mathrm{head}_i = \mathrm{Attention}(QW_i^Q, KW_i^K, VW_i^V),\qquad \mathrm{MHA} = \mathrm{Concat}(\mathrm{head}_1,\dots,\mathrm{head}_h)W^O
$$

**意义**：让模型在多个子空间关注不同类型的关系（语法、指代、位置模式），比单头表达力强。

**5）Attention 变体（面试高频，务必会）**

| 变体 | Q 头数 | KV 头数 | KV Cache 大小 | 代表模型 |
| --- | --- | --- | --- | --- |
| **MHA** | $h$ | $h$ | 1× | GPT-2、原始 Transformer |
| **MQA** | $h$ | 1 | $1/h$ | PaLM |
| **GQA** | $h$ | $g$（$1<g<h$） | $g/h$ | LLaMA-2/3、Qwen2+ |
| **MLA** | $h$ | 低秩 latent 压缩 | **最小** | DeepSeek-V2/V3、Kimi |

- **为什么要压 KV 头**：decode 阶段是 memory-bound，**KV Cache 是显存主要消耗**，压 KV 头直接换更大 batch 和更长上下文；
- **GQA 实现**：`K.repeat_interleave(h // g, dim=0)` 把 KV 头复制对齐到 Q 头；
- **MLA**：把 KV 投影到**低秩 latent 空间**再存（+ 解耦 RoPE），KV Cache 显著变小 —— **这也是我们 PD 分离时 KV 传输量能压下来的根本原因**，MLA 架构的模型做长上下文 + PD 分离天然占优；
- **Cross-Attention**：Q 来自 decoder、K/V 来自 encoder 输出，只存在于 encoder-decoder 架构。

**6）FFN / MLP**

- 原始：$\mathrm{FFN}(x) = \mathrm{ReLU}(xW_1 + b_1)W_2 + b_2$，中间维度 $d_f = 4d$；
- 现代：**SwiGLU**

$$
\mathrm{SwiGLU}(X) = \big(\mathrm{SiLU}(XW_1) \odot XW_2\big)W_3
$$

  一路过 SiLU 当**门**、一路当**内容**，逐元素相乘后投影回 $d$。为保持参数量与原始 FFN 相当，$d_f \approx 8d/3$（实际常取 11008 / 14336 这类**对齐到 128 倍数**的值，为了 GEMM 效率）；

- **MoE（重点，我天天在部署）**：把 FFN 换成 **N 个 expert + router（top-k 门控）**，激活参数远小于总参数。比如 Qwen3.5-397B-**A17B** = 总参数 397B、**每 token 只激活 17B**。
  - **收益**：同等算力下模型容量大得多；
  - **代价**：**all-to-all 通信**（DeepEP，两阶段都要开，因为 expert 数几百个单卡放不下）、**负载不均**（热点 expert）、**显存要放全部 expert**（靠 EP 切分）、`w4a8` 量化还不支持开 EP。

**7）Normalization**

- LayerNorm → **RMSNorm**（去掉减均值的中心化，只除以均方根）：

$$
\mathrm{RMS}(x) = \sqrt{\tfrac{1}{d}\textstyle\sum_i x_i^2 + \epsilon},\qquad y = \frac{x}{\mathrm{RMS}(x)} \odot g
$$

  **更快（少一次 reduce）、效果相当**；
- Post-Norm → **Pre-Norm**（norm 放在子层之前）：**深层网络训练更稳定**，是现代 LLM 标配（残差通路上没有 norm 阻挡，梯度可以直通到底）。

**8）残差连接**：$x = x + \mathrm{Sublayer}(x)$，保证梯度通路、支持堆很深。

**9）激活函数演进**：ReLU → GELU → **SiLU / Swish**（SwiGLU 的门）。

### 三、推理视角（主动切过来，这是我的主场）

**1）两阶段，性质完全不同**

| | Prefill | Decode |
| --- | --- | --- |
| 一次算多少 token | $T$ 个（整个 prompt） | **1 个** |
| 瓶颈 | **compute-bound**（大 GEMM，算力打满） | **memory-bound**（要把全部权重 + KV 从 HBM 读一遍，算力闲置） |
| 决定指标 | **TTFT** | **TPOT / ITL** |
| 优化手段 | chunked prefill、TP、EP、prefix cache | CUDA Graph、DP Attention、量化、投机解码、加大 batch |

**2）KV Cache（一切优化的起点）**

因为因果 mask，**历史 token 的 K/V 永远不变** → 缓存起来，每步只算新 token：

$$
\text{KV bytes per request} = 2 \times L \times H_{kv} \times d_{head} \times \text{dtype} \times T
$$

（前面那个 2 是 K 和 V；MLA 会小很多，因为压到 latent 空间）

**由此衍生出我做的所有工作**：

- 显存碎片 → **PagedAttention**（block table 逻辑→物理映射，类比虚拟内存页表，**外部碎片为 0**，只有最后一个 block 平均浪费 `page_size/2` 的**内部碎片**）；
- 重复计算 → **RadixAttention / prefix caching**（radix tree 做最长前缀匹配，**cache key 就是 token id 序列本身**，所以不存在"内容变了命中旧 KV"的正确性问题）；
- 两阶段性质不同 → **PD 分离**；
- 单请求 KV 跨节点搬运 → **Mooncake / NIXL + RDMA**；
- 显存不够 → **多级缓存 HiCache**（GPU HBM → Host DRAM → NVMe）。

**3）$2N$ 法则（能报数很加分）**：每个 token 前向约 $2N$ FLOPs（$N$ = 激活参数量，乘加各算一次）→ 可以直接估算 prefill 时间：$T_{\text{prefill}} \approx \dfrac{2N \times T_{\text{tokens}}}{\text{GPU 有效算力}}$。这也是 PD 配比理论估算的基础。

**4）优化手段对应架构的哪一层**

| 层 | 手段 |
| --- | --- |
| 调度层 | Continuous batching、Chunked prefill、`schedule-conservativeness` |
| 并行层 | TP / EP / **DP Attention** / PP（在线服务不开 PP，pipeline bubble 让延迟不可控） |
| Kernel 层 | CUDA Graph、FlashAttention / FlashMLA、算子融合 |
| 数值层 | W4A8 / W8A8-INT8 量化、FP8 |
| 内存层 | PagedAttention、radix cache、HiCache |
| 解码层 | 投机解码 MTP / EAGLE / Medusa |
| 架构层 | GQA / MLA、MoE、SwiGLU、RMSNorm |

### 四、原始 Transformer（encoder-decoder）对比（备着，被问到再说）

**Encoder**（双向 self-attention，能看到全文）+ **Decoder**（causal self-attention + **cross-attention**：Q 来自 decoder、K/V 来自 encoder 输出）+ 各自的 FFN。

**为什么现在 LLM 基本都是 decoder-only**：

1. **训练目标统一** —— 全部参数都在做同一件事（next token prediction），每个 token 都产生 loss，训练效率高；
2. **in-context learning 能力强**，few-shot 表现好；
3. **工程上只需一套 KV Cache 机制**，推理链路简单。

**其他形态**：Encoder-only（BERT）用于理解/分类类任务；Encoder-Decoder（T5 / BART）用于翻译、摘要这类有明确输入输出的任务。

---

# 五、手撕

## Q15 手撕：最长递增子序列（LC300）

> 已是 CodeTop 手册第 25 题（[[Leetcode/CodeTop手撕40题背诵手册]]，标注"快手一面手撕"）。**面试要写 O(n log n) 版本，O(n²) DP 只当兜底或先讲思路。**

**题目**：给定整数数组 `nums`，返回其中最长**严格递增子序列**的长度。子序列**不要求连续**，只要求保持相对顺序。

### 解法一：贪心 + 二分（O(n log n)）——**首选，写这个**

**核心思想**：维护一个 `tails` 数组，**`tails[k]` = 所有长度为 `k+1` 的递增子序列中，结尾最小的那个值**。

- 为什么存"最小结尾"：结尾越小，**后面能接上的数就越多**，这个长度的子序列"潜力"越大；
- `tails` 一定是**严格递增**的（可证），所以能二分；
- 对每个 `x`：在 `tails` 里找**第一个 ≥ x 的位置**替换掉它（让那个长度的结尾变得更小）；如果 `x` 比所有都大，就 **append**（长度 +1）；
- **答案就是 `len(tails)`**。

> ⚠️ **最容易踩的坑（面试官一定会追问）**：`tails` **不是**真实的 LIS 序列！它只是一个长度正确的辅助数组。比如 `nums = [3,5,6,2,5,4,19,5,6,7,12]`，过程中 `tails` 可能出现 `[2,4,5,6,7,12]`，其中 `2,4` 的相对顺序在原数组里并不成立。

```python
from typing import List
import bisect

class Solution:
    def lengthOfLIS(self, nums: List[int]) -> int:
        if not nums:
            return 0

        # tails[k]：长度为 k+1 的递增子序列中，最小的结尾值
        tails = []

        for x in nums:
            # 在 tails 中找第一个 >= x 的位置
            # 严格递增用 bisect_left；若题目允许相等（非严格递增）用 bisect_right
            i = bisect.bisect_left(tails, x)

            if i == len(tails):
                # x 比所有结尾都大 → 可以延长最长子序列
                tails.append(x)
            else:
                # 替换掉第一个 >= x 的结尾，让该长度的结尾变小（潜力更大）
                tails[i] = x

        return len(tails)
```

**手写二分版（面试官常要求不许用 `bisect`）**：

```python
class Solution:
    def lengthOfLIS(self, nums: List[int]) -> int:
        tails = []

        for x in nums:
            # 手写二分：找第一个 >= x 的下标（左闭右开）
            lo, hi = 0, len(tails)
            while lo < hi:
                mid = (lo + hi) // 2
                if tails[mid] < x:
                    lo = mid + 1
                else:
                    hi = mid
            if lo == len(tails):
                tails.append(x)
            else:
                tails[lo] = x

        return len(tails)
```

- **时间复杂度**：$O(n \log n)$ —— n 个元素，每个二分 $O(\log n)$
- **空间复杂度**：$O(n)$ —— tails 最长为 n

### 解法二：动态规划（O(n²)）——先讲思路 / 兜底

**定义**：`dp[i]` = **以 `nums[i]` 结尾**的最长递增子序列长度。

**转移**：对每个 `i`，看它前面所有 `j`，只要 `nums[j] < nums[i]`，就能把 `i` 接到 `j` 后面：

$$
dp[i] = \max_{j < i,\; nums[j] < nums[i]} \big(dp[j] + 1\big),\qquad \text{初值 } dp[i] = 1
$$

**答案**：$\max_i dp[i]$（**注意不是 `dp[n-1]`**，因为 LIS 不一定以最后一个元素结尾）。

```python
class Solution:
    def lengthOfLIS(self, nums: List[int]) -> int:
        n = len(nums)
        if n == 0:
            return 0

        # dp[i] 表示以 nums[i] 作为结尾的最长递增子序列长度
        dp = [1] * n
        ans = 1

        # 从左到右枚举每个位置作为子序列结尾
        for i in range(n):
            # 枚举 i 前面的所有位置
            for j in range(i):
                # 只有 nums[j] < nums[i]，nums[i] 才能接在 nums[j] 后面
                if nums[j] < nums[i]:
                    dp[i] = max(dp[i], dp[j] + 1)
            ans = max(ans, dp[i])

        return ans
```

- **时间** $O(n^2)$，**空间** $O(n)$

### 追问预案

**Q：怎么还原出具体的子序列（不只是长度）？**

记录每个元素**被放入时的长度**和**前驱索引**，从最长的末尾回溯：

```python
class Solution:
    def lengthOfLIS(self, nums: List[int]) -> int:
        import bisect
        n = len(nums)
        tails = []           # tails[k] = 长度 k+1 的最小结尾值
        tails_idx = []       # 对应结尾值在 nums 中的下标
        prev = [-1] * n      # 每个位置的前驱下标
        length = [0] * n     # 每个位置作为结尾时的 LIS 长度

        for i, x in enumerate(nums):
            pos = bisect.bisect_left(tails, x)
            if pos == len(tails):
                tails.append(x); tails_idx.append(i)
            else:
                tails[pos] = x; tails_idx[pos] = i
            # 前驱是"长度比自己小 1"的那条链的当前结尾
            prev[i] = tails_idx[pos - 1] if pos > 0 else -1
            length[i] = pos + 1

        # 从最长的那条链的末尾往前回溯
        k = max(range(n), key=lambda i: length[i])
        seq = []
        while k != -1:
            seq.append(nums[k])
            k = prev[k]
        seq.reverse()
        return len(seq)      # 或返回 seq
```

**Q：严格递增 vs 非严格递增（允许相等）怎么改？**

- **严格递增**（本题）：用 `bisect_left` —— 遇到相等的值会**替换**，不延长；
- **非严格递增**（`<=` 也算）：用 `bisect_right` —— 遇到相等的值会**追加**，允许延长。
- DP 版对应：`nums[j] < nums[i]` 改成 `nums[j] <= nums[i]`。

**Q：变体题**

| 题 | 差异 | 解法 |
| --- | --- | --- |
| **LC674 最长连续递增子序列** | 要求**连续** | 双指针 / 一次遍历，$O(n)$，不需要二分 |
| **LC354 俄罗斯套娃信封** | 二维，宽和高都要严格递增 | 宽度**升序** + 同宽时高度**降序**排序，再对高度做 LIS（降序是为了避免同宽的信封互相套） |
| **LC673 最长递增子序列的个数** | 要数量不只长度 | DP 加一个 `cnt[i]`，`dp[i]` 相等时累加计数 |
| **LC1626 无矛盾的最佳球队** | 带权 LIS | DP，`dp[i] = score[i] + max(dp[j])` for 合法 j |

**Q：为什么贪心 + 二分是对的？（要能说清证明思路）**

**归纳证明 `tails` 始终严格递增，且 `tails[k]` 确实是长度 `k+1` 的递增子序列的最小结尾**：
- 处理 `x` 时，若 `x` 大于所有 `tails`，则 `x` 可以接在最长链后面，长度 +1，且新结尾就是 `x`（最小）；
- 若 `x` 替换了 `tails[i]`，说明存在一条长度为 `i` 的链（结尾 `< x`，因为 `tails[i-1] < x`），把 `x` 接上去得到长度 `i+1` 的链，其结尾 `x` **≤ 原来的 `tails[i]`** → 更新后仍是该长度的最小结尾；
- `tails` 严格递增保证二分正确。
- **`len(tails)` 单调不减**，最终值就是最长长度。

---

# 六、反问面试官（准备 3 个，按时间挑）

**关于业务与规模（快手是短视频/推荐场景，这些问得很贴）**：

1. 团队的推理服务主要承载哪类 workload？是**推荐/排序类的小模型高 QPS**，还是**大模型生成类**（多模态理解、视频描述、AIGC、Agent）？两者对 Infra 的要求差别很大，我想了解重心在哪。
2. 目前在线服务的规模量级——大概多少卡、多少模型、峰值 QPS 是多少？PD 分离 / 投机解码 / 多级 KV 缓存这些落地到什么程度了？
3. 快手的流量有非常明显的**波峰波谷**（晚高峰 vs 凌晨），团队是走**静态配比 + 预留**，还是已经在做**动态调度/弹性伸缩**（类似 Dynamo Planner 那种按 SLA 预测副本数）？弹性实例（同一 GPU pool 里按需切 P/D 角色）有没有在生产上跑？

**关于团队与技术方向**：

4. 团队的调度层是自研还是基于开源（Dynamo / SGLang router / vLLM）二开？我可以贡献在哪一块？
5. 硬件上是单一 GPU 还是**多种加速卡混合**？我在平头哥 PPU（非 NVIDIA 生态）上做过大量适配踩坑（attention backend、量化 × EP 兼容矩阵、peermem、RDMA 调参），这类异构硬件适配是团队的需求吗？
6. KV Cache 这块有没有往**多级缓存 / 分布式 KV 池**（Mooncake Store、3FS 那类）方向做？我们内部评估过 HiCache，卡在了容量评估这一步。

**关于成长**：

7. 这个岗位入职后前 3~6 个月，最希望我先解决的具体问题是什么？

---

# 七、面试前 30 分钟速记卡

> 只背这一页。**报数、报参数名、报因果链**，不要只说"优化了"。

## 数字弹药

| 指标 | 数值 |
| --- | --- |
| 平台总资源 | **21 机 / 336 张 PPU 卡**，**13 个**大模型服务，利用率 **100%**（0 空闲） |
| 单模型生产配比 | Kimi-K2.6 **3P2D = 48P + 32D = 80 卡**（router × 2） |
| 最大占卡模型 | DeepSeek-V4-Flash **144 卡（43%）** |
| 硬件 | 平头哥 PPU 真武 810E，**单卡 96GB HBM，显存大 / 算力低** |
| SLA | **TTFT P99 < 2~3s，TPOT < 50~60ms** |
| bound line | **并发 30 时 TPOT 升到 60ms** |
| 平均输入长度 | **80K+ tokens**（长输入短输出 → 配比偏 P） |
| KV 占用率健康区间 | **0.6~0.8**；**> 0.9 = decode 容量见底** |
| 关键参数 | `mem-fraction-static` **P 0.9~0.92 / D 0.7~0.8**；`page-size 64`；`chunked-prefill-size 163840`；`schedule-conservativeness 0.3`；`dp-size 16`；`moe-dense-tp-size 1`；`MC_NUM_QP_PER_EP 4`；RDMA **8 张** `mlx5_bond_0..7` |
| 环境 | **3 套**（pdev / pprod / prod），GitOps：Gitea + ArgoCD + Kustomize |
| warmup 治理 | **4 份 ConfigMap → 1 份**，影响 **15+** deploy.yaml，**100%** 向后兼容 |
| OPPO | FP16 → **INT4/INT8**，精度损失 **< 1%** |

## 十句必答金句

1. **为什么 PD 分离**：Prefill compute-bound、Decode memory-bound，混部时新 prefill 抢算力导致 TPOT 抖动；PPU 显存大算力低，拆开才能各取所需。
2. **配比怎么定**：理论估算定方向 → 阶梯压测找瓶颈侧 → SLA 硬约束下取成本最优 → 上线后用"并发–TPOT 正相关曲线"反推 bound line → 长期靠动态调度替代静态配比。
3. **怎么识别对方（三层）**：**etcd/注解解决"谁在哪"，bootstrap server（TCP 带外）解决"RDMA 怎么建连"，bootstrap_room 解决"这次 KV 是谁的"。**
4. **DGD**：一份 YAML 描述整套服务拓扑图；`replicas` 就是 P/D 配比；operator reconcile 把 graph 拆成 component，component 再生成 Deployment/Pod/Service。**graph 报错 = 顶层编排，component 报错 = 某角色起不来。**
5. **命中率 vs 占用率**：**命中率是"计算能不能省"，占用率是"显存够不够"**；**占用率是红线、命中率是收益，永远先保占用率**；最有效的平衡是**架构级解耦**——命中率只在 P 端优化，占用率只在 D 端控制，两个目标不抢同一块显存。
6. **K8s 启动**：apply → 认证鉴权 → **准入 webhook** → etcd → scheduler 过滤打分绑定 → kubelet → CRI 拉镜像 → sandbox → CNI 配网 → 挂卷 → initContainers → 主容器 → **startupProbe → readinessProbe（才进 Endpoints）→ livenessProbe**。推理 Pod 特殊在：extended resource（gpu + `rdma/hca`）、**hostNetwork 必须开**、`IPC_LOCK` + memlock、startupProbe 防 CrashLoopBackOff、MTU 对齐。
7. **RDMA bad address 根因**：Decode 机缺 `alixpu-peermem` → `ibv_reg_mr` 无法注册设备显存 → bad address。排查靠**分层验证 + 最小复现**（先 `ib_write_bw` 打裸流排除网络，再 `lsmod | grep peermem`）。
8. **反直觉实验**：`tp=8, dp=2` 的 TTFT 反而变差 —— DP 变小 → 每卡扛更多 attention、KV 分片收益没了，MoE all-to-all 分组变碎。结论：**D 端 `dp-size == tp-size`（dense_tp=1）是默认最优**。
9. **没效果的实验同样有价值**：CUDA Graph 密集桶对压测无改善 → **瓶颈不在 kernel launch，而在通信/KV 传输/调度** → 排除了一个优化方向。
10. **论文 ↔ 工作的同构性**：论文的"卸载决策 + 缓存替换"≈ 推理平台的"请求路由 + KV Cache 驱逐"；论文的 **CTDE**（中心 critic 训练、边缘 actor 执行）≈ **sgl-router 近似全局 radix tree 选 P + P 本地精确匹配**，也 ≈ **Dynamo Planner 中心决策副本数 + worker 本地自治 batching**。

## 三条绝对不要说的话

- ❌ "我调了一下参数性能就变好了"（**没有对照组的调参是玄学**，一定要说"单变量对照 + 能讲出因果链"）
- ❌ "这块是别人做的我不太清楚"（**说清边界比含糊过去好**："这层我用过、排查过，但没做过内核开发"）
- ❌ 编数字（**不确定的就说需要回去核对**，尤其是论文的具体算法实现和 RDMA 实测速率）

## 仍待补充（面试中若被追问，坦诚说"需要回去核对"）

- [ ] RDMA 调优后的**实测传输速率**（xx GB/s）、与 ICN 理论带宽（700 GB/s）的对比、KV 传输耗时占 TTFT 的比例（与商汤 Q9 / 百度 Q8 是同一个待补项）
- [ ] 线上 prefix cache **命中率实测数据**（`--enable-cache-report` 有出，未整理成图表）
- [ ] 论文的**具体算法族**（MAPPO / QMIX / MADDPG）、regret 项的**具体加入位置**、实验 baseline 与主要数字
- [ ] 平台服务的**内部用户数 / 日请求量**；GitOps 带来的**上线周期缩短**量化数字
- [ ] PPU 看板口径核对：看板 Kimi-K2.6 显示 **64 卡**，与 **3P2D = 80 卡**不一致（是单环境快照还是配比已调整？）；"13 个大模型"与"7 个在线模型"是否同口径
- [ ] warmup 改造后 TTFT P99 的**实际下降幅度**（见 [[Warmup效果对比]]）

---

## 面试后复盘（面完再填）

**答得不错的**：

**明显缺口，需要补**：

**面试官倾向判断**：

**后续行动**：
- [ ] 深读 Dynamo Operator 源码（CRD reconcile 链路、KV Router 的 overlap score 实现）
- [ ] 补 K8s 深度（scheduler 打分插件、CNI/CRI 细节、device plugin 机制）
- [ ] 补 RDMA 实测速率数字
