
## 0. 概览

本看板设计基于**NVIDIA Dynamo v1.3.0**，并在其基础上做了适配和调整：后续会详细解释每个面板的指标含义、计算公式与判读方法，最后给横向对比与选用建议。

**四个看板分工**：

| #   | 看板                                | 一句话定位                                | 主切分变量                     | 外部依赖                                         |
| --- | --------------------------------- | ------------------------------------ | ------------------------- | -------------------------------------------- |
| 1   | **Dynamo Dashboard**              | 数据面服务质量，**按模型**看延迟/吞吐/缓存             | model                     | 无                                            |
| 2   | **Dynamo Disaggregated Analysis** | 数据面硬件视角，**P/D 分离**调优与 GPU/NVLink 利用率 | namespace                 | 重（DCGM + kube-state-metrics + node-exporter） |
| 3   | **Dynamo Planner Dashboard**      | 控制面弹性决策，**扩缩容预测**与 SLA 达成            | namespace                 | 需启用 Planner                                  |
| 4   | **Dynamo Operator**               | 控制面 K8s 编排，**CRD 调谐**与准入校验健康度        | namespace + resource_type | 无                                            |

**来源**：https://github.com/ai-dynamo/dynamo/tree/v1.3.0/

## 1. Dynamo Dashboard —— 按模型看

> **背景：一次推理请求的生命周期与核心指标**
> 一个请求进来后分两个阶段：先 **prefill**（把整段输入 prompt 一次性算完、生成第一个 token），再 **decode**（逐个往外吐后续 token）。由此定义几个关键延迟：
> - **TTFT**（Time To First Token，首字延迟）：从请求进来到吐出第一个字的等待，主要由排队 + prefill 决定——"回车后要等多久"。
> - **ITL**（Inter-Token Latency，出字间隔）：decode 阶段相邻两个 token 的间隔，决定出字快慢；〖1〗 ≈ 每秒出字数。
> - **E2E**（端到端总时长）：一个请求从进入到说完的总耗时，近似满足 〖2〗。
> - **ISL / OSL**（Input / Output Sequence Length）：输入 / 输出的 token 数。ISL 越长 prefill 越重（TTFT 升），OSL 越长 decode 越久（E2E 升）。
> - **RPS**（Requests Per Second）：每秒进来多少请求，是负载度量，其他曲线都要对照它判读。
> - **分位数 P50/P90/P99**："X% 的请求都比这个值快"。P50 是典型体验、P99 是最差体验，比平均值更能反映长尾。
> - **KV cache / 前缀缓存**：把已算过的 token 的中间结果（Key/Value）缓存起来，后续请求若**前缀命中**就能跳过这部分 prefill，直接降低 TTFT；命中的那部分就是 **Cached Tokens**。
> - **worker**：真正跑模型推理的实例（一个 pod）；**router / KV routing**：前面的路由层，负责挑一个前缀命中率高的 worker 来处理请求。
https://app-grafana-dev.eng.t-head.cn/d/97ae8df9-138a-4f7a-9b0f-635b77d818fe/dynamo-dashboard?orgId=1
### Row 1 · Overview（区间汇总，7 项）

![[Pasted image 20260811171222.png]]

| 参数名                  | 单位            | 计算公式                                                    | 详细解释                                                                     |
| -------------------- | ------------- | ------------------------------------------------------- | ------------------------------------------------------------------------ |
| Request Success Rate | percent (%)   | 〖3〗     | 只扣掉服务端内部错误，用户取消、参数非法、过载被拒都仍算成功。所以它反映的是"后端有没有 bug"，健康时应恒为 100%。           |
| Total Requests       | short（个）      | 〖4〗                           | 窗口内的请求总数，是所有平均值和分位数的统计基数。基数太小分位数就不可信，为 0 说明没流量或采集断了。                     |
| Input Tokens         | short（个）      | 〖5〗                                   | 窗口内输入 token 总量，代表 prefill 侧的工作量与成本。与输出量的比例决定系统是 prefill 重还是 decode 重。    |
| Output Tokens        | short（个）      | 〖6〗，吞吐 〖7〗         | 窗口内生成的 token 总量，除以窗口时长 〖8〗 就是系统总吞吐（tok/s），是产能的核心口径。                      |
| Average TTFT         | ms            | 〖9〗        | 从请求进来到吐出第一个字的平均等待时间，包含排队、路由和 prefill，决定"回车后要等多久"。                        |
| Average ITL          | ms            | 〖10〗 | 相邻两个输出 token 之间的平均间隔，决定出字快慢；〖11〗 就是每秒出字数。                          |
| Average E2E Latency  | s（注意与上两项单位不同） | 〖12〗          | 一个请求从进入到说完的平均总时长。它满足 〖13〗，所以必须结合输出长度才有意义。 |


