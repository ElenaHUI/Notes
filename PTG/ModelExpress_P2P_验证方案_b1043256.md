# Holmes-LLM NIXL 权重 P2P 传输方案（基于代码分析）

> 基于 Holmes-LLM 仓库代码深度分析，回答两个问题：
> 1. `import nixl` 为什么失败？正确的使用方式是什么？
> 2. 如何在模型启动权重加载阶段使用 NIXL 做 P2P 传输？

---

## 一、NIXL 打包方式确认

### `import nixl` 失败的根本原因

NIXL 在 Holmes-LLM 中 **不是** 独立的顶层 Python 包，而是以三层结构嵌入在 `tensorrt_llm` 内部：

```
tensorrt_llm/
├── libs/
│   ├── libtensorrt_llm_nixl_wrapper.so            # C++ wrapper
│   └── nixl/
│       ├── *.so*                                   # NIXL native 库
│       ├── ucx/                                    # UCX 运行时
│       └── python/
│           ├── nixl_cu12/                          # pybind11 C++ extension（实际 binding）
│           └── nixl/                               # 纯 Python meta shim（re-export nixl_cu12）
├── tensorrt_llm_transfer_agent_binding*.so         # 独立 C++ agent binding
└── _torch/disaggregation/nixl/
    ├── agent.py                                    # 路由层（选 C++ 或 Python 实现）
    ├── _agent_cpp.py                               # C++ binding 实现（默认，释放 GIL）
    └── _agent_py.py                                # Python 实现（使用 nixl_cu12）
```

**三个失败原因叠加**：
1. `nixl` 不是 pip 安装的包，不在 `site-packages`
2. Docker 镜像构建时 `install_nixl.sh` 执行了 `rm -rf nixl*` 删除了 meta shim 源码
3. `tensorrt_llm/__init__.py` 中的 `_setup_nixl_python_path()` 会将 `libs/nixl/python` 注入 `sys.path`，但这只在 `import tensorrt_llm` **之后**才生效

### 正确的 NIXL 导入方式

```python
# ✅ 方式一（推荐）：通过 tensorrt_llm 高层 API
from tensorrt_llm._torch.disaggregation.nixl.agent import NixlTransferAgent

# ✅ 方式二：先 import tensorrt_llm 触发 sys.path 注入，再用底层 API
import tensorrt_llm
from nixl_cu12 import nixl_agent, nixl_agent_config

# ❌ 错误：直接 import nixl（meta shim 在镜像中不存在）
import nixl  # ModuleNotFoundError
```

### 对 ModelExpress 客户端的影响

ModelExpress 的 `_nixl.py` 按顺序尝试 `nixl_cu13 → nixl_cu12 → nixl`。由于 `python3 -m dynamo.trtllm` 启动时会先 `import tensorrt_llm`（触发 sys.path 注入），之后 `nixl_cu12` 可被正常导入。因此 **ModelExpress 客户端在运行时不受此问题影响**。

---

## 二、Holmes-LLM MX 集成状态：已完整合入

**重要发现**：Holmes-LLM 已经包含完整的 MX (ModelExpress) P2P 权重传输集成代码。

### 已有代码清单

| 组件 | 文件 | 状态 |
|------|------|------|
| `ModelExpressConfig` | `tensorrt_llm/llmapi/llm_args.py:4326` | ✅ 完整，含 `server_url`, `server_query_timeout_s`, `preshard_strategy` |
| `checkpoint_format` 字段 | `tensorrt_llm/llmapi/llm_args.py:4600` | ✅ 支持 `"MX"` 字符串值 |
| `mx_config` 字段 | `tensorrt_llm/llmapi/llm_args.py:4611` | ✅ `TorchLlmArgs` 上的 `ModelExpressConfig` |
| `MXCheckpointLoader` | `tensorrt_llm/_torch/models/checkpoints/mx/checkpoint_loader.py` | ✅ 注册为 `"MX"` 格式，继承 `HfCheckpointLoader` |
| `register_checkpoint_loader("MX")` | 同上 | ✅ 自动注册 |

