"""知乎热榜适配器 - 通过 DailyHotApi 获取知乎热榜"""

import logging

from src.crawler.protocol import HotTopic
from src.crawler.dailyhot import fetch_dailyhot
from src.crawler import register_crawler

logger = logging.getLogger(__name__)


class ZhihuCrawler:
    def get_hot_list(self) -> list[HotTopic]:
        raw_items = fetch_dailyhot("zhihu")
        results = []
        for item in raw_items:
            results.append(HotTopic(
                title=item.get("title", ""),
                url=item.get("url", ""),
                source="zhihu",
                hot_value=str(item.get("hot", "")),
                category="知乎热榜",
            ))
        return results


register_crawler(ZhihuCrawler())
