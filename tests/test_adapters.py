"""平台适配器单元测试"""

from unittest.mock import patch

import pytest

from src.crawler.models import HotTopic

MOCK_DATA = [
    {"title": "测试热搜1", "url": "https://example.com/1", "hot": "1000000", "desc": "描述1"},
    {"title": "测试热搜2", "url": "https://example.com/2", "hot": "500000", "desc": "描述2"},
]


class TestWeiboCrawler:
    @patch("src.crawler.weibo.fetch_dailyhot")
    def test_returns_hottopic_list(self, mock_fetch):
        mock_fetch.return_value = MOCK_DATA
        from src.crawler.weibo import WeiboCrawler
        crawler = WeiboCrawler()
        topics = crawler.get_hot_list()
        assert len(topics) == 2
        assert all(isinstance(t, HotTopic) for t in topics)
        assert topics[0].source == "weibo"
        assert topics[0].title == "测试热搜1"
        assert topics[0].category == "微博热搜"

    @patch("src.crawler.weibo.fetch_dailyhot")
    def test_empty_list(self, mock_fetch):
        mock_fetch.return_value = []
        from src.crawler.weibo import WeiboCrawler
        crawler = WeiboCrawler()
        assert crawler.get_hot_list() == []


class TestZhihuCrawler:
    @patch("src.crawler.zhihu.fetch_dailyhot")
    def test_returns_hottopic_list(self, mock_fetch):
        mock_fetch.return_value = MOCK_DATA
        from src.crawler.zhihu import ZhihuCrawler
        crawler = ZhihuCrawler()
        topics = crawler.get_hot_list()
        assert len(topics) == 2
        assert all(isinstance(t, HotTopic) for t in topics)
        assert topics[0].source == "zhihu"
        assert topics[0].category == "知乎热榜"

    @patch("src.crawler.zhihu.fetch_dailyhot")
    def test_empty_list(self, mock_fetch):
        mock_fetch.return_value = []
        from src.crawler.zhihu import ZhihuCrawler
        crawler = ZhihuCrawler()
        assert crawler.get_hot_list() == []


class TestBaiduCrawler:
    @patch("src.crawler.baidu.fetch_dailyhot")
    def test_returns_hottopic_list(self, mock_fetch):
        mock_fetch.return_value = MOCK_DATA
        from src.crawler.baidu import BaiduCrawler
        crawler = BaiduCrawler()
        topics = crawler.get_hot_list()
        assert len(topics) == 2
        assert all(isinstance(t, HotTopic) for t in topics)
        assert topics[0].source == "baidu"
        assert topics[0].category == "百度热搜"

    @patch("src.crawler.baidu.fetch_dailyhot")
    def test_empty_list(self, mock_fetch):
        mock_fetch.return_value = []
        from src.crawler.baidu import BaiduCrawler
        crawler = BaiduCrawler()
        assert crawler.get_hot_list() == []
