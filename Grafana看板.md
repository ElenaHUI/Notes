
基于已解析的 4 个 JSON（v1.3.1），逐个说特点，最后给对比与选用建议。

## 1. Dynamo Dashboard —— 唯一"按模型"看的主力盘

-![[Pasted image 20260806171222.png]]

# Row 1 · Overview（区间汇总，7 项）

| 参数名                  | 单位            | 含义                 | 计算方式                                                                                                                                                       | 什么情况下比较好                                                                                                      |
| -------------------- | ------------- | ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Request Success Rate | percent (%)   | 非 internal 错误的请求占比 | `(sum(increase(f_requests_total[R])) - sum(increase(f_requests_total{error_type="internal"}[R])) or vector(0)) / sum(increase(f_requests_total[R])) * 100` | **≥ 99 为绿、<99 为红**；理想 100。注意它不扣 cancelled/validation/overload，所以"99% 以上"只代表**没有内部错误**，需配合 Row 2 的 Outcome 图确认 |
| Total Requests       | short（个）      | 窗口内前端收到的总请求数       | `sum(increase(f_requests_total[R]))`                                                                                                                       | 无好坏，是**基数**。它必须足够大（≥ 几百）其他分位数才有统计意义；为 0 说明没流量或采集断了                                                            |
| Input Tokens         | short（个）      | 窗口内输入 token 总量     | `sum(increase(f_input_sequence_tokens_sum[R]))`                                                                                                            | 无好坏，成本/负载口径。与 Output 一起看比例：**输入远大于输出**说明适合开前缀缓存/P-D 分离                                                        |
| Output Tokens        | short（个）      | 窗口内输出 token 总量     | `sum(increase(f_output_sequence_tokens_sum[R]))`                                                                                                           | 无好坏。`Output Tokens ÷ 窗口秒数` = 系统总输出吞吐，**越高越好**（同等延迟下）                                                          |
| Average TTFT         | ms            | 窗口内平均首 token 延迟    | `sum(increase(f_time_to_first_token_seconds_sum[R])) / sum(increase(..._count[R])) * 1000`                                                                 | 越低越好。交互式对话经验值 **< 500 ms 良好、< 1000 ms 可接受**；且应与 Row 2 的 P50 接近（差距大说明有长尾拉偏均值）                                  |
| Average ITL          | ms            | 窗口内平均 token 间延迟    | `sum(increase(f_inter_token_latency_seconds_sum[R])) / sum(increase(..._count[R])) * 1000`                                                                 | 越低越好。**< 50 ms**（≈20 tok/s）已快于人类阅读速度，**< 100 ms** 可接受；`1000/ITL` 即每秒出字数                                       |
| Average E2E Latency  | s（注意与上两项单位不同） | 窗口内平均端到端耗时         | `sum(increase(f_request_duration_seconds_sum[R])) / sum(increase(..._count[R]))`                                                                           | 越低越好，但要**除以输出长度归一化**才可比。健康关系式：`E2E ≈ TTFT + ITL × Output_len`，若 E2E 明显大于该估算值 → 存在排队/路由额外开销                    |

> ⚠️ 后 6 项面板内置阈值均为模板残留的 `red @ 80`（超过 80 就标红），对 token/请求数无意义，**只看数字别看颜色**。

# Row 2 · Frontend（对外服务质量，9 项）

