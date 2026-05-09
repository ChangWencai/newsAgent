# Phase 1: Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-09
**Phase:** 1-Foundation
**Areas discussed:** 依赖注入方式, 数据库层设计, 测试策略与目录结构, 生产部署配置

---

## 依赖注入方式

| Option | Description | Selected |
|--------|-------------|----------|
| Blueprint 构造函数注入 | 在 Blueprint 的工厂函数中传入 db 实例，路由函数通过 closure 捕获 db | ✓ |
| Flask g 对象 | 每次请求通过 before_request 钩子将 db 注入 g.db | |
| app.config 注入 | 将 db 实例存入 app.config['db']，路由函数从 current_app.config 取 | |

**User's choice:** Blueprint 构造函数注入 (Recommended)

### Blueprint 拆分

| Option | Description | Selected |
|--------|-------------|----------|
| 2 个 Blueprint | web_bp (视图) + api_bp (API) | ✓ |
| 3 个 Blueprint | web_bp + api_bp + settings_bp | |
| 1 个 Blueprint | 所有路由放一个 web Blueprint | |

**User's choice:** 2 个 Blueprint (Recommended)

### RSS 路由处理

| Option | Description | Selected |
|--------|-------------|----------|
| 并入 api Blueprint | /rss 和 /health 路由合并到 api Blueprint 中 | ✓ |
| 保持独立 app | rss_feed 保持 create_rss_app() 独立模式 | |
| 创建 rss Blueprint | 专门的 rss Blueprint | |

**User's choice:** 并入 api Blueprint (Recommended)

### Scheduler 注入

| Option | Description | Selected |
|--------|-------------|----------|
| 构造函数注入到 scheduler | create_pipeline(crawler, writer, db) 返回可调用函数 | ✓ |
| 传 db 到 run_pipeline，内部还是 new | 保持 run_pipeline(db) 签名不变 | |
| 全局依赖容器 | 创建简单的 DI 容器 | |

**User's choice:** 构造函数注入到 scheduler (Recommended)

### publish.py 处理

| Option | Description | Selected |
|--------|-------------|----------|
| 保留独立入口 | publish.py 继续作为独立脚本，内部也用构造函数注入 | ✓ |
| 合并到 main.py | publish 功能作为 main.py 的子命令 | |
| 保留现状 | publish.py 不在重构范围内 | |

**User's choice:** 保留独立入口 (Recommended)

### 模块文件结构

| Option | Description | Selected |
|--------|-------------|----------|
| src/web/routes/__init__.py 导出 | src/web/routes/ 目录，__init__.py 导出两个 Blueprint 工厂函数 | ✓ |
| web_routes.py + api_routes.py | routes.py 拆成两个平行文件 | |
| 一个文件两个 Blueprint | 不拆文件，一个文件内定义两个 Blueprint | |

**User's choice:** src/web/routes/__init__.py 导出 (Recommended)

---

## 数据库层设计

### ORM 选择

| Option | Description | Selected |
|--------|-------------|----------|
| 补齐 Database 类 | 继续用原生 sqlite3，补齐所有缺失方法 | ✓ |
| 引入 SQLAlchemy ORM | 用 SQLAlchemy 定义模型和查询 | |
| 混合方案 | 简单查询用 Database 类，复杂查询用 SQLAlchemy | |

**User's choice:** 补齐 Database 类 (Recommended)

### 连接管理

| Option | Description | Selected |
|--------|-------------|----------|
| 单连接 + threading.Lock | Database 实例持有单一 SQLite 连接，写操作用 Lock 序列化 | ✓ |
| 单连接 + WAL 模式 | 单一连接 + PRAGMA journal_mode=WAL | |
| 连接池 (每次新建 + 超时重试) | 保持每次新建连接，但加 busy_timeout 和重试逻辑 | |

**User's choice:** 单连接 + threading.Lock (Recommended)

### DB 方法清单

