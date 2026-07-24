### GPU 硬件架构

以 NVIDIA A100 为例，一块 GPU 包含 128 个 SM（Streaming Multiprocessor）。SM 是 GPU 的核心计算单元，内部包含 CUDA 计算核心、Warp Scheduler、Register File、Shared Memory 等。

存储层级从快到慢：

- Register File（寄存器堆）：在 SM 内部，最快，每个线程私有
- L1 Cache / Shared Memory：在 SM 内部，速度极快，容量小（128~192KB，可配置比例）。Shared Memory 供同一 Block 内的线程共享通信
- L2 Cache：在 GPU die 上，所有 SM 共享，容量较大
- Global Memory（HBM/DRAM）：显存，容量大但速度慢得多。GPU 计算瓶颈往往不在算力而在显存带宽

### 执行模型

GPU 的执行按 Grid → Block → Warp → Thread 四层组织：

Grid：一次 kernel 启动生成一个 Grid，包含若干 Block。可以是一维、二维或三维排列。

Block：一个 Block 最多 1024 个线程，会被调度到同一个 SM 上执行。Block 内的线程可以通过 Shared Memory 互相通信和同步（__syncthreads）。Block 数量没有硬件上限（实际上受 SM 数量限制）。

Warp（线程束）：Block 内的线程每 32 个自动组成一个 Warp。Warp 是 GPU 调度和执行的真正最小单位——同一 Warp 的 32 个线程在同一时钟周期执行同一条指令（SIMT 模型）。

Thread（线程）：最小的执行单元，每个线程有自己的寄存器和局部变量，通过 threadIdx 标识身份。

一个 Block 最多 32 × 32 = 1024 个线程，即最多 32 个 Warp。

### 优化策略

#### 1. 减少 Control Divergence

当 Warp 中遇到 if 语句且线程走了不同分支时，GPU 必须串行执行两个分支（先执行 if 分支，等走 if 的线程算完，再执行 else 分支让其余线程算），造成严重的性能浪费。优化方法：尽量少写 if 语句，或用算术运算替代条件分支。

#### 2. 低精度计算 — MXFP8

MXFP8（Microscaling FP8）是 OCP 提出的 MX 系列低精度格式，核心思路是在 8 bit 存储空间内结合块级缩放（Block Scaling）机制来更灵活地表示数据。

MXFP8 包含两种子格式：E4M3（4 位指数 + 3 位尾数，精度更高，适合权重）和 E5M2（5 位指数 + 2 位尾数，动态范围更大，适合梯度和激活值）。

与标准 FP8 的区别：标准 FP8 是"一刀切"的，选定格式后所有数据统一使用。MXFP8 把数据分块（通常 32 个元素一组），每组共享一个缩放因子（scale），并可根据数据分布动态选择子格式。量化误差比固定格式 FP8 低 20%~40%，不需要提前手动校准量化参数。

NVIDIA Blackwell 架构（如 B200）已原生支持 MXFP8，能在保持接近 FP16 精度的同时获得接近 2 倍算力提升和更低显存占用。

#### 3. Operator Fusion（算子融合）

将多个连续的小算子（如 LayerNorm + Linear + Activation）融合成一个大算子，减少中间结果写入显存再读回来的次数，核心目标是减少数据搬运（memory traffic），让计算在高速缓存中一气呵成。

#### 4. Recomputation（重计算 / Gradient Checkpointing）

大模型训练中的内存优化技术，用"多算"换"少存"。前向传播时不全存所有中间 activation，只隔一段存一个 checkpoint，中间的 activation 算完就丢弃。反向传播时从最近的 checkpoint 重新算一遍需要的 activation。

好处：显存占用大幅降低（例如每 10 层存一个 checkpoint，显存降至约 1/10），计算量仅增加约 33%。省下的显存可用于增大 batch size，提高 GPU 并行利用率，从而提升整体训练效率。

#### 5. Memory Coalescing（显存合并访问）

DRAM 按固定宽度（如 128 字节）一次读取一整段数据。如果同一 Warp 的 32 个线程访问的是连续内存地址，硬件可以将这 32 次访问合并成一次或少数几次事务（transaction），充分利用总线带宽。反之如果地址分散（strided access），每次访问都要独立发起事务，带宽浪费严重。优化方法：确保线程按连续地址访问全局显存。

#### 6. Tiling（分块计算）

将大矩阵切成小块（tile），让每个 tile 在高速 Shared Memory 中完成计算，减少对慢速全局显存的访问。

以矩阵乘法 C = A × B 为例：将 A 和 B 按 2×2 或更大尺寸切分，每次加载一对 tile 到 Shared Memory，在高速缓存中计算局部乘积并累加，处理完所有 tile 后写回结果。每个 tile 从显存加载一次就反复使用，数据复用率大幅提高，显存带宽压力显著降低。

#### 7. FlashAttention

将 Tiling 思想应用到 Transformer 的 Attention 计算上。标准 Attention 的问题：需要构造完整的 N×N 注意力矩阵并写入显存，序列长度一大就爆显存且读写开销巨大。

FlashAttention 的做法：把 Q、K、V 按 block 切分，每次只在 SRAM（Shared Memory）中计算一小块 attention，用 online softmax 的技巧边算边更新——维护 running max 和 running sum 来逐步修正 softmax 结果，同时累加局部贡献到输出 O。全程不产生 N×N 中间矩阵。

效果：显存从 O(N²) 降到 O(N)，速度大幅提升（省掉了大量 HBM 读写），数值结果与标准 Attention 精确等价（不是近似）。

PyTorch 2.0+ 中 `F.scaled_dot_product_attention` 会自动调用 FlashAttention，flash-attn 库提供更灵活的接口。