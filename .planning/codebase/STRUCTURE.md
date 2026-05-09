# Codebase Structure

**Analysis Date:** 2026/05/09

## Directory Layout

```
newsAgent/
├── main.py                  # 主入口：Flask + APScheduler 服务启动
├── publish.py               # 头条发布工具入口（独立 CLI 脚本）
├── requirements.txt         # Python 依赖（6 个包）
├── .env                     # 环境变量（gitignore，含 API keys）
├── .env.example             # 环境变量模板
├── .gitignore               # Git 忽略规则
├── config/                  # 配置模块
│   ├── __init__.py          # 空文件
│   └── settings.py          # 从 .env 读取所有配置项（9 个配置变量）
├── src/                     # 核心源码
│   ├── __init__.py          # 空文件
│   ├── crawler/             # 数据抓取层
│   │   ├── __init__.py      # 空文件
│   │   └── tophub.py        # DouyinCrawler: 抖音热搜抓取（37 行）
│   ├── writer/              # AI 写作层
│   │   ├── __init__.py      # 空文件
│   │   ├── generator.py     # ArticleGenerator: MiniMax API 调用（103 行）
│   │   └── styles.py        # STYLES 字典 + detect_style 关键词匹配（76 行）
│   ├── storage/             # 数据存储层
│   │   ├── __init__.py      # 空文件
│   │   └── database.py      # Database 类: SQLite CRUD（109 行）
│   ├── publisher/           # 发布层
│   │   ├── __init__.py      # 空文件
│   │   ├── rss_feed.py      # RSS 2.0 XML 生成（63 行）
│   │   └── toutiao_publisher.py  # ToutiaoPublisher: Playwright 自动发布（189 行）
│   ├── scheduler/           # 调度层
│   │   ├── __init__.py      # 空文件
│   │   └── jobs.py          # run_pipeline(): 流水线编排（73 行）
│   └── web/                 # Web 管理界面
│       ├── __init__.py      # 空文件
│       ├── routes.py        # Flask 路由定义（150 行）
│       ├── static/          # 静态资源目录（当前为空）
│       └── templates/       # Jinja2 HTML 模板
│           ├── base.html    # 基础布局（内联 CSS/JS，85 行）
│           ├── index.html   # 仪表盘首页
│           ├── topics.html  # 热点列表页
│           ├── articles.html # 文章列表页
│           ├── article_detail.html # 文章详情页
│           └── settings.html # 设置展示页
├── data/                    # 运行时数据（gitignore）
│   ├── newsagent.db         # SQLite 数据库（2 张表）
│   └── cookies/             # Playwright cookie 存储
│       └── toutiao_state.json # 头条登录状态
└── venv/                    # Python 虚拟环境（gitignore）
```

## Directory Purposes

**`config/`:**
- Purpose: 集中管理所有项目配置
- Contains: `settings.py` 从 `.env` 读取 9 个配置变量（`TOPHUB_API_KEY`, `TOPHUB_BASE_URL`, `DOUYIN_NODE_HASHID`, `MINIMAX_API_KEY`, `MINIMAX_BASE_URL`, `MINIMAX_MODEL`, `RSS_HOST`, `RSS_PORT`, `RSS_BASE_URL`, `DEFAULT_STYLE`, `MAX_TOPICS_PER_RUN`, `DB_PATH`）
- Key files: `config/settings.py`
- Pattern: 模块级常量导出，无类封装

**`src/crawler/`:**
- Purpose: 从外部数据源抓取热点话题
- Contains: `DouyinCrawler` 类，单方法 `get_hot_list()` 返回 `list[dict]`
- Key files: `src/crawler/tophub.py`（37 行）
- Note: 文件名 `tophub.py` 与实际抓取源（抖音）不匹配，可能存在历史遗留命名

**`src/writer/`:**
- Purpose: AI 文章生成和风格控制
- Contains: `ArticleGenerator` 类（`generate_article`, `_parse_response`），`STYLES` 字典（3 种风格模板），`detect_style()` 关键词匹配函数
- Key files: `src/writer/generator.py`（103 行），`src/writer/styles.py`（76 行）
- API endpoint: `https://api.minimaxi.com/anthropic`（Anthropic SDK 兼容）

