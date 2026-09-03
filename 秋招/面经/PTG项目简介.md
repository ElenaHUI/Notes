---
tags:
  - 面经
  - 项目简介
  - PTG
  - GitOps
  - AI-infra
aliases:
  - PTG项目介绍
  - 项目简介
type: 项目简介
scope: 通用（跨公司复用）
date: 2026-09-03
---

# PTG 项目简介（面试通用版）

> **用途**：面试开场「介绍一下你的项目 / 你实习做了什么」的标准答案。
> 三个长度版本按场合取用，后面的拆解表用来应付追问。
> **相关面经**：[[秋招/面经/百度 AI infra面经|百度 AI Infra]]、[[秋招/面经/商汤 大模型系统工程师面经|商汤 大模型系统]]

---

## 一、30 秒版（一句话定位）

> 我在**红区（内网隔离、无外网）环境**里搭一套**供内部使用的大模型基础设施**：以 **GitOps（Gitea + ArgoCD + Kustomize）** 为交付主干，往下把 7 个 MoE / Dense 大模型在**平头哥自研 PPU** 上用 SGLang / vLLM 跑成生产级推理服务（含 PD 分离、RDMA、量化），往上提供统一网关、监控看板和性能分析平台，并支撑 OpenCode / QwenCode 这类内部编码 Agent 落地。

---

## 二、2 分钟标准版（面试开口用）

**1）背景 —— 为什么是 GitOps**

红区是完全隔离的内网环境，**没有外网**：不能 `pip install`、不能拉公网镜像、不能连 SaaS。所以所有交付必须走**声明式 + 版本化**的路子——配置全部落在自托管 **Gitea** 仓库里，由 **ArgoCD** 按环境（pdev / pprod / prod）拉取并 reconcile，**Kustomize** 的 base + overlays 处理环境差异。任何一次上线都是「提 MR → 评审 → 合并 → ArgoCD 自动同步」，可回滚、可审计、可复现。

**2）我的角色 —— 整条链路的 owner**

不是只做其中一小块。从**模型上卡 → 参数调优 → K8s 编排 → 网络/RDMA 打通 → 压测标定 → 故障定位 → 上线配置 → 监控报表**，这条链路是我负责的。

**3）三块具体工作**

- **模型部署与调优**：在 PPU 真武 810E（单卡 96GB HBM，**显存大但算力低**）上，用 W4A8 / W8A8-INT8 量化 + PD 分离 + Mooncake RDMA 传输，把 Kimi-K2.6 这类 MoE 模型跑到生产配比 **3P2D（48 卡 Prefill + 32 卡 Decode = 80 卡）**，满足 **TTFT P99 < 2~3s、TPOT < 50~60ms** 的 SLA。
- **平台建设**：litellm-proxy 统一网关（多模型路由 + 真实请求抓取/回放）、web-mgmt 管理台、Prometheus + Grafana 观测链路，以及一个让 Agent 自动连 Prometheus 出**周报/日报性能分析**的 Skill，覆盖 7 个在线模型的 TTFT / TPOT / 吞吐 / KV 利用率 / KV 命中率。
- **Agent 侧**：支撑 OpenCode / QwenCode 等内部编码 Agent 接入；因为红区无外网，还要做**离线交付**——比如把 Harness Web UI 打成自解压单文件（内含 Node 运行时 + 应用闭包）直接投放到目标机。

**4）一个能体现工程判断的例子（主动抛）**

模型启动 warmup 原本用一段通用纯文本，跟编码 Agent 的真实请求（多轮对话 + system prompt + tool_calls + 长上下文代码）差距很大，预热效果有限；而且 warmup 脚本在 4 个 ConfigMap 里有 4 份副本、核心逻辑 95% 相同，被 15+ 个 deploy.yaml 引用。我做的事是：**从网关侧录制真实请求 → 导出成 JSONL → 启动时回放**，同时把 4 份脚本合并成 1 份共享 ConfigMap，**差异全部收敛到环境变量**，做到 100% 向后兼容灰度上线。

---

## 三、GitOps 主干（差异化亮点，别漏讲）

大多数候选人只会讲「我调了 SGLang 参数」。GitOps 这层能体现你是**做基础设施**而不是**做一次性部署**。

