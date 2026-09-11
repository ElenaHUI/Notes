## 1. 项目背景
### 1.1 业务场景
红区部署了 vLLM 和 SGLang 大模型推理服务，用户通过 opencode 客户端访问这些模型进行代码辅助开发。当用户遇到端侧问题（如对话中断无输出、响应异常、连接超时等）时，需要一种快速、低门槛的方式上报问题。

  

一键上报插件（report-issue）就是为此设计的：用户在 opencode 中输入 `/report` 命令，插件自动收集诊断信息（日志、版本、配置、会话信息等），经过脱敏处理后发送到服务端保存，同时推送钉钉群通知相关人员，后续还可在 web 管理页面查看和管理所有上报记录。

  

### 1.2 系统全景

  

```

┌──────────────┐ ┌──────────────┐ ┌──────────────────┐ ┌──────────────┐

│ 用户终端 │ │ opencode │ │ app-notifier │ │ 钉钉群 │

│ │ │ 插件 │ │ 服务端 (Flask) │ │ │

│ /report │────►│ │────►│ │────►│ Markdown │

│ 输入问题描述 │ │ 1.收集诊断信息 │ │ 1.保存JSON文件 │ │ 通知+@成员 │

│ │ │ 2.脱敏处理 │ │ 2.发送钉钉通知 │ │ │

│ │ │ 3.HTTP发送 │ │ 3.存数据库 │ └──────────────┘

└──────────────┘ └──────────────┘ └────────┬─────────┘

│

▼

┌──────────────────┐

│ web-mgmt 前端 │

│ (React) │

│ │

│ 列表页 │

│ 详情页 │

└──────────────────┘

```

  

**数据流说明**：

1. 用户在 opencode TUI 中输入 `/report`，弹出对话框输入问题描述

2. 插件自动收集诊断信息（日志最后 N 行、版本、配置、会话、环境），执行脱敏处理

3. 插件通过 HTTP POST 将报告发送到 app-notifier 服务端

4. 服务端将报告保存为 JSON 文件（按日期分目录），并发送钉钉 Markdown 通知

5. （未来）服务端将报告存入数据库，web-mgmt 前端提供列表查看和详情管理页面

  

---

  

## 2. 当前功能现状

  

### 2.1 已实现功能

  

| 功能 | 状态 | 说明 |

|------|------|------|

| TUI `/report` 命令 | 已实现 | 用户在 opencode 中输入 `/report` 触发上报流程 |

| 问题描述输入 | 已实现 | DialogPrompt 对话框收集用户对问题的文字描述 |

| 诊断信息收集 | 已实现 | 日志（最后 2000 行）、版本、配置、会话、环境信息 |

| 数据脱敏 | 已实现 | API Key、Bearer token、家目录路径、20 个敏感配置字段名 |

| HTTP 发送到服务端 | 已实现 | POST 到 app-notifier `/alert/issue/report` 接口 |

| 发送失败本地兜底 | 已实现 | 保存到 `~/.local/share/opencode/reports/{id}.json` |

| 服务端文件保存 | 已实现 | 按日期分目录保存 JSON 文件到 `/data/issue-reports/` |

| 钉钉群通知 | 已实现 | Markdown 消息推送到钉钉群，支持 @指定成员 |

| Server 插件工具 | 已实现 | 注册 `report_issue` 工具，供 LLM/Agent 主动调用 |

| 数据库持久化 | 未实现 | 当前只保存到文件系统，需要改为数据库存储 |

| web-mgmt 展示页面 | 未实现 | 需要开发前端查看和管理页面 |

| 查询/状态管理 API | 未实现 | 需要新增列表查询、详情查询、状态更新接口 |

  

### 2.2 已有代码清单

  

**插件代码**（opencode-plugins 仓库）：

  

| 文件路径 | 说明 |

|----------|------|

| `opencode-plugins/plugins/report-issue/src/tui.ts` | TUI 插件主逻辑，注册 `/report` 斜杠命令 |

| `opencode-plugins/plugins/report-issue/src/server.ts` | Server 插件，注册 `report_issue` 工具供 LLM 调用 |

| `opencode-plugins/plugins/report-issue/src/types.ts` | 共享类型定义（PluginConfig、IssueReport 等） |

| `opencode-plugins/plugins/report-issue/src/collect.ts` | 诊断信息收集（日志读取、环境信息、报告 ID 生成） |

| `opencode-plugins/plugins/report-issue/src/sanitize.ts` | 脱敏处理（API Key、token、路径、敏感字段） |

| `opencode-plugins/plugins/report-issue/src/send.ts` | HTTP 发送 + 本地兜底保存 |

| `opencode-plugins/plugins/report-issue/config.example.jsonc` | 配置文件示例 |

| `opencode-plugins/plugins/report-issue/install.sh` | 插件专属安装脚本 |

| `opencode-plugins/plugins/report-issue/uninstall.sh` | 插件专属卸载脚本 |

| `opencode-plugins/install.sh` | 通用安装脚本（支持 --list/--plugin/--all） |

