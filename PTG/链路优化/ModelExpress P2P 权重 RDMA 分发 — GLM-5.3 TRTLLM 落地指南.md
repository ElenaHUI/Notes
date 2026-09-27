## 背景与原理

ModelExpress (MX) 是模型权重 P2P RDMA 分发方案。核心思路：
1. **首个 Pod** 按常规方式从宿主机磁盘加载模型权重 → 执行量化/转换 → 写入显存
2. 加载完成后，向 **MX Server** 注册权重元数据（模型名、NIXL 端点、张量布局）
3. **后续 Pod** 启动时查询 MX Server 发现已有 source → 通过 **NIXL/UCX RDMA** 直接从 source Pod 显存拉取 **已转换** 的权重
4. P2P 完成后，新 Pod 也注册自己成为 source，供更多副本使用
**为什么每个节点都有云盘还需要 P2P？** 磁盘加载需要读取原始权重后在 CPU 上执行量化变换，再写入显存。P2P 直接传输 **已在显存中的变换后权重**，跳过 CPU 变换步骤，在 RDMA ~400-500 Gbps 带宽下远快于磁盘读取+CPU 变换。
**TRTLLM 集成方式**：在引擎配置文件（ConfigMap）中添加 `checkpoint_format: MX` + `mx_config.server_url`。TRT-LLM 识别此配置后使用 `MxModelLoader` 替代默认加载器，运行策略链 `rdma → server-cache → model_streamer → gds → default`。**完全不影响** 现有 NIXL KV transfer 配置（两者使用独立的 NIXL Agent 实例）。

---
## 当前基线

| 维度 | 当前状态 |
|------|----------|
| 模型 | GLM-5.3 INT8 量化 |
| 框架 | TRTLLM (`python3 -m dynamo.trtllm`) |
| 拓扑 | 1P1D，Prefill/Decode 各 1 replica，TP=16，每节点 16 PPU |
| KV Transfer | NIXL backend（`cache_transceiver_config.backend: "NIXL"`），已验证 |
| RDMA | BF3L RoCE v2，`rdma/hca` |
| 网络 | `hostNetwork: true`, `privileged: true` |
| 模型路径 | `/ppusw/datasets/checkpoints/ppu_quantization/GLM-5.3-Quant-W-INT8-PerChannel-A-INT8-PerToken/` |
| 镜像 | `art.eng.t-head.cn/ptgai-docker_ai-service/ai-tmp/holmes:llm-torch2.9-cuda12.9-ubuntu24.04-py312-dpskv4-ppu202609021210` |
| DGD 名称 | `glm-5dot3-1p1d`，命名空间 `app` |
| ModelExpress | **未部署**（CRD 未安装、Server 未部署、客户端未集成） |

---

## 依赖关系与执行顺序

```
Step 0 (前置验证) ──┐
Step 1 (CRD)  ──────┤
Step 2 (MX 镜像) ───┼──→ Step 5 (修改 ConfigMap) ──→ Step 6 (修改 DGD) ──→ Step 7 (replicas=1) ──→ Step 8 (P2P)
Step 3 (客户端镜像) ┤
Step 4 (部署 MX)  ──┘
```

Step 0-4 之间无依赖可并行。Step 5/6 需要全部前置步骤完成。

---

## Step 0：前置验证（必做，10 分钟）

确认 Holmes 镜像中 TRT-LLM 是否支持 `checkpoint_format: MX` 配置。

```bash
# 在任意 PPU 节点上进入 Holmes 镜像
docker run --rm -it \
  art.eng.t-head.cn/ptgai-docker_ai-service/ai-tmp/holmes:llm-torch2.9-cuda12.9-ubuntu24.04-py312-dpskv4-ppu202609021210 \
  bash

# 方法一：搜索 TRT-LLM 中是否有 checkpoint_format / MxModelLoader 相关代码
grep -r "checkpoint_format" $(python3 -c "import tensorrt_llm; print(tensorrt_llm.__path__[0])") 2>/dev/null | head -20
grep -r "MxModelLoader\|modelexpress" $(python3 -c "import tensorrt_llm; print(tensorrt_llm.__path__[0])") 2>/dev/null | head -20

# 方法二：检查 update_llm_args_with_extra_options 是否处理 checkpoint_format
python3 -c "
try:
    from tensorrt_llm.llmapi.llm_utils import update_llm_args_with_extra_options
    print('update_llm_args_with_extra_options 可用')
except ImportError as e:
    print('无法导入:', e)
"

# 方法三：确认 NIXL 可正常导入
python3 -c "
try:
    import nixl
    print('NIXL 可用:', nixl.__file__)
except ImportError:
    print('NIXL 不可用 - 检查 PYTHONPATH')
"
```

