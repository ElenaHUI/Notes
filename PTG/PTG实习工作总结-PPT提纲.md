# PTG 实习工作总结 · PPT 提纲

> 用法：直接在本文档里改文字 / 增删条目 / 调整页序，改完告我一声我按这份提纲重新生成 PPT。
> 结构标记说明：`kicker` = 页面左上角英文小标；`卡片【】` = 一个灰底卡片；`▸` = 卡片内要点；`图` = 嵌入的截图。

---

## 请先确认这几处

1. **本次已按你的口径重排**：全篇只保留你确认的 7 项工作。删掉了原 P13「性能分析报告 Skill」、原 P9 里团队级的「Dynamo 智能调度架构迁移」定位，以及 Kimi-K2.6 / Qwen3.5-397B / Qwen3-235B / MiniMax-M2.7 等非本人负责的模型；新增 P18「红区自动值守 Agent 开发」。如果哪项其实也有你的参与，告我加回来。
2. **数字口径**（第 7 页四个大数字）：`2 套部署形态` `4 个看板` `3 套环境` `15+ 份部署清单` —— 都是从你笔记里数出来的，请核一遍；特别是「4 个看板」如果只有 Dynamo Dashboard 是你适配的，我改成更保守的写法。
3. **时间口径**：目录第 02 项我写的是「工作总结」（模版原文是「半年总结」，但你 2026.06 入职至今约 3 个月，说"半年"不准）。如果这次汇报场合就叫"半年总结"，告我改回去。
4. **敏感信息**：内文出现了内部域名、环境名（pdev / pprod / prod / B 红区）、机器路径、模型名。如果这份 PPT 要给外部或跨部门看，请标出哪些需要脱敏。
5. **篇幅**：现在 21 页。如果汇报只有 10 分钟，建议先合并 P9 + P10（DGD 部署与参数调优并回一页），再把 P16（四个阻塞问题）并进 P15 的一张卡。
6. **未来规划**（第 20 页）：已收窄到你自己这几条线，但仍是我推测最多的一页，请重点改。

---

## P1 · 封面

- 主标题：**红区大模型推理平台建设与优化**
- 副标题：模型部署 · PD 分离调优 · 监控链路 · Agent 工具链
- 姓名：闫一慧
- 职位：LLM 推理平台实习生 · 阿里巴巴平头哥半导体
- 日期：2026 / 09

## P2 · 目录

1. 个人介绍
2. 工作总结
3. 未来规划

---

## P3 · 章节页 01

- 序号：01　标题：个人介绍　英文：PROFILE
- 右侧要点：
  - 个人介绍
  - 岗位职责
  - 技术栈与工具链

## P4 · 个人介绍

kicker: PROFILE　标题：个人介绍

卡片【教育背景】
- ▸ **华东师范大学**　软件工程 硕士 · 2024.09 — 2027.06
- ▸ **西安电子科技大学**　软件工程 学士 · 2020.06 — 2024.09

卡片【岗位职责】
- ▸ 负责 DeepSeek-V4-Flash 在自研 PPU 芯片上的 PD 分离部署、DGD 部署形态与参数调优
- ▸ 负责 Dynamo frontend 监控链路搭建与看板适配、Warmup 方案的设计与统一落地
- ▸ 负责红区 Agent 工具链：Opencode 上报插件与链路、DSH 离线包、自动值守 Agent

卡片【技术栈】
- ▸ **推理引擎**　SGLang · vLLM 
- ▸ **分布式传输**　Mooncake · RDMA 
- ▸ **云原生**　Kubernetes · ArgoCD 
- ▸ **可观测性**　Prometheus · Grafana

---

## P5 · 章节页 02

- 序号：02　标题：工作总结　英文：WORK SUMMARY
- 右侧要点：
  - 工作全景
  - DeepSeek-V4-Flash模型部署
  - SGLang适配DeepSeek-V4-Flash-0731的DGD部署与参数调优
  - Dynamo frontend监控链路搭建与适配
  - Warmup 方案设计与实现
  - Opencode 上报插件开发、链路搭建与问题排查
  - DSH 红区支持适配与打包
  - 红区自动值守Agent开发

