# Phase 3: Multi-Source - Pattern Map

**Mapped:** 2026-05-09
**Files analyzed:** 17 (10 new, 7 modified)
**Analogs found:** 12 / 17

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/crawler/__init__.py` | registry | request-response | (无 — 项目无注册模式先例) | no-analog |
| `src/crawler/models.py` | model | CRUD | (无 — 项目无 dataclass 先例) | no-analog |
| `src/crawler/protocol.py` | model | CRUD | (无 — 项目无 Protocol 先例) | no-analog |
| `src/crawler/dailyhot.py` | service | request-response | `src/crawler/tophub.py` | role-match |
| `src/crawler/weibo.py` | service | request-response | `src/crawler/tophub.py` | exact |
| `src/crawler/zhihu.py` | service | request-response | `src/crawler/tophub.py` | exact |
| `src/crawler/baidu.py` | service | request-response | `src/crawler/tophub.py` | exact |
| `src/crawler/tophub.py` (修改) | service | request-response | 自身 — 升级返回值类型 | self |
| `src/scheduler/jobs.py` (修改) | controller | CRUD | 自身 — 多源遍历改造 | self |
| `src/storage/database.py` (修改) | model | CRUD | 自身 — 添加 source 列 | self |
| `config/settings.py` (修改) | config | — | 自身 — 添加常量 | self |
| `docker-compose.yml` | config | — | (无 — 项目无 Docker 配置) | no-analog |
| `main.py` (修改) | controller | request-response | 自身 — run_pipeline 签名更新 | self |
| `tests/test_models.py` | test | — | `tests/test_database.py` | role-match |
| `tests/test_registry.py` | test | — | `tests/test_database.py` | role-match |
| `tests/test_adapters.py` | test | — | `tests/test_pipeline.py` | role-match |
| `tests/test_dedup.py` | test | — | `tests/test_pipeline.py` | role-match |

## Pattern Assignments

### `src/crawler/__init__.py` (registry)

**Analog:** 无直接类比。参考 `config/settings.py` 的模块级常量模式 + `src/web/routes/__init__.py` 的导出模式。

**核心模式** — 模块级列表 + 注册/查询函数:
```python
from src.crawler.protocol import CrawlerProtocol

CRAWLERS: list[CrawlerProtocol] = []

def register_crawler(crawler: CrawlerProtocol) -> None:
    CRAWLERS.append(crawler)

def get_registered_crawlers() -> list[CrawlerProtocol]:
    return list(CRAWLERS)
```

**导入约定** (参考 `src/scheduler/jobs.py` lines 1-10):
```python
from src.crawler.protocol import CrawlerProtocol
```

---

### `src/crawler/models.py` (model)

**Analog:** 无直接类比。遵循 `rules/python/coding-style.md` 的 frozen dataclass 模式。

**核心模式** — frozen dataclass:
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class HotTopic:
    title: str
    url: str
    source: str
    hot_value: str = ""
    category: str = ""
    fetched_at: str = ""
```

**不可变性要求** (参考 `rules/common/coding-style.md`):
- `frozen=True` 保证不可变，符合项目 immutability 原则
- 所有字段使用 `str` 类型，与现有 `insert_topic` 参数类型一致

---

### `src/crawler/protocol.py` (model)

**Analog:** 无直接类比。遵循 `rules/python/patterns.md` 的 Protocol 模式。

**核心模式** — typing.Protocol:
```python
from typing import Protocol
from src.crawler.models import HotTopic

class CrawlerProtocol(Protocol):
    def get_hot_list(self) -> list[HotTopic]: ...
```

**注意:** Protocol 不需要继承，只需方法签名匹配即可。各爬虫无需 `import CrawlerProtocol` 或显式继承。

---

### `src/crawler/dailyhot.py` (service, request-response)

**Analog:** `src/crawler/tophub.py` — 同为 HTTP 请求 + JSON 解析

**导入模式** (参考 `src/crawler/tophub.py` lines 1-8):
```python
import logging
import requests
from typing import Any

logger = logging.getLogger(__name__)
```

**HTTP 调用模式** (参考 `src/crawler/tophub.py` line 49):
```python
# 必须设置 timeout=15，避免容器未启动时无限阻塞
resp = requests.get(url, timeout=15)
resp.raise_for_status()
```

