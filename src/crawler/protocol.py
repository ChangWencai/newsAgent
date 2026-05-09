"""爬虫协议定义"""

from typing import Protocol

from src.crawler.models import HotTopic


class CrawlerProtocol(Protocol):
    def get_hot_list(self) -> list[HotTopic]: ...
