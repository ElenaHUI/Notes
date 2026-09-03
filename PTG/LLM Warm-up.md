# LLM 模型启动 Warmup 真实请求录制回放完整方案

## 一、现状分析

### 当前 Warmup 机制

三阶段启动流程（`monitor_and_warmup.sh`）：

1. **健康检查等待** — 轮询 `localhost:{PORT}/health`，间隔 10s，超时 1200s，同时监控推理引擎 PID 存活
2. **单请求预热** — 读取 `/warmup-data/warmup-input-1w.text`（约 1 万字静态纯文本），发送 1 条 `/v1/chat/completions` 请求
3. **就绪标记** — `touch /tmp/warmup-done`，readinessProbe 通过 `exec: test -f /tmp/warmup-done` 检测

### 核心问题

- **warmup 数据与真实请求差距大**：当前使用通用纯文本 prompt，而 OpenCode/QwenCode 的真实请求是多轮对话 + system prompt + tool_calls + 长上下文代码，warmup 效果有限
- **脚本 4 副本散落**：`sglang-init-scripts`、`vllm-monitor-script`、`llm-init-scripts`、`glm-5dot2-warmup-script` 四个 ConfigMap 核心逻辑 95% 相同，仅变量名（`SGLANG_PID`/`VLLM_PID`/`LLM_PID`、`SG_PORT`/`VLLM_PORT`/`LLM_PORT`）和默认模型名不同
- **影响范围广**：`monitor_and_warmup.sh` 被 15+ 个 deploy.yaml 引用（sglang: GLM-5 pdev/pprod、Kimi-K2.6; vllm: Qwen3-Coder-Next、DeepSeek-V4-Flash、Qwen3.6-27B、minimax-m2.7 等）

### 已有基础设施

|组件|能力|关键文件|
|---|---|---|
|litellm-proxy 请求抓取|按 API Key/User ID 抓取完整请求，含 `transformed_request`（标准 OpenAI 格式 body）、session 关联|`litellm-proxy/request_response_capture.py`|
|litellm-proxy 请求转发|从抓取文件读取 `transformed_request.body` 转发到任意目标，支持 model 替换、message 截断|`litellm-proxy/capture_relay.py`|
|web-mgmt 抓取 UI|CaptureConfigPanel / CaptureResultPanel / CaptureRelayModal 完整前端|`web-mgmt/src/components/capture/`|
|共享存储|所有模型 Pod 已挂载 hostPath `/ppusw/devops/llm_platform/` → 容器 `/warmup-data/`|各 deploy.yaml `host-warmup-data` volume|

---

## 二、整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    请求录制阶段（一次性/定期）                    │
│                                                             │
│  OpenCode/QwenCode → litellm-proxy → 抓取为 capture JSON    │
│                            │                                │
│              GET /capture/export-warmup                     │
│                            │                                │
│                    ┌───────▼────────┐                       │
│                    │  warmup.jsonl  │  ← JSONL 格式         │
│                    └───────┬────────┘                       │
│                            │ 放置到共享 NFS                  │
│  /ppusw/devops/llm_platform/warmup/{model-name}.jsonl      │
└─────────────────────────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                    模型启动阶段（每次 Pod 启动）                 │
│                                                             │
│  引擎后台启动 → monitor_and_warmup.sh                        │
│    Step 1: 轮询 /health 等健康检查                            │
│    Step 2: 读取 JSONL → 逐条发送 /v1/chat/completions       │
│    Step 3: touch /tmp/warmup-done → readinessProbe 通过     │
│                                                             │
│  共享 ConfigMap: llm-warmup-scripts（统一脚本）               │
│  差异通过 env 控制: WARMUP_DATA_FILE, LLM_PORT, MODEL_NAME  │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、实施步骤

### Phase 1: 请求采集 — litellm-proxy 导出端点

#### Step 1.1: 新增 `/capture/export-warmup` API

**修改文件**: `litellm-proxy/request_response_capture.py`