| `opencode-plugins/scripts/build.sh` | 构建脚本（生成 tarball + index.json） |

| `opencode-plugins/Dockerfile` | 镜像构建定义 |

  

**服务端代码**（app-notifier 仓库）：

  

| 文件路径 | 说明 |

|----------|------|

| `app-notifier/app/routes/issue_routes.py` | API 路由，接收 POST `/alert/issue/report` |

| `app-notifier/app/services/issue_report_service.py` | 服务逻辑（保存报告 + 构建钉钉消息） |

| `app-notifier/app/models/schemas.py` | 数据模型（`IssueReport` dataclass，第 86-97 行） |

| `app-notifier/app/config.py` | 配置项（`ISSUE_REPORT_*` 系列环境变量，第 96-100 行） |

| `app-notifier/app/services/dingtalk_client.py` | 钉钉客户端（签名 + 发送 + @双写） |

| `app-notifier/app/services/app_info_service.py` | 数据库使用参考（PyMySQL + DictCursor 模式） |

  

**设计文档**：

  

| 文件路径 | 说明 |

|----------|------|

| `opencode-plugins/PUBLISHING.md` | 插件发布机制完整文档 |

| `opencode-plugins/REPORT-ISSUE-DESIGN.md` | 插件设计方案完整文档 |

  

---

  

## 3. 插件发布机制

  

### 3.1 开发环境（绿区）

  

- 开发工具：Qoder IDE

- 代码仓库：`/Users/yuansheng.wzw/Documents/code/opencode-plugins`

- 插件源码目录：`plugins/report-issue/src/`

- 修改代码后需要构建 Docker 镜像并部署到红区才能生效

  

### 3.2 发布流程（绿区到红区）

  

```

1. 绿区 Git push 开发者推送代码到 opencode-plugins 仓库

↓

2. 红区 CI/CD 构建镜像 拉取代码 → docker build → 执行 build.sh

↓

3. 镜像推送到容器仓库 镜像包含 /plugin-files/ 产物目录

↓

4. K8s 部署 file-updater 更新 Deployment 镜像 tag → 触发新 Pod 创建

↓

5. initContainer 同步 将 /plugin-files/ 原子性同步到宿主机共享目录

↓

6. ingress-nginx 提供下载 hostPath 挂载到 ingress-nginx，通过 /files/ 路径对外提供

↓

7. 用户安装 curl | bash 一键安装/更新插件

```

  

**关键点**：

- file-updater 使用 `strategy: Recreate`，确保旧 Pod 先终止再创建，避免并发写冲突

- 每个插件的更新是原子性的（先复制到 .tmp 临时目录，再 mv 替换）

- 会自动清理镜像中已移除的插件

- `SERVER_URL` 环境变量在部署时通过 sed 替换 install.sh 中的默认 URL

  

### 3.3 本地安装/更新插件

  

安装或更新 report-issue 插件（开发环境地址）：

  

```bash

curl -fsSL http://aliwl-sw529.eng.t-head.cn:31762/files/dev/install.sh | bash -s -- \

--plugin report-issue \

--endpoint https://tone.eng.t-head.cn/app-notifier/alert/issue/report

```

  

安装脚本会自动完成以下操作：

1. 下载 `index.json` 确认插件存在

2. 下载插件专属 `install.sh`

3. 下载 tarball、解压到 `~/.config/opencode/plugins/opencode-report-issue/`

4. 更新 `~/.config/opencode/opencode.jsonc` 配置文件，写入插件路径和配置

  

### 3.4 测试流程

  

1. 用上述 curl 命令安装/更新插件

2. 启动 opencode（`opencode` 命令）

3. 在 opencode TUI 中输入 `/report` 测试上报功能

4. 在弹出的对话框中输入问题描述并确认

5. 检查服务端是否收到数据（查看 app-notifier 日志）

6. 检查钉钉群是否收到通知

7. 检查 `/data/issue-reports/` 目录下是否生成了 JSON 文件

  

### 3.5 插件配置

  

插件配置在 `~/.config/opencode/opencode.jsonc` 中，安装脚本会自动写入。配置项说明：

  

| 配置项 | 类型 | 默认值 | 说明 |

|--------|------|--------|------|

| `endpoint` | string | `""` | 服务端上报地址，生产环境为 `https://tone.eng.t-head.cn/app-notifier/alert/issue/report` |

| `maxLogLines` | number | `2000` | 收集日志文件的最大行数（从文件末尾开始读取） |

| `timeout` | number | `30000` | HTTP 请求超时毫秒数，超时后中止请求并本地兜底保存 |

  

配置示例（config.example.jsonc）：

  

```jsonc

{

"$schema": "https://opencode.ai/config.json",

"plugin": [

// TUI 插件：注册 /report 斜杠命令

[

"file:///path/to/opencode-report-issue/src/tui.ts",

{

"endpoint": "https://tone.eng.t-head.cn/app-notifier/alert/issue/report",

"maxLogLines": 2000,

"timeout": 30000

}

],

// Server 插件：注册 report_issue 工具，供 LLM/Agent 主动调用

[

"file:///path/to/opencode-report-issue/src/server.ts",

{

"endpoint": "https://tone.eng.t-head.cn/app-notifier/alert/issue/report",

"maxLogLines": 2000,

"timeout": 30000

}

]

]

}

```

  

