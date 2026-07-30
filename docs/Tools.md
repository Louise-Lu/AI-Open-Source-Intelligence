# 工具体系

## 概述

Agent 的工具分为两层：**Discovery（发现）** 和 **Capability（采集）**，构成两阶段流水线。

```text
Discovery（搜索引擎）         Capability（阅读器）
    搜索各平台                     深入读取资源
    返回 DiscoveryResult           返回 CapabilityResult
    轻量级元信息                   重量级证据内容
```

Agent 先用 Discovery 找到候选资源，再根据元信息决定哪些值得深入，调用 Capability 读取完整内容。

所有工具通过 `agent/tools/__init__.py` 统一暴露为 `TOOLS` 列表，注册到 LangGraph ReAct Agent。

---

## 统一返回结构

### DiscoveryResult

所有 Discovery 工具返回 `list[DiscoveryResult]`：

```python
{
    "source": "github",              # 来源平台
    "identifier": "owner/repo",      # 资源标识（用于传给 Capability 工具）
    "title": "LangGraph",            # 资源标题
    "url": "https://github.com/...", # 资源链接
    "score": 0.95,                   # 相关性分数
    "reason": "..."                  # 为什么相关
}
```

### CapabilityResult

所有 Capability 工具返回 `dict`（通过 `capability_result()` 构造）：

```python
{
    "source": "github",                    # 来源平台
    "type": "project_profile",             # 证据类型
    "summary": "LangGraph 是一个...",      # 一句话摘要
    "evidence": { ... }                    # 完整证据内容
}
```

---

## Discovery 工具（5 个）

### `github_search(query)`

搜索 GitHub 仓库。

| 参数 | 说明 |
|------|------|
| `query` | 搜索关键词 |

**返回**: 最多 2 个 `DiscoveryResult`

**实现细节**:
- 调用 GitHub Search API，按 stars 排序
- 结果按 **repo 名称相关性** 重排（`_rank_github_search_items`），优先精确匹配 > 包含匹配 > 全名匹配，而非仅按 stars 排序
- `identifier` 格式: `owner/repo`

---

### `huggingface_search(query)`

搜索 HuggingFace 模型。

| 参数 | 说明 |
|------|------|
| `query` | 搜索关键词 |

**返回**: 最多 5 个 `DiscoveryResult`

**实现细节**:
- 调用 HuggingFace Models API，按 downloads 排序
- `identifier` 格式: `model_id`（如 `Qwen/Qwen2.5-7B`）

---

### `community_search(query, platforms)`

搜索社区讨论，支持多平台。

| 参数 | 说明 |
|------|------|
| `query` | 搜索关键词 |
| `platforms` | 目标平台列表，如 `["reddit", "twitter"]` |

**返回**: 各平台的 `DiscoveryResult` 列表，Reddit 结果逐条帖子拆分

**支持平台**:

| 平台 | 实现方式 | `identifier` 格式 |
|------|----------|-------------------|
| Reddit | OpenCLI（`opencli reddit search`） | `reddit:post_id` |
| Twitter | twitter-cli（带进程级缓存） | `twitter:tweet_id` |
| B站 | B站公开搜索 API | `bilibili:bvid` |
| V2EX | V2EX 热门主题 + 本地标题过滤 | `v2ex:topic_id` |

**Reddit 特殊处理**:
- 多候选词策略（`_reddit_query_candidates`）：精准词优先，原始查询兜底
- 结果过滤（`_filter_reddit_yaml_output`）：排除图片帖、无关内容
- 歧义短词（如 "coze"）额外检查 AI 上下文（`_has_reddit_ai_context`）
- timeout: 25 秒

---

### `web_search(query)`

搜索公开 Web 资料。

| 参数 | 说明 |
|------|------|
| `query` | 搜索关键词 |

**返回**: 最多 3 个 `DiscoveryResult`

**搜索引擎**:
- `standard` 模式：Tavily → Brave → Exa
- `deep` 模式：Exa（语义搜索）→ Tavily → Brave
- 自动 fallback：主引擎失败切换备选

`identifier` 格式: 网页 URL

---

### `youtube_search(query)`

搜索 YouTube 视频。

| 参数 | 说明 |
|------|------|
| `query` | 搜索关键词 |

**返回**: 最多 5 个 `DiscoveryResult`

**实现**: 使用 yt-dlp 搜索

`identifier` 格式: YouTube 视频 URL

---

## Capability 工具（10 个）

### GitHub（4 个）

#### `github_project_profile(owner, repo)`

获取项目基础画像。

| 参数 | 说明 |
|------|------|
| `owner` | 仓库所有者 |
| `repo` | 仓库名称 |

**证据内容**: 仓库元信息（stars/forks/language/license/topics）+ README 全文

---

#### `github_project_health(owner, repo)`

获取项目健康度。

| 参数 | 说明 |
|------|------|
| `owner` | 仓库所有者 |
| `repo` | 仓库名称 |

**证据内容**: Issues 列表 + Pull Requests 列表 + 提交活跃度（commit activity）

---

#### `github_release_summary(owner, repo)`

获取发布与规划信息。

| 参数 | 说明 |
|------|------|
| `owner` | 仓库所有者 |
| `repo` | 仓库名称 |

**证据内容**: Releases 列表 + 里程碑（planning signals）

---

#### `github_ecosystem(owner, repo)`

获取社区生态信息。

| 参数 | 说明 |
|------|------|
| `owner` | 仓库所有者 |
| `repo` | 仓库名称 |

**证据内容**: Discussions 信号 + 生态信号（相关项目、依赖关系）

---

