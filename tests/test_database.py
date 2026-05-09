"""Database 类单元测试"""
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from src.storage.database import Database


class TestDatabaseInit:
    """验证单连接、WAL 模式、写锁"""

    def test_single_connection(self, db: Database):
        conn1 = db._get_conn()
        conn2 = db._get_conn()
        assert conn1 is conn2

    def test_wal_mode(self, db: Database):
        mode = db._conn.execute("PRAGMA journal_mode").fetchone()[0]
        # :memory: 数据库使用 memory 模式，文件数据库使用 wal 模式
        assert mode in ("wal", "memory")

    def test_write_lock_exists(self, db: Database):
        assert isinstance(db._write_lock, threading.Lock)


class TestDashboardStats:
    """验证 get_dashboard_stats 方法"""

    def test_empty_dashboard(self, db: Database):
        stats = db.get_dashboard_stats()
        assert stats["topic_count"] == 0
        assert stats["article_count"] == 0
        assert stats["draft_count"] == 0
        assert stats["published_count"] == 0
        assert stats["recent_articles"] == []

    def test_dashboard_with_data(self, db: Database):
        topic_id = db.insert_topic("测试热点", "http://example.com", "100", "科技")
        db.insert_article(topic_id, "文章1", "内容1", "news")
        db.insert_article(topic_id, "文章2", "内容2", "analysis")

        stats = db.get_dashboard_stats()
        assert stats["topic_count"] == 1
        assert stats["article_count"] == 2
        assert stats["draft_count"] == 2
        assert stats["published_count"] == 0
        assert len(stats["recent_articles"]) == 2


class TestGetTopics:
    """验证 get_topics 方法"""

    def test_get_topics_empty(self, db: Database):
        topics = db.get_topics()
        assert topics == []

    def test_get_topics_with_limit(self, db: Database):
        for i in range(5):
            db.insert_topic(f"热点{i}", f"http://example.com/{i}", str(i * 10), "科技")
        topics = db.get_topics(limit=3)
        assert len(topics) == 3
        # 验证 ORDER BY id DESC（最新插入的在前）
        assert topics[0]["title"] == "热点4"
        assert topics[2]["title"] == "热点2"


class TestGetArticles:
    """验证 get_articles 方法"""

    def test_get_articles_all(self, db: Database):
        topic_id = db.insert_topic("热点", "", "", "")
        db.insert_article(topic_id, "文章1", "内容1", "news")
        db.insert_article(topic_id, "文章2", "内容2", "analysis")
        articles = db.get_articles()
        assert len(articles) == 2

    def test_get_articles_by_status(self, db: Database):
        topic_id = db.insert_topic("热点", "", "", "")
        db.insert_article(topic_id, "草稿文章", "内容", "news")
        article_id = db.insert_article(topic_id, "已发布文章", "内容", "analysis")
        db.mark_published(article_id)

        drafts = db.get_articles(status="draft")
        published = db.get_articles(status="published")
        assert len(drafts) == 1
        assert drafts[0]["title"] == "草稿文章"
        assert len(published) == 1
        assert published[0]["title"] == "已发布文章"


class TestGetArticle:
    """验证 get_article 方法"""

    def test_get_existing(self, db: Database):
        topic_id = db.insert_topic("热点", "", "", "")
        article_id = db.insert_article(topic_id, "测试文章", "测试内容", "news")
        article = db.get_article(article_id)
        assert article is not None
        assert article["title"] == "测试文章"
        assert article["content"] == "测试内容"

    def test_get_nonexistent(self, db: Database):
        article = db.get_article(99999)
        assert article is None


class TestDeleteArticle:
    """验证 delete_article 方法"""

    def test_delete_existing(self, db: Database):
        topic_id = db.insert_topic("热点", "", "", "")
        article_id = db.insert_article(topic_id, "待删除", "内容", "news")
        result = db.delete_article(article_id)
        assert result is True
        assert db.get_article(article_id) is None

    def test_delete_nonexistent(self, db: Database):
        result = db.delete_article(99999)
        assert result is False


class TestConcurrentWrites:
    """验证并发写入安全性"""

    def test_concurrent_writes(self):
        db = Database(":memory:")
        errors = []

        def insert_topic(index: int):
            try:
                db.insert_topic(f"并发热点{index}", "", "", "")
            except Exception as e:
                errors.append(str(e))

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(insert_topic, i) for i in range(20)]
            for future in as_completed(futures):
                future.result()

        assert len(errors) == 0, f"并发写入出错: {errors}"
        topics = db.get_topics()
        assert len(topics) == 20
        db._conn.close()