### Row 2 · Frontend（对外服务质量，9 项）
![[Pasted image 20260811171322.png]]

| 参数名                       | 单位             | 计算公式                                                                                                        | 详细解释                                                             |
| ------------------------- | -------------- | ----------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| Frontend RPS              | req/s          | 〖14〗                                                                      | 每秒进来多少请求，是负载的度量。其他所有曲线都要对照它判读：RPS 降而延迟升，说明系统已劣化。                 |
| E2E Request Latency       | s              | 〖15〗                                                                               | 端到端耗时的分布。P50 是典型体验、P99 是最差体验，看的是分布形状而不是单个数（MAX 为桶上界，只作量级参考）。     |
| Request Outcome Breakdown | reqps（堆叠）      | 〖16〗，〖17〗 | 把请求速率按结果分色堆叠，用来回答"失败的请求是怎么失败的"。理想图形是只有 success 一条带。              |
| Active vs Queued Requests | short（并发数，瞬时值） | 〖18〗；〖19〗                                              | 瞬时并发水位与排队长度：active 是正在跑的，queued 是还没吐出第一个字、卡在排队的。queued 持续上涨就是积压。 |
| TTFT (p50/p90/p99)        | ms             | 〖20〗                                                                                                 | 首字延迟的分布，比平均值可靠。P99 偏高说明有请求在 prefill 队列里等。                        |
| ITL (p50/p90/p99)         | ms             | 〖21〗                                                                                                  | 出字间隔的分布。分位差大说明部分请求的 decode 被打断过（抢占或缓存换出）。                        |
| ISL Distribution          | short（token 数） | 〖22〗                                                                                                  | 输入长度（prompt 大小）的分布，是性能的自变量：输入变长，延迟自然变长。                          |
| Output Size Distribution  | short（token 数） | 〖23〗                                                                                                  | 输出长度的分布，是 decode 侧工作量的来源。判断 E2E 合不合理必须先看它。                       |
| Cached Tokens             | short（token 数） | 〖24〗，复用率 〖25〗                                                            | 输入里有多少 token 命中了前缀缓存、可以跳过 prefill。越高越好，TTFT 会明显下降。               |

### Row 3 · KV Routing（路由内部，5 项 —— 仅 KV-aware router 模式有数据）
![[Pasted image 20260811171507.png]]

| 参数名                              | 单位               | 计算公式                                                                                        | 详细解释                                                  |
| -------------------------------- | ---------------- | ------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| Per-Worker Active Decode Blocks  | short（block 数）   | 〖26〗，按 worker 分线                                                                        | 每个 worker 当前占用了多少 decode KV 显存块。用来看负载是否均摊、缓存是否将满。     |
| Per-Worker Active Prefill Tokens | short（token 数）   | 〖27〗，按 worker 分线                                                                        | 每个 worker 手上正在算的 prefill token 量，看 prefill 侧忙不忙、是否偏斜。 |
| KV Hit Rate Distribution         | percentunit（0~1） | 〖28〗，取 〖29〗                                               | 路由在挑 worker 时预估的前缀命中比例。命中越多，prefill 越省，TTFT 越低。       |
| Routing Overhead Breakdown       | ms               | 〖30〗，〖31〗 | 路由自己花掉的时间（算哈希、查前缀索引、选实例）。它是纯开销，应远小于 TTFT。             |
| KV Events Applied Breakdown      | ops（堆叠）          | 〖32〗                                                  | 路由更新前缀索引的事件速率。出现失败类事件说明索引与 worker 真实缓存已经不一致。          |

### Row 4 · Workers（单实例下钻，3 项）
![[Pasted image 20260811171531.png]]