**判断标准**：
- ✅ grep 找到 `checkpoint_format` 或 `MxModelLoader` 相关代码 → 继续后续步骤
- ❌ 完全无相关代码 → Holmes TRT-LLM 版本未合入 MX 集成，需联系框架同学确认升级方案
- ✅ NIXL 必须可导入（KV transfer 在用，应该没问题）

---

## Step 1：安装 ModelExpress CRDs（一次性，需 cluster-admin，2 分钟）

CRD 是集群级资源，幂等操作，不影响任何现有工作负载。

```bash
# CRD 文件在 modelexpress 源码仓库中
kubectl apply -f modelexpress/helm/crds/modelexpress-crds.yaml

# 验证
kubectl get crd modelmetadatas.modelexpress.nvidia.com
kubectl get crd modelcacheentries.modelexpress.nvidia.com
# 预期：两个 CRD 都存在，状态 ESTABLISHED
```

---

## Step 2：镜像 MX Server 到内部仓库（5 分钟）

MX Server 是轻量级元数据协调服务（Rust 实现），不需要 GPU/PPU。

```bash
# 在能访问 nvcr.io 的机器上拉取（或从离线包导入）
docker pull nvcr.io/nvidia/ai-dynamo/modelexpress-server:0.3.0

# 打内部仓库 tag
docker tag nvcr.io/nvidia/ai-dynamo/modelexpress-server:0.3.0 \
  art.eng.t-head.cn/ptgai-docker_ai-service/ai-tmp/modelexpress-server:0.3.0

# 推送
docker push art.eng.t-head.cn/ptgai-docker_ai-service/ai-tmp/modelexpress-server:0.3.0
```

> 如无法访问 nvcr.io，需通过跳板机或离线包传输镜像。

---

## Step 3：构建含 MX 客户端的运行时镜像（10 分钟）

在 Holmes 镜像基础上层叠 ModelExpress Python 客户端。

**创建 `Dockerfile.mx-glm53`**（放在 modelexpress 源码仓库根目录）：

```dockerfile
ARG BASE_IMAGE=art.eng.t-head.cn/ptgai-docker_ai-service/ai-tmp/holmes:llm-torch2.9-cuda12.9-ubuntu24.04-py312-dpskv4-ppu202609021210
FROM ${BASE_IMAGE}

# 复制 ModelExpress Python 客户端源码
COPY modelexpress_client/python /opt/modelexpress/client
WORKDIR /opt/modelexpress/client

# 清除可能存在的旧版本
RUN python3 -m pip uninstall -y modelexpress 2>/dev/null || true

# 关键：--no-deps 不替换 Holmes 镜像中的 TRT-LLM / NIXL 等依赖栈
RUN python3 -m pip install --no-cache-dir --no-deps .

WORKDIR /workspace
```

构建并推送：

```bash
cd /path/to/modelexpress   # modelexpress 源码仓库根目录

docker build -f Dockerfile.mx-glm53 \
  -t art.eng.t-head.cn/ptgai-docker_ai-service/ai-tmp/mx-glm53-trtllm:v0.1 .

docker push art.eng.t-head.cn/ptgai-docker_ai-service/ai-tmp/mx-glm53-trtllm:v0.1
```

**构建后验证**：

