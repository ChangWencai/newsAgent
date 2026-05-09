"""定时任务调度模块"""

import difflib
import logging

from config.settings import MAX_TOPICS_PER_RUN, DEFAULT_STYLE
from src.crawler import get_registered_crawlers
from src.crawler.protocol import HotTopic
from src.writer.generator import ArticleGenerator
from src.storage.database import Database
from src.publisher.toutiao_publisher import ToutiaoPublisher
from src.validator.sensitive import check_sensitive_words

logger = logging.getLogger(__name__)


def dedup_topics(topics: list[HotTopic], threshold: float = 0.6) -> list[HotTopic]:
    """按标题相似度分组，每组保留 hot_value 最高的条目"""
    if not topics:
        return []
    groups: list[list[HotTopic]] = []
    for topic in sorted(topics, key=lambda t: int(t.hot_value or 0), reverse=True):
        matched = False
        for group in groups:
            if difflib.SequenceMatcher(None, topic.title, group[0].title).ratio() >= threshold:
                group.append(topic)
                matched = True
                break
        if not matched:
            groups.append([topic])
    return [g[0] for g in groups]


def create_pipeline(db):
    """创建多源 pipeline，从注册列表获取所有爬虫"""

    def pipeline():
        # 频率控制检查（在爬虫之前，避免不必要的 API 调用）
        check = db.can_publish(max_daily=5, min_interval_minutes=30)
        if not check["allowed"]:
            logger.info("发布跳过: %s, 下次: %s", check["reason"], check["next_available"])
            return

        crawlers = get_registered_crawlers()
        all_topics: list[HotTopic] = []

        for crawler in crawlers:
            try:
                topics = crawler.get_hot_list()
                all_topics.extend(topics)
                logger.info("获取 %s: %d 条", crawler.__class__.__name__, len(topics))
            except Exception as e:
                logger.error("爬虫失败 [%s]: %s", crawler.__class__.__name__, e)

        if not all_topics:
            logger.warning("未获取到任何热点数据")
            return

        # 组内去重
        unique_topics = dedup_topics(all_topics)
        logger.info("去重后: %d 条（原始 %d 条）", len(unique_topics), len(all_topics))

        # DB 历史去重 + 限制数量
        new_topics = []
        for topic in unique_topics:
            if not db.topic_exists(topic.title):
                new_topics.append(topic)
            if len(new_topics) >= MAX_TOPICS_PER_RUN:
                break

        if not new_topics:
            logger.info("没有新的热点需要处理")
            return

        logger.info("过滤后有 %d 条新热点待处理", len(new_topics))

        # 创建 writer
        writer = ArticleGenerator()

        # 逐条生成文章
        for topic in new_topics:
            try:
                # 存储热点
                topic_id = db.insert_topic(
                    title=topic.title,
                    url=topic.url,
                    hot_value=topic.hot_value,
                    category=topic.category,
                    source=topic.source,
                )

                # AI 生成文章
                article = writer.generate_article(
                    title=topic.title,
                    style=DEFAULT_STYLE,
                )
                if not article:
                    logger.warning("文章生成失败: %s", topic.title)
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
                logger.error("处理热点失败 [%s]: %s", topic.title, e)

        logger.info("本次流水线执行完成")

    return pipeline


def create_publisher(db: Database) -> ToutiaoPublisher:
    """创建 publisher，注入数据库依赖"""
    return ToutiaoPublisher(db=db)


def run_pipeline(db: Database):
    """兼容入口：通过注册列表获取爬虫"""
    pipeline = create_pipeline(db)
    pipeline()
