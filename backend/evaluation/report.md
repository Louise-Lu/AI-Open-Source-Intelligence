# Agent Evaluation Report

Total questions: 40
Errors: 1 
- What is FastAPI

## Aggregate Metrics

Intent Accuracy

N/A (Phase 1 stub)

Tool Precision

86.4%

Tool Recall

88.3%

Tool F1

85.8%

Tool Call Order

82.7%

Evidence Completeness

N/A (Phase 1 stub)

Reasoning

N/A (Phase 1 stub)

Answer Quality

N/A (Phase 1 stub)

Average Latency

14.04 seconds

## Per-Question Tool Selection
计算公式：
- Precision = (找对的Tools个数) / (总共找回来的Tools总数) "准不准"
- Recall = (找对的Tools个数) / (本来应该有的Tools总数) "全不全"

**权衡关系 (Trade-off)**
这两个指标往往是互相矛盾的。

如果只想保证高正确性（找得对）：会非常谨慎，但可能会漏掉很多正确答案（召回率很低）。

如果只想保证高召回率（找得全）：全部调用（召回率 100%），但里面混杂了大量的错误Tools（正确率极低）。

正确性：Agent 调用工具后，返回的仓库信息都是你想要的且绝对正确的吗？如果它经常把 langgraph 错说成 langraph，或者分析的是错的代码文件，那正确性就差。

召回率：Agent 有没有把所有重要的信息都提取出来？比如分析一个仓库，除了看 Star 数，它有没有把 Issues、PR、贡献者、代码结构这些相关上下文都考虑到？如果漏掉了很多重要线索，那召回率就差。

F1-Score 来综合衡量这两者：

- F1 = 2 × (Precision × Recall) / (Precision + Recall)

只有当精确率和召回率都比较高时，F1 才会高。这说明你的 Agent 不仅找得准，而且找得全。


| ID | Intent | Precision | Recall | Missed | Extra | Latency (s) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | project_overview | 100.0% | 100.0% | - | - | 16.80 |
| 2 | repository | 100.0% | 100.0% | - | - | 4.53 |
| 3 | repository | 100.0% | 100.0% | - | - | 5.86 |
| 4 | repository | 100.0% | 100.0% | - | - | 5.21 |
| 5 | readme | 100.0% | 100.0% | - | - | 13.81 |
| 6 | readme | 100.0% | 100.0% | - | - | 9.30 |
| 7 | release | 100.0% | 100.0% | - | - | 13.10 |
| 8 | release | 100.0% | 100.0% | - | - | 5.72 |
| 9 | issue | 100.0% | 100.0% | - | - | 9.67 |
| 10 | issue | 100.0% | 100.0% | - | - | 9.28 |
| 11 | pr | 100.0% | 100.0% | - | - | 7.90 |
| 12 | pr | 100.0% | 100.0% | - | - | 5.63 |
| 13 | project_overview | 40.0% | 100.0% | - | get_issues, get_pull_requests, get_releases | 24.98 |
| 14 | project_health | 75.0% | 100.0% | - | get_pull_requests | 11.98 |
| 15 | project_health | 80.0% | 100.0% | - | get_readme | 25.22 |
| 16 | roadmap | 80.0% | 100.0% | - | get_repository | 19.10 |
| 17 | roadmap | 100.0% | 66.7% | get_releases | - | 12.83 |
| 18 | recommendation | 80.0% | 100.0% | - | get_pull_requests | 20.79 |
| 19 | recommendation | 80.0% | 100.0% | - | get_pull_requests | 22.22 |
| 20 | project_overview | 0.0% | 0.0% | get_readme, get_repository | - | 9.63 |
| 21 | repository | 100.0% | 100.0% | - | - | 4.50 |
| 22 | readme | 100.0% | 100.0% | - | - | 14.77 |
| 23 | release | 100.0% | 100.0% | - | - | 14.52 |
| 24 | issue | 100.0% | 100.0% | - | - | 12.59 |
| 25 | pr | 100.0% | 100.0% | - | - | 9.94 |
| 26 | project_health | 100.0% | 100.0% | - | - | 24.47 |
| 27 | recommendation | 80.0% | 100.0% | - | get_pull_requests | 21.89 |
| 28 | project_overview | 0.0% | 0.0% | get_readme, get_repository | - | 2.46 |
| 29 | repository | 100.0% | 100.0% | - | - | 3.80 |
| 30 | release | 100.0% | 100.0% | - | - | 14.84 |
| 31 | issue | 100.0% | 100.0% | - | - | 6.27 |
| 32 | roadmap | 60.0% | 100.0% | - | get_readme, get_repository | 22.22 |
| 33 | comparison | ERR | ERR | - | - | 1.78 |
| 34 | comparison | 100.0% | 33.3% | get_issues, get_releases | - | 15.32 |
| 35 | comparison | 80.0% | 100.0% | - | get_pull_requests | 39.22 |
| 36 | repository | 100.0% | 100.0% | - | - | 12.40 |
| 37 | readme | 100.0% | 100.0% | - | - | 3.98 |
| 38 | project_health | 100.0% | 33.3% | get_releases, get_repository | - | 6.87 |
| 39 | pr | 100.0% | 100.0% | - | - | 11.84 |
| 40 | recommendation | 100.0% | 100.0% | - | - | 52.12 |

## Notes

- Phase 1 implements Tool Selection only.
