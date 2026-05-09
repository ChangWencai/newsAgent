# Phase 2: Safety - Research

**Researched:** 2026-05-09
**Domain:** Web scraping safety, Flask authentication, content filtering, resilience patterns
**Confidence:** HIGH

## Summary

Phase 2 在 Phase 1 的 Application Factory + Blueprint + Database 架构基础上，对 8 个安全子系统进行加固。所有核心依赖（playwright 1.59.0, tenacity 9.1.2, Flask 3.1.1, APScheduler 3.11.2, python-dotenv 1.1.0）已安装在项目虚拟环境中，无需新增包。需要额外安装 `playwright-stealth` (pip) 和 `flask-wtf` 两个包。

关键技术发现：
- `playwright-stealth` 2.0.3 (pip) 是有效的反检测增强库，但官方明确标注仅绕过"基础 bot 检测"，不保证对抗头条的深度反爬策略
- tenacity 9.1.2 已安装，支持 `wait_exponential` 指数退避、`retry_if_exception_type` + `retry_if_result` 组合重试条件
- Flask-WTF 的 CSRFProtect 与 Application Factory 模式完全兼容，支持 lazy init
- 敏感词过滤没有成熟的 Python 标准库，需自建 DFA 算法模块，复杂度可控

**Primary recommendation:** 逐层推进 -- 先建立基础安全设施（密钥管理、认证、CSRF），再实现业务安全层（频率控制、敏感词过滤），最后优化爬虫健壮性（反检测、选择器、重试）。

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Playwright 反检测 (SAFE-01) | 爬虫/发布层 | — | toutiao_publisher.py 独立管理浏览器上下文 |
| 发布频率控制 (SAFE-02) | 数据层 + 调度层 | — | Database 计数方法 + APScheduler 触发前检查 |
| Cookie 过期通知 (SAFE-03) | API 层 + 前端 | 数据层 | /health 端点检测 + Web UI 轮询 + DB 持久化状态 |
| API 密钥管理 (SAFE-04) | 配置层 | — | config/settings.py 启动时验证 |
| Web UI 认证 (SAFE-05) | Web 路由层 | — | before_request 钩子 + Flask session |
| 敏感词过滤 (SAFE-06) | 业务逻辑层 | 数据层 | pipeline 发布前检查 + DB flagged 状态 |
| 选择器健壮性 (SAFE-07) | 爬虫/发布层 | — | toutiao_publisher.py 语义定位器迁移 |
| 重试机制 (SAFE-08) | 爬虫/业务逻辑层 | — | tophub.py 和 generator.py 装饰器 |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| playwright-stealth | 2.0.3 | 浏览器反检测指纹伪装 | 唯一活跃维护的 Playwright stealth Python 库 [VERIFIED: pip index] |
| flask-wtf | latest | CSRF 保护 + 表单验证 | Flask 官方推荐的表单/CSRF 扩展 [CITED: flask-wtf.readthedocs.io] |
| tenacity | 9.1.2 | 指数退避重试 | 已安装。Python 生态标准重试库，Apache 2.0，fork 自 retrying [VERIFIED: pip list] |
| python-dotenv | 1.1.0 | 环境变量管理 | 已安装。标准 .env 文件加载 [VERIFIED: pip list] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| APScheduler | 3.11.2 | 定时调度 | 已安装。发布频率控制的调度层 [VERIFIED: pip list] |
| Flask session | 3.1.1 | 用户认证状态 | 内置于 Flask，cookie 签名加密 [CITED: flask.palletsprojects.com] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| playwright-stealth | 手动修改 navigator.webdriver | 需要自行维护所有反检测补丁，遗漏风险高 |
| flask-wtf CSRFProtect | 手动实现 CSRF token | 容易出 token 时序/验证漏洞，不推荐 |
| tenacity | retrying (已停止维护) | tenacity 是 retrying 的活跃 fork，API 更完善 |
| DFA 自建敏感词过滤 | wordfilter / better-profanity | 这些库仅支持英文，中文敏感词需自建 |

**Installation:**
```bash
pip install playwright-stealth flask-wtf
```