class TestExistingMethodsCompatibility:
    """验证已有方法在重构后仍然正常工作"""

    def test_topic_exists(self, db: Database):
        assert db.topic_exists("不存在") is False
        db.insert_topic("存在", "", "", "")
        assert db.topic_exists("存在") is True

    def test_insert_and_retrieve(self, db: Database):
        topic_id = db.insert_topic("热点A", "http://a.com", "500", "社会")
        assert topic_id > 0
        article_id = db.insert_article(topic_id, "文章A", "内容A", "news")
        assert article_id > 0

        recent = db.get_recent_articles(limit=10)
        assert len(recent) == 1
        assert recent[0]["title"] == "文章A"

        unpublished = db.get_unpublished_articles(limit=10)
        assert len(unpublished) == 1

    def test_mark_published(self, db: Database):
        topic_id = db.insert_topic("热点", "", "", "")
        article_id = db.insert_article(topic_id, "文章", "内容", "news")
        db.mark_published(article_id)

        article = db.get_article(article_id)
        assert article["status"] == "published"
        assert article["published_at"] is not None

        unpublished = db.get_unpublished_articles()
        assert len(unpublished) == 0


class TestCanPublish:
    """验证 can_publish 频率控制逻辑"""

    def test_allowed_when_no_articles(self, db: Database):
        result = db.can_publish()
        assert result["allowed"] is True
        assert result["reason"] == ""
        assert result["next_available"] == ""

    def test_daily_limit_exceeded(self, db: Database):
        topic_id = db.insert_topic("热点", "", "", "")
        for i in range(5):
            article_id = db.insert_article(topic_id, f"文章{i}", "内容", "news")
            db.mark_published(article_id)

        result = db.can_publish(max_daily=5)
        assert result["allowed"] is False
        assert "今日已发布 5 篇" in result["reason"]
        assert "明天 00:00" in result["next_available"]

    def test_daily_limit_not_exceeded(self, db: Database):
        topic_id = db.insert_topic("热点", "", "", "")
        for i in range(3):
            article_id = db.insert_article(topic_id, f"文章{i}", "内容", "news")
            db.mark_published(article_id)

        result = db.can_publish(max_daily=5, min_interval_minutes=0)
        assert result["allowed"] is True

    def test_min_interval_not_met(self, db: Database):
        topic_id = db.insert_topic("热点", "", "", "")
        article_id = db.insert_article(topic_id, "文章", "内容", "news")
        db.mark_published(article_id)

        result = db.can_publish(min_interval_minutes=30)
        assert result["allowed"] is False
        assert "距上次发布仅" in result["reason"]
        assert "分钟后" in result["next_available"]

    def test_custom_limits(self, db: Database):
        topic_id = db.insert_topic("热点", "", "", "")
        for i in range(2):
            article_id = db.insert_article(topic_id, f"文章{i}", "内容", "news")
            db.mark_published(article_id)

        result = db.can_publish(max_daily=10, min_interval_minutes=0)
        assert result["allowed"] is True


class TestTodayPublishCount:
    """验证 get_today_publish_count"""

    def test_zero_when_no_published(self, db: Database):
        assert db.get_today_publish_count() == 0

    def test_counts_only_today(self, db: Database):
        topic_id = db.insert_topic("热点", "", "", "")
        article_id = db.insert_article(topic_id, "文章", "内容", "news")
        db.mark_published(article_id)
        assert db.get_today_publish_count() == 1

    def test_ignores_drafts(self, db: Database):
        topic_id = db.insert_topic("热点", "", "", "")
        db.insert_article(topic_id, "草稿文章", "内容", "news")
        assert db.get_today_publish_count() == 0


class TestLastPublishTime:
    """验证 get_last_publish_time"""

    def test_none_when_no_published(self, db: Database):
        assert db.get_last_publish_time() is None

    def test_returns_latest(self, db: Database):
        topic_id = db.insert_topic("热点", "", "", "")
        article_id = db.insert_article(topic_id, "文章", "内容", "news")
        db.mark_published(article_id)
        result = db.get_last_publish_time()
        assert result is not None


class TestCookieStatus:
    """验证 cookie 状态管理"""

    def test_missing_when_not_set(self, db: Database):
        result = db.get_cookie_status()
        assert result["status"] == "missing"
        assert result["updated_at"] is None

    def test_set_and_get_valid(self, db: Database):
        db.set_cookie_status("valid")
        result = db.get_cookie_status()
        assert result["status"] == "valid"
        assert result["updated_at"] is not None

    def test_set_and_get_expired(self, db: Database):
        db.set_cookie_status("expired")
        result = db.get_cookie_status()
        assert result["status"] == "expired"

    def test_update_existing(self, db: Database):
        db.set_cookie_status("valid")
        db.set_cookie_status("expired")
        result = db.get_cookie_status()
        assert result["status"] == "expired"

    def test_system_kv_table_exists(self, db: Database):
        cursor = db._execute_read(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='system_kv'"
        )
        assert cursor.fetchone() is not None
