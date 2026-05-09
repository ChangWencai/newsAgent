# Phase 1: Foundation - Research

**Researched:** 2026-05-09
**Domain:** Flask Application Factory + SQLite 并发 + pytest 测试基础设施 + gunicorn 部署
**Confidence:** HIGH

## Summary

当前项目存在 5 个核心架构缺陷：(1) `routes.py` 使用模块级 `_db` 全局变量，(2) 路由层绕过 `Database` 类直接执行原始 SQL，(3) `Database` 类每次操作新建/关闭连接且无写锁序列化，(4) 零测试覆盖，(5) 使用 Werkzeug 开发服务器作为生产部署。

Phase 1 的目标是将这些反模式替换为行业标准实践：Flask Application Factory + Blueprint 依赖注入 + Database 类完整封装（单连接 + `threading.Lock` + WAL 模式）+ pytest 测试基础设施 + gunicorn 生产部署。所有决策已在 CONTEXT.md 中锁定，本研究提供实施细节。

**主要建议：** 按 5 个 Wave 顺序实施，每个 Wave 可独立验证，回滚半径小。

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FOUND-01 | Flask Application Factory 模式，消除模块级 `_db` 变量 | Flask 官方 Factory 文档 + Blueprint 工厂注入模式 |
| FOUND-02 | Database 类补齐所有数据访问方法，路由层零 SQL | 当前 routes.py 有 5 处直接 SQL，需新增 ~6 个方法 |
| FOUND-03 | Flask Blueprint 路由组织，按功能域拆分 | Flask 官方 Blueprint 文档，2 个 Blueprint（web + api） |
| FOUND-04 | SQLite WAL 模式 + threading.Lock 写锁序列化 | SQLite WAL 官方文档 + Python threading.Lock 模式 |
| FOUND-05 | pyproject.toml + conftest.py 测试基础设施 | pytest fixtures 文档 + :memory: SQLite fixture 模式 |
| FOUND-06 | gunicorn 替换 Werkzeug 开发服务器 | gunicorn 23.0.0（已安装）+ gthread worker 配置 |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Flask | >=3.0.0 | Web 框架 | 项目已有依赖，Application Factory 是官方推荐模式 [VERIFIED: requirements.txt] |
| gunicorn | 23.0.0 | WSGI 生产服务器 | 已安装，支持 gthread 多线程 [VERIFIED: pip3 show] |
| pytest | latest | 测试框架 | Python 生态标准，fixture 系统支持数据库隔离 [VERIFIED: pytest docs] |
| sqlite3 (stdlib) | 3.x | 数据库 | 项目已有，WAL 模式满足单用户并发需求 [VERIFIED: SQLite WAL docs] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-cov | latest | 测试覆盖率 | 所有测试运行时生成覆盖率报告 |
| APScheduler | >=3.10.0 | 定时任务 | 项目已有，需适配 Factory 模式 [VERIFIED: requirements.txt] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| threading.Lock + WAL | SQLAlchemy + 连接池 | 增加复杂度，单用户场景收益不大 |
| gunicorn gthread | uvicorn + uvloop | 仅支持 ASGI，Flask 是 WSGI 框架 |
| pytest | unittest | pytest fixture 系统更适合数据库测试 |

**安装：**
```bash
pip install pytest pytest-cov
```

## Architecture Patterns

### System Architecture Diagram (重构后)

```text
                          gunicorn (单 worker, 4 线程)
                                |
                          +-----v-----+
                          | main.py   |
                          |create_app |
                          +--v-----v--+
                   +---------+     +---------+
            +------v------+        +-------v-------+
            |  web_bp     |        |   api_bp      |
            | (Blueprint) |        |  (Blueprint)  |
            | dashboard   |        | /api/*        |
            | /topics     |        | /rss          |
            | /articles   |        | /health       |
            | /article/*  |        | /api/run-     |
            | /settings   |        |   pipeline    |
            +------+------v        +-------v-------+
                   |                       |
                   +----------v------------+
                              |
                       +------v------+
                       |  Database   |
                       | (单连接     |
                       |  + Lock     |
                       |  + WAL)     |
                       +------v------+
                              |
                   +----------v----------+
                   |          |          |
             +-----v----+ +--v---+ +----v-----+
             | Scheduler| |Writer| |Crawler   |
             | (APsched)| |      | |          |
             +----------+ +------+ +----------+
```

