# NewsAgent

## What This Is

AI 驱动的全自动新闻生产流水线：从多平台（抖音、微博、知乎、百度）自动发现热点，通过 AI 智能匹配写作风格生成文章，全天候自动发布到头条号。面向流量变现目标，追求高效、大量、高质量的内容产出。

## Core Value

全自动发现热点 → AI 生成差异化文章 → 无缝发布到头条，整个流程无需人工干预，最大化流量变现效率。

## Requirements

### Validated

- ✓ 抖音热点抓取 — 通过今日热榜 API 获取抖音热搜（已有实现）
- ✓ AI 文章生成 — 通过 MiniMax-M2.7 模型生成文章（已有实现）
- ✓ 头条号发布 — 通过 Playwright 浏览器自动化发布到头条（已有实现）
- ✓ RSS Feed 输出 — Flask 提供 RSS 订阅源（已有实现）
- ✓ 定时任务调度 — APScheduler 自动执行抓取和发布（已有实现）
- ✓ Web 管理界面 — Flask + Jinja2 提供文章管理和设置页面（已有实现）
- ✓ 多种文章风格 — 新闻报道、深度分析、轻松解读（已有实现）

### Active

- [ ] 微博热搜抓取 — 支持从微博热榜获取热点
- [ ] 知乎热榜抓取 — 支持从知乎热榜获取热点
- [ ] 百度热搜抓取 — 支持从百度风云榜获取热点
- [ ] 智能风格匹配 — 根据热点类型自动选择最合适的写作风格
- [ ] 热点去重与角度区分 — 同一热点从不同角度生成多篇文章
- [ ] 全天候自动运行 — 优化调度器支持 24/7 持续运行
- [ ] 安全加固 — API 密钥管理、Web UI 认证、CSRF 防护
- [ ] 测试覆盖 — 引入 pytest，目标 80% 覆盖率

### Out of Scope

- 多平台发布（微信公众号、微博等） — 当前聚焦头条单平台，流量变现效果最佳
- 实时视频/图片生成 — 仅做文本内容生产
- 用户评论互动 — 自动化流水线不涉及评论区运营
- 付费订阅功能 — 当前以广告流量变现为主

## Context

### 技术环境
- Python 3.13.2 + Flask + APScheduler + SQLite
- AI: MiniMax-M2.7（通过 Anthropic SDK 兼容接口）
- 发布: Playwright 浏览器自动化（非 API）
- 热点: 今日热榜 API

### 已知问题
- `.env` 中存储真实 API 密钥，需迁移到环境变量管理
- 模块级全局 `_db` 变量导致测试困难
- 路由层直接执行 SQL，违反分层架构
- 零测试覆盖，无 CI/CD
- 使用 Werkzeug 开发服务器运行在生产环境
- `styles.py:70` 大小写匹配 bug

### 代码库状态
- 已有完整代码库扫描（`.planning/codebase/`）
- 6 个功能模块：crawler, writer, publisher, scheduler, storage, web
- 最大文件 189 行（toutiao_publisher.py）

## Constraints

- **Tech stack**: 保持 Python + Flask 生态，不引入新语言
- **目标平台**: 头条号是唯一发布渠道
- **AI 模型**: 使用 MiniMax-M2.7，通过 Anthropic 兼容接口
- **数据存储**: SQLite（单用户场景，无需分布式数据库）
- **部署**: 单机部署，无需考虑水平扩展
- **合规**: AI 生成内容需符合头条平台规范

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 使用 MiniMax 而非 OpenAI | 国内访问稳定，成本更低 | — Pending |
| Playwright 而非 API 发布 | 头条号无公开发布 API | — Pending |
| SQLite 而非 PostgreSQL | 单用户场景，简单够用 | — Pending |
| 全自动无人工审核 | 追求效率最大化，流量变现导向 | — Pending |
| 多平台热点角度区分 | 避免重复，增加文章多样性 | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-09 after initialization*