**`src/storage/`:**
- Purpose: 数据持久化
- Contains: `Database` 类，6 个公开方法 + 2 个私有方法（`_get_conn`, `_init_tables`）
- Key files: `src/storage/database.py`（109 行）
- Tables: `hot_topics`（6 列）, `articles`（8 列，外键关联 hot_topics）
- Indexes: `idx_topics_title`, `idx_articles_status`

**`src/publisher/`:**
- Purpose: 内容发布到外部平台
- Contains:
  - `rss_feed.py`: `create_rss_app(db)` 工厂函数 + `_build_rss_xml()` XML 构建
  - `toutiao_publisher.py`: `ToutiaoPublisher` 类（8 个方法），`publish_article()` 同步包装函数
- Key files: `src/publisher/rss_feed.py`（63 行），`src/publisher/toutiao_publisher.py`（189 行，项目最大源文件）
- External dep: `playwright`（头条发布）

**`src/scheduler/`:**
- Purpose: 定时任务编排
- Contains: `run_pipeline(db)` 编排函数，4 步流水线（抓取 -> 去重 -> 生成 -> 存储）
- Key files: `src/scheduler/jobs.py`（73 行）
- Config: `MAX_TOPICS_PER_RUN`（默认 5）控制每轮处理热点数

**`src/web/`:**
- Purpose: Web 管理界面
- Contains: 7 个路由（dashboard, topics, articles, article_detail, api_run_pipeline, api_delete_article, settings），6 个 Jinja2 模板
- Key files: `src/web/routes.py`（150 行），`src/web/templates/base.html`
- Static: `src/web/static/` 目录存在但为空，所有 CSS/JS 内联在 `base.html` 中

**`data/`:**
- Purpose: 运行时持久化数据
- Contains: SQLite 数据库文件，Playwright cookie 文件
- Generated: Yes（运行时自动创建，`Database.__init__` 创建目录和表）
- Committed: No（在 `.gitignore` 中）

## Key File Locations

**Entry Points:**
- `/Users/wencai/github/newsAgent/main.py`: 主服务入口 -- 启动 Flask Web + APScheduler 定时任务
- `/Users/wencai/github/newsAgent/publish.py`: 头条发布工具入口 -- 独立 CLI 脚本，支持 `--login` 和 `--id` 参数

**Configuration:**
- `/Users/wencai/github/newsAgent/config/settings.py`: 所有配置项集中定义，从 `.env` 读取
- `/Users/wencai/github/newsAgent/.env`: 实际环境变量值（含 API keys）
- `/Users/wencai/github/newsAgent/.env.example`: 环境变量模板，列出所有必需配置

**Core Logic:**
- `/Users/wencai/github/newsAgent/src/scheduler/jobs.py`: 生产流水线编排（`run_pipeline`）
- `/Users/wencai/github/newsAgent/src/crawler/tophub.py`: 热点数据抓取（`DouyinCrawler`）
- `/Users/wencai/github/newsAgent/src/writer/generator.py`: AI 文章生成（`ArticleGenerator`）
- `/Users/wencai/github/newsAgent/src/writer/styles.py`: 文章风格模板和自动分类
- `/Users/wencai/github/newsAgent/src/storage/database.py`: 数据库操作封装（`Database`）

**Publishing:**
- `/Users/wencai/github/newsAgent/src/publisher/rss_feed.py`: RSS Feed 生成
- `/Users/wencai/github/newsAgent/src/publisher/toutiao_publisher.py`: 头条号自动发布

**Web Interface:**
- `/Users/wencai/github/newsAgent/src/web/routes.py`: Flask 路由定义
- `/Users/wencai/github/newsAgent/src/web/templates/base.html`: 基础布局模板（含所有 CSS/JS）

**Testing:**
- 不存在 -- 无测试文件、无测试配置、无 pytest.ini / setup.cfg 中的测试段

## Naming Conventions

**Files:**
- Python modules: 小写蛇形命名（`tophub.py`, `rss_feed.py`, `toutiao_publisher.py`）
- HTML templates: 小写蛇形命名（`article_detail.html`, `base.html`）
- Root scripts: 小写单词（`main.py`, `publish.py`）

