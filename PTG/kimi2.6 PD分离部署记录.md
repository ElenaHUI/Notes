# 文档

官网

[https://docs.sglang.io/docs/advanced_features/server_arguments#pd-disaggregation](https://docs.sglang.io/docs/advanced_features/server_arguments#pd-disaggregation)

# 配置输入

[vLLM PD 分离](https://alidocs.dingtalk.com/i/nodes/Amq4vjg890G07Kpwu2Xzql47J3kdP0wQ?cid=3939817874%3A5685869479&utm_source=im&utm_scene=team_space&iframeQuery=utm_medium%3Dim_card%26utm_source%3Dim&utm_medium=im_card&corpId=ding5f9a690be26948824ac5d6980864d335)

[https://aliyuque.antfin.com/alinpu_engineering/snxi21/cngf3gf1bscfu2x9](https://aliyuque.antfin.com/alinpu_engineering/snxi21/cngf3gf1bscfu2x9)

[https://help.aliyun.com/zh/ack/ack-lingjun-managed-clusters/user-guide/ack-lingjun-pod-using-rdma?scm=20140722.S_help%40%40%E6%96%87%E6%A1%A3%40%402869336._.ID_help%40%40%E6%96%87%E6%A1%A3%40%402869336-RL_%E7%81%B5%E9%AA%8F-LOC_doc%7EUND%7Eab-OR_ser-PAR1_6a0b3eeb17775182852761122d0099-V_4-PAR3_o-RE_new11-P0_10-P1_0&spm=a2c4g.11174283.help-search.i20](https://help.aliyun.com/zh/ack/ack-lingjun-managed-clusters/user-guide/ack-lingjun-pod-using-rdma?scm=20140722.S_help%40%40%E6%96%87%E6%A1%A3%40%402869336._.ID_help%40%40%E6%96%87%E6%A1%A3%40%402869336-RL_%E7%81%B5%E9%AA%8F-LOC_doc%7EUND%7Eab-OR_ser-PAR1_6a0b3eeb17775182852761122d0099-V_4-PAR3_o-RE_new11-P0_10-P1_0&spm=a2c4g.11174283.help-search.i20)

尝试走机内ICN配置

设置这两个环境变量就行了 MC_FORCE_MNNVL=1 MC_USE_NVLINK_IPC=1

运行的时候如何检查是否真正走了icn link呢

MC_LOG_LEVEL=TRACE

这个可以看mooncake的详细log，应该会有对应的register memory: addr之类的log

P 端

CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 SGLANG_MOONCAKE_CUSTOM_MEM_POOL=True MC_NUM_QP_PER_EP=4 MC_FORCE_MNNVL=1 SAIL_SGL_DEEPEP_RECV_HOOK=0 SAIL_SGL_DEEPEP_ICN=1 SGLANG_DEEPEP_NUM_MAX_DISPATCH_TOKENS_PER_RANK=512 MC_TE_METRIC=1 MC_LOG_LEVEL=TRACE python3 -m sglang.launch_server --trust-remote-code --host 0.0.0.0 --port 8100 --model-path /ppusw/datasets/checkpoints/LLM/qwen/v3.5/Qwen3.5-397B-A17B-INT8 --tp-size 8 --attention-backend fa3 --page-size 64 --disable-radix-cache --trust-remote-code --watchdog-timeout 3600 --dist-timeout 3600 --log-level info --enable-metrics --enable-cache-report --disable-custom-all-reduce --disable-shared-experts-fusion --disaggregation-ib-device mlx5_bond_0,mlx5_bond_1,mlx5_bond_2,mlx5_bond_3,mlx5_bond_4,mlx5_bond_5,mlx5_bond_6,mlx5_bond_7 --disaggregation-mode prefill --mem-fraction-static 0.9 --quantization w8a8_int8

D 端：

CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 SGLANG_MOONCAKE_CUSTOM_MEM_POOL=True MC_NUM_QP_PER_EP=4 MC_FORCE_MNNVL=1 SAIL_SGL_DEEPEP_RECV_HOOK=0 SAIL_SGL_DEEPEP_ICN=1 SGLANG_DEEPEP_NUM_MAX_DISPATCH_TOKENS_PER_RANK=512 MC_TE_METRIC=1 MC_LOG_LEVEL=TRACE python3 -m sglang.launch_server --trust-remote-code --host 0.0.0.0 --port 12100 --model-path /ppusw/datasets/checkpoints/LLM/qwen/v3.5/Qwen3.5-397B-A17B-INT8 --tp-size 8 --attention-backend fa3 --page-size 64 --disable-radix-cache --trust-remote-code --watchdog-timeout 3600 --dist-timeout 3600 --log-level info --enable-metrics --enable-cache-report --disable-custom-all-reduce --disable-shared-experts-fusion --disaggregation-ib-device mlx5_bond_0,mlx5_bond_1,mlx5_bond_2,mlx5_bond_3,mlx5_bond_4,mlx5_bond_5,mlx5_bond_6,mlx5_bond_7 --disable-radix-cache --disaggregation-mode decode --cuda-graph-max-bs 128 --enable-expert-distribution-metrics --mem-fraction-static 0.7 --moe-a2a-backend deepep --dp-size 8 --enable-dp-lm-head --deepep-mode low_latency --enable-dp-attention --prefill-round-robin-balance --moe-dense-tp-size 1 --quantization w8a8_int8

main server：

python -m sglang_router.launch_router --pd-disaggregation --host 0.0.0.0 --mini-lb --port 8999 --prefill [http://sh01t-swu27.eng.t-head.cn:8100](http://sh01t-swu27.eng.t-head.cn:8100) --decode [http://sh01t-swu28.eng.t-head.cn:12100](http://sh01t-swu28.eng.t-head.cn:12100)

李祎凡

CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15 PYTHONUNBUFFERED=1 SGL_ENABLE_JIT_DEEPGEMM=1 python3 -m sglang.launch_server --trust-remote-code --host 0.0.0.0 --port 8100 --model-path /ppusw/datasets/checkpoints/LLM/qwen/v3.0/Qwen3-235B-A22B-Instruct-2507-W8A8-INT8 --tp-size 16 --attention-backend fa3 --disable-radix-cache --context-length 16384 --enable-dp-attention --dp-size 16 --quantization w8a8_int8 --trust-remote-code --max-running-requests 1024 --watchdog-timeout 3600 --dist-timeout 3600 --log-level info --enable-cache-report --disaggregation-transfer-backend mooncake --disaggregation-mode prefill --mem-fraction-static 0.92 --disable-shared-experts-fusion

CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15 PYTHONUNBUFFERED=1 SGL_ENABLE_JIT_DEEPGEMM=1 SAIL_SGL_DEEPEP_ICN=1 SGLANG_DEEPEP_NUM_MAX_DISPATCH_TOKENS_PER_RANK=512 SGL_DEEP_EP_RECV_HOOK=False python3 -m sglang.launch_server --trust-remote-code --host 0.0.0.0 --port 12100 --model-path /ppusw/datasets/checkpoints/LLM/qwen/v3.0/Qwen3-235B-A22B-Instruct-2507-W8A8-INT8 --tp-size 16 --attention-backend fa3 --disable-radix-cache --context-length 16384 --enable-dp-attention --dp-size 16 --quantization w8a8_int8 --trust-remote-code --max-running-requests 1024 --watchdog-timeout 3600 --dist-timeout 3600 --log-level info --enable-cache-report --disaggregation-transfer-backend mooncake --moe-dense-tp-size 1 --prefill-round-robin-balance --chunked-prefill-size 163840 --enable-dp-lm-head --decode-log-interval 50 --mem-fraction-static 0.8 --schedule-conservativeness 0.3 --load-balance-method auto --cuda-graph-bs 1 2 3 4 5 6 7 8 10 12 14 16 18 20 22 24 26 28 30 32 40 48 56 64 --moe-a2a-backend deepep --deepep-mode low_latency --disable-radix-cache --disaggregation-mode decode'

PREFILL_DP_SIZE=1 DECODE_DP_SIZE=16 python -m sglang_router.launch_router --pd-disaggregation --host 0.0.0.0 --mini-lb --port 8999 --prefill [http://na131t-swu139.eng.t-head.cn:8100](http://na131t-swu139.eng.t-head.cn:8100) --decode [http://na131t-swu199.eng.t-head.cn:12100](http://na131t-swu199.eng.t-head.cn:12100)

# Docker部署

[kimi-Docker部署](https://alidocs.dingtalk.com/i/nodes/y20BglGWO2d2oKE5s0nBwk6j8A7depqY)

# 问题

## 问题1: RuntimeError: q_v is only supported for Hopper GPUs

decode节点会报错，至文说你碰到过了，请问需要如何处理

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde537024e4aa570f2781f00ae151cbfa7eb75b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d5bb044b3671ec6295641413a6d4196afadf7c7163a36ca42ae32d6660a03f14703716e209d665a4e1?tmpCode=328f863f-090e-45de-9f25-3a9b26af4151)

这个是 fa3 内部不支持的问题，现在 kimi / glm5 / dpsk v32 设置 --attention-backend fa3 都会有这个错误

需要把 --attention-backend fa3 换成 --decode-attention-backend flashmla --prefill-attention-backend fa3

## 问题2: assert m == m_ and n == n_ and k == k AssertError

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde537024e4aa570f2781f00ae151cbfa7eb75b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d5cc87af9123659186baf241439a90f73b320088687c33d8a648d3807c3d63bd991c25f921ffffc45f?tmpCode=328f863f-090e-45de-9f25-3a9b26af4151)

解决方法：

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde537024e4aa570f2781f00ae151cbfa7eb75b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d5fde5e222027e2ff0ecdf58afeb7613798ddc14b8fc678faebb80a7c321e6ee6ff231a9e02ba3bd6b?tmpCode=328f863f-090e-45de-9f25-3a9b26af4151)

这两个要删掉，w4a8 不支持开 ep

## 问题3: RDMA通信异常

[Kimi-K2.6 PD分离部署通信异常问题定位报告](https://alidocs.dingtalk.com/i/nodes/ndMj49yWjXnXREO6TwRw90bZJ3pmz5aA)

## 问题4: Warmup failed: KeyError 'choices'（context-length 不足）

### 症状

`sglang.bench_serving` 跑 vLLM/sglang 后端时，warmup 阶段直接失败，rc=1，stderr 末尾形如：

`ValueError: Warmup failed - Please make sure benchmark arguments are correctly specified. Error: Traceback (most recent call last):   File ".../sglang/bench_serving.py", line 300, in async_request_openai_completions     if data["choices"][0]["text"]:        ~~~~^^^^^^^^^^^ KeyError: 'choices'`

伴随的 CUDA / NVML warning 是误导项——`bench_serving` 是纯客户端，本身不需要 GPU，可以忽略。

### 根因

服务端启动时配置的最大上下文长度小于本次压测请求长度，server 直接以错误 JSON（不含 `choices` 字段）拒绝请求，客户端在解析 warmup 响应时抛 `KeyError: 'choices'`。

本次现场：

- 启动参数：`--context-length 16384`
    
- 压测参数：`--random-input-len 65536 --random-output-len 1536`（合计约 67K，远大于 16384）
    
- 把 `--random-input-len` 调小到 ≤ 16384 - output_len 后即正常。
    

### 排查方法

1. 直接 curl 服务端，看真实返回，错误响应通常会明确写 `maximum context length` 之类的信息：
    
2. 把 `--random-input-len` 临时降到很小（如 4096）重跑，能跑通就基本锁定是 context 长度问题。
    

### 解决

- 服务端：启动 vLLM/sglang 时把 `--context-length`（或 vLLM 的 `--max-model-len`）调到 ≥ `random-input-len + random-output-len`，并预留余量；同时确认 KV cache 显存够用。
    
- 客户端：本次跑的 input/output 长度不能超过服务端实际支持的 context 上限。
    

### 同类陷阱（同样表现为 `KeyError: 'choices'`）

- `--served-model-name` 与服务端注册名不一致，server 回 `model not found`。
    
- 服务端权重加载失败 / KV cache OOM，请求直接 5xx。
    

排查时先 curl 一次拿到原始错误体即可区分。

## 问题5: 通信速率低，怀疑RDMA通信未生效

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde537024e4aa570f2781f00ae151cbfa7eb75b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d5d9381773282cf5004ce600da3cfb390b2179fb300e21d02a7a5996f3e980ec6f70ddd684740ac4ad?tmpCode=328f863f-090e-45de-9f25-3a9b26af4151)

1P1D 短序列测试正常；但是长输入ttft非常差。

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde537024e4aa570f2781f00ae151cbfa7eb75b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d5311bfaa9f6cb131a4264c39e6a0d7f929b00e632d43d1ede70c87a6bcbe88ca9556de7a2f824c3bf?tmpCode=328f863f-090e-45de-9f25-3a9b26af4151)

查看P节点的日志 Transfer Engine Stats (over last 5s): Throughput: 34.31 MB/s ，这个只有20～30MB/s。实测两台host机器的RDMA通信速率在300GB/s以上。

[https://project.aone.alibaba-inc.com/v2/project/996329/bug/82636009#](https://project.aone.alibaba-inc.com/v2/project/996329/bug/82636009#) 《1P1D部署Kimi-K2.6，1P1D 短序列测试正常,但是长输入ttft非常差》

开发定位结论：

配置基本都排查了，gid，lid，mtu，也比对了，看起来都正常。Mooncake的log里面能看到拓扑发现成功，mooncake列出来的网卡的信息我也check了一下，idx和gid也都是正确的

根据胡超的建议，去除P节点的dp参数后，Throughput增加了十倍

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde537024e4aa570f2781f00ae151cbfa7eb75b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d519aa80e449f5e53740069377ef72363f8a571727af05a69e7f537885a247b5249808f13ff274fb21?tmpCode=328f863f-090e-45de-9f25-3a9b26af4151)

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde537024e4aa570f2781f00ae151cbfa7eb75b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d5ac65eeba0a7ea89f28bffa4b232adb7c0d1c514ff413366f21550bf88fd0c79a8bdee7ceaf1f8bd5?tmpCode=328f863f-090e-45de-9f25-3a9b26af4151)

# 对比测试

## K8S 1P1D对比 Host 1P1D（ 短序列）

## ![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde537024e4aa570f2781f00ae151cbfa7eb75b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d50d595d736262af9605c9724368374d7703a389f9336ab197f96dfd55f130b75ddff39bf56741dd88?tmpCode=328f863f-090e-45de-9f25-3a9b26af4151)

## K8S 1P1D对比 Host 1P1D（ 长序列）

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde537024e4aa570f2781f00ae151cbfa7eb75b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d5d8d710b9058ae3496d401bc264a70194fbefba2c952cc78659053b5eafd7ef657c40cbbeb47d4d65?tmpCode=328f863f-090e-45de-9f25-3a9b26af4151)

## K8S 1P1D对比K8S 2P1D（ 短序列）

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde537024e4aa570f2781f00ae151cbfa7eb75b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d59020c7f73fa549bb1f8b82a41af401ba4825e0ec1788a5d13d7e15635e1ea2e09a38c95236605983?tmpCode=328f863f-090e-45de-9f25-3a9b26af4151)

