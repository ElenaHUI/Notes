---
tags:
  - 面经
  - 百度
  - AI-infra
  - PD分离
  - KVCache
  - RDMA
  - MCP
  - AgentInfra
aliases:
  - 百度面经
company: 百度
position: AI Infra（Agent Infra 方向）
date: 2026-09-02
---

# 百度 AI Infra 面经

> **岗位**：AI Infra（团队实际方向是 Agent Infra：RL 环境 + Agent Harness）
> **面试时间**：2026-09-02（周三）上午 11:00
> **主线**：PD 分离部署 → 调参方法论 → KV Cache 结构 → RDMA → 多级缓存 → 后训练/Agent 协议 → PD 配比 → 团队方向
> **项目简介（开场标准答案）**：见私有笔记《PTG项目简介》（仅 vault 内，站点不发布）

- [x] 周三上午11点面试 ✅ 2026-09-02
- [ ] 测评 📅 2026-09-12

---

## 一、项目与职责

### Q1 你这套 PD 分离的部署，具体做了哪些工作？

围绕**在平头哥 PPU（真武 810E，单卡 96GB HBM）上用 SGLang 把 MoE 大模型（Kimi-K2.6 / Qwen3.5-397B / Qwen3-235B）跑成生产级 PD 分离服务**，做的是端到端的事：

**1）模型 & 硬件适配**

- W4A8 / W8A8-INT8 量化下模型加载与精度验证；
- Attention backend 适配：FA3 在 PPU 上报 `RuntimeError: q_v is only supported for Hopper GPUs`，改成 `--prefill-attention-backend fa3 --decode-attention-backend flashmla` 拆开配置；
- `w4a8` 不支持开 EP（`assert m == m_ and n == n_ and k == k_`），踩坑后固化成部署 checklist。

**2）传输链路（PD 之间的 KV Cache 搬运）**
- Mooncake Transfer Engine + RDMA：`--disaggregation-ib-device mlx5_bond_0..7`（8 张网卡并行）；
- 机内走 ICN/NVLink：`MC_FORCE_MNNVL=1`、`MC_USE_NVLINK_IPC=1`，用 `MC_LOG_LEVEL=TRACE` 确认真的走了 ICN link（看 `register memory: addr` 日志）；
- `MC_NUM_QP_PER_EP` 多 QP 调优。

**3）部署形态：裸机 → K8s**
- 从 host 直接 `sglang.launch_server`，迁到 **DynamoGraphDeployment（DGD）**：`backendFramework: sglang`、etcd 服务发现、nats 事件面、`rdma/hca: 4` 资源声明、PPU + `board.type=810e` 节点亲和；
- 关键点：`extraPodSpec` 必须开 `hostNetwork / hostPID / hostIPC + dnsPolicy: ClusterFirstWithHostNet`，否则 Mooncake 拿不到宿主机 `mlx5_bond_*`，RDMA 初始化失败或 fallback 到低效路径；
- 网络层：`cni0` 与 `flannel.1` MTU 必须和物理 bond 对齐（物理 1500 → 1450；物理 9000 → 8950，VXLAN 约 50B 封装开销），跨机不一致会出现丢包 / PMTU 黑洞。

**4）Router 与调度**

- `mini-lb` vs `sgl-router` 对比；上线用 sgl-router 开 **cache-aware routing**（router 维护带 worker 标签的近似 radix tree 选 P 节点，P 节点自己再做精确前缀匹配复用 KV）；
- Router 资源标定：4 核 8G vs 64 核 128G 实测无差异（近似树 + tokenizer + Rust runtime 稳态 2~4GB）。

**5）压测与配比标定**：1P1D → 2P1D → 3P1D → 3P2D 阶梯压测（见 Q19）。

**6）故障定位**

- Decode 机缺 `alixpu-peermem` → RDMA 注册显存失败 → `bad address`（见 Q12）；
- `--context-length 16384` < 压测 `input 65536 + output 1536` → server 返错 JSON → 客户端 `KeyError: 'choices'`（同类陷阱：`--served-model-name` 不匹配、KV OOM 5xx，都是先 curl 拿原始错误体区分）。

**7）可观测**：`--enable-metrics --enable-cache-report --enable-expert-distribution-metrics`，接 Prometheus 出 TTFT / TPOT / 并发 / cache 命中率报表。

> 详见 [[kimi2.6 PD分离部署记录]]、[[DeepSeek-Flash-0731 SGLang 的PD分离部署]]。

### Q2 其中哪一块是你负责的？业务场景是什么？

**业务场景**：内部推理服务（红区 Infra），支撑内部 LLM 应用，典型 workload 是**长输入短输出**——平均 input 80K+ tokens（文档理解 / RAG / 代码类），output 相对短。这个分布直接决定了后面 PD 配比偏 P。

**我负责的部分**：从模型上卡到上线的**整条链路 owner**——环境适配、启动参数、K8s 编排、RDMA/网络打通、压测标定、故障定位、上线配置和监控报表。不是只做其中一小块，1P1D 到 3P2D 的所有对比实验和上线配置都是我做的。

---

## 二、调参方法论（面试官重点追问）

### Q3 升级版本 / debug / 解码参数调优，你在调参过程中有没有沉淀和方法论？能不能讲讲参数背后的原理？

我的方法论是**「定基线 → 归因瓶颈 → 单变量对照 → 反直觉结果必须深挖 → 文档化」**这五步：

**1）先把实验做成可复现的（否则调参就是玄学）**

- 固定 workload：同一份线上真实 prompt 长度分布，固定 `--random-input-len / --random-output-len`、并发阶梯、请求数；
- 固定环境：同一镜像版本、同一批机器、同一 router 配置；
- 固定脚本：`sglang.bench_serving` 一条命令跑完，指标自动落盘，避免手工误差。

**2）先归因瓶颈，再决定调哪个参数**

不同瓶颈对应完全不同的参数空间，先判断是 **compute-bound / memory-bound / 通信-bound / 传输-bound**：

| 现象 | 瓶颈 | 该动的参数 |
| --- | --- | --- |
| TTFT 高、P 端 GPU util > 90% | Prefill 算力 | 加 P 副本、`chunked-prefill-size`、EP、cache-aware routing 提命中率 |
| TPOT 高、D 端 KV 占用 > 85%、排队 | Decode 显存/带宽 | `mem-fraction-static`、`dp-size`、`max-running-requests`、`cuda-graph-bs` |
| 两侧都不满、TTFT/TPOT 都抖 | KV 传输 | `MC_NUM_QP_PER_EP`、IB device 数、GDR/peermem、MTU |
| MoE 层耗时占比高 | all-to-all | DeepEP `low_latency` 模式、`SGLANG_DEEPEP_NUM_MAX_DISPATCH_TOKENS_PER_RANK` |

**3）单变量对照，一次只改一个**

举几个我实际调过的、能讲清因果的参数：

- **`mem-fraction-static`**：P 端 0.9~0.92，D 端 0.7~0.8。
  *为什么不对称*：P 端算完 prefill 后 KV 立刻通过 RDMA 传走，本地 KV pool 只需要周转，显存可以更多给权重和 chunked-prefill 的 activation 峰值；D 端要长期持有所有在飞请求的 KV，还要给 CUDA Graph 的静态 buffer + decode activation 留余量，所以必须压低，否则 capture 阶段直接 OOM。

- **`dp-size` / `moe-dense-tp-size`**（恒等式 `tp-size = dp-size × moe-dense-tp-size`）：
  Decode 每步每请求只算 1 个 token 的 attention，用 16 卡 TP 去分摊是严重浪费，还要付 all-reduce 通信。改成 `dp-size=16, moe-dense-tp-size=1` 后：attention 层每卡独立算自己的请求，**零通信**；MoE 层仍保持 16 卡 EP，expert 覆盖不变。所以 D 端 `dp-size == tp-size` 是默认最优解，只有单卡放不下 attention 参数时才降 dp、提 dense_tp。
  *反过来我试过 `tp=8, dp=2`，TTFT 竟然变差了* —— 这就是必须深挖的反直觉结果：DP 变小意味着每卡要扛更多请求的 attention，KV 分片收益没了，同时 MoE 侧 all-to-all 的分组结构变了，通信 pattern 反而更碎。

