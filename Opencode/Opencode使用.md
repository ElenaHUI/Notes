### 配置Opencode

- 将全局 OpenCode 配置放在 `~/.config/opencode/opencode.json`中  
    （启动opencode时会自动创建~/.config/opencode文件夹，也可以手动创建此目录文件 `~/.config/opencode/opencode.json`）。
    
- 确认你所在的红区（B红区、T红区，具体看自己申请的红区账号选择，一般来说都选择EU95T，所以选择T红区配置即可）！拷贝下面的配置，并进行个人 API Key（个人API Key的申请在下一步）的替换！
    

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "Tone": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Tone",
      "options": {
        "baseURL": "https://openapi-devops-pprod.eng.t-head.cn/v1",
        "apiKey": "kshrYzOcWemvs8T1nB3TT7uJcTkacCwK"
      },
      "models": {
        "Qwen3-Coder-Next": {
          "name": "Qwen3-Coder-Next",
          "modalities": {
            "input": ["text"],
            "output": ["text"]
          }
        },
        "Qwen3.5-397B-A17B-INT8": {
          "name": "Qwen3.5-397B-A17B-INT8",
          "modalities": {
            "input": ["text", "image"],
            "output": ["text"]
          }
        },
        "MiniMax-M2.7": {
          "name": "MiniMax-M2.7",
          "modalities": {
            "input": ["text"],
            "output": ["text"]
          }
        },
        "DeepSeek-V4-Flash": {
          "name": "DeepSeek-V4-Flash",
          "modalities": {
            "input": ["text"],
            "output": ["text"]
          }
        },
        "Kimi-K2.6": {
          "name": "Kimi-K2.6",
          "modalities": {
            "input": ["text", "image"],
            "output": ["text"]
          }
        },
        "Qwen3.6-27B": {
          "name": "Qwen3.6-27B",
          "modalities": {
            "input": ["text", "image"],
            "output": ["text"]
          }
        }
      }
    }
  },
  "enabled_providers": [
    "Tone"
  ]
}
```


```
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "Qwen3-Coder-Next": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Tone",
      "options": {
        "baseURL": "https://bredzone-openapi-devops.eng.t-head.cn/qwen3-coder-next/v1",
        "apiKey": "YOUR-API-KEY"
      },
      "models": {
        "Qwen3-Coder-Next": {
          "name": "Qwen3-Coder-Next",
          "modalities": {
            "input": ["text"],
            "output": ["text"]
          }
        }
      }
    },
    "Qwen3.5-397B-A17B-INT8": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Tone",
      "options": {
        "baseURL": "https://bredzone-openapi-devops.eng.t-head.cn/qwen3dot5-397b-a17b-int8/v1",
        "apiKey": "YOUR-API-KEY"
      },
      "models": {
        "Qwen3.5-397B-A17B-INT8": {
          "name": "Qwen3.5-397B-A17B-INT8",
          "modalities": {
            "input": ["text", "image"],
            "output": ["text"]
          }
        }
      }
    },
    "MiniMax-M2.7": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Tone",
      "options": {
        "baseURL": "https://bredzone-openapi-devops.eng.t-head.cn/minimax-m2dot7/v1",
        "apiKey": "YOUR-API-KEY"
      },
      "models": {
        "MiniMax-M2.7": {
          "name": "MiniMax-M2.7",
          "modalities": {
            "input": ["text"],
            "output": ["text"]
          }
        }
      }
    },
    "DeepSeek-V4-Flash": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Tone",
      "options": {
        "baseURL": "https://bredzone-openapi-devops.eng.t-head.cn/deepseek-v4-flash/v1",
        "apiKey": "YOUR-API-KEY"
      },
      "models": {
        "DeepSeek-V4-Flash": {
          "name": "DeepSeek-V4-Flash",
          "modalities": {
            "input": ["text"],
            "output": ["text"]
          }
        }
      }
    },
    "Kimi-K2.6": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Tone",
      "options": {
        "baseURL": "https://bredzone-openapi-devops.eng.t-head.cn/kimi-k2dot6/v1",
        "apiKey": "YOUR-API-KEY"
      },
      "models": {
        "Kimi-K2.6": {
          "name": "Kimi-K2.6",
          "modalities": {
            "input": ["text", "image"],
            "output": ["text"]
          }
        }
      }
    },
    "Qwen3.6-27B": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Tone",
      "options": {
        "baseURL": "https://bredzone-openapi-devops.eng.t-head.cn/qwen3dot6-27b/v1",
        "apiKey": "YOUR-API-KEY"
      },
      "models": {
        "Qwen3.6-27B": {
          "name": "Qwen3.6-27B",
          "modalities": {
            "input": ["text", "image"],
            "output": ["text"]
          }
        }
      }
    }
  },
  "enabled_providers": [
    "Qwen3-Coder-Next",
    "Qwen3.5-397B-A17B-INT8",
    "MiniMax-M2.7",
    "DeepSeek-V4-Flash",
    "Kimi-K2.6",
    "Qwen3.6-27B"
  ]
}
```

### 个人API Key申请

在红区机器上进入T-ONE平台[https://tone.eng.t-head.cn/app/llm](https://tone.eng.t-head.cn/app/llm)，点击申请ApiKey申请个人API Key，按照要求填写好理由后，不需要等待审核，点击查看ApiKey可以看到自己的个人API Key，将其替换opencode 的配置文件中`YOUR-API-KEY`

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde55e8e7c60c753e3599e759baf0cb8cef275b8339e1c4c24831b75b38faadcd24bec177c308ebd5304f96f2f6fe391875b460b6a1cee629c1d9a3faf92ba9cf98410a666d87a360b98f836293607c7b2314fb4c8ed7016461c?tmpCode=2d5960fe-184f-47f6-8134-115fcf95831d)

小技巧：由于每次启动opencode都需要清除代理并执行上述的三步，因此可以在～/.bashrc文件中添加下述代码，保存后使配置生效source ～/.bashrc，下一次启动opencode只需要在终端输入opencode即可。

```
# Auto-load and start opencode without proxy interference
opencode() {
    # 1. 清除代理环境变量 (防止网络问题)
    unset HTTPS_PROXY HTTP_PROXY http_proxy https_proxy ALL_PROXY all_proxy

    # 2. 确保 module 命令可用
    if ! type module &>/dev/null; then
        echo "Warning: module command not available. Trying to initialize..."
        # 尝试初始化 module 系统（根据具体服务器环境可能需要调整路径）
        source /etc/profile.d/modules.sh 2>/dev/null || true
    fi

    # 3. 添加模块路径
    module use /tools/common/env/modulefiles

    # 4. 加载指定版本的 opencode
    module load opencode/1.17.15

    # 5. 检查是否加载成功
    if ! command -v opencode &> /dev/null; then
        echo "Error: Failed to load opencode. Please check module availability."
        return 1
    fi

    # 6. 启动 opencode (传入所有参数)
    command opencode "$@"
}
```