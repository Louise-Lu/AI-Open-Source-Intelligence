# GitHub AI Intelligence Platform

> AI-powered Open Source Intelligence Platform for GitHub Repositories.

### MVP简介

GitHub AI Intelligence Platform 是一个利用 Large Language Model（LLM）分析 GitHub 开源项目的平台。

与传统 GitHub 搜索不同，本项目不仅获取仓库信息，还能够自动完成：

- Repository Analysis
- Repository Profile
- Repository Comparison
- Release Diff
- RoadMap Prediction

帮助开发者快速理解开源项目，并提前洞察其未来动向。

---

## 功能

### 1. Repository Analysis

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
    "langgraph"
  ],
  "maintenance_score": 7,
  "enterprise_score": 8,
  "community_score": 9,
  "summary": "这个项目是一个用于构建、管理和部署长期运行的、有状态代理的低级编排框架，核心价值在于提供稳定和可扩展的基础架构。",
  "recommendation": "推荐给需要构建复杂、长期运行的AI代理或工作流的开发者和团队。适合的应用场景包括需要高度定制化和灵活性的企业级应用，例如自动化任务处理、智能客服系统等。"
}
```
方便：Dashboard / 搜索 / 排序 / 比较

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

### 5. RoadMap 预测

提前嗅探一个仓库的未来路线规划和潜在动向，构建三层情报体系：**显性规划、隐性动态和社区脉搏**。

**输入**：仓库地址（可指定 `main` 与 `next` 分支）  
**输出**：JSON 结构化预测报告

#### 示例输出结构

```json
{
  "repo": "vllm-project/vllm",
  "prediction_timestamp": "2026-07-16T10:00:00Z",
  "confidence_level": "high",
  "next_milestone": "v0.9.0",
  "predicted_directions": [
    {
      "theme": "多模态模型支持",
      "signals": [
        "ROADMAP.md 明确列出 Multi-modal 为 Q3 重点",
        "分支 `feature/vlm-engine` 频繁提交",
        "近期合并了抽象层重构 PR #12345，为多模态架构打底"
      ],
      "source_layer": "显性规划 + 隐性动态",
      "eta": "2026 Q3",
      "confidence": "very high"
    },
    {
      "theme": "PyTorch 原生后端集成",
      "signals": [
        "核心维护者在 Discussions #890 中多次提及将减少对自定义 CUDA 内核的依赖",
        "依赖文件新增 `torch.compile` 相关实验性包",
        "代码中大量出现 `if ENABLE_PT2:` 特性开关"
      ],
      "source_layer": "社区脉搏 + 隐性动态",
      "eta": "2026 Q4",
      "confidence": "medium"
    }
  ],
  "risk_alerts": [
    "里程碑 v0.8.0 已延期 3 次，短期交付能力存疑",
    "核心维护者近一个月活跃度下降 40%"
  ],
  "evidence_materials": {
    "roadmap_md_last_update": "2026-06-20",
    "key_pr_links": [
      "https://github.com/vllm-project/vllm/pull/12345",
      "https://github.com/vllm-project/vllm/pull/12888"
    ],
    "relevant_discussions": [
      "https://github.com/vllm-project/vllm/discussions/890"
    ]
  }
}
```
---

## 需要调用的 GitHub API 清单

下面按功能列出所需的 REST API 和必要的 GraphQL 查询。未标注“官方 SDK 封装”的，都是标准 REST 端点。

### 基础信息（所有功能共用）
- `GET /repos/{owner}/{repo}` — 仓库基本信息
- `GET /repos/{owner}/{repo}/languages` — 语言统计
- `GET /repos/{owner}/{repo}/topics` — 主题标签（需要 Accept header）
- `GET /repos/{owner}/{repo}/license` — 许可证

### Repository Analysis / Profile / Comparison
- `GET /repos/{owner}/{repo}/releases` — Releases 列表
- `GET /repos/{owner}/{repo}/commits` — 提交历史（可获取贡献者频率）
- `GET /repos/{owner}/{repo}/issues?state=all&labels=bug,enhancement` — 按标签筛选 Issue
- `GET /repos/{owner}/{repo}/pulls?state=open` — 开放 PR
- `GET /repos/{owner}/{repo}/stats/contributors` — 贡献者统计（需等待缓存生成）
- `GET /repos/{owner}/{repo}/stats/code_frequency` — 代码变更频率

### Release Diff
- `GET /repos/{owner}/{repo}/releases` — 获取版本列表
- `GET /repos/{owner}/{repo}/releases/{release_id}` — 获取单个 Release 的 body（发布说明）
- `GET /repos/{owner}/{repo}/compare/{base}...{head}` — 比较两个标签/提交之间的提交和文件差异

### RoadMap 预测（核心新功能）
这部分调用最为密集，混合了 REST 与 GraphQL。

**显性规划**
- `GET /repos/{owner}/{repo}/contents/ROADMAP.md` （或 `FUTURE.md`, `CHANGELOG.md`） — 读取规划文件内容
- `GET /repos/{owner}/{repo}/milestones` — 所有里程碑及完成状态
- `GET /repos/{owner}/{repo}/issues?labels=proposal,planned,accepted,breaking-change&state=open` — 按规划类标签拉取 Issue

**隐性动态**
- `GET /repos/{owner}/{repo}/branches` — 获取所有分支列表
- `GET /repos/{owner}/{repo}/compare/{base}...{head}` — 比较 `main` 与 `next`/`develop` 分支差异
- `GET /search/code?q=FeatureFlag+repo:{owner}/{repo}+language:python` — 全局代码搜索，用来查 Feature Flag 关键字（需要多次调用不同的特征模式）
- `GET /repos/{owner}/{repo}/git/trees/{branch_sha}?recursive=1` — 获取仓库文件树，辅助定位依赖文件
- 依赖文件内容直接通过 `GET /repos/{owner}/{repo}/contents/{path}` 读取（如 `package.json`）
- `GET /repos/{owner}/{repo}/pulls?state=closed&sort=updated&direction=desc` — 查看最近合并的 PR，结合 `GET /repos/{owner}/{repo}/pulls/{pull_number}` 获取详情，特别关注“只添加测试”或“大规模重构”类型的 PR

**社区脉搏**
- GraphQL 查询 **Discussions**（REST API 不提供 Discussions）：
  ```graphql
  query {
    repository(owner: "owner", name: "repo") {
      discussions(first: 20, orderBy: {field: UPDATED_AT, direction: DESC}) {
        nodes {
          title
          body
          category { name }
          labels(first: 5) { nodes { name } }
          comments(first: 3) { nodes { author { login } body } }
          answer { body }
        }
      }
    }
  }


## 成果
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