### 代码调用链

```
dynamo.trtllm 启动
  └→ --extra-engine-args 读取 ConfigMap YAML（含 checkpoint_format: MX + mx_config）
      └→ update_llm_args_with_extra_options() 合并到引擎参数
          └→ _construct_checkpoint_loader(checkpoint_format="MX", mx_config=...)
              └→ MXCheckpointLoader(mx_server_url="...", ...)
                  └→ load_weights()
                      ├→ from modelexpress.trtllm_live_transfer import MxLiveWeightLoader  # ⚠️
                      ├→ MxLiveWeightLoader(mx_server=url).load_weights(ckpt_dir, mapping, model)
                      │   └→ NIXL RDMA P2P 从 source 拉取权重到 model params
                      └→ fallback: HfCheckpointLoader 磁盘加载（ImportError 或 P2P 失败时）
```

### 关键缺口：`modelexpress.trtllm_live_transfer` 模块

Holmes-LLM 的 `MXCheckpointLoader` 依赖以下上游 API：

```python
from modelexpress.trtllm_live_transfer import (
    MxClient,
    MxLiveWeightLoader,       # 核心：load_weights(ckpt_dir, mapping=, model=)
    _build_trtllm_identity,
    publish_model_params,      # 发布权重为 source
)
```

**但当前本地 modelexpress 源码（`/Users/sailor/Documents/code/modelexpress/`）中不存在 `trtllm_live_transfer` 模块**。现有的是 `modelexpress.engines.trtllm.loader.MxModelLoader`——这是给 `trtllm-serve` CLI 用的另一条集成路径，API 不同。

这意味着：要走 Holmes-LLM 的原生 MX 路径，需要获取包含 `trtllm_live_transfer` 模块的正确版本 modelexpress 客户端。

---

## 三、实施方案

根据代码分析，有三种可行方案：

### 方案 A：获取正确版本的 ModelExpress 客户端（推荐，如果可获取）

**原理**：Holmes-LLM 的 `MXCheckpointLoader` 已完整实现，只需安装包含 `trtllm_live_transfer` 模块的 modelexpress 客户端即可激活。

**步骤**：
1. **获取新版 modelexpress 客户端**：检查 `ai-dynamo/modelexpress` 上游仓库的最新 release/tag，寻找包含 `trtllm_live_transfer` 模块的版本
   ```bash
   cd /path/to/modelexpress
   git fetch --tags
   git log --oneline --all | head -20
   # 或检查 GitHub releases
   ```

2. **构建镜像**：在 Holmes 镜像上层叠新版 modelexpress 客户端
   ```dockerfile
   ARG BASE_IMAGE=art.eng.t-head.cn/.../holmes:llm-torch2.9-cuda12.9-...
   FROM ${BASE_IMAGE}
   COPY modelexpress_client/python /opt/modelexpress/client
   WORKDIR /opt/modelexpress/client
   RUN python3 -m pip install --no-cache-dir --no-deps .
   WORKDIR /workspace
   ```

3. **部署 MX Server**：同之前方案，部署到 `foundation` 命名空间

4. **修改 ConfigMap**：在 `configmap-engine-args.yaml` 的 prefill/decode 段添加
   ```yaml
   checkpoint_format: MX
   mx_config:
     server_url: modelexpress-server.foundation.svc.cluster.local:8001
   ```

5. **添加 MX 环境变量**：在 DGD 的 envs 中添加
   ```yaml
   - {name: MX_RDMA_NIC_PIN, value: "off"}
   - {name: MX_POOL_REG, value: "0"}
   - {name: MX_VMM_ARENA, value: "0"}
   - {name: MODEL_EXPRESS_LOG_LEVEL, value: "DEBUG"}
   ```

**优势**：零代码开发，复用 Holmes-LLM 已有的 `MXCheckpointLoader`，自带 fallback/超时/TP 对齐。
**前提**：能获取到包含 `trtllm_live_transfer` 的 modelexpress 版本。

