## 概述

该Skill是一个 LLM 推理性能分析技能，让Agent连接 Prometheus 实例 `na131t-sw642.eng.t-head.cn:31365`，采集 SGLang 和 vLLM 两个推理引擎上 7 个目标模型的性能指标，支持周级别（weekly）和日级别（daily）两种对比分析模式，生成详细报告。

## 分析模式


| 模式         | 当前周期                   | 对比周期     | 文件夹                  |
| ---------- | ---------------------- | -------- | -------------------- |
| weekly（默认） | 上周完整自然周（周一至周日）         | 上上周完整自然周 | `week_data_reports/` |
| daily      | 昨天 00:00:00 - 23:59:59 | 前天       | `day_data_reports/`  |

## 目标模型

| 短名称                      | Prometheus model_name  | 推理引擎   |
| ------------------------ | ---------------------- | ------ |
| qwen3-coder-next         | Qwen3-Coder-Next       | vLLM   |
| qwen3dot5-397b-a17b-int8 | Qwen3.5-397B-A17B-INT8 | vLLM   |
| minimax-m2dot7           | MiniMax-M2.7           | vLLM   |
| deepseek-v4-flash        | DeepSeek-V4-Flash      | vLLM   |
| qwen3dot6-27b            | Qwen3.6-27B            | vLLM   |
| kimi-k2dot6              | Kimi-K2.6              | SGLang |
| glm-5dot2                | GLM-5.2                | SGLang |

## 采集指标

|   |   |   |   |
|---|---|---|---|
|指标|说明|单位|计算方式|
|TTFT|首Token延迟|ms|`sum(rate( *_sum[5m])) / sum(rate( *_count[5m])) * 1000`|
|TPOT|每Token输出延迟|ms|同上（使用 inter_token_latency 或 request_time_per_output_token）|
|Throughput|请求吞吐量|req/s|`sum(rate(request_success_total / num_requests_total [5m]))`|
|KV Util|KV Cache 利用率|%|按 Pod 独立采集 → 过滤零值 → 按时间点取平均|
|KV Hit Rate|KV Cache 命中率|%|vLLM: `hits / queries * 100`；SGLang: 按 Pod 独立采集 cache_hit_rate → 过滤零值 → 按时间点取平均 → * 100|

## 文件目录结构

```
~/llm_platform/agents_data_analysis/
├── week_data_reports/                     # 周对比报告
│   ├── llms_analysis_reports_YYYYMMDD/    # 每周报告按日期独立文件夹
│   │   ├── llms_analysis_reports_YYYYMMDD.md
│   │   └── llms_analysis_reports_YYYYMMDD.html
│   └── ...
└── day_data_reports/                      # 日对比报告
    ├── llms_analysis_reports_YYYYMMDD_daily/    # 每日报告按日期独立文件夹
    │   ├── llms_analysis_reports_YYYYMMDD_daily.md
    │   └── llms_analysis_reports_YYYYMMDD_daily.html
    └── ...                 # 日对比报告（空，待生成）
```

报告按 `<prefix>` 为文件夹名存放，md 和 html 在同一文件夹内。

## 报告内容结构

### 1. 执行摘要

- 本周/本日分析范围及关键发现
- Top 重要指标变化
### 2. 指标汇总对比

- 各模型在两个周期内的平均值对比表
### 3. 各模型详细统计

每个模型的详细统计表，包含：

- 当前周期数据：Avg、Max、Min、Median、P95、StdDev
- 对比周期数据：Avg、Max、Min、Median、P95、StdDev
- 趋势标注：TTFT/TPOT 使用 🟢↓（改善）或 🔴↑（恶化）彩色箭头
- 变化率：Avg 变化率和 P95 变化率
### 4. 深度分析与建议

- 延迟分析（TTFT/TPOT）
    
- 吞吐量与 KV Cache 容量分析
    
- 后端效率对比
    
- KV Cache 效率分析
    
- 资源压力评估
    
- 模型特性分析
    
- 可执行建议
    

## 关键计算方法

### KV Cache 利用率计算

1. 按每个 Pod 独立采集时间序列
    
2. 过滤掉值为 0 的时间点（仅统计 Pod 有实际推理请求的时段）
    
3. 在相同时间点上，对该模型所有 Pod 的值取平均
    
4. 基于各时间点平均值计算统计量
    
5. 对于 SGLang，按 (pod, engine_type) 独立计算后取平均
    

### KV Cache 命中率计算（SGLang）

与 KV 利用率采用相同逻辑：

1. 按每个 Pod 独立采集 cache_hit_rate 时间序列（0-1 小数）
    
2. 过滤掉值为 0 的时间点
    
3. 在每个时间点上对所有 pod 取平均后 * 100
    
4. 计算 Avg、Max、Min、Median、P95、StdDev
    

### 趋势箭头规则

- TTFT、TPOT：🟢`↓` 绿色 = 延迟下降（改善）；🔴`↑` 红色 = 延迟上升（恶化）
    
- 其他指标：`↑` = 上升；`↓` = 下降；`→` = 持平（纯文字，不带颜色）
    

## 脚本说明

所有 Python 脚本保存在 skill 目录的 `scripts/` 下：

- `fetch_metrics_YYYYMMDD.py`：周分析数据采集脚本
    
- `fetch_metrics_YYYYMMDD_daily.py`：日分析数据采集脚本
    
- `generate_report_YYYYMMDD.py`：周报告生成脚本
    
- `generate_report_YYYYMMDD_daily.py`：日报告生成脚本
    

## 数据来源

Prometheus 地址：`http://na131t-sw642.eng.t-head.cn:31365/api/v1/query\_range\` 采样间隔：5分钟 分析周期（weekly）：完整自然周（周一到周日） 分析周期（daily）：昨天（00:00 - 23:59）

## 后续将与大模型性能分析平台建设结合，定时产出模型平台的实际性能