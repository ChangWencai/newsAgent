"""SQLite 数据存储模块"""

import os
import sqlite3
import threading
from datetime import datetime


class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        if db_path != ':memory:':
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._write_lock = threading.Lock()
        self._init_tables()

    def _get_conn(self):
        return self._conn

    def _execute_write(self, sql, params=()):
        with self._write_lock:
            cursor = self._conn.execute(sql, params)
            self._conn.commit()
            return cursor

    def _execute_read(self, sql, params=()):
        return self._conn.execute(sql, params)

    def _init_tables(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS hot_topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT,
                hot_value TEXT,
                category TEXT,
                fetched_at TEXT NOT NULL,
                status TEXT DEFAULT 'pending'
            );

            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                style TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                published_at TEXT,
                status TEXT DEFAULT 'draft',
                FOREIGN KEY (topic_id) REFERENCES hot_topics(id)
            );

            CREATE INDEX IF NOT EXISTS idx_topics_title ON hot_topics(title);
            CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(status);
        """)
        self._conn.commit()

    def topic_exists(self, title):
        row = self._execute_read(
            "SELECT 1 FROM hot_topics WHERE title = ?", (title,)
        ).fetchone()
        return row is not None

    def insert_topic(self, title, url="", hot_value="", category=""):
        now = datetime.now().isoformat()
        cursor = self._execute_write(
            "INSERT INTO hot_topics (title, url, hot_value, category, fetched_at) VALUES (?, ?, ?, ?, ?)",
            (title, url, hot_value, category, now)
        )
        return cursor.lastrowid

    def insert_article(self, topic_id, title, content, style):
        now = datetime.now().isoformat()
        cursor = self._execute_write(
            "INSERT INTO articles (topic_id, title, content, style, generated_at) VALUES (?, ?, ?, ?, ?)",
            (topic_id, title, content, style, now)
        )
        return cursor.lastrowid

    def get_unpublished_articles(self, limit=20):
        rows = self._execute_read(
            "SELECT * FROM articles WHERE status = 'draft' ORDER BY generated_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(row) for row in rows]

    def get_recent_articles(self, limit=20):
        rows = self._execute_read(
            "SELECT * FROM articles ORDER BY generated_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(row) for row in rows]

    def mark_published(self, article_id):
        now = datetime.now().isoformat()
        self._execute_write(
            "UPDATE articles SET status = 'published', published_at = ? WHERE id = ?",
            (now, article_id)
        )

    def get_dashboard_stats(self) -> dict:
        topic_count = self._execute_read(
            "SELECT COUNT(*) FROM hot_topics"
        ).fetchone()[0]
        article_count = self._execute_read(
            "SELECT COUNT(*) FROM articles"
        ).fetchone()[0]
        draft_count = self._execute_read(
            "SELECT COUNT(*) FROM articles WHERE status='draft'"
        ).fetchone()[0]
        published_count = self._execute_read(
            "SELECT COUNT(*) FROM articles WHERE status='published'"
        ).fetchone()[0]
        recent_rows = self._execute_read(
            "SELECT * FROM articles ORDER BY generated_at DESC LIMIT 10"
        ).fetchall()
        return {
            "topic_count": topic_count,
            "article_count": article_count,
            "draft_count": draft_count,
            "published_count": published_count,
            "recent_articles": [dict(row) for row in recent_rows],
        }

    def get_topics(self, limit: int = 50) -> list[dict]:
        rows = self._execute_read(
            "SELECT * FROM hot_topics ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]

    def get_articles(self, status: str = None) -> list[dict]:
        if status in ("draft", "published"):
            rows = self._execute_read(
                "SELECT * FROM articles WHERE status=? ORDER BY generated_at DESC",
                (status,)
            ).fetchall()
        else:
            rows = self._execute_read(
                "SELECT * FROM articles ORDER BY generated_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def get_article(self, article_id: int) -> dict | None:
        row = self._execute_read(
            "SELECT * FROM articles WHERE id=?", (article_id,)
        ).fetchone()
        return dict(row) if row else None

    def delete_article(self, article_id: int) -> bool:
        cursor = self._execute_write(
            "DELETE FROM articles WHERE id=?", (article_id,)
        )
        return cursor.rowcount > 0
