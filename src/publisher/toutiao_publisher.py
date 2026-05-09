"""头条号 Playwright 自动发布模块

参考: https://github.com/InterestWatcher-Xiaofeng/toutiao-auto-publisher
"""

import asyncio
import logging
import os
import random
import time

from playwright_stealth import Stealth

logger = logging.getLogger(__name__)

PUBLISH_URL = "https://mp.toutiao.com/profile_v4/graphic/publish"
LOGIN_URL = "https://mp.toutiao.com/auth/page/login"
COOKIE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "cookies")


class ToutiaoPublisher:
    """基于 Playwright 的头条号文章自动发布"""

    def __init__(self, db=None):
        os.makedirs(COOKIE_DIR, exist_ok=True)
        self.db = db

    async def publish(self, title, content, headless=False):
        """发布文章到头条号

        Args:
            title: 文章标题
            content: 文章正文（纯文本）
            headless: 是否无头模式（首次登录需 False）
        """
        from playwright.async_api import async_playwright

        # 初始化截图目录
        screenshot_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "screenshots")
        os.makedirs(screenshot_dir, exist_ok=True)
        self._screenshot_dir = screenshot_dir

        async with Stealth().use_async(async_playwright()) as p:
            browser = await p.chromium.launch(headless=headless)
            context = await self._create_context(browser)
            page = await context.new_page()

            try:
                # 检查登录状态
                logged_in = await self._check_login(page)
                if not logged_in:
                    logger.info("未登录，等待手动登录...")
                    success = await self._wait_login(page, context)
                    if not success:
                        return {"success": False, "message": "登录失败或超时"}

                # 发布文章
                return await self._do_publish(page, title, content)

            finally:
                await browser.close()

    async def _create_context(self, browser):
        """创建浏览器上下文，尝试加载已有 cookie"""
        cookie_file = os.path.join(COOKIE_DIR, "toutiao_state.json")
        if os.path.exists(cookie_file):
            context = await browser.new_context(storage_state=cookie_file)
            logger.info("已加载登录状态")
        else:
            context = await browser.new_context()
        return context

    async def _check_login(self, page):
        """检查是否已登录"""
        try:
            await page.goto(PUBLISH_URL, wait_until="domcontentloaded", timeout=15000)
            url = page.url
            if "login" in url or "auth" in url:
                if self.db:
                    self.db.set_cookie_status("expired")
                return False
            if self.db:
                self.db.set_cookie_status("valid")
            return True
        except Exception:
            if self.db:
                self.db.set_cookie_status("expired")
            return False

    async def _wait_login(self, page, context):
        """打开登录页，等待手动登录（最长5分钟）"""
        await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
        logger.info("请在弹出的浏览器中手动登录...")

        waited = 0
        while waited < 300:
            await asyncio.sleep(2)
            waited += 2
            url = page.url or ""
            if "login" not in url and "auth" not in url:
                logger.info("检测到已登录")
                # 保存 cookie
                cookie_file = os.path.join(COOKIE_DIR, "toutiao_state.json")
                await context.storage_state(path=cookie_file)
                logger.info("登录状态已保存")
                if self.db:
                    self.db.set_cookie_status("valid")
                return True
            if waited % 10 == 0:
                logger.info(f"等待登录中... ({waited}/300秒)")

        logger.warning("登录等待超时")
        return False

    async def _do_publish(self, page, title, content):
        """执行发布流程"""
        logger.info(f"开始发布文章: {title[:30]}...")

        # 1. 打开发布页面
        await page.goto(PUBLISH_URL, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(random.uniform(2, 3))

        # 2. 等待标题输入框（语义定位器）
        try:
            title_input = page.get_by_role("textbox").first
            await title_input.wait_for(timeout=15000)
        except Exception:
            screenshot_path = os.path.join(self._screenshot_dir, f"timeout_{int(time.time())}.png")
            await page.screenshot(path=screenshot_path)
            logger.error("选择器超时，截图已保存: %s", screenshot_path)
            raise

        # 3. 填写标题
        await title_input.fill(title)
        logger.info("标题填写完成")
        await asyncio.sleep(random.uniform(3, 5))

        # 4. 填写正文（头条 ProseMirror 编辑器，无语义属性，保留 CSS class）
        try:
            editor = page.locator(".ProseMirror")
            await editor.wait_for(timeout=15000)
            await editor.fill(content)
        except Exception:
            screenshot_path = os.path.join(self._screenshot_dir, f"timeout_{int(time.time())}.png")
            await page.screenshot(path=screenshot_path)
            logger.error("选择器超时，截图已保存: %s", screenshot_path)
            raise
        logger.info("正文填写完成")
        await asyncio.sleep(random.uniform(4, 6))

        # 5. 选择封面（尝试从素材库，失败不影响发布）
        try:
            await self._select_cover(page)
        except Exception as e:
            logger.warning(f"封面选择失败（跳过）: {e}")

        await asyncio.sleep(random.uniform(2, 3))

        # 6. 点击发布按钮（语义定位器）
        try:
            publish_btn = page.get_by_role("button", name="发布")
            await publish_btn.wait_for(timeout=10000)
            await publish_btn.scroll_into_view_if_needed()
            await asyncio.sleep(random.uniform(1, 2))
            await publish_btn.click()
            logger.info("已点击发布按钮")
            await asyncio.sleep(random.uniform(2, 4))
        except Exception:
            screenshot_path = os.path.join(self._screenshot_dir, f"timeout_{int(time.time())}.png")
            await page.screenshot(path=screenshot_path)
            logger.error("选择器超时，截图已保存: %s", screenshot_path)
            return {"success": False, "message": "未找到发布按钮"}

        # 7. 确认发布（如有弹窗）
        try:
            confirm = page.get_by_role("button", name="发布")
            await confirm.wait_for(timeout=5000)
            await confirm.click()
            logger.info("已确认发布")
        except Exception:
            pass

        await asyncio.sleep(random.uniform(3, 5))
        logger.info(f"文章发布完成: {title[:30]}")
        return {"success": True, "message": "发布成功"}

    async def _select_cover(self, page):
        """从素材库选择封面"""
        # 点击封面选择按钮
        cover_btn = await page.wait_for_selector(
            ".article-cover-images-wrap .article-cover-images > div > div > div > div",
            state="visible", timeout=5000
        )
        if cover_btn:
            await cover_btn.click(force=True)
            await asyncio.sleep(random.uniform(3, 4))

        # 点击"我的素材"
        material_tab = await page.wait_for_selector("text=我的素材", state="visible", timeout=5000)
        if material_tab:
            await material_tab.click(force=True)
            await asyncio.sleep(random.uniform(3, 4))

        # 选择第一张图片
        first_img = await page.wait_for_selector(".byte-drawer .img-span", state="visible", timeout=5000)
        if first_img:
            await first_img.click()
            await asyncio.sleep(random.uniform(2, 3))

        # 点击确定
        confirm = await page.wait_for_selector(
            "div.byte-drawer .footer button.byte-btn-primary",
            state="visible", timeout=5000
        )
        if confirm:
            await confirm.evaluate("el => el.click()")
            logger.info("封面选择完成")
            await asyncio.sleep(random.uniform(3, 4))


def publish_article(title, content):
    """同步包装，方便非异步环境调用"""
    pub = ToutiaoPublisher()
    return asyncio.run(pub.publish(title, content))
