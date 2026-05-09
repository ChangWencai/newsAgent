"""头条文章发布工具

用法:
  python publish.py              # 发布所有待发布文章
  python publish.py --id 1       # 发布指定文章
  python publish.py --login      # 仅登录保存Cookie
"""

import argparse
import asyncio
import logging
import sys

from config.settings import DB_PATH
from src.storage.database import Database
from src.publisher.toutiao_publisher import ToutiaoPublisher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def login_only():
    """仅登录保存Cookie"""
    pub = ToutiaoPublisher()
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(pub.LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
        logger.info("请在浏览器中手动登录...")

        waited = 0
        while waited < 300:
            await asyncio.sleep(2)
            waited += 2
            url = page.url or ""
            if "login" not in url and "auth" not in url:
                import os
                cookie_file = os.path.join(pub.COOKIE_DIR, "toutiao_state.json")
                await context.storage_state(path=cookie_file)
                logger.info("登录状态已保存!")
                await browser.close()
                return True
            if waited % 10 == 0:
                logger.info(f"等待登录中... ({waited}/300秒)")

        logger.warning("登录超时")
        await browser.close()
        return False


async def publish_articles(article_ids=None):
    """发布文章"""
    db = Database(DB_PATH)
    pub = ToutiaoPublisher()

    if article_ids:
        articles = []
        for aid in article_ids:
            article = db.get_article(aid)
            if article:
                articles.append(article)
    else:
        articles = db.get_unpublished_articles()

    if not articles:
        logger.info("没有待发布的文章")
        return

    logger.info(f"共 {len(articles)} 篇文章待发布")

    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await pub._create_context(browser)
        page = await context.new_page()

        # 检查登录
        logged_in = await pub._check_login(page)
        if not logged_in:
            success = await pub._wait_login(page, context)
            if not success:
                logger.error("登录失败")
                await browser.close()
                return

        # 逐篇发布
        for article in articles:
            logger.info(f"发布 [{article['id']}]: {article['title']}")
            result = await pub._do_publish(page, article["title"], article["content"])
            if result["success"]:
                db.mark_published(article["id"])
                logger.info(f"发布成功: {article['title']}")
            else:
                logger.error(f"发布失败: {result['message']}")

        await browser.close()


def main():
    parser = argparse.ArgumentParser(description="头条文章发布工具")
    parser.add_argument("--login", action="store_true", help="仅登录保存Cookie")
    parser.add_argument("--id", type=int, nargs="+", help="指定文章ID发布")
    args = parser.parse_args()

    if args.login:
        asyncio.run(login_only())
    else:
        asyncio.run(publish_articles(args.id))


if __name__ == "__main__":
    main()
