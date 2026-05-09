# Plan 03-05 Summary — 跨平台去重 + 多源 Pipeline 调度

**Completed:** 2026-05-09
**Wave:** 3
**Requirements:** MULTI-08, MULTI-09

## Changes

### src/scheduler/jobs.py
- 新增 `dedup_topics(topics, threshold=0.6)` — 基于 difflib.SequenceMatcher 的标题相似度去重
- `create_pipeline(db)` 签名从三参数变为单参数
- 内部使用 `get_registered_crawlers()` 遍历所有注册爬虫
- 单个爬虫失败 try/except 隔离，不影响其他爬虫
- 频率控制检查移至爬虫调用之前
- `ArticleGenerator` 在 pipeline 内部创建
- `insert_topic` 调用添加 `source=topic.source` 参数

### main.py
- 添加 4 个爬虫模块导入触发自动注册

### tests/test_dedup.py (新建)
- 5 个去重测试用例全部通过

### tests/test_pipeline.py (重写)
- 所有 7 个测试迁移到新签名 `create_pipeline(db)`
- 使用 `@patch("src.scheduler.jobs.get_registered_crawlers")` 注入 mock 爬虫
- 使用 `@patch("src.scheduler.jobs.ArticleGenerator")` 注入 mock writer
- mock 爬虫返回 HotTopic 对象

## Test Results
- 95 tests passing (88 existing + 7 new)
- 0 regressions