- **`page-size 64`**：block 粒度。大 page → block table 更短、元数据更少、kernel 访存更连续；但内部碎片变大（最后一个 block 平均浪费 page_size/2 个 token 的空间），且 prefix 复用的粒度变粗、命中率下降。64 是长序列场景下的折中。

- **`chunked-prefill-size 163840`**：切块太大 → 单次 forward 显存峰值高、其他请求 TTFT 被拖长；切块太小 → GEMM 打不满、prefill 总时长上升。长输入 workload 下要往大调，但要盯着 activation 显存峰值。

- **`cuda-graph-bs` 密集桶（1..64 共 24 个）**：桶多且密 → padding 浪费少，但录制慢、每张图持有静态 buffer 吃显存；桶少且疏 → 启动快省显存，padding 浪费算力。
  *实测结论是这组密集桶对压测基本没效果* → 说明**当前瓶颈不在 kernel launch overhead**，而是被通信 / KV 传输 / 调度占住了，或者 `dp-size=16` 下每卡 batch 本来就很小、launch 开销占比不高。这个"没效果"的结论比"有效果"更有价值，它把优化方向从 CUDA Graph 排除了。

- **`schedule-conservativeness 0.3`**：调度保守度，控制给未来 decode 预留多少 KV。调低 → 敢塞更多并发、吞吐上去，但抢占/回退风险增加；调高 → 稳但吞吐低。

- **三个 `--disable-*` 全去掉**（`disable-custom-all-reduce` / `disable-radix-cache` / `disable-shared-experts-fusion`）：这三个是早期为了跑通稳定性加的兜底开关，稳定后逐个摘掉，TTFT/TPOT 都明显改善。**调参不只是加参数，更要清理历史包袱。**

**4）指标优先级要写死**

TTFT P99（SLA 硬约束）> TPOT（体感流畅度）> 吞吐 tokens/s/GPU（成本）> KV cache 命中率 / GPU util（诊断用）。**不看单一指标，任何"吞吐涨了"都要同时确认 TTFT/TPOT 没恶化**，否则是拿延迟换吞吐。

**5）沉淀成文档**

每次实验记录「参数 diff + 指标表 + 结论 + 原理解释」，踩坑记成 `问题N: 现象 / 根因 / 解决方法 / 排查方法` 的固定模板（比如 `alixpu-peermem` 那条我把内核模块原理、为什么只有 D 端报错、检查命令都写全了）。这样下次换模型/换版本时是查表，不是重新试错。

> [!tip] 一句话总结
> 调参的方法论 = **把每次调参变成一个有对照组的实验，并且能说出参数 → 硬件行为 → 指标的完整因果链**。说不清因果链的调参才是"调参侠"。

---

## 三、KV Cache 结构与内存管理

### Q4 KV Cache（prefix cache）有解决"缓存内容变化"的问题吗？用 SGLang 会不会有缓存失效的问题？

**不会有正确性问题，因为 cache key 就是 token id 序列本身，不是"内容语义"。**

SGLang 的 RadixAttention 用 **token 序列做 key 做最长前缀匹配**：只有前缀的 token id **逐个完全相同**才会命中，任何一个 token 变了，从那个位置往后的子树就匹配不上，自然不会复用。所以不存在"内容变了但命中旧 KV"的问题。

几个容易混淆的点：

- **采样参数不影响 KV**：`temperature / top_p / seed` 作用在 logits 之后，KV 只依赖 token id + position，所以不同采样参数的请求可以安全共享 prefix KV；
- **chat template / system prompt 变了 → 前缀不同 → 自然不命中**，这是"失效"的正常形态，靠 LRU 驱逐回收；
- **需要显式隔离的维度**（否则真的会串味）：
  - **LoRA adapter**：不同 adapter 的 KV 不同，必须进 key 或按 namespace 隔离；
  - **多模态输入**：图像/音频要把它的内容 hash 进 key；
  - **模型版本 / 量化精度 / TP 切分方式变化**：整体失效，重启即清空；
  - **page-size / 内存布局变化**：物理布局不兼容。
- **并发安全**：block 有引用计数，`ref_count > 0` 的 block 不会被驱逐，正在被 decode 使用的 KV 不会被抢走；写时复制（CoW）处理分叉。
- **PD 分离下的差异化策略**：**P 端开 radix cache，D 端 `--disable-radix-cache`**。因为 D 端的 KV 是 P 通过 RDMA 传过来的，本地前缀复用价值低，而 D 端显存要留给更大的 decode batch。上线配置是 router 开 kv-aware + P 端 3 副本开 radix cache。

### Q5 这两种 KV Cache 结构，类比 C++/Java 里的数据结构，有哪些相似性？

| LLM 推理里的结构 | 编程语言 / OS 里的类比 |
| --- | --- |
| **Block Table**（逻辑块号 → 物理块号） | **虚拟内存页表**；C++ 里就是 `std::vector<int>`，Java 是 `int[]` / `ArrayList<Integer>` |
| **全局空闲块管理** | **free list**（单/双向链表），或 slab allocator 的空闲槽链 |
| **固定大小 KV block 池** | **内存池 / slab allocator**：`boost::pool`、`tcmalloc` 的 size class；Java 的 `ByteBuffer.allocateDirect` 池化 |
| **Radix Tree 前缀索引** | **Patricia Trie / 压缩前缀树**（C++/Java 标准库都没有，需要自己实现）；行为上接近 `std::map<string, V>` / `TreeMap` 的有序前缀查找，或文件系统的路径 dentry cache |
| **block 引用计数** | `std::shared_ptr` 的 refcount；Java 里没有直接对应（GC 是另一套），最接近的是 `Cleaner`/`PhantomReference` |
| **Copy-on-Write 分叉** | `fork()` 的 COW page；C++ 早期 `std::string` 的 COW 实现 |
| **LRU 驱逐** | `std::list` + `std::unordered_map` 的经典组合；Java 直接就是 `LinkedHashMap(cap, 0.75f, true)` |
| **两级映射 `ReqToTokenPool` → `TokenToKVPool`** | **两级页表**（page directory + page table）；或 `Map<Request, int[]>` + `int[] → 物理 slot` 的间接寻址 |
| **KV slot 数组本身** | 一个大 `ndarray` / 扁平化 `std::vector<half>`，靠 index 寻址，不做对象封装（避免 GC / 分配开销） |

**核心共性**：都是**「间接寻址 + 固定粒度分配 + 引用计数 + 缓存驱逐」**这四件套。区别在于 KV Cache 是**跨 step 长期存活、且要在 GPU 上被 kernel 直接按裸地址访问**，所以不能用语言自带的 GC/容器，必须自己做一套显式的、地址稳定的池化管理——这也是为什么实现上更像"手写 OS 内存管理"而不是"用 STL"。

### Q6 你说的是链表 + 数组（虚拟内存和页表）。那 SGLang 为什么没有碎片化问题？

> 现场我答的是"页表 + 数组 + 链表"，方向对，但需要说得更准确：**block table 是数组，全局空闲块是 free list（链表），前缀索引是 radix tree（树）**，三者分工不同。

**PagedAttention / RadixAttention 没有外部碎片的根本原因：**

1. **固定大小 block 分配**
   所有 KV block 尺寸完全一致（`page_size × num_kv_heads × head_dim × 2(K,V) × dtype_bytes`），分配和释放都是整块操作。空闲空间永远是"若干个标准块"，任何新请求要的也是"若干个标准块"——**不存在"总量够但找不到一段连续区间"的情况，即外部碎片为 0**。

2. **逻辑连续 → 物理离散（间接寻址）**
   请求视角的 token 序列是逻辑连续的，物理块号由 block table 间接映射。所以**根本不需要连续物理显存**。这是从虚拟内存借来的核心思想：页表把"连续地址空间"和"离散物理页"解耦。

3. **按需增长，不预留 max_seq_len**
   naive 实现要为每个请求按最大长度预留连续显存 → vLLM 论文实测这类系统 KV 浪费 **60%~80%**。paged 方案是每生成 `page_size` 个 token 才申请一个新块，用多少占多少。

