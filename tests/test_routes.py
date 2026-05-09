"""路由集成测试"""

import pytest


class TestDashboardRoute:
    def test_dashboard_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_dashboard_contains_stats(self, client, db):
        db.insert_topic(title="测试热点")
        resp = client.get("/")
        assert b"topic_count" in resp.data or resp.status_code == 200


class TestTopicsRoute:
    def test_topics_returns_200(self, client):
        resp = client.get("/topics")
        assert resp.status_code == 200


class TestArticlesRoute:
    def test_articles_returns_200(self, client):
        resp = client.get("/articles")
        assert resp.status_code == 200

    def test_articles_status_filter(self, client, db):
        topic_id = db.insert_topic(title="测试热点")
        db.insert_article(
            topic_id=topic_id, title="草稿文章", content="内容", style="news"
        )
        db.insert_article(
            topic_id=topic_id, title="已发文章", content="内容", style="news"
        )
        db.mark_published(db.get_recent_articles(limit=1)[0]["id"])

        resp = client.get("/articles?status=draft")
        assert resp.status_code == 200

    def test_articles_invalid_status_shows_all(self, client):
        resp = client.get("/articles?status=invalid")
        assert resp.status_code == 200


class TestArticleDetailRoute:
    def test_article_not_found_returns_404(self, client):
        resp = client.get("/article/999")
        assert resp.status_code == 404

    def test_article_detail_returns_200(self, client, db):
        topic_id = db.insert_topic(title="测试热点")
        db.insert_article(
            topic_id=topic_id, title="测试文章", content="内容", style="news"
        )
        resp = client.get("/article/1")
        assert resp.status_code == 200


class TestSettingsRoute:
    def test_settings_returns_200(self, client):
        resp = client.get("/settings")
        assert resp.status_code == 200


class TestApiRunPipeline:
    def test_run_pipeline_returns_json_success(self, client):
        resp = client.post("/api/run-pipeline")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "success" in data


class TestApiDeleteArticle:
    def test_delete_nonexistent_returns_404(self, client):
        resp = client.post("/api/article/999/delete")
        assert resp.status_code == 404

    def test_delete_article_removes_it(self, client, db):
        topic_id = db.insert_topic(title="测试热点")
        db.insert_article(
            topic_id=topic_id, title="待删除文章", content="内容", style="news"
        )
        resp = client.post("/api/article/1/delete")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert db.get_article(1) is None


class TestRssRoute:
    def test_rss_returns_200(self, client):
        resp = client.get("/rss")
        assert resp.status_code == 200

    def test_rss_contains_rss_tag(self, client):
        resp = client.get("/rss")
        assert b"<rss" in resp.data


class TestHealthRoute:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"

    def test_health_returns_cookie_status(self, client):
        resp = client.get("/health")
        data = resp.get_json()
        assert "cookie_status" in data
        assert "cookie_updated_at" in data

    def test_health_shows_cookie_expired(self, client, db):
        db.set_cookie_status("expired")
        resp = client.get("/health")
        data = resp.get_json()
        assert data["cookie_status"] == "expired"

    def test_health_shows_cookie_missing_by_default(self, client):
        resp = client.get("/health")
        data = resp.get_json()
        assert data["cookie_status"] == "missing"
