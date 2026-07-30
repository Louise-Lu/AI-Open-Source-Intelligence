# 系统架构

## 概述

系统由两条并行的分析流水线组成：

```text
┌──────────────────────────────────────────────────────────────┐
│                        前端（React）                          │
│                                                              │
│   Dashboard（仓库画像/分析/对比/Release Diff/Roadmap）         │
│   Chat（自然语言研究对话）                                     │
└──────────────┬───────────────────────────┬───────────────────┘
               │                           │
               ▼                           ▼
┌──────────────────────────┐  ┌────────────────────────────────┐
│   Repo Insights            │  │   Research Agent               │
│   确定性 GitHub 分析      │  │   ReAct 多源自主研究            │
│   输入: owner/repo       │  │   输入: 自然语言查询            │
│   数据源: 仅 GitHub      │  │   数据源: GitHub + 社区 + Web   │
│   输出: 单维度报告        │  │   输出: 综合研究简报            │
└──────────────────────────┘  └────────────────────────────────┘
```

两条流水线共享基础设施（LLM、GitHub API、Evidence Builder），但执行逻辑完全独立。

---

## Repo Insights

确定性流水线，给定 `owner/repo` 直接执行固定流程。

```text
owner/repo
  │
  ▼
EntityAdapter → RepositoryRef
  │
  ▼
ReportPipeline（中枢调度器）
  │
  ├── EvidenceService（并发收集 9 维 GitHub 证据）
  │     └── EvidenceBuilder → IntelligenceEvidence
  │
  └── 按 report_type 分发
        ├── ProfileService    → RepositoryProfile (JSON)
        ├── AnalysisService   → Markdown
        ├── ComparisonService → RepositoryComparisonReport
        ├── ReleaseDiffService → Markdown
        └── RoadmapService    → RoadmapReport (JSON)
```

详见 [RepoInsights.md](./RepoInsights.md)

---

## Research Agent

ReAct 模式的自主研究流水线，处理开放式自然语言问题。

```text
用户查询（自然语言）
  │
  ▼
┌─────────────────────────────────────────────────────────┐
│  编排层（research_agent/）                                │
│                                                         │
│  1. IntentRouter        意图理解 → ResearchIntent        │
│  2. EntityExtractor     实体提取 → ExtractedEntity       │
│  3. EntityResolver      实体标准化 → ResolvedEntity      │
│  4. ExecutionPlanBuilder 执行计划 → ExecutionPlan        │
│                                                         │
│  以上 4 步为确定性流水线（LLM + 规则兜底）                │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│  执行层（agent/）                                        │
│                                                         │
│  5. ResearchPolicy      运行时策略（预算/来源/停止条件）   │
│  6. ReAct Agent         自主工具调用（LangGraph）         │
│     ├── Discovery 工具   搜索发现（5 个）                 │
│     └── Capability 工具  深入读取（10 个）                │
│                                                         │
│  以上为 LLM 自主决策 + Python 策略约束                    │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│  输出层（research_agent/）                                │
│                                                         │
│  7. SignalExtractor     结构化信号提取（4 维度）          │
│  8. Composer            研究简报生成 → ResearchBrief     │
└─────────────────────────────────────────────────────────┘
```

详见 [Agent.md](./Agent.md) 和 [09_Tools.md](./09_Tools.md)

---

## 分层架构

```text
┌─────────────────────────────────────────────────────────┐
│  API 层（FastAPI）                                       │
│                                                         │
│  Insights: GET /repositories/{owner}/{repo}/profile      │
│           GET /repositories/{owner}/{repo}/analysis      │
│           GET /repositories/compare                      │
│           GET /release-diff/repositories/.../diff        │
│           GET /repositories/{owner}/{repo}/roadmap       │
│                                                         │
│  Agent:   POST /chat                                    │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│  服务层                                                  │
│                                                         │
│  Insights: ReportPipeline → 各 Service                  │
│  Agent:   ChatService → Intent → Entity → Plan → Agent  │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│  工具层                                                  │
│                                                         │
│  Insights: GitHubAPI（直接调用）                         │
│  Agent:   Discovery + Capability（15 个工具）            │
│           └── _raw.py（原始 API 调用）                   │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│  数据源                                                  │
│                                                         │
│  GitHub API    HuggingFace API    Tavily / Exa / Brave   │
│  OpenCLI       twitter-cli        Jina Reader            │
│  yt-dlp        feedparser         B站 API                │
└─────────────────────────────────────────────────────────┘
```

