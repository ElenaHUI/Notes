
## 前置条件

构建机必须是 **Linux x86_64 且能访问 npm registry**。

不能用 macOS：`node-pty` 安装时按当前平台用 node-gyp 现编译，landlock 的 `os: linux` optionalDependencies 在 macOS 上会被跳过。只有 Mac 时用 `--platform linux/amd64` 的 Docker 容器执行全部步骤。

目标机要求：Linux x86_64、glibc ≥ 2.28（`ldd --version | head -1` 确认）。

---

## 步骤 1：安装应用闭包

```sh
mkdir -p /tmp/dsh-npm && cd /tmp/dsh-npm
npm init -y
npm install @deepseek-ai/dsh

ls /tmp/dsh-npm/node_modules/@deepseek-ai/dsh/lib/bin.js
```

registry 不可达时先配代理：
```sh
npm config set proxy "$http_proxy"
npm config set https-proxy "$https_proxy"
```

---

## 步骤 2：下载 Node 运行时

```sh
cd /tmp
NODE_VER=v22.23.2
curl -fLO "https://nodejs.org/dist/${NODE_VER}/node-${NODE_VER}-linux-x64.tar.xz"
```

---

## 步骤 3：组装 bundle 目录

```sh
cd /tmp
rm -rf dsh-bundle && mkdir dsh-bundle

tar xf "node-${NODE_VER}-linux-x64.tar.xz" -C dsh-bundle
mv "dsh-bundle/node-${NODE_VER}-linux-x64" dsh-bundle/node

cp -r /tmp/dsh-npm dsh-bundle/app
```

---

## 步骤 4：写启动脚本

```sh
cat > /tmp/dsh-bundle/start.sh <<'EOF'
#!/bin/sh
DIR=$(cd "$(dirname "$0")" && pwd)

# 首次启动播种默认模型配置。settings.yaml 同时是 Web 模型设置页的写入目标，
# 已存在时不得覆写，否则会抹掉用户在界面上做的选择。
DSH_HOME_DIR="${DSH_HOME:-$HOME/.dsh}"
SETTINGS="$DSH_HOME_DIR/settings.yaml"
if [ ! -e "$SETTINGS" ]; then
  mkdir -p "$DSH_HOME_DIR"
  cat > "$SETTINGS" <<'YAML'
llm-pi-ai:
  providers:
    tone:
      api: openai-completions
      baseURL: https://openapi-devops-pprod.eng.t-head.cn/v1
      apiKeyEnv: TONE_API_KEY
      models:
        - id: Qwen3-Coder-Next
          input: [ text ]
        - id: Qwen3.5-397B-A17B-INT8
          input: [ text, image ]
        - id: MiniMax-M2.7
          input: [ text ]
        - id: DeepSeek-V4-Flash
          input: [ text ]
        - id: Kimi-K2.6
          input: [ text ]
        - id: Qwen3.6-27B
          input: [ text ]
agent-default-model:
  provider: tone
  model: DeepSeek-V4-Flash
YAML
  echo "已写入默认模型配置：$SETTINGS" >&2
fi

# 端口交由操作系统分配，避免多人或多实例在同一台机器上冲突。
# 用户显式传入的 --port 仍然优先。
if [ "$1" = "web" ]; then
  has_port=0
  for arg in "$@"; do
    case "$arg" in
      --port|--port=*) has_port=1 ;;
    esac
  done
  if [ "$has_port" = 0 ]; then
    set -- "$@" --port 0
  fi
fi

exec "$DIR/node/bin/node" "$DIR/app/node_modules/@deepseek-ai/dsh/lib/bin.js" "$@"
EOF
chmod +x /tmp/dsh-bundle/start.sh
```

### 结构检查

```sh
ls /tmp/dsh-bundle/                                             # 期望 app  node  start.sh
ls /tmp/dsh-bundle/node/bin/node
ls /tmp/dsh-bundle/app/node_modules/@deepseek-ai/dsh/lib/bin.js
```

三条都要有输出。

---

## 步骤 5：生成自解压单文件

```sh
cd /tmp
tar czf dsh-bundle.tar.gz dsh-bundle

cat > header.sh <<'HEADER'
#!/bin/sh
set -e
DIR="${DSH_INSTALL_DIR:-$HOME/.dsh-bundle}"
if [ ! -f "$DIR/start.sh" ]; then
  echo "首次运行，正在解压到 $DIR ..." >&2
  mkdir -p "$DIR"
  LINE=$(awk '/^__PAYLOAD_BELOW__$/{print NR+1; exit}' "$0")
  tail -n +"$LINE" "$0" | tar xz -C "$DIR" --strip-components=1
  echo "解压完成" >&2
fi
exec sh "$DIR/start.sh" "$@"
__PAYLOAD_BELOW__
HEADER

cat header.sh dsh-bundle.tar.gz > dsh.sh
ls -lh dsh.sh dsh-bundle.tar.gz
```

`dsh.sh` 大小应与 `dsh-bundle.tar.gz` 接近。

header 里两处设计要保留：
- 最后一行 `exec` 在解释器读到二进制载荷前替换进程映像，shell 永不把 tar 数据当脚本解析
- 用 `exec sh "$DIR/start.sh"` 和 `[ ! -f ]`（而非 `[ ! -x ]`），流程不依赖执行权限位——摆渡系统与 FAT 介质会丢失该位

---

## 步骤 6：验证