4. **共享 + 引用计数**
   相同前缀的 block 被多个请求共享同一份物理块，不重复分配 —— 这既省显存，也减少了"分配-释放"的循环，间接降低碎片产生。

5. **可抢占 / 可换出**
   显存不够时驱逐 radix tree 的 LRU 叶子节点，或 swap 到 host（HiCache），而不是直接 OOM 拒绝请求。

**但它有内部碎片**：每个请求最后一个 block 平均浪费 `page_size / 2` 个 token 的空间。所以 `page_size` 是一个明确的权衡：

| page_size | 内部碎片 | 元数据 / block table 长度 | kernel 访存连续性 | prefix 复用粒度 |
| --- | --- | --- | --- | --- |
| 小（1~16） | 小 | 长 | 差 | 细，命中率高 |
| 大（64~128） | 大 | 短 | 好 | 粗，命中率低 |

我们用 64，是因为长输入 workload 下 prefix 本来就长，粗粒度对命中率影响小，而 kernel 效率和元数据开销收益更明显。

**补充：SGLang 相对 vLLM 的额外一层**
vLLM 的 paged 解决的是**物理碎片**；SGLang 的 radix tree 在此之上解决的是**重复计算**——把"已算过的前缀"变成可检索、可共享、可 LRU 驱逐的缓存对象。物理层仍然是同一个 block pool，radix tree 只是索引层，驱逐时以 block 为单位归还 free list。

### Q7 KV Cache 要存的元数据都有哪些？整个数据包里最关键的资料是什么？

**A. 本地管理需要的元数据（memory pool 侧）**

| 类别 | 字段 |
| --- | --- |
| 映射 | block table / slot mapping（逻辑 block idx → 物理 block idx）、`ReqToTokenPool` 的 req → token 索引 |
| 长度 | 已缓存 token 数、已分配 block 数、max context length |
| 生命周期 | ref count、last access timestamp（LRU）、是否可驱逐（是否叶子节点） |
| 索引 key | token id 序列的 hash / radix tree 节点、（多模态时的图像 hash、LoRA id） |
| 布局 | num_layers、num_kv_heads、head_dim、dtype、page_size、是否 MLA（latent 压缩维度） |
| 并行 | TP/DP rank → head 分片映射、device id |
| 标识 | request id |

**B. PD 分离时通过 RDMA 传输的数据包，最关键的几项**

1. **会话标识**：`bootstrap room` / request id —— P、D、router 三方靠它对齐同一次传输；
2. **KV 布局元信息**：`num_layers, num_kv_heads, head_dim, dtype, page_size` + **TP/DP rank 映射** —— D 端的并行切分方式如果和 P 端不同（我们就是 P 端 dp=1、D 端 dp=16），必须靠这个把源分片重排到目的分片；
3. **地址描述符（最核心）**：`(remote_addr, rkey, length)` 与本地 `(addr, lkey, length)` 的配对列表，即 **scatter-gather list** —— 因为 KV 在物理上是离散 block，一次传输是多个不连续片段的批量 WRITE；
4. **块数量 / token 数**：决定要传多少、完成判据是什么（见 Q9）；
5. **前缀命中信息**：哪些 block D 端已经有了，可以跳过传输；
6. **完成状态**：transfer status / done flag。

> [!note] 一句话
> **数据面传的是"地址 + 长度 + rkey"的 SGE 列表，控制面传的是"布局 + rank 映射 + room id + 完成信号"**。KV 本体从不经过序列化，就是裸显存地址的 DMA。

---

## 四、RDMA

### Q8 你针对 RDMA 做过优化，具体有哪些参数？一次 RDMA 通信要传哪些关键字段、函数里有哪些信息？

**A. Verbs API 的完整链路（函数级）**

```
ibv_get_device_list / ibv_open_device     → 打开 HCA
ibv_alloc_pd                              → Protection Domain（隔离域）
ibv_reg_mr(pd, addr, len, access_flags)   → 注册 Memory Region，返回 lkey / rkey
                                            （这一步就是需要 peermem 才能注册显存的地方）
ibv_create_cq                             → Completion Queue
ibv_create_qp(pd, {cap, qp_type=IBV_QPT_RC}) → Queue Pair（含 SQ 发送队列 + RQ 接收队列）
ibv_modify_qp: RESET→INIT→RTR→RTS         → 状态机，建连
ibv_post_send / ibv_post_recv             → 下发 Work Request（WR），敲 doorbell
ibv_poll_cq                               → 轮询 Work Completion（WC）
```

**B. 建连必须带外交换的信息**（RDMA 自己不发现对端，走 TCP / etcd）：
`QP number`、`LID`（IB）或 `GID`（RoCE v2，含 IP）、`PSN`（packet sequence number，初始序号）、`MTU`、以及 `rkey + remote_addr`（授权对端访问哪块内存）。

**C. WR（`ibv_send_wr`）的关键字段**

| 字段 | 含义 |
| --- | --- |
| `wr_id` | 用户自定义 64bit 标识，completion 时原样带回，用于关联是哪个请求 |
| `opcode` | `IBV_WR_RDMA_WRITE` / `RDMA_READ` / `SEND`（Mooncake 主要用单边 WRITE） |
| `sg_list` + `num_sge` | scatter-gather：每项 `{addr, length, lkey}`，支持一次 WR 搬多个不连续片段 |
| `wr.rdma.remote_addr` | 对端虚拟地址 |
| `wr.rdma.rkey` | 对端内存的远程访问密钥 |
| `send_flags` | `IBV_SEND_SIGNALED`（是否产生 CQE）、`IBV_SEND_INLINE`（小数据内联进 WQE，省一次 DMA 读）、`IBV_SEND_FENCE` |
| `imm_data` | 32bit 立即数，会在对端产生 CQE，可用来做带内完成通知 |

**D. WC（`ibv_wc`）的关键字段**：`wr_id`、`status`（`IBV_WC_SUCCESS` / `IBV_WC_RETRY_EXC_ERR` / `IBV_WC_REM_ACCESS_ERR` / `IBV_WC_RNR_RETRY_EXC_ERR`）、`opcode`、`byte_len`、`imm_data`。

**E. 我实际调过的优化参数**

| 参数 | 作用 | 我们的值 / 结论 |
| --- | --- | --- |
| `--disaggregation-ib-device` | 多网卡并行，聚合带宽 | `mlx5_bond_0..7` 全 8 张 |
| `MC_NUM_QP_PER_EP` | 每 endpoint 的 QP 数，多 QP 打满多路径、提升并发度 | 4（试过 8） |
| `MC_FORCE_MNNVL` / `MC_USE_NVLINK_IPC` | 机内传输走 NVLink/ICN IPC 而非 PCIe P2P 或共享内存拷贝 | 都开，TRACE 日志验证生效 |
| **GPUDirect RDMA** | 网卡直接 DMA HBM，省掉 host bounce buffer | 依赖 `alixpu-peermem`，缺失就退化甚至报 bad address |
| MTU | IB MTU 4096；网络侧 bond/eth/cni0/flannel.1 对齐 | 1500→1450 或 9000→8950 |
| 选择性 signal | 不是每个 WR 都要 `SIGNALED`，每 N 个 signal 一次，减少 CQ 压力和 poll 开销 | — |
| chunk size | 太小 → WR 多、doorbell 频繁；太大 → 单流不均、尾延迟高 | — |
| inline threshold | 小于阈值的数据内联进 WQE，省一次网卡 DMA 读主存 | 对控制消息有用 |
| NUMA / PCIe affinity | 网卡与 GPU 挂同一 PCIe switch / NUMA node，跨 NUMA 掉带宽 | K8s 侧靠 `GPU_TOPOLOGY_ANNOTATION` |
| RoCE 无损网络 | PFC / ECN / DSCP / traffic class、GID index 选 RoCE v2 | 集群侧配置 |

**F. 排查工具**：`ibv_devinfo`、`ibstat`、`show_gids`、`ib_write_bw` / `ib_read_bw`（perftest 打裸流）、`ethtool -i`、`lsmod | grep peermem`、`dmesg`。

