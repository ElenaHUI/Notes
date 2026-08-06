---
title: NVIDIA Dynamo 博客学习笔记
date: 2026-08-03
source: https://developer.nvidia.com/blog/introducing-nvidia-dynamo-a-low-latency-distributed-inference-framework-for-scaling-reasoning-ai-models/
authors: Amr Elmeleegy, Harry Kim, David Zier, Kyle Kranen, Neelay Shah, Ryan Olson, Omri Kahalon
published: 2025-03-18
tags:
  - dynamo
  - llm-inference
  - pd-disaggregation
  - kv-cache
  - nixl
  - nvidia
  - reasoning-model
---

# NVIDIA Dynamo 博客学习笔记

这篇博客是 NVIDIA 在 GTC 2025 上发布 Dynamo 的官方技术文章，把 Dynamo 定位成一个面向生成式 AI 和推理模型的高吞吐、低延迟开源推理 serving 框架。它基于 Triton Inference Server 演进而来，代码仓库在 `ai-dynamo/dynamo`，后续也会通过 NVIDIA AI Enterprise 和 NIM microservices 提供支持。

## 一、核心定位与背景

### 1.1 为什么需要 Dynamo

当前 LLM serving 面临几个典型矛盾：
![[Pasted image 20260803155626.png]]

- **Prefill 是计算密集，Decode 是内存/带宽密集**：两者混布在同一 GPU 上时，batch 中只要有长输入的 prefill 请求，就会拖慢同 batch 内 decode 请求的 inter-token latency（ITL）。
- **Reasoning 模型让输出长度暴涨**：像 DeepSeek-R1 这类模型，输出 token 数量可能远超过普通对话模型，decode 阶段的内存压力和延迟被进一步放大。
- **KV Cache 复用率低**：相似请求、多轮对话、前缀共享等场景里，如果不做路由，KV cache 会被反复重算，浪费大量算力。
- **GPU 利用率不均**：突发流量、输入/输出长度分布不均时，prefill 和 decode 的负载很难自然平衡。

Dynamo 的设计目标就是把这些拆开治理：把 [[PD分离]]、让 GPU 动态调度、让请求按 KV cache 位置智能路由、让 KV cache 跨多级存储卸载。

### 1.2 与现有生态的关系

- **向后兼容 Triton**：Dynamo 是在 Triton Inference Server 基础上构建的，已有的 Triton 生产部署不会被抛弃，NVIDIA 会继续维护。
- **多后端支持**：PyTorch、SGLang、NVIDIA TensorRT-LLM、vLLM 都能接入。
- **开源 + 商业两条线**：GitHub 上开源，同时通过 NIM/AI Enterprise 提供企业级支持。

## 二、关键性能数据

博客给出了两组核心对比：
![[Pasted image 20260803155656.png]]

| 场景 | 配置 | 收益 |
|------|------|------|
| DeepSeek-R1 671B on GB200 NVL72 | TensorRT-LLM, FP4, ISL/OSL 32K/8K；无 Dynamo 用 inflight batching TEP16PP4DP4，有 Dynamo 用 PD 分离 Context EP4DP16 + Generation EP64DP3 | 请求处理量提升 **30x** |
| Llama 70B on Hopper | vLLM, FP8, ISL/OSL 3K/50；无 Dynamo 用 TP8DP2，有 Dynamo 用 PD 分离 Context TP2DP4 + Generation TP8 | 吞吐 **翻倍以上** |

这些数据是在特定 workload 和硬件配置上测出来的，实际收益取决于输入输出长度分布、batch size、并行策略等因素，但方向很明确：PD 分离 + 智能路由 + 多级 KV cache 对推理效率提升非常显著。

## 三、整体架构与数据流

- NVIDIA Dynamo Planner
- NVIDIA Dynamo Smart Router
- NVIDIA Dynamo Distributed KV Cache Manager
- NVIDIA Inference Transfer Library (NIXL)
![[Pasted image 20260803155725.png]]
## 四、核心组件详解

### 4.1 Disaggregated Serving（PD 分离）

这是 Dynamo 最底层的设计变化。传统做法把 prefill 和 decode 放在同一批 GPU 上，用 inflight batching 让它们共享资源；Dynamo 则把两个阶段物理拆开：

- **Prefill Worker**：只做 prompt 的全量计算。这个阶段是 compute-bound，可以用较小的 tensor parallelism（TP）来减少 all-reduce 通信。
- **Decode Worker**：只做自回归生成。这个阶段是 memory-bound，通常用更大的 TP 来优化内存访问和权重放置。

拆开之后的好处：

1. **独立扩缩容**：输入流量大时加 prefill GPU，输出流量大时加 decode GPU。
2. **独立并行策略**：prefill 选通信少的策略，decode 选内存友好的策略。
3. **TTFT 和 ITL 解耦**：长输入不会阻塞短输出的 decode，反之亦然。
4. **资源利用更充分**：避免一种阶段挨饿、另一种阶段过载。

### 4.2 NVIDIA Dynamo Planner
![[Pasted image 20260804174319.png]]

Planner 是一个持续监控 GPU 容量并结合 SLO 做决策的调度器。它考虑的指标包括：

- TTFT（Time-To-First-Token）
- ITL（Inter-Token Latency）
- 当前 prefill / decode GPU 的利用率
- 输入/输出长度分布

它能做的决策包括：

- 采用 disaggregated serving 还是 aggregated serving；
- 在 prefill 和 decode 之间动态调整 GPU 数量；
- 当 decode GPU 空闲时，让它们临时处理 prefill 任务，反之亦然。

博客举了一个例子：突发大量长输入/短输出的 summarization 请求时，prefill GPU 会被打满，而 decode GPU 可能很闲；Planner 可以临时把 decode GPU 拉去帮忙做 prefill，或者把部分 GPU 重新分配给 prefill 池。

