---
tags:
  - CS336
  - Triton
  - CUDA
  - kernels
  - optimization
  - FlashAttention
lecture: L6
aliases:
  - Triton编程
  - GPU Kernel
---

### GPU 硬件规格对比

|   |   |   |   |
|---|---|---|---|
|指标|A100|H100|B200|
|SM 数量|108|132|148|
|Register（每 SM）|256 KB|256 KB|256 KB|
|L1 + Shared Memory（每 SM）|192 KB|256 KB|256 KB|
|L2 Cache|40 MB|50 MB|96-126 MB|
|HBM 容量|80 GB|80 GB|192 GB|
|Register 带宽|~116 TB/s|~401 TB/s|~447 TB/s|
|L1 + Shared 带宽|~19 TB/s|~33 TB/s|~19 TB/s|
|L2 带宽|~5-8 TB/s|~12 TB/s|~9 TB/s|
|HBM 带宽|2 TB/s|3.35 TB/s|8 TB/s|

B200 还有 Tensor Memory（TMEM），位于寄存器和 Shared Memory 之间，供 Tensor Core 使用，对程序员不可见。

**Bank Conflicts（共享内存冲突）：** Shared Memory 被分成 32 个 bank，每个 4 字节宽。每个周期每个 bank 只能被一个线程访问。如果同一 Warp 中多个线程访问同一 bank（且不是同一地址），访问会被串行化，造成性能损失。典型场景：矩阵乘法时访问 A 的行和 B 的列。解决方案是 swizzling（如 row XOR col）重排 Shared Memory 布局来避免冲突。

**Block Occupancy（Block 占用率）：** Thread Block 按 wave 调度到 SM 上。比如 B200 有 148 个 SM，如果启动 160 个 block，第一 wave 148 个，第二 wave 只有 12 个，剩余 SM 空闲。解决方案：让 block 数量能被 SM 数量整除。

### Benchmarking 与 Profiling

**Benchmarking** 衡量操作的端到端耗时，用于比较不同实现和理解性能随规模的变化规律。要点：warmup 后再测（避免编译等开销）、用 CUDA events 精确计时（避免 CPU 开销）、torch.cuda.synchronize() 确保 GPU 计算完成。

**Profiling** 定位时间花在了哪里——具体调用了哪些 CUDA kernel、各占多少时间。用 torch.profiler 可以查看。从 kernel 名称能读出实现细节，比如 cutlass3x_sm100_simt_sgemm_f32_64x64x16 表示：cutlass 库、Blackwell 架构（sm100）、float32、tile 大小 64×64×16。

### 算子融合实例：GeLU 的三种实现

**Naive 实现（无融合，最慢）：**

```
def naive_gelu(x):
    # 每一步都是一个独立的 PyTorch 算子，各自产生一个 CUDA kernel
    # 每步都要从 HBM 读、计算、写回 HBM → 大量冗余的显存读写
    return 0.5 * x * (1 + torch.tanh(0.79788456 * (x + 0.044715 * x * x * x)))
```

这条表达式被拆成了多步：x³ → 乘系数 → 加 x → 乘系数 → tanh → 加1 → 乘 x → 乘0.5。每步中间结果都写回 HBM，下一步再从 HBM 读回来。profiling 会看到多个 CUDA kernel。

**Builtin 实现（融合，快）：**

```
def builtin_gelu(x):
    return torch.nn.functional.gelu(x, approximate="tanh")
```

PyTorch 内置实现会将整个计算融合到一个 CUDA kernel 中，只从 HBM 读一次 x，写回一次结果。

**Compiled 实现（自动融合，和 builtin 一样快）：**

```
compiled_gelu = torch.compile(naive_gelu)  # PyTorch 编译器自动识别可融合的算子
y = compiled_gelu(x)
```

torch.compile 会将 naive_gelu 中的多个算子自动融合成一个 kernel（实际上编译后是一个 Triton kernel），性能与 builtin 相当，且不需要手动写融合代码。