---

### 方案 B：直接使用 NixlTransferAgent 实现 P2P 权重加载（自主可控）

**原理**：绕过 ModelExpress，直接利用 Holmes-LLM 内置的 `NixlTransferAgent` 实现轻量级权重 P2P 传输。

**NIXL Agent 能力确认**：
- `register_memory(RegMemoryDescs("VRAM", [(tensor.data_ptr(), tensor.nbytes, device_id, name)]))` — 支持注册**任意 GPU tensor**，不仅限于 KV cache
- `submit_transfer_requests(TransferRequest(op="READ", ...))` — 支持从远端 VRAM 读取数据
- per-tensor 粒度完全支持，每个 `MemoryDescs` entry 是独立内存段

**核心实现（约 300 行 Python）**：

#### B.1 实现 NixlWeightServer（Source Pod 侧）

```python
"""Source 端：加载完权重后注册到 NIXL 并发布元数据"""
import json
import torch
from tensorrt_llm._torch.disaggregation.nixl.agent import NixlTransferAgent

class NixlWeightServer:
    def __init__(self, agent_name: str, device_id: int = 0):
        self.agent = NixlTransferAgent(agent_name)
        self.device_id = device_id
        self.tensor_catalog = {}  # name -> (ptr, size, dtype)

    def register_model_weights(self, model: torch.nn.Module):
        """将模型所有权重参数注册到 NIXL"""
        descs = []
        for name, param in model.named_parameters():
            ptr = param.data_ptr()
            size = param.nelement() * param.element_size()
            descs.append((ptr, size, self.device_id, name))
            self.tensor_catalog[name] = {
                "ptr": ptr, "size": size,
                "dtype": str(param.dtype), "shape": list(param.shape)
            }
        # 批量注册所有权重到 VRAM
        self.agent.register_memory(RegMemoryDescs("VRAM", descs))

    def get_metadata(self) -> dict:
        """返回 agent 描述符 + tensor 清单，供 target 发现"""
        return {
            "agent_desc": self.agent.get_local_agent_desc().hex(),
            "tensor_catalog": self.tensor_catalog,
        }
    # 通过 etcd/Redis/HTTP 发布 metadata（复用现有 Dynamo 的 etcd）
```

#### B.2 实现 NixlWeightClient（Target Pod 侧）

```python
"""Target 端：从 Source VRAM 拉取权重"""
class NixlWeightClient:
    def __init__(self, agent_name: str, device_id: int = 0):
        self.agent = NixlTransferAgent(agent_name)
        self.device_id = device_id

    def load_weights_from_source(
        self, model: torch.nn.Module, source_metadata: dict
    ) -> bool:
        """通过 NIXL RDMA 从 source 拉取权重到本地 model params"""
        # 连接 source agent
        agent_desc = bytes.fromhex(source_metadata["agent_desc"])
        self.agent.load_remote_agent("source", agent_desc)

        catalog = source_metadata["tensor_catalog"]
        # 注册本地 tensor
        local_descs = []
        for name, param in model.named_parameters():
            local_descs.append((
                param.data_ptr(), param.nelement() * param.element_size(),
                self.device_id, name
            ))
        self.agent.register_memory(RegMemoryDescs("VRAM", local_descs))

        # 逐 tensor 提交 READ 请求
        for name, param in model.named_parameters():
            if name not in catalog:
                continue
            src_info = catalog[name]
            req = TransferRequest(
                op="READ",
                src_descs=MemoryDescs("VRAM", [(src_info["ptr"], src_info["size"], 0)]),
                dst_descs=MemoryDescs("VRAM", [(param.data_ptr(), src_info["size"], self.device_id)]),
                remote_name="source",
            )
            status = self.agent.submit_transfer_requests(req)
            status.wait(timeout_ms=30000)
        return True
```

#### B.3 元数据发现机制