## P6 · 工作全景

kicker: BIG PICTURE　标题：工作全景：红区 AI Infra 分层视图

图（左侧占 2/3）：`asset/红区AI Infra.png` 分层脑图

卡片【我的负责范围】
- ▸ **编排层**　DeepSeek-V4-Flash 的Dynamo DGD 部署
- ▸ **运行时**　SGLang 启动参数调优、Warmup 机制统一
- ▸ **度量层**　Dynamo frontend 指标采集链路与 Grafana 看板适配
- ▸ **交付层**　Gitea + ArgoCD GitOps 声明式发布流程
- ▸ **Agent 侧**　Opencode 上报插件全链路、DSH 红区离线包、红区自动值守 Agent
- ▸ *(小字)* 图示为团队整体 AI Infra 分层，上述为本人负责的部分

## P7 · 成果速览

kicker: HIGHLIGHTS　标题：成果速览

四个数字卡（第一行）：

| 数字 | 单位 | 标签 | 小字说明 |
|---|---|---|---|
| 2 | 套形态 | DeepSeek-V4-Flash 部署 | 自研 Deployment 版 PD 分离 + Dynamo DGD |
| 4 | 个看板 | Dynamo 监控看板适配 | 共 76 个面板，frontend 采集链路根治重复抓取 |
| 3 | 套环境 | Opencode 上报链路上线 | dev / prod / B 红区全部验证 |
| 15+ | 份清单 | Warmup 脚本统一覆盖 | 4 份重复 ConfigMap 收敛为 1 份共享脚本 |

卡片【模型部署与调优】
- ▸ DeepSeek-V4-Flash 上线接入打通：t-one 建应用 → GitOps 配置 → Apollo 白名单 → 转发验证
- ▸ SGLang PD 分离 + Mooncake 跨节点 KV 传输跑通，去掉三处 disable 开关后 TTFT / TPOT 同步改善
- ▸ Dynamo v1.3.0 DGD 部署形态适配完成，一份声明展开出 Frontend / P / D 完整推理图
- ▸ 定位 CP 与 DP attention 互斥、fa3 算子不支持 Hopper 之外等引擎级约束

卡片【链路优化】
- ▸ Dynamo frontend 指标采集链路搭建，四个看板按红区实际部署形态适配
- ▸ Warmup 真实请求录制回放方案，解决冷启动首请求 3 分 56 秒的问题

卡片【Agent 工具链】
- ▸ 自研 Opencode /report 插件（TUI + Server 双进程），打通服务端 + 钉钉 + web-mgmt 全链路
- ▸ DSH Web UI 红区离线包，一条命令在无外网机器即开即用
- ▸ 红区支持群自动值守 Agent：单轮巡检耗时由约 10 分钟降至 2–3 分钟

---

## P8 · DeepSeek-V4-Flash 模型部署与上线接入

kicker: MODEL ONBOARDING　标题：DeepSeek-V4-Flash 模型部署与上线接入

顶部流程图（4 步，橙色描边框 + 箭头）
 `GitOps 配置`（镜像 / 卡数 / datasets）→ `Argo CD同步`（查看全景图）→ `连通性测试与验证`

卡片（左，大）
- **GitOps 配置（gitea-app-manifests）**
  - ▸ 更新推理镜像；卡数与资源限额对齐
  - ▸ datasets 的 hostPath 从 `/ppusw/datasets_new` 改回 `/ppusw/datasets`
  - ▸ litellm-proxy 两处 overlay 同步：pdev 的 litellm-config-file、pprod 的 ingress-tone
- **可见与联调**
  - ▸ Apollo 白名单补登后模型才会出现在 tone 大模型列表，否则服务跑着但用户看不到
  - ▸ ArgoCD sync 后验证域名转发与实际推理调用，打通才算上线

