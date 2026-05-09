---
phase: 01-foundation
plan: 01-01
subsystem: testing
tags:
  - infrastructure
  - pytest
  - testing
provides:
  - pytest 测试框架配置
  - 共享 db fixture
  - 冒烟测试验证
requires: []
affects:
  - 01-02 (Database 重构，db fixture 被复用)
  - 01-03 (Blueprint 路由测试，conftest 扩展)
  - 01-04 (Pipeline 测试，conftest 扩展)
tech-stack:
  added:
    - pytest 9.0.3
    - pytest-cov 7.1.0
  patterns:
    - tmp_path 临时文件数据库隔离
key-files:
  created:
    - pyproject.toml
    - tests/__init__.py
    - tests/conftest.py
    - tests/test_smoke.py
  modified:
    - requirements.txt
decisions: []
---

# Phase 01 Plan 01: 测试基础设施 Summary

## One-Liner

建立 pytest 测试框架，提供 tmp_path 隔离数据库 fixture 和 3 个冒烟测试，为后续所有重构提供安全网。

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | 创建 pyproject.toml 和安装测试依赖 | `7a22f83` | pyproject.toml, requirements.txt |
| 2 | 创建测试目录和 conftest.py 共享 fixtures | `e31244a` | tests/__init__.py, tests/conftest.py |
| 3 | 创建冒烟测试验证基础设施 | `7e9cbaa` | tests/test_smoke.py |

## Verification Results

```
tests/test_smoke.py::test_db_fixture_works PASSED
tests/test_smoke.py::test_db_insert_and_query PASSED
tests/test_smoke.py::test_db_article_crud PASSED
3 passed in 0.01s
```

## Success Criteria

- [x] pyproject.toml 包含 `[tool.pytest.ini_options]` 配置段，testpaths = ["tests"]
- [x] requirements.txt 包含 pytest>=8.0.0 和 pytest-cov>=5.0.0
- [x] `pytest tests/ -v` 执行成功，3 个测试全部通过
- [x] conftest.py 的 db fixture 使用 tmp_path 创建隔离数据库
- [x] 测试基础设施可被后续 Wave 的测试文件复用

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

- pyproject.toml: EXISTS
- tests/__init__.py: EXISTS
- tests/conftest.py: EXISTS
- tests/test_smoke.py: EXISTS
- requirements.txt: EXISTS (contains pytest>=8.0.0 and pytest-cov>=5.0.0)
- Commit 7a22f83: FOUND
- Commit e31244a: FOUND
- Commit 7e9cbaa: FOUND
