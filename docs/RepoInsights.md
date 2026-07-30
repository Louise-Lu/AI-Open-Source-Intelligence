# Repo Insights — GitHub 仓库智能分析

## 概述

Repo Insights 是一个确定性的 GitHub 仓库分析系统。给定 `owner/repo`，系统并发收集 9 维 GitHub 证据，通过 LLM 生成结构化报告。

与 Research Agent 的区别：

| | Repo Insights | Research Agent |
|---|---|---|
| 数据源 | 仅 GitHub | GitHub + 社区 + Web + HuggingFace + YouTube |
| 执行方式 | 固定流水线 | ReAct 自主决策 |
| 输入 | `owner/repo` | 自然语言查询 |
| 输出 | 单维度报告 | 综合研究简报 |
| 适用场景 | 精确的仓库级分析 | 开放式研究问题 |

---

## 流水线架构

```text
HTTP 请求（owner/repo）
  │
  ▼
┌─────────────────────────────────────────────┐
│  EntityAdapter                               │
│  owner/repo → RepositoryRef                  │
└─────────────────────┬───────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│  ReportPipeline（中枢调度器）                 │
│  1. 调用 EvidenceService 收集证据             │
│  2. 根据 report_type 分发到对应 Service       │
└─────────────────────┬───────────────────────┘
                      │
         ┌────────────┼────────────┐
         ▼            ▼            ▼
   ┌──────────┐ ┌──────────┐ ┌──────────┐
   │ Profile  │ │ Analysis │ │ Roadmap  │  ...
   │ Service  │ │ Service  │ │ Service  │
   └────┬─────┘ └────┬─────┘ └────┬─────┘
        │             │             │
        ▼             ▼             ▼
   Structured    Markdown      Structured
   JSON          Report        JSON
```

---

## 五大功能

### 1. Repository Profile — 仓库画像

**API**: `GET /repositories/{owner}/{repo}/profile`

**输出**: 结构化 JSON

```json
{
  "project_type": "AI Agent 编排框架",
  "target_users": "AI 应用开发者",
  "core_features": ["状态管理", "持久化执行", "Human-in-the-loop"],
  "technical_stack": ["Python", "LangChain"],
  "strengths": ["活跃维护", "MIT License"],
  "weaknesses": ["学习曲线较陡"],
  "enterprise_readiness": {
    "level": "growing",
    "explanation": "..."
  },
  "summary": "..."
}
```

**Service**: `profile_service.py` → `deepseek_structured_model.with_structured_output(RepositoryProfile)`

---

### 2. Repository Analysis — 仓库分析

**API**: `GET /repositories/{owner}/{repo}/analysis`

**输出**: Markdown 报告

包含五个部分：项目定位、为什么值得关注、维护情况、企业成熟度、未来三个月发展方向。

**Service**: `analysis_service.py` → `deepseek_model.invoke()` → Markdown 字符串

---

### 3. Repository Comparison — 仓库对比

**API**: `GET /repositories/compare?repo1=owner/repo&repo2=owner/repo`

**输出**: 结构化 JSON（`RepositoryComparisonReport`）

分别收集两个仓库的证据，LLM 从五个维度对比：项目定位、技术路线、社区活跃度、企业成熟度、推荐场景。

**Service**: `comparison_service.py` → 两份 evidence → LLM → `RepositoryComparisonReport`

---

### 4. Release Diff — 版本差异分析

**API**: `GET /release-diff/repositories/{owner}/{repo}/releases/diff?old_tag=v1.0&new_tag=v2.0`

**输出**: Markdown 报告

包含：Overview、New Features、Improvements、Bug Fixes、Breaking Changes、Upgrade Recommendation。

**Service**: `release_diff_service.py` → `ReleaseDiffEvidence`（两个 release 的 body）→ LLM → Markdown

---

### 5. Roadmap 预测 — 路线图预测

**API**: `GET /repositories/{owner}/{repo}/roadmap`

**输出**: 结构化 JSON（`RoadmapReport`）

基于三层情报体系预测项目未来方向：

| 情报层 | 数据来源 |
|--------|----------|
| 显性规划 | ROADMAP.md、里程碑、规划类 Issue |
| 隐性动态 | 提交频率、PR 主题、分支活动 |
| 社区脉搏 | Discussions、Reddit、HuggingFace |

```json
{
  "current_stage": "快速迭代期",
  "recent_direction": ["多模态支持", "性能优化"],
  "future_3_months": ["..."],
  "future_6_12_months": ["..."],
  "opportunities": ["..."],
  "risks": ["..."],
  "prediction_reasoning": "..."
}
```

**Service**: `roadmap_service.py` → `deepseek_structured_model.with_structured_output(RoadmapReport)`

---

## 证据收集 — `repo_evidence.py`

`RepositoryEvidenceService` 并发调用 9 个 GitHub API，收集完整的仓库证据：