> [!todo] 待补充
> RDMA 调优后的**实测传输速率**（xx GB/s），与 ICN 理论带宽（700 GB/s）的对比，以及 KV 传输耗时占 TTFT 的比例。（和 [[秋招/面经/商汤 大模型系统工程师面经]] 的 Q9 是同一个待补项）

### Q9 Decode 端已经收到完整 KV Cache、要开始生成 token 了，它怎么通过 RDMA 的通信状态判定"消息已完整、可以开始 decode"？

判定是**「数据面 completion + 控制面通知 + 队列状态机」三层配合**：

**1）数据面：CQE 计数 / 字节数匹配**

- D 端在 prealloc 阶段就知道这次要收多少个 block、多少字节（P 端通过控制面先把元信息发过来）；
- `ibv_poll_cq` 收到对应数量的 CQE 且全部 `status == IBV_WC_SUCCESS`，或者累计 `byte_len` 等于期望值，才算这一批 WRITE 落地；
- **RC 语义下 completion 意味着数据已经在对端内存里了**（RC 的 ACK 表示远端 HCA 已接收并写入），不需要额外读回验证；
- 需要内存屏障保证 DMA 写入对后续 GPU kernel 可见（x86 上 `ibv_poll_cq` 返回即已满足；跨 PCIe 到 HBM 时要靠 GDR 的写序保证）。

**2）控制面：显式 done 通知**

实际工程里不会让 D 端纯靠数 CQE，而是**控制面 + 数据面分离**：
- 数据面走 **RDMA WRITE（单边操作）**，不占 D 端 CPU；
- P 端所有 WRITE 完成后，再通过控制通道（SGLang 的 bootstrap server / ZMQ / TCP）发一条 `KV sent` 消息；
- D 端收到这条消息才认为完整。因为**单边 WRITE 对端 CPU 是不知道的**（除非用 `imm_data` 或 `RDMA_WRITE_WITH_IMM` 产生 CQE），必须有人告诉它"传完了"。

**3）队列状态机（SGLang 的实现）**

```
请求到 D 端
  → DecodePreallocQueue   ：预分配 KV block、注册 RDMA buffer，把 (addr, rkey) 报给 P 端
  → DecodeTransferQueue   ：等待传输，polling thread 轮询 Mooncake 的 getTransferStatus()
  → 传输完成 → waiting queue → 参与 continuous batching → 开始 decode
```

预分配这一步很关键：**buffer 地址必须先固定下来**，P 端才有 `remote_addr` 可以 WRITE，同时也保证了重传的幂等性（见 Q10）。

### Q10 只靠这个完成标志够吗？它应该像 TCP 一样做完整性校验、编号、结束校验吧？如果 D 端收到了、完整的，但回执告知 P 端时阻塞了或数据丢了，发送端会不会重试？

**分层看，可靠性由不同层负责：**

**1）传输层：RC QP 已经做了 TCP 那套，而且是硬件 offload**

- **编号**：每个包带 PSN（Packet Sequence Number），接收端按序检查；
- **ACK / NAK**：接收端 HCA 自动回 ACK，乱序或丢失回 NAK；
- **超时重传**：`timeout` / `retry_cnt` / `rnr_retry_cnt` 三个 QP 属性控制，超过次数 QP 进入 error state；
- **校验**：链路层 LCRC + 端到端 ICRC（Invariant CRC），覆盖 payload 完整性；
- 所以在 RC 语义下**不会静默丢数据**：要么成功 completion，要么 WC 报明确错误码（`IBV_WC_RETRY_EXC_ERR` 重传超限、`IBV_WC_RNR_RETRY_EXC_ERR` 对端 RQ 没 buffer、`IBV_WC_REM_ACCESS_ERR` rkey/权限错）。这时 QP 需要 reset 重建，不能继续用。

**2）应用层：一般不做内容 checksum**

因为 RDMA 已有 ICRC，再算一遍 checksum 要吃 CPU/GPU 和带宽，得不偿失。应用层做的是**结构性校验**：block count、total length、layer/head 维度是否匹配、request id 是否存在。

**3）真正会出问题的是「控制面回执」——面试官问的这个场景**

D 端已经收全了，但通知 P 端的那条消息丢了 / P 端阻塞了。这时的处理：

- **超时 + 重试**：P 端等 D 端 ACK 有 timeout，超时后重发或重传；SGLang 侧有 `--disaggregation-transfer-timeout` / watchdog（我们把 `--watchdog-timeout` 和 `--dist-timeout` 都设到 3600 避免误杀长任务）；
- **重试是幂等的，这是设计出来的**：因为 D 端**预分配了固定 buffer**，P 端重传是往同一个 `remote_addr` 覆盖写同样的数据 → **RDMA WRITE 到相同地址天然幂等**，重传多少次结果都一样。这就是为什么要先 prealloc 再传，而不是让 P 端动态指定地址；
- **request id 去重**：D 端收到重复的"开始 decode"通知时，靠 room id 判断这个请求是否已经在 running batch 里，避免重复触发；
- **状态查询兜底**：Mooncake 的 `getTransferStatus()` 可以主动查某个 transfer 的状态，不完全依赖异步通知（拉 + 推结合）；
- **最坏情况 abort**：多次重试仍失败就 abort 这个 request，返回错误让上游重试整个请求（此时 P 端可能还有 radix cache，重跑 prefill 成本低）。

**4）发送端会不会多次发起 RDMA 请求？会。**

- 正常路径下，一次 KV 传输本身就是**多个 WR 的批量提交**（每层、每个 block 分片一个 SGE，可能几百上千个 WR，通过 `ibv_post_send` 的 `next` 指针链成链表一次提交）；
- 失败重试路径下，transfer engine 会重新提交整批或失败的那部分；
- 多 QP 场景（`MC_NUM_QP_PER_EP=4`）下，WR 会分散到多个 QP 上并行，完成判定要跨 QP 聚合。

> [!tip] 总结
> **可靠性 = RC 硬件层（PSN/ACK/CRC/重传）+ 应用层（固定 buffer 保证幂等 + request id 去重 + timeout/abort）**。完成标志本身不够，但它不是唯一的保障，底下的 RC 语义才是。

### Q11 RDMA 传输过程中经过 CPU 吗？它的目的不就是直接传到 GPU、这样更快吗？完全不经过 CPU？

**要区分控制面和数据面：**

**数据面：完全不经过 CPU。** 这正是 RDMA 的三个核心特性：

- **Kernel bypass**：应用直接操作 verbs，不走系统调用、不进内核协议栈；
- **Zero copy**：网卡 DMA 引擎直接读写应用内存，没有 `sk_buff` 拷贝、没有用户态↔内核态拷贝；
- **CPU offload**：协议处理（分段、CRC、重传、ACK）全在 HCA 硬件里做，**对端 CPU 甚至完全不知道有数据到达**（单边 WRITE/READ 不产生对端 CQE，除非用 imm）。

对比 TCP：一次 `send()` 要经过系统调用 → socket buffer → TCP/IP 协议栈 → 分段 → 拷贝到网卡 → 对端中断 → 协议栈 → 拷贝到用户态，每 GB 数据要吃掉可观的 CPU 核数。这也是为什么不用 RDMA 的话吞吐会掉 1~2 个数量级。

**控制面：经过 CPU，但只"下发指令"不"搬数据"。**

- `ibv_post_send`：CPU 构造 WQE 写入 SQ（用户态 mmap 的内存），然后 MMIO 写 doorbell 通知网卡 —— 几百纳秒级；
- `ibv_poll_cq`：CPU 轮询（busy polling，或事件模式 `ibv_req_notify_cq`）；
- 建连、地址交换、元信息协商：走 TCP/etcd，CPU 参与。

**是否直接到 GPU：需要 GPUDirect RDMA（GDR），不是默认的。**

```
无 peermem（退化路径）：GPU HBM → cudaMemcpy → host bounce buffer → 网卡
                       → 对端网卡 → host buffer → cudaMemcpy → GPU HBM
                       （2 次额外拷贝 + CPU 参与，且 ibv_reg_mr 注册显存直接失败）

有 peermem（GDR 路径）：网卡 ⇄ GPU HBM 直接 DMA（零拷贝）
```

