# Research Agent 架构文档

## 概述

AI Intelligence Agent 是一个基于 LangGraph ReAct 模式的多源研究系统。用户提出自然语言问题，Agent 自主规划搜索策略、调用工具收集证据、最终生成结构化研究简报。

核心设计原则：

- **Fail Fast**：非研究意图直接返回，无实体不启动 Agent，无证据不生成简报
- **确定性 + 自主性结合**：意图理解、实体解析、执行计划用确定性规则；工具调用由 LLM 自主决策
- **策略约束**：Research Policy 对 Agent 的工具调用进行预算控制和来源限制
- **多层兜底**：每个 LLM 调用都有规则兜底，保证系统可用性

---

## 整体流水线

```text
用户查询
  │
  ▼
┌─────────────────────────────────────────────────┐
│  1. Intent Understanding（意图理解）              │
│     intent.py → ResearchIntent                   │
│     objective / entities / focus / depth          │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│  2. Entity Extraction & Resolution（实体提取与标准化）│
│     entity_extractor.py → ExtractedEntity        │
│     entity_resolver.py → ResolvedEntity          │
│     name / entity_scope / entity_origin           │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│  3. ExecutionPlan Builder（执行计划构建）          │
│     context_builder.py → ExecutionPlan           │
│     mode / source_scope / budget / stop_conditions│
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│  4. Research Policy（运行时策略初始化）            │
│     research_policy.py                           │
│     start_research_policy(plan)                  │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│  5. ReAct Agent（自主工具调用）                    │
│     intelligence_agent.py                        │
│     Discovery → Capability → Observe → Loop      │
│     before_tool_call / after_tool_call 约束       │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│  6. Signal Extraction（结构化信号提取）            │
│     signal_extractor.py                          │
│     technology / community / ecosystem / risk     │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│  7. Composer（研究简报生成）                       │
│     composer.py → ResearchBrief                  │
│     summary / key_findings / analysis / sources   │
└─────────────────────────────────────────────────┘
```

编排入口：`services/chat_service.py` 的 `ChatService.chat()` 方法串联以上所有步骤。

---

## 模块详解

### 1. 意图理解 — `intent.py`

将用户自然语言查询解析为结构化的 `ResearchIntent`。

**输出字段：**

| 字段 | 说明 | 示例 |
|------|------|------|
| `objective` | 研究目标分类 | `evaluation`, `trend_analysis`, `information_lookup` |
| `entities` | 研究对象 | `["LangGraph"]` |
| `focus` | 用户关心的信息维度 | `["community", "sentiment"]` |
| `depth` | 研究深度 | `quick`, `standard`, `deep` |

**实现方式：**

- LLM 结构化输出（`deepseek_structured_model`）为主
- 规则兜底（`_rule_based_route`）：关键词匹配推断 objective/focus/depth
- 非研究意图（greeting/small_talk/help）快速判断，直接返回不走 Agent

**正则提取（不经过 LLM）：**

- `extract_time_range(query)`：从查询中提取时间范围（latest/recent/historical/any）
- `extract_platforms(query)`：从查询中提取用户显式提到的平台（reddit/twitter/bilibili/v2ex 等）

---

### 2. 实体提取与标准化 — `entity_extractor.py` + `entity_resolver.py`

**Entity Extractor** 从查询中提取原始实体名称：

- LLM 结构化输出 → `ExtractedEntity(name=...)`
- 规则兜底：已知项目名列表匹配

**Entity Resolver** 将原始实体标准化为 `ResolvedEntity`：

| 字段 | 说明 | 示例 |
|------|------|------|
| `name` | 标准名称 | `"langgraph"` |
| `entity_scope` | 信息存在的平台 | `["github", "web"]` |
| `entity_origin` | 项目归属 | `"international"` / `"chinese"` / `"unknown"` |
| `aliases` | 别名列表 | `["langgraph", "langchain-ai/langgraph"]` |
| `official_name` | 官方名称 | `"LangGraph"` |