**配置读取** (参考 `config/settings.py` lines 9-12):
```python
from config.settings import DAILYHOT_BASE_URL
```

**核心模式** — 通用 DailyHotApi fetcher:
```python
def fetch_dailyhot(platform: str) -> list[dict[str, Any]]:
    """从 DailyHotApi 获取指定平台热榜，返回原始 data 列表"""
    resp = requests.get(
        f"{DAILYHOT_BASE_URL}/{platform}",
        timeout=15
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 200:
        raise ValueError(f"DailyHotApi 返回异常: code={data.get('code')}")
    return data.get("data", [])
```

---

### `src/crawler/weibo.py` (service, request-response)

**Analog:** `src/crawler/tophub.py` — 结构完全一致（HTTP 抓取 + 字段映射 + 返回列表）

**导入模式** (参考 `src/crawler/tophub.py` lines 1-8):
```python
import logging
from src.crawler.protocol import HotTopic
from src.crawler.dailyhot import fetch_dailyhot
from src.crawler import register_crawler

logger = logging.getLogger(__name__)
```

**核心模式** — 适配器 + 自动注册:
```python
class WeiboCrawler:
    def get_hot_list(self) -> list[HotTopic]:
        raw_items = fetch_dailyhot("weibo")
        results = []
        for item in raw_items:
            results.append(HotTopic(
                title=item.get("title", ""),
                url=item.get("url", ""),
                source="weibo",
                hot_value=str(item.get("hot", "")),
                category="微博热搜",
            ))
        return results

register_crawler(WeiboCrawler())
```

**错误处理:** 不在爬虫内 try/except，由 pipeline 层统一处理（参考 RESEARCH.md D-19）。

---

### `src/crawler/zhihu.py` (service, request-response)

**Analog:** `src/crawler/weibo.py` — 完全相同的模式，仅 platform 和 source 不同

**核心模式** — 与 weibo.py 结构一致:
```python
class ZhihuCrawler:
    def get_hot_list(self) -> list[HotTopic]:
        raw_items = fetch_dailyhot("zhihu")
        results = []
        for item in raw_items:
            results.append(HotTopic(
                title=item.get("title", ""),
                url=item.get("url", ""),
                source="zhihu",
                hot_value=str(item.get("hot", "")),
                category="知乎热榜",
            ))
        return results

register_crawler(ZhihuCrawler())
```

---

### `src/crawler/baidu.py` (service, request-response)

**Analog:** `src/crawler/weibo.py` — 完全相同的模式

**核心模式** — 与 weibo.py 结构一致:
```python
class BaiduCrawler:
    def get_hot_list(self) -> list[HotTopic]:
        raw_items = fetch_dailyhot("baidu")
        results = []
        for item in raw_items:
            results.append(HotTopic(
                title=item.get("title", ""),
                url=item.get("url", ""),
                source="baidu",
                hot_value=str(item.get("hot", "")),
                category="百度热搜",
            ))
        return results

register_crawler(BaiduCrawler())
```

---

### `src/crawler/tophub.py` (修改 — 升级返回值)

**Analog:** 自身 — 保留现有 retry 装饰器、HEADERS、URL 常量

**保留不变的部分** (lines 1-38):
- `_is_retryable()` 函数
- `crawl_retry` 装饰器
- `DOUYIN_HOT_URL`, `HEADERS` 常量

**修改部分** (lines 41-62) — 返回值从 `List[Dict]` 升级为 `list[HotTopic]`:

**新增导入:**
```python
from src.crawler.protocol import HotTopic
from src.crawler import register_crawler
```

**修改后的 get_hot_list:**
```python
class DouyinCrawler:
    @crawl_retry
    def get_hot_list(self) -> list[HotTopic]:
        resp = requests.get(DOUYIN_HOT_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        word_list = data.get("data", {}).get("word_list", [])
        results = []
        for item in word_list:
            results.append(HotTopic(
                title=item.get("word", ""),
                url=f"https://www.douyin.com/search/{item.get('word', '')}",
                source="douyin",
                hot_value=str(item.get("hot_value", 0)),
                category="抖音热搜",
            ))
        return results

# 文件末尾添加注册
register_crawler(DouyinCrawler())
```

---

### `src/scheduler/jobs.py` (修改 — 多源 pipeline)

