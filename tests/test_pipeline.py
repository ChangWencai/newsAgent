"""Pipeline 编排逻辑单元测试"""
from unittest.mock import MagicMock, patch

import pytest

from src.crawler.models import HotTopic
from src.scheduler.jobs import create_pipeline


class TestCreatePipeline:
    def test_returns_callable(self, db):
        pipeline = create_pipeline(db)
        assert callable(pipeline)

    @patch("src.scheduler.jobs.ArticleGenerator")
    @patch("src.scheduler.jobs.get_registered_crawlers")
    def test_pipeline_no_topics(self, mock_get_crawlers, mock_gen_cls, db):
        """crawler 返回空列表时不调用 writer"""
        mock_crawler = MagicMock()
        mock_crawler.get_hot_list.return_value = []
        mock_crawler.__class__.__name__ = "MockCrawler"
        mock_get_crawlers.return_value = [mock_crawler]

        pipeline = create_pipeline(db)
        pipeline()

        mock_gen_cls.return_value.generate_article.assert_not_called()

    @patch("src.scheduler.jobs.ArticleGenerator")
    @patch("src.scheduler.jobs.get_registered_crawlers")
    def test_pipeline_dedup(self, mock_get_crawlers, mock_gen_cls, db):
        """已存在热点被跳过，新热点被处理"""
        mock_crawler = MagicMock()
        mock_crawler.__class__.__name__ = "MockCrawler"
        mock_crawler.get_hot_list.return_value = [
            HotTopic(title="已存在热点", url="http://1", source="test", hot_value="100", category="测试"),
            HotTopic(title="全新的科技突破", url="http://2", source="test", hot_value="200", category="测试"),
        ]
        mock_get_crawlers.return_value = [mock_crawler]

        # 预先插入"已存在热点"
        db.insert_topic("已存在热点", "http://old", "50", "测试")

        mock_writer = MagicMock()
        mock_writer.generate_article.return_value = {
            "title": "新热点文章",
            "content": "文章内容",
            "summary": "摘要",
            "style": "news",
        }
        mock_gen_cls.return_value = mock_writer

        pipeline = create_pipeline(db)
        pipeline()

        # writer 只应为"全新的科技突破"调用一次
        mock_writer.generate_article.assert_called_once_with(title="全新的科技突破", style="auto")

    @patch("src.scheduler.jobs.ArticleGenerator")
    @patch("src.scheduler.jobs.get_registered_crawlers")
    def test_pipeline_full_flow(self, mock_get_crawlers, mock_gen_cls, db):
        """完整流程验证数据入库：1 热点 -> 1 文章"""
        mock_crawler = MagicMock()
        mock_crawler.__class__.__name__ = "MockCrawler"
        mock_crawler.get_hot_list.return_value = [
            HotTopic(title="完整流程测试热点", url="http://test", source="test", hot_value="999", category="测试"),
        ]
        mock_get_crawlers.return_value = [mock_crawler]

        mock_writer = MagicMock()
        mock_writer.generate_article.return_value = {
            "title": "完整流程文章",
            "content": "完整文章内容",
            "summary": "摘要",
            "style": "news",
        }
        mock_gen_cls.return_value = mock_writer

        pipeline = create_pipeline(db)
        pipeline()

        # 验证热点入库
        topics = db.get_topics()
        assert any(t["title"] == "完整流程测试热点" for t in topics)

        # 验证文章入库
        articles = db.get_articles()
        assert any(a["title"] == "完整流程文章" for a in articles)

    @patch("src.scheduler.jobs.ArticleGenerator")
    @patch("src.scheduler.jobs.get_registered_crawlers")
    def test_pipeline_writer_failure_continues(self, mock_get_crawlers, mock_gen_cls, db):
        """writer 返回 None 时该条跳过但后续继续"""
        mock_crawler = MagicMock()
        mock_crawler.__class__.__name__ = "MockCrawler"
        mock_crawler.get_hot_list.return_value = [
            HotTopic(title="科技突破新闻", url="http://1", source="test", hot_value="100", category="测试"),
            HotTopic(title="体育赛事报道", url="http://2", source="test", hot_value="200", category="测试"),
        ]
        mock_get_crawlers.return_value = [mock_crawler]

        mock_writer = MagicMock()
        # 第一次返回 None（失败），第二次成功
        mock_writer.generate_article.side_effect = [
            None,
            {"title": "体育文章", "content": "内容", "summary": "摘要", "style": "news"},
        ]
        mock_gen_cls.return_value = mock_writer

        pipeline = create_pipeline(db)
        pipeline()

        # writer 被调用了两次（两个完全不同的标题）
        assert mock_writer.generate_article.call_count == 2

        # 只有成功生成的文章入库
        articles = db.get_articles()
        assert len(articles) == 1
        assert articles[0]["title"] == "体育文章"

    def test_pipeline_skips_when_daily_limit_exceeded(self, db):
        """达到每日发布上限时 pipeline 自动跳过"""
        topic_id = db.insert_topic("热点", "", "", "")
        for i in range(5):
            article_id = db.insert_article(topic_id, f"文章{i}", "内容", "news")
            db.mark_published(article_id)

        with patch("src.scheduler.jobs.get_registered_crawlers") as mock_get_crawlers:
            mock_crawler = MagicMock()
            mock_crawler.__class__.__name__ = "MockCrawler"
            mock_crawler.get_hot_list.return_value = [
                HotTopic(title="新热点", url="http://1", source="test", hot_value="100", category="测试"),
            ]
            mock_get_crawlers.return_value = [mock_crawler]

            pipeline = create_pipeline(db)
            pipeline()

            mock_crawler.get_hot_list.assert_not_called()

    @patch("src.scheduler.jobs.ArticleGenerator")
    @patch("src.scheduler.jobs.get_registered_crawlers")
    def test_pipeline_flags_sensitive_articles(self, mock_get_crawlers, mock_gen_cls, db):
        """含敏感词的文章被标记为 flagged 且不进入发布流程"""
        mock_crawler = MagicMock()
        mock_crawler.__class__.__name__ = "MockCrawler"
        mock_crawler.get_hot_list.return_value = [
            HotTopic(title="敏感热点", url="http://1", source="test", hot_value="100", category="测试"),
        ]
        mock_get_crawlers.return_value = [mock_crawler]

        mock_writer = MagicMock()
        mock_writer.generate_article.return_value = {
            "title": "敏感文章",
            "content": "这篇文章涉及赌博和色情内容",
            "summary": "摘要",
            "style": "news",
        }
        mock_gen_cls.return_value = mock_writer

        pipeline = create_pipeline(db)
        pipeline()

        # 文章应入库但状态为 flagged
        articles = db.get_articles()
        assert len(articles) == 1
        assert articles[0]["status"] == "flagged"

    @patch("src.scheduler.jobs.ArticleGenerator")
    @patch("src.scheduler.jobs.get_registered_crawlers")
    def test_pipeline_normal_article_stays_draft(self, mock_get_crawlers, mock_gen_cls, db):
        """不含敏感词的文章保持 draft 状态"""
        mock_crawler = MagicMock()
        mock_crawler.__class__.__name__ = "MockCrawler"
        mock_crawler.get_hot_list.return_value = [
            HotTopic(title="正常热点", url="http://1", source="test", hot_value="100", category="科技"),
        ]
        mock_get_crawlers.return_value = [mock_crawler]

        mock_writer = MagicMock()
        mock_writer.generate_article.return_value = {
            "title": "正常科技文章",
            "content": "人工智能在医疗领域取得重大进展",
            "summary": "摘要",
            "style": "news",
        }
        mock_gen_cls.return_value = mock_writer

        pipeline = create_pipeline(db)
        pipeline()

        articles = db.get_articles()
        assert len(articles) == 1
        assert articles[0]["status"] == "draft"