原理：`nvidia-peermem`（PPU 上是阿里自研的 `alixpu-peermem`，早期叫 `nv_peer_mem`）是内核模块，向 `ib_core` 注册一个 **peer memory client**，让 `ibv_reg_mr` 能识别并注册设备显存地址，网卡拿到显存的物理地址后直接 DMA。新内核也可以用 **DMA-BUF** 机制替代 peermem。

所以准确答案是：**数据搬运完全不经过 CPU；指令下发和完成检查经过 CPU；能不能直接落到 GPU 显存取决于 peermem/DMA-BUF 是否就位。**

### Q12 你是通过什么方式排查出 RDMA 没生效的？整个链路里是哪个阶段不支持导致的？

**现场案例**：Decode 机器上缺少 `alixpu-peermem` 内核模块，导致 D 端报 `bad address`。

**现象**：P 端正常，D 端在接收 KV 时报 bad address，服务跑不通或 TTFT 极高（fallback 到低效路径）。

**根因链**：PD 分离下 KV Cache 通过 Mooncake Transfer Engine 走 RDMA（`mlx5_bond_*`）从 P 传到 D。D 端要把接收缓冲区**直接注册到自己加速卡的显存**里（`ibv_reg_mr`），这一步依赖 `alixpu-peermem` 提供的 peer memory client。模块缺失 → RDMA 层无法把显存地址映射成 HCA 可用的物理地址 → 注册内存返回无效地址 → `bad address`。

**为什么只有 Decode 端报错**：KV 的接收目标是 D 端显存，接收侧注册显存这一步最直接暴露。稳妥起见 P/D 两端都要装（P 端发送时源 buffer 也在显存）。

**排查方法（自上而下分层验证）**：

| 层 | 检查什么 | 命令 |
| --- | --- | --- |
| 应用层 | Mooncake 是否成功 register memory、有没有 fallback 到 TCP | `MC_LOG_LEVEL=TRACE`，grep `register memory: addr` |
| Verbs 层 | 设备是否 UP、port state ACTIVE、link layer（IB / RoCE）、rate | `ibv_devinfo`、`ibstat`、`show_gids` |
| 裸流验证 | 排除网络问题，看纯 RDMA 带宽是否正常 | `ib_write_bw` / `ib_read_bw`（perftest） |
| 内核层 | peermem 是否加载、驱动报错 | `lsmod \| grep peermem`、`modprobe alixpu-peermem`、`dmesg \| grep -iE 'peer\|ib_\|mlx5'` |
| 容器/K8s 层 | 是否 request `rdma/hca`、是否 `hostNetwork`（否则拿不到宿主机网卡和 IB namespace）、`/dev/infiniband/*` 是否挂进容器、`IPC_LOCK` capability + `ulimit memlock unlimited`（注册大内存要 pin） | `kubectl describe pod`、容器内 `ibv_devinfo` |
| 网络层 | bond/eth MTU 一致性、`cni0`/`flannel.1` MTU（1450 vs 8950）、RoCE 的 PFC/ECN、GID index | `ip link show \| grep -E 'bond\|eth\|cni0\|flannel'`、`ping -M do -s 8922 <对端>` |
| 拓扑层 | 网卡与 GPU 的 PCIe / NUMA affinity | `nvidia-smi topo -m`（PPU 对应工具） |

**方法论**：**分层验证 + 最小复现**。先用 perftest 打裸流把"网络/硬件"这一大类排除掉，再回到应用层看注册内存失败的具体 errno 和日志，就能把范围收敛到"哪一层不支持"。这次的结论就是：网络和 verbs 都正常，卡在**内核 peer memory 这一层不支持显存注册**。

**修复 + 固化**：

```bash
lsmod | grep peermem
modprobe alixpu-peermem
# 写入 /etc/modules-load.d/ 保证重启自动加载
```

验证：加载后 TRACE 日志里 register memory 成功，不再出现 bad address。并且把这条写进部署 checklist —— **新机器上架第一件事就是查 peermem**。

---

## 五、多级缓存

### Q13 对多级缓存（比如 SGLang 的 HiCache）有做什么配置吗？GPU、CPU、NVMe 各层的比例怎么定？

**A. 层级结构**

| 层 | 介质 | 容量 | 带宽量级 | 适合放什么 |
| --- | --- | --- | --- | --- |
| L1 | GPU HBM | 几十 GB（去掉权重和 activation 后的剩余） | ~1-3 TB/s | 热的、正在跑的、短 prefix |
| L2 | Host DRAM | 数百 GB ~ TB | 内存本身 50-100 GB/s，**但受 PCIe 4.0 x16 单向 ~32 GB/s 限制** | 温的、多轮会话的历史 prefix |
| L3 | NVMe / 分布式存储（Mooncake Store、3FS） | TB ~ PB | ~3-7 GB/s（本地 NVMe） | 冷的、超长上下文、跨实例共享的系统级 prefix |

**B. SGLang 的配置参数**

- `--enable-hierarchical-cache`：总开关；
- `--hicache-ratio`：host memory = ratio × device KV pool size（默认 2）；或 `--hicache-size` 直接指定 GB；
- `--hicache-write-policy`：`write_through`（每层都写，命中率高但 PCIe 流量大）/ `write_through_selective`（只下沉热的，推荐）/ `write_back`（先写 GPU，驱逐时才下沉，延迟低但有丢失风险）；
- `--hicache-io-backend`：`direct`（O_DIRECT 绕 page cache）/ `kernel`；
- `--hicache-mem-layout`：`layer_first`（按层存，方便传输和计算 overlap 流水）/ `page_first`（按 page 存，方便整体加载）；
- `--hicache-storage-backend`：`file` / `mooncake` / `hf3fs`。

**C. 比例怎么定 —— 不是拍脑袋，是算「回读 vs 重算」的盈亏平衡**

第一步，算单请求 KV 占用：

$$
\text{KV bytes} = 2 \times L_{\text{layers}} \times H_{\text{kv}} \times D_{\text{head}} \times \text{dtype} \times \text{seq\_len}
$$

（MLA 架构会小很多，因为 KV 被压到 latent 空间，这也是 Kimi/DeepSeek 系做长上下文的优势。）

第二步，比较两条路径的耗时（对长度为 $N$ 的 prefix）：

- **重新 prefill**：$T_{\text{prefill}} \approx \dfrac{N \times \text{FLOPs}_{\text{token}}}{\text{GPU 有效算力}}$，compute-bound，长 prefix 很贵；
- **从 L2 回读**：$T_{\text{load}} \approx \dfrac{N \times \text{KV}_{\text{token}}}{\text{PCIe 带宽}}$，带宽-bound。

**当 $\dfrac{\text{KV}_{\text{token}}}{\text{BW}_{\text{PCIe}}} < \dfrac{\text{FLOPs}_{\text{token}}}{\text{算力}}$ 时，回读比重算划算。** 结论就是：**prefix 越长、KV 越压缩（MLA / 量化）、GPU 算力越紧张，HiCache 收益越大**。我们的 PPU 恰好是"显存大、带宽高、算力相对低"，理论上 HiCache 收益是放大的。

第三步，容量比例的实操起点：

- **L1**：由 `mem-fraction-static` 减掉权重和 activation 决定，是瓶颈层，不是自由变量；
- **L2 = 2~4 × L1**：DRAM 便宜，PCIe 带宽也够，性价比最高的一层，默认 ratio=2 起步，看命中率曲线往上加；
- **L3**：容量可以很大，但**只放"重算代价极高"的冷 prefix**（超长 system prompt、多轮会话历史、共享知识库前缀），因为它带宽低，回读慢的话还不如重算。

第四步，用指标闭环调：观测**各层命中率、L2/L3 回读延迟、PCIe 带宽占用、TTFT 变化**。如果 L2 命中率很高但 TTFT 没改善 → 说明回读吃掉了收益，要么改成 `layer_first` 做 overlap，要么缩小 L2 只留最热的。

**D. 我们实际的选择**

上线时**没有开 HiCache**，而是走了另一条路：**P 端开 radix cache（纯 GPU 层）+ router 开 cache-aware routing**。原因是：