```bash
docker run --rm -it \
  art.eng.t-head.cn/ptgai-docker_ai-service/ai-tmp/mx-glm53-trtllm:v0.1 bash

# 验证 modelexpress 包已安装
python3 -c "import modelexpress; print('modelexpress OK')"

# 验证 TRTLLM 引擎适配器
python3 -c "from modelexpress.engines.trtllm.loader import MxModelLoader; print('MxModelLoader OK')"

# 验证 NIXL 仍可用
python3 -c "import nixl; print('NIXL OK:', nixl.__file__)"

# 验证 TRT-LLM 未被替换
python3 -c "import tensorrt_llm; print('TRTLLM version:', tensorrt_llm.__version__)"
```

> **`--no-deps` 是关键**！不加会让 pip 拉取 MX client 的 PyPI 依赖（grpcio、protobuf 等），可能与 Holmes 镜像中的版本冲突导致启动失败。

---

## Step 4：部署 MX Server（ArgoCD 方式）

### 4.1 创建部署配置文件

在 `gitea-app-manifests-0912` 仓库中创建以下文件：

**`foundation/modelexpress/kustomization.yaml`**：

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
- rbac.yaml
- server.yaml
```

**`foundation/modelexpress/rbac.yaml`**：

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: modelexpress
  labels:
    app.kubernetes.io/name: modelexpress
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: modelexpress-metadata
  labels:
    app.kubernetes.io/name: modelexpress
rules:
  - apiGroups: [modelexpress.nvidia.com]
    resources: [modelmetadatas, modelmetadatas/status]
    verbs: [get, list, watch, create, update, patch, delete]
  - apiGroups: [""]
    resources: [configmaps]
    verbs: [get, list, watch, create, update, patch, delete]
  - apiGroups: [modelexpress.nvidia.com]
    resources: [modelcacheentries, modelcacheentries/status]
    verbs: [get, list, watch, create, update, patch, delete]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: modelexpress-metadata
  labels:
    app.kubernetes.io/name: modelexpress
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: modelexpress-metadata
subjects:
  - kind: ServiceAccount
    name: modelexpress
```

**`foundation/modelexpress/server.yaml`**：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: modelexpress-server
  labels:
    app: modelexpress-server
spec:
  type: ClusterIP
  ports:
    - port: 8001
      targetPort: 8001
      name: grpc
  selector:
    app: modelexpress-server
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: modelexpress-server
  labels:
    app: modelexpress-server
spec:
  replicas: 1
  selector:
    matchLabels:
      app: modelexpress-server
  template:
    metadata:
      labels:
        app: modelexpress-server
    spec:
      serviceAccountName: modelexpress
      containers:
        - name: modelexpress-server
          image: art.eng.t-head.cn/ptgai-docker_ai-service/ai-tmp/modelexpress-server:0.3.0
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 8001
          env:
            - name: MX_METADATA_BACKEND
              value: "kubernetes"
            - name: MX_METADATA_NAMESPACE
              valueFrom:
                fieldRef:
                  fieldPath: metadata.namespace
            - name: MODEL_EXPRESS_LOG_LEVEL
              value: "info"
          resources:
            requests:
              cpu: "2"
              memory: 4Gi
            limits:
              cpu: "4"
              memory: 8Gi
          livenessProbe:
            tcpSocket:
              port: 8001
            initialDelaySeconds: 10
            periodSeconds: 10
          readinessProbe:
            tcpSocket:
              port: 8001
            initialDelaySeconds: 10
            periodSeconds: 10
```

### 4.2 创建 ArgoCD Application

**`argocd-apps/pprod/foundation/modelexpress.yaml`**：

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: modelexpress
  namespace: argocd
spec:
  destination:
    namespace: foundation
    server: https://kubernetes.default.svc
  project: pprod
  source:
    path: foundation/modelexpress
    repoURL: http://aliwl-sw443.eng.t-head.cn:31671/yuansheng.wzw/gitea-app-manifests.git
    targetRevision: HEAD
  syncPolicy:
    syncOptions:
    - CreateNamespace=true
```

### 4.3 提交 & 同步

```bash
cd gitea-app-manifests-0912
git add foundation/modelexpress/ argocd-apps/pprod/foundation/modelexpress.yaml
git commit -m "feat: add ModelExpress server for P2P weight transfer"
git push

# 同步 ArgoCD
kubectl apply -f argocd-apps/pprod/foundation/modelexpress.yaml -n argocd

# 验证部署
kubectl get pods -n foundation -l app=modelexpress-server
kubectl get svc -n foundation modelexpress-server
# 预期：Pod Running, Service ClusterIP 在 8001 端口
```

