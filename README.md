# GitHub Intelligence Agent

一个基于 **LangGraph + LLM + GitHub API Tools** 构建的智能 GitHub 仓库分析 Agent。

不同于传统固定流程的数据分析工具，本项目采用 **AI Agent 架构**：

用户通过自然语言提出问题，Agent 会自主理解任务需求，选择合适的 GitHub 工具获取信息，并基于真实仓库数据生成智能分析结果。

同时提供完整的 **Tool Execution Trace（工具调用追踪）**，帮助用户理解 Agent 的决策过程，提高系统透明度和可调试性。


# ✨ Features


## 🤖 Agent 驱动的仓库智能分析

传统 GitHub 分析工具通常采用固定流程：

```
获取数据
    ↓
处理数据
    ↓
生成报告
```

本项目采用 Agent 工作模式：

```
用户问题

    ↓

理解用户意图

    ↓

选择需要的工具

    ↓

调用 GitHub API

    ↓

分析仓库信息

    ↓

生成智能回答
```


例如：

用户：

```
LangGraph 是否适合企业使用？
```


Agent 自动执行：

```
get_repository
        ↓
get_readme
        ↓
get_releases
        ↓
get_issues
        ↓

生成企业级分析结果
```


---

# 🔧 GitHub Tools


Agent 当前支持多个 GitHub 数据工具。


## Repository Tool

获取仓库基础信息：

- 仓库名称
- 仓库描述
- Stars
- Forks
- 编程语言
- License
- Topics
- 创建时间
- 更新时间


示例：

```json
{
  "full_name": "langchain-ai/langgraph",
  "language": "Python",
  "stars": 37000,
  "license": "MIT License"
}
```

## Profile Tool
- 项目定位
- 社区活跃度
- 企业成熟度
- 技术路线
- Release 演进
- 多项目比较
---

## README Tool

获取项目官方 README 文档。

用于分析：

- 项目定位
- 核心功能
- 技术方向
- 使用场景


---

## Release Tool

获取项目版本发布信息。

用于分析：

- 最新版本
- Release 变化
- 新功能
- Bug 修复
- 升级建议


---

## Issue Tool

获取 GitHub Issue 信息。

用于分析：

- 社区活跃度
- Bug 情况
- 用户反馈
- 项目维护状态


---

## Pull Request Tool

获取 Pull Request 信息。

用于分析：

- 开发活跃程度
- 代码贡献情况
- 社区参与度


---

# 🔍 Agent Tool Trace


为了提高 Agent 的透明度，本项目实现了工具调用追踪。


用户：

```
LangGraph 是做什么的？
```


Agent 执行：

```
🔧 Tool:

get_readme


Input:

{
  "owner": "langchain-ai",
  "repo": "langgraph"
}


Output:

{
  "length": 6351,
  "preview": "Build resilient agents..."
}
```


最终生成：

```
LangGraph 是一个用于构建、管理和部署长期运行且具有状态的 AI Agent 的低级编排框架。
```


Tool Trace 可以帮助：

- 调试 Agent 行为
- 分析工具调用路径
- 定位错误来源
- 提升系统可观察性


---

# 🏗️ System Architecture


```
                 User

                  |

                  v

            React Chat UI

                  |

                  v

              FastAPI

                  |

                  v

          LangGraph Agent

                  |

        ---------------------

        |          |          |

        v          v          v


 Repository    README    Release

   Tool        Tool       Tool


        |

        v


      GitHub API


        |

        v


 Evidence Builder


        |

        v


        LLM


        |

        v


 Intelligent Response
```


---

# 🧠 Agent Workflow


```
用户输入问题

        |

        v

Agent 理解任务

        |

        v

选择 Tool

        |

        v

调用 GitHub API

        |

        v

获取真实数据

        |

        v

Evidence Builder 数据整理

        |

        v

LLM 分析推理

        |

        v

返回最终回答
```


---

# 📦 Evidence Pipeline


GitHub API 返回的数据不会直接发送给 LLM。


系统增加 Evidence Builder 层：

```
GitHub API

    |

    v

Raw Response


    |

    v


Evidence Builder


    |

    v


Structured Evidence


    |

    v


LLM Analysis
```


作用：

- 数据清洗
- 字段标准化
- 降低 Prompt 复杂度
- 提高输出稳定性
- 避免模型直接处理复杂 API 数据


---

# 🛠️ Tech Stack


## Backend

- Python
- FastAPI
- LangGraph
- LangChain
- Pydantic
- Qwen LLM


## Frontend

- React
- Vite
- TailwindCSS


## External API

- GitHub REST API


---

# 📂 Project Structure