新增 GET 端点，功能：

- **参数**: `api_key`（按 key 筛选）、`user_id`、`model`（按模型筛选）、`limit`（默认 5）、`max_prompt_tokens`（默认 32768，过滤超长请求避免 OOM）、`deduplicate`（默认 true，按 messages 内容 hash 去重）
- **逻辑**: 扫描抓取索引 → 筛选 status=success 的记录 → 从每条 capture 文件提取 `transformed_request.body`（优先）或 `proxy_server_request.body` → 只保留 `messages`、`max_tokens`、`temperature` 等推理字段（移除 `model`、`stream`、`cache`、`api_key`、`stream_options` 等服务端字段）→ 按 prompt tokens 降序排列
- **输出**: JSONL 格式（每行一个标准 OpenAI chat completions request body，不含 model 字段），Content-Disposition 为 attachment 下载

#### Step 1.2: 编写离线导出辅助脚本

**新建文件**: `litellm-proxy/scripts/export_warmup_data.sh`

封装 curl 调用：

```
#!/bin/bash
# 用法: ./export_warmup_data.sh <model_name> [limit] [max_prompt_tokens]
# 示例: ./export_warmup_data.sh Qwen3-Coder-Next 5 32768
MODEL=${1:?"Usage: $0 <model_name> [limit] [max_prompt_tokens]"}
LIMIT=${2:-5}
MAX_TOKENS=${3:-32768}
PROXY_URL=${LITELLM_PROXY_URL:-"http://litellm-proxy:4000"}
OUTPUT_DIR="/ppusw/devops/llm_platform/warmup"
mkdir -p "$OUTPUT_DIR"
curl -sS "${PROXY_URL}/capture/export-warmup?model=${MODEL}&limit=${LIMIT}&max_prompt_tokens=${MAX_TOKENS}" \
  -o "${OUTPUT_DIR}/${MODEL}.jsonl"
echo "Exported to ${OUTPUT_DIR}/${MODEL}.jsonl"
```

可在 litellm-proxy Pod 或任意有 NFS 访问权限的 Pod 中执行。

### Phase 2: 统一 Warmup 脚本

#### Step 2.1: 创建共享 ConfigMap

**新建文件**: `gitea-app-manifests-0818/foundation/llm-warmup/llm-warmup-scripts.yaml`

ConfigMap 名称: `llm-warmup-scripts`，包含以下文件：

**`monitor_and_warmup.sh`** — 统一入口脚本：

- 变量标准化: `LLM_PID`（第一个位置参数）、`LLM_PORT`（环境变量，三级回退 `LLM_PORT` → `VLLM_PORT` → `SG_PORT`→ 8000）
- Step 1: 健康检查等待（与现有逻辑完全一致）
- Step 2: 预热请求（调用内嵌 Python 脚本 `warmup_replay`）
    - **JSONL 模式**: 当 `WARMUP_DATA_FILE` 环境变量指向 `.jsonl` 文件且文件存在时，逐行解析 JSON，每条自动注入 `model` 字段（来自 `MODEL_NAME` 环境变量），逐条串行发送 `/v1/chat/completions`
    - **Legacy 纯文本模式**: 当 `WARMUP_DATA_FILE` 指向 `.text`/`.txt` 文件或未设置时（回退到 `WARMUP_FILE` 兼容旧配置），读取全文作为单条 user message 发送（完全复现当前行为）
    - **Skip 模式**: 当 `WARMUP_SKIP=true` 时直接跳到 Step 3（适用于 GLM-5.2 PD disaggregation 等已有内置 warmup 的场景）
    - **关键保护**: warmup 失败仅打印 WARNING 日志但**不退出**，始终执行 Step 3 创建就绪标记。避免 warmup 异常导致 Pod 永远不 Ready
- Step 3: `touch /tmp/warmup-done`

**环境变量接口**（全部有默认值，100% 向后兼容）：

