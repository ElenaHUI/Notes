**核心主题**：编排计算以避免数据传输瓶颈。上周（单 GPU）通过 fusion/tiling 减少内存访问；本周（多 GPU）通过 replication/sharding 减少跨 GPU/节点通信。

**为什么要多 GPU**：(1) 参数（optimizer state + gradients + activations）单卡放不下；(2) 想用更多 FLOPs 加速训练。

---

### Part 1: Building Blocks of Distributed Communication/Computation

#### 存储/互联层级（从快到慢）

|   |   |   |
|---|---|---|
|层级|介质|带宽|
|单 GPU 内|L1 cache / shared memory|最快|
|单 GPU 内|HBM|~8 TB/s|
|同节点多 GPU|NVLink / NVSwitch (NVLink 5.0, B200)|1.8 TB/s|
|跨节点（同 pod）|Infiniband (PCIe → HCA/NIC → cable)|~0.05 TB/s|
|跨 pod / 数据中心|Ethernet (PCIe → CPU)|~200 MB/s|

经典家用场景：同节点 GPU 走 PCIe 总线（v7.0 x16 → 242 GB/s），跨节点走 Ethernet。

现代数据中心典型配置：8 GPU/node（NVLink + NVSwitch）→ 256 nodes/pod（Infiniband）→ N pods/cluster（Ethernet）。GB200/GB300 NVL72 把 9 个 tray × 8 GPU = 72 GPU 放进一个 NVLink domain。

#### RDMA（绕过 CPU）

传统 Ethernet 通信需经过 CPU（拷贝到 kernel socket buffer → 构建 TCP 包 → 拷贝到 NIC ring buffer）。RDMA 允许一个 GPU 直接读写另一个 GPU 的显存，不经过 CPU。Infiniband 原生支持 RDMA；标准 Ethernet 不支持，但 RoCE（RDMA over Converged Ethernet）可以在 Ethernet 上实现类似能力（Meta 在用），比 Infiniband 便宜但稍弱。

#### 集合通信原语 (Collective Operations)

源自 1980s 并行编程文献。"Collective" 意为指定跨多设备的通用通信模式，比手动管理点对点通信更高效。

基本术语：Rank = 一个设备/GPU；World size = 设备总数。

**基础操作：**

- Broadcast：rank 0 → 所有 rank（用途：rank 0 加载 checkpoint 后广播）
- Scatter：rank 0 的张量切分分发到各 rank
- Gather：各 rank 的数据收集到 rank 0（Scatter 的逆）
- Reduce：各 rank 数据做归约运算（sum/min/max）到 rank 0

**核心工作操作（workhorse）：**

- AllGather：Gather 到所有 rank（用途：每个 rank 持有参数分片，gather 得到完整参数做 forward）
- ReduceScatter：对每个维度做 reduce，再 scatter 结果到各 rank（用途：backward 后汇总梯度但分散存储）
- AllReduce = ReduceScatter + AllGather（用途：backward 后汇总梯度且所有 rank 保持完整参数副本）

将 AllReduce 拆解为 ReduceScatter + AllGather 提供了灵活性（如 ZeRO/FSDP 只存部分参数）。

- AllToAll：每个 rank 向每个其他 rank 发送不同数据块（最通用的操作）。用途：MoE 中各 rank 持有不同 expert，需要路由数据。对均衡切分来说，AllToAll 等价于 transpose。

**记忆口诀**：Reduce = 做结合/交换运算；Scatter 是 Gather 的逆；All = 目标是所有设备。

#### NCCL（NVIDIA Collective Communications Library）

将集合通信原语翻译为 GPU 间的底层数据包。功能：检测硬件拓扑（节点数、交换机、NVLink/PCIe）→ 优化 GPU 间路径 → 启动 GPU kernel 收发数据。

#### PyTorch Distributed (torch.distributed)

- 提供集合通信的干净接口（all_reduce, reduce_scatter_tensor, all_gather_into_tensor 等）
- 多后端：gloo（CPU）、nccl（GPU）
- 同步语义：dist.barrier()（等所有进程到达同一点）、async_op 参数控制同步/异步
- 更高层封装：FullyShardedDataParallel（本课程未使用）

#### 通信带宽 Benchmark

AllReduce 有效带宽计算：sent_bytes = size_bytes × 2 × (world_size - 1)（2x 因为 send + receive），bandwidth = sent_bytes / (world_size × duration)。结论：有效带宽与 world_size 无关，与拓扑（ring/tree）无关。

ReduceScatter 无 2x 因子。AllReduce 比 ReduceScatter 多传 2x 数据、多花 2x 时间，所以测出的带宽相近。

---

### Part 2: Distributed Training（三种并行策略）

用 bare-bones MLP 实现演示（MLP 是 Transformer 的计算瓶颈，具有代表性）。

#### Data Parallelism（数据并行）— 沿 batch 维度切

每个 rank 持有完整模型副本，各自处理 batch 的不同 slice。流程：local forward → local backward → dist.all_reduce(param.grad, op=AVG) 同步梯度 → optimizer.step()。

关键性质：各 rank 的 loss 不同（因为数据不同），但梯度 all-reduce 后相同，因此参数始终保持一致。

进阶：FSDP/ZeRO 用 AllGather + ReduceScatter 替代 AllReduce，避免每个 rank 都存全部参数。

#### Tensor Parallelism（张量并行）— 沿 width 维度切

每个 rank 持有每层参数的 1/world_size（切 num_dim 维度）。所有 rank 拿到完整输入数据。每层计算后通过 dist.all_gather 收集各 rank 的 partial activations，concatenate 得到完整 activation 再送入下一层。

特点：每层都需要通信，因此要求极快互联（NVLink 级别）。

#### Pipeline Parallelism（流水线并行）— 沿 depth 维度切

每个 rank 持有部分 layers。将 batch 切成 micro-batches 以最小化 pipeline bubble。rank 间用点对点通信（dist.send / dist.recv）传递 activations。

特点：可以容忍较慢的互联（只在相邻 stage 间通信），但需要处理 pipeline bubble（本课未涉及 communication/computation overlap）。

#### 总结与权衡

- 并行方式：data (batch)、tensor/expert (width)、pipeline (depth)、sequence (length)
- DDP 用 AllReduce；FSDP/ZeRO 用 AllGather + ReduceScatter
- Tensor parallelism 需要极快互联（NVLink）；Pipeline parallelism 可用慢互联但要减少 bubble
- 核心权衡三角：re-compute（重算）vs store in memory（存显存）vs communicate（存别的 GPU 再传过来）
- 硬件在变快，但模型总会更大 → 层级结构会一直存在