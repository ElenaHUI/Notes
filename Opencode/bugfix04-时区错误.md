## 问题

web-mgmt 的 `/app/issue-reports` 列表页显示的时间比实际上报时间**多 8 小时**：页面显示 `2026-08-11 18:12:30`，而机器 `date` 是 `10:12:30 CST`。

## 排查过程

分三步收敛：

1. **先排除插件端**。查 `plugins/report-issue/src/`，客户端在 [tui.ts:151](file:///Users/elenay/%E5%B7%A5%E4%BD%9C/opencode/opencode-plugins/plugins/report-issue/src/tui.ts#L151) 和 [server.ts:119](file:///Users/elenay/%E5%B7%A5%E4%BD%9C/opencode/opencode-plugins/plugins/report-issue/src/server.ts#L119)、[server.ts:164](file:///Users/elenay/%E5%B7%A5%E4%BD%9C/opencode/opencode-plugins/plugins/report-issue/src/server.ts#L164) 用 `new Date().toISOString()` 生成 UTC ISO 字符串（带 `Z`），**行为完全正确**。
2. **发现页面显示的字段不是插件上报的 `timestamp`**，而是数据库入库时间 `created_at`（[index.tsx:71-74](file:///Users/elenay/%E5%B7%A5%E4%BD%9C/web-mgmt/src/pages/app/issue-reports/index.tsx#L71-L74)）—— 排查方向由此从插件转向 app-notifier 服务端。
3. **实测 MySQL 时区确认前提**：`@@global.time_zone` / `@@session.time_zone` 均为 `Asia/Shanghai`，`NOW()`=10:34:07 而 `UTC_TIMESTAMP()`=02:34:07；同时 `pymysql.connect()` 未传 `init_command`，会话时区继承全局。

## 根因

**北京时间被谎报成 UTC，浏览器又补偿了一次 +8 小时**：

```
MySQL created_at = 10:12:30（北京墙上时间，DATETIME 不带时区信息）  → pymysql 取出 naive datetime，时区信息丢失  → Flask 3.0 默认 JSON provider 用 http_date()，对 naive 值一律假定 UTC    → "Tue, 11 Aug 2026 10:12:30 GMT"          ← 第一次错：谎报时区  → 前端 dayjs(t) 按 UTC 解析，转本地 +08:00    → 18:12:30                                  ← 第二次错：二次加 8h
```

排查中还发现**同源的第二个 bug**（方向相反）：`_parse_timestamp` / `_format_timestamp` 里 `datetime.fromisoformat()` 正确解析出带 UTC 时区的对象后，`strftime()` **没做 `astimezone` 转换就丢掉了 tzinfo**，导致 `timestamp` 列存 UTC、钉钉消息"上报时间"早 8 小时、JSON 文件落到 UTC 日期目录。有意思的是这两个 bug 恰好互相抵消 —— 如果页面展示 `timestamp` 而非 `created_at`，反而"凑巧"显示正确。

## 解决方案

修改范围锁定在 **app-notifier 一个仓库、2 个文件**：

- **A（必改，解决 +8h）**：`issue_report_db_service.py` 新增 `CN_TZ` + `_iso_dt_fields()`，在 `list_reports()` / `get_report()` 返回前把 naive datetime 显式标注 `Asia/Shanghai` 并输出带偏移的 ISO（`2026-08-11T10:12:30+08:00`）。前端零改动。
- **B（同源修复）**：三处 `_parse_timestamp` / `_format_timestamp` 补 `.astimezone(CN_TZ)`；兜底分支的裸 `datetime.now()` 改为 `datetime.now(CN_TZ)`（Dockerfile 和 k8s-deployment.yaml 都没设 `TZ`，容器内很可能是 UTC）。