`entity_scope` 直接决定后续 `source_scope`（Agent 能访问哪些数据源），`entity_origin` 影响社区平台推断。

---

### 3. 执行计划构建 — `context_builder.py`

`ExecutionPlanBuilder` 根据 `ResearchIntent` + `ResolvedEntity` 列表，纯规则组装出 `ExecutionPlan`，不调用 LLM。

**ExecutionPlan 核心字段：**

```text
┌─ 来自 Intent ──────────────────────────────┐
│  objective    研究目标                       │
│  entities     标准化后的研究对象              │
│  focus        用户关注的信息维度              │
│  time_range   时间范围（正则提取）            │
├─ ContextBuilder 生成 ──────────────────────┤
│  user_goal    一句话任务描述                  │
│  mode         quick / standard / deep        │
│  source_scope 允许的数据源                   │
│  avoid_sources 主动排除的来源                │
│  required_evidence 必须覆盖的证据类型        │
│  community_platforms  社区搜索目标平台       │
├─ 预算 ─────────────────────────────────────┤
│  max_tool_calls             总工具调用上限   │
│  max_discovery_per_source   每源 Discovery 上限│
│  max_empty_retry_per_source 空结果重试上限   │
│  max_reader_per_source      每源 Reader 上限 │
│  max_evidence_items         证据条目上限     │
├─ 停止条件 ─────────────────────────────────┤
│  stop_conditions.min_sources        最少来源数│
│  stop_conditions.min_evidence_items 最少证据数│
└────────────────────────────────────────────┘
```

**社区平台推断逻辑：**

- 中国项目（`entity_origin=chinese`）→ `["bilibili", "reddit"]`
- 海外项目（`entity_origin=international`）→ `["reddit", "twitter"]`
- 用户显式提到平台时优先使用用户指定的

---

### 4. 运行时策略 — `research_policy.py`

在 Agent 执行期间管理工具调用约束。使用 `ContextVar` 实现请求隔离。

**生命周期：**

```text
start_research_policy(plan)   ← 初始化
    ↓
before_tool_call(name, input) ← 每次工具调用前检查
    ↓
[Tool 执行]
    ↓
after_tool_call(name, output) ← 每次工具调用后更新状态
    ↓
build_policy_hint()           ← 生成给 LLM 看的进度提示
    ↓
clear_research_policy()       ← 研究结束清理
```

**before_tool_call 检查顺序：**

1. 工具来源不在 `source_scope` 或在 `avoid_sources` → 拦截
2. 工具预算耗尽（`max_total_tool_calls`）→ 拦截
3. 停止条件满足（`required_evidence` + `min_sources` + `min_evidence_items`）→ 拦截
4. Discovery 工具：`discovery_count + empty_count >= max_discovery + max_empty_retry` → 拦截
5. Reader 工具：`reader_count >= max_reader_per_source` → 拦截

**停止条件（`_is_ready_to_finish`）：**

同时满足以下三项才正常停止：
- `required_evidence` 全部覆盖
- `evidence_sources` 数量 >= `min_sources`
- `evidence_items` >= `min_evidence_items`

或者硬性上限：工具预算用完 / 证据条目达到上限。

---

### 5. ReAct Agent — `intelligence_agent.py`

基于 LangGraph `create_react_agent` 构建的自主研究执行引擎。

**Agent 循环：**

```text
LLM 接收：system_prompt + policy_hint + 历史消息
    ↓
LLM 产生 thought（推理下一步）
    ↓
LLM 选择工具 + 构造参数
    ↓
before_tool_call() 硬约束检查
    ├── 拦截 → 返回 policy_block 给 LLM
    └── 放行 → 工具执行
              ↓
         after_tool_call() 更新状态
              ↓
         build_policy_hint() 生成新提示
              ↓
         结果 + policy_hint 返回 LLM 观察
              ↓
         LLM 决定：继续搜索 / 切换来源 / 停止
```

