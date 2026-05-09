---
phase: 02-safety
plan: 03
subsystem: rate-limit
tags:
  - rate-limiting
  - cookie-monitoring
  - publish-control
  - health-check
dependency_graph:
  requires:
    - Database (src/storage/database.py)
  provides:
    - can_publish() method
    - system_kv table
    - cookie_status in /health
    - cookie expiry banner
  affects:
    - src/storage/database.py
    - src/scheduler/jobs.py
    - src/web/routes/api.py
    - src/web/templates/base.html
tech_stack:
  added:
    - system_kv table (key-value store for system state)
  patterns:
    - frequency gating via can_publish()
    - polling-based cookie monitoring (5-min interval)
key_files:
  created: []
  modified:
    - src/storage/database.py
    - src/scheduler/jobs.py
    - src/web/routes/api.py
    - src/web/templates/base.html
    - tests/test_database.py
    - tests/test_pipeline.py
    - tests/test_routes.py
decisions:
  - "can_publish() 超限时自动跳过而非报错，pipeline 日志记录原因后静默返回"
  - "cookie banner 仅在 cookie_status === 'expired' 时显示，missing 状态不触发避免首次启动误报"
  - "system_kv 表使用 INSERT OR REPLACE 实现键值更新，updated_at 记录修改时间"
  - "轮询间隔 300 秒（5 分钟），页面加载时立即执行一次检查"
metrics:
  duration_seconds: ~15
  completed: "2026-05-09T17:15:00Z"
  tasks_completed: 2
  files_changed: 7
  tests_added: 21
---

# Phase 2 Plan 03: 发布频率控制 + Cookie 状态监控 Summary

## 一行为概述

Database 新增 system_kv 表和 5 个方法（can_publish/频率控制 + cookie 状态管理），Pipeline 集成频率检查，/health 返回 cookie_status，Web UI 添加 cookie 过期轮询 banner。

## 完成的任务

### Task 7: Database 频率控制 + cookie 状态方法
- `_init_tables` 新增 `system_kv` 表（key, value, updated_at）
- `can_publish(max_daily=5, min_interval_minutes=30)` 返回 `{allowed, reason, next_available}`
- `get_today_publish_count()` 统计当日 published 文章数
- `get_last_publish_time()` 返回最近发布时间或 None
- `set_cookie_status(status)` / `get_cookie_status()` 写入和读取 cookie 状态
- 新增 16 个测试覆盖频率控制和 cookie 状态场景
- **Commit:** `86601d8`

### Task 8: Pipeline 频率检查 + /health 扩展 + cookie banner
- `_run_pipeline_inner` 开头添加 `can_publish()` 检查，不通过则 log + return
- `/health` 端点扩展返回 `{status, cookie_status, cookie_updated_at}`
- `base.html` 新增 cookie 过期红色 banner + 5 分钟轮询 JS
- `cookie_status === 'expired'` 时才显示 banner，`missing` 不触发
- 新增 5 个测试（1 个 pipeline + 4 个 health route）
- **Commit:** `fc8af96`

## 偏差与调整

无偏差，计划按原样执行。

## 测试结果

```
tests/test_database.py: 32 passed
tests/test_pipeline.py: 6 passed
tests/test_routes.py::TestHealthRoute: 4 passed

相关测试共 42 passed in 0.27s
```

## 已知存根

无。

## Self-Check: PASSED

- [x] src/storage/database.py 包含 can_publish/get_today_publish_count/get_last_publish_time/set_cookie_status/get_cookie_status 方法
- [x] src/storage/database.py 包含 system_kv 表定义
- [x] src/scheduler/jobs.py 的 _run_pipeline_inner 开头有 can_publish() 检查
- [x] src/web/routes/api.py 的 /health 返回 cookie_status 字段
- [x] src/web/templates/base.html 包含 cookie banner + checkCookieStatus 轮询逻辑
- [x] 2 个 commit 已确认：86601d8, fc8af96