| 参数名                                 | 单位                      | 计算公式                                                                       | 详细解释                                           |
| ----------------------------------- | ----------------------- | -------------------------------------------------------------------------- | ---------------------------------------------- |
| Worker Request Breakdown Per Worker | reqps                   | 〖33〗，错误按 〖34〗 分组 | 每个实例各自承担多少请求、出多少错。用来判断调度是否均衡、哪个 pod 有问题。       |
| Worker Request Duration Per Worker  | s                       | 〖35〗，〖36〗 = worker 内部处理耗时                                        | 只算 worker 里的推理时间，不含排队与路由。它与 E2E 的差值就是花在调度上的时间。 |
| Component Throughput (bytes/sec)    | 无（实为 bytes/s，面板未设 unit） | 〖37〗，按 instance 分线                             | 端点上进出的字节速率，用来交叉验证请求量与报文大小是否正常（如是否来了超大 prompt）。 |

### 相关参数

| 关系式 | 健康表现 | 违背时的含义 |
|---|---|---|
| 〖38〗 | 两边接近 | 左边明显偏大 → 存在额外排队/路由开销 |
| 〖39〗 | 差值小且稳定 | 差值大 → 瓶颈在排队/调度，不在推理 |
| 〖40〗 vs 〖41〗（KV Hit Rate） | 两者数值接近 | 偏差大 → 路由预测不准，查 KV Events 异常 |
| 〖42〗 | 〖43〗 | 超过 → 路由本身成瓶颈 |
| Per-Worker 曲线离散度 | 小 | 大 → 路由不均衡，存在热点 |
| 〖44〗 与 〖45〗 | 同步且都低 | queued 涨而 TTFT 未涨 → 指标口径有问题（注意 queued 缺 model 过滤） |

## 2. Dynamo Disaggregated Analysis —— 按硬件看

> **背景：P/D 分离与相关硬件名词**（TTFT/ITL/prefill/decode 等见第 1 节背景）
> - **P/D 分离（Disaggregation）**：把 prefill 和 decode 拆到不同的 worker（甚至不同 GPU）上跑，各自独立扩缩容。好处是两阶段互不抢资源、可按 ISL/OSL 特征分别配比。
> - **NIXL**：P/D 分离后，prefill 算出的 KV cache 要传给 decode worker 用，这条 KV 传输通道就是 NIXL。它变慢会直接抬高 TTFT，是本盘重点观测对象。
> - **NVLink**：GPU 之间的高速互联总线，KV 传输和多卡并行都走它；带宽太低（如 < 1 GB/s）说明 NIXL 退化成了走主机内存拷贝，没吃到 NVLink。
> - **TP（Tensor Parallel，张量并行）**：把一个模型切到多张卡上并行算，卡间通信也走 NVLink。
> - **DCGM / node-exporter / kube-state-metrics**：三个额外的指标采集器，分别提供 GPU（利用率/显存/NVLink）、节点（CPU）、K8s 对象（pod 状态）指标——本盘的 GPU 与节点面板全靠它们，缺一就面板空白。
https://app-grafana-dev.eng.t-head.cn/d/dynamo-disagg-fixed/dynamo-disaggregated-analysis-fixed?orgId=1&var-datasource=Prometheus-pdev&var-namespace=app&var-job_frontend=dynamo-system%2Fdynamo-frontend&var-job_worker=All&from=1786429561311&to=1786431336242
### Row 1 · Frontend（对外服务质量，6 项，y=0 / y=8）
![[Pasted image 20260811171718.png]]

| 参数名                                       | 单位                  | 计算公式                                                                                             | 详细解释                                                       |
| ----------------------------------------- | ------------------- | ------------------------------------------------------------------------------------------------ | ---------------------------------------------------------- |
| Frontend Requests / Sec                   | 无（实为 req/s）         | 〖46〗，〖47〗                     | 前端请求速率，是负载的度量，其余曲线都要对照它判读。                                 |
| Frontend Avg Time to First Token          | 无（实为 ms，查询里已 ×1000） | 〖48〗          | 平均首 token 延迟，含 prefill 排队 + GPU 计算 + NIXL 传输               |
| Frontend Avg Request Duration             | 无（实为 ms）            | 〖49〗            | 平均端到端请求耗时。应满足 〖50〗              |
| Frontend Avg Inter-Token Latency          | 无（实为 ms）            | 〖51〗                | 平均 token 间延迟，即 decode 出字速度。                                |
| Frontend Avg Input/Output Sequence Length | 无（token 数）          | 〖52〗，〖53〗 同理，均 〖54〗 | 两条线：输入长度 ISL 与输出长度 OSL。故障。                                 |
| **Frontend Queued Requests**              | short（个，瞬时值）        | 〖55〗  | 排队等待的请求数（三阶段之和，按 pod 聚合）。面板说明称其为诊断 prefill worker 瓶颈的第一指标。 |

