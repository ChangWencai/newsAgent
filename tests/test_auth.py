"""认证与 CSRF 集成测试"""

import pytest


@pytest.fixture
def auth_app(db, monkeypatch):
    """创建启用认证的测试应用"""
    monkeypatch.setenv("ADMIN_PASSWORD", "test123")
    # 重新加载 settings 使 ADMIN_PASSWORD 生效
    import importlib
    import config.settings as settings
    importlib.reload(settings)

    from main import create_app
    app = create_app(db=db)
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    yield app
    # 恢复 settings 状态，避免影响其他测试
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    importlib.reload(settings)


@pytest.fixture
def auth_client(auth_app):
    return auth_app.test_client()


class TestAuth:
    def test_unauthenticated_redirect(self, auth_client):
        """未认证用户访问 / 被重定向到 /login"""
        r = auth_client.get("/")
        assert r.status_code == 302
        assert "/login" in r.headers["Location"]

    def test_api_no_auth_required(self, auth_client):
        """API 端点不需要认证"""
        r = auth_client.get("/health")
        assert r.status_code == 200
        assert r.get_json()["status"] == "ok"

    def test_login_success(self, auth_client):
        """正确密码登录后重定向到仪表盘"""
        r = auth_client.post("/login", data={"password": "test123"})
        assert r.status_code == 302
        assert "/" == r.headers["Location"] or "dashboard" in r.headers["Location"]

    def test_login_wrong_password(self, auth_client):
        """错误密码返回 401"""
        r = auth_client.post("/login", data={"password": "wrong"})
        assert r.status_code == 401

    def test_logout(self, auth_client):
        """登出后清除 session，再次访问需重新登录"""
        # 先登录
        auth_client.post("/login", data={"password": "test123"})
        # 登出
        r = auth_client.get("/logout")
        assert r.status_code == 302
        # 再次访问被重定向
        r = auth_client.get("/")
        assert r.status_code == 302
        assert "/login" in r.headers["Location"]

    def test_csrf_required(self, auth_app):
        """POST 表单缺少 CSRF token 返回 400"""
        auth_app.config["WTF_CSRF_ENABLED"] = True
        client = auth_app.test_client()
        r = client.post("/login", data={"password": "test123"})
        assert r.status_code == 400