### Recommended Project Structure (Phase 1 改动)

```
newsAgent/
|-- main.py                         # Application Factory: create_app()
|-- gunicorn.conf.py                # NEW: gunicorn 配置
|-- pyproject.toml                  # NEW: 项目元数据 + pytest 配置
|-- requirements.txt                # UPDATE: 添加 pytest, pytest-cov, gunicorn
|-- src/
|   |-- web/
|   |   |-- routes/
|   |   |   |-- __init__.py         # NEW: 导出 create_web_bp, create_api_bp
|   |   |   |-- web.py              # NEW: 视图路由（dashboard/topics/articles/settings）
|   |   |   +-- api.py              # NEW: API 路由（run-pipeline/delete/rss/health）
|   |   |-- routes.py               # 保留旧文件，迁移完成后删除
|   |   |-- templates/              # 不变
|   |   +-- static/                 # 不变
|   |-- storage/
|   |   +-- database.py             # 重构：单连接 + Lock + WAL + 新增方法
|   |-- scheduler/
|   |   +-- jobs.py                 # 重构：构造函数注入
|   |-- writer/                     # 不变
|   |-- crawler/                    # 不变
|   +-- publisher/
|       +-- rss_feed.py             # 重构：合并入 api_bp
|-- tests/                          # NEW: 测试目录
|   |-- conftest.py                 # 共享 fixtures（db, app, client）
|   |-- test_database.py            # Database 单元测试
|   |-- test_routes.py              # 路由集成测试
|   +-- test_pipeline.py            # Pipeline 编排测试
+-- config/
    +-- settings.py                 # 不变
```

### Pattern 1: Application Factory + Blueprint 依赖注入

**What:** `create_app()` 工厂函数创建 Flask 实例，Blueprint 工厂函数通过闭包捕获 `db` 参数。
**When to use:** 需要测试时注入 mock 数据库；需要多个 app 实例（测试/生产）。
**Example:**
```python
# Source: Flask 官方文档 - https://flask.palletsprojects.com/en/stable/patterns/appfactories/
# src/web/routes/__init__.py
from flask import Blueprint

def create_web_bp(db):
    """Blueprint 工厂函数，通过闭包注入 db 依赖"""
    bp = Blueprint('web', __name__)

    @bp.route('/')
    def dashboard():
        stats = db.get_dashboard_stats()  # 调用 Database 方法，不执行 SQL
        return render_template('index.html', **stats)

    @bp.route('/topics')
    def topics_list():
        topics = db.get_topics(limit=50)
        return render_template('topics.html', topics=topics)

    return bp
```

```python
# main.py - Application Factory
def create_app(db_path=None):
    app = Flask(__name__, template_folder='src/web/templates',
                static_folder='src/web/static')

    db_path = db_path or DB_PATH
    db = Database(db_path)

    from src.web.routes import create_web_bp, create_api_bp
    app.register_blueprint(create_web_bp(db))
    app.register_blueprint(create_api_bp(db))

    return app

# gunicorn 导入: gunicorn main:create_app
```

### Pattern 2: Database 单连接 + threading.Lock + WAL

**What:** Database 实例持有单一 SQLite 连接（`check_same_thread=False`），所有写操作通过 `threading.Lock` 序列化，读操作在 WAL 模式下无需加锁。
**When to use:** Flask 多线程场景 + APScheduler 后台线程共享数据库。
**Example:**
```python
# Source: SQLite WAL 官方文档 - https://www.sqlite.org/wal.html
import sqlite3
import threading

class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        # 单连接，允许跨线程访问
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        # 启用 WAL 模式
        self._conn.execute("PRAGMA journal_mode=WAL")
        # 写操作锁
        self._write_lock = threading.Lock()
        self._init_tables()

    def _execute_write(self, sql, params=()):
        """所有写操作通过此方法，自动加锁"""
        with self._write_lock:
            cursor = self._conn.execute(sql, params)
            self._conn.commit()
            return cursor

    def _execute_read(self, sql, params=()):
        """读操作无需加锁（WAL 模式下并发读安全）"""
        return self._conn.execute(sql, params).fetchall()
```