**Agent 系统提示词包含：**

- 执行计划摘要（user_goal、source_scope、mode）
- 工具分类说明（Discovery 工具 vs Capability 工具）
- 搜索查询生成原则（根据 objective 选择修饰词）
- 研究原则（先 Discovery 后 Capability、避免重复、空结果换关键词）

---

### 6. 工具体系 — `agent/tools/`

工具分为三层：

```text
┌─ Discovery 工具（发现）──────────────────────┐
│  搜索各平台，返回轻量级 DiscoveryResult       │
│  github_search / huggingface_search           │
│  community_search / web_search / youtube_search│
├─ Capability 工具（采集）─────────────────────┤
│  深入读取，返回重量级 CapabilityResult         │
│  github_project_profile / github_project_health│
│  github_release_summary / github_ecosystem     │
│  huggingface_model_profile / community_reader  │
│  webpage_reader / youtube_transcript           │
│  rss_reader / podcast_transcript               │
├─ 原始数据层（_raw.py）───────────────────────┤
│  封装各平台底层 API 调用                       │
│  Discovery 和 Capability 共享                  │
└──────────────────────────────────────────────┘
```

**两阶段流水线：Discover → Acquire**

```text
Agent 调用 github_search("LangGraph")
    → 返回 DiscoveryResult: {identifier: "langchain-ai/langgraph", title: "...", url: "..."}
    → Agent 决定深入读取
Agent 调用 github_project_profile("langchain-ai", "langgraph")
    → 返回 CapabilityResult: {source: "github", evidence: {仓库信息 + README}}
```

**各平台工具一览：**

| 平台 | Discovery | Capability |
|------|-----------|------------|
| GitHub | `github_search` | `github_project_profile`, `github_project_health`, `github_release_summary`, `github_ecosystem` |
| HuggingFace | `huggingface_search` | `huggingface_model_profile` |
| 社区 | `community_search`（Twitter/Reddit/B站/V2EX） | `community_reader`（统一入口，按 identifier 前缀分发） |
| Web | `web_search`（Tavily + Exa） | `webpage_reader`（Jina Reader） |
| YouTube | `youtube_search` | `youtube_transcript` |
| RSS | — | `rss_reader` |
| 播客 | — | `podcast_transcript` |

---

### 7. 信号提取 — `signal_extractor.py`

从多源证据中提取结构化信号，支持四个维度：

| 维度 | 内容 |
|------|------|
| Technology | 技术架构、核心能力、性能基准 |
| Community | 社区情绪、用户反馈、活跃度 |
| Ecosystem | 集成情况、生态系统、采用率 |
| Risk | 潜在风险、依赖问题、维护隐患 |

**维度选择逻辑（`_needed_dimensions`）：**

- 根据 `focus` 决定：用户关心社区 → 只提取 Community，不额外提取 Technology
- 根据 `objective` 兜底：所有研究默认提取 Technology，evaluation 加 Community，trend_analysis 加 Ecosystem

**并行执行：** 四个维度使用 `ThreadPoolExecutor` 并行调用 LLM 结构化输出。

---

### 8. 简报生成 — `composer.py`

将证据和信号组合为最终的 `ResearchBrief`。

**两种模式：**

- **LLM 模式**（`compose`）：调用结构化输出生成完整简报
- **快速模式**（`compose_fast`，默认）：不调用 LLM，直接从证据中提取关键信息拼装

**ResearchBrief 结构：**

```text
summary        一句话总结
key_findings   关键发现列表
analysis       详细分析
signals        结构化信号（来自 SignalExtractor）
sources        来源列表
recommendations 建议
```

---

## 数据模型 — `schemas/`

### `schemas/entity.py`

| 模型 | 用途 |
|------|------|
| `ExtractedEntity` | 原始提取的实体（仅 name） |
| `EntityExtraction` | 实体提取结果容器 |
| `ResolvedEntity` | 标准化实体（含 scope、origin、aliases） |

