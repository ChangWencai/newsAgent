"""去重逻辑单元测试"""

from src.crawler.models import HotTopic
from src.scheduler.jobs import dedup_topics


class TestDedupTopics:
    def test_similar_titles_dedup(self):
        """相似标题去重，保留 hot_value 更高的"""
        topics = [
            HotTopic(title="人工智能大会召开", url="https://1.com", source="weibo", hot_value="500"),
            HotTopic(title="人工智能大会今日召开", url="https://2.com", source="douyin", hot_value="1000"),
        ]
        result = dedup_topics(topics)
        assert len(result) == 1
        assert result[0].hot_value == "1000"

    def test_different_titles_no_dedup(self):
        """不同标题不去重，全部保留"""
        topics = [
            HotTopic(title="科技新闻", url="https://1.com", source="weibo", hot_value="100"),
            HotTopic(title="体育赛事", url="https://2.com", source="douyin", hot_value="200"),
        ]
        result = dedup_topics(topics)
        assert len(result) == 2

    def test_empty_list(self):
        """空列表返回空列表"""
        assert dedup_topics([]) == []

    def test_cross_platform_same_event(self):
        """跨平台同事件去重 — 相似标题合并，差异大的保留"""
        topics = [
            HotTopic(title="人工智能大会召开", url="https://1.com", source="weibo", hot_value="500"),
            HotTopic(title="人工智能大会今日召开", url="https://2.com", source="douyin", hot_value="1000"),
            HotTopic(title="AI大会召开", url="https://3.com", source="zhihu", hot_value="800"),
        ]
        result = dedup_topics(topics)
        # "人工智能大会召开" 和 "人工智能大会今日召开" 相似度 0.89 → 合并，保留 1000
        # "AI大会召开" 与前者相似度 ~0.5 < 0.6 → 独立保留
        assert len(result) == 2
        assert result[0].hot_value == "1000"

    def test_numeric_hot_value_sorting(self):
        """数字 hot_value 正确排序（数值排序而非字典序）"""
        topics = [
            HotTopic(title="热点A", url="https://1.com", source="weibo", hot_value="9"),
            HotTopic(title="热点A相同", url="https://2.com", source="douyin", hot_value="100"),
        ]
        result = dedup_topics(topics)
        assert len(result) == 1
        assert result[0].hot_value == "100"