**关键区别：** 读操作不加锁，写操作加 `threading.Lock`。WAL 模式保证 readers 不阻塞 writer，writer 不阻塞 readers [VERIFIED: SQLite WAL docs]。

### Pattern 3: pytest + :memory: SQLite Fixture

**What:** `conftest.py` 提供 `db` fixture，使用 `:memory:` SQLite 创建隔离的测试数据库，每个测试函数独立实例。
**When to use:** 测试 Database 类方法和路由行为。
**Example:**
```python
# Source: pytest fixtures 文档 - https://docs.pytest.org/en/stable/how-to/fixtures.html
# tests/conftest.py
import pytest
from src.storage.database import Database

@pytest.fixture
def db():
    """每个测试函数获得独立的内存数据库"""
    database = Database(':memory:')
    yield database
    database._conn.close()

@pytest.fixture
def app(db):
    """Flask 测试 app，注入内存数据库"""
    from main import create_app
    app = Flask(__name__, template_folder='src/web/templates')
    from src.web.routes import create_web_bp, create_api_bp
    app.register_blueprint(create_web_bp(db))
    app.register_blueprint(create_api_bp(db))
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    """Flask 测试客户端"""
    return app.test_client()
```

### Anti-Patterns to Avoid

- **Blueprint 中直接访问 `current_app` 获取 db：** 增加了间接性和测试复杂度。优先使用闭包注入（`create_web_bp(db)`），db 直接在路由函数作用域内可用。
- **为测试创建独立的 Database 子类：** 不要创建 `TestDatabase` 子类。直接使用 `:memory:` 路径构造真实 `Database` 实例即可。
- **在 conftest.py 中使用 session-scoped db fixture：** 测试之间会互相污染。使用 function-scoped fixture 保证隔离。
- **连接关闭后不清理资源：** `_conn.close()` 在 fixture teardown 中执行（`yield` 后的代码）。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Web 服务器 | Flask dev server | gunicorn | dev server 单线程、无信号处理、不适合生产 [VERIFIED: Flask docs] |
| 测试数据库 | 文件 SQLite + 手动清理 | :memory: SQLite fixture | 零 I/O、自动隔离、无文件残留 [VERIFIED: pytest docs] |
| 并发写入序列化 | 自定义队列/信号量 | threading.Lock | Python 标库内置，语义清晰 [VERIFIED: Python docs] |
| SQLite 并发 | 连接池 | 单连接 + Lock + WAL | SQLite 单写者限制下连接池无实际收益 [VERIFIED: SQLite docs] |

**关键洞察：** SQLite 的单写者限制意味着即使使用连接池，写操作也必须串行化。单连接 + Lock 是最简方案，WAL 模式保证读不阻塞。

## Common Pitfalls

### Pitfall 1: Application Factory 中循环导入

**What goes wrong:** Blueprint 模块在导入时引用 `create_app()` 返回的 `app` 对象，导致循环依赖。
**Why it happens:** 旧代码在模块顶层使用 `app` 对象注册路由。
**How to avoid:** 使用 Blueprint 工厂函数模式。Blueprint 模块导出工厂函数，不直接引用 `app`。`app` 只在 `create_app()` 内部创建。
**Warning signs:** `ImportError: cannot import name 'app' from 'main'`。

### Pitfall 2: Database 连接未在测试间隔离

**What goes wrong:** 使用 `tmp_path` 创建文件数据库，测试间未清理导致状态泄漏。
**Why it happens:** 文件数据库在测试间保留数据。
**How to avoid:** 使用 `:memory:` 数据库，每个测试函数独立的 fixture 实例。`Database(':memory:')` 在进程内完全隔离。
**Warning signs:** 测试在单独运行时通过，但批量运行时失败。

### Pitfall 3: WAL 模式下仍需锁写操作

**What goes wrong:** 认为 WAL 模式消除了所有锁需求，导致并发写入 `SQLITE_BUSY` 错误。
**Why it happens:** WAL 允许 reader-writer 并发，但不允许 writer-writer 并发。
**How to avoid:** 所有写操作（INSERT, UPDATE, DELETE）必须通过 `threading.Lock` 序列化。读操作（SELECT）无需加锁。
**Warning signs:** 偶发的 `database is locked` 错误。

### Pitfall 4: gunicorn 多 worker 导致 APScheduler 重复执行