卡片【易踩的坑】（右上）
- ▸ 模型名写错（包括 `.` 未换 dot、拼写偏差）会同时影响路由与监控标签，后期纠正成本高
- ▸ datasets 路径、卡数这类字段部分会被自动同步，但**不能假设一定到位**，提交前逐项核
- ▸ 白名单 / ingress / 模型库记录分属不同系统，任一环缺失都表现为「服务正常但用不了」

卡片【沉淀】（右下）
- ▸ 把上线流程整理为可直接照做的步骤文档，后续新模型接入直接复用
- ▸ *(小字)* 流程口径来自 `Dynamo/Dynamo监控链路搭建/模型部署.md`，如果里面的截图对应的是其他模型，告我换成 DeepSeek-V4-Flash 的记录

## P9 · SGLang 适配 DeepSeek-V4-Flash-0731：DGD 部署与传输链路

kicker: PD DISAGGREGATION　标题：SGLang 适配 DeepSeek-V4-Flash-0731：DGD 部署与传输链路

卡片【部署形态：DynamoGraphDeployment】（左上）
- ▸ **CRD**　nvidia.com/v1alpha1 · backendFramework: sglang
- ▸ **拓扑**　Prefill / Decode 两个 Worker，各 1 副本 8 卡 PPU
- ▸ **端口**　P 8100 · D 8101，disaggregation-mode 区分角色
- ▸ **服务发现**　etcd；事件面 nats
- ▸ **资源**　rdma/hca: 4，节点亲和 PPU + board.type=810e
- ▸ **传输**　Mooncake，GPU 拓扑由注解注入
- ▸ *(小字)* 以 GitOps 声明式发布，ArgoCD 按环境分批 sync

卡片【传输链路打通】（左下）
- ▸ SGLang PD 分离 + Mooncake 跨节点 KV Cache 传输，绑定 mlx5_bond_* 多网卡
- ▸ 机内场景启用 ICN：MC_FORCE_MNNVL / MC_USE_NVLINK_IPC，以 TRACE 日志验证链路真实生效
- ▸ K8s 侧 hostNetwork / hostPID / hostIPC + ClusterFirstWithHostNet 是 RDMA 初始化的前提
- ▸ router 以 mini-lb 串联 P / D，按 round-robin 做 prefill 均衡

图（右上）：ArgoCD DGD 资源树截图 —— 说明文字「DGD 资源树：一次声明展开为完整的 P / D 推理图」

卡片【与自研 Deployment 版的差异】（右下）
- ▸ 自研版：P / D 各一份 Deployment，靠 mini-lb 手工串联，副本与端口硬编码
- ▸ DGD：一份声明由 Operator 展开出 Frontend / P / D 与配套 Service，发布口径统一
- ▸ 同时 Operator 会自动为 frontend 生成 ServiceMonitor，直接影响后面的监控采集口径（见 P12）
- ▸ 控制面具备 Planner，为后续按指标做扩缩容决策留出位置

## P10 · 参数调优与引擎级约束

kicker: TUNING　标题：参数调优与引擎级约束

卡片（左，大）
- **开关收敛**
  - ▸ 去掉 disable-custom-all-reduce / disable-radix-cache / disable-shared-experts-fusion 三个开关，TTFT 与 TPOT 同步改善
  - ▸ 逐项回退验证，确认改善来自具体开关而不是环境波动
- **P / D 差异化配置**
  - ▸ P 端保留 NSA Context Parallel（attn-cp-size 8），承担长输入 prefill
  - ▸ D 端使用 DP attention + DP LM head，提升 decode 并发
  - ▸ 注意力算子拆分：flashmla 负责 decode、fa3 负责 prefill
- **沉淀**
  - ▸ 形成可复用的 P / D 最小可运行配置模版与排障清单

卡片【典型问题 → 解法】（右）
- ▸ fa3 报 q_v only supported for Hopper → 拆成 flashmla decode + fa3 prefill
- ▸ round-robin-split CP 下开 dp-size 报错（CP 与 DP attention 互斥）→ P 端 dp-size 固定为 1
- ▸ 未开 host 网络时 Mooncake 退化、TTFT 极高 → 补齐 extraPodSpec 三件套与 DNS 策略
- ▸ *(小字)* engine：SGLang 0.5.16 / Dynamo 1.3.1；经验阈值：NVLink 带宽 < 1 GB/s 即判定传输退化为 host 内存拷贝

