---
phase: 02-safety
plan: 04
subsystem: content-safety
tags: [dfa, sensitive-words, filter, pipeline, hot-reload]

requires:
  - phase: 02-safety
    provides: Database 类（insert_article、update_article_status）、pipeline 基础框架
provides:
  - DFA 敏感词过滤模块（SensitiveWordFilter 类 + check_sensitive_words 便捷函数）
  - 敏感词词库文件（16 个初始词）
  - Pipeline 集成：文章生成后自动检查，命中标记 flagged
  - 6 个模块测试 + 2 个 pipeline 集成测试
affects:
  - 02-safety (pipeline 发布流程依赖敏感词过滤)
  - future phases requiring content moderation

tech-stack:
  added: []
  patterns:
    - DFA 多模式匹配算法
    - 文件 mtime 热重载
    - 模块级单例模式

key-files:
  created:
    - src/validator/__init__.py
    - src/validator/sensitive.py
    - data/sensitive_words.txt
    - tests/test_sensitive.py
  modified:
    - src/storage/database.py (新增 update_article_status)
    - src/scheduler/jobs.py (集成敏感词检查)
    - tests/test_pipeline.py (新增 2 个 pipeline 测试)
    - .gitignore (data/* 改为 data/* + !data/sensitive_words.txt)

key-decisions:
  - "使用 DFA 算法而非正则匹配：O(n) 时间复杂度，适合大量敏感词场景"
  - "基于文件 mtime 的热重载：无需重启服务即可更新词库"
  - "敏感词命中直接标记 flagged 而非删除：保留文章供人工审核"
  - "词库文件纳入版本控制：.gitignore 从 data/ 改为 data/* + 白名单例外"

requirements-completed: [SAFE-06]

metrics:
  duration: 10min
  completed: 2026-05-09
---

# Phase 02 Plan 04: 敏感词过滤 Summary

**DFA 敏感词检测模块集成到 pipeline，文章生成后自动扫描，命中敏感词标记 flagged 阻止发布**

## Performance

- **Duration:** 约 10 分钟
- **Started:** 2026-05-09T17:20:00+08:00
- **Completed:** 2026-05-09T17:30:00+08:00
- **Tasks:** 2 (Task 9: DFA 模块, Task 10: Pipeline 集成)
- **Files created:** 4
- **Files modified:** 4

## Accomplishments

- 实现 DFA（确定性有限自动机）敏感词检测算法，O(n) 时间复杂度支持大量敏感词匹配
- 文件 mtime 热重载机制，修改词库文件后自动生效，无需重启服务
- Pipeline 集成：文章 insert 后立即检查敏感词，命中则标记 `status='flagged'` 并跳过
- 完整测试覆盖：6 个模块测试 + 2 个 pipeline 集成测试，全部 46 个相关测试通过

## Task Commits

1. **Task 9: DFA 敏感词模块 + 词库文件** - `9d4cc66` (test)
2. **Task 10: Pipeline 集成敏感词检查** - 变更包含在 `d809224` 和 `e566403` 中（与 02-05 计划并行提交）

## Files Created/Modified

- `src/validator/__init__.py` - 模块空文件
- `src/validator/sensitive.py` - DFA 敏感词检测核心模块（SensitiveWordFilter 类 + check_sensitive_words 便捷函数）
- `data/sensitive_words.txt` - 初始敏感词库（16 个词：赌博、色情、暴力、反动、违禁品、毒品、枪支、炸药、传销、诈骗、假币、黑客、恐怖、分裂、颠覆、窃密）
- `tests/test_sensitive.py` - 6 个测试：基本匹配、无匹配、空文本、多词匹配、热重载、模块函数
- `src/storage/database.py` - 新增 `update_article_status(article_id, status)` 方法
- `src/scheduler/jobs.py` - 集成 `check_sensitive_words`，命中敏感词标记 flagged
- `tests/test_pipeline.py` - 新增 `test_pipeline_flags_sensitive_articles` 和 `test_pipeline_normal_article_stays_draft`
- `.gitignore` - `data/` 改为 `data/*` + `!data/sensitive_words.txt` 白名单

## Decisions Made

- 使用 DFA 算法而非正则：正则在敏感词数量大时性能退化，DFA 为 O(n) 线性扫描
- 基于 mtime 热重载：比定时轮询更高效，文件不变时零开销
- flagged 而非 delete：保留文章内容供人工审核，符合 T-02-10 威胁模型要求
- 词库纳入版本控制：敏感词是项目配置而非运行时数据，应被追踪

## Deviations from Plan

**1. [Rule 3 - Blocking] 安装 playwright_stealth 依赖**
- **Found during:** 运行 pipeline 测试时
- **Issue:** `src.publisher.toutiao_publisher` 导入 `playwright_stealth` 模块缺失导致测试收集失败
- **Fix:** `pip install playwright_stealth`
- **Verification:** pipeline 测试可正常导入并运行

**2. 并行提交合并**
- **Found during:** Task 10 提交阶段
- **Issue:** 另一个 agent（02-05 计划）同时提交了 `d809224`，包含了本计划 Task 10 的 jobs.py 和 database.py 变更
- **Fix:** 确认所有变更均已提交，无需重复提交
- **Verification:** `git status` 无待提交修改，14 个相关测试全部通过

---

**Total deviations:** 2（1 个 blocking 依赖安装，1 个并行提交协调）
**Impact on plan:** 无功能影响，所有代码变更已正确提交

## Issues Encountered

- `data/` 在 `.gitignore` 中导致敏感词文件无法被 git 追踪。修改为 `data/*` + `!data/sensitive_words.txt` 白名单例外模式
- `test_sensitive.py` 共 6 个测试（plan 要求 5 个），额外增加 `test_check_sensitive_words_returns_list` 验证模块级函数

## Next Phase Readiness

- 敏感词过滤已集成到 pipeline，SAFE-06 需求完成
- flagged 文章需人工审核发布流程（后续计划可实现审核 UI）
- 词库规模增长后可考虑引入 Aho-Corasick 算法替代 DFA 以提升性能

## Self-Check: PASSED

- `src/validator/sensitive.py` — FOUND
- `src/validator/__init__.py` — FOUND
- `data/sensitive_words.txt` — FOUND
- `tests/test_sensitive.py` — FOUND
- `02-04-SUMMARY.md` — FOUND
- Commit `9d4cc66` — FOUND
- Commit `d809224` — FOUND
- Commit `e566403` — FOUND

---
*Phase: 02-safety*
*Completed: 2026-05-09*
