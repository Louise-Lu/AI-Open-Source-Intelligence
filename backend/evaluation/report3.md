# Agent 评测报告

## 基础信息

测试问题数量：
40

错误数量：
0


## 综合指标


### 意图理解


准确率：

90.4%



### 工具选择能力


工具 Precision:

71.7%


工具 Recall:

100.0%


工具 F1:

80.0%



### 证据质量


平均分:

92.3


证据完整性:

95.4


证据新鲜度:

97


证据覆盖:

84.1



### 推理质量


平均分:

89.3



### 响应质量


暂未实现



### 平均延迟


13.3 秒


## 逐题结果

| ID | 预期意图 | 预测意图 | 意图分 | 工具P | 工具R | 证据 | 推理 | 延迟(秒) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | project_overview | project_overview, readme | 67 | 40.0% | 100.0% | 97 | 96 | 13.58 |
| 2 | repository | repository | 100 | 100.0% | 100.0% | 86 | 88 | 2.27 |
| 3 | repository | project_overview, repository | 67 | 100.0% | 100.0% | 97 | 90 | 2.89 |
| 4 | repository | repository | 100 | 100.0% | 100.0% | 97 | 90 | 3.73 |
| 5 | readme | readme | 100 | 20.0% | 100.0% | 97 | 97 | 15.29 |
| 6 | readme | readme | 100 | 100.0% | 100.0% | 85 | 92 | 7.08 |
| 7 | release | release | 100 | 100.0% | 100.0% | 94 | 80 | 7.23 |
| 8 | release | release | 100 | 100.0% | 100.0% | 94 | 80 | 7.38 |
| 9 | issue | issue | 100 | 100.0% | 100.0% | 94 | 79 | 5.41 |
| 10 | issue | issue | 100 | 33.3% | 100.0% | 97 | 100 | 22.73 |
| 11 | pr | pr | 100 | 100.0% | 100.0% | 94 | 85 | 6.77 |
| 12 | pr | pr | 100 | 20.0% | 100.0% | 97 | 95 | 14.97 |
| 13 | project_overview | project_overview | 100 | 40.0% | 100.0% | 97 | 98 | 14.38 |
| 14 | project_health, recommendation | project_health, recommendation | 100 | 80.0% | 100.0% | 97 | 97 | 16.30 |
| 15 | project_health | project_health | 100 | 80.0% | 100.0% | 97 | 96 | 14.90 |
| 16 | roadmap | roadmap | 100 | 80.0% | 100.0% | 97 | 96 | 17.77 |
| 17 | roadmap | roadmap, pr, issue | 50 | 60.0% | 100.0% | 97 | 97 | 19.61 |
| 18 | recommendation | recommendation | 100 | 80.0% | 100.0% | 97 | 96 | 15.72 |
| 19 | recommendation | project_overview, recommendation | 67 | 80.0% | 100.0% | 97 | 97 | 20.79 |
| 20 | project_overview | project_overview, readme | 67 | 40.0% | 100.0% | 97 | 81 | 21.86 |
| 21 | repository | project_overview | 0 | 100.0% | 100.0% | 97 | 90 | 3.74 |
| 22 | readme | readme | 100 | 20.0% | 100.0% | 94 | 82 | 14.99 |
| 23 | release | release | 100 | 100.0% | 100.0% | 97 | 97 | 7.63 |
| 24 | issue | issue | 100 | 33.3% | 100.0% | 44 | 84 | 15.66 |
| 25 | pr | pr | 100 | 100.0% | 100.0% | 91 | 81 | 5.84 |
| 26 | project_health | project_health | 100 | 80.0% | 100.0% | 84 | 97 | 23.41 |
| 27 | recommendation | recommendation | 100 | 80.0% | 100.0% | 82 | 80 | 15.13 |
| 28 | project_overview | project_overview | 100 | 40.0% | 100.0% | 94 | 96 | 23.14 |
| 29 | repository | repository | 100 | 100.0% | 100.0% | 97 | 90 | 3.49 |
| 30 | release | release | 100 | 50.0% | 100.0% | 94 | 80 | 10.61 |
| 31 | issue | issue | 100 | 50.0% | 100.0% | 97 | 99 | 9.40 |
| 32 | roadmap | project_overview, roadmap | 67 | 60.0% | 100.0% | 94 | 69 | 19.17 |
| 33 | comparison | comparison | 100 | 60.0% | 100.0% | 91 | 97 | 25.14 |
| 34 | comparison | comparison | 100 | 60.0% | 100.0% | 71 | 67 | 20.22 |
| 35 | comparison | comparison | 100 | 80.0% | 100.0% | 91 | 61 | 22.16 |
| 36 | repository | repository | 100 | 100.0% | 100.0% | 97 | 100 | 8.80 |
| 37 | readme | readme | 100 | 100.0% | 100.0% | 85 | 95 | 5.79 |
| 38 | project_health | project_health, issue | 67 | 75.0% | 100.0% | 97 | 99 | 12.99 |
| 39 | pr | pr, roadmap | 67 | 25.0% | 100.0% | 94 | 80 | 17.87 |
| 40 | recommendation | recommendation | 100 | 100.0% | 100.0% | 97 | 98 | 18.02 |

## 说明

- Layer 1 意图理解、Layer 2 工具选择、Layer 3 证据质量、Layer 4 推理质量已实现。
- 响应质量评测暂未实现。