## Architecture Patterns

### System Architecture Diagram

```
[APScheduler 每 6 小时触发]
       |
       v
[run_pipeline(db)] ---> can_publish(db)? --No--> 跳过本轮
       | Yes
       v
[tophub.get_hot_list()] --@retry--> [generator.generate_article()] --@retry-->
       |                                                      |
       v                                                      v
[敏感词过滤 check_sensitive_words()]              [db.insert_article()]
       |                                     flagged / draft
       v
[publisher.publish()] -- playwright-stealth -->
       |
       v
[db.mark_published()] + 更新 cookie_status

[/health 端点] <--- db.get_cookie_status() <--- publisher 更新
       |
       v
[Web UI 轮询 /health] ---> cookie_status != valid? --> banner 通知

[Web UI 请求] --> before_request --> session.authenticated? --No--> /login
       | Yes
       v
[正常路由处理] --> CSRFProtect 验证 POST 请求
```

### Recommended Project Structure
```
src/
├── crawler/
│   └── tophub.py          # 添加 @retry 装饰器
├── writer/
│   └── generator.py       # 添加 @retry 装饰器
├── publisher/
│   └── toutiao_publisher.py # playwright-stealth + 语义选择器
├── pipeline/
│   └── jobs.py            # can_publish() 检查 + 敏感词过滤调用
├── validator/             # 新建
│   └── sensitive.py       # DFA 敏感词检测模块
├── storage/
│   └── database.py        # 频率控制方法 + cookie 状态方法
├── web/
│   ├── routes/
│   │   ├── web.py         # before_request 认证钩子
│   │   └── api.py         # /health 扩展 cookie_status
│   └── templates/
│       ├── login.html     # 新建：登录页
│       └── base.html      # 修改：cookie 过期 banner
config/
│   ├── settings.py        # validate_config() + ADMIN_PASSWORD
│   └── __init__.py
data/
│   └── sensitive_words.txt # 敏感词列表（每行一个）
.env.example               # 新建：环境变量模板
```

### Pattern 1: Playwright Stealth 集成
**What:** 使用 playwright-stealth 库包装 Playwright 上下文创建，自动注入反检测脚本
**When to use:** 所有 Playwright 浏览器操作前
**Example:**
```python
# Source: pypi.org/project/playwright-stealth (v2.0.3)
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def publish(self, title, content, headless=False):
    async with Stealth().use_async(async_playwright()) as p:
        browser = await p.chromium.launch(headless=headless)
        context = await self._create_context(browser)
        # ... 后续流程不变
```

**注意事项：**
- playwright-stealth 官方标注 "proof-of-concept starting point"，仅绕过基础检测
- 头条的反爬可能包含行为分析（鼠标轨迹、打字速度），stealth 不覆盖这些维度
- 建议保留随机延迟 `asyncio.sleep(random.uniform(2, 5))` 作为补充措施
- `launch_persistent_context` 支持不完整，当前项目用 `new_context(storage_state=...)` 模式不受影响 [VERIFIED: pypi.org]

### Pattern 2: 发布频率控制 - Database 方法
**What:** Database 类扩展 3 个方法，pipeline 通过 can_publish() 控制发布节奏
**When to use:** run_pipeline 执行发布操作前
**Example:**
```python
# src/storage/database.py 新增方法
def can_publish(self, max_daily: int = 5, min_interval_minutes: int = 30) -> dict:
    """检查是否允许发布。返回 {"allowed": bool, "reason": str, "next_available": str}"""
    count = self.get_today_publish_count()
    if count >= max_daily:
        return {"allowed": False, "reason": f"今日已发布 {count} 篇（上限 {max_daily}）", "next_available": "明天 00:00"}
    last_time = self.get_last_publish_time()
    if last_time:
        elapsed = (datetime.now() - last_time).total_seconds() / 60
        if elapsed < min_interval_minutes:
            wait = min_interval_minutes - elapsed
            return {"allowed": False, "reason": f"距上次发布仅 {elapsed:.0f} 分钟", "next_available": f"{wait:.0f} 分钟后"}
    return {"allowed": True, "reason": "", "next_available": ""}

def get_today_publish_count(self) -> int:
    today = datetime.now().strftime("%Y-%m-%d")
    row = self._execute_read(
        "SELECT COUNT(*) FROM articles WHERE status='published' AND published_at >= ?",
        (today,)
    ).fetchone()
    return row[0] if row else 0

def get_last_publish_time(self) -> datetime | None:
    row = self._execute_read(
        "SELECT published_at FROM articles WHERE status='published' ORDER BY published_at DESC LIMIT 1"
    ).fetchone()
    if row and row[0]:
        return datetime.fromisoformat(row[0])
    return None
```