## P11 · Dynamo frontend 监控链路搭建与适配

kicker: OBSERVABILITY　标题：Dynamo frontend 监控链路搭建与适配

四个看板卡（第一行）
- **Dynamo Dashboard**　28 面板 · 按 model 切分，看延迟 / 吞吐 / 缓存，零外部依赖
- **Disaggregated Analysis**　21 面板 · 按 namespace 看 P/D 与 GPU、NVLink 利用率
- **Planner Dashboard**　13 面板 · 控制面弹性决策，扩缩容预测与 SLA 达成
- **Dynamo Operator**　14 面板 · CRD 调谐、准入校验与资源清单健康度

图（左下）：Grafana Frontend 行截图 —— 说明文字「Frontend 行：RPS / E2E / TTFT / ITL / ISL / OSL / Cached Tokens」

卡片【链路搭建与适配】（右下）
- ▸ 以 Dynamo v1.3.0 官方看板为底本，按红区实际部署形态适配指标名、变量与图例
- ▸ 打通 frontend 指标采集：ServiceMonitor → Prometheus → Grafana，接入 5 类指标族（frontend / component / router / planner / operator）
- ▸ 硬件视角面板依赖 DCGM、node-exporter、kube-state-metrics，缺依赖则该行无数据
- ▸ 判读方法沉淀：逐面板写清计算公式与判读结论，交叉校验 E2E ≈ TTFT + ITL × OSL，不成立即怀疑采集口径

## P12 · 监控问题定位与根因修复

kicker: TROUBLESHOOTING　标题：监控问题定位与根因修复（2×2 四张卡）

卡片【看板图例重复 · 采集层去重】
- ▸ **现象**　Per-Worker Active Decode Blocks 图例 6 条但只有 2 个 worker ID，同名曲线相位错开，sum() 结果放大 2~3 倍
- ▸ **定位**　面板 JSON → Prometheus 原始序列标签（仅 endpoint / job / service 不同）→ count_over_time 验证抓取间隔为 5s / 5s / 15s
- ▸ **根因**　三个 ServiceMonitor 的 selector 过宽，同时命中同一个 frontend Pod，同份指标被重复采集三遍
- ▸ **处置**　只保留 Operator 原生 endpoint=http 的 ServiceMonitor，删除模型模版与平台侧两份
- ▸ *(小字)* 结论：采集层重复不应用面板层 max by 掩盖，否则冗余存储与相位错位仍在

卡片【Component Throughput 图例错乱 · 同现象不同根因】
- ▸ **现象**　图例 4 条但只有 Request / Response bytes 两个名字，无法区分 worker
- ▸ **根因**　此处不是重复抓取（只有一个采集源），而是 2 个真实 worker 副本 + legendFormat 写死
- ▸ **处置**　图例改为 `{{worker_id}}` 模板化；rate 窗口应 ≥ 4 倍抓取间隔，避免欠采样造成断点毛刺

卡片【Namespace 变量污染】
- ▸ **现象**　下拉出现 canary、v142-default 等历史 namespace，误选即无数据
- ▸ **处置**　变量改用 label_values(dynamo_frontend_requests_total, dynamo_namespace) 动态收敛

卡片【方法论沉淀】
- ▸ 「图例重名」是现象不是根因：先看面板 JSON，再回 Prometheus 比对原始序列标签，最后用抓取频率定性
- ▸ 同一现象可能对应采集层（重复抓取）或展示层（legend 写死）两类根因，修法完全不同
- ▸ 修在最上游：采集重复就收敛 selector，展示问题才改面板

## P13 · Warmup 方案设计与实现：真实请求录制回放

kicker: COLD START　标题：Warmup 方案设计与实现：真实请求录制回放

