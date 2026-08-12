# 针对Dynamo v1.3.0的Grafana看板 · 公式清单（共 133 处，去重后 121 个）

| 标记 | 位置 | LaTeX | 相同公式的其他标记 |
| --- | --- | --- | --- |
| 〖1〗 | 1. Dynamo Dashboard —— 按模型看 | `1000/ITL` | 11 |
| 〖2〗 | 1. Dynamo Dashboard —— 按模型看 | `E2E \approx TTFT + ITL \times OSL` | 13、38、78 |
| 〖3〗 | Request Success Rate | `\dfrac{N_{req}-N_{internal}}{N_{req}}\times 100\%` | - |
| 〖4〗 | Total Requests | `N_{req}=\Delta C_{requests}` | - |
| 〖5〗 | Input Tokens | `T_{in}=\sum_i ISL_i` | - |
| 〖6〗 | Output Tokens | `T_{out}=\sum_i OSL_i` | - |
| 〖7〗 | Output Tokens | `=\dfrac{T_{out}}{R}` | - |
| 〖8〗 | Output Tokens | `R` | - |
| 〖9〗 | Average TTFT | `\overline{TTFT}=\dfrac{\sum_i TTFT_i}{N_{req}}` | - |
| 〖10〗 | Average ITL | `\overline{ITL}=\dfrac{\sum_i\sum_j ITL_{ij}}{N_{gap}}` | - |
| 〖11〗 | Average ITL | `1000/ITL` | 1 |
| 〖12〗 | Average E2E Latency | `\overline{E2E}=\dfrac{\sum_i E2E_i}{N_{req}}` | - |
| 〖13〗 | Average E2E Latency | `E2E \approx TTFT + ITL \times OSL` | 2、38、78 |
| 〖14〗 | Frontend RPS | `RPS=\dfrac{\Delta N_{req}}{\Delta t}` | - |
| 〖15〗 | E2E Request Latency | `P_q(E2E),\ q\in\{50,90,99\}` | - |
| 〖16〗 | Request Outcome Breakdown | `r_s=\dfrac{\Delta N_s}{\Delta t}` | - |
| 〖17〗 | Request Outcome Breakdown | `s\in\{success,\ cancelled,\ validation,\ overload,\ internal,\ \dots\}` | - |
| 〖18〗 | Active vs Queued Requests | `N_{active}(t)` | - |
| 〖19〗 | Active vs Queued Requests | `N_{queued}(t)=N_{pre}+N_{route}+N_{dispatch}` | - |
| 〖20〗 | TTFT (p50/p90/p99) | `P_q(TTFT)` | - |
| 〖21〗 | ITL (p50/p90/p99) | `P_q(ITL)` | - |
| 〖22〗 | ISL Distribution | `P_q(ISL)` | - |
| 〖23〗 | Output Size Distribution | `P_q(OSL)` | - |
| 〖24〗 | Cached Tokens | `P_q(N_{cached})` | - |
| 〖25〗 | Cached Tokens | `=\dfrac{N_{cached}}{ISL}` | - |
| 〖26〗 | Per-Worker Active Decode Blocks | `B_w(t)` | - |
| 〖27〗 | Per-Worker Active Prefill Tokens | `T_w(t)` | - |
| 〖28〗 | KV Hit Rate Distribution | `H=\dfrac{B_{overlap}}{B_{input}}` | - |
| 〖29〗 | KV Hit Rate Distribution | `P_q(H)` | - |
| 〖30〗 | Routing Overhead Breakdown | `\overline{t_{stage}}=\dfrac{\sum t_{stage}}{N_{stage}}` | - |
| 〖31〗 | Routing Overhead Breakdown | `t_{total}=\sum_{stage} t_{stage}` | - |
| 〖32〗 | KV Events Applied Breakdown | `r_{e,s}=\dfrac{\Delta N_{e,s}}{\Delta t}` | - |
| 〖33〗 | Worker Request Breakdown Per Worker | `r_{inst}=\dfrac{\Delta N_{inst}}{\Delta t}` | - |
| 〖34〗 | Worker Request Breakdown Per Worker | `(inst,\ error\_type)` | - |
| 〖35〗 | Worker Request Duration Per Worker | `P_q(D_{inst})` | - |
| 〖36〗 | Worker Request Duration Per Worker | `D` | - |
| 〖37〗 | Component Throughput (bytes/sec) | `\dfrac{\Delta Bytes}{\Delta t}` | - |
| 〖38〗 | $E2E \approx TTFT + ITL \times OSL$ | `E2E \approx TTFT + ITL \times OSL` | 2、13、78 |
| 〖39〗 | $E2E_{frontend} - D_{worker}$ | `E2E_{frontend} - D_{worker}` | - |
| 〖40〗 | $\dfrac{N_{cached}}{ISL}$ vs $H$（KV Hit Rate） | `\dfrac{N_{cached}}{ISL}` | - |
| 〖41〗 | $\dfrac{N_{cached}}{ISL}$ vs $H$（KV Hit Rate） | `H` | - |
| 〖42〗 | $\dfrac{t_{total}}{TTFT}$ | `\dfrac{t_{total}}{TTFT}` | - |
| 〖43〗 | $\dfrac{t_{total}}{TTFT}$ | `< 5\%\sim10\%` | - |
| 〖44〗 | $N_{queued}$ 与 $P_{99}(TTFT)$ | `N_{queued}` | 82 |
| 〖45〗 | $N_{queued}$ 与 $P_{99}(TTFT)$ | `P_{99}(TTFT)` | - |
| 〖46〗 | Frontend Requests / Sec | `RPS=\dfrac{\Delta N_{req}}{\Delta t}\cdot\mathcal{R}` | - |
| 〖47〗 | Frontend Requests / Sec | `\Delta t=30\text{s}` | - |
| 〖48〗 | Frontend Avg Time to First Token | `\overline{TTFT}=1000\times\dfrac{\Delta\sum_i TTFT_i}{\Delta N_{req}}\cdot\mathcal{R}` | - |
| 〖49〗 | Frontend Avg Request Duration | `\overline{E2E}=1000\times\dfrac{\Delta\sum_i E2E_i}{\Delta N_{req}}\cdot\mathcal{R}` | - |
| 〖50〗 | Frontend Avg Request Duration | `E2E\approx TTFT+ITL\times OSL` | - |
| 〖51〗 | Frontend Avg Inter-Token Latency | `\overline{ITL}=1000\times\dfrac{\Delta\sum ITL}{\Delta N_{gap}}\cdot\mathcal{R}` | - |
| 〖52〗 | Frontend Avg Input/Output Sequence Length | `\overline{ISL}=\dfrac{\Delta\sum ISL}{\Delta N_{req}}` | - |
| 〖53〗 | Frontend Avg Input/Output Sequence Length | `\overline{OSL}` | - |
| 〖54〗 | Frontend Avg Input/Output Sequence Length | `\cdot\mathcal{R}` | 58、62 |
| 〖55〗 | **Frontend Queued Requests** | `N_{queued}(t)=\sum_{pod}\ \sum_{s\in\{preprocess,\ route,\ dispatch\}} N_s(t)\cdot\mathcal{R}` | - |
| 〖56〗 | Prefill Worker Processing Time | `\overline{D_p}=1000\times\dfrac{\Delta\sum D_p}{\Delta N_p}` | - |
| 〖57〗 | Prefill Worker Processing Time | `P_{99}(D_p)` | - |
| 〖58〗 | Prefill Worker Processing Time | `\cdot\mathcal{R}` | 54、62 |
| 〖59〗 | Prefill Worker Throughput | `r_p=\dfrac{\Delta N_p}{\Delta t}\cdot\mathcal{R}` | - |
| 〖60〗 | **Component Latency - Prefill vs Decode** | `\overline{D_p}=\dfrac{\Delta\sum D_p}{\Delta N_p}` | - |
| 〖61〗 | **Component Latency - Prefill vs Decode** | `\overline{D_d}=\dfrac{\Delta\sum D_d}{\Delta N_d}` | - |
| 〖62〗 | **Component Latency - Prefill vs Decode** | `\cdot\mathcal{R}` | 54、58 |
| 〖63〗 | Decode Worker - Request Throughput | `r_d=\dfrac{\Delta N_d}{\Delta t}\cdot\mathcal{R}` | - |
| 〖64〗 | Decode Worker - Avg Request Duration | `\overline{D_d}=\dfrac{\Delta\sum D_d}{\Delta N_d}\cdot\mathcal{R}` | - |
| 〖65〗 | **KV Cache Utilization** | `U_{kv}(t)\cdot\mathcal{R}` | - |
| 〖66〗 | KV Cache Blocks (Total) | `B_{total}(t)\cdot\mathcal{R}` | - |
| 〖67〗 | GPU Compute Utilization | `U_{sm}(t)` | - |
| 〖68〗 | GPU Memory Used | `M_{used}=\dfrac{M_{MiB}}{1024}` | - |
| 〖69〗 | **GPU Memory Bandwidth** | `U_{mem}(t)` | - |
| 〖70〗 | **NVLink Bandwidth** | `BW_{nvl}=\dfrac{\Delta B_{tx}+\Delta B_{rx}}{\Delta t\times 10^9}` | - |
| 〖71〗 | **NVLink Bandwidth** | `\Delta t=1\text{m}` | - |
| 〖72〗 | **Worker CPU Usage** | `C_{cpu}=\dfrac{\Delta t_{cpu}}{\Delta t}\cdot\mathcal{R}` | - |
| 〖73〗 | Node CPU Utilization | `U_{node}=100-100\times\overline{\left(\dfrac{\Delta t_{idle}}{\Delta t}\right)}` | - |
| 〖74〗 | Worker Request Throughput | `r_c=\dfrac{\Delta N_c}{\Delta t}\cdot\mathcal{R}` | - |
| 〖75〗 | Worker Request Throughput | `r_p\approx r_d` | - |
| 〖76〗 | Worker Data Transfer | `\dfrac{\Delta B_{req}}{\Delta t}` | - |
| 〖77〗 | Worker Data Transfer | `\dfrac{\Delta B_{resp}}{\Delta t}` | - |
| 〖78〗 | $E2E \approx TTFT + ITL \times OSL$ | `E2E \approx TTFT + ITL \times OSL` | 2、13、38 |
| 〖79〗 | $\overline{D_p}$ vs $\overline{D_d}$（Component Latency） | `\overline{D_p}` | - |
| 〖80〗 | $\overline{D_p}$ vs $\overline{D_d}$（Component Latency） | `\overline{D_d}` | - |
| 〖81〗 | $r_p \approx r_d$ | `r_p \approx r_d` | - |
| 〖82〗 | $N_{queued}$ 与 $\overline{TTFT}$ | `N_{queued}` | 44 |
| 〖83〗 | $N_{queued}$ 与 $\overline{TTFT}$ | `\overline{TTFT}` | - |
| 〖84〗 | $U_{kv}$ 与 $\overline{ITL}$ | `U_{kv}` | - |
| 〖85〗 | $U_{kv}$ 与 $\overline{ITL}$ | `\overline{ITL}` | - |
| 〖86〗 | $U_{kv}$ 与 $\overline{ITL}$ | `U_{kv}\in[0.6,0.8]` | - |
| 〖87〗 | $U_{kv}$ 与 $\overline{ITL}$ | `U_{kv}>0.9` | - |
| 〖88〗 | $BW_{nvl}$ 与 $U_{mem}$ | `BW_{nvl}` | - |
| 〖89〗 | $BW_{nvl}$ 与 $U_{mem}$ | `U_{mem}` | 91 |
| 〖90〗 | $BW_{nvl}$ 与 $U_{mem}$ | `BW_{nvl}<1` | - |
| 〖91〗 | $BW_{nvl}$ 与 $U_{mem}$ | `U_{mem}` | 89 |
| 〖92〗 | Prefill Workers | `N_p(t)` | 96 |
| 〖93〗 | Decode Workers | `N_d(t)` | 97 |
| 〖94〗 | Cumulative GPU Hours | `H_{gpu}(t)=\displaystyle\int N_{gpu}\,dt` | - |
| 〖95〗 | Cumulative GPU Hours | `\dfrac{H_{gpu}\times 单价}{T_{out}}` | - |
| 〖96〗 | Worker Count History | `N_p(t)` | 92 |
| 〖97〗 | Worker Count History | `N_d(t)` | 93 |
| 〖98〗 | **Observed Latency (TTFT & ITL)** | `TTFT_{obs}` | - |
| 〖99〗 | **Observed Latency (TTFT & ITL)** | `ITL_{obs}` | - |
| 〖100〗 | **Observed Latency (TTFT & ITL)** | `TTFT_{sla}` | - |
| 〖101〗 | **Observed Latency (TTFT & ITL)** | `ITL_{sla}` | - |
| 〖102〗 | Observed Request Rate & Duration | `RPS_{obs}` | 108 |
| 〖103〗 | Observed Request Rate & Duration | `\overline{E2E}_{obs}` | - |
| 〖104〗 | Observed Request Rate & Duration | `TTFT+ITL\times OSL` | - |
| 〖105〗 | Observed Sequence Lengths (ISL & OSL) | `\overline{ISL}_{obs}` | - |
| 〖106〗 | Observed Sequence Lengths (ISL & OSL) | `\overline{OSL}_{obs}` | - |
| 〖107〗 | Predicted Request Rate | `RPS_{pred}(t)` | - |
| 〖108〗 | Predicted Request Rate | `RPS_{obs}` | 102 |
| 〖109〗 | Predicted Sequence Lengths (ISL & OSL) | `\overline{ISL}_{pred}` | - |
| 〖110〗 | Predicted Sequence Lengths (ISL & OSL) | `\overline{OSL}_{pred}` | - |
| 〖111〗 | Predicted Replica Counts | `N_p^{pred}` | - |
| 〖112〗 | Predicted Replica Counts | `N_d^{pred}` | - |
| 〖113〗 | Reconciliation Rate | `r_{rec}=\dfrac{\Delta N_{rec}}{\Delta t}` | - |
| 〖114〗 | Reconciliation Rate | `(type,\ result)` | - |
| 〖115〗 | Reconciliation Rate | `result\in\{success,\ error\}` | - |
| 〖116〗 | Reconciliation Duration (P95) | `P_{95}(D_{rec})` | - |
| 〖117〗 | Reconciliation Duration (P95) | `type` | 125 |
| 〖118〗 | **Reconciliation Errors** | `r_{err}=\dfrac{\Delta N_{err}}{\Delta t}` | - |
| 〖119〗 | **Reconciliation Errors** | `(type,\ err)` | - |
| 〖120〗 | Webhook Request Rate | `r_{wh}=\dfrac{\Delta N_{wh}}{\Delta t}` | - |
| 〖121〗 | Webhook Request Rate | `(type,\ op,\ result)` | - |
| 〖122〗 | Webhook Request Rate | `op\in\{CREATE,\ UPDATE,\ DELETE\}` | - |
| 〖123〗 | Webhook Request Rate | `result=allowed` | - |
| 〖124〗 | Webhook Duration (P95) | `P_{95}(D_{wh})` | - |
| 〖125〗 | Webhook Duration (P95) | `type` | 117 |
| 〖126〗 | **Webhook Denials** | `r_{deny}=\dfrac{\Delta N_{deny}}{\Delta t}` | - |
| 〖127〗 | **Webhook Denials** | `(type,\ op,\ reason)` | - |
| 〖128〗 | Resource Inventory by State | `N_{res}(t)` | - |
| 〖129〗 | Resource Inventory by State | `(type,\ ns,\ status)` | - |
| 〖130〗 | Resource Count by State | `N_{res}` | - |
| 〖131〗 | Resource Count by State | `(type,\ status)` | - |
| 〖132〗 | **Reconciliation Success Rate** | `S_{rec}=\dfrac{r_{rec}(success)}{r_{rec}}\times 100\%` | - |
| 〖133〗 | **Webhook Admission Success Rate** | `S_{wh}=\dfrac{r_{wh}(allowed)}{r_{wh}}\times 100\%` | - |