|变量|默认值|说明|
|---|---|---|
|`LLM_PID`|(位置参数 $1，必需)|推理引擎进程 PID|
|`LLM_PORT`|回退链 → 8000|推理服务端口|
|`MODEL_NAME`|""|served-model-name，注入到 warmup 请求的 model 字段|
|`WARMUP_DATA_FILE`|""|JSONL 格式预热文件路径（优先级最高）|
|`WARMUP_FILE`|`/warmup-data/warmup-input-1w.text`|旧版纯文本路径（兼容回退）|
|`WARMUP_SKIP`|"false"|设为 "true" 跳过 warmup 请求步骤|
|`WARMUP_MAX_REQUESTS`|5|JSONL 模式下最多发送的请求条数|
|`WARMUP_REQUEST_TIMEOUT`|600|单条 warmup 请求超时（秒）|
|`STARTUP_TIMEOUT_SECONDS`|1200|引擎健康检查总超时|
|`HEALTH_CHECK_INTERVAL`|10|健康检查轮询间隔|

**`warmup_replay` Python 脚本核心逻辑**：

```
# 伪代码，实际实现在 ConfigMap 中
for i, line in enumerate(jsonl_lines[:max_requests]):
    request_body = json.loads(line)
    request_body["model"] = model_name
    request_body["max_tokens"] = min(request_body.get("max_tokens", 1024), 2048)  # 安全上限
    request_body["stream"] = False
    resp = requests.post(f"http://localhost:{port}/v1/chat/completions", json=request_body, timeout=timeout)
    # 输出: 请求序号、耗时(ms)、prompt_tokens、completion_tokens、总token/s
    print(f"[Warmup {i+1}/{total}] {duration_ms:.0f}ms | usage: {usage}")
```

**`init-gpu-env.sh` + `parse_gpu.py`** — 从现有 `sglang-init-scripts` 原样保留（PPU GPU 拓扑解析，仅 PPU 节点使用）。

#### Step 2.2: 新建 kustomization.yaml

**新建文件**: `gitea-app-manifests-0818/foundation/llm-warmup/kustomization.yaml`

```
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
- llm-warmup-scripts.yaml
```

#### Step 2.3: 新建 ArgoCD Application

**新建文件**: `gitea-app-manifests-0818/argocd-apps/pdev/foundation/llm-warmup.yaml`（以及 pprod、prod 环境各一份）

将 `foundation/llm-warmup/` 作为独立 ArgoCD App 部署到对应 namespace，与现有 `foundation/` 下的 kong、es、filebeat 等组件保持一致的管理模式。

### Phase 3: 数据准备 — 录制与导出

#### Step 3.1: 在 litellm-proxy 中为 OpenCode/QwenCode 启动抓取

通过已有的 `/capture/start` API 或 web-mgmt CaptureConfigPanel，按 API Key 或 User ID 启动抓取：

- **OpenCode**: 通过 `x-session-affinity` header 自动关联 session
- **QwenCode**: 通过对应的 API Key 筛选

建议抓取 1-2 天的日常使用数据，积累足够的请求样本。

#### Step 3.2: 导出 warmup 数据

抓取完成后，使用 Step 1.1 的 API 或 Step 1.2 的脚本导出：

```
# 为 Qwen3-Coder-Next 导出（OpenCode 主要使用的模型）
./export_warmup_data.sh Qwen3-Coder-Next 5 32768

# 为其他需要 warmup 的模型导出
./export_warmup_data.sh GLM-5 5 16384
./export_warmup_data.sh DeepSeek-V4-Flash 5 32768
```

导出的 JSONL 文件示例（每行一条请求）：

```
{"messages":[{"role":"system","content":"You are a coding assistant..."},{"role":"user","content":"请分析这段代码..."}],"max_tokens":2048,"temperature":0.7}
{"messages":[{"role":"user","content":"帮我重构这个函数..."}],"max_tokens":1024}
```

文件放置于共享 NFS: `/ppusw/devops/llm_platform/warmup/{model-name}.jsonl`