| 层 | 组件 | 作用 |
| --- | --- | --- |
| 代码托管 | **Gitea**（自托管） | 红区无外网，Git 服务必须自建；仓库 `gitea-app-manifests` |
| 持续部署 | **ArgoCD** | 每个环境（pdev / pprod / prod）一个 Application，拉取仓库自动 reconcile，支持回滚 |
| 配置编排 | **Kustomize** | base + overlays：同一份模型部署，按环境覆盖副本数 / 资源 / 参数 |
| 仓库结构 | `foundation/` | 公共组件：kong（API 网关）、es、filebeat、llm-warmup |
| 仓库结构 | `apps/{engine}/{model}/overlays/{env}/deploy.yaml` | 每个模型 × 每个环境一份，如 `apps/vllm/qwen3-coder-next/overlays/pdev/` |
| 交付物 | 离线包 / 私有 registry | 无外网 → 镜像、npm 闭包、Node 运行时都要预先打包投放 |

**可能被追问**：

- *为什么不用 Helm？* → Kustomize 是纯声明式 patch，没有模板语法，diff 出来就是最终 YAML，评审和排障更直观；ArgoCD 对两者都是一等支持。
- *配置漂移怎么办？* → ArgoCD 持续对比集群实际状态与 Git 期望状态，漂移会被检出并自动/手动纠正；Git 是唯一事实来源。
- *怎么做灰度？* → 先改 pdev overlay 验证，再 pprod，最后 prod，三个环境三份 overlay，逐级推进（warmup 改造就是这么上的）。

---

## 四、三条业务线拆解（追问时展开）

### A. 模型部署

| 维度 | 内容 |
| --- | --- |
| 硬件 | 平头哥 PPU 真武 810E，单卡 96GB HBM，显存大 / 算力低 |
| 引擎 | **SGLang**（Kimi-K2.6、GLM-5.2）、**vLLM**（Qwen3-Coder-Next、Qwen3.5-397B-A17B-INT8、MiniMax-M2.7、DeepSeek-V4-Flash、Qwen3.6-27B） |
| 架构 | PD 分离 + Dynamo DGD（DynamoGraphDeployment）编排 + etcd 服务发现 + nats 事件面 |
| 量化 | W4A8 / W8A8-INT8（注意 `w4a8` 不支持开 EP） |
| 传输 | Mooncake Transfer Engine + RDMA，8 张 `mlx5_bond_0..7` 并行；机内走 ICN / NVLink |
| 路由 | sgl-router × 2，开 **cache-aware routing**（router 维护近似 radix tree 选 P 节点） |
| 生产配比 | Kimi-K2.6：**3P2D = 48P + 32D = 80 卡** |
| Workload | 内部应用，**长输入短输出**，平均 input 80K+ tokens → 配比偏 P |

→ 细节见 [[秋招/面经/百度 AI infra面经|百度面经 Q1 / Q19]]、[[秋招/面经/商汤 大模型系统工程师面经|商汤面经 Q1-Q9]]、[[PTG/kimi2.6 PD分离部署记录]]

### B. 平台

| 组件 | 能力 |
| --- | --- |
| **litellm-proxy** | 统一网关：多模型路由、按 API Key / User ID 抓取完整请求（含 `transformed_request` 标准 OpenAI 格式）、请求回放转发、`/capture/export-warmup` 导出 |
| **web-mgmt** | 管理台前端：抓取配置面板、抓取结果面板、回放弹窗、Web 模型设置页 |
| **可观测** | Prometheus + Grafana（Dynamo v1.3.0 专用看板）；SGLang 侧开 `--enable-metrics --enable-cache-report --enable-expert-distribution-metrics` |
| **性能分析 Skill** | Agent 连 Prometheus 采集 7 个模型的 TTFT / TPOT / 吞吐 / KV 利用率 / KV 命中率，weekly（自然周环比）+ daily（日环比）两种模式，定时产出报告 |
| **共享存储** | hostPath `/ppusw/devops/llm_platform/` → 容器 `/warmup-data/`，所有模型 Pod 挂载 |

→ 细节见 [[PTG/LLM Prometheus 性能分析报告生成Skill]]、[[Dynamo/Dynamo监控链路搭建/针对Dynamo v1.3.0的Grafana看板]]

### C. Agent

