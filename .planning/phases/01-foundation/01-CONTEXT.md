# Phase 1: Foundation - Context

**Gathered:** 2026-05-09
**Status:** Ready for planning

<domain>
## Phase Boundary

消除模块级全局状态，建立可测试的分层架构基础。将当前 routes.py 中的模块级 `_db` 全局变量、路由中直接执行的 SQL、零测试覆盖、Werkzeug 开发服务器替换为 Application Factory + Blueprint 依赖注入 + Database 类完整封装 + pytest 测试基础设施 + gunicorn 生产部署。

</domain>

<decisions>
## Implementation Decisions

### 依赖注入方式
- **D-01:** 使用 Flask Blueprint 构造函数注入。`create_web_bp(db)` 和 `create_api_bp(db)` 工厂函数接收 Database 实例，路由函数通过 closure 捕获 db。测试时直接传 mock db 即可。
- **D-02:** 拆分为 2 个 Blueprint：`web_bp`（dashboard/topics/articles/detail/settings 视图路由）+ `api_bp`（run-pipeline/delete API + rss/health 路由合并）。
- **D-03:** 文件结构采用 `src/web/routes/__init__.py` 导出两个 Blueprint 工厂函数，`web.py` 和 `api.py` 分别定义路由。
- **D-04:** `run_pipeline(db)` 重构为构造函数注入：`create_pipeline(crawler, writer, db)` 返回可调用函数，`main.py` 组装依赖后传给 APScheduler。
- **D-05:** `publish.py` 保留独立 CLI 入口，内部也用构造函数注入组装依赖，与 web 服务解耦。

### 数据库层设计
- **D-06:** 继续使用原生 sqlite3，补齐 Database 类所有缺失方法（`get_dashboard_stats()`, `get_topics()`, `get_articles(filter)`, `get_article(id)`, `delete_article(id)`），routes.py 零 SQL。
- **D-07:** Database 实例持有单一 SQLite 连接（`check_same_thread=False`），写操作用 `threading.Lock` 序列化，叠加 `PRAGMA journal_mode=WAL` 支持并发读。
- **D-08:** `_get_conn()` 改为初始化时创建一次连接并缓存，不再每次操作新建/关闭。

### 测试策略与目录结构
- **D-09:** 测试文件放在顶层 `tests/` 目录（`tests/test_database.py`, `tests/test_routes.py`, `tests/test_pipeline.py` 等），pytest 标准布局。
- **D-10:** `conftest.py` 提供共享 db fixture：用 `:memory:` 创建 SQLite 连接，初始化表结构，测试后清理。快速、隔离、无文件残留。
- **D-11:** 分层测试策略：单元测试 mock 外部调用（MiniMax API、Playwright、HTTP），集成测试用真实依赖（`@pytest.mark.integration` 标记）。
- **D-12:** 测试覆盖优先级：Database → routes → pipeline。先测核心重构模块，建立安全网。

### 生产部署配置
- **D-13:** gunicorn 单 worker + 多线程：`gunicorn -w 1 --threads 4 main:create_app`。单进程避免 APScheduler 重复调度，多线程提升 Web 并发。
- **D-14:** `main.py` 兼容两种模式：`if __name__ == '__main__'` 块用于开发（Flask dev server），`create_app()` 工厂函数暴露给 gunicorn 直接导入。
- **D-15:** `gunicorn.conf.py` 配置文件集中配置 bind/workers/threads/log 等参数，命令行只需 `gunicorn -c gunicorn.conf.py main:create_app`。
- **D-16:** 注册 `atexit` handler 调用 `scheduler.shutdown(wait=True)`，同时捕获 SIGTERM/SIGINT，确保 pipeline 任务安全退出。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 项目文档
- `.planning/PROJECT.md` — 项目整体上下文、技术栈、已知问题
- `.planning/REQUIREMENTS.md` — FOUND-01~06 需求定义
- `.planning/STATE.md` — 当前进度和关键决策

### 代码库分析
- `.planning/codebase/ARCHITECTURE.md` — 系统架构图、组件职责、数据流、Anti-Patterns
- `.planning/codebase/STRUCTURE.md` — 目录布局、命名约定、在哪里添加新代码
- `.planning/codebase/CONCERNS.md` — 技术债务、安全问题、可靠性问题详细清单

### 核心源码（重构目标）
- `main.py` — 主入口，需重构为 Application Factory
- `src/web/routes.py` — 路由定义，需拆分为 Blueprint + 依赖注入
- `src/storage/database.py` — Database 类，需补齐方法 + 单连接 + Lock
- `src/scheduler/jobs.py` — pipeline 编排，需构造函数注入
- `config/settings.py` — 配置模块

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Database` 类已有 6 个公开方法和表初始化逻辑，直接在重构基础上扩展
- `ArticleGenerator` 构造函数已支持依赖注入（API key 参数），适合作为构造函数注入目标
- `DouyinCrawler` 无状态单方法类，天然适合构造函数注入
- Flask 模板系统（base.html + 6 个子模板）无需改动，Blueprint 切换对模板透明

### Established Patterns
- Pipeline 模式：抓取 -> 去重 -> 生成 -> 存储，4 步顺序编排，保持不变
- Repository 模式：Database 类封装所有数据访问，补齐缺失方法后 routes 零 SQL
- 模块级常量配置：`config/settings.py` 用大写蛇形常量导出，无需修改

### Integration Points
- `main.py` 创建 Database 并组装所有依赖（Blueprint 工厂、scheduler）
- `rss_feed.py` 的 `create_rss_app(db)` 需重构为 Blueprint 工厂函数并入 api_bp
- `publish.py` 独立创建 Database 和 ToutiaoPublisher，用相同注入模式
- APScheduler `BackgroundScheduler.add_job()` 需接收 `create_pipeline()` 返回的函数

</code_context>

<specifics>
## Specific Ideas

无特定样式或视觉参考要求。重构方向明确：消除全局状态、补齐分层、建立测试基础、生产部署。

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 1-Foundation*
*Context gathered: 2026-05-09*
