"""爬虫数据模型"""

from dataclasses import dataclass


@dataclass(frozen=True)
class HotTopic:
    title: str
    url: str
    source: str
    hot_value: str = ""
    category: str = ""
    fetched_at: str = ""