### Row 2 · Prefill 与 P/D 对比（3 项）
![[Pasted image 20260811171832.png]]
> 注：暂时没有开启PD分离，故只有decode有数据

| 参数名                                       | 单位    | 计算公式                                                                                                                                | 详细解释                                                                                                                                                                               |
| ----------------------------------------- | ----- | ----------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Prefill Worker Processing Time            | ms    | 〖56〗；〖57〗 取自直方图桶，按 pod 分线，均 〖58〗                    | prefill worker 处理耗时（Avg + P99），含 KV cache 经 NIXL 传输的时间。                                                                                                                            |
| Prefill Worker Throughput                 | reqps | 〖59〗，按 pod 分线                                                                         | 各 prefill worker 的请求吞吐（仅统计 generate 端点）。各 pod 量级接近 = 负载均衡良好；某 pod 显著低 = 未被有效调度或已异常；总和应与前端 RPS 匹配。                                                                                  |
| **Component Latency - Prefill vs Decode** | s     | 同图两条：〖60〗 与 〖61〗，均 〖62〗 | 全盘最有价值的面板。健康表现：两侧耗时处于同一量级、比例稳定。prefill 远高于 decode → prefill 是瓶颈（扩 prefill / 减小 chunk）；decode 远高 → decode 拥挤（扩 decode / 查 KV cache 利用率）。⚠️ decode worker 的组件名是 `backend`，不叫 decode。 |

### Row 3 · Decode 与 KV Cache（4 项）
![[Pasted image 20260811171845.png]]
![[Pasted image 20260811172103.png|265]]

| 参数名                                  | 单位             | 计算公式                                                                | 详细解释                                                                                                |
| ------------------------------------ | -------------- | ------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| Decode Worker - Request Throughput   | reqps          | 〖63〗                  | 各 decode worker 的请求吞吐。各 pod 均衡、随负载平滑变化为好。                                                           |
| Decode Worker - Avg Request Duration | s              | 〖64〗 | 各 decode worker 平均处理耗时。各 pod 曲线重叠、离散度小为好；单个 pod 突出 = 坏 worker（GPU 降频 / KV 打满 / 邻居干扰），可直接拿 pod 名定位。  |
| **KV Cache Utilization**             | percentunit    | 〖65〗（瞬时值，直接读取）                               | decode worker 的 KV cache GPU 显存占用率。理想稳定在 **0.6~0.8**：太低=显存浪费，>0.9 = decode 容量见底、batch 被压缩、ITL 随之恶化。 |
| KV Cache Blocks (Total)              | short（block 数） | 〖66〗（瞬时值，直接读取）                            | decode worker 上 KV cache 的总容量。是常量参照线，正常应为水平直线；突然变化 = worker 重启/重新分配显存。                              |

### Row 4 · GPU 与 NVLink 硬件（4 项）


> 硬件暂时不匹配，后续可适配

