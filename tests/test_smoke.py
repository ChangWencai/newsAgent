"""测试基础设施冒烟测试"""


def test_db_fixture_works(db):
    """验证 db fixture 能创建 Database 实例且表结构正确"""
    conn = db._get_conn()
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    table_names = [t[0] for t in tables]
    conn.close()
    assert 'hot_topics' in table_names
    assert 'articles' in table_names


def test_db_insert_and_query(db):
    """验证 Database 基本 CRUD 操作"""
    topic_id = db.insert_topic(
        "测试热点", "http://example.com", "100", "科技"
    )
    assert topic_id is not None
    assert topic_id > 0
    assert db.topic_exists("测试热点") is True
    assert db.topic_exists("不存在的热点") is False


def test_db_article_crud(db):
    """验证文章创建和查询"""
    topic_id = db.insert_topic("文章测试热点", "http://example.com", "200", "社会")
    article_id = db.insert_article(topic_id, "测试文章标题", "测试文章内容", "news")
    assert article_id is not None
    articles = db.get_recent_articles(limit=5)
    assert len(articles) == 1
    assert articles[0]["title"] == "测试文章标题"
    assert articles[0]["status"] == "draft"
