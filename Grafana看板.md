
基于已解析的 4 个 JSON（v1.3.1），逐个说特点，最后给对比与选用建议。

## 1. Dynamo Dashboard —— 唯一"按模型"看的主力盘

-![[Pasted image 20260806171222.png]]

# Row 1 · Overview（区间汇总，7 项）

| 参数名                  | 单位            | 计算公式                                                    | 详细解释                                                                     |
| -------------------- | ------------- | ------------------------------------------------------- | ------------------------------------------------------------------------ |
| Request Success Rate | percent (%)   | $\dfrac{N_{req}-N_{internal}}{N_{req}}\times 100\%$     | 只扣掉服务端内部错误，用户取消、参数非法、过载被拒都仍算成功。所以它反映的是"后端有没有 bug"，健康时应恒为 100%。           |
| Total Requests       | short（个）      | $N_{req}=\Delta C_{requests}$                           | 窗口内的请求总数，是所有平均值和分位数的统计基数。基数太小分位数就不可信，为 0 说明没流量或采集断了。                     |
| Input Tokens         | short（个）      | $T_{in}=\sum_i ISL_i$                                   | 窗口内输入 token 总量，代表 prefill 侧的工作量与成本。与输出量的比例决定系统是 prefill 重还是 decode 重。    |
| Output Tokens        | short（个）      | $T_{out}=\sum_i OSL_i$，吞吐 $=\dfrac{T_{out}}{R}$         | 窗口内生成的 token 总量，除以窗口时长 $R$ 就是系统总吞吐（tok/s），是产能的核心口径。                      |
| Average TTFT         | ms            | $\overline{TTFT}=\dfrac{\sum_i TTFT_i}{N_{req}}$        | 从请求进来到吐出第一个字的平均等待时间，包含排队、路由和 prefill，决定"回车后要等多久"。                        |
| Average ITL          | ms            | $\overline{ITL}=\dfrac{\sum_i\sum_j ITL_{ij}}{N_{gap}}$ | 相邻两个输出 token 之间的平均间隔，决定出字快慢；$1000/ITL$ 就是每秒出字数。                          |
| Average E2E Latency  | s（注意与上两项单位不同） | $\overline{E2E}=\dfrac{\sum_i E2E_i}{N_{req}}$          | 一个请求从进入到说完的平均总时长。它满足 $E2E \approx TTFT + ITL \times OSL$，所以必须结合输出长度才有意义。 |

> ⚠️ 后 6 项面板内置阈值均为模板残留的 `red @ 80`（超过 80 就标红），对 token/请求数无意义，**只看数字别看颜色**。

# Row 2 · Frontend（对外服务质量，9 项）

| 参数名 | 单位 | 计算公式 | 详细解释 |
| --- | --- | --- | --- |
| Frontend RPS | req/s | $RPS=\dfrac{\Delta N_{req}}{\Delta t}$ | 每秒进来多少请求，是负载的度量。其他所有曲线都要对照它判读：RPS 降而延迟升，说明系统已劣化。 |
| E2E Request Latency | s | $P_q(E2E),\ q\in\{50,90,99\}$ | 端到端耗时的分布。P50 是典型体验、P99 是最差体验，看的是分布形状而不是单个数（MAX 为桶上界，只作量级参考）。 |
| Request Outcome Breakdown | reqps（堆叠） | $r_s=\dfrac{\Delta N_s}{\Delta t}$，$s\in\{success,\ cancelled,\ validation,\ overload,\ internal,\ \dots\}$ | 把请求速率按结果分色堆叠，用来回答"失败的请求是怎么失败的"。理想图形是只有 success 一条带。 |
| Active vs Queued Requests | short（并发数，瞬时值） | $N_{active}(t)$；$N_{queued}(t)=N_{pre}+N_{route}+N_{dispatch}$ | 瞬时并发水位与排队长度：active 是正在跑的，queued 是还没吐出第一个字、卡在排队的。queued 持续上涨就是积压。 |
| TTFT (p50/p90/p99) | ms | $P_q(TTFT)$ | 首字延迟的分布，比平均值可靠。P99 偏高说明有请求在 prefill 队列里等。 |
| ITL (p50/p90/p99) | ms | $P_q(ITL)$ | 出字间隔的分布。分位差大说明部分请求的 decode 被打断过（抢占或缓存换出）。 |
| ISL Distribution | short（token 数） | $P_q(ISL)$ | 输入长度（prompt 大小）的分布，是性能的自变量：输入变长，延迟自然变长。 |
| Output Size Distribution | short（token 数） | $P_q(OSL)$ | 输出长度的分布，是 decode 侧工作量的来源。判断 E2E 合不合理必须先看它。 |
| Cached Tokens | short（token 数） | $P_q(N_{cached})$，复用率 $=\dfrac{N_{cached}}{ISL}$ | 输入里有多少 token 命中了前缀缓存、可以跳过 prefill。越高越好，TTFT 会明显下降。 |

