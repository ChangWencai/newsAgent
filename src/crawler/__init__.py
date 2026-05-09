"""爬虫注册中心"""

from src.crawler.protocol import CrawlerProtocol

CRAWLERS: list[CrawlerProtocol] = []


def register_crawler(crawler: CrawlerProtocol) -> None:
    CRAWLERS.append(crawler)


def get_registered_crawlers() -> list[CrawlerProtocol]:
    return list(CRAWLERS)
