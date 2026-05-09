"""MiniMax-M2.7 文章生成模块（Token Plan / Anthropic SDK）"""

import logging

import anthropic
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log

from config.settings import MINIMAX_API_KEY
from src.writer.styles import STYLES, detect_style

logger = logging.getLogger(__name__)

api_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((
        requests.RequestException,
        anthropic.APIConnectionError,
        anthropic.RateLimitError,
    )),
    reraise=True,
    before_sleep=before_sleep_log(logger, logging.WARNING),
)

MINIMAX_BASE_URL = "https://api.minimaxi.com/anthropic"
MINIMAX_MODEL = "MiniMax-M2.7"


class ArticleGenerator:
    def __init__(self, api_key=None):
        self.api_key = api_key or MINIMAX_API_KEY
        self.client = anthropic.Anthropic(
            base_url=MINIMAX_BASE_URL,
            api_key=self.api_key,
        )

    @api_retry
    def generate_article(self, title, style="auto", context=None):
        """生成文章

        API 异常由 tenacity 重试装饰器处理（APIConnectionError、RateLimitError），
        最多重试 3 次，指数退避后仍失败则抛出原始异常。

        Args:
            title: 热点话题标题
            style: 文章风格 (news/comment/entertainment/auto)
            context: 可选的补充背景信息

        Returns:
            dict: {title, content, summary, style}
        """
        if style == "auto":
            style = detect_style(title)

        style_config = STYLES.get(style, STYLES["news"])

        user_prompt = f"热点话题：{title}"
        if context:
            user_prompt += f"\n\n背景信息：{context}"

        message = self.client.messages.create(
            model=MINIMAX_MODEL,
            max_tokens=2000,
            system=style_config["system"],
            messages=[
                {"role": "user", "content": [{"type": "text", "text": user_prompt}]}
            ],
        )

        content = ""
        for block in message.content:
            if block.type == "text":
                content += block.text

        return self._parse_response(content, style)

    def _parse_response(self, content, style):
        """解析模型输出，提取标题、正文、摘要"""
        lines = content.strip().split("\n")
        article_title = ""
        article_content = ""
        article_summary = ""

        section = None
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("标题："):
                section = "title"
                article_title = stripped[3:].strip()
            elif stripped.startswith("正文："):
                section = "content"
                article_content = stripped[3:].strip()
            elif stripped.startswith("摘要："):
                section = "summary"
                article_summary = stripped[3:].strip()
            elif section == "content":
                article_content += "\n" + line
            elif section == "summary":
                article_summary += "\n" + line
            elif section == "title":
                article_title += stripped

        # 兜底：如果解析失败，用第一行作标题，其余作正文
        if not article_title and not article_content:
            text = content.strip()
            if text:
                parts = text.split("\n", 1)
                article_title = parts[0].strip("# ").strip()[:50]
                article_content = parts[1].strip() if len(parts) > 1 else text
                article_summary = article_content[:100]

        return {
            "title": article_title.strip(),
            "content": article_content.strip(),
            "summary": article_summary.strip(),
            "style": style,
        }
