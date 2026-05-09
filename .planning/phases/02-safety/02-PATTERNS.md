# Phase 2: Safety - Pattern Map

**Mapped:** 2026-05-09
**Files analyzed:** 13 (9 modified + 4 new)
**Analogs found:** 9 / 9 (所有修改文件均有精确匹配)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/storage/database.py` | model | CRUD | 现有文件 | exact |
| `src/web/routes/web.py` | controller | request-response | 现有文件 | exact |
| `src/web/routes/api.py` | controller | request-response | 现有文件 | exact |
| `config/settings.py` | config | 配置加载 | 现有文件 | exact |
| `src/publisher/toutiao_publisher.py` | service | file-I/O | 现有文件 | exact |
| `src/crawler/tophub.py` | service | request-response | 现有文件 | exact |
| `src/writer/generator.py` | service | request-response | 现有文件 | exact |
| `src/scheduler/jobs.py` | pipeline | event-driven | 现有文件 | exact |
| `main.py` | factory | 启动配置 | 现有文件 | exact |
| `src/validator/sensitive.py` | utility | transform | 新模块 (DFA 模式) | no-analog |
| `data/sensitive_words.txt` | data | 静态数据 | 新文件 | no-analog |
| `tests/test_sensitive.py` | test | unit-test | `tests/test_database.py` | role-match |
| `tests/test_auth.py` | test | integration | `tests/test_routes.py` | role-match |

## Existing Patterns Reference

### Database Extension Pattern

**来源:** `/Users/wencai/github/newsAgent/src/storage/database.py`

Database 类使用单连接 + threading.Lock + WAL 模式，所有公开方法通过 `_execute_read` / `_execute_write` 封装：

**核心读写模式** (lines 23-30):
```python
def _execute_write(self, sql, params=()):
    with self._write_lock:
        cursor = self._conn.execute(sql, params)
        self._conn.commit()
        return cursor

def _execute_read(self, sql, params=()):
    return self._conn.execute(sql, params)
```

**现有方法签名模式** (lines 61-156):
- `topic_exists(title)` -> bool: 查询存在性，返回 `row is not None`
- `insert_topic(title, url, hot_value, category)` -> int: 插入并返回 `cursor.lastrowid`
- `get_dashboard_stats()` -> dict: 聚合查询返回字典
- `get_article(article_id)` -> dict | None: 单条查询，`dict(row) if row else None`
- `delete_article(article_id)` -> bool: 删除，返回 `cursor.rowcount > 0`

**扩展频率控制方法应遵循:**
- 使用 `_execute_read` 查询发布计数和时间
- 返回 dict 包含 `allowed`, `reason`, `next_available` 字段
- 不需要加锁（只读操作）

**扩展 cookie 状态方法应遵循:**
- `set_cookie_status()` 使用 `_execute_write`
- `get_cookie_status()` 使用 `_execute_read`
- 需新建 `system_kv` 表存储键值对

---

### Blueprint Factory Pattern

**来源:** `/Users/wencai/github/newsAgent/src/web/routes/web.py`

Blueprint 工厂函数通过闭包注入 db 实例：

**工厂函数签名** (line 18):
```python
def create_web_bp(db):
    """创建 Web 视图 Blueprint，通过闭包注入 db"""
    bp = Blueprint("web", __name__)
    # ... 路由定义
    return bp
```

**before_request 注册位置:** 在 `bp = Blueprint(...)` 之后、第一个 `@bp.route` 之前注册：
```python
@bp.before_request
def require_auth():
    if request.endpoint in ("web.login", "web.static", None):
        return None
    if not session.get("authenticated"):
        return redirect(url_for("web.login"))
```

**需新增路由:**
- `/login` (GET/POST): 登录页面
- `/logout` (GET): 清除 session

---

### Configuration Pattern

**来源:** `/Users/wencai/github/newsAgent/config/settings.py`

配置常量定义模式 (lines 1-28):
```python
import os
from dotenv import load_dotenv

load_dotenv()

# 环境变量带默认值
TOPHUB_API_KEY = os.getenv("TOPHUB_API_KEY", "")
RSS_HOST = os.getenv("RSS_HOST", "0.0.0.0")
RSS_PORT = int(os.getenv("RSS_PORT", "5000"))

# 固定常量
TOPHUB_BASE_URL = "https://api.tophubdata.com"
DB_PATH = os.path.join(...)
```

**新增配置项应遵循:**
- 环境变量: `ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")`
- 添加 `validate_config()` 启动验证函数
- 必填变量列表: `REQUIRED_VARS = ["MINIMAX_API_KEY", "TOPHUB_API_KEY"]`

---

### Publisher Pattern

**来源:** `/Users/wencai/github/newsAgent/src/publisher/toutiao_publisher.py`

Playwright 异步使用模式 (lines 24-52):
```python
async def publish(self, title, content, headless=False):
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await self._create_context(browser)
        page = await context.new_page()
        try:
            # ... 操作流程
        finally:
            await browser.close()
```

**选择器使用模式** (lines 107-128):
- `page.wait_for_selector("textarea", timeout=15000)` - 等待元素
- `page.fill("textarea", title)` - 填写表单
- `page.wait_for_selector("button.publish-btn-last", timeout=10000)` - 等待按钮

**playwright-stealth 集成点:**
- 替换 `async_playwright()` 为 `Stealth().use_async(async_playwright())`
- 选择器迁移优先级: `page.get_by_role()`, `page.get_by_text()`, `page.get_by_placeholder()`

---

### Pipeline Pattern

**来源:** `/Users/wencai/github/newsAgent/src/scheduler/jobs.py`