| 参数名                      | 单位                       | 计算公式                                                                                     | 详细解释                                                                                                                                                       |
| ------------------------ | ------------------------ | ---------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GPU Compute Utilization  | percent（0~100）           | 〖67〗（瞬时值）                                                                         | GPU SM 计算利用率。prefill GPU 应在 prefill 期间接近 100%；decode GPU 偏低是正常的。                                                                                           |
| GPU Memory Used          | gbytes（GB）               | 〖68〗                                                         | GPU 显存占用。应平稳且留有余量（离显存上限有 10% 以上空间）。持续贴顶 = OOM 风险；锯齿状剧烈波动 = KV block 反复分配释放。                                                                                |
| **GPU Memory Bandwidth** | percent（0~100）           | 〖69〗（瞬时值）                                                                        | 显存拷贝带宽利用率，尖峰即 NIXL 的 KV cache 传输。健康表现：只在 KV 传输时出现尖峰、之后回落；持续 >80% = 传输已成瓶颈。                                                                                 |
| **NVLink Bandwidth**     | GBs（GB/s，Y 轴 0~50，2 位小数） | 〖70〗，〖71〗 | 每 GPU 的 NVLink 双向总带宽。，但要两头看：**< 1 GB/s 反而是坏信号**——面板说明写明这代表跨 pod 的 NIXL KV 传输退化成了走主机内存拷贝，没吃到 NVLink/GPUDirect；> 35 GB/s 则接近 NVLink 饱和，健康区间大致 **1~20 GB/s**。 |

### Row 5 · Worker 与系统资源（4 项，y=40 / y=48）
![[Pasted image 20260811172207.png|266]]
![[Pasted image 20260811172157.png]]

| 参数名                       | 单位                | 计算公式                                                                                            | 详细解释                                                                                                      |
| ------------------------- | ----------------- | ----------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| **Worker CPU Usage**      | short（CPU 核数）     | 〖72〗                                      | worker pod 的 CPU 用量，单位就是核数。应远低于 pod 的 CPU limit；打到 limit 说明 CPU 成了瓶颈（tokenize / 采样 / 调度抢不到 CPU，会拖累 TTFT）。 |
| Node CPU Utilization      | percent（0~100，堆叠） | 〖73〗，按 instance 聚合 | 节点整体 CPU 利用率（用 idle 反推）。**< 70% 为好**，留出突发余量。                                                              |
| Worker Request Throughput | short（实为 req/s）   | 〖74〗，按组件 × pod 分线                                 | 唯一同时显示 prefill 与 decode 吞吐的面板（仅统计 generate 端点）。健康表现：〖75〗                                      |
| Worker Data Transfer      | Bps（字节/秒）         | IN：〖76〗；OUT：〖77〗                   | worker 的入/出字节速率（IN=请求、OUT=响应）。应与请求量、ISL/OSL 同步变化，用来交叉验证报文大小是否正常；IN 突增而 RPS 未涨 = 来了超大 prompt。              |

### 相关参数

| 关系式 | 健康表现 | 违背时的含义 |
|---|---|---|
| 〖78〗 | 两边接近 | 左边明显偏大 → 存在额外排队/调度开销 |
| 〖79〗 vs 〖80〗（Component Latency） | 同一量级、比例稳定 | 哪侧高哪侧就是瓶颈：prefill 高 → 扩 prefill/减小 chunk；decode 高 → 扩 decode/查 KV 利用率 |
| 〖81〗 | 两条速率守恒 | 不等 → P/D 流水线中间有堆积或丢弃 |
| 〖82〗 与 〖83〗 | 同步且都低 | queued 持续 >0 并上升 → prefill worker 已饱和 |
| 〖84〗 与 〖85〗 | 〖86〗 且 ITL 平直 | 〖87〗 伴随 ITL 抬升 → decode 容量见底，batch 被压缩 |
| 〖88〗 与 〖89〗 | NVLink 有量（1~20 GB/s）、显存带宽只见尖峰 | 〖90〗 而 〖91〗 持续高 → NIXL 退化成主机内存拷贝 |
| Per-pod 曲线离散度（吞吐 / 耗时） | 小 | 大 → 调度不均衡或存在坏 worker，可用 pod 名定位 |

## 3. Dynamo Planner Dashboard —— "决策/预测"视角，含 SLA 基线

> **背景：Planner 与本盘名词**
> - **Planner（规划器）**：Dynamo 的**自动扩缩容大脑**。它持续观测实际流量与延迟，预测未来需求，据此决定 prefill / decode 各该起几个副本——本盘就是把它的"观测 → 预测 → 决策"三步摊开看。
> - **Observed（实测）vs Predicted（预测）**：Observed 是 planner 当下**真实测到**的量（Row 2），Predicted 是它**预测未来**的量（Row 3）。二者贴合、且预测略微领先实测，才说明预测有效。
> - **SLA / SLO 基线**：你设定的延迟目标线（如 TTFT、ITL 的上限）。planner 的目标就是让实测延迟**始终压在 SLA 线之下**：越线 = 违约要扩容，远低于线 = 过度配置可缩容。
> - **replica（副本）**：某个角色的 worker 实例个数；**flapping**：副本数频繁来回扩缩，说明阈值太敏感，会反复付冷启动开销。
> - **GPU Hours**：累计消耗的 GPU 小时，用来折算每 token 成本。
> - **prefill / decode / ISL / OSL / TTFT / ITL** 等见第 1 节背景。