卡片（左，大）
- **问题**
  - ▸ 原 warmup 只发一条 1 万字静态纯文本，与真实的多轮对话 + system prompt + tool_calls + 长上下文差距大
  - ▸ 四份 ConfigMap 逻辑 95% 重复，被 15+ 个 deploy.yaml 引用，改一处要改一片
- **方案**
  - ▸ litellm-proxy 网关处拦截真实请求，导出 JSONL 到共享存储
  - ▸ 统一 llm-warmup-scripts 共享 ConfigMap，支持 JSONL / Legacy 纯文本 / Skip 三种模式，env 全部带默认值，100% 向后兼容

卡片【痛点实证】（右上）
- 图：未预热首请求截图 —— 说明文字「未预热实例的首次请求：一句「你好」端到端 3 分 56 秒」

卡片【预期收益】（右下）
- ▸ 首请求 TTFT 显著下降，算子 / kernel 缓存在 Ready 前完成填充
- ▸ readinessProbe 与真实可服务状态对齐，避免流量打到未热实例
- ▸ 脚本单点维护，新模型接入只需一个环境变量


## P14 · Opencode 上报插件开发（端侧）

kicker: OPENCODE PLUGIN　标题：Opencode 上报插件开发：端侧采集与分发

卡片（左，大）
- **插件形态：TUI + Server 双进程**
  - ▸ TUI 进程注册 `/report` 斜杠命令，交互式收集问题描述、会话日志与运行配置
  - ▸ Server 进程后台采集运行上下文，两进程共用同一套上报与脱敏逻辑
  - ▸ file:// 协议插件必须 `export default { id, tui }` / `{ id, server }`，缺 id 即加载失败
- **采集与脱敏**
  - ▸ 日志限 maxLogLines 2000、请求超时 30s，避免大日志拖垮端侧
  - ▸ 审查脱敏规则有无遗漏的敏感信息类型，按需补齐 GPU 型号、模型服务端点等定位端侧问题所需字段

图（右上）：`asset/Pasted image 20260803160451.png` —— 说明文字「安装后 `/report` 出现在斜杠命令列表：收集诊断信息并上报问题」

卡片【一条 curl 安装 · 版本兼容与防降级】（右下）
- ▸ `curl -fsSL .../install.sh | bash -s -- --plugin report-issue --endpoint ...`，红区机器同样适用
- ▸ install.sh 分写两份配置：server 条目进 opencode.jsonc、TUI 条目进 tui.json；uninstall.sh --all --force 同步清理，支持完整回退
- ▸ v1.1.53 的 plugin schema 为 z.string().array()，不认 `["file://...", {options}]` 元组 → 安装时校验版本，低于 v1.16.0 直接拒绝
- ▸ 安装时注入 autoupdate: false，防止启动时被 autoupdate 拉回旧版
- ▸ *(小字)* 插件 / 服务端 / 前端分属 opencode-plugins · app-notifier · web-mgmt 三个仓库；曾出现升级后再次启动自动降级、同一问题反复的情况

## P15 · 上报链路搭建：服务端与前端全链路

kicker: REPORT PIPELINE　标题：上报链路搭建：从端侧到 web-mgmt 闭环

顶部流程图（5 步，橙色描边框 + 箭头）
`Opencode /report`（端侧采集与脱敏）→ `app-notifier`（落盘 + MySQL 双写）→ `钉钉通知`（实时推送到群）→ `web-mgmt`（列表页 / 详情页）→ `状态闭环`（open → resolved）

卡片【服务端：文件 + MySQL 双写】（左中）
- ▸ app_mgmt 库新建 issue_report 表，issue_report_db_service.py 沿用 app_info_service.py 的 PyMySQL 模式
- ▸ save_to_db / list_reports / get_report / update_status 四个方法，覆盖写入、分页、详情与状态全路径
- ▸ 新增 3 个 API：GET /alert/issue/list（分页 + 状态 / 上报人筛选）、GET /alert/issue/\<id\>、PUT /alert/issue/\<id\>/status
- ▸ 收到上报后做三件事：JSON 落盘 /data/issue-reports/、写库、发钉钉（消息内附详情页链接）

