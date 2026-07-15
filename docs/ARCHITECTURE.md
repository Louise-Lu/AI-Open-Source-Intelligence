# GitHub AI Intelligence Platform - 系统架构

## 1. 项目目标

GitHub AI Intelligence Platform 是一个基于 LLM 的开源项目情报分析平台。

目标不是做 GitHub ChatBot，而是帮助开发者、技术负责人和 AI 创业团队快速理解一个开源项目：

- 项目定位
- 社区活跃度
- 企业成熟度
- 技术路线
- Release 演进
- 多项目比较

目前 V1 采用 Workflow Architecture。

未来 V2 V3...逐步演进到真正的 AI Agent。

---

# 2. 当前架构（V1）

```
                用户

                  │

             FastAPI API

                  │

            Service Layer
                  │
        ┌─────────┴─────────┐
        │                   │
 GitHub API Client      Evidence Builder 
        │                   │
        └─────────┬─────────┘
                  │
         Structured Evidence
                  │
             Qwen-Max LLM 
                  │
        Markdown / JSON Report
                  │
              Frontend
```

---

# 3. 分层职责

## API Layer

负责：

- HTTP 请求
- 参数校验
- 返回 JSON

例如：

```
POST /analysis

POST /profile

POST /comparison

POST /release-diff
```

API 不包含业务逻辑。

---

## Service Layer

负责：

整个业务流程。

例如：

Repository Analysis：

```
获取 GitHub 数据

↓

Evidence Builder

↓

调用 LLM

↓

返回报告
```

Service 不负责：

- GitHub API
- Prompt
- 数据结构

它只负责组织流程。

---

## GitHub API Layer

统一封装 GitHub REST API。

例如：

```
RepositoryTool

ReleaseTool

IssueTool

PullRequestTool

ReadmeTool
```

所有 HTTP 请求统一管理。

方便以后：

- Token
- Retry
- Cache

统一扩展。

---

## Evidence Builder

作用：

把 GitHub 原始 JSON

转换成

统一结构化 Evidence。

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

## LLM Layer

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

# 4. 当前为什么不是 Agent

目前：

所有流程都是固定的。

例如：

Analysis

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

因此：

当前属于：

LLM Workflow。

不是：

AI Agent。

---

# 5. V2 演进

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
React Dashboard

↓

FastAPI

↓

Chat Service

↓

LangGraph ReAct Agent

↓

GitHub Tools

↓

Evidence Builder（可选）

↓

LLM

↓

Streaming

```

此时：

LLM 自主决定：

调用哪些 Tool。

真正进入：

ReAct Agent。

---

# 6. V3 演进

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

# 7. 当前目录

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

职责清晰。

方便继续扩展。

---

# 8. 当前能力（V1）

✅ Repository Analysis

输出：

Markdown

---

✅ Repository Profile

输出：

Structured JSON

---

✅ Repository Comparison

输出：

Markdown

---

✅ Release Diff

输出：

Markdown

---

# 9. 后续 Roadmap

V2

- Chat Agent
- Tool Calling
- Memory

V3

- Multi-Agent
- Planning
- RAG
- Knowledge Base
