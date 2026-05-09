"""抖音热榜抓取模块（直接抓取）"""

import requests
import logging

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception, before_sleep_log

logger = logging.getLogger(__name__)


def _is_retryable(exc: BaseException) -> bool:
    """判断异常是否应触发重试。

    网络异常（ConnectionError、Timeout 等）始终重试；
    HTTP 错误仅 429 和 5xx 重试，其他 4xx 不重试。
    """
    if isinstance(exc, requests.ConnectionError | requests.Timeout):
        return True
    if isinstance(exc, requests.HTTPError):
        resp = exc.response
        if resp is not None:
            return resp.status_code == 429 or resp.status_code >= 500
    return False


crawl_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception(_is_retryable),
    reraise=True,
    before_sleep=before_sleep_log(logger, logging.WARNING),
)

DOUYIN_HOT_URL = "https://www.douyin.com/aweme/v1/web/hot/search/list/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.douyin.com/",
}


class DouyinCrawler:
    @crawl_retry
    def get_hot_list(self):
        """获取抖音热搜榜

        网络异常（RequestException）由 tenacity 重试装饰器处理，
        最多重试 3 次，指数退避后仍失败则抛出原始异常。
        """
        resp = requests.get(DOUYIN_HOT_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        word_list = data.get("data", {}).get("word_list", [])
        results = []
        for item in word_list:
            results.append({
                "title": item.get("word", ""),
                "url": f"https://www.douyin.com/search/{item.get('word', '')}",
                "hot_value": str(item.get("hot_value", 0)),
                "category": "抖音热搜",
            })
        return results