| 参数名                       | 单位             | 含义                                                                                             | 计算方式                                                                                                                                       | 什么情况下比较好                                                                                                                                |
| ------------------------- | -------------- | ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------- |
| Frontend RPS              | req/s          | 前端请求吞吐                                                                                         | `sum by(model)(rate(f_requests_total[w]))`                                                                                                 | 无绝对好坏，是**参照基线**。健康表现：RPS 上升时延迟平缓上升；**RPS 下降而延迟上升 = 系统已劣化**                                                                              |
| E2E Request Latency       | s              | 端到端耗时的 P50/P90/Average/P99/MAX 五条线                                                             | `histogram_quantile(q, sum by(le)(rate(f_request_duration_seconds_bucket[w])))`；Average 用 `sum(rate(_sum))/clamp_min(sum(rate(_count)),1)` | **P99/P50 比值 < 3** 说明尾部可控；P50 稳定、曲线平滑无锯齿。P99 突刺 = 长尾/排队/坏 worker。MAX 是最高有值桶上界，阶梯状偏大，只作量级参考                                              |
| Request Outcome Breakdown | reqps（堆叠）      | 按结果拆分请求速率：success + cancelled / validation / not_found / not_implemented / overload / internal | `sum(rate(f_requests_total{status="success"}[w]))` 及各 `{status="error", error_type="X"}`                                                   | **理想：只有 success 一条带，其余贴地为 0**。`internal` 必须为 0（有就是 bug）；`overload` > 0 即容量不足；`validation`/`not_found` > 0 是调用方问题；`cancelled` 少量正常（用户中断） |
| Active vs Queued Requests | short（并发数，瞬时值） | active=在途请求总数；queued=首 token 前卡在 preprocess/route/dispatch 的请求数                                | `sum(f_active_requests)`；`sum(f_stage_requests{stage=~"preprocess\|route\|dispatch"})` ⚠️**无 model 过滤**                                    | **queued 长期贴近 0** 且只在流量尖峰时短暂抬起 = 健康；queued 持续 >0 且单调上升 = 积压（TTFT 必然恶化，需扩容/调路由）。active 稳定在容量区间内、不撞天花板                                    |
| TTFT (p50/p90/p99)        | ms             | 首 token 延迟分位                                                                                   | `histogram_quantile(q, sum(rate(f_time_to_first_token_seconds_bucket[w])) by(le)) * 1000`                                                  | 越低越平稳越好；经验 **P50 < 500 ms、P99 < 2 s**。P99 抖动通常是 prefill 排队 → 查 Queued 与 KV Hit Rate                                                     |
| ITL (p50/p90/p99)         | ms             | token 间延迟分位                                                                                    | `histogram_quantile(q, sum(rate(f_inter_token_latency_seconds_bucket[w])) by(le)) * 1000`                                                  | 越低且**曲线平直**越好，经验 **P50 < 50 ms、P99 < 200 ms**。ITL 随并发上升缓慢抬高属正常；阶梯式跳升 = decode batch 被 KV cache 压缩                                       |
| ISL Distribution          | short（token 数） | 输入长度（prompt 大小）分位                                                                              | `histogram_quantile(q, sum(rate(f_input_sequence_tokens_bucket[w])) by(le))`                                                               | 本身无好坏，**关键是稳定**。突增会带动 TTFT 上升（属输入变化而非故障）；P99 远大于 P50 说明请求异构，此时用平均值判断性能会失真                                                               |
| Output Size Distribution  | short（token 数） | 输出长度分位                                                                                         | `histogram_quantile(q, sum(rate(f_output_sequence_tokens_bucket[w])) by(le))`                                                              | 同样看稳定性。它是 decode 侧总工作量的驱动因子，判断 E2E 是否合理必须先看它                                                                                            |
| Cached Tokens             | short（token 数） | 每请求命中前缀缓存的 token 数（后端 usage 口径）                                                                | `histogram_quantile(q, sum(rate(f_cached_tokens_bucket[w])) by(le))`                                                                       | **越高越好**，且应与 ISL 一起看：`Cached ÷ ISL` 即真实前缀复用率，**> 50% 属很好**，此时 TTFT 会明显下降。为 0 说明缓存完全没起作用                                                 |

# Row 3 · KV Routing（路由内部，5 项 —— 均无 model 过滤，仅 KV-aware router 模式有数据）