### `schemas/research.py`

| 模型 | 用途 |
|------|------|
| `ResearchIntent` | 用户研究意图（LLM 输出） |
| `ExecutionPlan` | 统一执行计划（Intent 信息 + 执行参数 + 预算 + 停止条件） |
| `StopConditions` | 结构化停止条件 |
| `TechnologySignal` | 技术维度信号 |
| `CommunitySignal` | 社区维度信号 |
| `EcosystemSignal_` | 生态维度信号 |
| `RiskSignal` | 风险维度信号 |
| `ExtractedSignals` | 信号容器 |
| `ResearchBrief` | 最终研究简报 |

---

## 目录结构

```text
backend/
├── agent/                          # Agent 执行层
│   ├── intelligence_agent.py       # ReAct Agent 定义
│   ├── research_policy.py          # 运行时策略管理
│   ├── state.py                    # Agent 状态定义
│   ├── tool_gateway.py             # 工具网关
│   ├── trace.py                    # 执行 trace 管理
│   ├── schemas/
│   │   └── discovery_result.py     # DiscoveryResult 模型
│   └── tools/
│       ├── _raw.py                 # 原始 API 调用层
│       ├── _shared.py              # 共享工具（策略日志装饰器等）
│       ├── discovery.py            # Discovery 工具（5 个）
│       └── capability.py           # Capability 工具（9 个）
│
├── research_agent/                 # 研究编排层
│   ├── intent.py                   # 意图理解
│   ├── entity_extractor.py         # 实体提取
│   ├── entity_resolver.py          # 实体标准化
│   ├── context_builder.py          # 执行计划构建
│   ├── signal_extractor.py         # 信号提取
│   ├── composer.py                 # 简报生成
│   ├── api/
│   │   └── chat.py                 # Chat API 路由
│   ├── prompts/
│   │   └── extraction.py           # 提取相关 prompt
│   ├── schemas/
│   │   ├── entity.py               # 实体数据模型
│   │   ├── research.py             # 研究流程数据模型
│   │   └── chat.py                 # Chat 数据模型
│   └── services/
│       └── chat_service.py         # 主服务编排入口
│
└── llms/
    └── deepseek.py                 # LLM 实例配置
        ├── deepseek_model          # 通用模型（思考模式开启）
        └── deepseek_structured_model # 结构化输出专用（思考模式关闭）
```

---

## 关键设计决策

### 为什么 time_range 不经过 LLM？

时间范围用正则从 raw_query 提取（`extract_time_range`），不放在 `ResearchIntent` 里让 LLM 判断。原因：
- 时间表达是确定性的（"最近" = recent，"去年" = historical）
- 减少 LLM 输出字段，降低出错概率
- 正则提取更快更稳定

### 为什么 ResearchContext 合并进 ExecutionPlan？

原来有两个模型：`ResearchContext`（研究上下文）和 `ExecutionPlan`（执行控制）。合并原因：
- 两者高度重叠（entities、focus、depth 都重复）
- Agent prompt 需要同时引用两者，增加复杂度
- 合并后一个 `ExecutionPlan` 包含所有信息，简化下游引用

### 为什么用 source_scope 而不是 allowed_tools？

原来用 `allowed_tools` / `blocked_tools` 做工具级白名单/黑名单。改为 `source_scope` / `avoid_sources` 做来源级控制。原因：
- 工具级控制太细，新增工具就要更新白名单
- 来源级控制更灵活：允许 "community" 就自动包含所有社区平台的工具
- 与 Discovery/Capability 两阶段设计更匹配

### 为什么空结果也消耗 Discovery 预算？

原来空结果不消耗预算，让 Agent 无限重试。改为空结果计入 `empty_discovery_counts`，受 `max_empty_retry_per_source` 限制。原因：
- 防止 Agent 对同一来源反复搜索空结果
- 迫使 Agent 换关键词或切换来源
- 总预算 = `max_discovery + max_empty_retry`，平衡探索与效率
