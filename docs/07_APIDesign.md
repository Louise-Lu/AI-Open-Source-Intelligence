# API Design

## Overview

Backend 提供 REST API，供前端调用 AI 分析能力。

---

# Analyze Repository

POST /api/analyze

## Request

{
    "repo_url":"https://github.com/langchain-ai/langgraph"
}

## Response

{
    "summary": "...",
    "profile": {},
    "roadmap": {},
    "release_diff": {}
}

---

# Compare Repository

POST /api/compare

## Request

{
    "repo_a":"...",
    "repo_b":"..."
}

## Response

{
    "comparison": {}
}

---

# Release Diff

POST /api/release-diff

## Request

{
    "repo":"...",
    "base":"v0.4",
    "target":"v0.5"
}

## Response

{
    "diff": {}
}

---

# Health Check

GET /health

Response

{
    "status":"ok"
}