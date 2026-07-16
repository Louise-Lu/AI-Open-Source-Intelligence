# MVP
## GitHub AI Intelligence Platform

> AI-powered Open Source Intelligence Platform for GitHub Repositories.

### MVP简介

GitHub AI Intelligence Platform 是一个利用 Large Language Model（LLM）分析 GitHub 开源项目的平台。

与传统 GitHub 搜索不同，本项目不仅获取仓库信息，还能够自动完成：

- Repository Analysis
- Repository Profile
- Repository Comparison
- Release Diff

帮助开发者快速理解开源项目。

---

## 功能

### 1.Repository Analysis

自动生成：

- 项目定位
- 技术特点
- 社区情况
- 企业成熟度
- 未来发展方向

输出：Markdown Report

---

### 2. Repository Profile

自动生成：
结构化项目画像。

输出：JSON

例如：

```json
{
  "full_name": "langchain-ai/langgraph",
  "description": "Build resilient agents.",
  "language": "Python",
  "license": "MIT License",
  "stars": 37383,
  "forks": 6265,
  "topics": [
    "agents",
    "ai-agents",
    "generative-ai",
    "langchain",
    "langgraph",
  ],
  "maintenance_score": 7,
  "enterprise_score": 8,
  "community_score": 9,
  "summary": "这个项目是一个用于构建、管理和部署长期运行的、有状态代理的低级编排框架，核心价值在于提供稳定和可扩展的基础架构。",
  "recommendation": "推荐给需要构建复杂、长期运行的AI代理或工作流的开发者和团队。适合的应用场景包括需要高度定制化和灵活性的企业级应用，例如自动化任务处理、智能客服系统等。"
}
```

方便：Dashboard

搜索

排序

比较

---

### 3. Repository Comparison

比较两个项目：

例如：LangGraph VS AutoGen

输出：JSON

- 项目定位
- 技术路线
- 社区活跃度
- 企业成熟度
- 推荐场景

---

### 4. Release Diff

比较：两个 Release。

自动总结：

- New Features
- Improvements
- Bug Fixes
- Breaking Changes
- Upgrade Recommendation

---

## 系统架构

```
FastAPI
↓
Service
↓
GitHub API 

↓     数据清洗，整合

Evidence Builder
↓

Qwen-Max

↓

Markdown / JSON
```

### 成果
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