**Analog:** 自身 — 保留 `_run_pipeline_inner` 的整体流程结构

**保留不变的部分:**
- `create_publisher(db)` 函数 (line 23-25)
- 频率控制检查逻辑 (line 31-34)
- 敏感词检查逻辑 (line 88-95)

**修改后的导入** (lines 1-10):
```python
import logging
import difflib
from config.settings import MAX_TOPICS_PER_RUN, DEFAULT_STYLE
from src.crawler import get_registered_crawlers
from src.crawler.protocol import HotTopic
from src.writer.generator import ArticleGenerator
from src.storage.database import Database
from src.publisher.toutiao_publisher import ToutiaoPublisher
from src.validator.sensitive import check_sensitive_words
```

**修改后的 create_pipeline** — 签名从三参数变为单参数:
```python
def create_pipeline(db):
    """创建多源 pipeline，从注册列表获取所有爬虫"""

    def pipeline():
        crawlers = get_registered_crawlers()
        all_topics: list[HotTopic] = []

        for crawler in crawlers:
            try:
                topics = crawler.get_hot_list()
                all_topics.extend(topics)
                logger.info("获取 %s: %d 条", crawler.__class__.__name__, len(topics))
            except Exception as e:
                logger.error("爬虫失败 [%s]: %s", crawler.__class__.__name__, e)

        if not all_topics:
            logger.warning("未获取到任何热点数据")
            return

        # 组内去重
        unique_topics = dedup_topics(all_topics)
        logger.info("去重后: %d 条（原始 %d 条）", len(unique_topics), len(all_topics))

        # DB 历史去重 + 限制数量
        new_topics = []
        for topic in unique_topics:
            if not db.topic_exists(topic.title):
                new_topics.append(topic)
            if len(new_topics) >= MAX_TOPICS_PER_RUN:
                break

        if not new_topics:
            logger.info("没有新的热点需要处理")
            return

        # 后续生成文章流程保持不变...
    return pipeline
```

**新增去重函数** (放在 create_pipeline 之前):
```python
def dedup_topics(topics: list[HotTopic], threshold: float = 0.6) -> list[HotTopic]:
    """按标题相似度分组，每组保留 hot_value 最高的"""
    if not topics:
        return []
    groups: list[list[HotTopic]] = []
    for topic in sorted(topics, key=lambda t: t.hot_value, reverse=True):
        matched = False
        for group in groups:
            if difflib.SequenceMatcher(None, topic.title, group[0].title).ratio() >= threshold:
                group.append(topic)
                matched = True
                break
        if not matched:
            groups.append([topic])
    return [g[0] for g in groups]
```

**修改后的 run_pipeline** — 适配新签名:
```python
def run_pipeline(db: Database):
    """兼容入口：通过注册列表获取爬虫"""
    pipeline = create_pipeline(db)
    pipeline()
```

---

### `src/storage/database.py` (修改 — 添加 source 支持)

**Analog:** 自身 — 保持 `_execute_write`/`_execute_read` 模式

**修改 `_init_tables`** (line 32-64) — hot_topics 表添加 source 列:
```sql
CREATE TABLE IF NOT EXISTS hot_topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    url TEXT,
    hot_value TEXT,
    category TEXT,
    source TEXT DEFAULT '',
    fetched_at TEXT NOT NULL,
    status TEXT DEFAULT 'pending'
);
```

**同时添加 ALTER TABLE** (处理已有数据库):
```python
def _init_tables(self):
    # ... 原有 CREATE TABLE IF NOT EXISTS ...

    # 添加 source 列（已有表兼容）
    try:
        self._execute_write("ALTER TABLE hot_topics ADD COLUMN source TEXT DEFAULT ''")
    except Exception:
        pass  # 列已存在时忽略
```

**修改 `insert_topic`** (line 73-79) — 添加 source 参数:
```python
def insert_topic(self, title, url="", hot_value="", category="", source=""):
    now = datetime.now().isoformat()
    cursor = self._execute_write(
        "INSERT INTO hot_topics (title, url, hot_value, category, source, fetched_at) VALUES (?, ?, ?, ?, ?, ?)",
        (title, url, hot_value, category, source, now)
    )
    return cursor.lastrowid
```

