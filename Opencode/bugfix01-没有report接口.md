### 一、现象

安装插件完成后重启 OpenCode，**没有 `/report`**。输入 `/` 查看斜杠命令列表，`/report` 命令不存在。
### 三、排查与定位

通过逐步排查，发现两个独立的问题叠加导致了同一现象：

#### 问题一：TUI 插件配置写入了错误文件

安装脚本将 TUI 和 Server 两个插件条目都写入了 `.opencode/opencode.jsonc`：

```jsonc
// .opencode/opencode.jsonc（错误 — TUI 条目不应在这里）
"plugin": [
  ["file://.../src/tui.ts", { ... }],      // ← TUI 条目放错了
  ["file://.../src/server.ts", { ... }],   // ← Server 条目正确
]
```

查阅 OpenCode 源码 [tui.ts](file:///Users/elenay/工作/opencode/packages/opencode/src/config/tui.ts#L176)，TUI 配置加载逻辑只从 `tui.json`/`tui.jsonc` 文件读取 `plugin` 数组：

```ts
// 第 176 行 — 只查找名为 "tui" 的配置文件
const projectFiles = yield* ConfigPaths.files("tui", ctx.directory)

// 第 184 行 — 全局也只查 tui 配置
for (const file of ConfigPaths.fileInDirectory(Global.Path.config, "tui")) { ... }
```

**结论**：TUI 配置系统完全不读 `opencode.jsonc`，TUI 插件条目必须放在 `tui.json` 中。

#### 问题二：文件型插件缺少 `id` 导出

配置文件位置修正后仍然没有 `/report`。查看 OpenCode 日志：

```
ERROR: failed to load plugin path=.../server.ts error="Path plugin ... must export id"
ERROR: failed to load plugin path=.../tui.ts error="must default export an object with server()"
```

查阅插件加载验证逻辑 [shared.ts](file:///Users/elenay/工作/opencode/packages/opencode/src/plugin/shared.ts#L306-L316)，`resolvePluginId()` 函数对 `file://` 协议的插件强制要求导出 `id`：

```ts
// 第 313-316 行
if (source === "file") {
  if (id) return id
  throw new TypeError(`Path plugin ${spec} must export id`)
}
```

原始导出写法缺少 `id` 字段：
```ts
// tui.ts — 修复前
export default { tui }

// server.ts — 修复前
export default { server: ReportPlugin }
```

**结论**：`file://` 协议的文件型插件必须在默认导出对象中包含 `id` 字段。npm 包型插件从 `package.json` 的 `name` 字段获取 ID，不受此限制。

---

### 四、修复

#### 4.1 配置文件分离

将 TUI 条目从 `opencode.jsonc` 移到 `tui.json`：

```json
// .opencode/tui.json（新建）
[
  "file:///Users/elenay/.config/opencode/plugins/opencode-report-issue/src/tui.ts",
  { "endpoint": "https://tone.eng.t-head.cn/app-notifier/alert/issue/report", "maxLogLines": 2000, "timeout": 30000 }
]
```

```jsonc
// .opencode/opencode.jsonc（只保留 Server 条目）
"plugin": [
  ["file://.../src/server.ts", { "endpoint": "...", "maxLogLines": 2000, "timeout": 30000 }]
]
```

#### 4.2 添加 `id` 导出

**[tui.ts](file:///Users/elenay/工作/opencode/opencode-plugins/plugins/report-issue/src/tui.ts#L267)**:
```ts
export default { id: "opencode-report-issue", tui }
```

**[server.ts](file:///Users/elenay/工作/opencode/opencode-plugins/plugins/report-issue/src/server.ts#L195)**:
```ts
export default { id: "opencode-report-issue", server: ReportPlugin }
```

修复后重启，`/report` 命令正常出现。

---

### 五、源码仓库同步

将修复同步回 `/Users/elenay/工作/opencode/opencode-plugins/plugins/report-issue/`，共修改 **6 个文件**：

| 文件 | 修改内容 |
|------|----------|
| `src/tui.ts` | `export default` 添加 `id: "opencode-report-issue"` |
| `src/server.ts` | `export default` 添加 `id: "opencode-report-issue"` |
| `config.example.jsonc` | 拆分为 Server 配置示例（`opencode.jsonc`）和 TUI 配置示例（`tui.json`，注释形式） |
| `install.sh` | 新增 `find_tui_config_file()`；`update_config()` 增加 `mode` 参数；`main()` 分两次写入 `opencode.jsonc`（server）和 `tui.json`（tui） |
| `uninstall.sh` | 新增 `find_tui_config_file()`；卸载时同时清理两个配置文件 |
| `README.md` | 更新安装说明，配置示例拆分为两部分 |

---

### 六、总结

| 问题 | 根因 | 参考源码 | 修复 |
|------|------|----------|------|
| 配置位置错误 | TUI 只读 `tui.json`，不读 `opencode.jsonc` | [tui.ts#L176](file:///Users/elenay/工作/opencode/packages/opencode/src/config/tui.ts#L176) | TUI 条目移到 `tui.json` |
| 插件加载失败 | `file://` 插件必须导出 `id` 字段 | [shared.ts#L313-L315](file:///Users/elenay/工作/opencode/packages/opencode/src/plugin/shared.ts#L313-L315) | `export default` 添加 `id` |