1. PD 分离下 prefix 复用的收益点全在 P 端（跳过 prefill），D 端 `--disable-radix-cache`，KV 都是从 P 传来的；
2. router 的 cache-aware 会把相同前缀的请求路由到同一台 P，**在 GPU 层就能拿到大部分命中**，先把这一层榨干；
3. HiCache 会引入 host 内存占用和 PCIe 流量，而我们 P 端的 `mem-fraction-static` 已经压到 0.9~0.92，host 侧还要跑 Mooncake 的注册内存，需要先做容量评估；
4. 属于**"下一步可以做"的优化项**，前置条件是先量化清楚 prefix 命中率分布和 miss 时的 prefill 代价。

> [!todo] 待补充
> 线上实际的 prefix cache 命中率数据（`--enable-cache-report` 有出，需要整理成图表），这是判断该不该上 HiCache 的直接依据。

---

## 六、后训练与 Agent

### Q14 模型的后训练有了解过吗？Agentic RL、长链推理 RL 做过吗？

> **现场回答**：导师项目里针对电信网络（3GPP 文档）做过微调，时间比较久、算法也不算新。RL 这块没实际做过。

**复盘补充（应该能说出来的）：**

**技术谱系**

| 阶段 | 方法 | 要点 |
| --- | --- | --- |
| SFT | Instruction Tuning / LoRA / QLoRA | cross-entropy + AdamW + cosine；LoRA 是 $W = W_0 + BA$ 低秩增量 |
| 偏好对齐 | RLHF (PPO) | 四模型：actor / critic / reference / reward，显存和调度都重 |
| | DPO | 直接从 preference pair 优化，去掉 RM，简单稳定 |
| 推理能力 | **GRPO** | Group Relative：同一 prompt 采 G 条，用组内 reward 均值/标准差做 advantage 归一化，**去掉 critic**（DeepSeek-R1 用的就是这个） |
| | **DAPO** | clip-higher（解耦上下 clip 缓解熵坍缩）、dynamic sampling（过滤全对/全错的组）、token-level policy gradient loss、overlong reward shaping |
| | **GSPO** | sequence-level importance ratio，解决长序列下 token-level IS 方差爆炸 |
| Agent | Agentic RL | 多轮 + 工具调用 + 环境反馈；reward 来自可验证环境（code exec、math、web shop、单元测试） |

**长链推理 / Agentic RL 的核心难点**

1. **Credit assignment**：一条轨迹几十轮、上万 token，只有末尾一个 reward，怎么分配到中间的每一步；
2. **长轨迹的显存和调度**：rollout 长度分布极不均，需要 partial rollout（截断续跑）、异步 rollout；
3. **训练-推理解耦**：rollout 用推理引擎（vLLM/SGLang），训练用 FSDP/Megatron，两边并行策略不同 → 需要 **weight resharding**（把训练侧权重快速重切分同步给推理侧）；
4. **off-policy 程度控制**：异步导致 rollout 用的策略落后于当前策略，要靠 importance sampling 修正或限制 staleness；
5. **环境的隔离与并发**：每个 rollout 要一个干净、可重置、可并行的环境（沙箱），这是 Agent Infra 的核心工程量。

**框架**：veRL、OpenRLHF、TRL、AReaL、ROLL。

**我能接上的一句**：RL 训练里 **rollout 生成占 70%+ 的时间**，本质上就是一个高并发、长 prefix 共享、多轮的推理服务 —— 这正好是我在推理侧做的事情。SGLang 的 RadixAttention 对 agent 多轮轨迹（system prompt + 历史轮次高度重复）的前缀复用有天然优势，PD 分离能让 rollout 的 prefill 和 decode 各自扩缩。所以从推理侧切进 Agent Infra 是很自然的路径。

### Q15 各种 Agent Harness 的标准协议范式有了解吗？比如 MCP、A2A 这类对接协议？

> **现场回答**：MCP 了解（24 年做过一个早期的 MCP server），A2A 那部分听得不太清、没展开。

**复盘补充：**

**MCP（Model Context Protocol，Anthropic）**

- 基于 **JSON-RPC 2.0**，client-server 架构（host app 是 client，工具/数据源是 server）；
- Server 提供的 primitives：**tools**（可调用函数）、**resources**（可读取的数据，URI 寻址）、**prompts**（预置模板）；
- Client 提供的 primitives：**sampling**（server 反向请求 client 做 LLM 推理）、**elicitation**（server 向用户征求输入）、**roots**（工作目录边界）；
- Transport：**stdio**（本机子进程）、**Streamable HTTP**（2025-03-26 spec，替代旧的 HTTP+SSE，单一 `/mcp` endpoint，可返回 JSON 也可升级为 SSE 流）；
- 生命周期：`initialize` 握手（交换 protocolVersion + capabilities）→ `notifications/initialized` → 正常请求。

**A2A（Agent2Agent，Google → Linux Foundation）**

- 解决 **agent 之间**的互操作（MCP 解决的是 agent ↔ 工具）；
- **Agent Card**（`/.well-known/agent.json`）：能力发现，声明 skills、endpoint、认证方式；
- **Task** 为核心抽象，有完整生命周期：`submitted → working → input-required → completed / failed / canceled`；
- 产出是 **Message + Artifact**（artifact 可增量流式产出）；
- JSON-RPC over HTTP(S)，支持 SSE streaming 和 push notification（webhook）；
- **天然为长任务设计**，这点比早期 MCP 强。

**其他**：ACP（IBM/BeeAI，REST 风格）、AGNTCY / AGP（Cisco 等）、OpenAI function calling 的 JSON Schema 工具描述（事实标准）。

**Agent Harness 的组件范式（Claude Code / Codex / Gemini CLI / Cursor 已经高度趋同）**

1. **Agent loop**：model → tool call → result → model，直到收敛；
2. **上下文管理**：system prompt 分层、context compaction / summarization、长期 memory；
3. **工具层**：file read/write/edit、shell、glob/grep、web search/fetch、code exec、browser；
4. **权限与安全**：allow/deny list、plan mode、sandbox、危险操作确认；
5. **会话与状态**：session 持久化、checkpoint、resume、fork；
6. **任务编排**：todo list、subagent 派生、并行 agent；
7. **扩展机制**：**MCP**（远程工具）+ **Skills**（本地 markdown prompt + 脚本，本质是可复用的领域知识包）；
8. **观测**：trace、token/cost 统计、tool 调用成功率。

> 关键区分：**Skill 是"本地存储的 prompt + 脚本"（知识/流程复用），MCP 是"网络传输协议"（能力接入）**，两者不是竞品而是互补。

### Q16 MCP 的通信方式（我的现场回答）+ 追问：为什么每个 tool call 都要传 id？

> **现场回答（记录）**：通信方式其实就是发送一个 JSON。工具调用可以用 MCP 或者 Skill —— Skill 是本地存储的 prompt，MCP 是一个接口，可以有多种通信方式：本机访问用 stdio，跨网络用 HTTP 或 SSE 流式协议。它本质上是一个网络传输协议，规定了输入输出、握手方式，以及消息组成的格式。

**追问：MCP 为什么要给每个请求传 id？**

1. **JSON-RPC 2.0 的请求-响应关联（最根本的原因）**
   MCP 的连接是**全双工、多路复用**的：同一个 stdio / HTTP 连接上可以**并发**发多个请求，而且**方向是双向的**（server 可以通过 `sampling` / `elicitation` 反向向 client 发请求）。响应到达的顺序不保证和请求发出顺序一致。**没有 id，就无法把 response 匹配回它对应的 request。**

2. **区分 request 和 notification**
   JSON-RPC 的语义是：**带 id = request（必须响应）；不带 id = notification（不需要响应）**。像 `notifications/progress`、`notifications/cancelled`、`notifications/initialized` 都是故意不带 id 的。id 的有无本身就是协议的一部分。

3. **取消 / 超时 / 重试的锚点**
   - `notifications/cancelled` 里要带 `requestId`，指明取消哪一个在飞的请求；
   - client 超时后要知道是哪个请求超时了；
   - 重试去重也依赖 id（server 可以缓存已处理的 id）。

4. **进度回调关联**
   请求可以在 `_meta.progressToken` 里塞一个 token，server 后续发的 `notifications/progress`（`progress / total / message`）带上这个 token，把中间进度关联回具体的调用 —— 这是长任务里保持连接不被网关掐断的手段。