### Phase 4: 部署迁移 — 各模型 YAML 改造

#### Step 4.1: 先验证模型（pdev 环境 Qwen3-Coder-Next）

**修改文件**: `apps/vllm/qwen3-coder-next/overlays/pdev/deploy.yaml`

- 新增 env: `WARMUP_DATA_FILE: "/warmup-data/warmup/Qwen3-Coder-Next.jsonl"`
- volume `init-scripts-volume` / `monitor-script-volume` 的 configMap name 改为 `llm-warmup-scripts`

**修改文件**: `apps/vllm/qwen3-coder-next/overlays/pdev/kustomization.yaml`

- 删除 `vllm-monitor-script.yaml` 资源引用（旧 ConfigMap 由共享替代）

#### Step 4.2: 验证通过后，逐步迁移其他模型

按优先级分批迁移（每批验证后再进行下一批）：

**批次 1 — pdev 高频模型**：

- `vllm/deepseek-v4-flash/overlays/pdev/`
- `sglang/glm-5/overlays/pdev/`

**批次 2 — pprod 高频模型**：

- `vllm/qwen3-coder-next/overlays/pprod/`
- `vllm/deepseek-v4-flash/overlays/pprod/`
- `sglang/glm-5/overlays/pprod/`

**批次 3 — 其余模型**：

- `vllm/qwen3dot6-27b/`、`vllm/minimax-m2dot7/`、`vllm/vllm-app/`、`sglang/kimi-k2dot6/` 等

每个模型的改动模板（约 3 处）：

1. `deploy.yaml` — env 新增 `WARMUP_DATA_FILE`，volume configMap name 改为 `llm-warmup-scripts`
2. `kustomization.yaml` — 删除旧的 `*-monitor-script.yaml` / `*-init-scripts.yaml` 资源引用
3. 旧 ConfigMap YAML 文件 — 可保留不删（ArgoCD 会自动 prune 未引用资源），或手动清理

**特殊处理**：

- **GLM-5.2 PD disaggregation**（`sglang/glm-5dot2/overlays/pprod/`）: 设置 `WARMUP_SKIP=true`，跳过 warmup 请求步骤
- **Embedding 模型**（`vllm/qwen3-embedding-4b/`）: warmup 请求需改为 `/v1/embeddings` 端点，或设置 `WARMUP_SKIP=true` 暂跳过

### Phase 5: 测试验证 Warmup 效果

#### Step 5.1: 功能验证（每个迁移批次必做）

1. **Pod 启动验证**: ArgoCD sync 后观察 Pod 启动日志：
    
    ```
    kubectl logs <pod-name> -c <container> | grep -A5 "Step 2"
    ```
    
    预期看到：
    
    - `[Warmup] Mode: JSONL (N requests from /warmup-data/warmup/xxx.jsonl)`
    - `[Warmup 1/N] 3500ms | prompt_tokens: 2048, completion_tokens: 256`
    - `[Warmup] All N requests completed in Xms`
    - `Ready flag created.`
2. **Readiness 门控验证**: 确认 Pod 状态从 NotReady → Ready 的时间点在 warmup 完成之后：
    
    ```
    kubectl get events --field-selector involvedObject.name=<pod-name> | grep Ready
    ```
    
3. **降级验证**: 临时将 `WARMUP_DATA_FILE` 指向不存在的路径，确认 Pod 仍能正常启动（仅打印 WARNING，不阻塞 Ready）
    

#### Step 5.2: 性能效果验证（warmup 前后对比）

**方法 A: TTFT（Time To First Token）对比**

1. 先部署无 warmup 版本（`WARMUP_SKIP=true`），Pod Ready 后立即发送一条真实请求，记录 TTFT
2. 部署有 warmup 版本（正常 JSONL 模式），Pod Ready 后立即发送**同一条**请求，记录 TTFT
3. 对比两者差异

测试命令：