profiling 对比：naive 版本调用多个 CUDA kernel，builtin 和 compiled 版本只有一个 kernel。

### Triton 入门

CUDA 是 NVIDIA 开发的，以 thread 为单位编程，需要手动管理 Shared Memory、同步等细节，控制粒度细但开发成本高。

Triton 是 OpenAI 开发的，以 thread block 为单位编程。核心理念：从 HBM 加载数据到 Shared Memory → 在 Shared Memory 中做计算（可以融合多个算子）→ 写回 HBM。**编译器自动处理 tiling、Shared Memory 分配、内存合并等底层细节。**

Triton 编译到 PTX（GPU 汇编语言），可以直接查看生成的代码。

### Triton 实例

#### 1. GeLU（Element-wise 操作）

```
def triton_gelu(x):
    assert x.is_cuda and x.is_contiguous()
    y = torch.empty_like(x)

    # 把全部元素分成多个 block，每个 block 处理 BLOCK_SIZE 个元素
    # | T T T T T T T T | T T T T T T T T | T T T T T T T T | ...
    # |    Block 0      |    Block 1      |    Block 2      | ...
    num_elements = x.numel()
    BLOCK_SIZE = 1024
    num_blocks = triton.cdiv(num_elements, BLOCK_SIZE)  # 向上取整

    # 启动 kernel：grid 是一维的 (num_blocks,)
    triton_gelu_kernel[(num_blocks,)](x, y, num_elements, BLOCK_SIZE=BLOCK_SIZE)
    return y

@triton.jit
def triton_gelu_kernel(x_ptr, y_ptr, num_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)       # 当前是第几个 block
    start = pid * BLOCK_SIZE          # 这个 block 负责的数据起始位置
    offsets = start + tl.arange(0, BLOCK_SIZE)  # 这个 block 内所有线程的偏移量
    mask = offsets < num_elements     # 最后一个 block 可能越界，用 mask 保护

    # 从 HBM 加载到 Shared Memory（编译器自动处理）
    x = tl.load(x_ptr + offsets, mask=mask)

    # 计算 GeLU（tanh 近似）—— 全部在寄存器/Shared Memory 中完成，不写中间结果
    # 公式: 0.5 * x * (1 + tanh(sqrt(2/pi) * (x + 0.044715 * x^3)))
    a = 0.79788456 * (x + 0.044715 * x * x * x)
    exp = tl.exp(2 * a)
    tanh = (exp - 1) / (exp + 1)  # tl 没有 tanh，用 exp 手动实现
    y = 0.5 * x * (1 + tanh)

    # 写回 HBM
    tl.store(y_ptr + offsets, y, mask=mask)
```

要点：这是最简单的 Triton kernel 模式——load → element-wise 计算 → store。所有中间运算都在寄存器中完成，没有额外的 HBM 读写，这就是算子融合的效果。PTX 中可以看到 thread coarsening——编译器让每个线程同时处理 8 个元素。

#### 2. Softmax（Reduction，行能放进一个 Block）