**What goes wrong:** 使用 `gunicorn -w 4` 启动 4 个 worker，每个 worker 各自启动 APScheduler，pipeline 每 6 小时执行 4 次。
**Why it happens:** APScheduler `BackgroundScheduler` 在每个 worker 进程中独立运行。
**How to avoid:** 必须使用 `-w 1` 单 worker 配置。多线程（`--threads 4`）可以提升 Web 并发而不影响 scheduler。
**Warning signs:** 日志中 pipeline 执行次数异常，数据库中出现重复记录。

### Pitfall 5: 迁移期间路由 URL 不一致

**What goes wrong:** 将路由拆分为 Blueprint 后，未注册 `url_prefix` 或 endpoint 名称变化导致 `url_for()` 失败。
**Why it happens:** Blueprint endpoint 自动前缀 Blueprint 名称（如 `web.dashboard` 而非 `dashboard`）。
**How to avoid:** 模板中的 `url_for()` 调用需要更新为 Blueprint 前缀格式，或在 Blueprint 注册时使用空 `url_prefix`。
**Warning signs:** 模板渲染时 `BuildError: Could not build url for endpoint 'dashboard'`。

## Code Examples

### 重构前 vs 重构后：Database 类

```python
# Source: 当前 src/storage/database.py
# 重构前：每次操作新建连接
def topic_exists(self, title):
    conn = self._get_conn()        # 新建连接
    row = conn.execute(...)
    conn.close()                   # 关闭连接
    return row is not None

# 重构后：单连接 + Lock + WAL
class Database:
    def __init__(self, db_path):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._write_lock = threading.Lock()
        self._init_tables()

    def topic_exists(self, title):
        # 读操作：无需加锁
        row = self._conn.execute(
            "SELECT 1 FROM hot_topics WHERE title = ?", (title,)
        ).fetchone()
        return row is not None

    def insert_topic(self, title, url="", hot_value="", category=""):
        # 写操作：加锁
        with self._write_lock:
            now = datetime.now().isoformat()
            cursor = self._conn.execute(
                "INSERT INTO hot_topics (title, url, hot_value, category, fetched_at) VALUES (?, ?, ?, ?, ?)",
                (title, url, hot_value, category, now)
            )
            self._conn.commit()
            return cursor.lastrowid
```

### 重构前 vs 重构后：路由注册

```python
# Source: 当前 main.py + routes.py
# 重构前：模块级全局 + init_web()
from src.web.routes import init_web
db = Database(DB_PATH)
init_web(app, db)  # 设置全局 _db 变量

# 重构后：Application Factory + Blueprint 工厂
def create_app(db_path=None):
    app = Flask(__name__, template_folder='src/web/templates',
                static_folder='src/web/static')
    db = Database(db_path or DB_PATH)

    from src.web.routes import create_web_bp, create_api_bp
    app.register_blueprint(create_web_bp(db))
    app.register_blueprint(create_api_bp(db))

    return app
```

### 新增 Database 方法（routes.py 当前直接 SQL 需要的）