```
# 记录 TTFT (使用流式请求，测量首个 token 到达时间)
curl -w "\nTTFT: %{time_starttransfer}s\nTotal: %{time_total}s\n" \
  -X POST "http://<model-svc>:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{"model":"<model-name>","messages":[{"role":"user","content":"请解释Python装饰器的实现原理"}],"max_tokens":512,"stream":true}' \
  -o /dev/null
```

**方法 B: CUDA Kernel 编译对比**

对于 sglang/flashinfer 场景，检查 warmup 后 `.so` 缓存是否已填充：

```
# 进入 Pod 检查 flashinfer 编译缓存
kubectl exec <pod> -- find /root/.cache/flashinfer -name "*.so" | wc -l
```

**方法 C: 利用已有 litellm-proxy relay 能力做自动化对比**

使用 `/capture/relay` 将同一组抓取请求分别转发到 warmup 前/后的模型实例，收集响应时间统计。

#### Step 5.3: warmup 数据质量验证

定期检查导出的 JSONL 文件：

- **覆盖度**: 包含的请求类型（纯文本对话、tool_calls、多轮上下文）是否代表真实流量分布
- **大小合理性**: 单个 JSONL 文件建议 < 1MB，请求条数 3-5 条
- **敏感信息**: 确认不包含 API Key、密码等敏感内容（export API 已自动清理，但需人工抽查）

---

## 四、JSONL Warmup 数据格式规范

```
{"messages":[{"role":"system","content":"..."},{"role":"user","content":"..."}],"max_tokens":1024,"temperature":0.7}
```

**规则**：

- 每行一个完整 JSON 对象，符合 OpenAI `/v1/chat/completions` request body 格式
- **不含** `model` 字段（由 warmup 脚本从 `MODEL_NAME` 环境变量注入）
- **不含** `stream`、`stream_options`、`cache`、`api_key` 等服务端/鉴权字段
- `max_tokens` 建议 ≤ 2048（warmup 脚本会强制 cap 到 `WARMUP_MAX_TOKENS` 上限，避免 warmup 耗时过长）
- 按 prompt_tokens 从大到小排列（先热大请求，覆盖更多 CUDA kernel 路径和 KV cache prefill pattern）

---

## 五、依赖关系

```
Phase 1 (litellm-proxy 导出端点) ──────────┐
                                            ├──► Phase 3 (数据录制+导出)
Phase 2 (统一 ConfigMap + ArgoCD App) ──────┤
                                            ├──► Phase 4 (部署迁移，分批)
                                            │         │
                                            │         ▼
                                            └──► Phase 5 (测试验证，每批做一次)
```

- Phase 1 和 Phase 2 **互相独立，可并行开发**
- Phase 3 依赖 Phase 1（需要 export API）
- Phase 4 依赖 Phase 2（需要共享 ConfigMap 已部署）和 Phase 3（需要 JSONL 数据已就绪）
- Phase 5 贯穿 Phase 4 每个批次

---

## 六、风险与缓解

|风险|严重性|缓解措施|
|---|---|---|
|warmup JSONL 包含超长 prompt 导致引擎 OOM|**高**|export API 强制 `max_prompt_tokens` 上限（32K）；脚本层 `max_tokens` cap 到 2048；每条 timeout 600s|
|warmup 脚本异常导致 Pod 永远不 Ready|**高**|**核心设计原则**: warmup 失败仅 WARNING，始终 `touch /tmp/warmup-done`。任何异常路径都不允许阻塞 Ready|
|PD disaggregation Pod 不支持 `/v1/chat/completions`|**高**|`WARMUP_SKIP=true` 环境变量直接跳过 Step 2|
|统一 ConfigMap 变更影响所有部署|**中**|pdev 先行验证 → pprod 跟进 → prod 最后。ArgoCD 可按 App 粒度控制 sync 节奏|
|共享 NFS 上 warmup 文件不存在|**中**|脚本检查文件存在性：不存在则回退到 `WARMUP_FILE`（旧文本），旧文本也不存在则 skip warmup 并 WARNING|
|从 `SG_PORT`/`VLLM_PORT` 统一为 `LLM_PORT` 的兼容性|**低**|三级回退: `LLM_PORT=${LLM_PORT:-${VLLM_PORT:-${SG_PORT:-8000}}}`|
|导出数据含敏感信息|**低**|export API 自动移除 `api_key`/`authorization` 字段，仅保留 messages 和推理参数|

