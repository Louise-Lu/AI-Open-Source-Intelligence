# 整体架构
```
                 GitHub
                   |
                   |
             GitHub Tools
                   |
                   |
              Evidence
                   |
        --------------------
        |                  |
        v                  v

  LLM Workflow         Chat Agent

 Dashboard             Conversation
```
# Workflow 分支（Dashboard）
今日 AI 开源情报

```
GitHub
Reddit
HuggingFace
Arxiv
X
    |
    |
    v

Data Collection Layer

    |
    |
    v

Evidence Layer

    |
    |
    +----------------+
    |                |
    v                v

Analysis        Roadmap
Profile         Release Diff
Comparison      Trend


    |
    |
    v

Reports

    |
    |
 Dashboard
```

> V1 采用 Workflow Architecture。 V2 V3...逐步演进到真正的 AI Agent。

---

## 信息流

```
                用户

                  │

             FastAPI API

                  │

            Service Layer
                  │
        ┌─────────┴─────────┐
        │                   │
 GitHub Tools    ->   Evidence Builder 
        │                   │
        └─────────┬─────────┘
                  │
         Structured Evidence
                  │
        Qwen-Max LLM / DeepSeek
                  │
        Markdown / JSON Report
                  │
              Frontend
```

---

## 分层职责

### FAST API Layer 后端路由层

负责：

- HTTP 请求
- 参数校验
- 返回 JSON

例如：

```
POST /analysis

POST /profile

```
自定义后端 API，不包含业务逻辑。

---

### Service Layer

负责：

每一个业务流程。


```
services/


repository_service.py
        |
        |
        ↓
    build evidence


analysis_service.py

    evidence
       |
       ↓
    LLM analysis



roadmap_service.py

    evidence
       |
       ↓
    LLM prediction



profile_service.py

    evidence
       |
       ↓
    structured output

```
Service 不负责：

- GitHub API ： TOOLS
- Prompt
- 数据结构

它只负责组织流程。

---

### GitHub Tools Layer

统一封装 GitHub 的 APIs -> GitHub Tools -> **事实数据**

#### 作用：Data Normalization（数据标准化）

例如：
```
GitHub API Response
        |
        v
  RepositoryInfo

     IssueTool

     PullRequestTool

     ReadmeTool
```
GitHub 原始 JSON 太复杂，抽取需要的字段。

---

### Evidence Builder

#### 作用：Evidence Modeling（证据建模）
**证据层统一采集，工作流按需消费**

把 GitHub 原始 JSON 转换成 统一结构化 Evidence。

例如：

```
GitHub JSON

↓

RepositoryInfo

↓

GitHubEvidence
```

Builder 不负责分析。

Builder 只负责：

- 清洗
- 聚合
- 标准化

---

### LLM Layer

负责：

根据 Evidence

输出：

Markdown

或者

Structured JSON。

例如：

Analysis

↓

Markdown

Profile

↓

RepositoryProfile

Comparison

↓

Markdown

Release Diff

↓

Markdown

LLM 不直接调用 GitHub API。

---

>当前为什么不是 Agent

目前V1所有流程都是固定的。比如分析：

```
GitHub API

↓

Evidence Builder

↓

LLM
```

LLM 不需要决定：

- 调哪个 Tool
- 调几次 Tool

因此：V1属于LLM Workflow。不是：AI Agent。

---

# Agent

新增：

```
POST /chat
```

用户：

```
Which framework is better for enterprise AI?
```

Agent：

```
                    Frontend


          Dashboard              Chat


              |                    |


        Intelligence          Agent


              |                    |


       Report Services       Tool Calling


              |                    |


          Evidence Layer <---------


                    |


              GitHub Data Tools


                    |


              GitHub API


```

此时：

LLM 自主决定：

调用哪些 Tool。

真正进入：

ReAct Agent。

---

# V3 演进: Multi-Agent Intelligence Platform

采用 Multi-Agent。

```
                Supervisor

        ┌────────┼────────┐

 Repository   Release   Issue

     │           │         │

      └───────Report Agent───────┘
```

各 Agent：

负责：

自己的专业领域。

最后：

Supervisor 汇总。

---

# 当前目录

```
backend/

api/

services/

github/

report/

prompts/

models/

tools/
```

职责清晰。方便继续扩展。

---