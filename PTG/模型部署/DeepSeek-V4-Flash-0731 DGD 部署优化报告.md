## 一、概述

本次优化将 DeepSeek-V4-Flash-0731 的部署从普通 Deployment 升级为 **DynamoGraphDeployment（DGD）**，实现 Prefill/Decode 分离。通过调整 sglang 参数和 K8s Pod 网络模式，解决了 Mooncake RDMA 初始化失败、TTFT 过高等问题，显著提升了服务稳定性。

## 二、优化前问题分析

| 问题 | 表现 | 根因 |
|---|---|---|
| 模型服务启动异常 / TTFT 极高 | Mooncake 无法初始化 RDMA 设备 | Pod 未使用 host 网络模式，无法访问宿主机 `mlx5_bond_*` 网卡 |
| 性能未达预期 | TTFT/TPOT 偏高 | 三个关键性能开关被 disable：custom all-reduce、radix cache、shared-experts-fusion |
| 参数冲突 | P 节点加 `--dp-size 8` 报错 | sglang 0.5.16 中 `round-robin-split CP` 与 `dp-size > 1` 不兼容 |
| 部署方式 | 普通 Deployment | 不支持 DGD 的双 Worker 编排和自动服务发现 |

## 三、优化方案

### 1. 部署方式升级
- 使用 `DynamoGraphDeployment` CRD 编排 Prefill/Decode 两个 Worker。
- 配置 `etcd` 服务发现、`NATS` 事件面、`GPU_TOPOLOGY_ANNOTATION` 读取 GPU 拓扑。

### 2. Pod 网络模式
- 添加 `hostNetwork: true`、`hostPID: true`、`hostIPC: true`、`dnsPolicy: ClusterFirstWithHostNet`，确保 Mooncake 能直接访问宿主机 RDMA 设备。

### 3. sglang 参数优化
- **P/D 节点都去掉**：
  - `--disable-custom-all-reduce`
  - `--disable-radix-cache`
  - `--disable-shared-experts-fusion`
- **P 节点**：保留 `round-robin-split CP`，`dp-size` 保持为 1（sglang 限制），去掉 `--enable-dp-attention`。
- **D 节点**：保持 `dp-size 8`、`--enable-dp-attention`、`--enable-dp-lm-head`。

## 四、优化后的完整 DGD 配置

```yaml
apiVersion: nvidia.com/v1alpha1
kind: DynamoGraphDeployment
metadata:
  name: deepseek-v4-flash-0731-pd
  namespace: default
spec:
  backendFramework: sglang
  runtime:
    image: art.eng.t-head.cn/ptgai-docker_ai_service/aisw/llm:v2.1.1-pytorch2.11.0-ubuntu24.04-cuda13.0-sglang0.5.16-py312-dynamo1.3.1-v0.0.2
    imagePullPolicy: IfNotPresent

  # 平台集成：etcd 服务发现、NATS 事件面
  env:
    - name: DYN_DISCOVERY_BACKEND
      value: "etcd"
    - name: DYN_EVENT_PLANE
      value: "nats"
    - name: GPU_TOPOLOGY_ANNOTATION
      value: "true"
    - name: SGLANG_NSA_FLASHMLA_BACKEND_DECODE_COMPUTE_FP8
      value: "0"
    - name: SGLANG_NSA_DUAL_STREAM
      value: "0"

  # host 网络模式：Mooncake RDMA 必需
  extraPodSpec:
    hostNetwork: true
    hostPID: true
    hostIPC: true
    dnsPolicy: ClusterFirstWithHostNet

  workers:
    # ---------------------------------------------------------
    # Prefill Worker
    # ---------------------------------------------------------
    - name: sglang-prefill-worker
      componentType: SglangPrefillWorker
      replicas: 1
      service:
        port: 8100
      resources:
        limits:
          nvidia.com/gpu: "8"
          rdma/hca: "4"
        requests:
          nvidia.com/gpu: "8"
          rdma/hca: "4"
      nodeSelector:
        board.type: "810e"
      affinity:
        podAntiAffinity: {}  # 根据实际调度策略填写
      command:
        - /bin/bash
        - -c
        - |
          echo "Running init-gpu-env.sh..." && \
          source /scripts/init-gpu-env.sh && \
          echo "Current CUDA_VISIBLE_DEVICES: $CUDA_VISIBLE_DEVICES" && \
          source /etc/environment && \
          python -c "import torch;print(torch.cuda.device_count())" && \
          python -m dynamo.sglang \
            --trust-remote-code \
            --host 0.0.0.0 \
            --port 8100 \
            --served-model-name DeepSeek-V4-Flash-0731 \
            --model-path /ppusw/datasets/checkpoints/LLM/deepseek-ai/v1.0/DeepSeek-V4-Flash-0731-w8a8 \
            --tp-size 8 \
            --quantization w8a8_int8 \
            --attention-backend nsa \
            --nsa-prefill-backend flashmla_sparse \
            --enable-nsa-prefill-context-parallel \
            --nsa-prefill-cp-mode round-robin-split \
            --attn-cp-size 8 \
            --enable-metrics \
            --max-running-requests 1024 \
            --watchdog-timeout 3600 \
            --dist-timeout 3600 \
            --log-level info \
            --enable-cache-report \
            --disaggregation-mode prefill \
            --disaggregation-bootstrap-port 8998 \
            --disaggregation-ib-device mlx5_bond_1,mlx5_bond_2,mlx5_bond_3,mlx5_bond_4 \
            --disaggregation-transfer-backend mooncake

    # ---------------------------------------------------------
    # Decode Worker
    # ---------------------------------------------------------
    - name: sglang-decode-worker
      componentType: SglangDecodeWorker
      replicas: 1
      service:
        port: 8101
      resources:
        limits:
          nvidia.com/gpu: "8"
          rdma/hca: "4"
        requests:
          nvidia.com/gpu: "8"
          rdma/hca: "4"
      nodeSelector:
        board.type: "810e"
      affinity:
        podAntiAffinity: {}  # 根据实际调度策略填写
      command:
        - /bin/bash
        - -c
        - |
          echo "Running init-gpu-env.sh..." && \
          source /scripts/init-gpu-env.sh && \
          echo "Current CUDA_VISIBLE_DEVICES: $CUDA_VISIBLE_DEVICES" && \
          source /etc/environment && \
          python -c "import torch;print(torch.cuda.device_count())" && \
          python -m dynamo.sglang \
            --trust-remote-code \
            --host 0.0.0.0 \
            --port 8101 \
            --served-model-name DeepSeek-V4-Flash-0731 \
            --model-path /ppusw/datasets/checkpoints/LLM/deepseek-ai/v1.0/DeepSeek-V4-Flash-0731-w8a8 \
            --tp-size 8 \
            --dp-size 8 \
            --quantization w8a8_int8 \
            --attention-backend nsa \
            --nsa-decode-backend flashmla_kv \
            --enable-dp-attention \
            --enable-dp-lm-head \
            --enable-metrics \
            --max-running-requests 1024 \
            --watchdog-timeout 3600 \
            --dist-timeout 3600 \
            --log-level info \
            --enable-cache-report \
            --disaggregation-mode decode \
            --disaggregation-bootstrap-port 8998 \
            --disaggregation-ib-device mlx5_bond_1,mlx5_bond_2,mlx5_bond_3,mlx5_bond_4 \
            --disaggregation-transfer-backend mooncake
```