卡片【前端：列表页 + 详情页】（右中）
- ▸ issueReport.ts 定义 API 服务，TanStack Query hooks 统一管请求与缓存
- ▸ 列表页：报告 ID / 上报人 / 描述 / 模型 / 状态 / 时间六列，Tabs 按 open / in_progress / resolved 筛选，分页 + 刷新，点行进详情
- ▸ 详情页：等宽字体可折叠日志、Monaco Editor 展示 JSON 配置、Select 切换状态完成闭环
- ▸ *(小字)* 前端与 app-notifier 相互独立，详情链接域名在 config.py 中以默认值注入

图（左下）：`Opencode/asset/Pasted image 20260730152903.png` —— 说明文字「web-mgmt 问题报告列表页：状态 Tabs + 分页 + 点行进详情」

卡片【钉钉通知与推进节奏】（右下）
- ▸ 机器人 webhook / secret / @ 人三个变量以 GitOps 方式配置在 gitea-app-manifests
- ▸ 四阶段推进：端到端调试 → 数据库持久化 → web-mgmt 前端 → 联调与体验优化
- ▸ dev → prod → B 红区三套环境全部验证通过（07-31 / 07-31 / 08-09）
- ▸ 通知中追加 web-mgmt 详情页链接，群里点链接即可看完整日志与配置

## P16 · 上报链路上线前的四个阻塞问题

kicker: DEBUGGING　标题：上报链路上线前的四个阻塞问题（2×2 四张卡）

卡片【/report 命令不出现 · 两处独立根因叠加】
- ▸ **现象**　安装完成重启后，`/` 斜杠命令列表里没有 /report
- ▸ **根因一**　安装脚本把 TUI 条目写进 opencode.jsonc；查 OpenCode 源码确认 TUI 配置只读 tui.json / tui.jsonc
- ▸ **根因二**　file:// 插件缺 id 导出，resolvePluginId() 直接抛错；npm 包型插件从 package.json 取名，不受此限
- ▸ **处置**　配置拆分 + 双文件补 id，修复同步回源码仓库共 6 个文件（含 install.sh / uninstall.sh / README）

卡片【上报 403 Forbidden · WAF 拦截】
- ▸ **现象**　插件上报 403，同 URL 用 curl 却成功
- ▸ **排查**　10 步收敛：排除端口 / UA / 请求体大小后，二分 JSON 字段锁定 logs，再逐词测试
- ▸ **根因**　日志中 `shell=/bin/bash` 命中 Tengine WAF 命令注入规则，请求未达 app-notifier 即被拦
- ▸ **处置**　拿到字段级证据后推动 WAF 放行；沉淀「先二分字段、再逐词验证」的排查路径

卡片【安装脚本报错 + 自动降级】
- ▸ **现象**　`Invalid input: expected string, received array plugin.0`；升级后再次启动又被拉回旧版
- ▸ **根因**　v1.1.53 plugin schema 只收纯字符串，不认元组；opencode 的 autoupdate 机制自动降级
- ▸ **处置**　安装时版本校验（< v1.16.0 拒绝）+ 元组配置写法 + 注入 autoupdate: false

卡片【列表页时间多 8 小时 · 时区双重错误】
- ▸ **现象**　页面显示比机器时间多 8h；插件端 toISOString() 行为正确，先排除端侧
- ▸ **根因**　MySQL DATETIME 不带时区 → pymysql 取出 naive 值 → Flask http_date 一律谎报 UTC → 前端 dayjs 再补 +8h
- ▸ **同源反向 bug**　strftime 丢 tzinfo 使 timestamp 列存 UTC，两个 bug 恰好互相抵消，反而掩盖了问题
- ▸ **处置**　改动锁定 app-notifier 一个仓库 2 个文件：naive 值显式标注 Asia/Shanghai、输出带偏移 ISO，前端零改动

## P17 · DSH 红区支持适配与打包

kicker: OFFLINE BUNDLE　标题：DSH（DeepSeek Harness）红区支持适配与打包

