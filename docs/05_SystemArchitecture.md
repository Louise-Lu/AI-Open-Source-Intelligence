# 分层架构（Layered Architecture）

                 前端（React）

                      │
                      ▼
              FastAPI Backend
                      │
      ┌───────────────┼────────────────┐
      ▼               ▼                ▼
 GitHub API      LLM Service      Database
      │               │                │
      └───────────────┼────────────────┘

                      ▼
          AI Analysis Engine

                      │

                      ▼

       Project Intelligence Report