# Row 3 · KV Routing（路由内部，5 项 —— 均无 model 过滤，仅 KV-aware router 模式有数据）

| 参数名                              | 单位               | 计算公式                                                                                        | 详细解释                                                  |
| -------------------------------- | ---------------- | ------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| Per-Worker Active Decode Blocks  | short（block 数）   | $B_w(t)$，按 worker 分线                                                                        | 每个 worker 当前占用了多少 decode KV 显存块。用来看负载是否均摊、缓存是否将满。     |
| Per-Worker Active Prefill Tokens | short（token 数）   | $T_w(t)$，按 worker 分线                                                                        | 每个 worker 手上正在算的 prefill token 量，看 prefill 侧忙不忙、是否偏斜。 |
| KV Hit Rate Distribution         | percentunit（0~1） | $H=\dfrac{B_{overlap}}{B_{input}}$，取 $P_q(H)$                                               | 路由在挑 worker 时预估的前缀命中比例。命中越多，prefill 越省，TTFT 越低。       |
| Routing Overhead Breakdown       | ms               | $\overline{t_{stage}}=\dfrac{\sum t_{stage}}{N_{stage}}$，$t_{total}=\sum_{stage} t_{stage}$ | 路由自己花掉的时间（算哈希、查前缀索引、选实例）。它是纯开销，应远小于 TTFT。             |
| KV Events Applied Breakdown      | ops（堆叠）          | $r_{e,s}=\dfrac{\Delta N_{e,s}}{\Delta t}$                                                  | 路由更新前缀索引的事件速率。出现失败类事件说明索引与 worker 真实缓存已经不一致。          |

# Row 4 · Workers（单实例下钻，3 项）

| 参数名                                 | 单位                      | 计算公式                                                                       | 详细解释                                           |
| ----------------------------------- | ----------------------- | -------------------------------------------------------------------------- | ---------------------------------------------- |
| Worker Request Breakdown Per Worker | reqps                   | $r_{inst}=\dfrac{\Delta N_{inst}}{\Delta t}$，错误按 $(inst,\ error\_type)$ 分组 | 每个实例各自承担多少请求、出多少错。用来判断调度是否均衡、哪个 pod 有问题。       |
| Worker Request Duration Per Worker  | s                       | $P_q(D_{inst})$，$D$ = worker 内部处理耗时                                        | 只算 worker 里的推理时间，不含排队与路由。它与 E2E 的差值就是花在调度上的时间。 |
| Component Throughput (bytes/sec)    | 无（实为 bytes/s，面板未设 unit） | $\dfrac{\Delta Bytes}{\Delta t}$，按 instance 分线                             | 端点上进出的字节速率，用来交叉验证请求量与报文大小是否正常（如是否来了超大 prompt）。 |

## 跨 row 的健康关系式（比单看某个数更有用）

| 关系式 | 健康表现 | 违背时的含义 |
|---|---|---|
| $E2E \approx TTFT + ITL \times OSL$ | 两边接近 | 左边明显偏大 → 存在额外排队/路由开销 |
| $E2E_{frontend} - D_{worker}$ | 差值小且稳定 | 差值大 → 瓶颈在排队/调度，不在推理 |
| $\dfrac{N_{cached}}{ISL}$ vs $H$（KV Hit Rate） | 两者数值接近 | 偏差大 → 路由预测不准，查 KV Events 异常 |
| $\dfrac{t_{total}}{TTFT}$ | $< 5\%\sim10\%$ | 超过 → 路由本身成瓶颈 |
| Per-Worker 曲线离散度 | 小 | 大 → 路由不均衡，存在热点 |
| $N_{queued}$ 与 $P_{99}(TTFT)$ | 同步且都低 | queued 涨而 TTFT 未涨 → 指标口径有问题（注意 queued 缺 model 过滤） |

## 2. Dynamo Disaggregated Analysis —— 唯一带 GPU/硬件视角的 P/D 分离盘