**验证跨命名空间连通性**（从 app 命名空间测试）：

```bash
kubectl run -n app --rm -it test-mx --image=busybox --restart=Never -- \
  sh -c "nc -zv modelexpress-server.foundation.svc.cluster.local 8001"
# 预期：Connected
```

> MX Server 部署在 `foundation` 命名空间，Worker Pod 在 `app` 命名空间。Worker 通过 gRPC 与 MX Server 通信，不直接访问 K8s API，因此跨命名空间无问题。DGD Pod 已设置 `dnsPolicy: ClusterFirstWithHostNet`，可正常解析集群内 DNS。

---
![[Pasted image 20260914151928.png]]
![[Pasted image 20260914152007.png]]
## Step 5：修改 ConfigMap 添加 MX 配置

**这是核心集成点**。在现有 `configmap-engine-args.yaml` 中为 prefill 和 decode 都添加 `checkpoint_format` + `mx_config`。

**文件**：`apps/hllm/glm-5dot3/overlays/pprod/configmap-engine-args.yaml`

在 **prefill 段末尾**（`cp_config` 之后）添加：

```yaml
    checkpoint_format: MX
    mx_config:
      server_url: modelexpress-server.foundation.svc.cluster.local:8001
```

在 **decode 段末尾**（`speculative_config` 之后）添加完全相同的配置：

```yaml
    checkpoint_format: MX
    mx_config:
      server_url: modelexpress-server.foundation.svc.cluster.local:8001
```

**原理**：`--extra-engine-args /etc/glm5dot3/engine/prefill` 读取此 YAML → TRT-LLM 的 `update_llm_args_with_extra_options()` 合并到引擎参数 → 看到 `checkpoint_format: MX` 后导入 `modelexpress.engines.trtllm.loader.MxModelLoader` 执行权重加载。**启动命令完全不需要修改。**

---

## Step 6：修改 DGD 部署配置

**文件**：`apps/hllm/glm-5dot3/overlays/pprod/deploy-1p1d.yaml`

### 6.1 更换镜像

将 prefill 和 decode **两个 service 的 image** 都换成 Step 3 构建的新镜像：

```yaml
# 原值：
image: art.eng.t-head.cn/ptgai-docker_ai-service/ai-tmp/holmes:llm-torch2.9-cuda12.9-ubuntu24.04-py312-dpskv4-ppu202609021210
# 改为：
image: art.eng.t-head.cn/ptgai-docker_ai-service/ai-tmp/mx-glm53-trtllm:v0.1
```

> 注意：prefill 的 `mainContainer.image`（约第 39 行）和 decode 的 `mainContainer.image`（约第 254 行）都要改。

### 6.2 添加 MX 环境变量

在 prefill 和 decode 两个 service 的 `envs` 列表末尾都添加：

```yaml
      # === ModelExpress P2P 配置 ===
      - name: MX_RDMA_NIC_PIN
        value: "off"
      - name: MX_POOL_REG
        value: "0"
      - name: MX_VMM_ARENA
        value: "0"
      - name: MODEL_EXPRESS_LOG_LEVEL
        value: "DEBUG"
      - name: NIXL_LOG_LEVEL
        value: "DEBUG"
      - name: UCX_RNDV_THRESH
        value: "0"
```

**环境变量说明**：

| 变量 | 值 | 说明 |
|------|-----|------|
| `MX_RDMA_NIC_PIN` | off | 禁用 NIC auto-probe（依赖 NVIDIA vendor ID，PPU 不适用） |
| `MX_POOL_REG` | 0 | 禁用 CUDA pool registration（PPU 不支持） |
| `MX_VMM_ARENA` | 0 | 禁用 VMM arena（PPU 不支持） |
| `MODEL_EXPRESS_LOG_LEVEL` | DEBUG | 验证阶段用 DEBUG，上线后改 INFO |
| `NIXL_LOG_LEVEL` | DEBUG | 验证阶段用 DEBUG，上线后改 INFO |
| `UCX_RNDV_THRESH` | 0 | 强制所有 RDMA 传输使用 rendezvous 协议（零拷贝） |

