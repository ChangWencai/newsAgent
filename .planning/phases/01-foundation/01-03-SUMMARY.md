---
phase: 01-foundation
plan: 03
subsystem: web
tags: [flask, blueprint, factory-pattern, refactoring]
dependency_graph:
  requires: [01-02]
  provides: [Blueprint routes, Application Factory]
  affects: [main.py, src/web/, tests/]
tech_stack:
  added: []
  patterns: [Flask Blueprint Factory, Application Factory, Dependency Injection via Closure]
key_files:
  created:
    - src/web/routes/__init__.py
    - src/web/routes/web.py
    - src/web/routes/api.py
    - tests/test_routes.py
  modified:
    - main.py
    - tests/conftest.py
  renamed:
    - src/web/routes.py -> src/web/routes_old.py
decisions:
  - 使用闭包注入 db 替代模块级全局变量
  - Blueprint 使用 url_prefix="" 保持原有 URL 路径不变
  - create_app 无参可调用以兼容 gunicorn
metrics:
  duration_seconds: 300
  completed: "2026-05-09"
---

# Phase 01 Plan 03: Application Factory + Blueprint 拆分 Summary

Flask Application Factory 模式和 Blueprint 拆分实现完成，模块级 `_db` 全局变量完全消除。

## Commit History

| Hash | Message |
|------|---------|
| ceae21c | feat(01-03): 创建 Blueprint 工厂函数，拆分路由包 |
| 6fadedc | refactor(01-03): 重构 main.py 为 Application Factory 模式 |
| d1c0718 | test(01-03): 添加路由集成测试和 app/client fixture |

## Task Results

### Task 1: 创建 Blueprint 工厂函数
- 旧 `src/web/routes.py` 备份为 `src/web/routes_old.py`
- 新建 `src/web/routes/` 包（`__init__.py` + `web.py` + `api.py`）
- `web.py`: 5 个视图路由（dashboard/topics/articles/detail/settings），通过闭包注入 db，零 SQL
- `api.py`: 4 个 API 路由（run-pipeline/delete/rss/health），RSS 函数从 `rss_feed.py` 迁移
- 验证：Blueprint 工厂导入和实例化成功，零 SQL，无全局 `_db`

### Task 2: 重构 main.py 为 Application Factory
- `create_app(db=None, db_path=None)` 支持无参调用（gunicorn 兼容）
- 消除 `init_web()` 和 `create_rss_app()` 旧接口
- `main()` 使用 `create_app(db=db)` 复用同一 db 实例
- 验证：签名正确，无参调用返回 Flask app

### Task 3: 路由集成测试
- `conftest.py` 新增 `app` 和 `client` fixture
- `test_routes.py`: 9 个测试类，15 个测试用例
- 覆盖所有视图路由和 API 路由
- 验证：全部 15 个测试通过

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- [x] 35 tests pass (smoke 3 + database 17 + routes 15)
- [x] No global `_db` in `src/web/routes/`
- [x] No SQL in `web.py` or `api.py`
- [x] `create_app(db=None, db_path=None)` exists with gunicorn-compatible signature
- [x] All template URL paths unchanged
