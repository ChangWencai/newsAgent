"""重试机制单元测试"""

import pytest
from unittest.mock import patch, MagicMock
import requests

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log

from src.crawler.tophub import DouyinCrawler, crawl_retry
from src.writer.generator import ArticleGenerator, api_retry


class TestCrawlRetry:
    """测试爬虫重试装饰器"""

    def test_crawl_retry_on_network_error(self):
        """前 2 次抛 requests.ConnectionError，第 3 次成功 → 返回结果"""
        call_count = 0

        @crawl_retry
        def flaky_request():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise requests.ConnectionError("network down")
            return "ok"

        result = flaky_request()
        assert result == "ok"
        assert call_count == 3

    def test_crawl_retry_exhausted(self):
        """始终抛 requests.ConnectionError → 最终抛出 ConnectionError"""
        call_count = 0

        @crawl_retry
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise requests.ConnectionError("always down")

        with pytest.raises(requests.ConnectionError, match="always down"):
            always_fail()
        assert call_count == 3

    def test_crawl_retry_does_not_retry_4xx(self):
        """HTTP 404 不应触发重试，仅调用 1 次即抛出异常"""
        call_count = 0

        @crawl_retry
        def http_404():
            nonlocal call_count
            call_count += 1
            mock_resp = MagicMock()
            mock_resp.status_code = 404
            raise requests.HTTPError(response=mock_resp)

        with pytest.raises(requests.HTTPError):
            http_404()
        assert call_count == 1


class TestApiRetry:
    """测试 AI API 重试装饰器"""

    def test_api_retry_on_rate_limit(self):
        """前 1 次抛 RateLimitError，第 2 次成功 → 返回结果"""
        from anthropic import RateLimitError

        call_count = 0

        @api_retry
        def flaky_api():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RateLimitError(
                    message="rate limited",
                    response=MagicMock(status_code=429),
                    body={"error": {"message": "rate limited"}},
                )
            return "article"

        result = flaky_api()
        assert result == "article"
        assert call_count == 2

    def test_api_retry_exhausted(self):
        """持续抛 APIConnectionError → 最终抛出"""
        import httpx
        from anthropic import APIConnectionError

        call_count = 0

        @api_retry
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise APIConnectionError(request=httpx.Request("POST", "https://api.example.com"))

        with pytest.raises(APIConnectionError):
            always_fail()
        assert call_count == 3
