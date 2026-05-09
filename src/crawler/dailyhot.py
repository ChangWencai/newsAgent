"""DailyHotApi 通用请求模块"""

import logging
from typing import Any

import requests

from config.settings import DAILYHOT_BASE_URL

logger = logging.getLogger(__name__)


def fetch_dailyhot(platform: str) -> list[dict[str, Any]]:
    """从 DailyHotApi 获取指定平台热榜，返回原始 data 列表"""
    url = f"{DAILYHOT_BASE_URL}/{platform}"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 200:
        raise ValueError(f"DailyHotApi 返回异常: platform={platform}, code={data.get('code')}")
    return data.get("data", [])