**新增 `find_similar_topics`** 方法:
```python
def find_similar_topics(self, title: str, threshold: float = 0.6) -> list[dict]:
    """查询已存在话题中与给定标题相似的记录"""
    import difflib
    rows = self._execute_read("SELECT * FROM hot_topics").fetchall()
    similar = []
    for row in rows:
        ratio = difflib.SequenceMatcher(None, title, row["title"]).ratio()
        if ratio >= threshold:
            similar.append(dict(row))
    return similar
```

---

### `config/settings.py` (修改 — 添加配置)

**Analog:** 自身 — 保持 `os.getenv()` 带默认值的模式

**新增常量** (放在 RSS 配置块之后):
```python
# DailyHotApi 服务
DAILYHOT_BASE_URL = os.getenv("DAILYHOT_BASE_URL", "https://api-hot.imsyy.top")
```

---

### `docker-compose.yml` (新文件)

**Analog:** 无直接类比。使用 DailyHotApi 官方 Docker 镜像。

**核心内容:**
```yaml
version: "3.8"
services:
  dailyhot:
    image: imsyy/dailyhot-api:latest
    container_name: dailyhot-api
    ports:
      - "6688:6688"
    restart: unless-stopped
```

---

### `main.py` (修改 — 适配新 pipeline)

**修改部分** (line 15, 64, 71-77):

**导入变更:**
```python
# 删除: from src.crawler.tophub import DouyinCrawler (不再直接导入)
# run_pipeline 签名不变: run_pipeline(db) 已兼容
```

**关键:** `run_pipeline(db)` 签名已兼容新设计，无需修改调用方式。但需确保爬虫模块在 `run_pipeline` 调用前已导入（触发 `register_crawler`）。

**添加爬虫导入触发注册** (在 main() 函数或 create_app 内):
```python
import src.crawler.tophub   # 触发 register_crawler(DouyinCrawler())
import src.crawler.weibo    # 触发 register_crawler(WeiboCrawler())
import src.crawler.zhihu    # 触发 register_crawler(ZhihuCrawler())
import src.crawler.baidu    # 触发 register_crawler(BaiduCrawler())
```

---

## Shared Patterns

### HTTP 请求模式
**Source:** `src/crawler/tophub.py` lines 26-32, 49
**Apply to:** `dailyhot.py`, `weibo.py`, `zhihu.py`, `baidu.py`
```python
# tenacity 重试（可选，dailyhot.py 可不加，由 pipeline 层 try/except 兜底）
resp = requests.get(url, timeout=15)  # 必须设置 timeout
resp.raise_for_status()
```

### 日志模式
**Source:** `src/crawler/tophub.py` line 8, `src/scheduler/jobs.py` line 11
**Apply to:** 所有新模块
```python
import logging
logger = logging.getLogger(__name__)
# 使用 logger.info/warning/error，不使用 print
```

### Pipeline 错误隔离
**Source:** `src/scheduler/jobs.py` lines 99-100
**Apply to:** 多源遍历中的 per-crawler try/except
```python
try:
    topics = crawler.get_hot_list()
    all_topics.extend(topics)
except Exception as e:
    logger.error("爬虫失败 [%s]: %s", crawler.__class__.__name__, e)
```

### 测试 Fixture 模式
**Source:** `tests/conftest.py`
**Apply to:** 所有新测试文件
```python
@pytest.fixture
def db():
    database = Database(':memory:')
    yield database
    database._conn.close()
```

### Mock 模式
**Source:** `tests/test_pipeline.py` lines 10-18
**Apply to:** 适配器测试、pipeline 测试
```python
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_crawler():
    return MagicMock()
```

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `src/crawler/__init__.py` | registry | — | 项目无注册模式先例，为全新模式 |
| `src/crawler/models.py` | model | — | 项目首次使用 dataclass，无先例 |
| `src/crawler/protocol.py` | model | — | 项目首次使用 Protocol，无先例 |
| `docker-compose.yml` | config | — | 项目无 Docker 配置先例 |
| `tests/test_dedup.py` | test | — | 去重逻辑为全新功能 |

以上无类比文件应参考 RESEARCH.md 中的 Code Examples 部分实现。

## Metadata

**Analog search scope:** `src/crawler/`, `src/scheduler/`, `src/storage/`, `src/web/`, `src/writer/`, `config/`, `tests/`
**Files scanned:** 15
**Pattern extraction date:** 2026-05-09