复用现有 Dynamo 的 etcd（`ETCD_ENDPOINTS` 已配置）：

```python
import etcd3
def publish_weight_metadata(etcd_endpoints, dgd_name, role, metadata):
    client = etcd3.client(host=..., port=...)
    key = f"/mx-weights/{dgd_name}/{role}"
    client.put(key, json.dumps(metadata))

def discover_weight_source(etcd_endpoints, dgd_name, role) -> dict:
    client = etcd3.client(host=..., port=...)
    key = f"/mx-weights/{dgd_name}/{role}"
    value, _ = client.get(key)
    return json.loads(value) if value else None
```

#### B.4 集成到 Holmes-LLM 权重加载流程

**Hook 点**：`tensorrt_llm/_torch/pyexecutor/model_loader.py` 中的 `ModelLoader.load()`

```python
# 在 model_loader.py 的 load() 方法中，checkpoint_loader.load_weights() 之前：
if os.environ.get("NIXL_WEIGHT_P2P_ENABLED") == "1":
    source_metadata = discover_weight_source(etcd_endpoints, dgd_name, role)
    if source_metadata:
        client = NixlWeightClient(f"target-{pod_name}", device_id=local_rank)
        success = client.load_weights_from_source(model, source_metadata)
        if success:
            # 跳过磁盘加载，直接进入 post_load_weights
            return model

# 正常磁盘加载
weights = checkpoint_loader.load_weights(...)
model.load_weights(weights)

# 加载完成后注册为 source
if os.environ.get("NIXL_WEIGHT_P2P_ENABLED") == "1":
    server = NixlWeightServer(f"source-{pod_name}", device_id=local_rank)
    server.register_model_weights(model)
    publish_weight_metadata(etcd_endpoints, dgd_name, role, server.get_metadata())
```

**优势**：不依赖 ModelExpress Server 和上游库版本，完全自主可控。
**代价**：需要自行处理 TP 对齐、容错、超时。但对于 GLM-5.3 固定拓扑（TP=16，prefill/decode 各独立），TP 对齐不是问题（source 和 target 使用相同 mapping）。

---

### 方案 C：创建 trtllm_live_transfer 适配层（折中方案）

**原理**：在现有 modelexpress 代码基础上，创建一个 `trtllm_live_transfer.py` shim 模块，适配 Holmes-LLM `MXCheckpointLoader` 期望的 API。

```python
# modelexpress/trtllm_live_transfer.py — 适配 shim
from modelexpress.engines.trtllm.loader import MxModelLoader
from modelexpress.engines.trtllm.adapter import build_trtllm_load_context

class MxLiveWeightLoader:
    def __init__(self, mx_server: str):
        self.mx_server = mx_server

    def load_weights(self, checkpoint_dir, mapping, model):
        """适配 MXCheckpointLoader 的调用签名"""
        loader = MxModelLoader(
            model_config=...,  # 从 model 推导
            mx_server_url=self.mx_server,
            p2p_enabled=True,
            ...
        )
        result = loader.load_model(model)
        return result  # {} 表示 P2P 成功，非空 dict 表示 fallback weights

def publish_model_params(model):
    """适配 publish 调用"""
    # 使用 MxModelLoader.publish_model() 逻辑
    ...

class MxClient:
    def __init__(self, server_url): ...
    def list_sources(self, identity): ...

def _build_trtllm_identity(model_name): ...
```

**优势**：复用 Holmes-LLM 已有的 `MXCheckpointLoader` + 现有 modelexpress 代码。
**代价**：需要适配两套不同 API 的参数映射，维护成本较高。

---

## 四、方案对比与建议