```
# Naive softmax —— 对比用，可以看到有多少冗余读写
def naive_softmax(x):
    M, N = x.shape
    x_max = x.max(dim=1)[0]           # MN 读 + M 写
    x = x - x_max[:, None]            # MN+M 读 + MN 写
    numerator = torch.exp(x)          # MN 读 + MN 写
    denominator = numerator.sum(dim=1) # MN 读 + M 写
    y = numerator / denominator[:, None] # MN 读 + MN 写
    # 总计: 5MN+M 读, 3MN+2M 写
    return y

# Triton softmax
def triton_softmax(x):
    y = torch.empty_like(x)
    M, N = x.shape
    block_size = triton.next_power_of_2(N)  # block 大小取 N 的下一个 2 的幂
    num_blocks = M                           # 每个 block 处理一行

    triton_softmax_kernel[(M,)](
        x_ptr=x, y_ptr=y,
        x_row_stride=x.stride(0), y_row_stride=y.stride(0),
        num_cols=N, BLOCK_SIZE=block_size
    )
    return y

@triton.jit
def triton_softmax_kernel(x_ptr, y_ptr, x_row_stride, y_row_stride,
                          num_cols, BLOCK_SIZE: tl.constexpr):
    row_idx = tl.program_id(0)  # 当前处理第几行
    col_offsets = tl.arange(0, BLOCK_SIZE)

    # 读：一次把整行从 HBM 加载到 Shared Memory
    x_start_ptr = x_ptr + row_idx * x_row_stride
    x_row = tl.load(x_start_ptr + col_offsets,
                    mask=col_offsets < num_cols, other=float("-inf"))

    # 算：所有 reduction 操作都在 Shared Memory 中完成
    x_row = x_row - tl.max(x_row, axis=0)  # 减 max（数值稳定）
    numerator = tl.exp(x_row)               # exp
    denominator = tl.sum(numerator, axis=0) # sum → 标量
    y_row = numerator / denominator         # 归一化

    # 写：一次写回 HBM
    y_start_ptr = y_ptr + row_idx * y_row_stride
    tl.store(y_start_ptr + col_offsets, y_row, mask=col_offsets < num_cols)
```

要点：每行独立由一个 block 处理。因为整行能放进一个 block（N ≤ BLOCK_SIZE），所有 reduction（max、sum）都由 Triton 在 Shared Memory 内自动完成。对比 naive 的 5MN+M 读 + 3MN+2M 写，Triton 只需 MN 读 + MN 写，理论加速约 4 倍。stride 参数用于处理矩阵在内存中的线性布局——PyTorch 中矩阵按行存储，stride(0) 是跨一行的步长。

#### 3. Row Sum（Reduction，行放不进 Block）

```
def triton_row_sum(x, BLOCK_SIZE=1024):
    M, N = x.shape
    y = torch.empty(M, device=x.device, dtype=x.dtype)
    row_sum_kernel[(M,)](x, y, N, BLOCK_SIZE=BLOCK_SIZE)
    return y

@triton.jit
def row_sum_kernel(x_ptr, out_ptr, N, BLOCK_SIZE: tl.constexpr):
    row = tl.program_id(0)  # 当前处理第几行

    # 每个线程维护一个 accumulator（初始化为 0）
    # 一行: T1 T2 T3 T4 | T1 T2 T3 T4 | T1 T2 T3 T4 (N=12, BLOCK_SIZE=4)
    acc = tl.zeros([BLOCK_SIZE], dtype=tl.float32)

    # 循环遍历所有 tile，累加到 accumulator
    for start in range(0, N, BLOCK_SIZE):
        cols = start + tl.arange(0, BLOCK_SIZE)
        mask = cols < N
        x = tl.load(x_ptr + row * N + cols, mask=mask, other=0.0)
        acc += x  # 在 Shared Memory 中累加

    # 所有 tile 处理完后，对 accumulator 做一次 reduction 得到标量
    result = tl.sum(acc, axis=0)

    tl.store(out_ptr + row, result)
```

要点：当列数 N 超过 BLOCK_SIZE 时（如 N=4096, BLOCK_SIZE=1024），一行无法放进一个 block。策略是把一行分成多个 tile，循环加载每个 tile 并累加到 accumulator，最后对 accumulator 做一次 reduction。这是 tiling 思想的简化版——和 softmax 的区别在于需要跨 tile 累积中间结果。

#### 4. Matmul + ReLU（Tiling，使用 Shared Memory）