## K8S 1P1D对比K8S 2P1D（ 长序列）

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde537024e4aa570f2781f00ae151cbfa7eb75b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d5f9734546ae08f920a9a4115a8d2278995db98ee847d4688eccab850a4873203d313d51b1e0eeafc0?tmpCode=328f863f-090e-45de-9f25-3a9b26af4151)

到20并发，2P的优势就明显了

tpot依然稳定。可以对比测试3P1D。

## K8S 3P1D对比K8S 2P1D（ 长序列）

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde537024e4aa570f2781f00ae151cbfa7eb75b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d50e3260b281b019f6a3d17596e72471e5358581f575fda77daace39039314085b4ddbf6c06c11c4dc?tmpCode=328f863f-090e-45de-9f25-3a9b26af4151)

3P1D 20并发确实好ttft好很多，tpot只是微升

## K8S 3P1D对比K8S 3P2D（ 长序列）

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde537024e4aa570f2781f00ae151cbfa7eb75b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d56ad15fe485a241f95673cdd200440d2c5ed097744b5dd50d006cc83b09a245bab91219ab8a48651d?tmpCode=328f863f-090e-45de-9f25-3a9b26af4151)

生产3P2D测试数据

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde537024e4aa570f2781f00ae151cbfa7eb75b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d59a247a20bfe702b308c5b9f283bd7336f6599af1b03f41b1cf0278bd3f10c02daeeec56c439ab0bb?tmpCode=328f863f-090e-45de-9f25-3a9b26af4151)

