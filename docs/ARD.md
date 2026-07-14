# Architecture Decision Record

---

## ADR-001

### 决策

采用 LangGraph 官方 create_react_agent。

### 原因

官方维护。

兼容未来版本。

### 收益

减少维护成本。

---

## ADR-002

### 决策

GitHub API 每个资源拆分为独立 Tool。

### 原因

符合单一职责原则（SRP）。

方便未来增加 Tool。

---

## ADR-003

### 决策

新增 Evidence Builder。

### 原因

避免 Agent 直接消费原始 JSON。

统一上下文。

### 收益

方便增加数据源。

---

## ADR-004

### 决策

Report 使用 Structured Output。

### 原因

方便：

React

API

Dashboard

后续统计分析。

---

## ADR-005

### 决策

Agent 使用 ReAct 模式，而不是固定 Workflow。

### 原因

Agent 能根据问题动态决定调用哪些 Tool。

未来更容易扩展 MCP、Memory、多 Agent。