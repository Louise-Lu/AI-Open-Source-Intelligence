# Agent Architecture

## Overview

GitHub Intelligence Agent 采用 ReAct（Reason + Act）模式。

用 LangGraph 把 Agent 的循环（Reason → Act → Observe）实现。

- LangGraph
- Tool Calling
- create_react_agent

Agent 不采用固定 Workflow，而是根据用户目标自主规划分析过程，并动态决定调用哪些 Tool。

整个分析过程由一个 Agent 完成，而不是多个 Agent 协同。

---

## Architecture

User

↓

Intent Understanding

↓

Planning

↓

Tool Selection 调用 GitHub API

↓

Observation

↓

Reasoning

↓

Enough Information？

├── No → Continue Tool Calling

└── Yes

↓

Generate Intelligence Report

---

## Core Components

### Intent Understanding

负责理解用户真正的问题。

例如：

用户：

"LangGraph 适合企业项目吗？"

Agent 不会只生成 Summary。

而会判断：

需要：

- Project Profile
- Community Activity
- Recent Release
- Roadmap

---

## Planning

生成分析计划。

例如：

Step 1

获取 Repository

Step 2

分析 Release

Step 3

分析 Issue

Step 4

生成报告

---

## Tool Selection

Agent 根据当前信息决定调用哪个 Tool。

例如：

Repository Tool

Issue Tool

Release Tool

Compare Tool

---

## Observation

保存每次 Tool 返回结果。

Agent 根据 Observation 判断：

信息是否足够。

---

## Reasoning

根据 Observation 推理：

是否继续搜索。

是否切换 Tool。

是否结束分析。

---

## Report Generation

最终生成：

Project Intelligence Report。

## 测试问题
现在测试 Chat Agent，不只测一个简单问题。要覆盖：

1. **直接查询（单工具）**
2. **需要多个工具**
3. **需要分析推理**
4. **容易误调用**
5. **上下文记忆（后面加 memory 测）**

---

## 1. 查询仓库基础信息（Repository Tool）

### 用户输入

```
LangGraph 有多少 stars？forks 多少？
```

预期 Agent：

调用：

```
get_repository
```

可能答案：

```
LangGraph (langchain-ai/langgraph) 当前约有 37k stars，6k+ forks。

该项目主要使用 Python 开发，采用 MIT License。
```

---

## 2. 查询项目定位（Repository + README）

### 用户输入

```
LangGraph 是做什么的？
```

预期：

调用：

```
get_repository
get_readme
```

答案：

```
LangGraph 是一个用于构建长期运行、有状态 AI Agent 的low-level编排框架。

它提供：
- 状态管理
- 持久化执行
- Human-in-the-loop
- Agent 工作流编排

主要用于构建复杂的生产级 Agent 系统。
```

---

## 3. 查询维护情况（多个工具）

### 用户输入

```
LangGraph 维护活跃吗？
```

预期：

调用：

```
get_repository
get_releases
get_issues
get_pull_requests
```

答案：

```
LangGraph 目前维护较为活跃。

依据：

- GitHub Stars 超过 3.7 万
- 最近持续发布多个 Release
- Issue 和 Pull Request 持续更新

说明项目仍处于积极开发阶段。
```

---

## 4. Release 查询

### 用户输入

```
LangGraph 最近更新了什么？
```

预期：

调用：

```
get_releases
```

答案：

```
最近版本为 v1.2.9。

该版本主要包含 bug 修复，例如：
- delta channel 相关问题修复
- metadata 和 counter 更新修复

没有明显的新功能或 breaking change。
```

---

## 5. 比较两个项目（测试多仓库能力）

### 用户输入

```
比较 LangGraph 和 LangChain
```

预期：

调用：

```
get_repository(langchain-ai/langgraph)

get_repository(langchain-ai/langchain)
```

答案：

```
LangGraph 和 LangChain 都属于 LangChain 生态。

区别：

LangChain：
- 提供 LLM 应用开发组件
- chains、retrievers、tools

LangGraph：
- 专注 Agent 工作流编排
- 状态管理
- 长运行 Agent

如果构建复杂 Agent，LangGraph 更适合。
```

---

## 6. 测试不存在仓库

### 用户输入

```
分析 abc/xyz 这个 GitHub 项目
```

预期：

不要崩。

答案：

```
无法找到该 GitHub Repository。

请检查 owner 和 repository 名称是否正确。
```

