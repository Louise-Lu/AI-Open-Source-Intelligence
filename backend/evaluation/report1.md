# Agent Evaluation Report

Total questions: 40
Errors: 0

## Aggregate Metrics

Intent Accuracy

N/A (stub)

Tool Precision

70.9%

Tool Recall

100.0%

Tool F1

79.1%

Tool Call Order

91.2%

## Evidence Quality

Average Score:

92.8

Evidence Completeness

96.2

Evidence Freshness

97.0

Evidence Coverage

84.2

## Reasoning Quality

Average Score:

74.3

Evidence Grounding

89.2

Contradiction Detection

43.1

Reasoning Completeness

84.5

Answer Quality

N/A (stub)

Average Latency

15.84 seconds

## Per-Question Results

| ID | Intent | Tool P | Tool R | Evidence | Reasoning | Unsupported | Latency (s) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | project_overview | 40.0% | 100.0% | 97 | 67 | - | 24.58 |
| 2 | repository | 100.0% | 100.0% | 86 | 88 | - | 2.08 |
| 3 | repository | 100.0% | 100.0% | 97 | 91 | - | 3.60 |
| 4 | repository | 100.0% | 100.0% | 97 | 92 | - | 4.67 |
| 5 | readme | 20.0% | 100.0% | 97 | 67 | - | 17.11 |
| 6 | readme | 100.0% | 100.0% | 85 | 93 | - | 6.68 |
| 7 | release | 100.0% | 100.0% | 91 | 76 | issues, pull_requests | 7.95 |
| 8 | release | 100.0% | 100.0% | 94 | 80 | issues | 8.00 |
| 9 | issue | 100.0% | 100.0% | 97 | 98 | - | 5.78 |
| 10 | issue | 20.0% | 100.0% | 97 | 100 | - | 27.63 |
| 11 | pr | 100.0% | 100.0% | 97 | 98 | - | 8.22 |
| 12 | pr | 20.0% | 100.0% | 97 | 85 | - | 15.72 |
| 13 | project_overview | 40.0% | 100.0% | 97 | 69 | - | 21.11 |
| 14 | project_health | 75.0% | 100.0% | 97 | 67 | - | 10.77 |
| 15 | project_health | 80.0% | 100.0% | 97 | 66 | - | 20.49 |
| 16 | roadmap | 80.0% | 100.0% | 97 | 96 | - | 25.77 |
| 17 | roadmap | 60.0% | 100.0% | 97 | 76 | - | 30.35 |
| 18 | recommendation | 80.0% | 100.0% | 97 | 66 | - | 15.34 |
| 19 | recommendation | 80.0% | 100.0% | 97 | 67 | - | 25.36 |
| 20 | project_overview | 40.0% | 100.0% | 97 | 66 | - | 22.80 |
| 21 | repository | 100.0% | 100.0% | 86 | 85 | - | 2.47 |
| 22 | readme | 20.0% | 100.0% | 94 | 52 | issues | 19.27 |
| 23 | release | 100.0% | 100.0% | 97 | 97 | - | 7.72 |
| 24 | issue | 25.0% | 100.0% | 44 | 63 | issues | 18.35 |
| 25 | pr | 100.0% | 100.0% | 91 | 81 | readme, issues | 6.60 |
| 26 | project_health | 80.0% | 100.0% | 82 | 52 | issues | 28.06 |
| 27 | recommendation | 80.0% | 100.0% | 84 | 65 | - | 18.12 |
| 28 | project_overview | 40.0% | 100.0% | 97 | 65 | - | 20.60 |
| 29 | repository | 100.0% | 100.0% | 97 | 90 | - | 3.92 |
| 30 | release | 50.0% | 100.0% | 94 | 80 | issues | 12.41 |
| 31 | issue | 50.0% | 100.0% | 97 | 69 | - | 12.54 |
| 32 | roadmap | 60.0% | 100.0% | 94 | 46 | number:28294, number:18571 | 24.49 |
| 33 | comparison | 60.0% | 100.0% | 91 | 52 | number:6271 | 30.61 |
| 34 | comparison | 60.0% | 100.0% | 91 | 54 | number:71951 | 24.61 |
| 35 | comparison | 80.0% | 100.0% | 91 | 47 | number:59774, number:8997 | 22.42 |
| 36 | repository | 100.0% | 100.0% | 97 | 70 | - | 8.52 |
| 37 | readme | 100.0% | 100.0% | 85 | 95 | - | 6.29 |
| 38 | project_health | 75.0% | 100.0% | 97 | 68 | - | 15.09 |
| 39 | pr | 20.0% | 100.0% | 97 | 67 | - | 22.75 |
| 40 | recommendation | 100.0% | 100.0% | 97 | 68 | - | 24.93 |

## Notes

- Layer 2 Tool Selection, Layer 3 Evidence Quality, and Layer 4 Reasoning Quality are implemented.
- Intent / Answer evaluators remain stubs.
