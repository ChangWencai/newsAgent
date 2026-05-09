"""百度热搜适配器 - 通过 DailyHotApi 获取百度热搜"""

import logging

from src.crawler.protocol import HotTopic
from src.crawler.dailyhot import fetch_dailyhot
from src.crawler import register_crawler

logger = logging.getLogger(__name__)


class BaiduCrawler:
    def get_hot_list(self) -> list[HotTopic]:
        raw_items = fetch_dailyhot("baidu")
        results = []
        for item in raw_items:
            results.append(HotTopic(
                title=item.get("title", ""),
                url=item.get("url", ""),
                source="baidu",
                hot_value=str(item.get("hot", "")),
                category="百度热搜",
            ))
        return results


register_crawler(BaiduCrawler())
