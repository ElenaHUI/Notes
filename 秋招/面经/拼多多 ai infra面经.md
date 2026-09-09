---
tags:
  - 面经
  - 拼多多
  - AI-infra
  - PD分离
  - KVCache
  - Mooncake
  - FlashAttention
  - MLA
  - 操作系统
  - 多线程
  - LRU
aliases:
  - 拼多多面经
  - 拼多多 AI Infra 面经
company: 拼多多
position: AI Infra
date: 2026-09-07
---

# 拼多多 AI Infra 面经

> **面试时间**：待补充
> **项目简介（开场标准答案）**：见 [[秋招/面经/PTG项目简介|PTG项目简介]]
> **关联**：[[秋招/面经/快手 AI infra面经|快手 AI Infra]] · [[秋招/面经/PTG项目简介|PTG项目简介]] · [[kimi2.6 PD分离部署记录]]

> [!tip] 这场面试的判读（先看这段）
> 问题分布很说明岗位画像：**项目/推理链路 12 问（深）+ 计算机基础 7 问（OS + 编码 + 手撕）**。
> - 项目部分**一路往"定量分析"钻**：PD 配比 → KV Cache 大小手推 → RDMA 传输延迟 → TTFT 是否变差。这类岗非常看重**从模型参数推算资源需求**的能力（Q5/Q6 未答出是最明显的失分点）。
> - **Mooncake / NVSHMEM / FA3 / MLA** 这几问考的是推理栈的**知识广度与深度**，答不出会显得只停留在"调参"层面。
> - 基础部分从 **Python 分配内存**顺势追到**虚拟内存 / 页表 / MMU / TLB**，是一条完整的 OS 内存链路，答得不错。
> - 手撕两道（交替打印 + LRU），考**多线程同步**和**哈希表 + 双向链表**的组合数据结构。

---

## 原始题目清单（面试官的顺序）

