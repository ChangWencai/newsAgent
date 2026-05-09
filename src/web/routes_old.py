"""Web 界面路由模块"""

import logging
from flask import render_template, jsonify, request
from config.settings import (
    TOPHUB_API_KEY,
    TOPHUB_BASE_URL,
    MINIMAX_MODEL,
    DEFAULT_STYLE,
    MAX_TOPICS_PER_RUN,
    DB_PATH,
    RSS_BASE_URL,
)
from src.storage.database import Database
from src.scheduler.jobs import run_pipeline

logger = logging.getLogger(__name__)

# 模块级变量，由 init_web 初始化
_db: Database = None  # type: ignore[assignment]


def init_web(app, db: Database):
    """注册所有 Web 路由到 Flask app"""
    global _db
    _db = db

    app.add_url_rule("/", view_func=dashboard)
    app.add_url_rule("/topics", view_func=topics_list)
    app.add_url_rule("/articles", view_func=articles_list)
    app.add_url_rule("/article/<int:article_id>", view_func=article_detail)
    app.add_url_rule("/api/run-pipeline", view_func=api_run_pipeline, methods=["POST"])
    app.add_url_rule(
        "/api/article/<int:article_id>/delete",
        view_func=api_delete_article,
        methods=["POST"],
    )
    app.add_url_rule("/settings", view_func=settings_page)


def dashboard():
    """仪表盘首页"""
    conn = _db._get_conn()
    topic_count = conn.execute("SELECT COUNT(*) FROM hot_topics").fetchone()[0]
    article_count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    draft_count = conn.execute(
        "SELECT COUNT(*) FROM articles WHERE status='draft'"
    ).fetchone()[0]
    published_count = conn.execute(
        "SELECT COUNT(*) FROM articles WHERE status='published'"
    ).fetchone()[0]
    recent_rows = conn.execute(
        "SELECT * FROM articles ORDER BY generated_at DESC LIMIT 10"
    ).fetchall()
    recent_articles = [dict(row) for row in recent_rows]
    conn.close()

    return render_template(
        "index.html",
        topic_count=topic_count,
        article_count=article_count,
        draft_count=draft_count,
        published_count=published_count,
        recent_articles=recent_articles,
    )


def topics_list():
    """热点列表"""
    conn = _db._get_conn()
    rows = conn.execute(
        "SELECT * FROM hot_topics ORDER BY id DESC LIMIT 50"
    ).fetchall()
    conn.close()
    topics = [dict(row) for row in rows]
    return render_template("topics.html", topics=topics)


def articles_list():
    """文章列表"""
    status_filter = request.args.get("status", "all")
    conn = _db._get_conn()

    if status_filter in ("draft", "published"):
        rows = conn.execute(
            "SELECT * FROM articles WHERE status=? ORDER BY generated_at DESC",
            (status_filter,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM articles ORDER BY generated_at DESC"
        ).fetchall()

    conn.close()
    articles = [dict(row) for row in rows]
    return render_template(
        "articles.html", articles=articles, current_status=status_filter
    )


def article_detail(article_id: int):
    """文章详情"""
    conn = _db._get_conn()
    row = conn.execute(
        "SELECT * FROM articles WHERE id=?", (article_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return "文章不存在", 404
    article = dict(row)
    return render_template("article_detail.html", article=article)


def api_run_pipeline():
    """触发流水线"""
    try:
        run_pipeline(_db)
        return jsonify({"success": True, "message": "流水线执行成功"})
    except Exception as e:
        logger.exception("流水线执行失败")
        return jsonify({"success": False, "message": f"执行失败: {e}"}), 500


def api_delete_article(article_id: int):
    """删除文章"""
    conn = _db._get_conn()
    row = conn.execute("SELECT id FROM articles WHERE id=?", (article_id,)).fetchone()
    if row is None:
        conn.close()
        return jsonify({"success": False, "message": "文章不存在"}), 404

    conn.execute("DELETE FROM articles WHERE id=?", (article_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "已删除"})


def settings_page():
    """设置页面"""
    config_values = {
        "TOPHUB_BASE_URL": TOPHUB_BASE_URL,
        "TOPHUB_API_KEY": "***" if TOPHUB_API_KEY else "(未设置)",
        "MINIMAX_MODEL": MINIMAX_MODEL,
        "DEFAULT_STYLE": DEFAULT_STYLE,
        "MAX_TOPICS_PER_RUN": MAX_TOPICS_PER_RUN,
        "DB_PATH": DB_PATH,
        "RSS_BASE_URL": RSS_BASE_URL,
    }
    return render_template("settings.html", config=config_values)