修改配置后重启 opencode 生效。

  

---

  

## 4. 开发需求

  

以下是实习生需要完成的开发任务，按优先级排列。前两项是已有功能的调试和确认，后三项是新功能开发。

  

### 4.1 需求一：快速命令上报（已实现，需端到端调试）

  

**当前状态**：TUI `/report` 命令已完整实现，包括命令注册、问题描述输入、诊断信息收集、脱敏、确认对话框、HTTP 发送、失败本地兜底的完整流程。

  

**交互流程**：

1. 用户在 opencode TUI 中输入 `/report`

2. 弹出 DialogPrompt 对话框，提示输入问题描述

3. 用户输入描述并确认后，显示 busy 状态，异步收集诊断信息

4. 收集完成后显示 DialogConfirm 确认对话框，展示摘要信息

5. 用户确认后，显示 busy 状态，异步发送报告到服务端

6. 发送成功显示 success toast；失败则本地兜底保存并显示 error toast

  

**实习生任务**：

- 安装插件后进行端到端测试，走通完整上报流程

- 确认服务端能正确接收数据并保存

- 确认钉钉群能收到通知

- 记录并修复发现的问题

- 特别注意：如果 endpoint 未配置，插件会显示错误 toast 而不会继续

  

### 4.2 需求二：关键诊断信息收集（已实现，需确认完整性）

  

**当前收集的信息**：

  

| 信息类别 | 具体内容 | 来源 |

|----------|----------|------|

| 报告 ID | UUID（`crypto.randomUUID()`） | `collect.ts` → `generateReportId()` |

| 问题描述 | 用户手动输入 | DialogPrompt |

| 上报时间 | ISO 8601 时间戳 | `new Date().toISOString()` |

| 上报人 | 用户名（USER/USERNAME/LOGNAME 环境变量） | `collect.ts` → `getReporter()` |

| opencode 版本 | 版本号、平台、架构 | `api.app.version`、`process.platform`、`process.arch` |

| 日志 | opencode.log 文件最后 N 行（默认 2000 行） | `collect.ts` → `readLogFile()` |

| 配置信息 | opencode 配置（脱敏后） | `api.state.config` |

| 会话信息 | 会话 ID、标题、模型、provider、创建/更新时间 | `api.state.session.get()` |

| 环境信息 | 平台、架构、Node/Bun 版本、进程运行时间 | `collect.ts` → `collectEnvironment()` |

  

**日志读取策略**（`readLogFile` 函数）：

- 日志路径：`$XDG_DATA_HOME/opencode/log/opencode.log`（默认 `~/.local/share/opencode/log/opencode.log`）

- 文件 <= 256KB：整体读取，取最后 N 行

- 文件 > 256KB：从文件末尾以 64KB 为 chunk 反向读取，直到收集够 N 行

  

**脱敏处理**（`sanitize.ts`）：

- API Key：匹配 `sk-` 前缀后跟至少 10 个字母数字字符，替换为 `***REDACTED***`

- Bearer Token：匹配 `Bearer xxx`，替换为 `Bearer ***REDACTED***`

- 家目录路径：替换为 `~`

- 通用 `/home/xxx` 和 `/Users/xxx` 路径：替换为 `***REDACTED***`

- 配置字段：20 个敏感字段名（apikey、token、password、secret 等）递归匹配并脱敏

  

**实习生任务**：

- 确认收集的信息是否足够定位常见的端侧问题

- 如果发现缺少关键信息（如 GPU 型号、模型服务端点等），按需补充收集逻辑

- 确认脱敏规则是否完善，没有遗漏的敏感信息类型

  

### 4.3 需求三：数据库持久化（未实现，需开发）

  

**当前状态**：服务端只将报告保存为 JSON 文件，路径为 `/data/issue-reports/{YYYY-MM-DD}/{HHMMSS}_{report_id}.json`。这种方式无法高效查询和管理。

  

**目标**：将报告保存到数据库，支持列表查询、详情查询、状态更新。

  

#### 4.3.1 数据库表设计

  

基于现有 `IssueReport` dataclass（`app-notifier/app/models/schemas.py` 第 86-97 行）和客户端 `types.ts` 中的 `IssueReport` 接口，建议表结构如下：

  