卡片（左，大）
- **问题**
  - ▸ 红区无外网机器无法 npm install，Harness Web UI 起不来；构建机还必须是 Linux x86_64（node-pty 按平台现编译）
  - ▸ 多人同机端口冲突；settings.yaml 同时是 Web 模型设置页的写入目标，覆写会抹掉用户选择
- **方案**
  - ▸ Node 运行时 + npm 应用闭包 + 启动脚本组装为 bundle，tar 后与 header 拼成自解压单文件 dsh.sh
  - ▸ 首启播种 settings.yaml：注册 tone 6 个模型、默认 DeepSeek-V4-Flash；已存在时不覆写
  - ▸ 注入 --port 0 由系统分配端口，用户显式 --port 仍优先

卡片【交付与验证】（右上）
- ▸ 交付到 /ppusw/share/yanyihui-dsh/，用户 cp 到家目录 + export TONE_API_KEY 后 `sh dsh.sh web` 即用
- ▸ 净环境（env -i，PATH 无 node）验证解压、播种、随机端口三步；二次运行换端口
- ▸ header 末尾用 exec 替换进程映像，shell 永不把 tar 载荷当脚本解析
- ▸ 以 `[ ! -f ]` 而非 `[ ! -x ]` 判断是否已解压，不依赖执行权限位（摆渡系统 / FAT 介质会丢）
- ▸ *(小字)* --host 0.0.0.0 被产品硬性拒绝（界面无认证），远程访问只能走 ssh 端口转发

卡片【已排除方案】（右下）
- ▸ pnpm deploy --prod：9 个依赖只声明为 peer / devDependencies，剪掉后启动即 ERR_MODULE_NOT_FOUND
- ▸ npx：未能链接 bin，报 dsh: not found，必须显式 npm install
- ▸ SEA 单文件：产物入口是 jsonrpc-agent，不含 Web UI；资源 glob 缺 html / css / 字体
- ▸ *(小字)* 三种方案均有硬阻塞，故选自打包 Node 运行时 + 应用闭包

## P18 · 红区自动值守 Agent 开发

kicker: AUTO ON-CALL　标题：红区支持群自动值守 Agent

顶部流程图（5 步，橙色描边框 + 箭头）
`定时巡检`（热路径增量 / 兜底回看 24h）→ `拉群消息`（checkpoint 增量）→ `确定性过滤分类`（输出 pending / review / cmd）→ `读 FAQ 文档判题`（图文多模态）→ `回复 / DING 告警 / 转人工 + 归档记账`

卡片（左，大）
- **功能定位**
  - ▸ 面向钉钉技术支持群的自动值守机器人：按计划巡检群消息，在团队 FAQ 文档中检索结论
  - ▸ **检索到才回复，检索不到保持静默**，保证每一条答复都有文档依据
  - ▸ 同时把支持同学产出、有复用价值的问答归档回文档，持续扩充知识库
- **架构：确定性脚本 + 大模型语义层分工**
  - ▸ 消息拉取、去重、时间窗过滤、归档配对、命令生成全部下沉到确定性脚本（仅标准库）
  - ▸ 脚本一次性输出 `need_doc` / `pending`（自带 reply_cmd、ding_cmd、download_cmd 模版）/ `review` / `commit_cmd`
  - ▸ 大模型只保留三项语义职责：读文档判题、拟答正文、复核归档，工具往返与出错面大幅缩小
- **两条巡检路径**
  - ▸ 热路径：分钟级、看 checkpoint 增量、复用文档快照，目标是及时回复
  - ▸ 兜底路径：小时/日级、固定回看 24h、强制重拉文档，目标是补漏与收录人工问答

卡片【关键优化】（右上）
- ▸ **耗时 10 分钟 → 2–3 分钟**：消息为空短路结束、无依赖步骤并行、`need_doc` 开关限制文档全文阅读、确定性脚本替代大模型往返
- ▸ **巡检 Prompt 精简**：收敛为固定 5 步；data-auth 不预执行，仅在报权限错时按需触发一次并重试
- ▸ **自动归档**：以引用形式的支持同学答复自动配对为归档候选，轮末统一复核、**串行** append（同一文档并发写会互相覆盖）
- ▸ **纯图片问题**：下载原图后以多模态直接阅读；扩展名不符时先 `file` 识别真实格式再重试

