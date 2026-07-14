# AI Open Source Intelligence Platform 系统架构
- Architecture Decision（架构决策）
> Version: MVP v1.0

---

# 1. 项目定位

AI Open Source Intelligence Platform（AI 开源情报平台）不是一个 GitHub 搜索工具，也不是一个 GitHub Summary 工具。

它是一个帮助 AI 产品经理、AI 创业者、技术负责人持续跟踪 AI 开源生态的智能分析平台。

产品目标：

> 持续追踪 AI 开源项目，自动收集证据，分析趋势，并生成结构化情报报告，帮助用户快速完成技术调研和技术选型。

---

# 2. 总体架构


```text
                React Dashboard
                        │
                        ▼
                  FastAPI Backend
                        │
        ┌───────────────┴───────────────┐
        ▼                               ▼
 GitHub Intelligence Agent         Report Service
        │                               │
        ▼                               ▼
 Evidence Builder              Structured Report
        │
        ▼
 GitHub Tools
```


---

# 3. 分层设计

## Presentation Layer（展示层）

负责：

- Dashboard
- Repository 页面
- Compare 页面
- 趋势分析页面

技术：

- React
- TailwindCSS

---

## API Layer（接口层）

负责：

- REST API
- Streaming
- Agent 调用
FastAPI（main.py + api/）：负责 HTTP、参数校验、调用业务。
技术：

- FastAPI

---

## Agent Layer（智能体）

负责：

- 理解用户问题
- 决定调用哪些 Tool
- 根据 Evidence 完成推理 
- 输出 Report
Agent：负责推理，决定调用哪些 Tool。
技术：

- LangGraph create_react_agent

workflow:

User
↓
Planner（LLM）
↓
Tool Calling
↓
Evidence Builder
↓
LLM Analysis
↓
Structured Report
---

## Evidence Layer（证据层）

负责：
聚合和清洗 Tool 返回的数据。
统一整理多个 Tool 的数据。

例如：

Repository

README

Release

Issue

Pull Request

Contributor

↓

Evidence

Agent 永远基于 Evidence 推理。

---

## Tool Layer（工具层）

每个 Tool 负责一个 GitHub API。
Tools：负责访问 GitHub API。
例如：

Repository Tool

Release Tool

Issue Tool

Readme Tool

Contributor Tool

Pull Request Tool

---

## Data Source

GitHub REST API

Report：负责生成结构化输出。