# Coding Conventions

**Analysis Date:** 2026-05-09

## Naming Patterns

**Files:**
- 模块文件使用 `snake_case.py`，例如 `tophub.py`, `rss_feed.py`, `toutiao_publisher.py`
- 入口文件位于项目根目录：`main.py`, `publish.py`
- 配置目录使用 `config/`，数据目录使用 `data/`

**Functions:**
- 公共方法使用 `snake_case`：`get_hot_list()`, `generate_article()`, `insert_topic()`
- 私有方法使用 `_` 前缀：`_get_conn()`, `_init_tables()`, `_parse_response()`, `_create_context()`
- 异步方法同样使用 `snake_case`：`publish()`, `_check_login()`, `_wait_login()`

**Variables:**
- 常量使用 `UPPER_SNAKE_CASE`：`PUBLISH_URL`, `LOGIN_URL`, `COOKIE_DIR`, `MINIMAX_BASE_URL`
- 模块级配置变量使用 `UPPER_SNAKE_CASE`：`TOPHUB_API_KEY`, `DB_PATH`, `RSS_HOST`
- 局部变量使用 `snake_case`：`article_title`, `hot_value`, `style_config`

**Types:**
- 未定义自定义类型或 dataclass
- 所有数据通过 `dict` 传递（无 TypedDict 或 Pydantic model）

## Code Style

**Formatting:**
- 未检测到格式化工具配置（无 black、autopep8、ruff format）
- 无 `pyproject.toml`、`setup.cfg`、`.flake8`、`ruff.toml` 等配置文件
- 缩进使用 4 空格（标准 Python）
- 字符串使用双引号为主，部分地方混用单引号

**Linting:**
- 未检测到任何 linting 工具配置
- 无 flake8、pylint、ruff、mypy、pyright 配置
- `requirements.txt` 中无开发依赖（linting/formatting/testing 包）

**行长度：**
- 大部分行保持在 100 字符以内
- 部分 Jinja2 system prompt 字符串超过 100 字符（`src/writer/styles.py`）

## Import Organization

**顺序（大部分文件遵循）：**
1. 标准库：`import os`, `import logging`, `import asyncio`, `import argparse`
2. 第三方库：`from flask import ...`, `import requests`, `import anthropic`
3. 项目内部：`from config.settings import ...`, `from src.storage.database import ...`

**问题：**
- `publish.py` 第 28 行和第 79 行：`from playwright.async_api import async_playwright` 为延迟导入（函数内部），与模块顶部导入不一致
- `src/writer/generator.py` 第 10-11 行：模块级重新定义 `MINIMAX_BASE_URL` 和 `MINIMAX_MODEL`，与 `config/settings.py` 中的同名常量冲突
- 无 path alias 配置

**示例（`src/scheduler/jobs.py`）：**
```python
import logging                                          # 标准库
from config.settings import MAX_TOPICS_PER_RUN, ...     # 项目内部
from src.crawler.tophub import DouyinCrawler            # 项目内部
from src.writer.generator import ArticleGenerator       # 项目内部
```

## Error Handling

**模式：**
- 使用 `logging` 模块记录错误，无 `print()` 调试语句
- 普遍使用 `except Exception as e` 宽泛捕获（见所有模块）
- 部分位置静默吞掉异常：`src/publisher/toutiao_publisher.py:72` 和 `:144`
- 网络请求有 `raise_for_status()` 检查（`src/crawler/tophub.py:20`）
- API 路由返回统一 JSON 格式：`{"success": bool, "message": str}`（`src/web/routes.py:118-121`）

**不一致之处：**
- `logger.error()` 使用 `%s` 格式化：`logger.error("获取抖音热榜失败: %s", e)`（`src/crawler/tophub.py:35`）
- `logger.info()` 使用 f-string：`logger.info(f"开始发布文章: {title[:30]}...")`（`src/publisher/toutiao_publisher.py:100`）
- 应统一使用 `%s` 格式化（延迟求值，性能更优）

## Logging

**框架：** Python 内置 `logging` 模块

**配置（所有入口文件）：**
```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
```

**使用模式：**
- 每个模块顶部创建 `logger = logging.getLogger(__name__)`
- 日志级别使用：`logger.info()` 用于流程跟踪，`logger.warning()` 用于非致命问题，`logger.error()` 用于错误
- `logger.exception()` 仅在 `src/web/routes.py:120` 使用（包含 traceback）

## Comments

**语言：** 中文注释和文档字符串

**docstring 使用：**
- 模块级 docstring：所有模块都有（如 `"""SQLite 数据存储模块"""`）
- 类级 docstring：仅 `ToutiaoPublisher` 有（`src/publisher/toutiao_publisher.py:19`）
- 方法级 docstring：不一致
  - 有：`generate_article()`（含 Args/Returns）、`publish()`（含 Args）、`login_only()`、`publish_articles()`
  - 无：`Database` 类的大部分方法、`DouyinCrawler.get_hot_list()`、路由处理函数中部分有简短 docstring

**格式：**
- 无 Google/NumPy 风格的统一 docstring 格式
- `generate_article()` 使用类 Google 风格的 Args/Returns（`src/writer/generator.py:23-31`）

## Function Design

**大小：**
- 大部分函数 < 40 行
- 最长函数：`ToutiaoPublisher._do_publish()` 约 50 行（`src/publisher/toutiao_publisher.py:98-149`）
- `publish_articles()` 约 47 行（`publish.py:57-104`）

**参数：**
- 无类型注解的函数占多数
- `Database` 方法无返回类型注解
- 仅有两处类型注解：`db: Database`（`src/scheduler/jobs.py:12`, `src/web/routes.py:23`）和 `article_id: int`（`src/web/routes.py:101, 124`）

**返回值：**
- 成功/失败使用 `dict` 返回：`{"success": bool, "message": str}`（`ToutiaoPublisher`）
- 数据库方法返回 `dict` 或 `list[dict]`
- 生成器方法返回 `dict` 或 `None`

## Module Design

**Exports:**
- 无 `__all__` 定义
- `__init__.py` 文件均为空

**Barrel Files:**
- 未使用 barrel file 模式
- 导入直接引用具体模块：`from src.storage.database import Database`

## State Management

**全局状态：**
- `src/web/routes.py:20`：模块级 `_db: Database = None`（使用 `global` 关键字赋值）
- `config/settings.py`：模块级配置变量（惰性加载 `.env`）

**数据库连接：**
- 每次操作创建新连接（无连接池）：`Database._get_conn()` 每次调用返回新 `sqlite3.Connection`

## Recommended Improvements

1. **添加格式化/linting 工具**：配置 `ruff` + `black`，创建 `pyproject.toml`
2. **添加类型注解**：对所有函数签名添加 type hints，配置 `mypy`
3. **统一日志格式化**：全部使用 `logger.info("msg: %s", var)` 而非 f-string
4. **消除全局状态**：将 `_db` 改为 Flask `g` 对象或应用上下文
5. **添加 input validation**：对函数参数进行类型和值校验
6. **消除重复常量**：`generator.py` 中的 `MINIMAX_BASE_URL` 和 `MINIMAX_MODEL` 应只从 `config/settings.py` 导入
7. **统一 docstring 风格**：采用 Google 风格，覆盖所有公共方法

---

*Convention analysis: 2026-05-09*