| # | 板块 | 题目 | 跳转 |
| --- | --- | --- | --- |
| 1 | 开场 | 自我介绍 + 简历项目 | [[#1. 请简单做个自我介绍，说一下简历上的项目\|Q1]] |
| 2 | 项目 | 平头哥项目具体做了什么 | [[#2. 具体说一下在平头哥的项目\|Q2]] |
| 3 | 硬件 | PPU（810E）分层存储结构，从近到远 | [[#3. PPU（810E）的分层存储结构，从近到远\|Q3]] |
| 4 | PD分离 | P/D 卡型号一样，为什么做 3:2 分离 | [[#4. P节点和D节点卡型号一样，为什么做3:2的PD分离？\|Q4]] |
| 5 | 定量 | Kimi K2.6 / 80K / W4A8 下 KV Cache 传输量 | [[#5. Kimi K2.6模型，80K上下文，W4A8场景下，KV Cache传输量是多少？\|Q5]] |
| 6 | 定量 | 80K KV Cache 用 Mooncake+RDMA 传输延迟 | [[#6. 80K的KV Cache用Mooncake+RDMA传输，延迟大概多少毫秒？\|Q6]] |
| 7 | PD分离 | PD 分离的核心目的是提升什么指标 | [[#7. PD分离的核心目的是提升什么指标？\|Q7]] |
| 8 | PD分离 | 做了 PD 分离后 TTFT 会不会更差 | [[#8. 做了PD分离后TTFT有没有可能反而更差？\|Q8]] |
| 9 | 传输 | Mooncake 是什么 | [[#9. Mooncake是什么？\|Q9]] |
| 10 | 传输 | Mooncake 和 NVSHMEM 对比 | [[#10. Mooncake和NSRL/NVSHMEM对比\|Q10]] |
| 11 | Kernel | FA3 兼容问题 / FA3 与 FA2 区别 | [[#11. FA3的兼容问题是什么？怎么解决的？FA3和FA2的区别？\|Q11]] |
| 12 | 架构 | 不同模型 KV Cache 占用是否一样 / MLA 是什么 | [[#12. 不同模型在相同上下文长度下KV Cache占用量一样吗？MLA是什么？\|Q12]] |
| 13 | 编码 | Python 一行代码分配 10GB 内存 | [[#13. 用Python一行代码分配10GB内存\|Q13]] |
| 14 | 操作系统 | 从 Python 到 OS 到硬件，分配内存背后发生了什么 | [[#14. 从Python层到操作系统层到硬件层，分配内存背后发生了什么？\|Q14]] |
| 15 | 操作系统 | 变量 a 是逻辑地址还是物理地址 | [[#15. 变量a是逻辑地址还是物理地址？\|Q15]] |
| 16 | 操作系统 | 逻辑地址和物理地址通过什么映射 | [[#16. 逻辑地址和物理地址通过什么映射？\|Q16]] |
| 17 | 操作系统 | 页表是怎样的结构？存在哪里 | [[#17. 页表是怎样的结构？存在哪里？\|Q17]] |
| 18 | 多线程 | 两个线程交替打印 0-99（奇偶分离） | [[#18. 用两个线程交替打印0-99（奇偶分离）\|Q18]] |
| 19 | 手撕 | Python 实现 LRU Cache（get + put） | [[#19. 用Python实现LRU Cache（get + put）\|Q19]] |

---

## 一、项目相关

### 1. 请简单做个自我介绍，说一下简历上的项目

**你的回答：** 华东师范大学软件工程研究生，研究边缘计算+强化学习，本科西电，实习做大模型部署、量化压缩等。

**参考答案：** 自我介绍属于个人内容，你的回答没有问题。建议结构更紧凑：**背景→研究方向→核心技能→与岗位的匹配点**，最后一句话点明"所以我对XX岗位很感兴趣"做收束。

---

### 2. 具体说一下在平头哥的项目

**你的回答：** 部门为集团内部提供大模型API，使用810E部署Deepseek、Kimi等模型，负责全链路。

**参考答案：** 回答方向正确。建议补充**量化数据**让回答更有说服力，例如：部署了多少个模型、服务了多少QPS、优化后性能提升了多少百分比。用"背景→挑战→你做了什么→结果"的STAR结构组织。

> [!info] 报数速查（详见 [[秋招/面经/PTG项目简介]]）
> 平台总量 **21 机 / 336 卡、13 个模型、利用率 100%**；Kimi-K2.6 单模型 **3P2D = 48P + 32D = 80 卡**；SLA **TTFT P99 < 2~3s、TPOT < 50~60ms**；平均 input **80K+ tokens**。

---

### 3. PPU（810E）的分层存储结构，从近到远

**你的回答：** 寄存器 → Shared Memory → HBM（96GB）→ CPU侧存储。

**参考答案：** 你的回答基本正确。更完整的层次：

| 层级 | 存储介质 | 容量量级 | 带宽 | 延迟 |
|------|---------|---------|------|------|
| L0 | **寄存器（Register File）** | KB级 | 最高 | ~1 cycle |
| L1 | **Shared Memory / L1 Cache**（片上SRAM） | 几十~几百KB/SM | TB/s级 | 几~十几 cycle |
| L2 | **L2 Cache**（片上共享） | MB级 | TB/s级 | 几十 cycle |
| L3 | **HBM（显存）** | 96GB（810E） | ~2-4 TB/s | 百 cycle级 |
| L4 | **Host Memory（CPU DRAM）** | 几百GB~TB | PCIe带宽，几十GB/s | 微秒级 |
| L5 | **NVMe SSD / 远端节点** | TB级 | GB/s~网络带宽 | 毫秒级 |

你漏掉了**L2 Cache**这一层。另外建议提到每一层的**带宽和延迟数量级**，这样能体现你对性能优化的直觉。

---

### 4. P节点和D节点卡型号一样，为什么做3:2的PD分离？

**你的回答：** 资源充沛，先整机部署再PD分离，根据压测调配比。上下文最长约80K。

**参考答案：** 你的回答说了"怎么调"，但没说清"为什么是3:2"。更好的回答：

> PD分离的配比取决于**Prefill和Decode的算力需求比**。Prefill是compute-bound，处理长上下文时单次计算量大但请求频次相对低；Decode是memory-bound，每次只算一个token但需要持续服务所有并发请求。
>
> 3P:2D意味着我们的场景中**Prefill的算力需求更大**——因为Agent场景上下文长（~80K），Prefill计算量与序列长度成平方关系（Self-Attention），而Decode每步计算量固定。具体配比通过监控**P卡的计算利用率**和**D卡的显存带宽利用率**来调整，目标是两端都不成为瓶颈。

> [!info] 配比调优四步法（详见 [[秋招/面经/快手 AI infra面经|快手面经 Q5]]）
> 理论估算定方向 → 阶梯压测找瓶颈侧 → SLA 硬约束下取成本最优档 → 上线后用"并发–TPOT 正相关曲线"反推 bound line（并发 30 时 TPOT 升到 60ms）。

---

### 5. Kimi K2.6模型，80K上下文，W4A8场景下，KV Cache传输量是多少？

**你的回答：** 未能回答。

**参考答案：** 手推过程如下（以典型MHA架构为例）：

```
KV Cache大小 = 2 × num_layers × seq_len × num_kv_heads × head_dim × bytes_per_element
```

Kimi K2.6的典型参数（假设类似Llama-70B级别）：
- `num_layers` = 80
- `num_kv_heads` = 8（GQA，8个KV头）
- `head_dim` = 128
- `seq_len` = 80,000
- W4A8场景下，KV Cache一般用FP8或INT8存储 → `bytes_per_element` = 1

```
= 2 × 80 × 80000 × 8 × 128 × 1 byte
= 2 × 80 × 80000 × 1024 byte
= 2 × 80 × 80000 × 1 KB
= 12,800,000 KB
≈ 12.2 GB
```

如果KV Cache是FP16（2 bytes）则翻倍约24.4GB。如果模型用了**MLA**（如Deepseek）或**MQA**，KV头数更少，传输量会大幅减小。

**关键点：** 面试官考察的不是精确数字，而是你能否**建立起从模型参数到KV Cache大小的推算链路**。即使不记得具体模型参数，也要能写出公式并说明哪些因素影响传输量。

---

### 6. 80K的KV Cache用Mooncake+RDMA传输，延迟大概多少毫秒？

**你的回答：** 未能回答，表示主要看TTFT和TPOT。

**参考答案：**

> 假设KV Cache约12GB（上题结果），使用RDMA传输：
>
> - 单机内NVLink带宽：~900 GB/s → 12GB / 900 ≈ **13ms**
> - 跨机RDMA（200Gbps = 25GB/s）→ 12GB / 25 ≈ **480ms**
> - 跨机RDMA（400Gbps = 50GB/s）→ 12GB / 50 ≈ **240ms**
>
> 实际还要加上连接建立、协议开销、分块传输的调度开销，通常额外增加几十ms。所以跨机场景下80K上下文的KV传输延迟大约在**几百毫秒**量级。
>
> 这就是为什么KV Cache传输是PD分离的核心瓶颈——几百毫秒的传输延迟直接叠加到TTFT上。

---

### 7. PD分离的核心目的是提升什么指标？

**你的回答：** Prefill是compute-bound，Decode是memory-bound，瓶颈不同所以分开优化。业务上主要提升TPOT。

**参考答案：** 原理部分正确。但业务指标的回答可以更全面：

> PD分离的核心目的是**同时优化TTFT和TPOT**：
>
> 1. **TPOT提升**（你答对了）：混合部署时Prefill的大量计算会抢占GPU算力，导致正在Decode的请求被阻塞（"Prefill抢占"），TPOT出现毛刺。分离后Decode卡专注逐token生成，TPOT更稳定。
>
> 2. **TTFT提升**：Prefill卡不需要为Decode请求预留显存和算力，可以更激进地做计算（比如更大batch的Prefill），减少排队时间。
>
> 3. **整体吞吐量提升**：两种不同特性的负载分别调优，资源利用率更高。P卡可以追求高计算利用率，D卡可以追求高显存带宽利用率。

---

### 8. 做了PD分离后TTFT有没有可能反而更差？

**你的回答：** 没观测到变差。认为KV Cache延迟高对TTFT应该没有特别大影响。

**参考答案：** **你的回答有误**。PD分离后TTFT可能变差的场景：

> **会变差。** PD分离引入了一个额外步骤：Prefill完成后，KV Cache必须从P节点传输到D节点，D节点收到KV Cache后才能开始Decode第一个token。
>
> ```
> 混合部署：TTFT = Prefill计算时间
> PD分离： TTFT = Prefill计算时间 + KV Cache传输时间 + D节点调度延迟
> ```
>
> 当上下文很长（如80K）时，KV Cache可能达到几GB甚至十几GB，跨机传输需要几百毫秒。这个传输延迟**直接叠加到TTFT上**。
>
> 所以PD分离对TTFT是一把双刃剑：
> - **利**：P卡专注Prefill，减少排队，Prefill计算本身更快
> - **弊**：多了KV传输延迟
>
> 当KV传输延迟 > 排队节省的时间时，TTFT就会变差。这也是为什么Mooncake等KV传输优化如此重要。

---

### 9. Mooncake是什么？

**你的回答：** 帮助KV Cache从GPU直接传到GPU，省去CPU中转，基于RDMA。

**参考答案：** 方向正确，可以更精确：

> Mooncake是月之暗面（Kimi团队）开源的**分布式KV Cache传输与管理框架**，核心能力：
>
> 1. **基于RDMA的GPU-to-GPU零拷贝传输**：绕过CPU，利用GPUDirect RDMA直接在两台机器的GPU显存之间传数据，大幅降低延迟和CPU开销。
>
> 2. **KV Cache的分布式存储池**：不只是传输工具，还管理KV Cache的生命周期——在多个节点间做缓存、复用、淘汰。支持prefix caching（相同前缀的请求复用KV Cache）。
>
> 3. **与推理框架（如vLLM）集成**：作为PD分离场景下P到D之间的"KV Cache搬运层"。
>
> 传统路径：GPU → CPU → 网卡 → 网络 → 网卡 → CPU → GPU（多次内存拷贝）
> Mooncake路径：GPU → RDMA网卡 → 网络 → RDMA网卡 → GPU（零拷贝）

---

### 10. Mooncake和NSRL/NVSHMEM对比

**你的回答：** Mooncake更上层基于RDMA，NSRL是NVIDIA底层直接访问工具，定位类似。

**参考答案：**

> | 维度 | Mooncake | NVSHMEM (NSRL) |
> |------|----------|----------------|
> | **定位** | 面向LLM推理的KV Cache传输框架 | NVIDIA提供的GPU间通信库（类似GPU版MPI） |
> | **抽象层级** | 应用层，封装了KV Cache管理逻辑 | 通信原语层，提供put/get/barrier等接口 |
> | **传输机制** | 底层可用RDMA、NVLink、GPUDirect等 | 底层用NVLink（机内）、InfiniBand RDMA（跨机） |
> | **适用范围** | 专为LLM PD分离场景设计 | 通用GPU通信，HPC/AI均可用 |
> | **编程模型** | 对推理框架暴露高级API | PGAS（Partitioned Global Address Space），需手动管理 |
> | **硬件绑定** | 不绑定特定GPU厂商 | 仅限NVIDIA GPU |
>
> 简单说：NVSHMEM是**通信原语**（类似TCP/UDP），Mooncake是**应用层协议**（类似HTTP）。Mooncake可以在底层使用NVSHMEM/RDMA作为传输后端。

---

### 11. FA3的兼容问题是什么？怎么解决的？FA3和FA2的区别？

**你的回答：** Kimi在Decode阶段不支持FA3，关闭FA3用替代方法。FA3与FA2区别不了解。

**参考答案：**

> **FA2 vs FA3核心区别：**
>
> | 维度 | FlashAttention-2 | FlashAttention-3 |
> |------|-------------------|-------------------|
> | **硬件目标** | Ampere/Ada (SM80/89) | Hopper (SM90，即H100) |
> | **核心优化** | 更好的work partitioning，减少non-matmul FLOPs | 利用Hopper的**异步特性**：warp specialization + WGMMA指令 + TMA硬件 |
> | **编程模型** | CUDA Cores为主 | 利用Tensor Memory Accelerator (TMA)做异步数据搬运，实现计算与访存overlap |
> | **FP8支持** | 不支持 | 原生支持FP8（block-wise quantization） |
> | **性能** | 在H100上已经很快 | 在H100上比FA2再快**1.5-2x**（接近理论峰值75%） |
>
> **为什么Decode不支持FA3：**
> FA3的优化主要针对长序列的Prefill（大矩阵乘法能充分利用Hopper的异步流水线）。Decode阶段每次只有1个query token，计算量极小，FA3的流水线无法填满，反而引入额外开销。部分模型的Decode attention实现（如带有特殊mask或稀疏pattern的）在FA3接口下可能不兼容。
>
> **更好的解法思路：** 不是简单"关闭FA3"，而是**Prefill阶段用FA3，Decode阶段fallback到FA2或用PagedAttention/FlashDecoding**。这也是PD分离的另一个好处——两个阶段可以用不同的attention实现。

> [!info] PPU 上的实际踩坑（详见 [[秋招/面经/快手 AI infra面经|快手面经 Q12 问题1]]）
> FA3 的 `q_v` 融合路径只对 Hopper 实现，PPU 上会报 `RuntimeError: q_v is only supported for Hopper GPUs`。解法是**拆开配置**：`--prefill-attention-backend fa3 --decode-attention-backend flashmla`。

---

### 12. 不同模型在相同上下文长度下KV Cache占用量一样吗？MLA是什么？

**你的回答：** 不太了解。知道MLA是Deepseek的，用于压缩KV Cache。

**参考答案：**

> **不一样，差异巨大。** KV Cache大小取决于模型的Attention架构：
>
> | 架构 | 代表模型 | KV头数 | 相对KV Cache大小 |
> |------|---------|--------|-----------------|
> | **MHA**（Multi-Head Attention） | GPT-3, 早期LLaMA | = Q头数（如128） | **100%**（基准） |
> | **MQA**（Multi-Query Attention） | PaLM, Falcon | 1 | **~1/128**（极小） |
> | **GQA**（Grouped-Query Attention） | LLaMA-2/3, Kimi | 分组数（如8） | **~8/128 = 6.25%** |
> | **MLA**（Multi-head Latent Attention） | Deepseek-V2/V3 | 压缩到低秩空间 | **~5-10%** |
>
> **MLA的核心思想：**
>
> 传统Attention中，每层每个头都要缓存独立的K、V向量。MLA将KV压缩到一个低秩的**latent向量**（compressed KV）：
>
> ```
> 传统：Cache = [K₁, V₁, K₂, V₂, ..., Kₕ, Vₕ]  → 大
> MLA ：Cache = [c]  （一个低维latent向量）       → 小得多
>        推理时：K, V = Up_proj(c)  （解压恢复）
> ```
>
> Deepseek-V2用MLA将KV Cache压缩到原来的**约5%**，使得超长上下文推理在显存上变得可行。代价是Decode时需要额外做一次上投影（up-projection），增加少量计算。
>
> 这就是为什么**同样80K上下文，Deepseek的KV Cache远小于Kimi（GQA）**，PD分离时的传输压力也小得多。

---

## 二、基础知识

### 13. 用Python一行代码分配10GB内存

**你的回答：** 未能回答。

**参考答案：**

```python
# 方法1：用bytearray（精确10GB）
a = bytearray(10 * 1024 * 1024 * 1024)

# 方法2：用numpy（面试官演示的方式）
import numpy as np
a = np.zeros(10 * 1024 * 1024 * 1024 // 8, dtype=np.float64)  # float64每个8字节

# 方法3：更简单的numpy写法
a = np.zeros(10 * (1024**3) // 1, dtype=np.uint8)  # 1字节元素，精确10GB

# 面试官给的示例大概是：
a = [0] * (10**8)  # 注意：这不是10GB，Python的int对象每个约28字节
                    # 实际占用约 28 * 10^8 ≈ 2.6GB（对象开销大）
```

**关键知识点：** Python的`list`存的是**对象引用**，每个`int`对象约28字节 + 指针8字节，内存远大于裸数据。如果要精确控制内存，用`bytearray`、`array.array`或`numpy`。

---

### 14. 从Python层到操作系统层到硬件层，分配内存背后发生了什么？

**你的回答：** Python分析变量、分配内存、转换机器码、向操作系统请求内存。

**参考答案：** 完整链路如下：

> **Python层：**
> 1. CPython解释器执行字节码，调用`list`的构造函数
> 2. 对每个元素调用Python内存分配器（**pymalloc**）——小对象（<512B）走pymalloc的arena/pool/block三级结构；大对象直接调用C的`malloc`
> 3. 10^8个`int(0)`对象 + list本身的指针数组 → 需要大量内存
>
> **C运行时层（glibc malloc）：**
> 4. `malloc`管理一个堆区（heap），小分配走**brk/sbrk**扩展堆顶；大分配（通常>128KB）走**mmap**直接映射匿名页
> 5. 10GB属于大分配 → 调用`mmap(NULL, size, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_ANONYMOUS, -1, 0)`
>
> **操作系统层（Linux内核）：**
> 6. `mmap`系统调用 → 内核在进程的**虚拟地址空间**中找到一段空闲区域，创建一个**VMA（Virtual Memory Area）**结构体，记录这段虚拟地址的范围和权限
> 7. **此时并没有分配物理内存！** 这是Linux的**lazy allocation / demand paging**
> 8. 当程序第一次**写入**某个虚拟页时 → 触发**Page Fault（缺页中断）**
> 9. 内核的缺页处理程序：分配一个物理页帧（4KB） → 在**页表**中建立虚拟页→物理页的映射 → 将该页清零 → 返回用户态继续执行
> 10. 如果物理内存不足 → 内核触发**页面回收**（LRU淘汰、swap到磁盘）或OOM Killer
>
> **硬件层：**
> 11. CPU访问虚拟地址 → **MMU（内存管理单元）** 查**TLB（Translation Lookaside Buffer）**
> 12. TLB命中 → 直接得到物理地址 → 访问内存
> 13. TLB未命中 → **Page Table Walk**：MMU硬件遍历多级页表（x86-64是4级：PGD→PUD→PMD→PTE）→ 找到物理地址 → 缓存到TLB → 访问内存
> 14. 物理地址发送到**内存控制器** → 选择DIMM通道 → 寻址到具体的rank/bank/row/column → 读写DRAM单元

---

### 15. 变量a是逻辑地址还是物理地址？

**你的回答：** 逻辑地址。✅

**参考答案：** 正确。补充：

> 用户态程序（包括Python）拿到的地址**全部是虚拟地址（逻辑地址）**。物理地址只有内核和MMU硬件能看到。这是操作系统内存保护的基础——进程间地址空间隔离，进程A的地址0x7fff0000和进程B的0x7fff0000映射到不同的物理页。
>
> 严格来说，x86-64的地址翻译是：**逻辑地址（段:偏移）→ 线性地址（虚拟地址）→ 物理地址**。但现代OS中段基址都是0，所以逻辑地址≈虚拟地址。

---

### 16. 逻辑地址和物理地址通过什么映射？

**你的回答：** 页表。✅

---

### 17. 页表是怎样的结构？存在哪里？

**你的回答：** 将内存分成块，记录起始节点、偏移量、大小。

**参考答案：**

> **页表存在哪里：** 存在**物理内存（DRAM）**中，每个进程有自己的页表。页表基地址存在CPU的**CR3寄存器**（x86-64）中，进程切换时内核会切换CR3。
>
> **页表结构（x86-64四级页表）：**
>
> ```
> 虚拟地址 (48位有效):
> ┌─────────┬─────────┬─────────┬─────────┬──────────┐
> │ PGD(9位) │ PUD(9位) │ PMD(9位) │ PTE(9位) │ Offset(12位) │
> └─────────┴─────────┴─────────┴─────────┴──────────┘
>     ↓          ↓          ↓          ↓
>   1级页表 → 2级页表 → 3级页表 → 4级页表 → 物理页帧号
>                                          + Offset → 物理地址
> ```
>
> - 每级页表是一个**512项的数组**（9位索引 = 512项）
> - 每项8字节，包含：下一级页表的物理地址 + 标志位（Present/Read-Write/User-Supervisor/Accessed/Dirty等）
> - 最终PTE项包含**物理页帧号（PFN）**，拼上12位页内偏移得到物理地址
> - **页大小**默认4KB（12位偏移），也支持2MB大页（合并PMD+PTE）和1GB巨页（合并PUD+PMD+PTE）
>
> **TLB加速：** 页表遍历需要4次内存访问，太慢。CPU内置TLB缓存最近使用的虚拟→物理映射，命中率通常>99%。
>
> **与 PagedAttention 的类比（可主动抛，加分）：** KV Cache 的分页管理就是这套虚拟内存思想——block table 做逻辑块→物理块映射，外部碎片为 0，只有最后一个 block 平均浪费 `page_size/2` 的内部碎片。

---

### 18. 用两个线程交替打印0-99（奇偶分离）

**你的回答：** 未能完成。

**参考答案：**

```python
import threading

lock = threading.Lock()
cond = threading.Condition(lock)
current = [0]  # 用list包装以便在闭包中修改

def print_odd():
    while current[0] < 100:
        with cond:
            while current[0] < 100 and current[0] % 2 == 0:
                cond.wait()
            if current[0] >= 100:
                break
            print(current[0])
            current[0] += 1
            cond.notify()

def print_even():
    while current[0] < 100:
        with cond:
            while current[0] < 100 and current[0] % 2 == 1:
                cond.wait()
            if current[0] >= 100:
                break
            print(current[0])
            current[0] += 1
            cond.notify()

t1 = threading.Thread(target=print_even)
t2 = threading.Thread(target=print_odd)
t1.start()
t2.start()
t1.join()
t2.join()
```

> **核心要点：**
> - 需要一个**同步机制**让两个线程交替执行——最常用的是**Condition Variable（条件变量）**
> - 偶数线程：当current是奇数时`wait()`，打印后`notify()`唤醒奇数线程
> - 奇数线程：当current是偶数时`wait()`，打印后`notify()`唤醒偶数线程
> - 也可以用`threading.Event`、`threading.Semaphore`或`threading.Barrier`实现
>
> **Python GIL补充：** Python有GIL（全局解释器锁），同一时刻只有一个线程执行Python字节码，所以Python多线程无法实现真正的CPU并行。但这道题考的是**线程同步**，GIL不影响正确性。面试中可以主动提一句"Python有GIL，真正的CPU并行需要multiprocessing"来加分。

---

### 19. 用Python实现LRU Cache（get + put）

**你的回答：** 选择了双端链表+哈希表（数据结构正确），代码有一些边界bug未修完。

**参考答案：**

```python
class Node:
    def __init__(self, key=0, val=0):
        self.key = key
        self.val = val
        self.prev = None
        self.next = None

class LRUCache:
    def __init__(self, capacity):
        self.cap = capacity
        self.cache = {}  # key -> Node
        self.head = Node()  # dummy head（最近使用）
        self.tail = Node()  # dummy tail（最久未使用）
        self.head.next = self.tail
        self.tail.prev = self.head

    def _remove(self, node):
        node.prev.next = node.next
        node.next.prev = node.prev

    def _add_to_head(self, node):
        node.next = self.head.next
        node.prev = self.head
        self.head.next.prev = node
        self.head.next = node

    def get(self, key):
        if key not in self.cache:
            return -1
        node = self.cache[key]
        self._remove(node)
        self._add_to_head(node)
        return node.val

    def put(self, key, val):
        if key in self.cache:
            node = self.cache[key]
            node.val = val
            self._remove(node)
            self._add_to_head(node)
        else:
            if len(self.cache) >= self.cap:
                # 淘汰尾部（最久未使用）
                lru = self.tail.prev
                self._remove(lru)
                del self.cache[lru.key]
            node = Node(key, val)
            self.cache[key] = node
            self._add_to_head(node)
```

> **关键设计点：**
> 1. **dummy head/tail**：避免处理空链表的边界条件，所有操作统一
> 2. **哈希表存Node引用**（不是存值）：`get`时O(1)找到节点，然后O(1)移动到链表头部
> 3. **Node中存key**：淘汰尾部节点时需要知道key才能从哈希表中删除——这是面试官提示你的"cache中set够不够"的问题
> 4. **`_remove`和`_add_to_head`分离**：所有移动操作都是"先remove再add_to_head"，复用逻辑
> 5. 时间复杂度：get O(1)，put O(1)
>
> 关联：LRU 也是 [[Leetcode/CodeTop手撕40题背诵手册|CodeTop 手撕手册]] 的高频题（LC146），面试前务必手写一遍。

---

## 三、面试后复盘

**答得好的部分：** PD分离原理、存储层次、Mooncake原理、逻辑/物理地址、页表、LRU数据结构选择——基础概念掌握是到位的。

**明显缺口，需要补：**

| 方向 | 具体建议 |
|------|---------|
| **定量分析能力** | 做推理优化要能手推KV Cache大小、传输延迟、显存占用，建议练习从模型参数推算各种资源需求（Q5/Q6 未答出是最直接的失分点） |
| **模型架构理解** | 了解MHA/GQA/MQA/MLA的区别和KV Cache影响，这是推理优化的核心知识 |
| **操作系统** | 重点补虚拟内存（页表遍历、TLB、demand paging）、多线程同步（mutex/condition/semaphore） |
| **编码熟练度** | 多练手写链表操作、哈希表组合数据结构、多线程同步的经典题 |
| **项目深度** | 对自己做的每个优化，都要能说清楚"优化前什么数字→优化后什么数字→为什么有这个提升" |

**后续行动：**
- [ ] 手推一遍 KV Cache 大小公式（Q5）+ RDMA 传输延迟估算（Q6），做到能白板演算
- [ ] 补齐 MHA/GQA/MQA/MLA 对比与对 KV Cache 的影响（Q12）
- [ ] 手写 LRU（LC146）+ 两线程交替打印（Condition/Semaphore 两种写法），到肌肉记忆
- [ ] 复盘 TTFT 变差的因果链（Q8），准备好"PD 分离是双刃剑"的标准答法
