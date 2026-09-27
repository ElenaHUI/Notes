## 【P1 · 封面】开场

各位老师、评委好,我是闫一慧,来自数据中心计算软件团队,测试 & 软件 DevOps 方向,担任软件 DevOps 实习生。我的实习从今年 7 月 21 日开始至今。今天很荣幸向大家汇报我这段时间的工作,请各位老师批评指正。

## 【P2 · 目录】

我的汇报分三部分:第一部分做个简单的自我介绍;第二部分是这段时间的实习工作总结,也是今天的重点;第三部分聊一聊我对未来的规划。

## 【P3–P4 · 个人介绍】

先做个自我介绍。我本科毕业于西安电子科技大学软件工程专业,目前在华东师范大学读软件工程硕士,预计 2027 年 6 月毕业。

实习期间我的工作大致分三条线:一是**模型侧**,负责 DeepSeek-V4-Flash 等模型在自研 PPU 芯片上的 PD 分离部署、DGD 形态部署和参数调优;二是**平台侧**,负责 Dynamo frontend 的监控链路搭建与看板适配、模型 Warmup 方案的统一落地,以及模型的 P2P 权重加载;三是 **Agent 方向**,负责红区 Agent 工具链的开发,包括 Opencode 上报插件、DSH 离线包和自动值守 Agent。

技术栈上,推理引擎主要用 SGLang 和 vLLM,分布式传输用 Mooncake 和 RDMA,云原生这块是 Kubernetes 加 ArgoCD,可观测性用 Prometheus 和 Grafana。

## 【P5–P7 · 工作全景 & 时间线】

这是我实习工作的全景。整体可以归纳为三块: **模型部署、链路优化、Agent 适配**。

从部署与运行时来看,编排层做了 DeepSeek-V4-Flash 的 Dynamo DGD 部署,运行层做了 Warmup 机制和模型权重的 P2P 加载,交付层用 Gitea 加 ArgoCD 的 GitOps 声明式发布。监控与 Agent 这块,搭了 Dynamo frontend 的指标采集链路和 Grafana 看板,Agent 侧做了 Opencode 上报插件全链路、DSH 红区离线包和自动值守 Agent。

大家看这条时间线,从 7 月底的 Opencode 上报链路,到 8 月的监控搭建、DSH 离线包、DeepSeek PD 分离部署,再到 9 月的 Warmup 和 P2P 权重分发,基本是按"先打通链路、再深入部署、最后做优化沉淀"的节奏推进的。下面我按三个部分展开讲。

## 【P8–P10 · Part 1 模型部署】

**第一部分,模型部署。**

先说模型的上线接入。整个流程是标准的 GitOps:在 gitea-app-manifests 里更新推理镜像、对齐卡数和资源限额、改好模型配置,然后用 ArgoCD 按环境分批 sync,同步后验证域名转发和实际推理链路,检查各资源健康状态,最后用 Tone 平台做连通性测试和压测,根据监控数据定位瓶颈、调整参数。

更进一步是 SGLang 适配 DeepSeek-V4-Flash 的 PD 分离部署。我们用的是 DynamoGraphDeployment 这种形态,Prefill 和 Decode 各一个 Worker,每个 8 卡 PPU,通过 disaggregation-mode 区分角色,服务发现用 etcd、事件面用 nats、传输走 Mooncake。

和过去相比,以前是 P、D 各一份 Deployment,靠 mini-lb 手工串联,副本和端口都是硬编码;现在一份声明就能由 Operator 展开出 Frontend、P、D 和配套 Service,还会自动生成 ServiceMonitor,控制面也预留了 Planner 做后续扩缩容。针对性优化上,P 端保留 NSA Context Parallel 承担长输入 prefill,D 端用 DP attention 提升并发,注意力算子也做了拆分,flashmla 负责 decode、fa3 负责 prefill。调优后吞吐提升很明显。

## 【P11–P14 · Part 2 链路优化(上):监控与 Warmup】

**第二部分,链路优化。**

首先是 Dynamo frontend 的监控链路。我以 Dynamo v1.3.0 官方看板为底本,按红区实际部署形态适配了指标名、变量和图例,采集链路是 ServiceMonitor → Prometheus → Grafana。最终落地了四块看板:Dynamo Dashboard 关注延迟、吞吐、缓存;Disaggregated Analysis 看 P/D 和 GPU、NVLink 利用率;Planner 看弹性决策和 SLA;Operator 看 CRD 调谐和资源健康度。每块看板我都配了详尽的说明文档。

