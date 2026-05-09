# Project Research Summary

**Project:** NewsAgent
**Domain:** AI 驱动的全自动新闻生产流水线（中国平台热点抓取 + AI 生成 + 头条号发布）
**Researched:** 2026-05-09
**Confidence:** MEDIUM-HIGH

## Executive Summary

NewsAgent 是一个面向中国互联网生态的 AI 内容自动化生产系统。核心流水线：从多平台（抖音、微博、知乎、百度等）自动发现热点话题，通过 AI 模型（MiniMax-M2.7）智能生成差异化文章，再通过 Playwright 浏览器自动化发布到头条号。已有抖音抓取、AI 生成、头条发布三个核心环节的可运行实现，但代码架构存在全局状态、SQL 散落在路由层、零测试覆盖等严重技术债。

研究一致认为：当前系统的首要任务不是扩展功能，而是加固基础架构。四份研究均指向同一结论——先消除全局状态、引入分层架构、建立重试与错误处理机制，然后再扩展多平台抓取和智能功能。

推荐的构建顺序遵循依赖链：基础架构加固（Phase 1）→ 安全与发布策略加固（Phase 2）→ 多平台爬取（Phase 3）→ 智能内容功能（Phase 4）→ 生产就绪（Phase 5）。

## Key Findings

### Recommended Stack

- **Flask 3.1.1** + Application Factory 模式消除全局状态
- **APScheduler 3.11.2 + SQLAlchemyJobStore** 添加任务持久化
- **SQLite + WAL 模式** 解决并发写入问题
- **Playwright + playwright-stealth** 添加反检测
- **MiniMax + DeepSeek** 双模型冗余（均兼容 Anthropic SDK）
- **DailyHotApi (Docker)** 覆盖 45+ 平台热点聚合
- **tenacity** HTTP/API 调用指数退避重试
- **ruff + pytest + bandit** 开发工具链

### Must Have (Table Stakes)

- 多平台热点聚合（至少抖音/微博/知乎/百度）
- 内容语义级去重（精确标题匹配不足）
- 合规检查（敏感词 + AI 审核，违规可致封号）
- 反检测发布（Playwright stealth + 行为模拟）
- 基础数据分析

### Critical Pitfalls

1. **头条号账号永久封禁** — 限制每日 ≤5 篇，间隔 30-120 分钟随机化
2. **Playwright CSS 选择器全面失效** — 使用 role 语义定位器替代
3. **AI 幻觉导致发布虚假新闻** — 生成后事实核查，敏感话题转人工
4. **SQLite 并发写入死锁** — WAL 模式 + Lock 序列化（Phase 1 首先解决）
5. **爬虫 IP 封禁** — DailyHotApi 聚合 API 绕过直连

## Phase Structure (5 Phases)

| Phase | Name | Rationale |
|-------|------|-----------|
| 1 | Foundation | 基础架构加固，阻塞一切后续工作 |
| 2 | Safety | 安全加固与发布策略，扩展前解决风险 |
| 3 | Multi-Source | 多平台热点聚合 |
| 4 | Intelligence | 智能内容功能，风格匹配 + 多角度生成 |
| 5 | Production | 生产就绪，容器化 + CI/CD |

## Confidence

| Area | Confidence |
|------|------------|
| Stack | HIGH |
| Features | HIGH |
| Architecture | HIGH |
| Pitfalls | MEDIUM-HIGH |

---

*Research completed: 2026-05-09*
*Ready for roadmap: yes*