```sql

CREATE TABLE issue_report (

id VARCHAR(64) NOT NULL COMMENT '报告ID (UUID)',

description TEXT NOT NULL COMMENT '问题描述',

timestamp DATETIME NOT NULL COMMENT '上报时间',

reporter VARCHAR(128) DEFAULT NULL COMMENT '上报人',

version VARCHAR(64) DEFAULT NULL COMMENT 'opencode版本号',

platform VARCHAR(32) DEFAULT NULL COMMENT '运行平台 (linux/darwin)',

arch VARCHAR(32) DEFAULT NULL COMMENT 'CPU架构 (x64/arm64)',

config JSON DEFAULT NULL COMMENT '脱敏后的配置 (JSON)',

session_id VARCHAR(128) DEFAULT NULL COMMENT '会话ID',

session_title VARCHAR(512) DEFAULT NULL COMMENT '会话标题',

model VARCHAR(128) DEFAULT NULL COMMENT '模型ID',

provider VARCHAR(128) DEFAULT NULL COMMENT 'Provider ID',

logs LONGTEXT DEFAULT NULL COMMENT '脱敏后的日志',

environment JSON DEFAULT NULL COMMENT '环境信息 (JSON)',

status VARCHAR(32) NOT NULL DEFAULT 'open' COMMENT '状态: open/in_progress/resolved',

created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '入库时间',

updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

PRIMARY KEY (id),

INDEX idx_status (status),

INDEX idx_reporter (reporter),

INDEX idx_created_at (created_at)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='opencode问题上报';

```

  

**设计说明**：

- `version`、`platform`、`arch` 从原始 `version` 嵌套对象中展平，方便查询

- `session_id`、`session_title`、`model`、`provider` 从原始 `session` 嵌套对象中展平

- `config` 和 `environment` 保留为 JSON 类型（MySQL 5.7+ 原生支持）

- `logs` 使用 LONGTEXT，因为日志可能很长（2000 行）

- `status` 字段是新增的，用于状态管理（原始数据模型中没有）

- `created_at` 和 `updated_at` 是数据库管理的时间戳

  

#### 4.3.2 服务端开发内容

  

**参考现有数据库使用方式**：`app-notifier/app/services/app_info_service.py` 是现成的参考，使用 PyMySQL + DictCursor + 上下文管理器模式。

  

需要开发的内容：

  

1. **新建 `app-notifier/app/services/issue_report_db_service.py`**：

- 参考 `app_info_service.py` 的 `_get_cursor()` 上下文管理器模式

- 实现 `save_to_db(report_data)` 方法：将报告插入数据库

- 实现 `list_reports(page, size, status_filter, reporter_filter)` 方法：分页查询列表

- 实现 `get_report(report_id)` 方法：查询单条详情

- 实现 `update_status(report_id, new_status)` 方法：更新状态

  

2. **修改 `app-notifier/app/routes/issue_routes.py`**：

- 在 `receive_issue_report()` 中，保存文件后同时保存到数据库

- 新增 `GET /alert/issue/list` 路由：分页查询列表（支持 status、reporter 筛选）

- 新增 `GET /alert/issue/<report_id>` 路由：查询单条详情

- 新增 `PUT /alert/issue/<report_id>/status` 路由：更新状态

  

3. **数据库配置**：

- app-notifier 已有 MySQL 配置（`config.py` 中的 `MYSQL_*` 环境变量）

- 数据库名为 `app_mgmt`，可直接在此库中新建 `issue_report` 表

- 无需新增配置项，复用现有的 MySQL 连接参数

  

**数据库连接参考**（来自 `app_info_service.py`）：

  

```python

import pymysql

from pymysql.cursors import DictCursor

from contextlib import contextmanager

  

@contextmanager

def _get_cursor(self):

conn = pymysql.connect(

host=self.host, port=self.port,

user=self.user, password=self.password,

database=self.database, charset=self.charset,

cursorclass=DictCursor,

connect_timeout=3, read_timeout=3, write_timeout=3

)

cursor = conn.cursor()

try:

yield cursor

conn.commit()

except Exception:

conn.rollback()

raise

finally:

cursor.close()

conn.close()

```

  

### 4.4 需求四：web-mgmt 展示页面（未实现，需开发）

  

**目标**：在 web-mgmt 前端开发问题上报查看和管理页面。

  

#### 4.4.1 web-mgmt 技术栈

  

web-mgmt 是一个 **React 19 + TypeScript** 项目（注意：不是 Vue），核心技术栈如下：

  

| 技术 | 版本 | 用途 |

|------|------|------|

| React | 19.2 | 前端框架 |

| TypeScript | 5.8 | 类型系统 |

| Vite | 7.3 | 构建工具 |

| Ant Design | 6.0-alpha | UI 组件库 |

| React Router | 7.18 | 路由（文件约定式自动生成） |

| TanStack Query | 5.101 | 数据请求与缓存 |

| ofetch | 1.5 | HTTP 客户端（封装为 apiFetch） |

| Zustand + Jotai | - | 状态管理 |

| Tailwind CSS | 3.4 | 样式 |

| dayjs | 1.11 | 时间处理 |

| sonner | 2.0 | Toast 通知 |

  

#### 4.4.2 项目结构约定

  