**Directories:**
- 功能模块命名: 小写单数名词（`crawler`, `writer`, `storage`, `publisher`, `scheduler`, `web`）

**Classes:**
- PascalCase: `DouyinCrawler`, `ArticleGenerator`, `ToutiaoPublisher`, `Database`

**Functions/Methods:**
- 小写蛇形: `get_hot_list()`, `generate_article()`, `run_pipeline()`, `topic_exists()`
- 私有方法: 前缀下划线: `_get_conn()`, `_init_tables()`, `_parse_response()`, `_create_context()`, `_check_login()`, `_wait_login()`, `_do_publish()`, `_select_cover()`

**Constants/Config:**
- 大写蛇形: `TOPHUB_API_KEY`, `MINIMAX_MODEL`, `RSS_HOST`, `DB_PATH`

**Module-level Variables:**
- 全局配置: 大写蛇形常量（`config/settings.py`）
- 模块状态: 小写蛇形（`_db` in `routes.py` -- 实际应避免）

## Where to Add New Code

**新增数据源抓取器:**
- 实现文件: `src/crawler/` 目录下新建 `.py` 文件
- Pattern: 参考 `src/crawler/tophub.py` 中的 `DouyinCrawler`，实现 `get_hot_list()` 方法返回 `list[dict]`
- 集成: 修改 `src/scheduler/jobs.py` 的 `run_pipeline()` 函数调用新抓取器

**新增文章风格:**
- 模板定义: `src/writer/styles.py` -- 在 `STYLES` 字典中添加 `{name: {name, system}}` 条目
- 关键词检测: `src/writer/styles.py` -- 在 `STYLE_KEYWORDS` 字典中添加关键词列表
- 自动生效: `detect_style()` 遍历 `STYLE_KEYWORDS`，新增风格无需修改调用方

**新增 Web 页面:**
- 路由: `src/web/routes.py` -- 添加视图函数，在 `init_web()` 中注册 `app.add_url_rule()`
- 模板: `src/web/templates/` -- 新建 HTML 文件，`{% extends "base.html" %}`
- 静态资源: `src/web/static/` -- 当前为空目录，可在此添加 CSS/JS 文件

**新增 API 端点:**
- 路由: `src/web/routes.py` -- 添加返回 `jsonify()` 的视图函数
- 注册: `src/web/routes.py` 的 `init_web()` 中添加 `app.add_url_rule(path, endpoint, view_func, methods=[...])`
- Pattern: 参考 `api_run_pipeline()` 和 `api_delete_article()`

**新增发布渠道:**
- 实现文件: `src/publisher/` 目录下新建 `.py` 文件
- RSS 类: 参考 `src/publisher/rss_feed.py`（Flask app factory 模式）
- 自动化类: 参考 `src/publisher/toutiao_publisher.py`（Playwright 模式）

**新增数据库表/方法:**
- Schema: `src/storage/database.py` 的 `_init_tables()` 中添加 CREATE TABLE / INDEX
- CRUD: 在 `Database` 类中添加新的公开方法
- 注意: 避免在 routes.py 中直接执行 SQL，所有数据库操作通过 `Database` 类方法

## Special Directories

**`data/`:**
- Purpose: 运行时数据（数据库、cookie）
- Generated: Yes（运行时自动创建）
- Committed: No（在 `.gitignore` 中）
- Contents: `newsagent.db`（SQLite），`cookies/toutiao_state.json`（Playwright 状态）

**`venv/`:**
- Purpose: Python 虚拟环境
- Generated: Yes
- Committed: No（在 `.gitignore` 中）

**`__pycache__/`:**
- Purpose: Python 字节码缓存
- Generated: Yes（多个 `__pycache__` 目录分布在 `src/`, `config/`, 根目录）
- Committed: No（在 `.gitignore` 中）

**`src/web/static/`:**
- Purpose: 静态资源（CSS, JS, images）
- Current: 空目录 -- 所有样式和脚本目前内联在 `base.html` 中
- Potential use: 提取内联 CSS/JS 到独立文件以提高可维护性

---

*Structure analysis: 2026/05/09*