```python
# 以下方法需要添加到 Database 类中

def get_dashboard_stats(self):
    """仪表盘统计数据"""
    topic_count = self._conn.execute("SELECT COUNT(*) FROM hot_topics").fetchone()[0]
    article_count = self._conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    draft_count = self._conn.execute("SELECT COUNT(*) FROM articles WHERE status='draft'").fetchone()[0]
    published_count = self._conn.execute("SELECT COUNT(*) FROM articles WHERE status='published'").fetchone()[0]
    recent_rows = self._conn.execute(
        "SELECT * FROM articles ORDER BY generated_at DESC LIMIT 10"
    ).fetchall()
    return {
        "topic_count": topic_count,
        "article_count": article_count,
        "draft_count": draft_count,
        "published_count": published_count,
        "recent_articles": [dict(r) for r in recent_rows],
    }

def get_topics(self, limit=50):
    """获取热点列表"""
    rows = self._conn.execute(
        "SELECT * FROM hot_topics ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]

def get_articles(self, status=None):
    """获取文章列表，可按状态筛选"""
    if status in ("draft", "published"):
        rows = self._conn.execute(
            "SELECT * FROM articles WHERE status=? ORDER BY generated_at DESC",
            (status,)
        ).fetchall()
    else:
        rows = self._conn.execute(
            "SELECT * FROM articles ORDER BY generated_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]

def get_article(self, article_id):
    """获取单篇文章"""
    row = self._conn.execute(
        "SELECT * FROM articles WHERE id=?", (article_id,)
    ).fetchone()
    return dict(row) if row else None

def delete_article(self, article_id):
    """删除文章"""
    with self._write_lock:
        cursor = self._conn.execute("DELETE FROM articles WHERE id=?", (article_id,))
        self._conn.commit()
        return cursor.rowcount > 0
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 模块级全局 `_db` 变量 | Blueprint 闭包注入 `create_bp(db)` | Flask 0.7+ (2011) | 可测试、无隐式依赖 |
| 每次操作新建 SQLite 连接 | 单连接 + `check_same_thread=False` | Python 3.2+ | 性能提升、线程安全 |
| 默认 journal mode (DELETE) | WAL 模式 | SQLite 3.7+ (2010) | 读写并发不阻塞 |
| Werkzeug dev server | gunicorn 生产服务器 | 长期最佳实践 | 多线程、信号处理、日志 |

**已过时：**
- `app.run()` 用于生产：Flask 官方文档明确标注为 "development server only" [VERIFIED: Flask docs]
- `init_web(app, db)` 全局初始化模式：Flask 官方推荐 Application Factory 替代

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 单 worker + 4 线程满足 Web 并发需求（日均 <100 请求） | gunicorn 配置 | 如果并发量增大需调整为多 worker + 外部 scheduler |
| A2 | SQLite WAL 模式在 macOS 上支持 :memory: 数据库 | pytest fixture | :memory: + WAL 可能有兼容性问题，需实测验证 |
| A3 | APScheduler BackgroundScheduler 在 gunicorn 单 worker 下运行正常 | gunicorn 配置 | fork 后的 worker 中 scheduler 行为需测试 |
| A4 | rss_feed.py 的 _build_rss_xml 函数可直接并入 api_bp | Blueprint 拆分 | RSS 路由注册方式变更可能导致外部订阅器 URL 变化 |

## Open Questions

1. **Blueprint 拆分后模板中的 `url_for()` 是否需要更新？**
   - What we know: 当前模板使用 `url_for('dashboard')` 等无前缀格式
   - What's unclear: Blueprint 注册时是否需要 `url_prefix=''` 来保持 endpoint 名不变
   - Recommendation: web_bp 使用空 url_prefix（根路径注册），api_bp 使用空 url_prefix（不改变 API URL）。endpoint 名会变为 `web.dashboard`，需要更新模板。

2. **publish.py 是否需要在 Phase 1 中同步重构？**
   - What we know: publish.py 也使用 `Database(DB_PATH)` + 原始 SQL
   - What's unclear: 是否保留为独立 CLI，还是合并入主应用
   - Recommendation: Phase 1 仅重构 publish.py 的 Database 使用方式（替换原始 SQL 为 Database 方法），保留独立 CLI 入口不变。login_only 重复逻辑的清理属于 Phase 2 范围。

3. **gunicorn 版本 23.0.0 vs PyPI 最新版 26.0.0**
   - What we know: 环境中已安装 23.0.0
   - What's unclear: 是否需要升级
   - Recommendation: 23.0.0 功能完整，无需升级。Phase 5 (Production) 时再评估。

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | 整个 Phase | yes | 3.13.2 | -- |
| Flask | Application Factory | yes | >=3.0.0 | -- |
| gunicorn | 生产部署 | yes | 23.0.0 | -- |
| APScheduler | 定时任务 | yes | >=3.10.0 | -- |
| sqlite3 | 数据库 | yes | stdlib | -- |
| pytest | 测试基础设施 | no | -- | pip install pytest pytest-cov |
| pytest-cov | 覆盖率报告 | no | -- | pip install pytest-cov |

**缺失依赖需安装：**
- `pip install pytest pytest-cov`

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (最新版) |
| Config file | pyproject.toml (新建) |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ --cov=src --cov-report=term-missing` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FOUND-01 | create_app() 返回 Flask 实例 | unit | `pytest tests/test_routes.py::test_create_app -x` | no Wave 0 |
| FOUND-02 | Database 方法返回正确数据 | unit | `pytest tests/test_database.py -x` | no Wave 0 |
| FOUND-03 | Blueprint 路由正常响应 | integration | `pytest tests/test_routes.py -x` | no Wave 0 |
| FOUND-04 | 并发写入不抛 SQLITE_BUSY | integration | `pytest tests/test_database.py::test_concurrent_writes -x` | no Wave 0 |
| FOUND-05 | pytest 基础设施可用 | smoke | `pytest tests/test_smoke.py -x` | no Wave 0 |
| FOUND-06 | gunicorn 可启动 app | manual | `gunicorn -c gunicorn.conf.py main:create_app` | no Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ --cov=src --cov-report=term-missing`
- **Phase gate:** Full suite green + coverage >= 80% before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `pyproject.toml` -- pytest 配置和项目元数据
- [ ] `tests/__init__.py` -- 测试包标记
- [ ] `tests/conftest.py` -- 共享 fixtures（db, app, client）
- [ ] `tests/test_database.py` -- Database 单元测试
- [ ] `tests/test_routes.py` -- 路由集成测试
- [ ] `tests/test_pipeline.py` -- Pipeline 编排测试
- [ ] `pip install pytest pytest-cov` -- 测试框架安装

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Phase 2 (SAFE-05) |
| V3 Session Management | no | Phase 2 |
| V4 Access Control | no | Phase 2 |
| V5 Input Validation | no | Phase 2 范围，Phase 1 保持现状 |
| V6 Cryptography | no | Phase 2 (SAFE-04) |

**Phase 1 不涉及安全加固。** 安全改进属于 Phase 2: Safety。Phase 1 仅重构架构，不改变安全行为。

## Implementation Order (推荐 Wave 划分)

### Wave 0: 测试基础设施（先于一切）
创建 `pyproject.toml`、`tests/conftest.py`（:memory: db fixture）、smoke test。
**产出：** `pytest tests/` 能运行。

### Wave 1: Database 类重构
单连接 + Lock + WAL，补齐 5 个缺失方法。已有方法签名不变。
**产出：** `tests/test_database.py` 全部通过，路由层可零 SQL。

### Wave 2: Application Factory + Blueprint 拆分
`create_app()` 工厂 + `create_web_bp(db)` + `create_api_bp(db)`。迁移路由。
**产出：** `tests/test_routes.py` 全部通过，`routes.py` 可删除。

### Wave 3: Pipeline 构造函数注入 + publish.py 适配
`create_pipeline(crawler, writer, db)` 注入。publish.py 替换原始 SQL。
**产出：** `tests/test_pipeline.py` 全部通过。

### Wave 4: gunicorn 部署 + 信号处理
`gunicorn.conf.py` + `atexit` handler + SIGTERM 处理。
**产出：** `gunicorn -c gunicorn.conf.py main:create_app` 可启动。

## Sources

### Primary (HIGH confidence)
- Flask 官方文档 Application Factories -- https://flask.palletsprojects.com/en/stable/patterns/appfactories/
- Flask 官方文档 Blueprints -- https://flask.palletsprojects.com/en/stable/blueprints/
- SQLite WAL 文档 -- https://www.sqlite.org/wal.html
- pytest fixtures 文档 -- https://docs.pytest.org/en/stable/how-to/fixtures.html
- 项目源码 main.py, routes.py, database.py, jobs.py -- [VERIFIED: 本地文件读取]
- 项目依赖 requirements.txt -- [VERIFIED: 本地文件读取]

### Secondary (MEDIUM confidence)
- gunicorn PyPI -- https://pypi.org/project/gunicorn/ (v26.0.0 release notes)
- Python threading.Lock stdlib 文档

### Tertiary (LOW confidence)
- gthread worker 配置细节 -- gunicorn 官方文档返回 404，使用训练知识补充

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- 所有依赖已验证存在于项目或可安装
- Architecture: HIGH -- Flask 官方文档直接支持 Factory + Blueprint 模式
- Pitfalls: MEDIUM -- gunicorn + APScheduler fork 行为需实测验证
- Database 并发: HIGH -- SQLite WAL 官方文档明确支持 reader-writer 并发

**Research date:** 2026-05-09
**Valid until:** 2026-06-09 (Flask/SQLite 生态稳定，30 天有效)