| 维度 | GitHub API | 说明 |
|------|-----------|------|
| repository | `GET /repos/{owner}/{repo}` | 仓库基本信息 |
| readme | `GET /repos/{owner}/{repo}/readme` | 项目文档 |
| releases | `GET /repos/{owner}/{repo}/releases` | 发布历史 |
| issues | `GET /repos/{owner}/{repo}/issues` | Issue 列表 |
| pull_requests | `GET /repos/{owner}/{repo}/pulls` | PR 列表 |
| commit_activity | `GET /repos/{owner}/{repo}/stats/commit_activity` | 提交活跃度 |
| planning | milestones + planning issues | 规划信号 |
| discussions | GraphQL Discussions | 社区讨论 |
| ecosystem | related repos + dependencies | 生态信号 |

**实现细节：**

- 使用 `ThreadPoolExecutor(max_workers=6)` 并发执行
- 内存级缓存（TTL=300 秒），相同仓库 5 分钟内不重复拉取
- 通过 `EvidenceBuilder.build()` 将原始数据组装为 `IntelligenceEvidence`

---

## 目录结构

```text
backend/repo_insights/
├── api/                              # API 路由层
│   ├── routes.py                     # 根路由 + 健康检查
│   ├── analysis.py                   # GET /repositories/{owner}/{repo}/analysis
│   ├── compare.py                    # GET /repositories/compare
│   ├── profile.py                    # GET /repositories/{owner}/{repo}/profile
│   ├── release_diff.py               # GET /release-diff/repositories/{owner}/{repo}/releases/diff
│   └── roadmap.py                    # GET /repositories/{owner}/{repo}/roadmap
│
├── services/                         # 业务逻辑层
│   ├── report_pipeline.py            # 中枢调度器（分发报告类型）
│   ├── entity_adapter.py             # owner/repo → RepositoryRef
│   ├── profile_service.py            # 画像生成（结构化输出）
│   ├── analysis_service.py           # 分析报告（Markdown）
│   ├── comparison_service.py         # 对比分析
│   ├── release_diff_service.py       # 版本差异（Markdown）
│   └── roadmap_service.py            # 路线图预测（结构化输出）
│
├── evidence/
│   └── repo_evidence.py              # 证据收集（9 维并发 + 缓存）
│
├── schemas/                          # 数据模型
│   ├── entity.py                     # RepositoryRef（repo_insights 专用）
│   ├── profile.py                    # RepositoryProfile
│   ├── analysis.py                   # AnalysisResponse
│   ├── comparison.py                 # RepositoryComparisonReport
│   ├── release_diff.py               # ReleaseDiffEvidence
│   ├── roadmap.py                    # RoadmapReport
│   └── composed_report.py            # ReportContext / ComposedAnswer
│
└── prompts/                          # LLM Prompt 模板
    ├── profile.py                    # PROFILE_PROMPT
    ├── analysis.py                   # ANALYSIS_PROMPT
    ├── comparison.py                 # COMPARISON_PROMPT
    ├── release_diff.py               # RELEASE_DIFF_PROMPT
    └── roadmap.py                    # ROADMAP_PROMPT
```

---

## 数据流

```text
owner/repo
  │
  ▼
EntityAdapter.from_owner_repo(owner, repo)
  │ → RepositoryRef(name="owner/repo", aliases=["repo"])
  │
  ▼
ReportPipeline.build_evidence(entity)
  │ → RepositoryEvidenceService.collect(entity)
  │   → 并发调用 9 个 GitHub API（ThreadPoolExecutor, max_workers=6）
  │   → EvidenceBuilder.build() → IntelligenceEvidence
  │   → 写入缓存（TTL=300s）
  │
  ▼
ReportPipeline.generate_report(entity, report_type)
  │
  ├── "profile"   → ProfileService.generate(evidence)     → RepositoryProfile (JSON)
  ├── "analysis"  → AnalysisService.analyze(evidence)     → str (Markdown)
  ├── "roadmap"   → RoadmapService.predict(evidence)      → RoadmapReport (JSON)
  │
  ▼ (comparison)
ReportPipeline.generate_comparison(left, right)
  │ → 分别 build_evidence → ComparisonService.compare()  → RepositoryComparisonReport
  │
  ▼ (release_diff)
ReportPipeline.generate_release_diff(entity, old_tag, new_tag)
  │ → GitHubAPI.get_releases() → 提取两个 release body
  │ → ReleaseDiffService.compare(evidence)               → str (Markdown)
```

---

## LLM 使用方式

| Service | 模型 | 输出格式 |
|---------|------|----------|
| ProfileService | `deepseek_structured_model` | 结构化 JSON（`with_structured_output`） |
| RoadmapService | `deepseek_structured_model` | 结构化 JSON（`with_structured_output`） |
| AnalysisService | `deepseek_model` | Markdown 字符串 |
| ComparisonService | `deepseek_model` | Markdown 字符串（包装为 `RepositoryComparisonReport`） |
| ReleaseDiffService | `deepseek_model` | Markdown 字符串 |

结构化输出使用 `deepseek_structured_model`（思考模式关闭），避免与 `tool_choice: required` 冲突。
