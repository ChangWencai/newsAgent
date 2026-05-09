---
phase: 01-foundation
plan: 02
subsystem: database
tags: sqlite, threading, wal, pytest, concurrency

# Dependency graph
requires:
  - phase: 01-foundation-01
    provides: 测试基础设施（pyproject.toml, conftest.py, test_smoke.py）
provides:
  - 单连接 + Lock + WAL 模式的 Database 类
  - 5 个新数据访问方法（get_dashboard_stats, get_topics, get_articles, get_article, delete_article）
  - 完整的 Database 单元测试和并发测试（17 个测试方法）
  - 路由层可零 SQL（routes.py 中的所有 SQL 可替换为 Database 方法调用）
affects:
  - routes.py（可替换直接 SQL 为 Database 方法调用）
  - main.py（Database 实例化方式不变）
  - scheduler/jobs.py（使用 Database 方法不变）

# Tech tracking
tech-stack:
  added: []
  patterns:
    - 单连接 + threading.Lock 写序列化
    - WAL 模式读写并发
    - _execute_write/_execute_read 辅助方法封装
    - :memory: 数据库测试 fixture

key-files:
  created:
    - tests/test_database.py
  modified:
    - src/storage/database.py
    - tests/conftest.py

key-decisions:
  - ":memory: 数据库不支持 WAL 模式（自动降级为 memory），文件数据库正常启用 WAL"
  - "_get_conn() 保留返回 self._conn 以兼容 routes.py 中的直接 SQL 调用"

patterns-established:
  - "Database 单连接模式：__init__ 中创建 self._conn（check_same_thread=False），不再每次操作新建/关闭连接"
  - "写锁序列化：_execute_write 方法中 with self._write_lock 保护所有写操作"
  - "读写分离：_execute_read 不加锁（WAL 模式下并发读安全），_execute_write 加锁"

requirements-completed: [FOUND-02, FOUND-04]

# Metrics
duration: 8min
completed: 2026-05-09
---

# Phase 01 Plan 02: Database 重构总结

**Database 类重构为单连接 + threading.Lock + WAL 模式，补齐 5 个缺失的数据访问方法，新增 17 个单元测试**

## Performance

- **Duration:** 8 min
- **Started:** 2026-05-09
- **Completed:** 2026-05-09
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- Database 类从每次操作新建/关闭连接重构为单连接 + check_same_thread=False
- 启用 WAL 模式（文件数据库），支持读写并发不阻塞
- 添加 threading.Lock 保护所有写操作序列化
- 补齐 5 个缺失方法，使路由层可零 SQL
- 新增 17 个单元测试，包含 20 线程并发写入验证

## Task Commits

1. **Task 1: 重构 Database 为单连接 + Lock + WAL** - `bd0fe8e` (refactor)
2. **Task 2: 补齐 Database 缺失的 5 个方法** - `4132cd2` (feat)
3. **Task 3: 编写 Database 单元测试和并发测试** - `7351032` (test)

## Files Created/Modified
- `src/storage/database.py` - 重构为单连接 + Lock + WAL，新增 5 个方法
- `tests/conftest.py` - 更新 db fixture 为 :memory: 单连接
- `tests/test_database.py` - 新建，17 个测试方法覆盖所有 Database 功能

## Decisions Made
- `:memory:` 数据库不支持 WAL 模式（自动降级为 memory），文件数据库正常启用 WAL — 已验证两种场景
- `_get_conn()` 保留返回 `self._conn` 以兼容 routes.py 中的直接 SQL 调用

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `:memory:` 数据库的 `PRAGMA journal_mode` 返回 `memory` 而非 `wal` — 这是 SQLite 的预期行为，不影响测试正确性。test_wal_mode 测试已调整为接受 `("wal", "memory")` 两种模式。

## Next Phase Readiness
- Database 类已补齐所有数据访问方法，routes.py 中的 5 处直接 SQL 可替换为 Database 方法调用
- 01-03 计划（Application Factory + Blueprint）可立即开始

---
*Phase: 01-foundation*
*Completed: 2026-05-09*
