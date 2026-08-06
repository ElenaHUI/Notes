### 遇到的两个问题

**问题一：启动时报错**
```
Invalid input: expected string, received array plugin.0
```


v1.1.53 的 plugin schema 是 `z.string().array()`，只接受纯字符串，不认元组 `["file://...", { options }]`。

**问题二：升级后再次启动自动降级**
用户升级 opencode 到兼容版本后，再次启动时 opencode 的 autoupdate 机制会**自动降级回旧版本**，导致问题反复出现。

### 解决方法

**1. 安装时检查版本** — 低于 v1.16.0 直接拒绝安装

**2. 配置格式改为元组** — `["file://...", { options }]` 是 V1 Effect Schema 直接支持的格式

**3. 写入 `autoupdate: false`** — 安装时自动在 server 配置中注入 `"autoupdate": false`，**防止 opencode 启动时自动降级版本**，确保升级后保持兼容版本不被回退