### HuggingFace（1 个）

#### `huggingface_model_profile(model_id)`

获取模型画像。

| 参数 | 说明 |
|------|------|
| `model_id` | 模型标识（如 `Qwen/Qwen2.5-7B`） |

**证据内容**: 下载量、likes、任务类型、模型卡片信息

---

### 社区 / Web / 视频（5 个）

#### `community_reader(identifier, platform)`

统一社区资源读取器。

| 参数 | 说明 |
|------|------|
| `identifier` | 资源标识（来自 Discovery 的 `identifier`） |
| `platform` | 平台名称（自动从 identifier 前缀推断） |

**按 identifier 前缀分发**:

| 前缀 | 平台 | 读取内容 |
|------|------|----------|
| `twitter:` | Twitter | 推文内容 |
| `reddit:` | Reddit | 帖子正文 + 热门评论（优先 RSS 快速通道） |
| `bilibili:` | B站 | 视频元信息 + 热门评论（B站公开 API，延迟 ~0.2s） |
| `v2ex:` | V2EX | 帖子内容 + 回复 |

---

#### `webpage_reader(url)`

读取网页正文。

| 参数 | 说明 |
|------|------|
| `url` | 网页 URL |

**实现**: Jina Reader（`r.jina.ai`）渲染并提取正文

**清理逻辑**（`_clean_jina_reader_text`）: 移除图片链接、blob 链接、JavaScript、导航噪声、多余 Markdown 格式

---

#### `youtube_transcript(video_url)`

读取 YouTube 视频字幕。

| 参数 | 说明 |
|------|------|
| `video_url` | YouTube 视频 URL |

**实现**: yt-dlp 获取字幕（VTT 格式 → 纯文本），无字幕时退回视频元信息

---

#### `rss_reader(url)`

读取 RSS/Atom 订阅源。

| 参数 | 说明 |
|------|------|
| `url` | RSS/Atom feed URL |

**实现**: feedparser 解析，返回最新条目列表

---

#### `podcast_transcript(url)`

转录小宇宙播客。

| 参数 | 说明 |
|------|------|
| `url` | 播客 URL |

**实现**: 调用外部转录脚本（依赖 Groq API）

---

## 原始数据层 — `_raw.py`

所有 Discovery 和 Capability 工具的底层 API 调用都封装在 `_raw.py` 中。工具层（`discovery.py` / `capability.py`）负责策略逻辑和结果格式化，`_raw.py` 负责纯数据获取。

```text
discovery.py / capability.py     ← 策略 + 格式化
          │
          ▼
       _raw.py                   ← 原始 API 调用
          │
          ▼
   GitHub API / HuggingFace API / OpenCLI / Jina Reader / yt-dlp / feedparser
```

**`_raw.py` 函数一览**:

| 函数 | 调用方 | 数据源 |
|------|--------|--------|
| `search_github_raw(query)` | `github_search` | GitHub Search API |
| `search_huggingface_raw(query)` | `huggingface_search` | HuggingFace Models API |
| `search_twitter_raw(query)` | `community_search` | twitter-cli |
| `search_reddit_raw(query)` | `community_search` | OpenCLI |
| `read_reddit_post_raw(post_id)` | `community_reader` | RSS + OpenCLI |
| `search_bilibili_raw(query)` | `community_search` | B站公开 API |
| `read_bilibili_video_raw(bvid)` | `community_reader` | B站公开 API |
| `search_v2ex_raw(query)` | `community_search` | V2EX API |
| `search_web_raw(query, mode)` | `web_search` | Tavily / Exa |
| `read_webpage_raw(url)` | `webpage_reader` | Jina Reader |
| `search_youtube_raw(query)` | `youtube_search` | yt-dlp |
| `youtube_transcript_raw(url)` | `youtube_transcript` | yt-dlp |
| `read_rss_raw(url)` | `rss_reader` | feedparser |
| `transcribe_podcast_raw(url)` | `podcast_transcript` | 外部脚本 |

---

## 共享基础设施 — `_shared.py`

| 组件 | 说明 |
|------|------|
| `github` | 全局 `GitHubAPI` 实例 |
| `huggingface` | 全局 `HuggingFaceClient` 实例 |
| `with_policy_logging(tool_name)` | 工具装饰器，进入工具前检查 Runtime Policy |
| `record(tool_name, input, output)` | 工具调用后更新 policy_state + trace，返回带 policy_hint 的 observation |
| `capability_result(...)` | 统一 Capability 返回结构构造函数 |
| `truncate_text(text, limit)` | 截断工具输出，避免 observation 过长（默认 4000 字符） |
| `agent_reach_env()` | 构建子进程环境变量，隔离 TRAE Python 路径 |
| `run_agent_reach_cmd(cmd)` | 运行 Agent Reach CLI 命令（twitter-cli / opencli） |

---

## 工具与来源映射

Research Policy 通过以下映射做来源级控制：

```python
DISCOVERY_TOOL_SOURCE = {
    "github_search": "github",
    "huggingface_search": "huggingface",
    "community_search": "community",
    "web_search": "web",
    "youtube_search": "youtube",
}

CAPABILITY_TOOLS_BY_SOURCE = {
    "github": ["github_project_profile", "github_project_health",
               "github_release_summary", "github_ecosystem"],
    "huggingface": ["huggingface_model_profile"],
    "community": ["community_reader"],
    "web": ["webpage_reader", "rss_reader"],
    "youtube": ["youtube_transcript"],
}
```

当 `source_scope = ["github", "community"]` 时，Agent 只能调用这 2 个来源对应的 Discovery + Capability 工具。