5. **另一层 id：`tool_call_id`（这个在 LLM 侧，不是 MCP 侧）**
   模型一轮可以并行发起多个 tool call，返回的 tool result 消息必须带 `tool_call_id` 才能对齐回是哪一个调用的结果。否则多工具并行时上下文直接错乱，模型不知道哪个结果对应哪个调用。**这是"为什么 id 必不可少"在 Agent 层面的体现。**

6. **可观测性**：id 天然是 trace id，串起 client 日志、server 日志、模型上下文三处。

### Q17 远程 MCP 工具调用会有超时、断联、网络抖动，怎么保证幂等？特别是 POST 类的写操作。

**先说清一个前提：MCP 协议本身不提供幂等保证。** 它是 JSON-RPC 传输层，只规定消息格式和握手，幂等必须由应用层（server 实现 + client 策略）来做。

**1）幂等键（Idempotency Key）—— 最标准的做法**

client 生成一个唯一 key（UUID）放在 `_meta` 或参数里，server 端持久化 `key → result`：

- 首次请求：执行 + 存结果；
- 重复请求（同 key）：**直接返回上次的结果，不再执行副作用**。

这是 Stripe 的经典模式，也是唯一能正确处理"请求已执行但响应丢了"的方案。

**2）request id 去重（轻量版）**

server 维护一个已处理 id 的短期缓存（TTL 几分钟），重复 id 返回缓存结果。比幂等键弱，因为 id 可能被 client 复用或重生成。

**3）把非幂等操作改造成幂等的 API 设计**

| 手段 | 说明 |
| --- | --- |
| **POST 创建 + GET 查询** | `POST /tasks (Idempotency-Key)` → 返回 task id → `GET /tasks/{id}` 轮询。把"写"转成"幂等的创建 + 幂等的查询"，这也是 A2A 的 task 模型 |
| **upsert 而非 insert** | 用业务唯一键做 `INSERT ... ON CONFLICT DO NOTHING` |
| **乐观锁 / 条件更新** | 带 version / etag，`UPDATE ... WHERE status='pending' AND version=?`，重复执行 affected_rows=0 |
| **状态机** | 只允许合法状态迁移，重复的"已完成"请求直接返回当前状态 |
| **两阶段** | prepare（预留资源，幂等）+ commit（带 prepare id，幂等） |
| **dry-run** | 提供预演模式，让 agent 先验证再执行 |

**4）超时后的正确行为：先查再重试，不要盲目重试**

```
超时 → 先 GET 状态（tasks/get）
     → 若已成功：拿结果，不重试
     → 若确认未执行：重试
     → 若状态未知：用同一个 idempotency key 重试（server 会去重）
重试策略：指数退避 + jitter + 最大次数 + 熔断
```

**5）连接层的抖动处理**

- Streamable HTTP 的 **`Mcp-Session-Id`** header：连接断了重连时带上，server 恢复会话上下文；
- **`Last-Event-ID`**：SSE 断线重连时从上次的事件位置续传，不丢消息；
- 长连接保活：定期 progress notification 或 ping，避免中间网关（LB / API GW）因空闲超时掐断；
- server 侧要处理 **client 突然消失**（清理 in-flight 资源）和 **client 重复连接**（不能重复启动任务）。

**6）不可幂等的操作：Saga / 补偿**

真的做不到幂等的（比如"发一封邮件"、"下单扣款"），就配一个补偿动作，并在工具描述里明确标注 `destructive: true` / `readOnlyHint: false`，让 agent 和用户在调用前确认。MCP 的 tool annotation 里就有 `readOnlyHint` / `destructiveHint` / `idempotentHint` / `openWorldHint` 这几个字段，**协议给了标注幂等性的位置，但不强制实现**。

**7）Agent 侧还有一层：防止模型自己重复调用**

loop detection（同一 tool + 同一参数在 N 轮内重复出现就打断）、tool 结果缓存（同一轮内相同调用直接复用结果）。

### Q18 MCP 对长任务（耗时很长、产出不确定）的支持，了解吗？

> **现场回答**：这块没有特别了解。我做的那个 MCP server 是 2024 年比较早期的版本，当时还没考虑异步化的问题，大部分用法就是"开个通道，把所有任务同步做完再返回"。

**复盘补充（这是明确的知识缺口，要补）：**

**1）早期 MCP（2024-11-05 spec）的局限**
就是同步 request-response。长任务会一直占着连接，中间网关（LB、API Gateway）通常有 30s~60s 空闲超时，直接掐断。这也是我做的那版的实际情况。

**2）协议逐步补上的能力**

| 能力 | spec 版本 | 解决什么 |
| --- | --- | --- |
| **progress notifications** | 早期就有 | `_meta.progressToken` + `notifications/progress`（progress/total/message）。汇报进度 + **保活**避免超时，但**不解决阻塞** |
| **cancellation** | 早期就有 | `notifications/cancelled`，client 主动取消在飞的长请求 |
| **Streamable HTTP transport** | 2025-03-26 | 替代 HTTP+SSE。单一 `/mcp` endpoint，server 可选择返回 JSON 或升级为 SSE 流；**`Mcp-Session-Id` 支持会话恢复、`Last-Event-ID` 支持断线续传** —— 这是长任务的关键基础设施 |
| **sampling** | — | server 反向请求 client 做 LLM 推理，让 server 端也能有"智能"，支持长流程中的多步推理 |
| **elicitation** | 2025-06-18 | server 中途向用户征求输入（human-in-the-loop），**天然支持长时间等待用户响应**而不阻塞连接 |
| **Tasks（异步操作）** | 较新 / 演进中 | 让长时间运行的操作**立即返回一个 task 句柄**，后续通过查询 / 取消 / 订阅拿结果。模型直接借鉴 A2A 的 task 生命周期 |

**3）A2A 的对比（从一开始就是为长任务设计的）**

- Task 有 id 和完整状态机：`submitted → working → input-required → completed / failed / canceled`；
- **Artifact 增量产出**：结果可以边生成边流式返回，不用等全部完成；
- **Push Notification（webhook）**：任务完成后主动回调 client，client 不需要一直挂着连接或轮询 —— 这是真正的"发起后断开"；
- client 可以带 `taskId` 重连恢复。

**4）工程实践的标准模式（如果现在让我重写那个 MCP server）**

```
方案 A：立即返回 job id
  tool call → server 立即返回 {job_id}
  → 另开一个 query_task(job_id) tool 让 agent 轮询
  → 期间用 progress notification 汇报进度和保活

方案 B：SSE 流式增量产出
  tool call → server 升级为 SSE → 边算边推进度/中间产物 → 最后推 result

方案 C：对接 A2A
  MCP server 作为薄适配层，把请求转成 A2A task，用 webhook 拿完成通知
```

关键设计原则：**把"长任务"从一次 RPC 里拆出来，变成"提交 + 状态查询/订阅"两个幂等操作**，这样超时、断联、重试全部变成可处理的（呼应 Q17）。

---

## 七、架构决策与团队方向

### Q19 PD 分离，你们是如何决策 P 和 D 的比例的？

**分四步：理论估算起点 → 阶梯压测标定 → SLA 约束下选优 → 上线后动态观测修正。**

**第一步：理论估算（给个起点，不是答案）**

稳态下两侧的处理速率要匹配，否则一侧堆积：

$$
\frac{N_P}{N_D} \approx \frac{T_{\text{prefill}}}{T_{\text{decode}}} = \frac{\text{input\_len} / \text{prefill\_吞吐 per 卡}}{\text{output\_len} \times \text{TPOT}}
$$

**最关键的变量是输入输出长度比：**

| Workload | 特征 | P:D 倾向 |
| --- | --- | --- |
| RAG / 文档理解 / 代码分析 | 长输入短输出（**我们就是这类，input 80K+**） | **偏 P**（P 多） |
| 长链推理 / 创作 / Agent 多轮生成 | 短输入长输出 | 偏 D |
| 对话类 | 均衡 | 接近 1:1 起 |

另外三个修正因子：