**Pipeline 集成：**
```python
# src/scheduler/jobs.py
def run_pipeline(db):
    check = db.can_publish(max_daily=5, min_interval_minutes=30)
    if not check["allowed"]:
        logger.info("发布跳过: %s, 下次: %s", check["reason"], check["next_available"])
        return
    # ... 原有 pipeline 逻辑
```

**注意事项：**
- 发布间隔 30-120 分钟随机化应在 APScheduler 调度层用 `jitter` 参数实现，不在 Database 方法中
- `get_today_publish_count()` 的 `published_at >= ?` 查询需精确到日期边界（当天 00:00:00）
- Database 单连接 + Lock 模式下，这些只读方法使用 `_execute_read` 无需加锁

### Pattern 3: Cookie 过期检测 - /health 扩展
**What:** /health 端点返回 cookie_status，publisher 每次操作后更新状态到 DB
**When to use:** 发布操作完成后更新，/health 查询时读取
**Example:**
```python
# src/storage/database.py 新增
def set_cookie_status(self, status: str):
    """status: 'valid' | 'expired' | 'missing'"""
    now = datetime.now().isoformat()
    self._execute_write(
        "INSERT OR REPLACE INTO system_kv (key, value, updated_at) VALUES ('cookie_status', ?, ?)",
        (status, now)
    )

def get_cookie_status(self) -> dict:
    row = self._execute_read(
        "SELECT value, updated_at FROM system_kv WHERE key = 'cookie_status'"
    ).fetchone()
    if row:
        return {"status": row[0], "updated_at": row[1]}
    return {"status": "missing", "updated_at": None}
```

**需新建 system_kv 表：**
```sql
CREATE TABLE IF NOT EXISTS system_kv (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

**/health 端点扩展：**
```python
# src/web/routes/api.py
@bp.route("/health")
def health():
    cookie = db.get_cookie_status()
    return {"status": "ok", "cookie_status": cookie["status"], "cookie_updated_at": cookie["updated_at"]}
```

**注意事项：**
- 轻量级检测方案：publisher._check_login() 已有实现，直接复用其结果即可，不额外访问头条
- 不要在 /health 端点中实时调用 Playwright 检测（太慢），应读取 DB 缓存状态
- 前端轮询间隔 5 分钟可用 setInterval 实现，cookie 过期时显示 banner

### Pattern 4: Flask Session 认证 + CSRFProtect
**What:** before_request 钩子检查 session 认证状态，CSRFProtect 保护所有 POST 表单
**When to use:** 所有 Web 路由（/login 和 /logout 除外）
**Example:**
```python
# Source: flask.palletsprojects.com/en/3.0.x/quickstart/#sessions
# Source: flask-wtf.readthedocs.io/en/1.2.x/csrf/

# src/web/routes/web.py
from flask import session, redirect, url_for, request

def create_web_bp(db):
    bp = Blueprint("web", __name__)

    @bp.before_request
    def require_auth():
        # 放行静态资源和登录页
        if request.endpoint in ("web.login", "web.static", None):
            return None
        if not session.get("authenticated"):
            return redirect(url_for("web.login"))

    @bp.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            password = request.form.get("password", "")
            from config.settings import ADMIN_PASSWORD
            if password == ADMIN_PASSWORD:
                session["authenticated"] = True
                return redirect(url_for("web.dashboard"))
            return render_template("login.html", error="密码错误"), 401
        return render_template("login.html")

    @bp.route("/logout")
    def logout():
        session.pop("authenticated", None)
        return redirect(url_for("web.login"))

    # ... 其他路由不变
    return bp