第二个是 Warmup 方案。问题是服务冷启动后第一条请求特别慢——因为 opencode 首条消息带了大约 15k tokens,叠加权重加载、kernel JIT 编译、CUDA Graph 捕获、KV cache 分配这些一次性开销。我的方案是录制 opencode 真实请求做回放预热:录制真实流量导出成 JSONL,Pod 启动后逐条回放,提前完成 prefill 和 kernel 编译。效果很直接,**未预热的首次请求端到端要 3 分 56 秒,预热后只要 10 秒**。

## 【P15–P17 · Part 2 链路优化(下):ModelExpress P2P】

链路优化里最有分量的是 ModelExpress 的 P2P 权重分发。

背景是扩容痛点:新扩的 Pod 要重新读取并通过网络搬运 GB 级权重,还要完成模型构造和显存加载,启动很慢;多个 Pod 同时扩容还会并发读 PVC,形成 I/O 瓶颈。ModelExpress 的思路是控制面和数据面分离,MX Server 做元数据登记和查询,MX Client 通过 NIXL/UCX RDMA 显存直传,引擎间点对点分发权重。

上线流程分五步:装 CRD、部署 MX Server、构建 Worker 镜像、配置 Prefill/Decode、最后做扩容验证。我基于 Holmes 加 GLM-5.3 完成了部署,解决了过程中的一系列问题,并把 P2P 方案和原生磁盘加载做了对比。

**验证结果很亮眼:权重搬运从磁盘加载的 371 秒降到 P2P 的 7.97 秒,约 46 倍加速;模型初始化从 425 秒降到 63 秒,约 6.7 倍;RDMA 传输吞吐达到 69.6 Gbps。** 结论是 P2P 显存直传的能力和性能都已验证,适用于增量扩容、故障恢复和滚动升级,冷启动没有 source 时会自动回退磁盘,后续会继续完善推理正确性和元数据自动回收。

## 【P18–P23 · Part 3 Agent 适配】

**第三部分,Agent 适配。**

第一件事是 Opencode 上报插件。背景是红区部署了 vLLM 和 SGLang 推理服务,用户用 opencode 做代码辅助开发,遇到对话中断、响应异常、连接超时这类端侧问题时,过去上报和日志抓取都很繁琐、追踪不清晰。我做了一条完整链路:opencode 的 /report 端侧采集脱敏,经 app-notifier 落库到 MySQL,同时钉钉实时推送到群,web-mgmt 提供列表页和详情页,状态从 open 到 resolved 形成闭环。过程中也踩了不少坑:上报 403 是命中了 WAF 命令注入规则,推动放行解决;页面时间多 8 小时是 MySQL DATETIME 没带时区,显式标注为 Asia/Shanghai;还有安装脚本报错,是插件版本不兼容加自动降级导致,我加了版本校验并关闭了 autoupdate。

第二件是 DSH 红区离线包。红区没有外网,官方 npm install 用不了,而且 DSH 的 Web UI 需要 22 以上的 Node,多人同机还会端口冲突。我把 Node 运行时、npm 应用闭包和启动脚本打包成一键式自解压的 dsh.sh,内置动态端口探测避免冲突,默认网关改成 Tone 并自动询问可用模型。安全上梳理了三级沙箱、权限升级审批、只放通回环访问等特性,并沉淀了完整文档。

第三件是红区支持群的自动值守 Agent。它面向钉钉技术支持群,自动巡检消息、在 FAQ 文档里检索结论并答复,减少人工答疑工作量,同时把有价值的问答归档回文档、持续扩充知识库。架构上是"确定性脚本 + 大模型语义理解":消息拉取、去重、归档配对这些固定到脚本,大模型只负责读文档、拟答、复核归档。经过短路、并行、脚本替代等优化,单轮耗时从 10 分钟降到 2–3 分钟,还支持群内图片识别,并对重要模型不可用做了严格阈值的 DING 告警。目前累计答疑 60 多次,收到一致好评,现在仍在持续值守。

## 【P24–P25 · 未来规划】

关于未来规划,我分三个阶段:**近期**把 P2P 转发适配到 vLLM 和 SGLang,并协助平台网关侧开发;**中期**协助最新模型的测试部署、完善平台功能;**长期**持续调研前沿模型部署方案、更多 Agent 工具和 AI 提效手段,也希望能深入了解 PPU 底层原理、更好地支撑团队。个人成长上,我会继续沉淀笔记和方案文档。

## 【P26 · 结尾】

以上就是我这段时间的工作汇报。非常感谢团队和导师的帮助与信任,也感谢各位老师的时间。我的汇报到此结束,请各位老师提问指正,谢谢!