| 参数名 | 单位 | 含义 | 计算方式 | 什么情况下比较好 |
|---|---|---|---|---|
| Per-Worker Active Decode Blocks | short（block 数） | 各 worker 当前占用的 decode KV block（前端路由器账本视角） | `dynamo_frontend_worker_active_decode_blocks`（裸 gauge，按 `worker_id/dp_rank/worker_type/instance` 分线） | **各 worker 曲线彼此贴合 = 负载均衡良好**；离散度越小越好。某条持续偏高 = 热点 worker；所有曲线都逼近上限 = KV cache 将满，ITL 会随之恶化 |
| Per-Worker Active Prefill Tokens | short（token 数） | 各 worker 当前在处理的 prefill token 数 | `dynamo_frontend_worker_active_prefill_tokens`（裸 gauge） | 同上，**齐平为好**。尖峰后应快速回落；持续高位 = prefill 侧饱和，TTFT 会涨 |
| KV Hit Rate Distribution | percentunit（0~1） | 路由**决策时预测**的 KV 命中率 = `overlap_blocks / input_sequence_blocks` | `histogram_quantile(q, sum(rate(c_router_kv_hit_rate_bucket[w])) by(le))`；Average 用 sum/count | **≥ 0.7 绿、0.3~0.7 黄、< 0.3 红**（面板真实阈值）。越高越好，>0.7 时 TTFT 明显受益；<0.3 说明前缀复用差或 cache 太小被频繁淘汰。可与 Row 2 的 Cached Tokens 对照验证预测准确性 |
| Routing Overhead Breakdown | ms | 路由开销按阶段拆分：block_hashing / indexer_find_matches / seq_hashing / scheduling / **total**，每阶段 avg+p50+p90 共 15 条 | avg：`sum(rate(r_overhead_X_ms_sum[w]))/clamp_min(sum(rate(..._count[w])),1)`；分位：`histogram_quantile(q, sum(rate(..._bucket[w])) by(le))` | **total 保持个位数 ms、且占 TTFT < 5~10%** 为好；各子阶段平稳无增长趋势。`indexer_find_matches` 随时间单调上升 = 前缀索引膨胀，是最常见的劣化点。建议只勾 `total avg/p90` 观察 |
| KV Events Applied Breakdown | ops（堆叠） | KV 索引更新事件速率，按 `event_type` × `status` 拆分 | `sum(rate(c_kv_cache_events_applied{event_type="…", status="…"}[w]))`，6 个组合 | **只有 `stored\|ok`、`removed\|ok`、`cleared\|ok` 三条有值，异常三条恒为 0** 为健康。出现 `parent_block_not_found` / `invalid_block` / `block_not_found` = 索引与 worker 真实 cache 脱节，会直接拉低上面的 KV Hit Rate |

# Row 4 · Workers（单实例下钻，3 项）

| 参数名 | 单位 | 含义 | 计算方式 | 什么情况下比较好 |
|---|---|---|---|---|
| Worker Request Breakdown Per Worker | reqps | 每个 worker 的总请求率 / 取消率 / 各类错误率 | `sum by(instance)(rate(c_requests_total[w]))`；`sum by(instance)(rate(c_cancellation_total[w]))`；`sum by(instance, error_type)(rate(c_errors_total[w]))` | **各 instance 的 total 曲线量级接近（均衡），error 与 cancelled 贴地为 0**。某 instance total 显著低 = 该 worker 未被有效调度或已异常。⚠️ `errors_total` 是诊断计数器、非互斥失败数（可能把取消算进去），**不要用它算成功率** |
| Worker Request Duration Per Worker | s | 每个 worker 内部 handler 的处理耗时分位（**仅推理，不含排队/路由**） | `histogram_quantile(q, sum by(instance,le)(rate(c_request_duration_seconds_bucket[w])))`；Average 用 sum/count by instance | **各 instance 曲线重叠、离散度小**为好；单个 instance 的 P99 突出 = 坏 worker（GPU 降频/KV 满/邻居干扰），可直接拿 instance 定位 pod。**核心判据：`E2E(Row2) − 本值` 应尽量小**，差值大说明时间花在排队与路由而非推理 |
| Component Throughput (bytes/sec) | 无（实为 bytes/s，面板未设 unit） | `generate` 端点的请求/响应字节速率，按 instance 分线（未做 sum） | `rate(c_request_bytes_total{dynamo_endpoint="generate"}[w])`、`rate(c_response_bytes_total{…}[w])` | 与 RPS、ISL/OSL **成比例变化**即健康。请求字节突增而 RPS 不变 = 有超大 prompt 进来；响应字节与输出 token 数比例突变 = 序列化/协议层异常 |

## 跨 row 的健康关系式（比单看某个数更有用）

| 关系式 | 健康表现 | 违背时的含义 |
|---|---|---|
| `E2E ≈ TTFT + ITL × Output_len` | 两边接近 | 左边明显偏大 → 存在额外排队/路由开销 |
| `E2E(前端) − Duration(worker)` | 差值小且稳定 | 差值大 → 瓶颈在排队/调度，不在推理 |
| `Cached Tokens ÷ ISL` vs `KV Hit Rate` | 两者数值接近 | 偏差大 → 路由预测不准，查 KV Events 异常 |
| `Routing total overhead ÷ TTFT` | < 5~10% | 超过 → 路由本身成瓶颈 |
| Per-Worker 曲线离散度 | 小 | 大 → 路由不均衡，存在热点 |
| `queued` 与 `TTFT P99` | 同步且都低 | queued 涨而 TTFT 未涨 → 指标口径有问题（注意 queued 缺 model 过滤） |

需要我把这四张表连同健康判据写成一份 Markdown 文档放到桌面吗？或者继续讲第二个盘（Disagg，带 GPU/NVLink 的那个）。
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