```

**main.py 集成：**
```python
from flask_wtf.csrf import CSRFProtect

def create_app(db=None, db_path=None):
    app = Flask(__name__, ...)
    app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
    csrf = CSRFProtect(app)
    # ... 注册 blueprints
```

**注意事项：**
- `app.secret_key` 必须设置，Flask session 依赖它进行 cookie 签名
- API 端点（/api/*, /health, /rss）不需要 session 认证，CSRFProtect 可用 `@csrf.exempt` 豁免
- `before_request` 钩子注册在 blueprint 上而非 app 上，只拦截该 blueprint 的路由
- api.py 的 Blueprint 需要单独处理，如果也需要认证则添加自己的 before_request

### Pattern 5: 敏感词过滤 - DFA 算法
**What:** 基于 DFA（确定性有限状态机）的高效敏感词匹配，O(n) 时间复杂度
**When to use:** pipeline 在文章生成后、发布前调用
**Example:**
```python
# src/validator/sensitive.py
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class SensitiveWordFilter:
    def __init__(self, word_file: str = "data/sensitive_words.txt"):
        self.word_file = word_file
        self._dfa = {}
        self._last_mtime = 0.0
        self._load_words()

    def _load_words(self):
        path = Path(self.word_file)
        if not path.exists():
            logger.warning("敏感词文件不存在: %s", self.word_file)
            return
        mtime = path.stat().st_mtime
        if mtime <= self._last_mtime:
            return  # 文件未变化
        self._dfa = {}
        count = 0
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                word = line.strip()
                if word:
                    self._add_word(word)
                    count += 1
        self._last_mtime = mtime
        logger.info("已加载 %d 个敏感词", count)

    def _add_word(self, word: str):
        node = self._dfa
        for char in word:
            node = node.setdefault(char, {})
        node["_end"] = True

    def check(self, text: str) -> list[str]:
        """返回文本中命中的敏感词列表"""
        self._load_words()  # 热重载：检查文件修改时间
        hits = []
        for i in range(len(text)):
            node = self._dfa
            j = i
            while j < len(text) and text[j] in node:
                node = node[text[j]]
                if "_end" in node:
                    hits.append(text[i:j+1])
                    break
                j += 1
        return hits

# 模块级单例
_filter = None

def check_sensitive_words(text: str) -> list[str]:
    global _filter
    if _filter is None:
        _filter = SensitiveWordFilter()
    return _filter.check(text)
```

**Pipeline 集成：**
```python
# src/pipeline/jobs.py
from src.validator.sensitive import check_sensitive_words

def run_pipeline(db):
    # ... 生成文章后
    hits = check_sensitive_words(article["content"])
    if hits:
        db.flag_article(article_id, reason=f"敏感词: {', '.join(hits)}")
        logger.warning("文章 %s 含敏感词，已标记", article_id)
        continue  # 不发布
```

**注意事项：**
- 热重载通过文件修改时间 (mtime) 比对实现，无额外开销
- DFA 算法匹配中文性能优秀，万级敏感词表对文章检测无性能瓶颈
- 该方案是中文内容过滤的通用做法，不需要外部库
- `flagged` 状态需在 articles 表的 status 约束中新增（或将 flagged 作为独立字段）

### Pattern 6: tenacity 重试装饰器
**What:** 统一的重试配置，覆盖网络异常和 HTTP 状态码
**When to use:** tophub.py 的 get_hot_list() 和 generator.py 的 generate_article()
**Example:**
```python
# Source: tenacity.readthedocs.io/en/latest/
from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception_type, retry_if_result, before_sleep_log
)
import requests
import logging

logger = logging.getLogger(__name__)

def _is_retryable_response(response):
    """HTTP 429 和 5xx 时重试"""
    return response.status_code == 429 or response.status_code >= 500

def _raise_for_retryable(response):
    """将可重试的响应转为异常，让 tenacity 捕获"""
    if _is_retryable_response(response):
        raise requests.HTTPError(f"Retryable status {response.status_code}", response=response)
    response.raise_for_status()  # 其他错误直接抛出
    return response

