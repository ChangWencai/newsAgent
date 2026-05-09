<!-- refreshed: 2026/05/09 -->
# Architecture

**Analysis Date:** 2026/05/09

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────┐
│                         CLI / Scheduler                              │
│   `main.py` (Flask + APScheduler 6h)    `publish.py` (手动发布)      │
└──────────┬───────────────────────────────────────┬──────────────────┘
           │ triggers                              │ triggers
           ▼                                       ▼
┌─────────────────────────┐         ┌──────────────────────────────┐
│  src/scheduler/jobs.py  │         │ src/publisher/toutiao_       │
│  run_pipeline(db)       │         │ publisher.py                 │
│                         │         │ ToutiaoPublisher             │
│ 1. Crawl  2. Dedup      │         │ (Playwright 自动化发布)       │
│ 3. Generate  4. Store   │         └──────────────────────────────┘
└────┬──────┬──────┬──────┘
     │      │      │
     ▼      │      ▼
┌────────┐  │  ┌─────────────────────────────────────────┐
│ Crawler│  │  │              Writer                      │
│tophub  │  │  │  generator.py (MiniMax-M2.7 via          │
│.py     │  │  │   Anthropic SDK)                         │
│(Douyin │  │  │  styles.py (news/comment/entertainment)  │
│ 热搜)  │  │  └──────────────┬──────────────────────────┘
└────────┘  │                 │
            ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                  src/storage/database.py                         │
│                  SQLite (data/newsagent.db)                      │
│                  Tables: hot_topics, articles                    │
└──────────┬──────────────────────────┬───────────────────────────┘
           │                          │
           ▼                          ▼