---

## 七、被否决的替代方案

|方案|否决原因|
|---|---|
|**CronJob 自动定期刷新 warmup 数据**|V1 阶段复杂度过高；warmup 数据更新频率低（模型/流量模式变化时才需更新），手动 export 足够|
|**warmup 请求并发发送**|GPU 启动阶段内存压力大，并发请求可能导致 OOM；串行更安全，3-5 条请求总耗时可接受（< 2min）|
|**kustomize components 方式引入共享脚本**|需要所有 overlay 的 kustomization.yaml 从 `resources` 改为 `components`引用方式，改动量大且与现有模式不一致|
|**ConfigMap 版本号命名（`llm-warmup-scripts-v1`）**|增加命名复杂度，pdev-first 分批验证已足够控制风险|
|**JSONL 中使用 `__MODEL__` 占位符由脚本替换**|不如直接在脚本层注入 `MODEL_NAME`，JSONL 保持纯数据更简洁|
|**在 web-mgmt 前端新增"导出 Warmup"按钮**|Nice-to-have，可后续迭代；V1 阶段 API + shell 脚本即可满足需求|

---

## 八、关键文件清单

|文件|角色|
|---|---|
|`litellm-proxy/request_response_capture.py`|新增 `/capture/export-warmup` 端点（~80 行）|
|`litellm-proxy/scripts/export_warmup_data.sh`|新建，离线导出辅助脚本|
|`gitea-app-manifests-0818/foundation/llm-warmup/llm-warmup-scripts.yaml`|新建，统一 warmup ConfigMap|
|`gitea-app-manifests-0818/foundation/llm-warmup/kustomization.yaml`|新建，kustomize 入口|
|`gitea-app-manifests-0818/argocd-apps/*/foundation/llm-warmup.yaml`|新建，各环境的 ArgoCD App|
|`gitea-app-manifests-0818/apps/vllm/qwen3-coder-next/overlays/pdev/deploy.yaml`|首个迁移对象（env + volume 改动）|
|`gitea-app-manifests-0818/apps/sglang/glm-5/overlays/pdev/deploy.yaml`|迁移对象|
|15+ 其他 deploy.yaml|后续批次迁移|

  

目录

- LLM 模型启动 Warmup 真实请求录制回放完整方案
- 一、现状分析
- 当前 Warmup 机制
- 核心问题
- 已有基础设施
- 二、整体架构
- 三、实施步骤
- Phase 1: 请求采集 — litellm-proxy 导出端点
- Step 1.1: 新增 /capture/export-warmup API
- Step 1.2: 编写离线导出辅助脚本
- Phase 2: 统一 Warmup 脚本
- Step 2.1: 创建共享 ConfigMap
- Step 2.2: 新建 kustomization.yaml
- Step 2.3: 新建 ArgoCD Application
- Phase 3: 数据准备 — 录制与导出
- Step 3.1: 在 litellm-proxy 中为 OpenCode/QwenCode 启动抓取
- Step 3.2: 导出 warmup 数据
- Phase 4: 部署迁移 — 各模型 YAML 改造
- Step 4.1: 先验证模型（pdev 环境 Qwen3-Coder-Next）
- Step 4.2: 验证通过后，逐步迁移其他模型
- Phase 5: 测试验证 Warmup 效果
- Step 5.1: 功能验证（每个迁移批次必做）
- Step 5.2: 性能效果验证（warmup 前后对比）
- Step 5.3: warmup 数据质量验证
- 四、JSONL Warmup 数据格式规范
- 五、依赖关系
- 六、风险与缓解
- 七、被否决的替代方案
- 八、关键文件清单