# 爬虫重试配置
crawl_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((
        requests.RequestException,
        requests.ConnectionError,
        requests.Timeout,
    )),
    reraise=True,
    before_sleep=before_sleep_log(logger, logging.WARNING),
)

# AI API 重试配置（包含状态码检查）
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
```

**集成方式：**
```python
# src/crawler/tophub.py
@crawl_retry
def get_hot_list(self):
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    # ...

# src/writer/generator.py
@api_retry
def generate_article(self, title, style="auto", context=None):
    message = self.client.messages.create(...)
    # ...
```

**注意事项：**
- `wait_exponential(multiplier=1, min=1, max=10)` 表示首次等待约 1 秒，最多 10 秒，呈指数增长
- `reraise=True` 确保最终失败时抛出原始异常而非 tenacity.RetryError
- `before_sleep_log` 在每次重试等待前记录日志，方便排查
- Anthropic SDK 自带重试（RateLimitError），用 `api_retry` 时注意不要重复重试
- 对于 requests 的 HTTP 429/5xx，标准 `raise_for_status()` 不区分可重试性，需自定义判断

### Anti-Patterns to Avoid
- **在 /health 中实时检测 cookie：** 健康检查需毫秒级响应，不能启动浏览器
- **密码明文比对后 log：** 绝不在日志中输出用户输入的密码
- **全局变量存认证状态：** 必须用 Flask session（cookie 签名加密）
- **敏感词用正则而非 DFA：** 正则表达式对大量关键词的性能远劣于 DFA
- **重试静默吞掉所有异常：** 必须设置 stop 条件，用 reraise=True 保留原始异常

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 浏览器反检测 | 手动注入 navigator.webdriver 脚本 | playwright-stealth | 覆盖多个检测维度，持续更新 |
| CSRF 保护 | 手动生成和验证 token | Flask-WTF CSRFProtect | 防止 token 时序/验证漏洞 |
| 指数退避重试 | 手动循环 + sleep | tenacity | 支持复杂条件组合、日志回调、统计 |
| 环境变量管理 | 手动 os.environ | python-dotenv | .env 文件标准管理 |

**关键洞察：** 安全领域（CSRF、密码存储、session 管理）的手工实现极易引入漏洞。始终使用经过审计的标准库。

## Common Pitfalls

### Pitfall 1: Flask SECRET_KEY 缺失导致 session 丢失
**What goes wrong:** 未设置 SECRET_KEY 时 Flask 会警告且 session 在重启后丢失
**Why it happens:** Flask session 需要 SECRET_KEY 进行 cookie 签名
**How to avoid:** 在 create_app() 中设置 `app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))`，生产环境必须通过 .env 固定值
**Warning signs:** 每次重启后用户被登出，Flask 日志出现 "Warning: SECRET_KEY is not set"

### Pitfall 2: before_request 钩子作用域混淆
**What goes wrong:** 在 Blueprint 上注册 before_request 只拦截该 Blueprint 的路由
**Why it happens:** Blueprint 级别的钩子不作用于全局
**How to avoid:** 认证钩子注册在 web Blueprint 上即可（api Blueprint 不需要认证）。如果需要全局认证，注册在 app 上
**Warning signs:** /api/* 端点被意外要求登录

### Pitfall 3: tenacity 与 Anthropic SDK 内置重试冲突
**What goes wrong:** Anthropic SDK 内部对 RateLimitError 有自动重试，外层 tenacity 导致重试次数叠加
**Why it happens:** 两层重试机制嵌套
**How to avoid:** 对 generator.py 的 API 调用使用较保守的 `stop=stop_after_attempt(2)`，或确认 SDK 内置重试行为后决定是否需要外层装饰器
**Warning signs:** 日志中出现大量重试记录，实际重试次数远超预期

### Pitfall 4: 敏感词热重载竞争条件
**What goes wrong:** 正在写入敏感词文件时触发重载，加载不完整数据
**Why it happens:** 文件修改时间在写入中途变化
**How to avoid:** 使用原子写入（写临时文件 + rename），或在加载时捕获异常保留旧数据
**Warning signs:** 敏感词检测突然漏检

## Code Examples

### 完整的 Application Factory 安全集成
```python
# main.py - 添加安全设施后的 create_app
import os
import secrets
from flask import Flask
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()