┌──────────────────────┐  ┌──────────────────────────────────────┐
│ src/web/routes.py    │  │ src/publisher/rss_feed.py            │
│ (Flask MVC)          │  │ /rss  -> RSS 2.0 XML                 │
│ /  仪表盘             │  │ /health -> {"status": "ok"}          │
│ /topics  热点榜       │  └──────────────────────────────────────┘
│ /articles  文章管理   │
│ /settings  设置       │
│ /api/*  JSON API      │
└──────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| DouyinCrawler | 抓取抖音热搜榜，返回结构化热点列表 | `src/crawler/tophub.py` |
| ArticleGenerator | 调用 MiniMax-M2.7 API 生成文章 | `src/writer/generator.py` |
| STYLES / detect_style | 文章风格模板与关键词自动分类 | `src/writer/styles.py` |
| Database | SQLite 持久化：热点和文章 CRUD | `src/storage/database.py` |
| run_pipeline | 编排完整流水线：抓取 -> 去重 -> 生成 -> 存储 | `src/scheduler/jobs.py` |
| ToutiaoPublisher | Playwright 自动登录并发布文章到头条号 | `src/publisher/toutiao_publisher.py` |
| RSS Feed | 生成 RSS 2.0 XML，供外部订阅 | `src/publisher/rss_feed.py` |
| Web Routes | Flask 路由：仪表盘、文章管理、设置、API | `src/web/routes.py` |
| Settings | 环境变量配置（dotenv） | `config/settings.py` |

## Pattern Overview

**Overall:** Pipeline + MVC hybrid

**Key Characteristics:**
- **Pipeline pattern** for core data flow: Crawl -> Deduplicate -> Generate -> Store -> Publish
- **MVC pattern** for the web management layer (Flask templates as views, routes as controllers, Database as model)
- **Repository pattern** encapsulates all SQLite access behind the `Database` class
- **Event-driven scheduling** via APScheduler background thread triggers pipeline every 6 hours

## Layers

**Crawler Layer:**
- Purpose: 从外部数据源抓取热点话题
- Location: `src/crawler/tophub.py`
- Contains: `DouyinCrawler` class with `get_hot_list()` method
- Depends on: `requests` library, Douyin API endpoint
- Used by: `src/scheduler/jobs.py`

**Writer Layer:**
- Purpose: 利用 AI 大模型生成文章
- Location: `src/writer/generator.py`, `src/writer/styles.py`
- Contains: `ArticleGenerator` class, 3 种 style 模板（news/comment/entertainment），基于关键词的 `detect_style()` 函数
- Depends on: `anthropic` SDK, MiniMax API（Anthropic 兼容端点 `https://api.minimaxi.com/anthropic`）
- Used by: `src/scheduler/jobs.py`

**Storage Layer:**
- Purpose: 数据持久化（热点和文章）
- Location: `src/storage/database.py`
- Contains: `Database` class -- 6 个公开方法：`topic_exists`, `insert_topic`, `insert_article`, `get_unpublished_articles`, `get_recent_articles`, `mark_published`
- Depends on: `sqlite3`（内置）
- Used by: 所有模块（crawler/writer 通过 scheduler 间接使用，routes/rss_feed/publish 直接使用）

**Publisher Layer:**
- Purpose: 将文章发布到外部平台或提供 RSS 输出
- Location: `src/publisher/rss_feed.py`, `src/publisher/toutiao_publisher.py`
- Contains: RSS XML 生成函数 `_build_rss_xml()`，`ToutiaoPublisher` 类（8 个方法：`publish`, `_create_context`, `_check_login`, `_wait_login`, `_do_publish`, `_select_cover`）
- Depends on: `playwright`, `flask`, `Database`
- Used by: `main.py`（RSS 路由注册），`publish.py`（头条发布）

**Scheduler Layer:**
- Purpose: 定时触发新闻生产流水线
- Location: `src/scheduler/jobs.py`
- Contains: `run_pipeline(db)` 编排函数（24 行，4 步流水线）
- Depends on: Crawler, Writer, Storage
- Used by: `main.py`（APScheduler），`src/web/routes.py`（手动触发 API）

**Web Layer:**
- Purpose: 提供管理界面和 REST API
- Location: `src/web/routes.py`, `src/web/templates/`, `src/web/static/`
- Contains: 7 个路由（`/`, `/topics`, `/articles`, `/article/<id>`, `/api/run-pipeline`, `/api/article/<id>/delete`, `/settings`），6 个 Jinja2 模板
- Depends on: Database（直接执行 SQL），Scheduler（调用 run_pipeline）
- Used by: `main.py`（通过 `init_web(app, db)` 注册）

## Data Flow

### Primary Pipeline Path（定时流水线，每 6 小时）

1. **APScheduler 触发** `run_pipeline(db)` (`main.py:60-69`, interval=6h)
2. **抓取热点** `DouyinCrawler.get_hot_list()` (`src/crawler/tophub.py:16-36`)
   - HTTP GET `https://www.douyin.com/aweme/v1/web/hot/search/list/`
   - 解析 JSON response -> `[{title, url, hot_value, category}]`
3. **去重过滤** `db.topic_exists(title)` (`src/scheduler/jobs.py:29-33`)
   - 遍历热点列表，跳过 title 已在 hot_topics 表中的条目
   - 截断到 `MAX_TOPICS_PER_RUN`（默认 5）条
4. **存储热点** `db.insert_topic(title, url, hot_value, category)` (`src/scheduler/jobs.py:45-49`)
   - INSERT into `hot_topics` 表，status='pending'
5. **AI 生成文章** `ArticleGenerator.generate_article(title, style)` (`src/writer/generator.py:22-61`)
   - 如果 style='auto'，调用 `detect_style(title)` 根据关键词选择风格
   - 构建 system prompt（来自 STYLES 字典），调用 MiniMax-M2.7 API
   - 解析响应：提取"标题："、"正文："、"摘要："段落
6. **存储文章** `db.insert_article(topic_id, title, content, style)` (`src/scheduler/jobs.py:62-67`)
   - INSERT into `articles` 表，status='draft'

### Manual Publish Path（手动发布）

1. **CLI 启动** `python publish.py [--id ID ...]` (`publish.py:107-116`)
2. **加载文章** `db.get_unpublished_articles()` 或指定 ID 查询 (`publish.py:57-71`)
3. **Playwright 自动化** `ToutiaoPublisher` 流程 (`src/publisher/toutiao_publisher.py:98-149`)
   - `_create_context()` 加载 cookie 文件（如果存在）
   - `_check_login()` 访问发布页检查登录状态
   - `_wait_login()` 未登录时打开登录页等待手动扫码（最长 5 分钟）
   - `_do_publish()` 填写标题（`textarea`）、正文（`.ProseMirror`）、选择封面、点击发布按钮
4. **标记已发布** `db.mark_published(article_id)` (`publish.py:99`)
   - UPDATE articles SET status='published', published_at=now

### RSS Output Path

1. **HTTP 请求** `GET /rss` (`src/publisher/rss_feed.py:14-18`)
2. **查询文章** `db.get_recent_articles(limit=20)` (`src/publisher/rss_feed.py:16`)
3. **生成 XML** `_build_rss_xml(articles)` (`src/publisher/rss_feed.py:27-47`)
   - 构建 RSS 2.0 XML tree，每篇文章一个 `<item>` 节点
4. **返回** `Response(xml_str, mimetype="application/rss+xml; charset=utf-8")`

**State Management:**
- 所有业务状态存储在 SQLite (`data/newsagent.db`)
- 文章状态流转: `draft` -> `published`
- 热点状态: 固定为 `pending`（无后续流转）
- 头条登录 Cookie: 文件存储在 `data/cookies/toutiao_state.json`
- 无内存缓存或 session 状态

## Key Abstractions

**Database (Repository Pattern):**
- Purpose: 封装所有数据访问，提供统一 CRUD 接口
- File: `src/storage/database.py`
- Pattern: 单一类提供 6 个公开方法，每次操作通过 `_get_conn()` 新建 SQLite 连接
- Note: routes.py 中部分路由绕过此类直接执行 SQL（见 Anti-Patterns）

**ArticleGenerator:**
- Purpose: 封装 AI 文章生成逻辑
- File: `src/writer/generator.py`
- Pattern: 构造函数注入 API key（默认从环境变量），`generate_article()` 接收标题和风格参数，返回 `{title, content, summary, style}` dict

**DouyinCrawler:**
- Purpose: 简单 HTTP 客户端封装
- File: `src/crawler/tophub.py`
- Pattern: 无状态单方法类，`get_hot_list()` 返回 `list[dict]`

**STYLES dict (Strategy Pattern):**
- Purpose: 通过 style key 选择不同的 AI system prompt
- File: `src/writer/styles.py`
- Pattern: 字典映射 style name -> system prompt，`detect_style()` 实现基于关键词的策略选择

## Entry Points

**main.py（主服务入口）:**
- Location: `/Users/wencai/github/newsAgent/main.py`
- Triggers: `python main.py [--run-once] [--port PORT] [--host HOST]`
- Responsibilities:
  - 创建 `Database` 实例
  - 启动 APScheduler `BackgroundScheduler`（interval=6h）
  - 创建 Flask app：合并 RSS 路由 + Web 管理路由
  - 启动 HTTP 服务（默认 `0.0.0.0:5000`）
- Dual mode: 服务模式（默认，持续运行）和单次执行模式（`--run_once`，执行一次后退出）

**publish.py（发布工具入口）:**
- Location: `/Users/wencai/github/newsAgent/publish.py`
- Triggers: `python publish.py [--id ID ...] [--login]`
- Responsibilities: 独立执行头条文章发布，不依赖 main.py
- `--login` flag: 仅登录保存 Cookie，不发布文章

## Architectural Constraints

- **Threading:** APScheduler `BackgroundScheduler` 在后台线程运行流水线，Flask 主线程处理 HTTP 请求。两者共享同一个 `Database` 实例。SQLite WAL 模式支持并发读，但写操作可能阻塞。
- **Global state:** `src/web/routes.py` 第 20 行定义模块级 `_db` 变量，由 `init_web()` 初始化。这是隐式全局状态，所有路由函数依赖此变量。
- **Circular imports:** 无已知循环导入。依赖方向清晰：`scheduler` -> `crawler`/`writer`/`storage`，`web` -> `storage`/`scheduler`，`publisher` -> `storage`/`flask`。
- **No connection pooling:** Database 每次操作通过 `_get_conn()` 新建/关闭连接，无连接池或上下文管理器。
- **No dependency injection:** `run_pipeline()` 中直接实例化 `DouyinCrawler()` 和 `ArticleGenerator()`，无法在测试中替换。
- **No authentication:** Web 界面无任何访问控制，所有路由完全公开。
- **No tests:** 无测试文件、无测试配置、无 pytest/unittest 基础设施。
- **Single-process only:** Flask 开发服务器，无 Gunicorn/uWSGI 多 worker 支持。

## Anti-Patterns

### 1. 模块级全局可变状态（Web Routes）

**What happens:** `src/web/routes.py` 第 20 行定义 `global _db`，所有路由函数（`dashboard`, `topics_list`, `articles_list`, `article_detail`, `api_run_pipeline`, `api_delete_article`, `settings_page`）通过此全局变量访问数据库。

**Why it's wrong:** 模块隐式依赖 `init_web()` 必须在首次请求前调用。无法在测试中独立测试路由函数。并发场景下全局状态可能导致不可预期行为。

**Do this instead:** 使用 Flask 应用工厂模式，通过 `app.config['db']` 或 `g.db` 传递依赖；或者将路由封装在 Blueprint 类中，通过构造函数注入 `db`。

### 2. Route Handler 中绕过 Repository 执行原始 SQL

**What happens:** `src/web/routes.py` 的 `dashboard()`（第 43-55 行）、`topics_list()`（第 70-76 行）、`articles_list()`（第 81-98 行）、`article_detail()`（第 103-111 行）、`api_delete_article()`（第 127-135 行）直接调用 `_db._get_conn().execute()` 执行原始 SQL，绕过了 `Database` 类的公共方法。

**Why it's wrong:** SQL 逻辑分散在 routes.py 和 database.py 两个地方，Database 类的抽象被破坏。修改表结构时需要同时修改两个文件。`api_delete_article()` 执行的 DELETE 操作在 Database 类中完全没有对应方法。

**Do this instead:** 在 `Database` 类中添加缺少的方法（`get_dashboard_stats()`, `get_topics(limit)`, `delete_article(id)` 等），所有 SQL 集中在 database.py 中，routes 只调用 Database 公共方法。

### 3. 重复的登录等待逻辑

**What happens:** `publish.py` 的 `login_only()` 函数（第 25-54 行）与 `ToutiaoPublisher._wait_login()`（第 75-96 行）逻辑几乎完全相同：都是打开登录页、轮询 URL 变化、保存 cookie。

**Why it's wrong:** 两份相同代码，修改时容易遗漏一处导致不一致。

**Do this instead:** 删除 `publish.py` 中的 `login_only()`，改为直接调用 `ToutiaoPublisher()._wait_login(page, context)` 或将其提取为独立公共函数。

### 4. 硬编码的 CSS 选择器依赖

**What happens:** `src/publisher/toutiao_publisher.py` 的 `_do_publish()` 和 `_select_cover()` 方法中硬编码了头条平台的 DOM 选择器（如 `"textarea"`, `".ProseMirror"`, `"button.publish-btn-last"`, `".article-cover-images-wrap .article-cover-images > div > div > div > div"`）。

**Why it's wrong:** 头条平台前端改版时，这些选择器会立即失效。深层嵌套选择器（7 层 `div`）极其脆弱。

**Do this instead:** 使用 data-testid 或更语义化的选择器；将选择器提取为模块级常量或配置，方便集中更新；添加选择器失效时的错误提示和降级逻辑。

### 5. ArticleGenerator 解析逻辑脆弱

**What happens:** `src/writer/generator.py` 的 `_parse_response()`（第 63-103 行）依赖 AI 输出严格遵循"标题："、"正文："、"摘要："前缀格式。如果模型输出格式稍有变化（如使用 Markdown `## 标题`），解析会失败并进入兜底逻辑。

**Why it's wrong:** AI 模型输出格式不可控，当前解析过于依赖特定格式。兜底逻辑仅取第一行作为标题（截断到 50 字），质量可能很差。

**Do this instead:** 使用更鲁棒的解析策略（正则表达式、多种格式兼容）；或让模型返回 JSON 格式（在 system prompt 中指定），使用 `json.loads()` 解析。

---

*Architecture analysis: 2026/05/09*