```

web-mgmt/src/

├── pages/ # 页面组件（文件约定式路由自动生成）

│ ├── app/ # /app/* 路由

│ │ ├── index.tsx → /app

│ │ ├── _layout.tsx → /app 的布局组件

│ │ ├── kv-cache-test.tsx → /app/kv-cache-test（参考此页面）

│ │ ├── llm.tsx → /app/llm

│ │ └── [appId]/ → /app/:appId 动态路由

│ │ └── logs.tsx → /app/:appId/logs

│ └── index.tsx → / (首页)

├── queries/ # TanStack Query hooks（数据请求封装）

│ ├── kvCacheTest.ts # 参考此文件

│ ├── app.ts

│ └── ...

├── services/ # API 服务定义

│ └── biz/

│ ├── kvCacheTest.ts # 参考此文件

│ ├── app.ts

│ └── ...

├── components/ # 公共组件

├── lib/

│ └── api-fetch.ts # apiFetch 封装（ofetch 实例，带 SSO 认证）

├── store/ # Zustand 状态

├── hooks/ # 自定义 hooks

├── types/ # 类型定义

└── router.tsx # 路由配置（createBrowserRouter + glob 自动生成）

```

  

#### 4.4.3 路由约定

  

web-mgmt 使用**文件约定式路由**，通过 `import.meta.glob` 自动扫描 `pages/` 目录生成路由：

  

- `pages/app/kv-cache-test.tsx` → 路由 `/app/kv-cache-test`

- `pages/app/[appId]/logs.tsx` → 路由 `/app/:appId/logs`（方括号表示动态参数）

- `pages/app/_layout.tsx` → `/app` 下所有子路由的布局组件

- `pages/app/index.tsx` → `/app` 的默认页面

  

**新建问题上报页面**，建议创建以下文件：

- `pages/app/issue-reports/index.tsx` → 列表页，路由 `/app/issue-reports`

- `pages/app/issue-reports/[id].tsx` → 详情页，路由 `/app/issue-reports/:id`

  

#### 4.4.4 API 调用模式

  

**Service 层**（参考 `services/biz/kvCacheTest.ts`）：

  

```typescript

import { apiFetch } from "@/lib/api-fetch"

  

export interface IssueReportRecord {

id: string

description: string

timestamp: string

reporter: string | null

version: string | null

platform: string | null

arch: string | null

status: "open" | "in_progress" | "resolved"

createdAt: string

// ... 其他字段

}

  

export const issueReportApi = {

list: (params: { status?: string; pageNum?: number; pageSize?: number }) => {

const qs = new URLSearchParams()

if (params.status) qs.set("status", params.status)

qs.set("pageNum", String(params.pageNum ?? 1))

qs.set("pageSize", String(params.pageSize ?? 20))

return apiFetch<{ data: { records: IssueReportRecord[]; total: number } }>(

`/api/app-notifier/alert/issue/list?${qs.toString()}`

)

},

detail: (id: string) =>

apiFetch<{ data: IssueReportRecord }>(`/api/app-notifier/alert/issue/${id}`),

updateStatus: (id: string, status: string) =>

apiFetch(`/api/app-notifier/alert/issue/${id}/status`, { method: "put", body: { status } }),

}

```

  

**注意**：apiFetch 会自动注入 SSO 认证 token 和 trace-id，响应格式约定为 `{ code: 200, data: ..., message: ... }`。

  

**Query hooks 层**（参考 `queries/kvCacheTest.ts`）：

  

```typescript

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { issueReportApi, type IssueReportRecord } from "@/services/biz/issueReport"

  

export const useIssueReportList = (params: { status?: string; pageNum?: number; pageSize?: number }) =>

useQuery({

queryKey: ["issue-report", "list", params],

queryFn: async () => {

const res = await issueReportApi.list(params)

return res?.data

},

})

  

export const useIssueReportDetail = (id: string | null) =>

useQuery({

enabled: !!id,

queryKey: ["issue-report", "detail", id],

queryFn: async () => {

if (!id) return null

const res = await issueReportApi.detail(id)

return res?.data as IssueReportRecord

},

})

  

export const useUpdateIssueReportStatus = () => {

const queryClient = useQueryClient()

return useMutation({

mutationFn: ({ id, status }: { id: string; status: string }) =>

issueReportApi.updateStatus(id, status),

onSuccess: () => {

queryClient.invalidateQueries({ queryKey: ["issue-report"] })

},

})

}

```

  

#### 4.4.5 列表页开发要求

  

参考 `pages/app/kv-cache-test.tsx` 的实现模式（Ant Design Table + TanStack Query）：

  

- **表格列**：报告 ID（截断显示）、上报人、描述（截断 + Tooltip）、模型、状态（Tag 标签）、时间

- **状态筛选**：Tabs 或 Select，支持按 open/in_progress/resolved 筛选

- **分页**：Ant Design Table 内置分页

- **刷新按钮**：手动触发 refetch

- **点击行**：跳转到详情页

  

状态 Tag 颜色映射建议：

- `open` → `error`（红色）

- `in_progress` → `processing`（蓝色）

- `resolved` → `success`（绿色）

  

#### 4.4.6 详情页开发要求

  

- 展示完整报告信息（所有字段）

- 日志内容：使用等宽字体展示，支持滚动，可折叠/展开

- 配置信息：JSON 格式化展示（可使用 Monaco Editor 组件，项目已集成 `@monaco-editor/react`）

