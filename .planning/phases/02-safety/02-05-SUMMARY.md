---
phase: 02-safety
plan: 05
subsystem: safety
tags: [playwright, stealth, semantic-locators, anti-detection, cookie-status]
requires: [SAFE-01, SAFE-07]
provides: [playwright-stealth, semantic-locators, cookie-status-tracking]
affects: [src/publisher/toutiao_publisher.py, src/scheduler/jobs.py, publish.py, tests/test_publisher.py]
tech-stack:
  added: [playwright-stealth]
  patterns: [Stealth context wrapper, Semantic locators (get_by_role), Timeout screenshot diagnostics]
key-files:
  created:
    - tests/test_publisher.py
  modified:
    - src/publisher/toutiao_publisher.py
    - src/scheduler/jobs.py
    - publish.py
decisions:
  - ProseMirror 编辑器保留 CSS class 选择器（头条特有组件，无语义属性）
  - 封面选择保留 CSS class（头条特有嵌套组件，语义定位器不可用）
  - Publisher 构造函数 db 参数可选（无 db 时 set_cookie_status 调用被跳过，向后兼容）
metrics:
  duration: ~10 minutes
  completed: 2026-05-09
  tasks: 3
  files: 4
---

# Phase 02 Plan 05: Playwright 反检测 + 语义定位器 Summary

## 概述

playwright-stealth 反检测集成（SAFE-01）+ 语义定位器迁移与超时截图（SAFE-07）+ cookie 状态写入 DB

## 完成的任务

### Task 11: playwright-stealth 集成
- 顶部导入 `from playwright_stealth import Stealth`
- `publish` 方法中 `async_playwright()` 替换为 `Stealth().use_async(async_playwright())`
- 浏览器上下文自动注入反检测脚本（navigator.webdriver 等）
- 保留所有 `random.uniform` 随机延迟不变
- **Commit:** `d809224`

### Task 12: 语义定位器迁移 + 超时截图
- 标题输入：`page.get_by_role("textbox").first` 替换 `page.wait_for_selector("textarea")`
- 发布按钮：`page.get_by_role("button", name="发布")` 替换 `page.wait_for_selector("button.publish-btn-last")`
- ProseMirror 编辑器：保留 `page.locator(".ProseMirror")`（头条特有组件无语义属性）
- 封面选择：保留 CSS class 选择器（头条特有嵌套组件）
- 关键选择器操作包裹 try/except，超时时截图到 `data/screenshots/timeout_{timestamp}.png` 并记录 `logger.error`
- `publish` 方法初始化截图目录 `data/screenshots/`
- 创建 `tests/test_publisher.py`：5 个测试类共 10 个测试用例
- **Commit:** `d809224`

### Task 13: Publisher cookie 状态写入 DB
- `ToutiaoPublisher.__init__` 添加 `db=None` 参数，`self.db = db`
- `_check_login` 成功分支添加 `db.set_cookie_status("valid")`
- `_check_login` 失败/异常分支添加 `db.set_cookie_status("expired")`
- `_wait_login` 成功后添加 `db.set_cookie_status("valid")`
- 所有 `set_cookie_status` 调用前检查 `if self.db:`（向后兼容，无 db 不报错）
- `src/scheduler/jobs.py` 添加 `create_publisher(db)` 工厂函数
- `publish.py` 的 `publish_articles` 创建 publisher 时传入 db
- 测试覆盖：登录有效/过期/异常、无 db 兼容、等待登录成功、create_publisher 工厂
- **Commit:** `d809224`

## 验证结果

- `python -c "from playwright_stealth import Stealth; print('stealth ok')"` — 通过
- `python -c "from src.publisher.toutiao_publisher import ToutiaoPublisher; print('stealth import ok')"` — 通过
- `python -m pytest tests/test_publisher.py -x -v` — **10 passed in 0.42s**
- `python -m pytest tests/test_publisher.py tests/test_database.py tests/test_pipeline.py -x -v` — **48 passed in 0.28s**（无回归）
- toutiao_publisher.py 中标题和发布按钮不再使用纯 CSS class

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None. 所有安全相关改动已在 threat_model 中覆盖：
- T-02-11 (DoS)：playwright-stealth + 随机延迟已 mitigate
- T-02-12 (Tampering)：超时截图 + 详细日志已 mitigate

## Self-Check: PASSED

- src/publisher/toutiao_publisher.py: Stealth 导入、use_async 包装、语义定位器、超时截图、db 参数 — 存在
- tests/test_publisher.py: 存在，10 个测试全部通过
- src/scheduler/jobs.py: create_publisher(db) 函数 — 存在
- publish.py: ToutiaoPublisher(db=db) — 已更新