```sh
rm -rf /tmp/verify && mkdir -p /tmp/verify
cd /tmp
env -i HOME=/tmp/verify PATH=/usr/bin:/bin TONE_API_KEY=dummy sh /tmp/dsh.sh web
```

`env -i` 清空全部环境变量、`PATH` 中无 node。应依次看到：

1. `首次运行，正在解压到 /tmp/verify/.dsh-bundle ...`
2. `已写入默认模型配置：/tmp/verify/.dsh/settings.yaml`
3. 一个随机端口的地址，如 `http://127.0.0.1:41237`

再跑一次应换成另一个端口。另开终端确认播种内容：

```sh
cat /tmp/verify/.dsh/settings.yaml
```

浏览器打开后进模型选择器，应看到 tone 的 6 个模型、默认选中 `DeepSeek-V4-Flash`。

---

## 步骤 7：交付

```sh
cp /tmp/dsh.sh /ppusw/share/yanyihui-dsh/
chmod 755 /ppusw/share/yanyihui-dsh/dsh.sh
chmod 755 /ppusw/share/yanyihui-dsh
ls -ld /ppusw/share /ppusw/share/yanyihui-dsh
```

上层目录对 others 需有 `x` 位，否则他人无法穿越进入。

---

## 用户使用

```sh
cp /ppusw/share/yanyihui-dsh/dsh.sh ~/
cd ~
export TONE_API_KEY=实际的key
sh dsh.sh web
```

记下打印出的端口，浏览器打开该地址。ssh 登录的场景在自己电脑上建隧道：

```sh
ssh -L 41237:127.0.0.1:41237 用户名@目标机器
```

两处端口都换成当次实际的值。

---

## 机制说明

| 项 | 说明 |
|---|---|
| 配置文件 | `$DSH_HOME/settings.yaml`，`$DSH_HOME` 默认 `~/.dsh` |
| `llm-pi-ai` 为何生效 | base bundle 里已挂载但 dormant，settings 提供 provider profiles 后路由才注册上线 |
| `agent-default-model` | 正式 settings 命名空间，字段 `{provider, model, reasoningEffort?}`，settings 层覆盖组合层 |
| `models` 语义 | **替换**该 provider 的目录，不追加；只影响 `tone` 路由，不影响 `deepseek-official` |
| `apiKeyEnv` | 只声明去哪个环境变量取 key，不含 key 本身 |
| 播种时机 | 仅当 `settings.yaml` 不存在时。该文件也是 Web 模型设置页的写入目标，覆写会抹掉用户选择 |
| 端口 | 产品默认 3080（`cordis.patch.yml`），本包注入 `--port 0` 改为随机分配 |
| 网络暴露 | `--host 0.0.0.0` 被 `startup.ts` 硬性拒绝：界面无认证，暴露等于开放无认证远程代码执行。远程访问只能用 ssh 端口转发 |

---

## 已排除的方案

**`pnpm deploy --filter @deepseek-ai/dsh --prod`** —— 闭包启动即报 `ERR_MODULE_NOT_FOUND: @deepseek-ai/cordis-plugin-group`。`dsh-app-boot` 把该包等 9 个依赖只声明为 peerDependencies + devDependencies，而 `@deepseek-ai/dsh` 未列为真实 dependencies；`--prod` 剪掉 devDeps 且不物化 peer，增删 `--config.auto-install-peers` 均无效。仓库内可运行仅靠 pnpm hoisting。

**`npx @deepseek-ai/dsh web`** —— 报 `sh: 1: dsh: not found`，npx 未能链接 bin，必须用显式 `npm install`。

**SEA 单文件二进制** —— `scripts/build-exe-for-python-sdk.ts` 产物入口是 jsonrpc-agent（stdio JSON-RPC 后端），不含 Web UI。改造需替换 `ENTRY_BIN` 并补全 `ASSET_GLOBS`（现仅收 `.js/.json/.node/.wasm`，缺 `.html/.css/.woff2/.svg`），且 `web-app` 通过 `require.resolve('@deepseek-ai/dsh-web-frontend/dist/index.html')` 读磁盘文件，SEA 虚拟文件系统能否解析未经验证。

---

## 排查参考

| 现象 | 处置 |
|---|---|
| glibc 版本错误 | 官方 Node linux-x64 需 glibc ≥ 2.28；CentOS 7（2.17）需改用 unofficial-builds 的旧 glibc 构建 |
| `Permission denied` 写文件 | 当前目录无写权限，`cd` 到可写目录 |
| `sh: 0: Can't open dsh.sh` | 当前目录无该文件，改用绝对路径 |
| 不知道端口是多少 | 前台看屏幕；后台运行须 `tail ~/dsh.log` |
| 模型选择器里没有 tone 的模型 | 检查 `~/.dsh/settings.yaml` 是否已生成、缩进是否正确 |
| 发消息报认证失败 | `TONE_API_KEY` 未设置或无效 |
| 用户仍运行旧版本 | 脚本检测到 `~/.dsh-bundle` 存在会跳过解压。升级须先 `rm -rf ~/.dsh-bundle` |
| 改了播种配置但不生效 | `settings.yaml` 已存在时不会覆写。需 `rm ~/.dsh/settings.yaml` 后重启 |

---

## 升级重打包

应用有新版本时重跑步骤 1，再重跑步骤 3–6；Node 运行时通常无需更换。交付新 `dsh.sh` 时须告知用户先 `rm -rf ~/.dsh-bundle`；若播种配置也变了，还要 `rm ~/.dsh/settings.yaml`。