- 状态管理：Select 下拉框切换状态（open → in_progress → resolved），调用更新接口

- 返回按钮：回到列表页

  

### 4.5 需求五：钉钉群通知（已实现，需确认）

  

**当前状态**：服务端收到报告后，构建 Markdown 消息推送到钉钉群。

  

**通知内容**：

  

```markdown

## 📋 opencode 问题上报

  

**报告ID**：a1b2c3d4-e5f6-7890-abcd-ef1234567890

  

**上报人**：yuansheng.wzw

  

**描述**：对话中断无输出，重启后恢复正常（截断到 100 字符）

  

**版本**：0.5.12

  

**平台**：linux/arm64

  

**会话**：abc123 (调试内存泄漏问题)

  

**模型**：anthropic/claude-sonnet-4-20250514

  

**上报时间**：2026-07-22 14:30:52

  

**保存路径**：/data/issue-reports/2026-07-22/143052_a1b2c3d4.json

  

@488387 @WB01996832

```

  

**@成员机制**：同时通过 `at.atUserIds` 和正文末尾 `@工号` 双写实现 @功能。工号列表来自 `ISSUE_REPORT_AT_USERS` 环境变量（逗号分隔）。

  

**配置项**（`app-notifier/app/config.py`）：

  

| 环境变量 | 默认值 | 说明 |

|----------|--------|------|

| `ISSUE_REPORT_WEBHOOK_URL` | `""` | 钉钉 Webhook 地址（空则跳过通知） |

| `ISSUE_REPORT_WEBHOOK_SECRET` | `""` | 钉钉 Webhook 签名密钥 |

| `ISSUE_REPORT_AT_USERS` | `""` | 逗号分隔的 @用户工号列表 |

| `REQUEST_TIMEOUT` | `10` | 钉钉发送 HTTP 超时秒数 |

  

**实习生任务**：

- 确认通知格式和内容是否满足需求

- 未来可在通知中添加 web-mgmt 详情页链接（待前端页面开发完成后）

  

---

  

## 5. 代码结构说明

  

### 5.1 插件代码（opencode-plugins/plugins/report-issue/src/）

  

| 文件 | 职责 | 关键函数/导出 |

|------|------|--------------|

| `tui.ts` | TUI 交互主逻辑，注册 `/report` 斜杠命令 | `tui`（默认导出），`parseConfig`，`getCurrentSessionID`，`extractSessionInfo` |

| `server.ts` | Server 插件，注册 `report_issue` 工具供 LLM 调用 | `server`（默认导出），使用 zod 定义参数 schema |

| `types.ts` | 共享类型定义 | `PluginConfig`，`IssueReport`，`ReportVersion`，`ReportSession`，`ReportEnvironment`，`ReportResult` |

| `collect.ts` | 诊断信息收集 | `readLogFile`，`collectEnvironment`，`generateReportId`，`getReporter`，`getLogFilePath` |

| `sanitize.ts` | 脱敏处理 | `sanitizeConfig`，`sanitizeLogs`，`sanitizeString`，`sanitizeValue`，`isSensitiveKey` |

| `send.ts` | HTTP 发送 + 本地兜底 | `sendReport`，`saveLocalFallback` |

  

**重要设计特点**：

- TUI 插件零 npm 运行时依赖（仅 `import type` + Node.js 内置模块），适合红区分发

- Server 插件依赖 `zod` 运行时库

- 脱敏处理在发送前完成，确保敏感信息不会离开客户端

- 发送失败时自动本地兜底保存到 `~/.local/share/opencode/reports/{id}.json`

  

### 5.2 服务端代码（app-notifier/）

  

| 文件 | 职责 | 关键函数/类 |

|------|------|------------|

| `app/routes/issue_routes.py` | API 路由 | `receive_issue_report()` — POST `/alert/issue/report` |

| `app/services/issue_report_service.py` | 服务逻辑 | `IssueReportService.save_report()`，`build_dingtalk_message()`，`_parse_timestamp()`，`_format_timestamp()` |

| `app/models/schemas.py` | 数据模型 | `IssueReport` dataclass（第 86-97 行） |

| `app/config.py` | 配置项 | `ISSUE_REPORT_SAVE_DIR`，`ISSUE_REPORT_WEBHOOK_URL`，`ISSUE_REPORT_WEBHOOK_SECRET`，`ISSUE_REPORT_AT_USERS`（第 96-100 行） |

| `app/services/dingtalk_client.py` | 钉钉客户端 | `DingTalkClient.send()`，`build_markdown_message()`，`get_signature()` |

| `app/services/app_info_service.py` | DB 使用参考 | `AppInfoService._get_cursor()` — PyMySQL 上下文管理器模式 |

| `app/__init__.py` | Flask 应用工厂 | 蓝图注册 `issue_bp`，url_prefix `/alert/issue` |

  

**服务端处理流程**（`issue_routes.py` → `receive_issue_report`）：

1. `request.get_json(force=True)` 解析请求体

2. 校验 `id`、`description`、`timestamp` 三个必填字段