> **说明**：DGD 的 CRD 字段名（如 `componentType`、`command`、`resources` 等）可能因实际 Operator 版本略有不同，以上 YAML 结构需要根据你集群中 `DynamoGraphDeployment` 的 OpenAPI 定义微调。

## 五、关键参数解释

| 参数 | 位置 | 作用 |
|---|---|---|
| `hostNetwork: true` | `extraPodSpec` | Pod 使用宿主机网络，Mooncake 可直接访问 IB 网卡。 |
| `hostPID: true` / `hostIPC: true` | `extraPodSpec` | 共享宿主机进程和 IPC 命名空间，辅助 RDMA/GPU 拓扑发现。 |
| `dnsPolicy: ClusterFirstWithHostNet` | `extraPodSpec` | hostNetwork 模式下仍使用集群 DNS。 |
| `rdma/hca: "4"` | resources | 申请 4 个 RDMA HCA，对应 `mlx5_bond_1~4`。 |
| `--disable-*` 去掉 | P/D | 开启 custom all-reduce、radix cache、shared-experts-fusion。 |
| `--enable-nsa-prefill-context-parallel` | P | 长文本 prefill 使用 Context Parallel。 |
| `--nsa-prefill-cp-mode round-robin-split` | P | CP 切分模式，与 `dp-size > 1` 不兼容。 |
| `--enable-dp-attention` / `--dp-size 8` | D | Decode 阶段数据并行 + DP Attention。 |
| `--enable-dp-lm-head` | D | Decode 阶段 LM head 数据并行。 |

## 六、验证结果

- 服务启动成功，Mooncake RDMA 正常初始化。
- 去掉三个 disable 后，TTFT / TPOT / 吞吐均明显改善。
- 长文本 workload（平均 input 80K+）下，P 节点 CP 生效，Cached Tokens 达到 125K–150K。

## 七、踩坑与注意事项

1. **P 节点不能加 `--dp-size 8`**  
   sglang 0.5.16 中 `round-robin-split CP` 与 `dp-size > 1` 冲突，会报：
   ```python
   AssertionError: For round-robin split mode, dp attention is not supported.
   ```
   P 节点必须保持 `dp-size=1`。

2. **hostNetwork 是 Mooncake RDMA 的前提**  
   没有 host 网络模式时，Pod 内无法正确初始化 `mlx5_bond_*` 设备，会 fallback 到 TCP 或 CPU copy。

3. **P/D 节点端口区分**  
   Prefill 用 8100，Decode 用 8101，`--disaggregation-bootstrap-port` 可以相同（用于服务发现握手）。

## 八、后续优化建议

| 优化项 | 预期收益 | 风险 |
|---|---|---|
| P 节点加 `--ep-size 8` | 降低 MoE all-to-all 通信，长文本 prefill 更快 | 中，需实测稳定性 |
| 检查 Mooncake GDR | 避免 CPU copy，降低 P→D KV 传输延迟 | 低，主要是配置检查 |
| D 节点加 `--ep-size 8` | Decode 阶段 MoE 通信优化 | 中 |
| `SGLANG_NSA_DUAL_STREAM=1` | H100/H800 上 decode 吞吐提升 5–15% | 低 |
| 调整 `max-running-requests` | 长文本下降低调度抖动 | 低 |

---

如果你需要，我可以把这份报告导出成 Markdown 文件保存到工作区。