---

## 7. 测试工具选择能力

### 用户输入

```
LangGraph 最近有没有 bug？
```

正确：

应该调用：

```
get_issues
```

而不是：

```
get_repository
```

答案：

```
GitHub Issues 中存在一些 bug 相关讨论。

例如：
- delta channel replay 问题
- checkpoint consistency 问题

这些问题主要集中在稳定性和性能优化方面。
```

---

## 8. 测试上下文（现在可能失败，等 memory）

第一轮：

```
LangGraph 有多少 stars？
```

回答：

```
约37344 stars
```

第二轮：

```
它维护活跃吗？
```

未来应该理解：

```
它 = LangGraph
```

现在没有 memory 的情况下可能不知道。

---

## 9. 测试复杂分析

### 用户输入

```
LangGraph 适合企业生产环境吗？
```

预期：

调用：

```
repository
readme
issues
releases
```

答案：

```
LangGraph 具备企业使用的一些条件：

优势：
- MIT License
- 活跃维护
- 支持长期运行 Agent
- 提供持久化和状态管理

需要注意：
- Agent 系统仍需要自行设计监控、安全和成本控制。
```

---

## 10. 测试中文回答

### 用户输入

```
用中文总结一下 LangGraph
```

答案：

```
LangGraph 是一个面向生产级 AI Agent 的编排框架。

它帮助开发者构建具有状态、记忆和复杂工作流能力的 Agent。
```

---

你测试的时候重点看三个东西：

### ① 有没有乱调用 Tool

例如：

问：

```
LangGraph 有多少 stars？
```

应该：

```
get_repository
```

不要：

```
get_releases
get_issues
get_readme
```

---

### ② 有没有重复调用

你之前的问题：

```
get_repository
get_repository
get_langchain
```

就是 Agent stop condition 不好。

---

### ③ trace 是否合理

理想：

```
User Question

↓
Agent

↓
Tool:
get_repository

↓
Tool Result

↓
Final Answer
```

不要：

```
Tool
Tool
Tool
Tool
Sorry need more steps
```

---
# Agent Evaluation Framework

- 第一层：Intent 是否理解正确
    - 是否正确理解用户问题
    - 是否正确识别 repository
    - 是否正确识别任务类型

- 第二层：Tool Selection（最重要）
    - Tool Precision
    - Tool Recall
    - 是否遗漏 Tool
    - 是否多调用 Tool
    - Tool Call Order

- 第三层：Evidence Quality
Agent 生成答案的时候，拿到的证据够不够？相关不相关？新不新？    
    - Evidence Completeness
    - Evidence Relevance
    - Evidence Freshness
    - 是否足够支持回答

- 第四层：Reasoning Quality
    - Logical Consistency
    - Grounded Reasoning
    - Unsupported Claims
    - Hallucination
    - Evidence → Reasoning → Conclusion
- 第五层：Final Answer Quality
    - Correctness
    - Completeness
    - Helpfulness
    - Structure
    - Readability

```
User Query
     │
     ▼
──────────────────────────────────────
Layer 1
Intent Understanding
──────────────────────────────────────
Agent 是否理解了用户真正的问题？

↓

──────────────────────────────────────
Layer 2
Tool Selection
──────────────────────────────────────
是否选择了正确的工具？
是否遗漏？
是否多调用？
调用顺序是否合理？

↓

──────────────────────────────────────
Layer 3
Evidence Collection
──────────────────────────────────────
Evidence 是否完整？
是否来自正确的数据源？
是否足够支持回答？

↓

──────────────────────────────────────
Layer 4
Reasoning / Intelligence
──────────────────────────────────────
Evidence
      ↓
Reasoning
      ↓
Conclusion

分析逻辑是否合理？
有没有跳跃推理？
有没有幻觉？
结论是否被 Evidence 支撑？

↓

──────────────────────────────────────
Layer 5
Final Answer
──────────────────────────────────────
是否真正回答用户问题？
是否清晰？
是否结构化？
是否可执行？
```
---

| 问题    | 期望工具                         |
| ----- | ---------------------------- |
| 介绍项目  | README                       |
| 项目活跃度 | repo + commits               |
| 最近趋势  | releases + commits           |
| 技术分析  | README + repo                |
| 竞品比较  | 多个repo                       |
| 商业价值  | repo + issues + contributors |
