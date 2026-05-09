# NewsAgent State

## Project Reference

- **Core value**: 全自动发现热点 → AI 生成差异化文章 → 无缝发布到头条，无需人工干预
- **Tech stack**: Python 3.13 + Flask + APScheduler + SQLite + Playwright + MiniMax-M2.7
- **Current focus**: Phase 2 — Safety 安全加固

## Current Position

```
Phase: 2 of 5 (Safety)
Plan:  3 of 5 (频率控制 + Cookie 监控) — COMPLETE
Status: 2/5 Phase 2 plans complete
Progress: [█████░░░░░░░░░░░░░░░] 35% (Phase 1 complete, Phase 2 2/5)
```

## Performance Metrics

- Requirements completed: 7 / 33 (FOUND-01, FOUND-03, FOUND-05, FOUND-06, SAFE-02, SAFE-03, SAFE-08)
- Phases completed: 1 / 5 (Foundation)
- Test coverage: 66 tests passing (smoke 3 + database 32 + routes 19 + pipeline 6 + retry 5 + auth 1)
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

### Known Issues

- `.env` 中存储真实 API 密钥，需迁移到环境变量管理
- ~~模块级全局 `_db` 变量导致测试困难~~ → 已解决（01-03：Blueprint 闭包注入）
- ~~路由层直接执行 SQL，违反分层架构~~ → 已解决（01-03：零 SQL 路由层）
- ~~run_pipeline 内部硬编码实例化~~ → 已解决（01-04：构造函数注入）
- ~~publish.py 直接 SQL 调用~~ → 已解决（01-04：使用 db.get_article）
- ~~零测试覆盖，无 CI/CD~~ → 部分解决（40 个测试通过，待 CI/CD）
- ~~使用 Werkzeug 开发服务器运行在生产环境~~ → 已解决（01-05：gunicorn 替代）
- `styles.py:70` 大小写匹配 bug

### Phase 1 Blockers

无。Phase 1 可立即开始。

## Session Continuity

- **Roadmap created**: 2026-05-09
- **Research completed**: 2026-05-09
- **Phase 1 context gathered**: 2026-05-09 — 16 个实现决策已确定（DI、数据库、测试、部署）
- **Phase 1 planned**: 2026-05-09 — 5 个计划（5 waves），需求覆盖 6/6
- **Phase 1 plan 04 completed**: 2026-05-09 — Pipeline 构造函数注入，40 个测试全部通过
- **Phase 1 plan 05 completed**: 2026-05-09 — gunicorn 生产部署，信号处理 + atexit 安全退出
- **Phase 2 context gathered**: 2026-05-09 — 22 个实现决策已确定（频率、Cookie、密钥、认证、CSRF、敏感词、重试、选择器）
- **Phase 2 planned**: 2026-05-09 — 5 个计划（4 waves），需求覆盖 8/8，验证通过（修复 3 个 blocker）
- **Phase 2 plan 02 completed**: 2026-05-09 — tenacity 指数退避重试机制，5 个测试通过，SAFE-08 完成
- **Phase 2 plan 03 completed**: 2026-05-09 — 发布频率控制 + cookie 状态监控，21 个新测试通过，SAFE-02 + SAFE-03 完成
- **Next action**: 执行 Phase 2 剩余计划（02-01, 02-04, 02-05）

## Phase Summary

| Phase | Goal | Requirements | Status |
|-------|------|-------------|--------|
| 1. Foundation | 消除全局状态，建立分层架构 | FOUND-01~06 | Ready to execute |
| 2. Safety | 安全加固与发布策略 | SAFE-01~08 | 2/5 complete |
| 3. Multi-Source | 多平台热点聚合 | MULTI-01~09 | Not started |
| 4. Intelligence | 智能内容生成 | INTEL-01~05 | Not started |
| 5. Production | 容器化与 CI/CD | PROD-01~05 | Not started |

---

*Last updated: 2026-05-09 — Phase 2 plan 03 complete (SAFE-02 frequency control + SAFE-03 cookie monitoring, 21 new tests passing)*
