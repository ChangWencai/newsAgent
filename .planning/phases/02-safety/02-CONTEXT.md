# Phase 2: Safety - Context

**Gathered:** 2026-05-09
**Mode:** --auto (自动选择推荐方案)

<domain>
## Phase Boundary

发布行为安全可控，账号风险降到最低，内容合规有保障。涵盖 8 个安全子系统：Playwright 反检测、发布频率控制、Cookie 有效性检测与通知、API 密钥管理、Web UI 认证与 CSRF、敏感词过滤、选择器健壮性、重试机制。

Phase 1 已完成：Application Factory + Blueprint 依赖注入、Database 单连接+Lock+WAL、pytest 测试基础设施、gunicorn 生产部署。本阶段在此架构基础上实施安全加固。

</domain>

<decisions>
## Implementation Decisions

### 发布频率控制 (SAFE-02)
- **D-01:** 使用 SQLite 数据库记录发布频率。在 Database 类中添加 `can_publish(max_daily=5, min_interval_minutes=30)` 方法，pipeline 执行前调用检查，返回是否允许发布及下次可发布时间。
- **D-02:** 添加 `get_today_publish_count()` 和 `get_last_publish_time()` 方法查询当日发布数和最近发布时间。发布间隔 30-120 分钟随机化在调度层处理。
- **D-03:** APScheduler 调度配置调整为固定间隔触发，但 pipeline 内部通过 `can_publish()` 控制实际执行，超限自动跳过而非报错。

### Cookie 过期通知 (SAFE-03)
- **D-04:** `/health` 端点扩展为返回 `cookie_status` 字段（`valid` / `expired` / `missing`）。通过尝试访问头条发布页 URL 检测 cookie 有效性，不触发实际发布。
- **D-05:** Web UI 前端每 5 分钟轮询 `/health`，当 `cookie_status != "valid"` 时弹出持久化通知 banner，引导用户重新登录。
- **D-06:** Database 类添加 `set_cookie_status(status)` 和 `get_cookie_status()` 方法，publisher 每次操作后更新状态。

### 密钥管理 (SAFE-04)
- **D-07:** 继续使用 python-dotenv + `.env` 文件管理密钥（项目已有此模式）。添加 `.env.example` 模板文件到版本控制，列出所有必填和可选环境变量。
- **D-08:** `config/settings.py` 添加启动验证函数 `validate_config()`，检查必填项（`MINIMAX_API_KEY`, `TOPHUB_API_KEY`）是否存在，缺失时抛出明确错误。
- **D-09:** `ADMIN_PASSWORD` 作为新增环境变量，用于 Web UI 认证。

### Web UI 认证 (SAFE-05)
- **D-10:** 使用密码表单 + Flask session 认证方案。用户访问任何页面时检查 session 中的 `authenticated` 标记，未认证时重定向到 `/login` 页面。
- **D-11:** `/login` 页面显示密码输入表单，提交后与 `ADMIN_PASSWORD` 环境变量比对，匹配则设置 `session['authenticated'] = True`。
- **D-12:** 添加 `/logout` 路由清除 session。Blueprint 工厂函数中注册 `before_request` 钩子统一检查认证状态。
- **D-13:** 使用 Flask-WTF 的 `CSRFProtect` 扩展，自动为所有 POST 表单注入和验证 CSRF token。`/login` 表单也受 CSRF 保护。

### 敏感词过滤 (SAFE-06)
- **D-14:** 敏感词列表存储在 `data/sensitive_words.txt`，每行一个词/短语。启动时加载到内存，支持热重载（文件修改时间变化时重新加载）。
- **D-15:** 新建 `src/validator/sensitive.py` 模块，提供 `check_sensitive_words(text) -> list[str]` 函数，返回命中词列表。pipeline 在文章生成后、发布前调用。
- **D-16:** 命中敏感词时：文章标记为 `flagged` 状态（需新增数据库 status 值），Web UI 显示违规标记，不自动发布。用户可在界面手动审核后放行。

