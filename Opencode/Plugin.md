插件代码
https://code.alibaba-inc.com/thead_devops/opencode-plugins

服务端代码
https://code.alibaba-inc.com/t-head-native/app-notifier

前端代码
https://code.alibaba-inc.com/thead_devops/web-mgmt

红区访问

发布页面
[https://tone.eng.t-head.cn/app/180/publish](https://tone.eng.t-head.cn/app/180/publish)

启动方式-dev
```bash
curl -fsSL http://aliwl-sw529.eng.t-head.cn:31762/files/dev/install.sh -o /tmp/install.sh
bash /tmp/install.sh --plugin report-issue --endpoint https://tone-dev.eng.t-head.cn/app-notifier/alert/issue/report
```


```bash
curl -fsSL http://aliwl-sw529.eng.t-head.cn:31762/files/dev/install.sh | bash -s -- --plugin report-issue --endpoint https://tone.eng.t-head.cn/app-notifier/alert/issue/report
```
进度：
- [x] dev环境测试 ✅ 2026-07-31
- [x] prod环境测试 ✅ 2026-07-31
- [ ] B红区测试

卸载方式

```shell
curl -fsSL http://aliwl-sw529.eng.t-head.cn:31762/files/prod/uninstall.sh | bash -s -- --all --force
```
