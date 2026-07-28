![[Pasted image 20260728113913.png]]

### 现象

opencode 插件向 `https://tone-dev.eng.t-head.cn/app-notifier/alert/issue/report` 上报问题时报 **403 Forbidden**。

### 排查过程

|步骤|排查内容|发现|
|---|---|---|
|1|对比请求 URL|插件请求出现了 `:8443` 端口，curl 用默认 443|
|2|测试 8443 端口|`Connection reset by peer`，8443 不通|
|3|排除 URL 差异|插件确认没有配置 8443，是代理内部行为|
|4|排除 User-Agent|用插件 UA `opencode/1.17.15` 发 curl 成功，不是 UA 问题|
|5|测试大请求体（100MB）|返回 413，nginx 有 body 限制，但插件请求只有 1.2KB|
|6|抓包看插件实际请求|请求头正常，Content-Length 1212 字节，排除大小问题|
|7|逐步测试 JSON 内容|发送简单 JSON 成功，发送插件完整 JSON 失败|
|8|二分法定位字段|确认是 `logs` 字段内容触发 403|
|9|逐词测试|`shell` 单独 → 200；`/bin/bash` 单独 → 403；`shell=/bin/bash` → 403|
|10|确认根因|WAF 匹配到 `/bin/bash` 路径特征，判定为命令注入攻击，拦截请求|

### 根因

opencode 插件上报的日志内容中包含 `/bin/bash` 字符串（如 `shell=/bin/bash`），被公司 **Tengine WAF** 匹配到**命令注入/路径穿越规则**，请求在到达 app-notifier 之前就被拦截返回 403。

### 解决方法

找相关人员放行