| 方向 | 内容 |
| --- | --- |
| **消费侧** | OpenCode / QwenCode 等内部编码 Agent，经 litellm-proxy 调用后端模型；OpenCode 用 `x-session-affinity` header 做 session 关联 |
| **交付侧** | 红区无外网 → Harness Web UI 打成**自解压单文件离线包**：内含 Node 运行时 + npm 应用闭包 + 启动脚本，`settings.yaml` 首次启动播种且已存在不覆写，端口交 OS 分配避免多实例冲突 |
| **提效侧** | 定时巡检 Agent（支持读图，替代关键词匹配） |
| **协议** | MCP / A2A 类工具对接、幂等与超时重试设计 |

→ 细节见 [[PTG/DeepSeek Harness Web UI 离线包构建流程]]、[[秋招/面经/百度 AI infra面经|百度面经 Q15-Q18]]、[[AI提效/定时巡检agent]]

---

## 五、数字弹药（面试要报数，别只说"优化了"）

| 指标 | 数值 | 用在哪 |
| --- | --- | --- |
| 在线模型数 | **7 个**（SGLang 2 + vLLM 5） | 说明平台规模 |
| 生产卡数 | **80 卡**（48P + 32D） | 说明部署体量 |
| SLA | TTFT P99 **< 2~3s**、TPOT **< 50~60ms** | 说明有硬约束、不是玩具 |
| bound line | 并发 **30** 时 TPOT 升到 **60ms** | 说明会用真实流量反推容量 |
| 平均输入长度 | **80K+ tokens** | 解释为什么配比偏 P |
| 环境数 | **3 套**（pdev / pprod / prod） | 说明 GitOps 分级发布 |
| warmup 收敛 | 4 份 ConfigMap → **1 份**，影响 **15+** deploy.yaml，**100%** 向后兼容 | 说明工程治理能力 |
| RDMA 网卡 | **8 张** `mlx5_bond` 并行 | 说明传输链路调优深度 |

> [!warning] 待补数字（有就填，没有别编）
> - [ ] warmup 改造后 TTFT P99 实际下降多少 / 首请求耗时对比（见 [[PTG/Warmup效果对比]]）
> - [ ] 平台服务的内部用户数 / 日请求量
> - [ ] 上线周期从多久缩短到多久（GitOps 收益的量化）
> - [ ] 单次故障定位平均耗时、可用性数字

---

## 六、按岗位裁剪

| 岗位 | 开口重点 | 弱化 |
| --- | --- | --- |
| **AI Infra / 推理** | PD 分离、RDMA、量化、配比标定、PPU 适配踩坑 | 离线包、管理台前端 |
| **Agent Infra** | Agent 接入链路、MCP / 工具协议、Harness 交付、warmup 用真实 Agent 流量回放 | 网络 MTU 类细节 |
| **平台 / SRE** | **GitOps 主干**、三环境灰度、可观测体系、性能报告自动化、配置收敛治理 | 算子 / 量化细节 |
| **通用后端** | GitOps 声明式交付 + 网关 + 配置治理，把大模型当"一种负载"讲 | 硬件型号 |

---

## 七、常见追问速查

| 追问 | 一句话答法 | 展开 |
| --- | --- | --- |
| 为什么 PD 分离？ | Prefill 是 compute-bound、Decode 是 memory-bound，PPU 显存大算力低，拆开才能各取所需 | [[Infra/PD分离]] |
| P:D 配比怎么定？ | 理论估算起点 → 阶梯压测标定 → SLA 约束选优 → 上线后真实流量修正 | 百度面经 Q19 |
| 为什么是小顶堆…（算法题） | — | [[Leetcode/CodeTop手撕40题背诵手册]] |
| KV Cache 怎么管的？ | radix tree + 分页，类比页表/虚拟内存，所以没有外部碎片 | 百度面经 Q4-Q7 |
| RDMA 过不过 CPU？ | 数据面 kernel bypass 直达显存，控制面仍要 CPU 建连/注册内存 | 百度面经 Q11 |
| 静态配比的局限？ | 波峰波谷 + 长短混合 → 要么浪费要么打爆，所以要 Dynamo 这类动态调度 | 百度面经 Q19 第五步 |
| 红区为什么要离线包？ | 无外网 → 依赖闭包 + 运行时全部预打包，自解压单文件投放 | [[PTG/DeepSeek Harness Web UI 离线包构建流程]] |
