---
title: 路由概念
subtitle: Dynamo 路由器的成本模型、worker 选择与路由原语
---

本页说明 Dynamo 路由器如何评估 worker、选择目标，以及它在请求链路中所处的位置。有关 CLI 参数和调优选项，请参阅 [配置与调优](/dynamo/dev/knowledge-base/modular-components/router/configuration-and-tuning)。

## KV 缓存路由

KV 缓存路由通过结合可复用的缓存状态和预测的活跃负载来引导请求，从而优化大语言模型推理。缓存复用减少了冗余的 prompt 计算，而实时的 prefill 与 decode 计量则防止那些缓存丰富的 worker 被压垮。

KV 缓存复用为 LLM 服务的负载均衡引入了复杂性。虽然它能显著降低计算成本，但忽略 worker 各自 KV 状态的路由策略可能导致：
- 由于 worker 选择欠佳而错失缓存复用机会
- 由于请求在各 worker 间分布不均而导致系统吞吐量下降

## 成本计算

![[Pasted image 20261012120749.png]]
在路由器选择成本最低的 worker 之前，请求 token 会被哈希，并结合 KV indexer 的前缀命中情况和 slot tracker 的活跃负载进行评估。Worker 的 KV 事件通过事件平面（event plane）更新 indexer。

成本函数组合了三个与 worker 相关的成本项：

- **Prefill 成本**：已经分配给该 worker 的活跃 prompt 工作，加上进入请求中未命中缓存的 prompt 工作。设备（device）、主机（host）、磁盘（disk）以及共享缓存（shared-cache）命中会根据其配置的信用额度（credits）降低该成本。
- **Decode 成本**：已经分配给该 worker 的活跃 KV 块，加上为进入请求所预测的块。
- **活跃请求成本**：对该 worker 上每个已处于活跃状态的请求，可选地计入一笔等值块（block-equivalent）开销。该项可用于表示那些步进延迟更贴近批大小（batch size）而非驻留 KV 占用量的 decode 场景。

```text
raw_prefill_blocks = active_prefill_blocks + incoming_prompt_blocks
adjusted_prefill_blocks = max(0, raw_prefill_blocks - overlap_credit_blocks)
potential_decode_blocks = active_decode_blocks + incoming_active_blocks
active_request_blocks = decode_active_request_weight * active_requests
cost = prefill_load_scale * adjusted_prefill_blocks + potential_decode_blocks + active_request_blocks
```