https://app-grafana-dev.eng.t-head.cn/d/dynamo-planner-dashboard-13/dynamo-planner-dashboard-1-3?orgId=1&var-datasource=Prometheus-pdev&var-namespace=All
>Planner 开启时有效，暂时未开启
![[Pasted image 20260811172341.png]]
### Row 1 · Worker Counts & GPU Usage（副本数与成本，4 项）

| 参数名                  | 单位                         | 计算公式                                       | 详细解释                                                                                                                 |
| -------------------- | -------------------------- | ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------- |
| Prefill Workers      | none（个，stat 取 lastNotNull） | 〖92〗                                   | 当前 prefill worker 副本数                                                                                                |
| Decode Workers       | none（个，stat 取 lastNotNull） | 〖93〗                                   | 当前 decode worker 副本数                                                                                                 |
| Cumulative GPU Hours | h（小时，2 位小数）                | 〖94〗 | planner 启动以来累计消耗的 GPU 小时，单调递增即正常。用途是算成本：〖95〗 = 每 token 成本，同等产出下越低越好；斜率突增而吞吐没涨 = 扩容浪费。 |
| Worker Count History | none（个，decimals=0）         | 〖96〗、〖97〗 同图两条时序                   | 副本数的变化过程。阶梯平缓、变化次数少为好；锯齿状频繁扩缩（flapping）说明 planner 阈值设得太敏感，会反复付冷启动开销。                                                 |

### Row 2 · Observed Metrics（planner 实际观测到的，3 项）

| 参数名 | 单位 | 计算公式 | 详细解释 |
| --- | --- | --- | --- |
| **Observed Latency (TTFT & ITL)** | ms | 同图 4 条：〖98〗、〖99〗 与目标线 〖100〗、〖101〗 | ⭐ 全盘最重要：两条实测线应持续位于对应 SLA 线之下。越贴近 SLA 线说明资源利用越充分（不浪费）；越线 = 违约，planner 应立即扩容；长期远低于 SLA = 过度配置，可缩容省钱。 |
| Observed Request Rate & Duration | 无（两条线量纲不同） | 同图两条：〖102〗 与 〖103〗 | 实测请求速率与请求耗时。Rate 平稳或缓变为好，Duration 应与 〖104〗 大致吻合。⚠️ 面板未设 unit，且把 req/s 与秒放在同一 Y 轴，量级差会压平其中一条 —— 读数请看 legend 的 lastNotNull/mean/max，别看曲线形状。 |
| Observed Sequence Lengths (ISL & OSL) | none（token 数） | 同图两条：〖105〗 与 〖106〗 | 实测输入/输出长度，是 planner 做预测的输入特征。稳定为好，剧烈漂移会直接导致 Row 3 的预测失准。 |

### Row 3 · Predicted Metrics（planner 的预测输出，3 项）

| 参数名                                    | 单位                 | 计算公式                                                   | 详细解释                                                                               |
| -------------------------------------- | ------------------ | ------------------------------------------------------ | ---------------------------------------------------------------------------------- |
| Predicted Request Rate                 | reqps              | 〖107〗，对照 〖108〗 看                       | 预测的请求速率。判据是与 Row 2 的实测速率对比：预测曲线应略微领先实测且形状吻合。滞后 = 预测无效（扩容总慢一步）；偏差大 = 预测模型不适配当前流量模式。 |
| Predicted Sequence Lengths (ISL & OSL) | token 数            | 同图两条：〖109〗 与 〖110〗 | 预测的输入/输出长度。与 Row 2 的实测值贴合为好；系统性偏高 → 会过度扩容，偏低 → 容量不足、SLA 有风险。                       |
| Predicted Replica Counts               | none（个，decimals=0） | 同图两条：〖111〗 与 〖112〗                       | 预测所需的副本数。与 Row 1 的实际副本数贴合 = planner 的决策被正常执行                                       |

