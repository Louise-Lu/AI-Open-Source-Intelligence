# GitHub AI Intelligence Platform

> AI-powered Open Source Intelligence Platform for GitHub Repositories.

---

# 项目简介

GitHub AI Intelligence Platform 是一个利用 Large Language Model（LLM）分析 GitHub 开源项目的平台。

与传统 GitHub 搜索不同，本项目不仅获取仓库信息，还能够自动完成：

- Repository Analysis
- Repository Profile
- Repository Comparison
- Release Diff

帮助开发者快速理解开源项目。

---

# 项目特点

## Repository Analysis

自动生成：

- 项目定位
- 技术特点
- 社区情况
- 企业成熟度
- 未来发展方向

输出：Markdown Report

---

## Repository Profile

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

## Repository Comparison

比较两个项目：

例如：LangGraph VS AutoGen

输出：JSON

- 项目定位
- 技术路线
- 社区活跃度
- 企业成熟度
- 推荐场景

---

## Release Diff

比较：两个 Release。

自动总结：

- New Features
- Improvements
- Bug Fixes
- Breaking Changes
- Upgrade Recommendation

---

# 系统架构

```
FastAPI

↓

Service

↓

GitHub API

↓

Evidence Builder

↓

Qwen-Max

↓

Markdown / JSON
```

更多内容：

请查看：

docs/ARCHITECTURE.md

---

# 技术栈

Backend

- Python
- FastAPI
- LangChain
- Qwen-Max
- Pydantic

LLM

- DashScope
- Qwen-Max

API

- GitHub REST API

Deployment

- Docker
- Render（Backend）
- Vercel（Frontend）

---

# 项目结构

```
backend/

api/

services/

github/

prompts/

schemas/

models/

tools/
```

---

# API

## Repository Analysis

```
POST /analysis
```

---

## Repository Profile

```
POST /profile
```

---

## Repository Comparison

```
POST /comparison
```

---

## Release Diff

```
POST /release-diff
```

---

# 本地运行

安装依赖：

```bash
pip install -r requirements.txt
```

配置：

```
DASHSCOPE_API_KEY=

GITHUB_TOKEN=
```

启动：

```bash
uvicorn main:app --reload
```

Swagger：

```
http://127.0.0.1:8000/docs
```

---

# MVP

V1

- Repository Analysis
- Repository Profile
- Repository Comparison
- Release Diff

---

# 当前版本

## V2

- Chat Agent
- Tool Calling
- Memory
- Streaming

## V3

- Multi-Agent
- Knowledge Graph
- RAG
- Long-term Memory
- AI Project Ranking

---

V1

GitHub Intelligence Platform

↓

V2

AI Repository Assistant

↓

V3

Multi-Agent Intelligence Platform

---
# License

MIT