3. `IssueReportService.save_report()` 保存到文件系统（按日期分目录）

4. 发送钉钉通知（独立处理，失败不影响保存结果）

5. 返回 `{ success: true, id: report_id, message: "问题报告已保存" }`

  

**文件保存路径规则**：

- 根目录：`ISSUE_REPORT_SAVE_DIR`（默认 `/data/issue-reports`）

- 子目录：`{YYYY-MM-DD}/`（按日期）

- 文件名：`{HHMMSS}_{report_id}.json`

- 示例：`/data/issue-reports/2026-07-22/143052_a1b2c3d4-e5f6-7890-abcd-ef1234567890.json`

  

### 5.3 前端代码（web-mgmt/）

  

web-mgmt 是 React 19 + TypeScript + Vite 项目，使用 Ant Design 6 作为 UI 框架。

  

**技术栈**：React 19 + TypeScript 5.8 + Vite 7.3 + Ant Design 6 + React Router 7 + TanStack Query 5 + ofetch + Zustand/Jotai + Tailwind CSS 3.4

  

**关键目录结构**：

  

| 目录 | 用途 | 新增文件位置 |

|------|------|------------|

| `src/pages/` | 页面组件（文件约定式路由） | `pages/app/issue-reports/index.tsx`（列表页）、`pages/app/issue-reports/[id].tsx`（详情页） |

| `src/queries/` | TanStack Query hooks | `queries/issueReport.ts` |

| `src/services/biz/` | API 服务定义 | `services/biz/issueReport.ts` |

| `src/lib/api-fetch.ts` | apiFetch 封装（ofetch 实例，带 SSO 认证、trace-id） | 无需修改，直接使用 |

| `src/components/` | 公共组件 | 按需新增 |

| `src/store/` | Zustand 状态管理 | 按需新增 |

  

**参考页面**：`src/pages/app/kv-cache-test.tsx` 是一个典型的列表页面，包含 Table + 分页 + Tabs 筛选 + 操作按钮，是开发问题上报列表页的最佳参考。

  

**参考 API 定义**：`src/services/biz/kvCacheTest.ts` 展示了标准的 API service 定义模式。

  

**参考 Query hooks**：`src/queries/kvCacheTest.ts` 展示了标准的 TanStack Query hooks 封装模式（useQuery + useMutation + useQueryClient）。

  

**开发代理配置**（`vite.config.ts`）：

- `/api` 代理到 `https://tone{EnvKey}.eng.t-head.cn/api`（gprod 环境为 `tone-g`）

- 开发时通过 `pnpm dev` 或 `APP_ENV=gprod pnpm dev` 启动

  

---

  

## 6. 开发步骤建议

  

### 第一阶段：环境搭建和现有功能调试（优先级：高）

  

1. 在绿区用 Qoder 打开 `opencode-plugins` 仓库

2. 阅读本文档和 `REPORT-ISSUE-DESIGN.md` 了解设计思路

3. 用 curl 命令安装插件到本地：

```bash

curl -fsSL http://aliwl-sw529.eng.t-head.cn:31762/files/dev/install.sh | bash -s -- \

--plugin report-issue \

--endpoint https://tone.eng.t-head.cn/app-notifier/alert/issue/report

```

4. 启动 opencode，在 TUI 中输入 `/report` 测试上报功能

5. 确认服务端能收到数据（查看 app-notifier 日志和 `/data/issue-reports/` 目录）

6. 确认钉钉群能收到通知

7. 记录发现的问题并修复

  

### 第二阶段：数据库持久化（优先级：高）

  

1. 在 `app_mgmt` 数据库中创建 `issue_report` 表（使用第 4.3.1 节的 DDL）

2. 参考 `app_info_service.py` 的 PyMySQL 模式，新建 `issue_report_db_service.py`

3. 实现 `save_to_db()`、`list_reports()`、`get_report()`、`update_status()` 方法

4. 修改 `issue_routes.py`，在保存文件后同时保存到数据库

5. 新增查询 API 路由：

- `GET /alert/issue/list` — 分页查询列表

- `GET /alert/issue/<report_id>` — 查询单条详情

- `PUT /alert/issue/<report_id>/status` — 更新状态

6. 用 curl 或 Postman 测试所有 API

  

### 第三阶段：web-mgmt 前端页面（优先级：中）

  

1. 在绿区用 Qoder 打开 `web-mgmt` 仓库

2. 阅读 `src/pages/app/kv-cache-test.tsx` 了解列表页开发模式

3. 阅读 `src/services/biz/kvCacheTest.ts` 和 `src/queries/kvCacheTest.ts` 了解 API 和 hooks 模式

4. 新建 `src/services/biz/issueReport.ts` — API 服务定义

5. 新建 `src/queries/issueReport.ts` — TanStack Query hooks

6. 新建 `src/pages/app/issue-reports/index.tsx` — 列表页

7. 新建 `src/pages/app/issue-reports/[id].tsx` — 详情页

8. `pnpm dev` 启动开发服务器，本地测试页面功能

  

### 第四阶段：联调和优化（优先级：中）

  

