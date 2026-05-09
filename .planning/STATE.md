# NewsAgent State

## Project Reference

- **Core value**: 全自动发现热点 → AI 生成差异化文章 → 无缝发布到头条，无需人工干预
- **Tech stack**: Python 3.13 + Flask + APScheduler + SQLite + Playwright + MiniMax-M2.7
- **Current focus**: Phase 3 — Multi-Source 多平台热点聚合

## Current Position

```
Phase: 3 of 5 (Multi-Source) — COMPLETE
Plan:  5 of 5 (Foundation+Douyin+DailyHot+Adapters+Pipeline) — DONE
Status: Verified
Progress: [██████████░░░░░░░░░░] 60% (Phase 1+2+3 complete)
```

## Performance Metrics

- Requirements completed: 21 / 33 (Phase 1: FOUND-01,03,05,06 + Phase 2: SAFE-01~08 + Phase 3: MULTI-01~09)
- Phases completed: 3 / 5 (Foundation + Safety + Multi-Source)
- Phase 3 plans: 5 plans in 3 waves (03-01 Foundation → 03-02/03/04 Adapters → 03-05 Pipeline)
- Test coverage: 95 tests passing (smoke 3 + database 32 + routes 18 + pipeline 7 + retry 5 + auth 6 + publisher 10 + sensitive 7 + models 3 + registry 3 + adapters 6 + dedup 5)
- Last deployment: N/A

## Accumulated Context

### Key Decisions

| Decision | Rationale |
|----------|-----------|
| 先 Foundation 后 Features | 全局状态和零测试阻塞所有后续开发 |
| DailyHotApi Docker 部署 | 避免爬虫 IP 封禁，覆盖 45+ 平台 |
| MiniMax + DeepSeek 双模型 | 国内访问稳定，fallback 防单点故障 |
| SQLite WAL 模式 | 解决并发写入死锁，单用户场景够用 |
| can_publish() 自动跳过而非报错 | 避免频率超限时 pipeline 异常退出 |
| cookie banner 仅 expired 触发 | missing 状态不报错，避免首次启动误报警 |
| HotTopic frozen dataclass | 不可变数据结构，线程安全 |
| CrawlerProtocol typing.Protocol | 鸭子类型，爬虫无需显式继承 |
| 模块级 register_crawler | 导入即注册，无需手动配置 |

### Known Issues

- `.env` 中存储真实 API 密钥，需迁移到环境变量管理
- `styles.py:70` 大小写匹配 bug
- test_publisher.py 缺少 pytest-asyncio 依赖导致 async 测试失败

## Session Continuity

- **Roadmap created**: 2026-05-09
- **Phase 1 complete**: 2026-05-09 — 5 个计划完成，40 个测试通过
- **Phase 2 complete**: 2026-05-09 — 5 个计划完成，88 个测试通过
- **Phase 3 context gathered**: 2026-05-09 — 19 个实现决策已确定
- **Phase 3 planned**: 2026-05-09 — 5 个计划（3 waves），需求覆盖 9/9
- **Phase 3 plan 01 completed**: 2026-05-09 — HotTopic + CrawlerProtocol + Registry + DB source 列
- **Phase 3 plan 02 completed**: 2026-05-09 — DouyinCrawler 迁移到 HotTopic 返回值
- **Phase 3 plan 03 completed**: 2026-05-09 — DailyHotApi 适配器 + docker-compose.yml
- **Phase 3 plan 04 completed**: 2026-05-09 — 微博/知乎/百度适配器，6 个测试通过
- **Phase 3 plan 05 completed**: 2026-05-09 — dedup_topics + 多源 pipeline，95 个测试全部通过
- **Phase 3 complete**: 2026-05-09 — 9/9 多源需求完成，95 个测试通过
- **Next action**: Phase 4 Intelligence — 智能风格匹配、多角度生成、调度持久化

## Phase Summary

| Phase | Goal | Requirements | Status |
|-------|------|-------------|--------|
| 1. Foundation | 消除全局状态，建立分层架构 | FOUND-01~06 | Complete |
| 2. Safety | 安全加固与发布策略 | SAFE-01~08 | Complete |
| 3. Multi-Source | 多平台热点聚合 | MULTI-01~09 | Complete |
| 4. Intelligence | 智能内容生成 | INTEL-01~05 | Not started |
| 5. Production | 容器化与 CI/CD | PROD-01~05 | Not started |

---

*Last updated: 2026-05-09 — Phase 3 complete (9/9 multi-source requirements, 95 tests passing)*
