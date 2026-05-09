---
phase: 01-foundation
plan: 04
subsystem: pipeline
tags: [di, pipeline, testing, python]

# Dependency graph
requires:
  - phase: 01-foundation-03
    provides: Blueprint 工厂函数模式、Database 类完整方法、测试基础设施
provides:
  - create_pipeline(crawler, writer, db) 工厂函数
  - publish.py 零直接 SQL
  - Pipeline 编排逻辑 5 个单元测试
affects: [scheduler, publisher, testing]

# Tech tracking
tech-stack:
  added: unittest.mock（mock crawler/writer）
  patterns: 构造函数注入（工厂函数返回闭包）、向后兼容入口函数

key-files:
  created:
    - tests/test_pipeline.py
  modified:
    - src/scheduler/jobs.py
    - publish.py

key-decisions:
  - "run_pipeline(db) 保留向后兼容入口，内部调用 create_pipeline"
  - "publish.py 使用 db.get_article(aid) 替代直接 SQL"

patterns-established:
  - "工厂函数模式：create_pipeline(crawler, writer, db) 返回 callable pipeline"

requirements-completed: [FOUND-01]

# Metrics
duration: 15min
completed: 2026-05-09
---

# Phase 1 Plan 04: Pipeline 构造函数注入 Summary

**create_pipeline(crawler, writer, db) 工厂函数消除 run_pipeline 内部硬编码依赖，publish.py 移除直接 SQL，5 个 pipeline 单元测试全部通过**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-05-09T15:00:00Z
- **Completed:** 2026-05-09T15:15:00Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- run_pipeline 重构为 create_pipeline(crawler, writer, db) 构造函数注入模式
- publish.py 中直接 SQL 和 _get_conn 调用替换为 db.get_article(aid)
- tests/test_pipeline.py 包含 5 个测试，覆盖空列表、去重、完整流程、writer 失败场景

## Task Commits

1. **Task 1: 重构 jobs.py 为 create_pipeline 构造函数注入** - `1a588c0` (refactor)
2. **Task 2: 更新 publish.py 使用 Database 方法** - `f8c9e8d` (refactor)
3. **Task 3: 编写 Pipeline 单元测试** - `9f10afe` (test)

## Files Created/Modified
- `src/scheduler/jobs.py` - 新增 create_pipeline 和 _run_pipeline_inner，保留 run_pipeline 兼容入口
- `publish.py` - 移除直接 SQL，使用 db.get_article(aid)
- `tests/test_pipeline.py` - 5 个 pipeline 编排单元测试

## Decisions Made
- run_pipeline(db) 保留向后兼容入口，main.py 和 routes/api.py 无需修改
- DEFAULT_STYLE 为 "auto"，pipeline 透传给 writer.generate_article

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 修正测试断言中的 DEFAULT_STYLE 值**
- **Found during:** Task 3（测试编写）
- **Issue:** test_pipeline_dedup 断言 style="news"，但 config/settings.py 中 DEFAULT_STYLE="auto"
- **Fix:** 修正断言为 style="auto"
- **Files modified:** tests/test_pipeline.py
- **Verification:** pytest 全部通过
- **Committed in:** 9f10afe（Task 3 commit）

---

**Total deviations:** 1 auto-fixed（1 bug）
**Impact on plan:** 极小，仅测试断言修正

## Issues Encountered
None

## User Setup Required
None

## Next Phase Readiness
- Pipeline 构造函数注入完成，后续计划可注入 mock 进行集成测试
- 下一计划 01-05（gunicorn 生产部署）可立即开始

---
*Phase: 01-foundation*
*Completed: 2026-05-09*
