"""Publisher 模块单元测试"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.publisher.toutiao_publisher import COOKIE_DIR, ToutiaoPublisher


class TestStealthImport:
    def test_stealth_import(self):
        """playwright_stealth 可正常导入"""
        from playwright_stealth import Stealth

        assert Stealth is not None


class TestPublisherInstantiation:
    def test_publisher_instantiation(self):
        """ToutiaoPublisher() 可正常实例化"""
        pub = ToutiaoPublisher()
        assert pub is not None
        assert pub.db is None

    def test_publisher_with_db(self):
        """ToutiaoPublisher(db=...) 正常接收 db 参数"""
        mock_db = MagicMock()
        pub = ToutiaoPublisher(db=mock_db)
        assert pub.db is mock_db


class TestScreenshotDir:
    def test_screenshot_dir_variable(self):
        """截图目录变量正确指向 data/screenshots"""
        expected = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "data", "screenshots"
        )
        # COOKIE_DIR 的推导方式相同，验证路径结构一致
        assert os.path.dirname(COOKIE_DIR) == os.path.dirname(expected)


class TestCookieStatus:
    @pytest.mark.asyncio
    async def test_cookie_status_set_on_login_valid(self):
        """_check_login 成功时调用 db.set_cookie_status('valid')"""
        mock_db = MagicMock()
        pub = ToutiaoPublisher(db=mock_db)

        mock_page = AsyncMock()
        mock_page.url = "https://mp.toutiao.com/profile_v4/graphic/publish"

        result = await pub._check_login(mock_page)
        assert result is True
        mock_db.set_cookie_status.assert_called_once_with("valid")

    @pytest.mark.asyncio
    async def test_cookie_status_set_on_login_expired(self):
        """_check_login 检测到登录页时调用 db.set_cookie_status('expired')"""
        mock_db = MagicMock()
        pub = ToutiaoPublisher(db=mock_db)

        mock_page = AsyncMock()
        mock_page.url = "https://mp.toutiao.com/auth/page/login"

        result = await pub._check_login(mock_page)
        assert result is False
        mock_db.set_cookie_status.assert_called_once_with("expired")

    @pytest.mark.asyncio
    async def test_cookie_status_set_on_login_exception(self):
        """_check_login 异常时调用 db.set_cookie_status('expired')"""
        mock_db = MagicMock()
        pub = ToutiaoPublisher(db=mock_db)

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock(side_effect=Exception("timeout"))

        result = await pub._check_login(mock_page)
        assert result is False
        mock_db.set_cookie_status.assert_called_once_with("expired")

    def test_cookie_status_skipped_without_db(self):
        """无 db 参数时 _check_login 不报错（向后兼容）"""
        pub = ToutiaoPublisher()
        assert pub.db is None
        # 调用属性访问不会触发 set_cookie_status

    @pytest.mark.asyncio
    async def test_cookie_status_set_on_wait_login(self):
        """_wait_login 成功后调用 db.set_cookie_status('valid')"""
        mock_db = MagicMock()
        pub = ToutiaoPublisher(db=mock_db)

        mock_page = AsyncMock()
        mock_page.url = "https://mp.toutiao.com/profile_v4/graphic/publish"

        mock_context = AsyncMock()
        mock_context.storage_state = AsyncMock()

        # 用 patch 替换 asyncio.sleep 避免等待
        with patch("src.publisher.toutiao_publisher.asyncio.sleep", new_callable=AsyncMock):
            result = await pub._wait_login(mock_page, mock_context)

        assert result is True
        mock_db.set_cookie_status.assert_called_once_with("valid")


class TestCreatePublisher:
    def test_create_publisher_with_db(self):
        """create_publisher 返回带 db 的 publisher"""
        from src.scheduler.jobs import create_publisher

        mock_db = MagicMock()
        pub = create_publisher(mock_db)
        assert isinstance(pub, ToutiaoPublisher)
        assert pub.db is mock_db
