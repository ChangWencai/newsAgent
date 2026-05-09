---
phase: 02-safety
plan: 02
subsystem: retry
tags:
  - tenacity
  - retry
  - resilience
  - exponential-backoff
dependency_graph:
  requires:
    - tenacity>=9.1.2
    - requests
    - anthropic
  provides:
    - crawl_retry decorator
    - api_retry decorator
  affects:
    - src/crawler/tophub.py
    - src/writer/generator.py
tech_stack:
  added:
    - tenacity 9.1.2 (retry_if_exception, wait_exponential, before_sleep_log)
  patterns:
    - decorator pattern (tenacity @retry)
    - custom retry predicate (_is_retryable)
key_files:
  created:
    - tests/test_retry.py
  modified:
    - src/crawler/tophub.py
    - src/writer/generator.py
decisions:
  - "crawl_retry 使用 retry_if_exception + 自定义 _is_retryable 谓词区分 4xx/5xx"
  - "api_retry 使用 retry_if_exception_type 捕获三种异常类型"
  - "移除 generator.py 中 generate_article 的 try/except，让异常传播给装饰器"
  - "移除 tophub.py 中 get_hot_list 的 try/except，不再静默吞掉网络错误"
metrics:
  duration_seconds: ~5
  completed: "2026-05-09T17:06:00Z"
  tasks_completed: 3
  files_changed: 3
  tests_added: 5
---

# Phase 2 Plan 02: 指数退避重试机制 Summary

## 一行为概述

为爬虫和 AI API 调用添加 tenacity 指数退避重试装饰器（stop=3, wait 1-10s），含 5 个单元测试全部通过。

## 完成的任务

### Task 4: 爬虫重试装饰器
- `src/crawler/tophub.py` 添加 `crawl_retry` 装饰器
- 使用 `retry_if_exception` + 自定义 `_is_retryable` 谓词
- 网络异常（ConnectionError, Timeout）始终重试
- HTTP 错误仅 429 和 5xx 重试，4xx 不重试
- 移除原有 try/except，让异常传播给装饰器处理
- **Commit:** `c101a7e`

### Task 5: AI API 重试装饰器
- `src/writer/generator.py` 添加 `api_retry` 装饰器
- 使用 `retry_if_exception_type` 捕获 requests.RequestException、anthropic.APIConnectionError、anthropic.RateLimitError
- 移除 generate_article 的 try/except 包装，异常直接传播
- **Commit:** `5df4683`

### Task 6: 重试机制测试
- 创建 `tests/test_retry.py`，5 个测试全部通过
- test_crawl_retry_on_network_error: 模拟网络异常后重试成功
- test_crawl_retry_exhausted: 重试耗尽后抛出原始异常
- test_crawl_retry_does_not_retry_4xx: HTTP 404 不触发重试（仅 1 次调用）
- test_api_retry_on_rate_limit: RateLimitError 后重试成功
- test_api_retry_exhausted: API 重试耗尽后抛出原始异常
- **Commit:** `98274eb`

## 偏差与调整

### 实现调整（非偏差）

**crawl_retry 使用自定义谓词替代 retry_if_exception_type：**
- 原计划使用 `retry_if_exception_type((requests.RequestException,))`
- 问题：`requests.HTTPError` 是 `RequestException` 子类，4xx 也会重试
- 调整：使用 `retry_if_exception(_is_retryable)` + 自定义函数区分 4xx/5xx
- 效果：符合计划要求"HTTP 429 和 5xx 触发重试，4xx 不重试"

**generator.py 移除 try/except：**
- 原代码捕获所有 Exception 返回 None
- 调整后：移除 try/except，让 retryable 异常传播给装饰器，最终失败仍抛出原始异常
- 好处：调用方可以区分"重试后仍失败"和"其他逻辑错误"

## 测试结果

```
tests/test_retry.py::TestCrawlRetry::test_crawl_retry_on_network_error PASSED
tests/test_retry.py::TestCrawlRetry::test_crawl_retry_exhausted PASSED
tests/test_retry.py::TestCrawlRetry::test_crawl_retry_does_not_retry_4xx PASSED
tests/test_retry.py::TestApiRetry::test_api_retry_on_rate_limit PASSED
tests/test_retry.py::TestApiRetry::test_api_retry_exhausted PASSED

5 passed in 10.27s
```

## 已知存根

无。

## Self-Check: PASSED

- [x] src/crawler/tophub.py 存在且包含 @crawl_retry 装饰器
- [x] src/writer/generator.py 存在且包含 @api_retry 装饰器
- [x] tests/test_retry.py 存在且 5 个测试全部通过
- [x] 3 个 commit 已确认：c101a7e, 5df4683, 98274eb
