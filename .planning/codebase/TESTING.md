# Testing Patterns

**Analysis Date:** 2026-05-09

## Test Framework

**Runner:**
- 未检测到任何测试框架配置
- `requirements.txt` 中无 pytest、unittest extras 或其他测试依赖
- 无 `pyproject.toml`、`setup.cfg`、`tox.ini`、`pytest.ini` 或 `conftest.py`

**Assertion Library:**
- 未配置

**Run Commands:**
```bash
# 当前无可用测试命令
# 建议添加:
pytest                           # 运行全部测试
pytest --cov=src --cov-report=term-missing  # 覆盖率报告
pytest -x                        # 首次失败即停止
```

## Test File Organization

**Location:**
- 项目中不存在任何测试文件
- 无 `tests/` 目录
- 无 `test_*.py` 或 `*_test.py` 文件
- 无 `conftest.py`

**应有结构：**
```
newsAgent/
├── tests/
│   ├── conftest.py              # 共享 fixtures
│   ├── test_database.py         # src/storage/database.py 测试
│   ├── test_crawler.py          # src/crawler/tophub.py 测试
│   ├── test_generator.py        # src/writer/generator.py 测试
│   ├── test_styles.py           # src/writer/styles.py 测试
│   ├── test_routes.py           # src/web/routes.py 测试
│   ├── test_rss_feed.py         # src/publisher/rss_feed.py 测试
│   ├── test_scheduler.py        # src/scheduler/jobs.py 测试
│   └── test_publisher.py        # src/publisher/toutiao_publisher.py 测试
```

## Coverage

**Requirements:** 未设置任何覆盖率要求

**当前覆盖率：0%** — 全部 11 个源文件（~1023 行代码）均无测试覆盖

**按模块的测试优先级：**

| 模块 | 行数 | 优先级 | 原因 |
|------|------|--------|------|
| `src/storage/database.py` | 108 | 高 | 数据层核心逻辑，SQL 操作，易于单元测试 |
| `src/writer/styles.py` | 75 | 高 | 纯函数 `detect_style()`，零依赖，极易测试 |
| `src/writer/generator.py` | 103 | 高 | `_parse_response()` 是纯函数，可直接测试 |
| `src/publisher/rss_feed.py` | 62 | 高 | XML 生成函数 `_build_rss_xml()`、`_content_to_html()` 可直接断言 |
| `src/crawler/tophub.py` | 36 | 中 | HTTP 调用需 mock，但逻辑简单 |
| `src/scheduler/jobs.py` | 73 | 中 | 流水线逻辑，需 mock 依赖 |
| `src/web/routes.py` | 149 | 中 | Flask 路由，使用 test client 测试 |
| `src/publisher/toutiao_publisher.py` | 188 | 低 | Playwright 浏览器自动化，E2E 测试成本高 |

## Test Strategy Recommendation

### Phase 1: Pure Functions and Data Layer (No Mock Required)

**`src/writer/styles.py` 的 `detect_style()`：**
```python
# 可直接测试的纯函数
def detect_style(title):
    title_lower = title.lower()
    for style, keywords in STYLE_KEYWORDS.items():
        for kw in keywords:
            if kw in title:
                return style
    return "news"
```
- 测试用例：娱乐关键词返回 `entertainment`，社会关键词返回 `comment`，无匹配返回 `news`
- 注意：`title_lower` 变量被赋值但未使用（第 70 行），这是一个 bug

**`src/publisher/rss_feed.py` 的 `_content_to_html()` 和 `_format_rfc822()`：**
- 纯函数，输入输出确定，零依赖

**`src/writer/generator.py` 的 `_parse_response()`：**
- 可通过构造 `ArticleGenerator` 实例后直接调用测试
- 测试各种输入格式：标准格式、无标题兜底格式、空内容

### Phase 2: Modules Requiring Mock

**`src/storage/database.py`：**
- 使用内存数据库 `:memory:` 进行测试，无需 mock
- 测试所有 CRUD 操作

**`src/crawler/tophub.py`：**
- 使用 `unittest.mock.patch` mock `requests.get`
- 测试正常响应、HTTP 错误、JSON 解析异常

**`src/scheduler/jobs.py`：**
- mock `DouyinCrawler` 和 `ArticleGenerator`
- 测试去重逻辑、数量限制、异常处理

### Phase 3: Web Routes and E2E

**`src/web/routes.py`：**
- 使用 Flask test client：`app.test_client()`
- 测试所有路由的 HTTP 响应码和内容

**`src/publisher/toutiao_publisher.py`：**
- 适合 E2E 测试，使用 Playwright test 模式
- 成本高，优先级低

## Mocking

**Framework:** 应使用 `unittest.mock`（Python 标准库）

**需 mock 的依赖：**
```python
from unittest.mock import patch, MagicMock

@patch("src.crawler.tophub.requests.get")
def test_get_hot_list_success(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "data": {"word_list": [{"word": "test", "hot_value": 100}]}
    }
    mock_get.return_value.raise_for_status = MagicMock()
    # ...
```

**不应 mock：**
- `Database` 类 — 使用内存 SQLite 数据库 `:memory:` 替代 mock
- `detect_style()`、`_parse_response()`、`_content_to_html()` — 纯函数，直接测试

## Fixtures

**建议的 conftest.py：**
```python
import pytest
from src.storage.database import Database

@pytest.fixture
def db():
    """内存数据库，每次测试自动清理"""
    database = Database(":memory:")
    yield database

@pytest.fixture
def sample_topics():
    """标准测试热点数据"""
    return [
        {"title": "test_topic_1", "url": "http://example.com/1", "hot_value": "1000", "category": "test"},
        {"title": "test_topic_2", "url": "http://example.com/2", "hot_value": "800", "category": "test"},
    ]

@pytest.fixture
def sample_article():
    """标准测试文章数据"""
    return {
        "title": "test_article_title",
        "content": "test_article_content",
        "summary": "test_summary",
        "style": "news",
    }
```

## Known Code Quality Issues (Affecting Testability)

1. **Global state** (`src/web/routes.py:20`): `_db: Database = None` uses module-level global variable, making route functions impossible to test independently. Should use Flask `app.config` or `g` object.

2. **Direct SQL execution** (`src/web/routes.py:43-54`, `publish.py:64-69`): Routes and publish script call `conn.execute()` directly, bypassing the data access abstraction layer.

3. **No return type annotations**: All `Database` methods lack return types, increasing type inference cost during testing.

4. **Bug in `detect_style()`** (`src/writer/styles.py:70`): `title_lower = title.lower()` is assigned but never used. Line 73 uses `title` instead of `title_lower`, making matching case-sensitive when it appears intended to be case-insensitive.

5. **Duplicate constant definitions** (`src/writer/generator.py:10-11`): `MINIMAX_BASE_URL` and `MINIMAX_MODEL` are redefined at module level with different values than `config/settings.py` (URL path differs: `/anthropic` vs `/v1`).

## Implementation Steps to Introduce Testing

```bash
# 1. Add test dependencies to requirements.txt
echo "pytest>=7.0.0" >> requirements.txt
echo "pytest-cov>=4.0.0" >> requirements.txt

# 2. Create test directory and conftest
mkdir -p tests
# Write tests/conftest.py

# 3. Start with simplest pure functions
# Write tests/test_styles.py
# Write tests/test_rss_feed.py

# 4. Add database tests
# Write tests/test_database.py

# 5. Run tests
python -m pytest tests/ -v --cov=src --cov-report=term-missing
```

---

*Testing analysis: 2026-05-09*