### 4.3 NVIDIA Dynamo Smart Router

Smart Router 解决的是“请求该发到哪台 GPU/哪个 worker”的问题。它的核心目标是**减少 KV cache 重算**。

实现方式：

- 对请求做 hashing；
- 用 **Radix Tree** 维护整个集群里已缓存的 KV block 位置；
- 维护插入和驱逐策略；
- 对每条新请求，计算它与集群中已缓存 block 的 overlap score；
- 综合 cache hit、workload balance、GPU capacity 做路由。

这与 vLLM 的 RadixAttention / Prefix Caching 思路一致，但扩展到**集群级别**：不是单卡内部共享前缀，而是把前缀缓存的位置信息暴露给全局路由器，让请求命中离它最近或负载最轻的缓存副本。

博客给出的验证实验：

- 两台 HGX-H100 节点；
- 八个 DeepSeek-R1-Distill-Llama-70B 实例；
- vLLM + FP8 + TP2；
- 10 万条真实 R1 请求，平均 ISL/OSL 4K/800；
- 结果：TTFT 和平均请求延迟都有改善。

### 4.4 NVIDIA Dynamo Distributed KV Cache Manager

KV cache 是推理服务里最大的内存消耗来源之一。Dynamo 把它当成一个**跨多级存储的缓存系统**来管理：
![[Pasted image 20260804175703.png]]

- **L1：GPU HBM**：最热数据；
- **L2：CPU host memory**：次热数据；
- **L3：本地 SSD / 网络对象存储**：冷数据。

Manager 负责：

- 缓存策略与驱逐策略；
- 把旧的、低频使用的 KV block 下放到更便宜的存储层；
- 在需要时把冷数据重新拉回到 GPU；
- 支持 petabyte 级别跨 GPU / 节点 / 集群的 KV cache。

它同时支持 PyTorch、SGLang、TensorRT-LLM、vLLM，并能利用 NVLink、Quantum InfiniBand、Spectrum Ethernet 等网络硬件。

### 4.5 NVIDIA Inference Transfer Library（NIXL）
![[Pasted image 20260804175637.png]]

NIXL 是支撑上述所有跨节点数据移动的通信库。它被描述为“high-throughput, low-latency point-to-point communication library”。

核心能力：

- **统一 API**：屏蔽底层异构存储差异；
- **非阻塞、非连续传输**：适合 KV cache 这种大块但不连续的数据；
- **多端点支持**：HBM、DRAM、本地 SSD、网络存储（S3 等）；
- **多网络后端**：NVLink（C2C / NVSwitch）、InfiniBand、RoCE、Ethernet；
- **通用 memory section 抽象**：把不同介质上的内存区域统一成可传输的 section。

NIXL 向上对接 Dynamo 的 KV Cache Manager 和 PD 分离中的 KV 跨节点搬运，向下对接 GPUDirect Storage、UCX、S3 等具体后端。

## 五、关键创新点总结

博客把 Dynamo 的创新归纳为五点：

1. Disaggregated prefill and decode inference stages
2. Dynamic scheduling of GPUs based on demand
3. LLM-aware request routing to avoid KV-cache recomputation
4. Accelerated asynchronous data transfer between GPUs
5. KV cache offloading across different memory hierarchies

这五点是相互咬合的：PD 分离产生跨阶段传输需求 → NIXL 解决传输 → Smart Router 减少重算 → KV Cache Manager 扩大缓存容量 → Planner 动态平衡资源。

## 六、与团队迁移工作的关联

这篇博客里提到的很多概念和我们团队正在做的 [[Kong 网关退场与 NVIDIA Dynamo 迁移]] 高度相关：

- **Phase1 的动态路由 + 四层 KV Cache**：对应 Dynamo 的 Smart Router + Distributed KV Cache Manager。
- **Phase2 的 SGLang PD 分离 + RDMA 网络解耦**：对应 Dynamo 的 Disaggregated Serving + NIXL 跨节点传输。
- **Kong 双写双跑过渡**：和 NVIDIA 对 Triton 的向后兼容策略类似，都是先并行再切换。

可以重点关注 Smart Router 的 Radix Tree 实现、NIXL 的 memory section 抽象，以及 Planner 的 SLO 驱动调度策略，这些很可能在后续 Dynamo 落地时需要对照实现或调参。

## 七、术语表

- **TEP / PP / DP**：Tensor Parallelism Expert Parallelism / Pipeline Parallelism / Data Parallelism。
- **ISL / OSL**：Input Sequence Length / Output Sequence Length。
- **TTFT**：Time-To-First-Token，从请求发出到第一个输出 token 返回的延迟。
- **ITL**：Inter-Token Latency，相邻两个输出 token 之间的延迟。
- **Inflight Batching**：在 batch 执行过程中动态替换已完成的请求，提高 GPU 利用率。
- **Radix Tree**：一种压缩前缀树，常用于前缀匹配和缓存索引。
- **NIXL**：NVIDIA Inference Transfer Library，Dynamo 的底层数据传输库。

## 八、下一步可以深挖的点

1. Dynamo GitHub 仓库的代码结构：Planner / Smart Router / KV Cache Manager / NIXL 分别对应哪些目录？
2. Smart Router 的 Radix Tree 集群一致性如何维护？缓存副本策略是什么？
3. NIXL 与现有 RDMA/UCX 的关系：它是在 UCX 之上做封装，还是完全独立实现？
4. Dynamo 与 vLLM 的 prefix caching 在实现上能否直接复用或借鉴？
5. 在昇腾 / 平头哥自研 PPU 环境下，NIXL 的哪些设计思想可以迁移？