### 6.3 不需要修改的部分

| 项目 | 状态 |
|------|------|
| 启动命令 `python3 -m dynamo.trtllm ...` | **不动** |
| `--extra-engine-args` 参数 | **不动**（已指向 ConfigMap，Step 5 的改动自动生效） |
| NIXL KV transfer 配置 | **不动** |
| hostNetwork / privileged | **不动** |
| 卷挂载（datasets、cache 等） | **不动** |
| 现有 UCX 环境变量 | **不动** |

---

## Step 7：部署验证 — replicas=1（首个 Pod 磁盘加载 + 注册）

```bash
cd gitea-app-manifests-0912
git add apps/hllm/glm-5dot3/overlays/pprod/
git commit -m "feat: enable ModelExpress P2P for GLM-5.3"
git push

# 通过 ArgoCD 同步
argocd app sync glm-5dot3

# 等待 Pod Ready
kubectl get dgd glm-5dot3-1p1d -n app -w
kubectl get pods -n app -l dynamo.nvidia.com/deployment=glm-5dot3-1p1d
```

### 验证检查清单

**1. MX Client 正常初始化**：

```bash
PREFILL_POD=$(kubectl get pods -n app -l dynamo.nvidia.com/deployment=glm-5dot3-1p1d -l dynamo.nvidia.com/service=prefill -o jsonpath='{.items[0].metadata.name}')
DECODE_POD=$(kubectl get pods -n app -l dynamo.nvidia.com/deployment=glm-5dot3-1p1d -l dynamo.nvidia.com/service=decode -o jsonpath='{.items[0].metadata.name}')

kubectl logs -n app $PREFILL_POD -c main 2>&1 | grep -iE "modelexpress|MxModelLoader|checkpoint_format"
kubectl logs -n app $DECODE_POD -c main 2>&1 | grep -iE "modelexpress|MxModelLoader|checkpoint_format"
```

预期日志：
```
[Worker 0] TRT-LLM MxModelLoader starting (model=GLM-5.3, p2p_enabled=True)
```

**2. 首次从磁盘加载（无 source 时的 fallback）**：

```bash
kubectl logs -n app $PREFILL_POD -c main 2>&1 | grep -iE "Trying strategy|fallback|default|COMPLETE"
```

预期：策略链尝试 rdma → 无 source → 回退到 default（磁盘加载）→ 加载完成后 publish。

**3. 元数据已发布到 MX Server**：

```bash
kubectl get modelmetadatas -n foundation
# 预期：看到注册的 ModelMetadata 条目

kubectl get modelmetadatas -n foundation -o yaml | head -50
```

**4. KV transfer 仍然正常**：

```bash
# 发一个推理请求后检查
kubectl logs -n app $PREFILL_POD -c main 2>&1 | grep -iE "NIXL|kv.*transfer"
```

**GO/NO-GO**：
- ✅ MxModelLoader 激活 + ModelMetadata 已注册 + KV transfer 正常 → 进入 Step 8
- ❌ MxModelLoader 未激活（无相关日志）→ 回到 Step 0 检查 TRT-LLM MX 支持
- ❌ MX Server 连接失败 → 检查 Step 4.3 的 DNS 连通性验证
- ❌ `modelexpress` 模块导入失败 → 检查 Step 3 的镜像构建

---

## Step 8：P2P 验证 — 扩容到 replicas=2

```bash
# 扩容 Decode Worker
kubectl patch dgd glm-5dot3-1p1d -n app --type merge \
  -p '{"spec":{"services":{"decode":{"replicas":2}}}}'

# 等待新 Pod 创建并观察日志
kubectl get pods -n app -l dynamo.nvidia.com/deployment=glm-5dot3-1p1d -w

# 获取新 Pod 名称（最新创建的）
NEW_POD=$(kubectl get pods -n app -l dynamo.nvidia.com/service=decode --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}')

# 实时查看 RDMA 传输日志
kubectl logs -n app $NEW_POD -c main -f 2>&1 | grep -iE "Trying strategy|rdma|Transfer complete|source.*select|MxModelLoader.*COMPLETE"
```