```
def triton_matmul_relu(a, b):
    assert a.is_cuda and b.is_cuda
    assert a.is_contiguous() and b.is_contiguous()
    M, K = a.shape
    K, N = b.shape
    c = torch.empty((M, N), device=a.device)

    # Tile 大小：output tile 64×64，K 维度每次加载 32
    BLOCK_M, BLOCK_N, BLOCK_K = 64, 64, 32
    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))

    matmul_relu_kernel[grid](
        a, b, c, M, N, K,
        a.stride(0), a.stride(1), b.stride(0), b.stride(1),
        c.stride(0), c.stride(1),
        BLOCK_M, BLOCK_N, BLOCK_K,
    )
    return c

@triton.jit
def matmul_relu_kernel(
    a_ptr, b_ptr, c_ptr,
    M, N, K,
    stride_am, stride_ak, stride_bk, stride_bn, stride_cm, stride_cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    # 当前 block 负责 C 矩阵中第 (pid_m, pid_n) 个 output tile
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    # 构造索引：这个 tile 覆盖的行/列/K 范围
    indices_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)  # [BLOCK_M] 行索引
    indices_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)  # [BLOCK_N] 列索引
    indices_k = tl.arange(0, BLOCK_K)                     # [BLOCK_K] K 维度索引

    # 构造 A 和 B tile 的指针矩阵
    # a_ptrs: [BLOCK_M, BLOCK_K] — A 的一个 row tile
    # b_ptrs: [BLOCK_K, BLOCK_N] — B 的一个 column tile
    a_ptrs = a_ptr + indices_m[:, None] * stride_am + indices_k[None, :] * stride_ak
    b_ptrs = b_ptr + indices_k[:, None] * stride_bk + indices_n[None, :] * stride_bn

    acc = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)

    # 核心循环：沿 K 维度遍历所有 tile pair
    for k in range(0, K, BLOCK_K):
        # 从 HBM 加载 A tile [BLOCK_M, BLOCK_K] 和 B tile [BLOCK_K, BLOCK_N] 到 Shared Memory
        a = tl.load(a_ptrs,
                    mask=(indices_m[:, None] < M) & (indices_k[None, :] + k < K),
                    other=0.0)
        b = tl.load(b_ptrs,
                    mask=(indices_k[:, None] + k < K) & (indices_n[None, :] < N),
                    other=0.0)

        # 在 Shared Memory 中做小块矩阵乘，累加到 acc
        acc += tl.dot(a, b)

        # 指针前进到下一个 K tile
        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk

    # 算子融合：K 维遍历完后，直接在结果上做 ReLU，不需要额外写回再读
    acc = tl.maximum(acc, 0.0)

    # 写回 HBM
    c_ptrs = c_ptr + indices_m[:, None] * stride_cm + indices_n[None, :] * stride_cn
    tl.store(c_ptrs, acc,
             mask=(indices_m[:, None] < M) & (indices_n[None, :] < N))
```

要点：这是最复杂的 kernel，体现了 tiling + 算子融合的完整思路。Grid 是二维的，每个 block 负责 C 中一个 64×64 的 output tile。对每个 output tile，沿 K 维度循环：每次加载 A 的 64×32 tile 和 B 的 32×64 tile 到 Shared Memory，用 tl.dot 做小块矩阵乘并累加。K 维遍历完后，acc 中就是完整的 output tile，直接做 ReLU（算子融合）再写回。

stride 的作用：PyTorch 中矩阵按行线性存储，x[i, j] 的内存地址 = base + i * stride(0) + j * stride(1)。对 contiguous 矩阵 stride = (N, 1)，但 stride 参数让 kernel 能处理非连续的情况。

算术强度：naive matmul 每算一个元素都要从 HBM 读写，算术强度 O(1)；tiling 后每个 tile 从 HBM 加载一次就反复使用，算术强度提升到 O(tile_size)。

---

## 相关链接

- GPU 硬件基础（SM、存储层级）：[[CS336-L5-GPUs-TPUs]]
- 多 GPU 并行（通信原语）：[[CS336-L7-Parallelism-1]]
- 算术强度在推理中的应用：[[CS336-L10-Inference]]
- 课程进度：[[课程进度]]