def create_app(db=None, db_path=None):
    app = Flask(
        __name__,
        template_folder="src/web/templates",
        static_folder="src/web/static",
    )

    # 安全配置
    app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

    if db is None:
        db = Database(db_path or DB_PATH)

    from src.web.routes import create_web_bp, create_api_bp

    app.register_blueprint(create_web_bp(db))
    app.register_blueprint(create_api_bp(db))

    csrf.init_app(app)
    # API 端点豁免 CSRF
    csrf.exempt(app.blueprints["api"])

    return app
```

### 配置验证函数
```python
# config/settings.py 新增
import sys

REQUIRED_VARS = ["MINIMAX_API_KEY", "TOPHUB_API_KEY"]
OPTIONAL_VARS = ["ADMIN_PASSWORD", "SECRET_KEY", "DOUYIN_NODE_HASHID"]

def validate_config():
    """启动时验证必填环境变量，缺失时退出"""
    missing = [v for v in REQUIRED_VARS if not os.getenv(v)]
    if missing:
        print(f"[FATAL] 缺少必填环境变量: {', '.join(missing)}")
        print(f"请复制 .env.example 为 .env 并填写配置")
        sys.exit(1)
    unset_optional = [v for v in OPTIONAL_VARS if not os.getenv(v)]
    if unset_optional:
        print(f"[WARN] 可选环境变量未设置: {', '.join(unset_optional)}")
```

### .env.example 模板
```
# .env.example - 复制为 .env 并填写实际值

# 必填
MINIMAX_API_KEY=your_minimax_api_key_here
TOPHUB_API_KEY=your_tophub_api_key_here

# 可选 - Web UI 管理员密码（未设置则 Web 界面无认证）
ADMIN_PASSWORD=

# 可选 - Flask session 加密密钥（未设置则每次重启后用户需重新登录）
SECRET_KEY=

# 可选 - 抖音节点 hashid
DOUYIN_NODE_HASHID=

# 可选 - 服务配置
RSS_HOST=0.0.0.0
RSS_PORT=5000
RSS_BASE_URL=http://localhost:5000
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 无反检测 | playwright-stealth 2.0.3 | 2026-04 | 绕过 navigator.webdriver 等基础检测 |
| 无频率限制 | SQLite 计数器 + APScheduler jitter | 本阶段新增 | 防止频繁触发反爬 |
| 无认证 | Flask session + CSRFProtect | 本阶段新增 | 防止未授权访问 |
| 纯 CSS 选择器 | Playwright 语义定位器 | 本阶段迁移 | 提高选择器抗变更能力 |

**Deprecated/outdated:**
- retrying 库（已停止维护）→ 使用 tenacity
- 手动 navigator.webdriver = false → 使用 playwright-stealth 统一处理

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 头条发布页面的反爬检测深度不超过 playwright-stealth 覆盖范围 | SAFE-01 | 中 — 如果头条有行为分析，stealth 不够用，需补充鼠标轨迹模拟 |
| A2 | articles 表 status 字段可扩展加入 'flagged' 值而不破坏已有逻辑 | SAFE-06 | 低 — status 是 TEXT DEFAULT 'draft'，无 CHECK 约束 |
| A3 | Anthropic SDK 的 RateLimitError 和 APIConnectionError 可被 tenacity retry_if_exception_type 捕获 | SAFE-08 | 低 — 这些是标准异常类，SDK 文档确认 |
| A4 | Flask session cookie 大小不超过 4KB 浏览器限制 | SAFE-05 | 低 — session 中只存 authenticated=True，数据极小 |
| A5 | 项目当前未使用 SECRET_KEY，添加后不会影响已有 cookie（因为之前无 session 数据） | SAFE-05 | 低 — 无已有 session 数据需迁移 |