**P2P 成功标志**：

```
[Worker 0] TRT-LLM MxModelLoader starting (model=GLM-5.3, p2p_enabled=True)
[Worker 0] Trying strategy: rdma
[Worker 0] Source selection: source_selector=random source_candidates_total=1 ...
[Worker 0] [TIMING] RDMA transfer complete: N tensors, X.XX GB, Y.YYs, Z.Z Gbps
[Worker 0] TRT-LLM MxModelLoader.load_model() COMPLETE in XX.XXs
```

**性能对比**：

```bash
# 第一个 Pod 加载时间（磁盘）
kubectl logs -n app $DECODE_POD -c main 2>&1 | grep -i "MxModelLoader.*COMPLETE"

# 第二个 Pod 加载时间（P2P RDMA）
kubectl logs -n app $NEW_POD -c main 2>&1 | grep -i "MxModelLoader.*COMPLETE"

# P2P 应比磁盘加载快数倍
```

**验证完成后缩回**：

```bash
kubectl patch dgd glm-5dot3-1p1d -n app --type merge \
  -p '{"spec":{"services":{"decode":{"replicas":1}}}}'
```

---

## 回滚方案

如果验证失败，回滚非常简单——只需还原 3 处改动：

1. **ConfigMap**：删除 `checkpoint_format: MX` 和 `mx_config` 段
2. **DGD 镜像**：恢复为原 Holmes 镜像
3. **DGD 环境变量**：删除 Step 6.2 新增的 6 个 MX 环境变量

通过 ArgoCD 同步即可生效。

**不需要清理的部分**（可保留不影响）：
- MX Server（不占 GPU/PPU 资源，~200m CPU / 256Mi 内存）
- CRD（集群级，不影响任何工作负载）
- 新镜像（保留在仓库中不影响原镜像）

---

## 风险与注意事项

| 风险 | 严重度 | 缓解 |
|------|--------|------|
| **Holmes TRT-LLM 不支持 `checkpoint_format: MX`** | **高** | Step 0 前置验证，不通过则不继续 |
| MX client `--no-deps` 缺少运行时依赖 | 中 | Step 3 构建后验证。缺失时单独安装缺少的包（如 `pip install grpcio protobuf`） |
| 跨命名空间通信被 NetworkPolicy 阻断 | 低 | Step 4.3 验证连通性。如有策略限制，添加 `foundation` ↔ `app` 的 NetworkPolicy |
| NIXL 端口冲突（P2P vs KV transfer） | 低 | P2P 用端口 `5555+device_id`，KV transfer 用 `19090`，不冲突 |
| 首个 Pod 启动时 MX Server 未就绪 | 低 | 优雅降级：跳过 RDMA 走磁盘加载，但 publish 会失败（best-effort），后续 Pod 无法 P2P。**确保 MX Server Ready 后再部署 DGD** |
| 两个 Pod 同时启动都走磁盘 | 低 | replicas=1 先启动完成后再扩容，保证有 source 可用 |

---

## 验证成功后的上线调整

1. `MODEL_EXPRESS_LOG_LEVEL` 和 `NIXL_LOG_LEVEL` 从 `DEBUG` 改为 `INFO`
2. 确认 P2P 传输速率满足预期（参考 RDMA 带宽 ~400-500 Gbps）
3. 按需扩容 replicas，验证多副本场景下 P2P 正常

---

## 附录：涉及的文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `foundation/modelexpress/kustomization.yaml` | **新建** | Kustomize 入口 |
| `foundation/modelexpress/rbac.yaml` | **新建** | SA + Role + RoleBinding |
| `foundation/modelexpress/server.yaml` | **新建** | MX Server Deployment + Service |
| `argocd-apps/pprod/foundation/modelexpress.yaml` | **新建** | ArgoCD Application |
| `apps/hllm/glm-5dot3/overlays/pprod/configmap-engine-args.yaml` | **修改** | 添加 `checkpoint_format: MX` + `mx_config` |
| `apps/hllm/glm-5dot3/overlays/pprod/deploy-1p1d.yaml` | **修改** | 更换镜像 + 添加 6 个 MX 环境变量 |