- **prefix cache 命中率**：命中高 → P 的实际计算量大减 → 可以降低 P 比例（所以我们 router 开 cache-aware + P 端开 radix cache，这直接影响配比）；
- **KV 传输带宽**：RDMA 慢的话 P 端要留余量等传输；
- **MTP / 投机解码**：提升 decode 效率 → D 需求下降。

**第二步：阶梯压测标定（实际决策依据）**

方法：固定线上真实 prompt 分布，用 `sglang.bench_serving` 阶梯加压（并发 1 / 5 / 10 / 20 / 30 / 50），每档记录 TTFT P50/P99、TPOT、吞吐、并发上限。判读规则：

- **TTFT 涨、P 端 GPU util > 90%、D 端有空闲 → P 不够**；
- **TPOT 涨、D 端 KV 占用 > 85%、decode 队列堆积 → D 不够**。

实测阶梯（K8s，长序列 workload）：

| 配置 | 结论 |
| --- | --- |
| Host 1P1D vs K8s 1P1D | 先验证容器化本身没有性能损失（顺带查 MTU / hostNetwork） |
| 1P1D → **2P1D** | 到 20 并发时 2P 优势明显，**TPOT 依然稳定** → 说明瓶颈确实在 P |
| 2P1D → **3P1D** | 20 并发下 **TTFT 好很多，TPOT 只是微升** → 继续加 P 仍有收益 |
| 3P1D → **3P2D** | 加 D 提升 TPOT 和并发上限，最终生产配置 |

![[Pasted image 20260901224755.png]]
![[Pasted image 20260901224925.png]]

**第三步：SLA 约束下选优**

硬约束：**TTFT P99 < 2~3s，TPOT < 50~60ms**。在满足 SLA 的所有配置里取**吞吐/成本最优**的那一档，而不是无脑加卡。

**最终上线配置**：

| 组件 | 副本数 | PPU 卡数 | 备注 |
| --- | --- | --- | --- |
| sglang-router | 2 | 0 | 开 kv-aware routing |
| Prefill | 3 | 48 | 开 radix-cache |
| Decode | 2 | 32 | `dp-size=16` |

即 **3P2D，48 卡 P + 32 卡 D = 80 卡**。

**第四步：上线后用真实流量反过来验证 bound line**

3P2D 上线后的周六流量分析结论：

- **Decode 并发综合数与 TPOT 曲线高度一致，完整正相关** → TPOT 是 D 侧的直接观测指标；
- **并发达到 30 时 TPOT 上升到 60ms** → 这就是 D 侧的 bound line，超过就该加 D 或限流；
- **TTFT 平均 2~3s** → P 侧还有余量，配比是合理的（如果 TTFT 也顶到 SLA，说明 P 不够）。

**第五步（进阶）：静态配比的局限 → 动态调度**

真实流量有波峰波谷、长短请求混合，静态配比要么在低谷浪费卡、要么在高峰被打爆。所以推进 **Dynamo** 这类方案：

- 按队列长度 / SLO 反馈**动态伸缩** prefill 和 decode worker 数量；
- 更激进的是**弹性实例**：同一个 GPU pool 里的实例可以按需切换 P/D 角色，用 KV cache 感知的全局调度器统一分配。

> [!tip] 一句话答法
> **先用输入输出长度比做理论估算定方向，再用阶梯压测找瓶颈侧，在 TTFT/TPOT 的 SLA 硬约束下取成本最优档，上线后用"并发-TPOT 正相关曲线"反推 bound line 持续修正，长期靠动态调度替代静态配比。**

### Q20 我们团队主要做 Agent Infra（RL 环境 + Agent Harness 多样性），你之前经历都在推理侧，对这块有考虑或兴趣吗？

> 面试官介绍：各种 Agent 在强化学习阶段需要有各种各样的模拟环境、隔离环境去交互，我们做的就是这块的 Infra —— 主要包括 **RL 的环境（agent runtime）**，以及 **IO 过程中 agent harness 的多样性**。

**我的回应（表达兴趣 + 建立连接）：**

**有兴趣，而且我认为推理侧的经验是 Agent Infra 的直接上游，不是转方向。**

1. **RL rollout 的瓶颈就在推理引擎**
   Agentic RL 里 rollout 生成占 70%+ 的时间，而且它的负载特征比普通推理服务更极端：**多轮、长轨迹、prefix 高度共享（同一 system prompt + 环境描述被复用成千上万次）、长度分布极不均**。SGLang 的 RadixAttention 对这种前缀复用是天然契合的，PD 分离能让 prefill 和 decode 独立扩缩。我做的正是这套东西的调优和上线。

2. **环境侧的核心问题和 KV Cache 管理是同构的**
   RL 环境要解决的是：**沙箱隔离、高并发调度、状态快照与回滚、fork 出多条分支轨迹**。这跟我熟的 KV Cache 管理是同一套思想 —— CoW 分叉、引用计数、池化分配、LRU 驱逐、checkpoint/restore。Agent 轨迹的 branch 本质就是 radix tree 上的一次 fork。

3. **IO 与传输层可以直接复用**
   环境的观测/动作数据、artifact 的增量产出、weight resharding 的同步，都是高带宽低延迟的传输问题。RDMA、多级缓存、host-device 数据通路这些我踩过的坑（peermem、MTU、PCIe affinity、NUMA）在环境集群里一样会遇到。

4. **Harness 多样性需要统一的协议层和可观测性**
   这块我在 MCP 上有实际开发经验（24 年做过早期的 MCP server），也理解 Skill / tool 协议 / trace 观测的范式趋同。多样性带来的问题是**评测的可复现性**，这需要统一的 harness 抽象和标准化的环境接口 —— 是我很想深入做的工程问题。

**我想补的短板（诚实说）**：RL 训练框架（veRL / OpenRLHF）的实际使用、异步 rollout 架构的设计、environment scaling 的工程实践。这些是我目前只在概念层面了解、没有动手做过的。

**反问面试官（可以追问的）**：

- 目前 RL 环境的并发规模和隔离方案是什么？（容器 / microVM / 进程级沙箱）
- rollout 和训练是同步还是异步？weight 同步的开销占多少？
- Harness 多样性具体指支持多少种 agent 框架，还是指环境类型的多样性？
- 环境的"状态快照 / fork"目前是怎么实现的，有没有和推理侧的 KV Cache 做联动？

---

## 复盘 & 待补充

**答得不错的**：Q1（项目全貌）、Q3（调参方法论，能说出反直觉实验的归因）、Q11-Q12（RDMA 分层原理 + peermem 排查）、Q19（PD 配比，有完整实测数据支撑）。

**明显缺口，需要补**：

- [ ] **Q18 MCP 长任务 / 异步支持**：progress notification、Streamable HTTP、`Mcp-Session-Id`、`Last-Event-ID`、elicitation、Tasks；对比 A2A 的 task 生命周期 + push notification
- [ ] **Q15 A2A 协议细节**：Agent Card、Task 状态机、Artifact 增量产出、认证方式
- [ ] **Q17 幂等性**：Idempotency Key 模式、MCP tool annotation 的 `idempotentHint` / `destructiveHint`
- [ ] **Q14 Agentic RL**：GRPO / DAPO / GSPO 的差异，veRL 的架构，weight resharding，partial rollout
- [ ] **Q6 KV Cache 结构**：把"链表 + 数组"说成完整的"数组(block table) + 链表(free list) + 树(radix)"三件套，并区分内部碎片 vs 外部碎片
- [ ] **Q8/Q9 RDMA 实测速率**：补上具体 GB/s 数字（和商汤面经 Q9 同一个待补项）
- [ ] **Q13 HiCache**：整理线上 prefix cache 命中率数据，作为是否上 HiCache 的决策依据

**面试官倾向判断**：技术深度问得很细（RDMA 一路追到"完成标志够不够""经不经过 CPU"），并且明显在往 **Agent Infra / RL 环境**方向引。这个岗位对推理侧的深度是认可的，但**最终考察点是能不能迁移到 Agent 侧**。所以补 Agent 协议 + RL 框架的优先级最高。

**关联笔记**：[[kimi2.6 PD分离部署记录]] · [[DeepSeek-Flash-0731 SGLang 的PD分离部署]] · [[Infra/PD分离]] · [[秋招/面经/商汤 大模型系统工程师面经]]
