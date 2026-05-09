---
phase: 02-safety
plan: 01
subsystem: safety
tags: [auth, csrf, config-validation, flask-wtf]
requires: [SAFE-04, SAFE-05]
provides: [web-auth, csrf-protection, config-validation]
affects: [main.py, config/settings.py, src/web/routes/web.py, src/web/templates/]
tech-stack:
  added: [flask-wtf, wtforms]
  patterns: [Flask session auth, CSRFProtect, Application Factory]
key-files:
  created:
    - .env.example
    - src/web/templates/login.html
    - tests/test_auth.py
  modified:
    - config/settings.py
    - main.py
    - src/web/routes/web.py
    - src/web/templates/base.html
decisions:
  - CSRF 豁免 API Blueprint（api 端点无需 CSRF token）
  - 登出使用 GET 路由（与 base.html 表单一致）
  - ADMIN_PASSWORD 默认空字符串（未设置时无密码保护）
metrics:
  duration: ~7 minutes
  completed: 2026-05-09
  tasks: 3
  files: 7
---

# Phase 02 Plan 01: 安全基础设施 Summary

## 概述

API 密钥启动验证（SAFE-04）+ Web UI 密码认证与 CSRF 保护（SAFE-05）

## 完成的任务

### Task 1: config 验证和环境变量模板
- `config/settings.py` 新增 `validate_config()` 函数：启动时检查 `MINIMAX_API_KEY` 和 `TOPHUB_API_KEY` 是否存在，缺失则打印 `[FATAL]` 并 `sys.exit(1)`
- 新增 `ADMIN_PASSWORD` 常量（从环境变量读取，默认空字符串）
- 新增 `REQUIRED_VARS` 和 `OPTIONAL_VARS` 列表，可选变量未设置时打印 `[WARN]`
- `.env.example` 分必填/可选区，包含所有环境变量模板
- **Commit:** `e0ac724`

### Task 2: Flask session 认证 + CSRFProtect
- `main.py` 添加 `CSRFProtect` 初始化、`app.secret_key` 配置、API Blueprint CSRF 豁免
- `src/web/routes/web.py` 添加 `before_request` 认证钩子：未登录重定向 `/login`
- `/login` 路由：GET 显示表单，POST 验证密码（与 `ADMIN_PASSWORD` 比对）
- `/logout` 路由：清除 session 并重定向登录页
- `login.html` 模板：居中卡片布局，密码表单 + CSRF token 隐藏字段
- `base.html` 导航栏添加登出按钮
- **Commit:** `8acc622`

### Task 3: 认证集成测试
- `tests/test_auth.py` 包含 6 个测试用例：
  1. `test_unauthenticated_redirect` — 未认证 GET / 返回 302 到 /login
  2. `test_api_no_auth_required` — /health 无需认证直接返回 200
  3. `test_login_success` — 正确密码 POST /login 返回 302
  4. `test_login_wrong_password` — 错误密码返回 401
  5. `test_logout` — 登出后 session 清除，访问需重新登录
  6. `test_csrf_required` — POST 表单无 CSRF token 返回 400
- **Commit:** `8acc622`（与 Task 2 同一提交）

## 验证结果

- `python -c "from config.settings import validate_config, ADMIN_PASSWORD; print('import ok')"` — 通过
- `python -m pytest tests/test_auth.py -x -v` — **6 passed in 0.32s**
- 未认证 GET / → 302 到 /login
- GET /health → 200 JSON（无需认证）

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

- config/settings.py: validate_config() 和 ADMIN_PASSWORD 可导入
- .env.example: 存在，包含 ADMIN_PASSWORD 和 SECRET_KEY
- main.py: 包含 CSRFProtect 初始化和 csrf.exempt(api_bp)
- src/web/routes/web.py: 包含 before_request、/login、/logout 路由
- src/web/templates/login.html: 存在，包含 csrf_token 隐藏字段
- tests/test_auth.py: 存在，6 个测试全部通过