## Router 4核8G 对比 64核128G

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde537024e4aa570f2781f00ae151cbfa7eb75b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d512b627d9e3c35f7ea79ed04b22ec7fc193b19c44e82bbf3c58a6a2a4812267c71332d9efc14ea3c3?tmpCode=328f863f-090e-45de-9f25-3a9b26af4151)

结论：数据看没影响

Router 路由机制

```
 要点：

  1. 调度选 P 是 router 干的。开启 --policy cache_aware（或新版的 cache_aware_routing）时，router 会按 token
  化后的请求前缀去匹配自己维护的"每个 worker 缓存了哪些前缀"的近似树，挑命中最长的那台 P。这个树是 router
  通过观察请求流量推断出来的，不会去实时拉 P 节点的真实 cache 状态。
  2. router 上的树是"近似"，不是 ground truth。它会有偏差（被驱逐的前缀 router 不一定知道），所以 router
  还会结合负载均衡（请求队列长度、in-flight 数）做权衡，避免热点。
  3. 真正命中 KV 复用是在被选中的 P 节点上。P 节点拿到请求后，再用自己真实的 radix cache 做一次精确前缀匹配，复用已有的 KV
  block，只对未命中的尾部做 prefill。
  4. D 节点不参与。decode 节点没有调度选择问题，KV 由 P 通过 disaggregation 通道传过来。

  所以记忆口诀：router 决定"去哪台 P"，P 决定"复用多少 KV"。
```