| Option | Description | Selected |
|--------|-------------|----------|
| 全部补齐 | Database 类新增所有缺失方法，routes.py 零 SQL | ✓ |
| 只补齐被直接 SQL 调用的 | 只补齐当前 routes.py 绕过 Database 的那些查询 | |
| 只补齐 delete 和统计查询 | 只补缺失最明显的 | |

**User's choice:** 全部补齐 (Recommended)

---

## 测试策略与目录结构

### 测试目录

| Option | Description | Selected |
|--------|-------------|----------|
| tests/ 顶层目录 | tests/test_crawler.py 等，pytest 标准布局 | ✓ |
| tests/ 镜像 src 结构 | tests/crawler/test_tophub.py 等 | |
| src/ 内同目录 | src/crawler/test_tophub.py | |

**User's choice:** tests/ 顶层目录 (Recommended)

### DB Fixture

| Option | Description | Selected |
|--------|-------------|----------|
| 内存 SQLite + conftest.py | :memory: 创建 SQLite 连接，初始化表结构，测试后清理 | ✓ |
| 临时文件 SQLite | 每次测试用 tempfile 创建 .db 文件 | |
| mock Database 对象 | 单元测试用 MagicMock 替代 Database | |

**User's choice:** 内存 SQLite + conftest.py 共享 fixture (Recommended)

### Mock 策略

| Option | Description | Selected |
|--------|-------------|----------|
| 分层测试 | 单元测试 mock，集成测试用真实依赖 | ✓ |
| 全部 mock | 所有测试都 mock 外部依赖 | |
| 全部真实调用 | 测试用真实 API 和浏览器 | |

**User's choice:** 分层测试 (Recommended)

### 测试优先级

| Option | Description | Selected |
|--------|-------------|----------|
| Database → routes → pipeline | 先测核心重构模块 | ✓ |
| 从简单到难 | styles.py → crawler → database → routes → pipeline | |
| 只测关键路径 | 只写 pipeline 和 database 的集成测试 | |

**User's choice:** Database → routes → pipeline (Recommended)

---

## 生产部署配置

### Gunicorn 配置

| Option | Description | Selected |
|--------|-------------|----------|
| 单 worker + 多线程 | gunicorn -w 1 --threads 4，避免 scheduler 重复调度 | ✓ |
| 单 worker 单线程 | gunicorn -w 1 | |
| 多 worker + 外部 scheduler | gunicorn -w 2，APScheduler 移到独立进程 | |

**User's choice:** 单 worker + 多线程 (Recommended)

### Dev/Prod 切换

| Option | Description | Selected |
|--------|-------------|----------|
| main.py 兼容两种模式 | if __name__ == '__main__' 用于开发，create_app() 给 gunicorn | ✓ |
| 分离启动脚本 | main.py 只提供 create_app()，开发用 dev.py | |
| FLASK_DEBUG 环境变量 | 通过环境变量控制 dev/prod 模式 | |

**User's choice:** main.py 兼容两种模式 (Recommended)

### 配置方式

| Option | Description | Selected |
|--------|-------------|----------|
| gunicorn.conf.py 配置文件 | 集中配置参数，命令行只需 gunicorn -c gunicorn.conf.py | ✓ |
| 命令行参数 | 在启动脚本或 README 中记录 | |
| systemd service + 环境变量 | systemd unit 文件中配置 | |

**User's choice:** gunicorn.conf.py 配置文件 (Recommended)

### 优雅关闭

| Option | Description | Selected |
|--------|-------------|----------|
| atexit + signal handler | 注册 atexit handler 调用 scheduler.shutdown(wait=True) | ✓ |
| 只用 gunicorn 信号 | 依赖 gunicorn 的 worker 退出机制 | |
| 不做处理 | 当前规模下可接受 | |

**User's choice:** atexit + signal handler (Recommended)

---

## Claude's Discretion

无 — 所有决策均由用户直接选择。

## Deferred Ideas

无 — 讨论始终在 Phase 1 范围内。