1. 完整流程测试：opencode 上报 → 服务端保存（文件+数据库）→ 钉钉通知 → web-mgmt 查看

2. 修复发现的问题

3. 优化用户体验（如钉钉通知中添加 web-mgmt 详情页链接）

4. 代码 review 和清理

  

---

  

## 7. 关键信息速查

  

### 7.1 重要路径

  

| 类别 | 路径 |

|------|------|

| 插件代码 | `/Users/yuansheng.wzw/Documents/code/opencode-plugins/plugins/report-issue/` |

| 插件源码 | `/Users/yuansheng.wzw/Documents/code/opencode-plugins/plugins/report-issue/src/` |

| 服务端代码 | `/Users/yuansheng.wzw/Documents/code/app-notifier/` |

| 服务端路由 | `/Users/yuansheng.wzw/Documents/code/app-notifier/app/routes/issue_routes.py` |

| 服务端逻辑 | `/Users/yuansheng.wzw/Documents/code/app-notifier/app/services/issue_report_service.py` |

| 数据模型 | `/Users/yuansheng.wzw/Documents/code/app-notifier/app/models/schemas.py`（第 86-97 行） |

| 服务端配置 | `/Users/yuansheng.wzw/Documents/code/app-notifier/app/config.py`（第 96-100 行） |

| DB 使用参考 | `/Users/yuansheng.wzw/Documents/code/app-notifier/app/services/app_info_service.py` |

| 前端代码 | `/Users/yuansheng.wzw/Documents/code/web-mgmt/` |

| 前端参考页面 | `/Users/yuansheng.wzw/Documents/code/web-mgmt/src/pages/app/kv-cache-test.tsx` |

| 前端参考 API | `/Users/yuansheng.wzw/Documents/code/web-mgmt/src/services/biz/kvCacheTest.ts` |

| 前端参考 hooks | `/Users/yuansheng.wzw/Documents/code/web-mgmt/src/queries/kvCacheTest.ts` |

| 前端 API 封装 | `/Users/yuansheng.wzw/Documents/code/web-mgmt/src/lib/api-fetch.ts` |

| K8s 部署 | `/Users/yuansheng.wzw/Documents/code/gitea-app-manifests/foundation/nginx-file-server/dev/deploy.yaml` |

| 发布方案文档 | `/Users/yuansheng.wzw/Documents/code/opencode-plugins/PUBLISHING.md` |

| 设计方案文档 | `/Users/yuansheng.wzw/Documents/code/opencode-plugins/REPORT-ISSUE-DESIGN.md` |

  

### 7.2 重要 URL

  

| 用途 | URL |

|------|-----|

| 插件安装脚本（开发环境） | `http://aliwl-sw529.eng.t-head.cn:31762/files/dev/install.sh` |

| 插件安装脚本（生产环境） | `http://na131t-sw693.eng.t-head.cn:31762/files/prod/install.sh` |

| 服务端上报 API | `https://tone.eng.t-head.cn/app-notifier/alert/issue/report` |

| app-notifier 服务 | `https://tone.eng.t-head.cn/app-notifier` |

| web-mgmt 开发代理（gprod） | `https://tone-g.eng.t-head.cn/api` |

  

### 7.3 插件安装命令

  

```bash

# 安装或更新 report-issue 插件（开发环境）

curl -fsSL http://aliwl-sw529.eng.t-head.cn:31762/files/dev/install.sh | bash -s -- \

--plugin report-issue \

--endpoint https://tone.eng.t-head.cn/app-notifier/alert/issue/report

  

# 列出可用插件

curl -fsSL http://aliwl-sw529.eng.t-head.cn:31762/files/dev/install.sh | bash -s -- --list

  

# 卸载插件

curl -fsSL http://aliwl-sw529.eng.t-head.cn:31762/files/dev/uninstall.sh | bash -s -- --plugin report-issue --force

```

  

### 7.4 服务端 API

  

**现有接口**：

  

| 方法 | 路径 | 说明 |

|------|------|------|

| POST | `/alert/issue/report` | 接收问题上报（已实现） |

  

**需要新增的接口**：

  

| 方法 | 路径 | 说明 |

|------|------|------|

| GET | `/alert/issue/list` | 分页查询列表（支持 status、reporter 筛选） |

| GET | `/alert/issue/<id>` | 查询单条详情 |

| PUT | `/alert/issue/<id>/status` | 更新状态（open/in_progress/resolved） |

  

### 7.5 参考文档

  

| 文档 | 路径 | 内容 |

|------|------|------|

| PUBLISHING.md | `opencode-plugins/PUBLISHING.md` | 插件发布机制完整说明（Docker 构建、K8s 部署、ingress-nginx 配置、安装脚本） |

| REPORT-ISSUE-DESIGN.md | `opencode-plugins/REPORT-ISSUE-DESIGN.md` | 插件设计方案完整说明（架构、数据模型、脱敏规则、交互流程、服务端处理） |

| 本文档 | `opencode-plugins/INTERN-HANDOVER.md` | 实习生交接文档（本文） |