Router 近似前缀树 资源消耗分析

```
Router 近似前缀树到底吃多少内存？
SGLang router（sglang-router-rs）是 Rust 实现的，整体内存比 Python 推理框架小很多。主要消耗分四块：
┌───────────────────────────┬─────────────┬────────────────────────────────────────────────────────────────────────────────────┐
 │ 项 │ 量级 │ 说明 │
 ├───────────────────────────┼─────────────┼────────────────────────────────────────────────────────────────────────────────────┤
 │ 近似 radix tree │ 1–3 │ 所有 P worker 共享一棵带 worker 标签的树，由 --max-tree-size（默认 2^24 ≈ 16M │
 │ │ GB（典型） │ 节点）封顶；每个节点 ~50–100B（token + 父子指针 + worker bitset + 时间戳） │
 ├───────────────────────────┼─────────────┼────────────────────────────────────────────────────────────────────────────────────┤
 │ Tokenizer │ 200–500 MB │ 看 vocab 大小，Llama3/Qwen 词表 ≥128K 会偏大 │
 ├───────────────────────────┼─────────────┼────────────────────────────────────────────────────────────────────────────────────┤
 │ Rust runtime + HTTP │ 500 MB–1 GB │ 请求队列、metrics、连接池 │
 │ server + in-flight buffer │ │ │
 ├───────────────────────────┼─────────────┼────────────────────────────────────────────────────────────────────────────────────┤
 │ 碎片 + headroom │ 500 MB–1 GB │ jemalloc/mimalloc 碎片，长跑会累积 │
 └───────────────────────────┴─────────────┴────────────────────────────────────────────────────────────────────────────────────┘
8Gi 够不够？看你的负载
● ✅ 中等 QPS（< 1k）+ 上下文 ≤ 32K：够。稳态 RSS 一般 2–4 GB，8Gi 有足够 headroom。
● ⚠️ 长上下文（128K / 256K）或 高 QPS：偏紧。长 prompt 让树膨胀飞快，建议 12–16 Gi。
● ⚠️ 常驻不重启（多周）：碎片会慢慢吃内存，建议留 30–40% headroom。
比加内存更值得先做的调参
1. --max-tree-size N —— 直接封顶树节点数，超了走 LRU 驱逐。先压低这个值最立竿见影。
2. --eviction-interval-secs（默认 60）—— 调短让冷 prefix 更早释放。
3. --cache-threshold（默认 0.5）—— 低于这个命中比就视作没命中、不写树，能减少树膨胀。
4. 建立 RSS 基线：kubectl top pod 或容器内 cat /proc/1/status | grep VmRSS，跑 1–2 周看曲线再决定扩容。
CPU 4 核
router 是 tokenization + tree lookup 主导，4 核在 1–2k QPS、prompt 平均 ≤ 8K token 通常够。如果 prompt 长且 QPS 高，tokenization
 会先成瓶颈 —— 这时加 CPU 比加内存更有用。
```