```
ai-intelligence-agent

│
├── backend
│
│   ├── agent
│   │
│   │   ├── graph.py
│   │   └── tools.py
│   │
│   ├── tools
│   │
│   │   └── github
│   │
│   ├── evidence
│   │
│   │   ├── builder.py
│   │   └── models.py
│   │
│   ├── services
│   │
│   └── api
│
│
└── frontend
    │
    ├── src
    │
    └── components
```


---

# 🚀 Getting Started


## Backend


进入 backend：

```bash
cd backend
```


创建虚拟环境：

```bash
python -m venv .venv

source .venv/bin/activate
```


安装依赖：

```bash
pip install -r requirements.txt
```


启动：

```bash
uvicorn main:app --reload
```


API:

```
http://localhost:8000
```


Swagger:

```
http://localhost:8000/docs
```


---

## Frontend


进入 frontend：

```bash
cd frontend
```


安装：

```bash
npm install
```


启动：

```bash
npm run dev
```


---

# 💬 Example Questions


## 项目理解

```
LangGraph 是做什么的？
```


## 企业分析

```
这个项目适合企业使用吗？
```


## 技术分析

```
这个项目使用了什么技术？
```


## 社区分析

```
这个项目维护情况怎么样？
```


## Release 分析

```
最近版本有什么变化？
```


## 综合评价

```
这个 GitHub 项目值得学习吗？
```


---

# 🔮 Future Improvements


## Conversation Memory

使用 LangGraph Checkpoint 实现多轮记忆：

```
用户:

LangGraph 是什么？


用户:

它适合企业吗？


Agent:

根据之前上下文继续回答。
```


---

## Advanced Repository Intelligence


计划增加：

- Repository Comparison Agent
- Security Analysis Agent
- Architecture Analysis Agent
- Documentation Analysis Agent


---

## Automated Technical Report


支持：

输入：

```
分析这个 GitHub 项目
```


输出：

```
项目定位

技术架构

社区活跃度

维护情况

企业适用性

风险分析

学习建议
```


---

# 🎯 Project Goal


本项目探索如何使用现代 AI Agent 架构解决真实工程问题：

- Agent 如何理解用户任务
- Agent 如何动态调用工具
- Agent 如何基于外部数据推理
- Agent 如何保持透明和可调试


最终目标是构建一个具备：

✅ Tool Calling  
✅ Agent Reasoning  
✅ External Data Access  
✅ Evidence Pipeline  
✅ Tool Observability  


的完整 AI Agent 系统。


---

# License

MIT License
---


# 分层职责

## API Layer

负责：

- HTTP 请求
- 参数校验
- 返回 JSON

例如：

```
POST /analysis

POST /profile

POST /comparison

POST /release-diff
```

API 不包含业务逻辑。

---

## Service Layer

负责：

整个业务流程。

例如：

Repository Analysis：

```
获取 GitHub 数据

↓

Evidence Builder

↓

调用 LLM

↓

返回报告
```

Service 不负责：

- GitHub API
- Prompt
- 数据结构

它只负责组织流程。

---

## GitHub API Layer

统一封装 GitHub REST API。

例如：

```
RepositoryTool

ReleaseTool

IssueTool

PullRequestTool

ReadmeTool
```

所有 HTTP 请求统一管理。

方便以后：

- Token
- Retry
- Cache

统一扩展。

---

## Evidence Builder

作用：

把 GitHub 原始 JSON

转换成

统一结构化 Evidence。

例如：

```
GitHub JSON

↓

RepositoryInfo

↓

GitHubEvidence
```

Builder 不负责分析。

Builder 只负责：

- 清洗
- 聚合
- 标准化

---

## LLM Layer

负责：

根据 Evidence

输出：

Markdown

或者

Structured JSON。

例如：

Analysis

↓

Markdown

Profile

↓

RepositoryProfile

Comparison

↓

Markdown

Release Diff

↓

Markdown

LLM 不直接调用 GitHub API。

----

# V2 演进

新增：

```
POST /chat
```

用户：

```
Which framework is better for enterprise AI?
```

Agent：

此时：

LLM 自主决定：

调用哪些 Tool。

真正进入：ReAct Agent。

---

# V3 演进

采用 Multi-Agent。

```
                Supervisor

        ┌────────┼────────┐

 Repository   Release   Issue

     │           │         │

      └───────Report Agent───────┘
```

各 Agent：

负责：

自己的专业领域。

最后：

Supervisor 汇总。

---

# 当前目录

```
backend/

api/

services/

github/

report/

prompts/

models/

tools/
```

职责清晰。

方便继续扩展。

---

# 后续 Roadmap
V2.1
- 完善 Trace

V2.2
- Memory

V2.3
- Report Agent

V2.4
- 部署 Docker

V3

- Multi-Agent
- Planning
- RAG
- Knowledge Base


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

AI Intelligence Agent

↓

V3

Multi-Agent Intelligence Platform

---
# License

MIT