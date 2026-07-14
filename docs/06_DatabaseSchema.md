# Database Schema

## Overview

为了避免重复分析同一个 Repository，并支持后续历史记录和缓存能力，系统需要保存 Repository 元数据以及 AI 分析结果。

V1 数据库保持简单，仅存储必要信息，不涉及用户系统。

---

# Entity Relationship

Repository
│
├── Analysis Report
├── Release
└── Compare History（Future）

---

## Repository

| Field | Type | Description |
|------|------|-------------|
| id | UUID | 主键 |
| owner | String | Repository Owner |
| name | String | Repository Name |
| stars | Integer | Star 数 |
| forks | Integer | Fork 数 |
| language | String | 主要语言 |
| license | String | License |
| github_url | String | GitHub 地址 |
| last_updated | Datetime | GitHub 更新时间 |

---

## Analysis Report

| Field | Type | Description |
|------|------|-------------|
| id | UUID | 主键 |
| repository_id | UUID | Repository 外键 |
| summary | Text | 项目总结 |
| profile | JSON | 项目画像 |
| roadmap | JSON | Roadmap Prediction |
| created_at | Datetime | 创建时间 |

---

## Release

| Field | Type | Description |
|------|------|-------------|
| id | UUID | 主键 |
| repository_id | UUID | Repository 外键 |
| version | String | Release Version |
| published_at | Datetime | 发布时间 |
| notes | Text | Release Notes |

---

## Future

未来可新增：

- User
- Watchlist
- Weekly Report
- Notification