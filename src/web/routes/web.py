"""Web 视图路由（仪表盘、热点、文章、设置）"""

import logging
from flask import Blueprint, render_template, request, session, redirect, url_for
from config import settings

logger = logging.getLogger(__name__)


def create_web_bp(db):
    """创建 Web 视图 Blueprint，通过闭包注入 db"""
    bp = Blueprint("web", __name__)

    @bp.before_request
    def require_auth():
        if request.endpoint in ("web.login", "web.static", None):
            return None
        if not settings.ADMIN_PASSWORD:
            return None
        if not session.get("authenticated"):
            return redirect(url_for("web.login"))

    @bp.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "GET":
            return render_template("login.html", error=None)

        password = request.form.get("password", "")
        if password == settings.ADMIN_PASSWORD:
            session["authenticated"] = True
            return redirect(url_for("web.dashboard"))
        return render_template("login.html", error="密码错误"), 401

    @bp.route("/logout")
    def logout():
        session.pop("authenticated", None)
        return redirect(url_for("web.login"))

    @bp.route("/")
    def dashboard():
        stats = db.get_dashboard_stats()
        return render_template(
            "index.html",
            topic_count=stats["topic_count"],
            article_count=stats["article_count"],
            draft_count=stats["draft_count"],
            published_count=stats["published_count"],
            recent_articles=stats["recent_articles"],
        )

    @bp.route("/topics")
    def topics_list():
        topics = db.get_topics(limit=50)
        return render_template("topics.html", topics=topics)

    @bp.route("/articles")
    def articles_list():
        status_filter = request.args.get("status", "all")
        if status_filter in ("draft", "published"):
            articles = db.get_articles(status=status_filter)
        else:
            articles = db.get_articles()
        return render_template(
            "articles.html", articles=articles, current_status=status_filter
        )

    @bp.route("/article/<int:article_id>")
    def article_detail(article_id):
        article = db.get_article(article_id)
        if article is None:
            return "文章不存在", 404
        return render_template("article_detail.html", article=article)

    @bp.route("/settings")
    def settings_page():
        config_values = {
            "TOPHUB_BASE_URL": settings.TOPHUB_BASE_URL,
            "TOPHUB_API_KEY": "***" if settings.TOPHUB_API_KEY else "(未设置)",
            "MINIMAX_MODEL": settings.MINIMAX_MODEL,
            "DEFAULT_STYLE": settings.DEFAULT_STYLE,
            "MAX_TOPICS_PER_RUN": settings.MAX_TOPICS_PER_RUN,
            "DB_PATH": settings.DB_PATH,
            "RSS_BASE_URL": settings.RSS_BASE_URL,
        }
        return render_template("settings.html", config=config_values)

    return bp