- **唯一区分 prefill 与 decode 角色**：用 `dynamo_component="prefill"` 与 `dynamo_component="backend"` 分别出图，并有专门的 **Component Latency - Prefill vs Decode** 对比面板 → 看 P/D 配比是否失衡、哪一侧是瓶颈。
- **唯一有 GPU 与节点层指标**：`DCGM_FI_DEV_GPU_UTIL`、`DCGM_FI_DEV_MEM_COPY_UTIL`、`DCGM_FI_DEV_FB_USED`、`container_cpu_usage_seconds_total`、`node_cpu_seconds_total`，以及 **NVLink 带宽**（`(rate(DCGM_FI_PROF_NVLINK_TX_BYTES[1m]) + rate(DCGM_FI_PROF_NVLINK_RX_BYTES[1m]))/1e9`，GB/s）→ tag 里也写明 `nixl, gpu`。
- **代价是依赖最重**：几乎每条查询都乘 `* on(pod, namespace) group_left() kube_pod_status_phase{phase="Running"}`（过滤掉非 Running pod），因此**必须有 kube-state-metrics + node-exporter + DCGM exporter**（且 NVLink 那两个 `DCGM_FI_PROF_*` 需按 `dcgm-metrics-with-nvlink.csv` 定制 DCGM 配置），缺一就有面板空白。
- **最实时**：`refresh: 10s` + 默认 `now-30m`，是 4 个里唯一适合压测/上线时盯屏的盘。
- **风格上最"糙"**：21 个 timeseries 全平铺、**没有 row 分组**；速率窗口硬编码 `[5m]`/`[30s]`/`[1m]` 而非 `$__rate_interval`（缩小时间窗时曲线会偏平滑）；单位多为 ms（查询里手工 `1000 *`）；分位数只有 p99（prefill）无完整分位族。
- **一个坑**：`namespace` 变量的 `current` 被硬编码为 `robert`（作者的开发 namespace），**导入后第一件事是切换 namespace**；而且它单选、无 All 选项。
- 它是 `setup-monitoring.sh` 唯一自动 apply 的那一个。

## 3. Dynamo Planner Dashboard —— 唯一"决策/预测"视角，含 SLA 基线

- **唯一同时画"观测值 vs 预测值"**：`dynamo_planner_observed_*` 与 `dynamo_planner_predicted_*` 成对出现（RPS、ISL/OSL、prefill/decode 副本数）→ 用来验证 planner 的预测准不准、扩缩是否跟得上负载。
- **唯一带 SLA 目标线**：`dynamo_planner_sla_target_ttft_ms` / `sla_target_itl_ms` 与 observed TTFT/ITL 画在同一面板 → 一眼看出是否违约。
- **唯一有成本口径指标**：`dynamo_planner_gpu_hours`（累计 GPU 小时 stat）。
- **查询最简单**：13 个面板全是裸 gauge 直取，无 `rate`、无 `histogram_quantile`、无聚合函数，因此**最省 Prometheus 资源、也最容易读**。
- `namespace` 变量是**多选 + All 且默认 All**（`refresh: 2` 即时间范围变化时重取），跨 namespace 横向对比很方便。
- 唯一 `graphTooltip: 1`（shared crosshair，多面板联动对齐时间点）；row 标题带 emoji（🖥️ / 📊 / 🔮）。
- **前提**：必须实际启用了 Planner（SLA-based planner）组件，否则整盘无数据；`refresh: ""` 不自动刷新。

## 4. Dynamo Operator —— 唯一控制面（control-plane）盘，与推理性能无关

- **观测对象完全不同**：不看请求/token/GPU，只看 K8s operator 自身健康 —— reconcile 速率与 P95 耗时、reconcile 错误（按 `error_type`）、admission webhook 速率/P95/拒绝原因（按 `reason`）、资源清单（按 `resource_type` × `status`）。指标全为 `dynamo_operator_*`。
- **参数最多（3 个）**：多了 `resource_type`（如 DynamoGraphDeployment 等 CRD 类型），且 `namespace` 与 `resource_type` 都有 `allValue: ".*"`，配合 `=~"$..."` 正则匹配 → **过滤组合最灵活**。
- **唯一使用 gauge 面板类型**：Operational Health 区两个百分比仪表 —— reconcile 成功率、webhook 准入成功率（`100 * success / total` 形式），直接当 SLO 看板用。
- `refresh: 30s`、默认 `now-1h`，定位是**平台运维值守**；分位数统一取 P95（不做 p50/p99 全家桶）。
- 面板最少（14 个）但 row 组织规整：Reconciliation / Webhook / Resource Inventory / Operational Health。
- 有独立配套文档 [operator-metrics.md](https://github.com/ai-dynamo/dynamo/blob/v1.3.1/docs/kubernetes/observability/operator-metrics.md)。

## 横向对比

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
- 四者互补、无重叠冲突（uid 各不相同），可以同时 apply 到 `monitoring` namespace 共存。
- min-max多个模型
