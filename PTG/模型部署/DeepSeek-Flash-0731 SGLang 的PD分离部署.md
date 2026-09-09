## 一、部署架构：DGD + PD 分离

你这次用的是 **DynamoGraphDeployment（DGD）** 方式部署，而不是普通 Deployment + `sglang.launch_server`。
![[Pasted image 20260828153229.png]]

|组件|说明|
|---|---|
|CRD|`nvidia.com/v1alpha1` / `kind: DynamoGraphDeployment`|
|后端框架|`backendFramework: sglang`，实际入口 `python -m dynamo.sglang`|
|版本|sglang 0.5.16 + dynamo 1.3.1|
|Worker 结构|两个 Worker，各 1 副本、8 卡 PPU|
|Prefill Worker|端口 8100，`--disaggregation-mode prefill`|
|Decode Worker|端口 8101，`--disaggregation-mode decode`|
|服务发现|`DYN_DISCOVERY_BACKEND=etcd`|
|事件面|`DYN_EVENT_PLANE=nats`|
|GPU 拓扑|`GPU_TOPOLOGY_ANNOTATION` 读取|
|RDMA 资源|请求 `rdma/hca: 4`|
|节点亲和|PPU + `board.type=810e`|

---

## 二、让服务跑通的关键：extraPodSpec 里的 host 网络模式

你加的这段配置是关键：

```
extraPodSpec:  hostNetwork: true  hostPID: true  hostIPC: true  dnsPolicy: ClusterFirstWithHostNet
```

为什么必须加？

|配置|作用|
|---|---|
|`hostNetwork: true`|Pod 直接使用宿主机网络命名空间，Mooncake 的 RDMA/IB 通信才能正常访问 `mlx5_bond_*` 网卡和宿主机网络栈。|
|`hostPID: true`|让 Pod 能看到宿主机进程，便于 RDMA/GPU 拓扑发现和 IPC。|
|`hostIPC: true`|共享宿主机 IPC 命名空间，对 RDMA 共享内存、GDR 等有帮助。|
|`dnsPolicy: ClusterFirstWithHostNet`|配合 `hostNetwork=true` 时，Pod 仍能用集群 DNS 解析 etcd/nats 等服务。|

**结论**：不加 host 网络模式时，Mooncake 没法正确初始化 RDMA 设备或 fallback 到低效路径，导致模型跑不通或 TTFT 极高。

---

## 三、我做的参数调优

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde51201f1430917b7315cb6db047757adaa75b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d5bbc19fd24a1fe8b7114ffa9525fd35f131366517ace7c2fe84103a20551940703596ad4008c74d1f?tmpCode=10b846e7-7f65-415e-b512-ef8ab00c9ec8)

### 1. 去掉三个性能开关的 disable

P 节点和 D 节点都把这三行删掉：

```
--disable-custom-all-reduce      # 开启 custom all-reduce，降低 TP 通信延迟
--disable-radix-cache            # 开启 radix cache，命中共享 prefix
--disable-shared-experts-fusion  # 开启 shared expert 融合
```

效果：TTFT/TPOT 都明显变好。

### 2. P 节点保留 Context Parallel，不能开 dp-size > 1

P 节点原始 CP 配置：

```
--enable-nsa-prefill-context-parallel
--nsa-prefill-cp-mode round-robin-split
--attn-cp-size 8
```

尝试加 `--dp-size 8` 时报错：

```
AssertionError: For round-robin split mode, dp attention is not supported.
```

**结论**：sglang 0.5.16 里，`round-robin-split CP` 模式下 `dp-size` 必须为 1。所以 P 节点不能加 `--dp-size 8`。

### 3. D 节点保持原样

D 节点可以继续用：

```
--tp-size 8
--dp-size 8
--enable-dp-attention
--enable-dp-lm-head
```

---
![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde51201f1430917b7315cb6db047757adaa75b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d5bf4e6c163b95d162953dbfe31095725bcc7ad1ac2efa512463b70c46006cc0c413ba2cc005165be9?tmpCode=d56a537c-f749-4faf-8e85-3213d49d7783)
![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde51201f1430917b7315cb6db047757adaa75b8339e1c4c2483f35a8ff3f0692652d08509556868857aa156a98577f418d52c7f2fe81754bdff2764ef40b486680b6fab06c7f791608ee0ebf4c17ac75c2a946710875ca44ec9?tmpCode=e4349e19-68c5-4ef6-a818-458823469dd6)

---

## 四、当前已确认可运行的最小配置

### P 节点

```
--tp-size 8
--quantization w8a8_int8
--attention-backend nsa
--nsa-prefill-backend flashmla_sparse
--enable-nsa-prefill-context-parallel
--nsa-prefill-cp-mode round-robin-split
--attn-cp-size 8
# 不要加 --dp-size 8
# 不要加 --enable-dp-attention
```

### D 节点

```
--tp-size 8
--dp-size 8
--attention-backend nsa
--nsa-decode-backend flashmla_kv
--enable-dp-attention
--enable-dp-lm-head
```

### 两个节点共同

```
# 这三个 disable 都去掉
# --disable-custom-all-reduce
# --disable-radix-cache
# --disable-shared-experts-fusion

--disaggregation-transfer-backend mooncake
--disaggregation-ib-device mlx5_bond_1,mlx5_bond_2,mlx5_bond_3,mlx5_bond_4
```

### K8s 部署

```
extraPodSpec:  hostNetwork: true  hostPID: true  hostIPC: true  dnsPolicy: ClusterFirstWithHostNet
```

---

## 五、后续还可以尝试的优化

现在服务已经跑通，但基于你的长文本 workload（平均 80K+ input），还可以继续提升：

1. **P 节点加 `--ep-size 8`**：降低 MoE all-to-all 通信，长文本 prefill 收益大。
2. **检查 Mooncake GDR**：确认 RDMA 走 GPU Direct，而不是 CPU copy。
3. **D 节点 `--ep-size 8`**：Decode 也可以加，但当前输出短，收益不如 P 节点明显。
4. **调整 `max-running-requests`**：长文本场景下 1024 可能偏大，可以降到 512 或 256 减少调度抖动。