### 选择器健壮性 (SAFE-07)
- **D-17:** `toutiao_publisher.py` 中的 CSS class 选择器优先替换为 Playwright 语义定位器：`page.get_by_role()`, `page.get_by_text()`, `page.get_by_placeholder()` 等。
- **D-18:** 无法用语义定位器替代时（如头条特有组件），使用 `data-testid` 或 `aria-label` 作为备选。最后手段才保留 CSS class，并添加选择器不存在时的明确错误提示。
- **D-19:** 发布操作添加选择器超时后的错误诊断：截图保存 + 详细日志，便于定位头条 UI 变更。

### 重试机制 (SAFE-08)
- **D-20:** 使用 tenacity 库为爬虫和 AI API 调用添加指数退避重试：`retry=3`, `wait=exponential(1, 10)`，即首次等待 1 秒，最多等待 10 秒。
- **D-21:** 重试条件：网络错误（`requests.RequestException`）、HTTP 5xx、HTTP 429（限流）。不重试：HTTP 4xx（除 429）、认证错误、解析错误。
- **D-22:** `src/crawler/tophub.py` 的 `get_hot_list()` 和 `src/writer/generator.py` 的 `generate_article()` 都添加 `@retry` 装饰器。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 项目文档
- `.planning/PROJECT.md` — 项目整体上下文、技术栈、已知问题
- `.planning/REQUIREMENTS.md` — SAFE-01~08 需求定义
- `.planning/STATE.md` — 当前进度和关键决策

### Phase 1 产出（本阶段依赖）
- `.planning/phases/01-foundation/01-CONTEXT.md` — Phase 1 实现决策（DI 方式、数据库设计、测试策略）
- `src/storage/database.py` — 已重构的 Database 类（单连接+Lock+WAL+11 个方法）
- `src/web/routes/web.py` — Blueprint 工厂 `create_web_bp(db)`
- `src/web/routes/api.py` — Blueprint 工厂 `create_api_bp(db)`
- `main.py` — Application Factory `create_app(db=None, db_path=None)`
- `tests/conftest.py` — 共享 db/app/client fixtures

### 核心源码（本阶段修改目标）
- `src/publisher/toutiao_publisher.py` — Playwright 发布模块，选择器和 cookie 管理
- `src/crawler/tophub.py` — 热点爬虫，需添加重试
- `src/writer/generator.py` — AI 文章生成，需添加重试
- `src/scheduler/jobs.py` — pipeline 编排，需添加频率控制
- `config/settings.py` — 配置模块，需添加验证
- `src/web/routes/api.py` — API 路由，/health 端点需扩展

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Database 类已补齐 11 个公开方法，可直接扩展 `can_publish()`、`get_today_publish_count()` 等频率控制方法
- Blueprint 工厂模式已建立，`before_request` 钩子可直接添加到 `create_web_bp(db)`
- `config/settings.py` 已使用 `os.getenv()` 模式，添加 `ADMIN_PASSWORD` 一行即可
- pytest 测试基础设施完备，conftest.py 提供 db/app/client fixtures
- `toutiao_publisher.py` 中的 `_check_login()` 可扩展为 cookie 有效性检测

### Established Patterns
- 工厂函数注入：`create_web_bp(db)`, `create_api_bp(db)`, `create_pipeline(crawler, writer, db)`
- Database 方法模式：`_execute_read` / `_execute_write` 统一封装
- 常量配置：`config/settings.py` 大写蛇形常量，`os.getenv()` 带默认值

### Integration Points
- `main.py` 已组装所有依赖，添加认证中间件和 CSRF 保护在此处注册
- `/health` 端点当前在 `api.py` 中，扩展 cookie 状态检查
- APScheduler 调度逻辑在 `main.py` 的 `main()` 函数中，频率控制在 pipeline 内部

</code_context>

<specifics>
## Specific Ideas

- 敏感词过滤作为独立模块，便于后续扩展（如接入在线敏感词 API）
- Cookie 状态检测避免频繁访问头条，仅在 health 检查时轻量探测
- 重试装饰器统一封装，爬虫和 AI 调用使用相同配置
- 选择器迁移优先级：发布流程 > 登录流程 > 封面选择

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 2-Safety*
*Context gathered: 2026-05-09 (auto mode)*
