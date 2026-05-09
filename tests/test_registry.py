"""爬虫注册中心单元测试"""

import pytest

from src.crawler import register_crawler, get_registered_crawlers, CRAWLERS
from src.crawler.models import HotTopic


class FakeCrawler:
    def get_hot_list(self) -> list[HotTopic]:
        return [HotTopic(title="测试", url="https://example.com", source="fake")]


@pytest.fixture(autouse=True)
def clear_registry():
    """每个测试前后清理注册表"""
    CRAWLERS.clear()
    yield
    CRAWLERS.clear()


class TestRegistry:
    def test_register_and_get(self):
        crawler = FakeCrawler()
        register_crawler(crawler)
        result = get_registered_crawlers()
        assert len(result) == 1
        assert result[0] is crawler

    def test_get_returns_copy(self):
        register_crawler(FakeCrawler())
        result = get_registered_crawlers()
        result.clear()
        assert len(get_registered_crawlers()) == 1

    def test_multiple_crawlers(self):
        register_crawler(FakeCrawler())
        register_crawler(FakeCrawler())
        assert len(get_registered_crawlers()) == 2