## cni0 flannel 的mtu设置 1450 VS 8950

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde537024e4aa570f2781f00ae151cbfa7eb75b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d5290974216f9a27ed7636861030ad2bf5e044c68d2a8f0355c30a4be5e0f4bf923fcde2d70840b499?tmpCode=328f863f-090e-45de-9f25-3a9b26af4151)

## 去除hostNetWork测试

报错

## mini-lb vs sgl-router (3P1D)

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde537024e4aa570f2781f00ae151cbfa7eb75b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d52edf71a5519e41b833cd2060ff87ff8ce588b1726086dddc99dd12a41ae3c350b9939b85c4e97c21?tmpCode=328f863f-090e-45de-9f25-3a9b26af4151)

## sglang-router +缓存命中 vs mini-lb+disable-radix-cache

{

"10.244.7.15": ["[http://11.159.106.181:31768/v1/chat/completions](http://11.159.106.181:31768/v1/chat/completions)"],

"10.244.6.67":["[http://11.159.106.181:31768/v1/chat/completions](http://11.159.106.181:31768/v1/chat/completions)"],

"10.244.14.175":["[http://11.159.106.181:31768/v1/chat/completions](http://11.159.106.181:31768/v1/chat/completions)"]

}

### 去除DEEPEP参数，配置MC_NUM_QP_PER_EP=8, 1P1D 对比

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde537024e4aa570f2781f00ae151cbfa7eb75b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d5206748ac9722f3e890009d29e96ce269a0955d67a5f53319f083a2ba7037545088d7f93e163e5897?tmpCode=328f863f-090e-45de-9f25-3a9b26af4151)