## 4. Dynamo Operator —— 唯一控制面盘，与推理性能无关

> **背景：什么是 Reconciliation（调谐）**
> K8s Operator 的核心机制：不断把「实际状态」拉向「期望状态」的「对比 → 修正」循环。你 `kubectl apply` 一个 CRD 后，YAML 写的是**期望状态**，operator 里的控制循环反复做三件事——① 观察资源当前的实际状态；② 对比期望与实际的差异；③ 差什么补什么（建/删/改 Pod）直到实际 = 期望。因为 Pod 会挂、有人会手改，所以要反复跑。看板里 `Reconciliation Rate` 就是这个循环每秒执行多少次，`Errors` 是修正过程中的报错。
>
> **背景：component 与 graph 是什么**
> 二者是看板按 `resource_type` 分线的两种值，对应 operator 管的两种 CRD，关系是父子包含：
> - **graph** = `DynamoGraphDeployment`（DGD）：**整套部署**的顶层描述——一次推理服务由哪些角色（frontend / prefill / decode / router）组成、各几个副本、怎么连。通常你 apply 的就是它。
> - **component** = `DynamoComponentDeployment`（DCD）：graph 里的**单个角色**的部署。
> - 流程：提交一个 graph → operator reconcile 把它拆成多个 component → 每个 component 各自生成真正的 Deployment / Pod / Service。
> - 排查时看哪条线红：**graph 报错** = 顶层编排出问题（配置解析、角色拼装）；**component 报错** = 某个具体角色起不来（镜像 / 资源 / 探针）。
>
> **背景：什么是准入校验（Admission Webhook）**
> K8s 的一道"入口安检"：你 `kubectl apply` 任何资源时，请求会先被 API Server 拦下、同步转发给 operator 注册的 webhook 做合法性校验，**通过（allowed）才真正写入 etcd，不通过（denied）当场拒绝、apply 直接失败**。它发生在 reconcile **之前**——先过安检、再进调谐循环。因为它同步阻塞在 `kubectl apply` 的调用路径上，所以必须极快（毫秒级），慢了会拖住所有部署操作。Row 2 的三个面板就是它的请求量、耗时和拒绝量。⚠️ 它是**集群级调用**，只按 `resource_type` 过滤、**不受 `namespace` 变量影响**，切 Namespace 时数值不变属正常。
>
> **背景**
> - **gauge**：可上下浮动的瞬时值（如当前副本数、当前利用率），与之相对的是只增不减的 counter（累计计数）。
> - **SLO / SLA**：SLO 是你给自己定的服务质量目标（如 P95 延迟 < 500ms）；SLA 是对外承诺的那条底线。Row 4 两个仪表就是在看 SLO 达成率。

https://app-grafana-dev.eng.t-head.cn/d/dynamo-operator-13/dynamo-operator-1-3?orgId=1&var-datasource=Prometheus-pdev&var-namespace=All&var-resource_type=All&from=now-7d&to=now&refresh=30s

### Row 1 · Reconciliation Metrics（控制器主循环，3 项）
![[Pasted image 20260811172450.png]]

| 参数名                           | 单位         | 计算公式                                                                                             | 详细解释                                                       |
| ----------------------------- | ---------- | ------------------------------------------------------------------------------------------------ | ---------------------------------------------------------- |
| Reconciliation Rate           | reqps（次/秒） | 〖113〗，按 〖114〗 分线，〖115〗 | 控制器主循环的执行速率。平稳的低速率且 success 占绝对主导为好，空闲期应接近 0（只有周期性 resync） |
| Reconciliation Duration (P95) | s          | 〖116〗，按 〖117〗 分线                                                                    | 单次 reconcile 的耗时分布上沿。亚秒级（< 1s）且平稳为好                        |
| **Reconciliation Errors**     | reqps      | 〖118〗，按 〖119〗 分线                                   | reconcile 的报错速率，理想恒为 0                                     |

### Row 2 · Webhook Metrics（准入校验，3 项）
![[Pasted image 20260811172510.png]]