卡片【两个关键决策】（右下）
- ▸ **移除关键词打分**：用户表述高度多样，「启动不了」匹配不到词表里的「起不来」，调阈值又顾此失彼 → 脚本不再判题，只做机器可确定的过滤，判题一律交给大模型语义匹配
- ▸ **DING 告警严格阈值**：DING 是强打扰，仅限重要模型不可用；需同时满足① 明确表达不可用、② 上下文无其他原因指向（用户环境 / 配置用法 / 额度权限）
- ▸ *(小字)* 静态配置集中在 redzone_config.json；回复 @ 提问者的用户 ID 取自群消息，无需静态配置

---

## P19 · 章节页 03

- 序号：03　标题：未来规划　英文：WHAT'S NEXT
- 右侧要点：
  - Warmup 全量落地与效果量化
  - 监控采集口径治理与 DGD 演进
  - Agent 工具链产品化

## P20 · 未来规划

kicker: WHAT'S NEXT　标题：未来规划

卡片【近期 · 落地收口】
- ▸ 录制 Opencode / QwenCode 真实请求，产出各模型 warmup 数据
- ▸ 统一 warmup 脚本从 pdev 推到 pprod、prod，完成 15+ 部署清单迁移
- ▸ 补齐 warmup 前后 TTFT 对比数据，把「预期收益」换成实测收益
- ▸ 收敛模型模版中过宽的 ServiceMonitor selector，根治图例重复复发

卡片【中期 · 部署与监控演进】
- ▸ DGD 部署形态从验证走向生产，推进 P / D 副本可独立伸缩
- ▸ 卡量到位后扩大 PD 分离覆盖的模型范围，复用现有配置模版
- ▸ 把 frontend 监控看板的异常判读口径沉淀为告警规则，从看图转为主动发现

卡片【长期 · Agent 工具链】
- ▸ 自动值守 Agent 持续扩充知识库，提升答复命中率，逐步覆盖更多支持群
- ▸ Opencode 上报链路与值守 Agent 打通：上报的问题可自动归档为 FAQ
- ▸ 把排障经验沉淀为可复用的部署模版与检查清单

卡片【个人成长】（通栏）
- ▸ 持续沉淀笔记与方案文档，把「跑通」变成「可复现、可移交」

## P21 · 谢谢

- 谢谢 / THANK YOU（模版原页，不改）

---

## 内容来源

| 页 | 来源笔记 |
|---|---|
| P4 | `秋招/简历.md` |
| P6 | `asset/红区AI Infra.png`、`PTG/红区Infra.md` |
| P8 | `Dynamo/Dynamo监控链路搭建/模型部署.md` |
| P9–P10 | `PTG/DeepSeek-Flash-0731 SGLang 的PD分离部署.md`、`Dynamo/Dynamo部署流程.md`、`Dynamo/Dynamo配置说明.md` |
| P11 | `Dynamo/Dynamo监控链路搭建/针对Dynamo v1.3.0的Grafana看板.md` |
| P12 | `Dynamo/Dynamo监控链路搭建/看板问题解决.md`、`后续问题解决.md` |
| P13 | `PTG/LLM Warm-up.md`、`PTG/Warmup效果对比.md` |
| P14 | `Opencode/需求手册.md`（需求一 / 二 / 五）、`Opencode/Plugin使用方法.md`、`Opencode/使用手册.md` |
| P15 | `Opencode/需求手册.md`（需求三 / 四 + 联调）、`Opencode/未命名.md`（链路图）、`Opencode/钉钉群消息.md` |
| P16 | `Opencode/bugfix01-没有report接口.md` ~ `bugfix04-时区错误.md` |
| P17 | `PTG/DeepSeek Harness Web UI 离线包构建流程.md` |
| P18 | `AI提效/定时巡检agent.md` |