1P（16卡）只能撑住10并发。

### MC_USE_NVLINK_IPC=1

强制 Mooncake 在同一台服务器内部进行数据传输时，使用基于 NVLink 的 IPC（进程间通信）机制，而非 PCIe P2P 或共享内存拷贝。

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde537024e4aa570f2781f00ae151cbfa7eb75b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d5118cc18d383301ce43356a6b329d9592751745fe4b36c2e12386f89c8a647e5ab7435268ef900c06?tmpCode=328f863f-090e-45de-9f25-3a9b26af4151)

看来D节点内卡间通信走的就是ICN

### Decode设置TP-size=8, DP-size=2

### ![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde537024e4aa570f2781f00ae151cbfa7eb75b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d59870371a5de3263cef404835d60285861ca10e8c7944800866f9af89a8d8ead82d7c4f5259d87655?tmpCode=328f863f-090e-45de-9f25-3a9b26af4151)

奇怪ttft竟然变差了

### moe-dense-tp-size 设置为4

报错只能是1或者None

这是 SGLang 当前实现的限制，moe-dense-tp-size 目前只支持 1 或 None（等同于 1）。

原因

1. 实现复杂度
    

moe-dense-tp-size > 1 意味着要在 DP Attention 模式下，把 GPU 分成子组做 Attention 的 Tensor Parallel。这需要：

- 额外的 NCCL 通信组（子组内 all-reduce）
    
- Attention 权重按子组切分
    
- KV cache 在子组间的管理逻辑
    

SGLang 目前只实现了 moe-dense-tp-size=1（每卡独立算 attention）这一条路径。

### remove decode dp

--enable-dp-attention \

--dp-size 1 \

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde537024e4aa570f2781f00ae151cbfa7eb75b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d503a5aef75dd070cd25e056469a33443f64a1231566b21df5523b5f2b3030d39623ad52d7e9a4029a?tmpCode=328f863f-090e-45de-9f25-3a9b26af4151)

传统 TP（不用 DP Attention）

所有 16 卡协同处理同一批 tokens，不管是 Attention 还是 MoE 层：

Attention: 16卡 Tensor Parallel → 需要 all-reduce 通信 MoE FFN: 16卡 Tensor Parallel → 需要 all-reduce 通信