Pipeline 编排模式 (lines 12-79):
```python
def create_pipeline(crawler, writer, db):
    """创建 pipeline 函数，通过构造函数注入依赖"""
    def pipeline():
        _run_pipeline_inner(crawler, writer, db)
    return pipeline

def _run_pipeline_inner(crawler, writer, db):
    """执行完整的新闻生产流水线"""
    # 1. 抓取热点
    topics = crawler.get_hot_list()
    # 2. 去重过滤
    # 3. 逐条生成文章
    for topic in new_topics:
        # 存储热点 -> AI 生成文章 -> 存储文章
```

**频率控制插入点:** 在 `_run_pipeline_inner()` 开头、抓取热点之前:
```python
check = db.can_publish(max_daily=5, min_interval_minutes=30)
if not check["allowed"]:
    logger.info("发布跳过: %s", check["reason"])
    return
```

**敏感词过滤插入点:** 在文章生成后、存储之前:
```python
hits = check_sensitive_words(article["content"])
if hits:
    db.flag_article(article_id, reason=f"敏感词: {', '.join(hits)}")
    continue
```

---

### Test Pattern

**来源:** `/Users/wencai/github/newsAgent/tests/conftest.py` 和 `tests/test_database.py`

**Fixture 定义模式** (conftest.py lines 6-25):
```python
@pytest.fixture
def db():
    """每个测试函数获得独立的内存数据库"""
    database = Database(':memory:')
    yield database
    database._conn.close()

@pytest.fixture
def app(db):
    from main import create_app
    app = create_app(db=db)
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    return app.test_client()
```

**测试类组织模式** (test_database.py):
```python
class TestDatabaseInit:
    """验证单连接、WAL 模式、写锁"""
    def test_single_connection(self, db: Database):
        # ...

class TestDashboardStats:
    """验证 get_dashboard_stats 方法"""
    def test_empty_dashboard(self, db: Database):
        # ...
```

**新测试文件命名:** `tests/test_sensitive.py`, `tests/test_auth.py`

---

## New Files to Create

| File | Based On Pattern | Notes |
|------|-----------------|-------|
| `src/validator/sensitive.py` | DFA 算法 (RESEARCH.md Pattern 5) | 敏感词过滤模块，热重载支持 |
| `data/sensitive_words.txt` | 静态数据文件 | 每行一个敏感词，UTF-8 编码 |
| `tests/test_sensitive.py` | `tests/test_database.py` | 测试类组织模式 |
| `tests/test_auth.py` | `tests/test_routes.py` | 路由集成测试模式 |
| `.env.example` | 已存在，需更新 | 添加 ADMIN_PASSWORD, SECRET_KEY |

---

## Files to Modify

| File | Change Type | Pattern |
|------|------------|---------|
| `src/storage/database.py` | 扩展方法 | 现有 `_execute_write`/`_execute_read` 模式 |
| `src/web/routes/web.py` | 添加 before_request + 登录路由 | Blueprint 工厂模式 |
| `src/web/routes/api.py` | 扩展 /health | 现有路由模式 |
| `config/settings.py` | 添加常量+验证 | 现有 `os.getenv` 模式 |
| `src/publisher/toutiao_publisher.py` | playwright-stealth + 语义选择器 | Playwright 异步模式 |
| `src/crawler/tophub.py` | 添加 @retry | tenacity 装饰器 |
| `src/writer/generator.py` | 添加 @retry | tenacity 装饰器 |
| `src/scheduler/jobs.py` | 添加频率检查+敏感词过滤 | 现有 pipeline 模式 |
| `main.py` | 添加 CSRF + secret_key | Application Factory 模式 |

---

## Shared Patterns

### Error Handling
**来源:** 多个文件的 try/except 模式
**应用到:** 所有新增和修改的文件

```python
# api.py 错误处理模式 (lines 18-25)
try:
    run_pipeline(db)
    return jsonify({"success": True, "message": "流水线执行成功"})
except Exception as e:
    logger.exception("流水线执行失败")
    return jsonify({"success": False, "message": f"执行失败: {e}"}), 500
```

### Logging
**来源:** 所有模块统一使用 `logging.getLogger(__name__)`
**应用到:** 所有新增模块

```python
import logging
logger = logging.getLogger(__name__)
```

### Retry Decorator (tenacity)
**来源:** RESEARCH.md Pattern 6
**应用到:** `src/crawler/tophub.py`, `src/writer/generator.py`

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log

crawl_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((requests.RequestException,)),
    reraise=True,
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
```

### Flask Session Authentication
**来源:** RESEARCH.md Pattern 4
**应用到:** `src/web/routes/web.py`

```python
@bp.before_request
def require_auth():
    if request.endpoint in ("web.login", "web.static", None):
        return None
    if not session.get("authenticated"):
        return redirect(url_for("web.login"))
```

### CSRF Protection
**来源:** RESEARCH.md Pattern 4
**应用到:** `main.py`

```python
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect()

def create_app(db=None, db_path=None):
    app = Flask(__name__, ...)
    app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
    csrf.init_app(app)
    csrf.exempt(app.blueprints["api"])  # API 端点豁免
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/validator/sensitive.py` | utility | transform | 项目无 DFA 过滤器，参考 RESEARCH.md Pattern 5 |
| `data/sensitive_words.txt` | data | 静态数据 | 新数据文件，需手动维护初始词库 |

---

## Metadata

**Analog search scope:** `/Users/wencai/github/newsAgent/src/`, `/Users/wencai/github/newsAgent/config/`, `/Users/wencai/github/newsAgent/tests/`
**Files scanned:** 18 个 Python 源文件
**Pattern extraction date:** 2026-05-09
