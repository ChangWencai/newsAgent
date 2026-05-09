"""RSS Feed 生成服务（供头条内容源接入）"""

import html as html_mod
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, tostring
from flask import Flask, Response
from config.settings import RSS_BASE_URL
from src.storage.database import Database


def create_rss_app(db: Database):
    app = Flask(__name__)

    @app.route("/rss")
    def rss_feed():
        articles = db.get_recent_articles(limit=20)
        xml_str = _build_rss_xml(articles)
        return Response(xml_str, mimetype="application/rss+xml; charset=utf-8")

    @app.route("/health")
    def health():
        return {"status": "ok"}

    return app


def _build_rss_xml(articles):
    rss = Element("rss", version="2.0")
    channel = SubElement(rss, "channel")

    SubElement(channel, "title").text = "NewsAgent 热点新闻"
    SubElement(channel, "link").text = RSS_BASE_URL
    SubElement(channel, "description").text = "由 AI 自动生成的热点新闻聚合"
    SubElement(channel, "language").text = "zh-cn"
    SubElement(channel, "lastBuildDate").text = _format_rfc822(datetime.now())

    for article in articles:
        item = SubElement(channel, "item")
        SubElement(item, "title").text = article["title"]
        SubElement(item, "link").text = f"{RSS_BASE_URL}/article/{article['id']}"
        SubElement(item, "description").text = _content_to_html(article["content"])
        SubElement(item, "pubDate").text = _format_rfc822(
            datetime.fromisoformat(article["generated_at"])
        )
        SubElement(item, "source").text = "NewsAgent"

    return '<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(rss, encoding="unicode")


def _content_to_html(content):
    escaped = html_mod.escape(content)
    paragraphs = escaped.split("\n")
    html_parts = []
    for p in paragraphs:
        p = p.strip()
        if p:
            html_parts.append(f"<p>{p}</p>")
    return "\n".join(html_parts)


def _format_rfc822(dt):
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0800")