`overlap_credit_blocks` 组合了所配置的 device、host、disk 和 shared-cache 信用额度。当某个缓存丰富的 worker 拥有过多活跃 prefill 负载时，`overlap_score_credit_decay` 可以降低其中 device 本地那部分的信用额度。调整后的 prefill 项会被钳制在零，因此重叠信用额度永远不会使其变为负值。`decode_active_request_weight` 默认为 `0`，所以活跃请求项是可选启用的。路由器会选择成本最低且符合条件的 worker。有关精确的调优行为，请参阅 [配置与调优](/dynamo/dev/knowledge-base/modular-components/router/configuration-and-tuning#tuning-guidelines)。

实验性的条件解耦（conditional-disaggregation）路径在禁用 prefill 跟踪且重叠信用额度仍为正值时，会对 decode-worker 使用一个例外规则：`cost = max(0, potential_decode_blocks - overlap_credit_blocks) + active_request_blocks`。这使得一个缓存热点的 decode worker 能够绕过常规的 prefill 路径。

### 活跃负载建模

prefill 与 decode 的预测都包含进入请求所带来的负载，加上已经分配给每个 worker 的活跃负载。

#### Prefill 负载建模

对于 prefill 负载，路由器通过从请求的输入 token 中减去其已缓存的前缀 token，来估算每个候选 worker 未命中缓存的 prompt 工作量。

默认情况下，该有效 prefill 负载会以全额计费，直到第一个输出 token 标志着 prefill 完成。启用 `--router-prefill-load-model ais` 后，路由器还会向 [AISimulate (AIS)](/dynamo/dev/knowledge-base/concepts/simulation/ai-simulate/overview) 请求一个预期 prefill 时长，该请求使用有效 ISL 和已缓存前缀长度进行计算。活跃负载跟踪器以最旧的活跃 prefill 作为时间锚点，并将已流逝的时间应用于该 worker 聚合后的建模 prefill 积压量。当最旧的请求完成时，下一个活跃 prefill 会成为新的锚点。如果某个被建模的非锚点请求先完成，跟踪器会调整锚点，以保持所报告负载的连续性。
![[Pasted image 20261012120833.png]]

时间线展示了 AIS 如何在聚合的建模积压量上衰减活跃 prefill 负载，并与"直到第一个输出 token 前采用静态计量"的方式进行对比。

该模型仅改变路由器侧的 prompt 负载计量；它不会改变后端的批处理或执行。

#### Decode 负载建模

对于 decode 负载，路由器会跟踪每个 worker 的活跃 KV 块和活跃请求数。它在同一个针对具体请求的 worker 负载预测中捕获这两个值。默认情况下，该成本涵盖已分配给活跃请求的 prompt 侧块，并在每个请求完成时释放它们。

启用 `--router-track-output-blocks` 后，路由器还会在生成过程跨越块边界时添加占位的输出块。如果请求包含 `nvext.agent_hints.osl`，那么这些输出块以及结构上互斥的 prompt 后缀会根据朝预期输出长度推进的进度获得一个分数权重。共享的 prompt 块保留全额权重。这个预期 OSL 的代理值让接近完成的请求贡献更少的未来 decode 负载。若没有预期 OSL，被跟踪的输出块会以全额权重计入，直到请求完成。

当 `--router-decode-active-request-weight` 为正值时，每个活跃请求还会额外计入所配置的等值块成本。当 decode 延迟对请求数敏感时，这可以改善数据并行（data-parallel）的批均衡；但当 KV 内存流量仍是主导成本时，它可能会降低缓存局部性，或对批处理造成过度惩罚。默认值为 `0`。

有关启用这些模型的参数，请参阅 [配置与调优](/dynamo/dev/knowledge-base/modular-components/router/configuration-and-tuning)。

## Worker 选择

路由器会选择成本最低的 worker。当 `router_temperature` 被设为非零值时，路由器会在归一化后的成本 logits 上使用 softmax 采样，为选择引入随机性，这有助于负载分布。

在打分之前，路由器会根据请求允许列表（allow-lists）、精确固定（exact pins）、DP-rank 边界、所需 taints 以及繁忙阈值（busy-threshold）过载状态来筛选候选者。有关这些硬性资格规则，请参阅 [路由器筛选](/dynamo/dev/knowledge-base/modular-components/router/router-filtering)。

若只想用静态链接的 Rust 代码替换打分和挑选阶段，请参阅 [编写自定义路由策略](/dynamo/dev/knowledge-base/modular-components/router/write-custom-routing-strategies)。

当请求在策略类队列（policy-class queues）中等待时，加权
[Deficit Round Robin 队列调度](/dynamo/dev/knowledge-base/modular-components/router/deficit-round-robin) 会在 worker 打分运行之前，先选出要派发的物理类（physical class）。

## 使用 KV 缓存路由器

要启用 KV 缓存感知路由，请像这样启动前端节点：

```bash
python -m dynamo.frontend --router-mode kv
```

当 KV 块被创建或移除时，引擎会通知 Dynamo 路由器。这些匹配会成为缓存信用额度（cache-credit）的输入，用于后续路由决策所依据的"缓存加负载"综合评分。

要评估 KV 感知路由带来的收益，可以将你的工作负载在使用 `--router-mode random|round-robin` 时的性能与 KV 感知路由进行对比。

有关详细的 CLI 参数和高级配置选项，请参阅 [配置与调优](/dynamo/dev/knowledge-base/modular-components/router/configuration-and-tuning)。

## 基础路由

在将请求从一个组件发送到另一个组件的端点时，Dynamo 支持多种路由策略。

首先，创建一个绑定到组件端点的客户端。这里我们获取一个绑定到 `worker` 组件 `generate` 端点的客户端。

```python
client = await runtime.endpoint("dynamo.worker.generate").client()
```

随后你可以使用客户端类所暴露的默认路由方法，向 `worker` 组件发送请求。

- **轮询路由（Round-robin）**：默认策略，可通过标准端点客户端上的 `client.generate()` 使用，也可通过 `client.round_robin()` 显式调用
- **随机路由（Random）**：通过 `client.random()` 随机选择一个 worker
- **二选一乘幂路由（Power-of-two）**：采样两个 worker 并选择负载较轻的那个，通过 `--router-mode power-of-two` 启用
- **直连路由（Direct）**：通过 `client.direct(input, component_id)` 显式指向特定 worker
- **最小负载路由（Least-loaded）**：路由到活跃连接数最少的 worker，通过 `--router-mode least-loaded` 启用
- **设备感知加权路由（Device-aware weighted）**：结合 CPU/非 CPU 比例预算，并在所选设备组内进行最小负载选择，通过 `--router-mode device-aware-weighted` 启用
KV 缓存路由使用直连路由，并配合一种特殊的 worker 选择算法。

有关对 KV 路由器性能进行基准测试，请参阅 [KV 路由器 A/B 基准测试指南](/dynamo/dev/recipes/benchmarks/kv-router-ab-testing)。
有关自定义路由逻辑和高级模式，请参阅 [路由模式](/dynamo/dev/knowledge-base/modular-components/router/router-examples#routing-patterns)。

## 设备感知加权路由

`device-aware-weighted` 面向 CPU 与非 CPU worker 共享同一端点的异构机群（heterogeneous fleets）而设计。路由器不会比较原始的在途请求数（in-flight counts），而是跨 CPU 组与非 CPU 组比较一个按能力归一化的负载，然后在胜出的组内选择负载最轻的 worker。

```text
normalized_load = total_inflight(group) / (instance_count(group) x throughput_weight)
```

吞吐量权重对于 CPU worker 为 `1`，对于非 CPU worker 为 `DYN_ENCODER_CUDA_TO_CPU_RATIO`。这使得路由器能够按设备能力成比例地分配请求，而不是长期让较慢的设备处于饥饿状态。

一次完整的多模态 embedding-cache 命中会绕过 CPU 与非 CPU 的比例。此时路由器会在那些持有请求中每一个不同缓存键（cache key）的 worker 之间，选择负载最轻的一个。部分命中则继续走加权组选择流程。请参阅 [Embedding 缓存](/dynamo/dev/multimodal/embedding-cache#configuration)。

当只存在一种设备类别时，该行为会退化为标准的最小负载路由。