| 维度 | 方案 A：正版 MX 客户端 | 方案 B：DIY NixlAgent | 方案 C：适配 shim |
|------|----------------------|---------------------|------------------|
| **开发量** | 0（配置即用） | ~300 行 Python | ~200 行 Python |
| **外部依赖** | MX Server + 正确版本 modelexpress | 仅 etcd（已有） | MX Server + 现有 modelexpress |
| **TP 对齐** | 自动处理 | 需相同 mapping | 取决于适配质量 |
| **容错 fallback** | 内置（→ 磁盘加载） | 需自行实现 | 继承 MXCheckpointLoader |
| **验证复杂度** | 低 | 中 | 中 |
| **自主可控** | 依赖上游版本 | 完全自主 | 部分依赖 |
| **适合场景** | 能获取 trtllm_live_transfer | 快速验证 / 长期维护 | 短期过渡 |

### 推荐路径

1. **首先尝试方案 A**：检查 modelexpress 上游最新版本是否已包含 `trtllm_live_transfer`。Holmes-LLM 代码注释引用了 `ai-dynamo/modelexpress`，该模块很可能在主线但本地 clone 版本较旧
2. **方案 A 不可行时选方案 B**：对于 GLM-5.3 固定拓扑部署，DIY 方案足够简单且完全可控。不需要 MX Server，复用现有 etcd 做 discovery
3. **方案 C 作为备选**：仅在需要复用 `MXCheckpointLoader` 的 fallback/timeout 逻辑时考虑

---

## 五、NixlTransferAgent 核心 API 速查

供实现方案 B 时参考：

```python
from tensorrt_llm._torch.disaggregation.nixl.agent import NixlTransferAgent
from tensorrt_llm._torch.disaggregation.nixl.base.agent import (
    RegMemoryDescs, MemoryDescs, TransferRequest, TransferStatus
)

# 创建 agent
agent = NixlTransferAgent(name="my-agent")

# 注册 GPU 内存区域
descs = RegMemoryDescs(
    type="VRAM",  # "VRAM" | "DRAM" | "BLK" | "OBJ" | "FILE"
    descs=[(ptr, size, device_id, name), ...]  # (int, int, int, str) 四元组
)
agent.register_memory(descs)

# 获取/交换 agent 描述符
local_desc: bytes = agent.get_local_agent_desc()
agent.load_remote_agent("remote-name", remote_desc_bytes)

# 发起传输
request = TransferRequest(
    op="READ",  # "READ" = 从远端拉取, "WRITE" = 推送到远端
    src_descs=MemoryDescs("VRAM", [(ptr, size, device_id), ...]),
    dst_descs=MemoryDescs("VRAM", [(ptr, size, device_id), ...]),
    remote_name="remote-name",
    sync_message=None,
)
status: TransferStatus = agent.submit_transfer_requests(request)

# 等待完成
completed = status.wait(timeout_ms=30000)  # 阻塞等待
# 或
is_done = status.is_completed()  # 非阻塞检查

# 清理
agent.deregister_memory(descs)
agent.invalidate_remote_agent("remote-name")
```

**关键约束**：
- Source 和 target 的 tensor 必须 size 完全匹配（RDMA 按字节传输）
- `device_id` 对应 `CUDA_VISIBLE_DEVICES` 中的逻辑设备号
- TP=16 场景下，每个 rank 独立运行 agent，只注册本 rank 的 tensor 分片
- UCX 环境变量（`UCX_TLS`, `UCX_RNDV_SCHEME` 等）需正确配置（DGD 已有）

---

## 六、关键风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| `modelexpress.trtllm_live_transfer` 在上游不可用 | 方案 A 不可行 | 转方案 B |
| TP 分片不一致（source/target 不同 mapping） | P2P 数据错误 | GLM-5.3 固定 TP=16，同角色 mapping 一致，不会发生 |
| NIXL 端口冲突（权重 P2P vs KV transfer） | 启动失败 | 两者使用独立 NixlAgent 实例，端口自动分配 |
| 首个 Pod 未 publish 时后续 Pod 启动 | 全部走磁盘 | 先 replicas=1 启动完成后再扩容 |
| FD_SETSIZE 溢出（PPU 已知问题） | 权重传输时 abort | 权重加载是一次性操作，并发度可控，风险极低 |