开启 DP Attention 后（dp-size=16, moe-dense-tp-size=1）

Attention: 每张卡独立处理各自的请求（Data Parallel, 无通信） MoE FFN: 16卡 Expert Parallel → all-to-all 通信（DeepEP）

关键等式：tp-size = dp-size × moe-dense-tp-size，即 16 = 16 × 1

- Attention 层：每张 GPU 独立处理自己分到的请求，完全无通信开销
    
- MoE 层：所有 16 张 GPU 通过 Expert Parallelism 协作，tokens 通过 all-to-all（DeepEP）路由到对应 expert
    

为什么 Decode 适合这么做？

Decode 阶段每步每个请求只处理 1 个 token，Attention 计算量极小（1 个 query token vs KV cache），用 16 卡 TP 来算一个 token 的 attention 是严重浪费。改成 DP 后，每张卡独立算自己负责的请求的 attention，零通信，效率大幅提升。

当前 D 节点 dp-size=16 是标准且合理的选择，原因：

1. Decode 阶段 attention 计算量极小，不需要 TP 来分摊
    
2. DP=16 意味着 16 路数据并行，能同时服务更多请求
    
3. moe-dense-tp-size=1 消除了 attention 层的 all-reduce 通信
    
4. MoE 层仍然有 16 卡的 Expert Parallelism，expert 覆盖充分
    

一般规则：对于 Decode 节点，dp-size 尽量等于 tp-size（即 dense_tp=1）。只有当单卡显存放不下完整的 attention 参数（如模型 attention head 特别多、hidden dim 特别大）时，才需要降低 dp-size、提高 dense_tp。Kimi-K2.6 用 W4A8 量化后，单卡放 attention 参数绑绑有余，所以 dp=16 没问题。

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde537024e4aa570f2781f00ae151cbfa7eb75b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d57d6699015c56cf899ba18bc420d8127a97fa819127a775d543291c3b810058e41f725db89f04db3e?tmpCode=328f863f-090e-45de-9f25-3a9b26af4151)

W4A8 量化的影响

- W4：所有权重（attention、MoE expert、embedding、LM head）都量化到 4-bit 存储，显存占用约为 FP16 的 1/4
    
- A8：激活值（运行时中间结果）使用 INT8 计算，加速 GEMM
    
- 量化后 MoE expert 参数虽然占比最大，但因为 W4 压缩 + EP 分布在 16 卡上，每卡实际存储量可控
    
- MLA 的 KV cache 本身就是压缩表示，再加上量化，Decode 阶段显存效率很高
    

这就是为什么 moe-dense-tp-size=1 可行 — 非 MoE 参数（attention + embedding + norm）量化后单卡完全放得下。

### --cuda-graph-bs 1 2 3 4 5 6 7 8 10 12 14 16 18 20 22 24 26 28 30 32 40 48 56 64

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde537024e4aa570f2781f00ae151cbfa7eb75b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d54e786b9b5d37ab320b663a9bf06f3367ddb821052374fd50d8375711320e8a30f6f944991f7b48da?tmpCode=328f863f-090e-45de-9f25-3a9b26af4151)

至少对我的压测没啥效果

# 上线配置

### 服务配置

|   |   |   |   |
|---|---|---|---|
|组件|副本数|ppu卡||
|sglang-router|2|0|开启kv aware|
|prefill|3|48|打开radix-cache|
|docode|2|32|dp-size=16|

### 升级镜像到sglang0.5.12

[https://aliyuque.antfin.com/alinpu_engineering/snxi21/reii905d1sec10uf](https://aliyuque.antfin.com/alinpu_engineering/snxi21/reii905d1sec10uf)

### 上线流量分析（3P2D）

周六流量分析

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde537024e4aa570f2781f00ae151cbfa7eb75b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d54d6d99fed0b2656c8cb6d6fa2678ad89192f52d4242efeea9ae9396b1c4b5b816e9914f7c1628841?tmpCode=328f863f-090e-45de-9f25-3a9b26af4151)

- Decode并发综合数和TPOT的曲线很一致，又完整的正相关性。
    
- 并发达到30，TPOT会上升到60ms
    
- ttfp平均2～3s