---

## 共享基础设施

| 组件 | 路径 | 说明 |
|------|------|------|
| LLM | `llms/deepseek.py` | `deepseek_model`（通用）+ `deepseek_structured_model`（结构化输出） |
| GitHub 客户端 | `sources/github/client.py` | `GitHubAPI` 封装所有 GitHub REST + GraphQL 调用 |
| HuggingFace 客户端 | `sources/huggingface/client.py` | `HuggingFaceClient` |
| Evidence Builder | `evidence/builder.py` | 将原始 API 数据组装为 `IntelligenceEvidence` |
| 工具网关 | `agent/tool_gateway.py` | Policy 检查 + Trace 记录 + Observation 封装 |

---

## 目录结构

```text
backend/
├── agent/                          # Agent 执行层
│   ├── intelligence_agent.py       # ReAct Agent
│   ├── research_policy.py          # 运行时策略
│   ├── state.py                    # Agent 状态
│   ├── tool_gateway.py             # 工具网关（Policy + Trace）
│   ├── trace.py                    # 执行 trace
│   ├── schemas/
│   │   └── discovery_result.py     # DiscoveryResult
│   └── tools/
│       ├── _raw.py                 # 原始 API 调用
│       ├── _shared.py              # 共享基础设施
│       ├── discovery.py            # Discovery 工具（5 个）
│       └── capability.py           # Capability 工具（10 个）
│
├── research_agent/                 # 研究编排层
│   ├── intent.py                   # 意图理解
│   ├── entity_extractor.py         # 实体提取
│   ├── entity_resolver.py          # 实体标准化
│   ├── context_builder.py          # 执行计划构建
│   ├── signal_extractor.py         # 信号提取
│   ├── composer.py                 # 简报生成
│   ├── api/chat.py                 # Chat API
│   ├── schemas/                    # 数据模型
│   └── services/chat_service.py    # 主编排入口
│
├── repo_insights/                  # Repo Insights Pipeline
│   ├── api/                        # REST API 路由
│   ├── services/                   # 业务逻辑
│   ├── evidence/                   # 证据收集
│   ├── schemas/                    # 数据模型
│   └── prompts/                    # LLM Prompt
│
├── llms/                           # LLM 配置
├── sources/                        # 数据源客户端
│   ├── github/                     # GitHub API
│   └── huggingface/                # HuggingFace API
├── evidence/                       # Evidence Builder
├── evaluation/                     # 评估框架
└── shared_schemas/                 # 共享数据模型

frontend/
└── src/
    ├── api/                        # API 调用
    └── components/                 # UI 组件
```

---

## 设计原则

### 确定性 + 自主性

编排层（Intent → Entity → Plan）用确定性规则，保证可控和可预测。执行层（Agent 工具调用）用 LLM 自主决策，保证灵活性。

### Fail Fast

- 非研究意图 → 直接返回，不走 Agent
- 无实体 → 引导用户补充，不启动研究
- 无证据 → 返回失败响应，不生成空洞简报

### 策略约束

Research Policy 对 Agent 做来源级控制（`source_scope`）、预算控制（`max_tool_calls`）、停止条件（`required_evidence` + `min_sources` + `min_evidence_items`），防止 Agent 发散。

### 多层兜底

每个 LLM 调用都有规则兜底（`_rule_based_route`、`_rule_based_extract`、`_rule_based_resolve`），保证 LLM 失败时系统仍可用。

### 两阶段工具调用

Discovery（搜索发现）→ Capability（深入读取），Agent 先找到目标再深入，避免盲目读取。
