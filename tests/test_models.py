"""HotTopic 数据模型单元测试"""

from src.crawler.models import HotTopic


class TestHotTopic:
    def test_create_with_all_fields(self):
        topic = HotTopic(
            title="测试标题",
            url="https://example.com",
            source="douyin",
            hot_value="1000",
            category="科技",
        )
        assert topic.title == "测试标题"
        assert topic.source == "douyin"

    def test_optional_fields_default_empty(self):
        topic = HotTopic(title="标题", url="https://example.com", source="weibo")
        assert topic.hot_value == ""
        assert topic.category == ""
        assert topic.fetched_at == ""

    def test_frozen_immutable(self):
        topic = HotTopic(title="标题", url="https://example.com", source="baidu")
        try:
            topic.title = "新标题"
            assert False, "Should raise FrozenInstanceError"
        except AttributeError:
            pass
