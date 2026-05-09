"""Pipeline 编排逻辑单元测试"""
from unittest.mock import MagicMock, patch

import pytest

from src.scheduler.jobs import create_pipeline


@pytest.fixture
def mock_crawler():
    return MagicMock()


@pytest.fixture
def mock_writer():
    return MagicMock()


class TestCreatePipeline:
    def test_returns_callable(self, mock_crawler, mock_writer, db):
        pipeline = create_pipeline(mock_crawler, mock_writer, db)
        assert callable(pipeline)

    def test_pipeline_no_topics(self, mock_crawler, mock_writer, db):
        """crawler 返回空列表时不调用 writer"""
        mock_crawler.get_hot_list.return_value = []
        pipeline = create_pipeline(mock_crawler, mock_writer, db)
        pipeline()
        mock_writer.generate_article.assert_not_called()

    def test_pipeline_dedup(self, mock_crawler, mock_writer, db):
        """已存在热点被跳过，新热点被处理"""
        mock_crawler.get_hot_list.return_value = [
            {"title": "已存在热点", "url": "http://1", "hot_value": "100", "category": "测试"},
            {"title": "新热点", "url": "http://2", "hot_value": "200", "category": "测试"},
        ]
        # 预先插入"已存在热点"
        db.insert_topic("已存在热点", "http://old", "50", "测试")

        mock_writer.generate_article.return_value = {
            "title": "新热点文章",
            "content": "文章内容",
            "summary": "摘要",
            "style": "news",
        }
        pipeline = create_pipeline(mock_crawler, mock_writer, db)
        pipeline()

        # writer 只应为"新热点"调用一次
        mock_writer.generate_article.assert_called_once_with(title="新热点", style="auto")

    def test_pipeline_full_flow(self, mock_crawler, mock_writer, db):
        """完整流程验证数据入库：1 热点 -> 1 文章"""
        mock_crawler.get_hot_list.return_value = [
            {"title": "完整流程测试热点", "url": "http://test", "hot_value": "999", "category": "测试"},
        ]
        mock_writer.generate_article.return_value = {
            "title": "完整流程文章",
            "content": "完整文章内容",
            "summary": "摘要",
            "style": "news",
        }
        pipeline = create_pipeline(mock_crawler, mock_writer, db)
        pipeline()

        # 验证热点入库
        topics = db.get_topics()
        assert any(t["title"] == "完整流程测试热点" for t in topics)

        # 验证文章入库
        articles = db.get_articles()
        assert any(a["title"] == "完整流程文章" for a in articles)

    def test_pipeline_writer_failure_continues(self, mock_crawler, mock_writer, db):
        """writer 返回 None 时该条跳过但后续继续"""
        mock_crawler.get_hot_list.return_value = [
            {"title": "热点1", "url": "http://1", "hot_value": "100", "category": "测试"},
            {"title": "热点2", "url": "http://2", "hot_value": "200", "category": "测试"},
        ]
        # 第一次返回 None（失败），第二次成功
        mock_writer.generate_article.side_effect = [
            None,
            {"title": "热点2文章", "content": "内容", "summary": "摘要", "style": "news"},
        ]
        pipeline = create_pipeline(mock_crawler, mock_writer, db)
        pipeline()

        # writer 被调用了两次
        assert mock_writer.generate_article.call_count == 2

        # 只有热点2对应的文章入库
        articles = db.get_articles()
        assert len(articles) == 1
        assert articles[0]["title"] == "热点2文章"

    def test_pipeline_skips_when_daily_limit_exceeded(self, mock_crawler, mock_writer, db):
        """达到每日发布上限时 pipeline 自动跳过"""
        topic_id = db.insert_topic("热点", "", "", "")
        for i in range(5):
            article_id = db.insert_article(topic_id, f"文章{i}", "内容", "news")
            db.mark_published(article_id)

        mock_crawler.get_hot_list.return_value = [
            {"title": "新热点", "url": "http://1", "hot_value": "100", "category": "测试"},
        ]
        pipeline = create_pipeline(mock_crawler, mock_writer, db)
        pipeline()

        mock_crawler.get_hot_list.assert_not_called()
        mock_writer.generate_article.assert_not_called()
