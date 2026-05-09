"""定时任务调度模块"""

import logging
from config.settings import MAX_TOPICS_PER_RUN, DEFAULT_STYLE
from src.crawler.tophub import DouyinCrawler
from src.writer.generator import ArticleGenerator
from src.storage.database import Database
from src.publisher.toutiao_publisher import ToutiaoPublisher
from src.validator.sensitive import check_sensitive_words

logger = logging.getLogger(__name__)


def create_pipeline(crawler, writer, db):
    """创建 pipeline 函数，通过构造函数注入依赖"""

    def pipeline():
        _run_pipeline_inner(crawler, writer, db)

    return pipeline


def create_publisher(db: Database) -> ToutiaoPublisher:
    """创建 publisher，注入数据库依赖"""
    return ToutiaoPublisher(db=db)


def _run_pipeline_inner(crawler, writer, db):
    """执行完整的新闻生产流水线"""
    # 频率控制检查
    check = db.can_publish(max_daily=5, min_interval_minutes=30)
    if not check["allowed"]:
        logger.info("发布跳过: %s, 下次: %s", check["reason"], check["next_available"])
        return

    logger.info("开始执行新闻生产流水线...")

    # 1. 抓取热点
    topics = crawler.get_hot_list()
    if not topics:
        logger.warning("未获取到热点数据")
        return

    logger.info("获取到 %d 条热点", len(topics))

    # 2. 去重过滤
    new_topics = []
    for topic in topics:
        if not db.topic_exists(topic["title"]):
            new_topics.append(topic)
        if len(new_topics) >= MAX_TOPICS_PER_RUN:
            break

    if not new_topics:
        logger.info("没有新的热点需要处理")
        return

    logger.info("过滤后有 %d 条新热点待处理", len(new_topics))

    # 3. 逐条生成文章
    for topic in new_topics:
        try:
            # 存储热点
            topic_id = db.insert_topic(
                title=topic["title"],
                url=topic["url"],
                hot_value=topic["hot_value"],
                category=topic["category"],
            )

            # AI 生成文章
            article = writer.generate_article(
                title=topic["title"],
                style=DEFAULT_STYLE,
            )
            if not article:
                logger.warning("文章生成失败: %s", topic["title"])
                continue

            # 存储文章
            article_id = db.insert_article(
                topic_id=topic_id,
                title=article["title"],
                content=article["content"],
                style=article["style"],
            )

            # 敏感词检查
            hits = check_sensitive_words(article["content"])
            if hits:
                db.update_article_status(article_id, status="flagged")
                logger.warning(
                    "文章含敏感词，已标记: %s, 命中: %s", article["title"], hits
                )
                continue

            logger.info("已生成文章: %s", article["title"])

        except Exception as e:
            logger.error("处理热点失败 [%s]: %s", topic["title"], e)

    logger.info("本次流水线执行完成")


def run_pipeline(db: Database):
    """兼容入口：创建默认依赖并执行"""
    crawler = DouyinCrawler()
    writer = ArticleGenerator()
    pipeline = create_pipeline(crawler, writer, db)
    pipeline()
