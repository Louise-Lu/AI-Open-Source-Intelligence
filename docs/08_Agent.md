# Agent Architecture

## Overview

GitHub Intelligence Agent 采用 ReAct（Reason + Act）模式。
用 LangGraph 把 Agent 的循环（Reason → Act → Observe）实现。
✅ LangGraph
✅ Tool Calling
✅ create_react_agent

Agent 不采用固定 Workflow，而是根据用户目标自主规划分析过程，并动态决定调用哪些 Tool。

整个分析过程由一个 Agent 完成，而不是多个 Agent 协同。

---

# Architecture

User

↓

Intent Understanding

↓

Planning

↓

Tool Selection

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

# Core Components

## Intent Understanding

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