| 参数名 | 单位 | 计算公式 | 详细解释 |
| --- | --- | --- | --- |
| Webhook Request Rate | reqps | 〖120〗，按 〖121〗 分线，〖122〗 | 准入请求速率。与你的部署操作频率相符即正常，〖123〗 应占绝对多数、空闲期接近 0。突然大量 UPDATE = 有控制器在反复改同一对象。 |
| Webhook Duration (P95) | s | 〖124〗，按 〖125〗 分线 | 准入校验耗时，必须是毫秒级（远小于 1s）。它同步阻塞在 API Server 的调用路径上，变慢会直接拖慢所有 `kubectl apply`；接近 webhook timeout（通常 10s）会导致资源创建直接失败。 |
| **Webhook Denials** | reqson | 〖126〗，按 〖127〗 分线 | 准入被拒的速率，理想恒为 0，阈值 **> 0.1/s 标橙**。有值说明有人提交了不合法的 DynamoGraphDeployment，拒绝原因直接指出被触发的校验规则 —— 排查"YAML apply 上去没生效"的第一站。 |

### Row 3 · Resource Inventory（资源清单，2 项）

| 参数名                         | 单位                          | 计算公式                                            | 详细解释                                                                  |
| --------------------------- | --------------------------- | ----------------------------------------------- | --------------------------------------------------------------------- |
| Resource Inventory by State | short（个，堆叠）                 | 〖128〗，按 〖129〗 分组求和，画成时序 | 各状态资源数量的变化过程。ready 那一层占满、其他层为 0 为好；出现并停留在 pending / failed 层 = 有部署卡住。 |
| Resource Count by State     | short（个，stat 取 lastNotNull） | 〖130〗，按 〖131〗 分组求和（瞬时快照）        | 当前各状态的资源数，是上一项的即时快照。                                                  |
![[Pasted image 20260811172529.png]]
### Row 4 · Operational Health（两个 SLO 仪表，2 项）
![[Pasted image 20260811172552.png]]

| 参数名                                | 单位                   | 计算公式                                                    | 详细解释                  |
| ---------------------------------- | -------------------- | ------------------------------------------------------- | --------------------- |
| **Reconciliation Success Rate**    | percent（0~100，gauge） | 〖132〗 | reconcile 成功率，理想 100。 |
| **Webhook Admission Success Rate** | percent（0~100，gauge） | 〖133〗    | 准入放行率                 |

## 对比

| 维度 | Dynamo Dashboard | Disagg Analysis | Planner | Operator |
|---|---|---|---|---|
| 关注层 | 数据面 · 服务质量 | 数据面 · 硬件/角色 | 控制面 · 弹性决策 | 控制面 · K8s 编排 |
| 主切分变量 | **model**（单选，必选） | namespace（单选，默认值有坑） | namespace（多选 All） | namespace + **resource_type**（多选 All） |
| 指标族 | `dynamo_frontend_*`/`component_*`/`router_*` | 上述 + **DCGM/node/container/kube-state** | `dynamo_planner_*` | `dynamo_operator_*` |
| 外部依赖 | 无 | **重**（DCGM+KSM+node-exporter+NVLink CSV） | 需启用 Planner | 无 |
| 实时性 | 无自动刷新 / 24h | **10s / 30m** | 无自动刷新 / 30m | 30s / 1h |
| 统计手法 | `increase($__range)` + p50/p90/p99 | 硬编码 `rate([5m])` + p99 | 裸 gauge | `rate([5m])` + P95 + gauge |
| 分组 | 4 row，最规整 | **无 row**，平铺 | 3 row（emoji） | 4 row |
| 面板数 | 28 | 21 | 13 | 14 |

## 怎么选

- **只装一个** → Dynamo Dashboard：零外部依赖、覆盖面最广、按模型看质量。
- **做 P/D 分离调优 / 关心 GPU 与 NVLink 利用率 / 压测盯屏** → Disagg Analysis（先把 DCGM、kube-state-metrics、node-exporter 备齐，并改掉 `robert`）。
- **开了 SLA planner，想验证扩缩容与 SLA 达成、算 GPU 成本** → Planner。
- **平台方排查 CRD 不生效、webhook 拒绝、reconcile 报错** → Operator。