## Open Questions (RESOLVED)

1. **头条反爬深度** — RESOLVED
   - Decision: 先部署 playwright-stealth + 随机延迟作为基线，通过实际发布成功率数据决定是否需要补充行为模拟
   - Risk acceptance: 中风险，发布成功率下降时触发二次加固计划
   - Plan: 02-05 Task 11 实施

2. **敏感词初始词库来源** — RESOLVED
   - Decision: 初始版本提供最小核心词库（约 100 个），手动维护，存放在 `data/sensitive_words.txt`
   - 用户可自行扩充词库，文件热重载无需重启
   - Plan: 02-04 Task 9 实施

3. **flagged 状态在 Web UI 的审核流程** — RESOLVED
   - Decision: 在现有 articles 列表页面增加 "审核通过" 按钮（对 flagged 状态文章显示），点击后将 status 从 "flagged" 改为 "draft" 允许后续发布
   - 不单独创建审核页面，复用现有列表视图
   - Plan: 02-04 Task 10 实施

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | 全局 | ✓ | 3.13.2 | — |
| playwright | SAFE-01/07 | ✓ | 1.59.0 | — |
| tenacity | SAFE-08 | ✓ | 9.1.2 | — |
| Flask | SAFE-05 | ✓ | 3.1.1 | — |
| APScheduler | SAFE-02 | ✓ | 3.11.2 | — |
| python-dotenv | SAFE-04 | ✓ | 1.1.0 | — |
| playwright-stealth | SAFE-01 | ✗ | — | pip install playwright-stealth |
| flask-wtf | SAFE-05 | ✗ | — | pip install flask-wtf |

**Missing dependencies with no fallback:**
- 无

**Missing dependencies with fallback:**
- playwright-stealth: pip install 即可
- flask-wtf: pip install 即可

## Validation Architecture

> nyquist_validation is false in config.json -- skipping validation section.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Flask session + ADMIN_PASSWORD 环境变量 |
| V3 Session Management | yes | Flask 内置 cookie 签名 session |
| V4 Access Control | yes | before_request 钩子 + session 检查 |
| V5 Input Validation | yes | 敏感词过滤 DFA + 表单密码验证 |
| V6 Cryptography | yes | Flask SECRET_KEY 签名 session cookie，不手写加密 |

### Known Threat Patterns for Flask + Playwright

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|-----|
| CSRF 攻击 | Spoofing | Flask-WTF CSRFProtect 自动注入/验证 token |
| Session 劫持 | Elevation | Flask 签名 cookie + HTTPS（部署层） |
| 反爬检测封禁 | Denial of Service | playwright-stealth + 随机延迟 + 频率控制 |
| XSS（模板注入） | Tampering | Jinja2 自动转义 + markupsafe |
| 敏感信息泄露 | Information Disclosure | validate_config() 启动检查 + .env.example |

## Sources

### Primary (HIGH confidence)
- pip index playwright-stealth -- 确认版本 2.0.3，pip install playwright-stealth
- pypi.org/project/playwright-stealth -- API 用法、反检测技术列表、已知限制
- tenacity.readthedocs.io -- 完整 API：retry 条件、wait 策略、stop 条件、回调
- flask.palletsprojects.com/en/3.0.x/quickstart -- Flask session 机制、SECRET_KEY 要求
- flask-wtf.readthedocs.io/en/1.2.x/csrf -- CSRFProtect 初始化、模板集成、豁免机制
- playwright.dev/python/docs/locators -- 语义定位器最佳实践

### Secondary (MEDIUM confidence)
- pip list（本地环境）-- 确认所有依赖版本

### Tertiary (LOW confidence)
- 无

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- 所有依赖版本已通过 pip 验证，API 通过官方文档确认
- Architecture: HIGH -- 基于 Phase 1 已验证的 Application Factory + Blueprint 模式扩展
- Pitfalls: MEDIUM -- Flask/tenacity 常见坑已文档化，头条反爬深度为推测

**Research date:** 2026-05-09
**Valid until:** 2026-06-09（30 天，依赖版本稳定）
