# Phase 3: Multi-Source - Research

**Researched:** 2026-05-09
**Domain:** 多平台热点聚合 — Python Protocol, dataclass, 爬虫注册, DailyHotApi 集成, 跨平台去重
**Confidence:** HIGH (核心架构) / MEDIUM (DailyHotApi 响应格式)

## Summary

Phase 3 将热点来源从单一抖音扩展到微博、知乎、百度四个平台。核心改动涉及 5 层：(1) `HotTopic` frozen dataclass 统一数据结构，(2) `typing.Protocol` 定义爬虫接口，(3) 模块级注册列表实现自动发现，(4) DailyHotApi HTTP 适配器，(5) `difflib.SequenceMatcher` 跨平台去重。

现有 `DouyinCrawler.get_hot_list()` 返回 `List[Dict]`，需要升级为 `list[HotTopic]`。Pipeline 从单一爬虫调用改为遍历注册列表，`create_pipeline` 签名从 `(crawler, writer, db)` 变为 `(db)`。Database `hot_topics` 表需要添加 `source` 列用于区分数据来源。

**主要推荐:** 使用 typing.Protocol + 模块级 CRAWLERS 注册列表 + DailyHotApi Docker 部署 + difflib.SequenceMatcher 标准库去重。不引入任何新第三方依赖（除 docker-compose.yml）。

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| CrawlerProtocol + HotTopic 定义 | API / Backend | — | 纯 Python 类型定义，无运行时依赖 |
| 爬虫注册机制 | API / Backend | — | 模块级列表，启动时自动注册 |
| DailyHotApi 部署 | Docker / 容器编排 | — | 独立服务容器，通过 HTTP API 交互 |
| 微博/知乎/百度适配器 | API / Backend | — | HTTP 调用 DailyHotApi，返回 HotTopic |
| 跨平台去重 | API / Backend | Database / Storage | Pipeline 层比较标题，DB 层查重 |
| 多源调度 | API / Backend | — | Pipeline 遍历注册爬虫 |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| typing.Protocol | Python 3.13 标准库 | 爬虫接口定义 | 无需继承，duck typing 友好 |
| dataclasses | Python 3.13 标准库 | HotTopic 数据结构 | frozen=True 不可变，无第三方依赖 |
| difflib.SequenceMatcher | Python 3.13 标准库 | 标题相似度去重 | 零依赖，60% 阈值可调 |
| requests | >=2.31.0 (已有) | DailyHotApi HTTP 调用 | 项目已依赖，无需新增 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Docker Compose v2 | latest | DailyHotApi 服务编排 | Phase 5 生产部署完善时 |
| logging | Python 3.13 标准库 | 爬虫失败日志 | 每个爬虫独立 try/except |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| typing.Protocol | ABC 基类 | ABC 强制继承，Protocol 更灵活 |
| difflib.SequenceMatcher | sentence-transformers 语义向量 | 后者需 GPU + 重型依赖，延迟到 Phase 4 |
| DailyHotApi Docker | 直连各平台 API | 直连易被封 IP，DailyHotApi 做中间层 |
| 模块级 CRAWLERS 列表 | importlib 插件发现 | 后者过度工程，当前只需 4 个爬虫 |

**Installation:**
```bash
# 无需安装新依赖，全部使用标准库 + 已有依赖
# Docker 部署单独步骤：
docker compose up -d  # 启动 DailyHotApi 容器
```

## Architecture Patterns

### System Architecture Diagram

```
                    ┌─────────────────────────────────────────────┐
                    │              Pipeline (调度层)               │
                    │  get_registered_crawlers() → 遍历所有爬虫    │
                    └─────────┬──────────┬──────────┬──────────┬──┘
                              │          │          │          │
                    ┌─────────▼─┐  ┌─────▼────┐ ┌──▼──────┐ ┌▼──────────┐
                    │ Douyin    │  │ Weibo    │ │ Zhihu   │ │ Baidu     │
                    │ Crawler   │  │ Crawler  │ │ Crawler │ │ Crawler   │
                    │ (直连)    │  │(DailyHot)│ │(DailyHot)│ │(DailyHot) │
                    └─────┬─────┘  └────┬─────┘ └────┬────┘ └────┬──────┘
                          │             │            │           │
                          │        ┌────▼────────────▼───────────▼──┐
                          │        │     DailyHotApi (Docker)       │
                          │        │     端口 6688                   │
                          │        └─────────────────────────────────┘
                          │
              ┌───────────▼────────────────────────────┐
              │     Pipeline 聚合层                      │
              │  1. 收集所有爬虫返回 list[HotTopic]       │
              │  2. difflib.SequenceMatcher 跨平台去重    │
              │  3. 每组保留热度最高条目                   │
              └───────────┬────────────────────────────┘
                          │
              ┌───────────▼────────────────────────────┐
              │     Database 层                          │
              │  topic_exists(title) 基础去重             │
              │  find_similar_topics(title, 0.6) 查重    │
              │  insert_topic(title, url, hot_value,     │
              │               category, source)          │
              └──────────────────────────────────────────┘
```

### Recommended Project Structure
```
src/crawler/
├── __init__.py          # CRAWLERS 注册列表 + register_crawler() + get_registered_crawlers()
├── models.py            # HotTopic frozen dataclass
├── protocol.py          # CrawlerProtocol (typing.Protocol)
├── tophub.py            # DouyinCrawler (已存在，升级返回值)
├── dailyhot.py          # DailyHotApi 通用适配器（HTTP 封装）
├── weibo.py             # WeiboCrawler (source="weibo")
├── zhihu.py             # ZhihuCrawler (source="zhihu")
└── baidu.py             # BaiduCrawler (source="baidu")
```

### Pattern 1: Protocol + 注册模式
**What:** 使用 typing.Protocol 定义爬虫接口，模块级 CRAWLERS 列表自动注册
**When to use:** 开发新爬虫适配器时
**Example:**
```python
# src/crawler/protocol.py
from typing import Protocol
from dataclasses import dataclass

@dataclass(frozen=True)
class HotTopic:
    title: str
    url: str
    source: str
    hot_value: str = ""
    category: str = ""
    fetched_at: str = ""

class CrawlerProtocol(Protocol):
    def get_hot_list(self) -> list[HotTopic]: ...
```

```python
# src/crawler/__init__.py
from .protocol import CrawlerProtocol, HotTopic

CRAWLERS: list[CrawlerProtocol] = []

def register_crawler(crawler: CrawlerProtocol) -> None:
    CRAWLERS.append(crawler)

def get_registered_crawlers() -> list[CrawlerProtocol]:
    return list(CRAWLERS)
```

```python
# src/crawler/weibo.py — 注册示例
from src.crawler import register_crawler
from src.crawler.protocol import HotTopic

class WeiboCrawler:
    def get_hot_list(self) -> list[HotTopic]:
        # DailyHotApi 调用 + 字段映射
        ...

register_crawler(WeiboCrawler())
```

### Pattern 2: DailyHotApi 适配器基类
**What:** 抽取 DailyHotApi HTTP 调用逻辑到 `dailyhot.py`，各平台适配器复用
**When to use:** 微博、知乎、百度适配器都通过 DailyHotApi 获取数据时
**Example:**
```python
# src/crawler/dailyhot.py
import requests
from typing import Any

DAILYHOT_BASE_URL = "http://localhost:6688"

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

```python
# src/crawler/weibo.py — 使用示例
from src.crawler.dailyhot import fetch_dailyhot

class WeiboCrawler:
    def get_hot_list(self) -> list[HotTopic]:
        raw_items = fetch_dailyhot("weibo")
        return [
            HotTopic(
                title=item.get("title", ""),
                url=item.get("url", ""),
                source="weibo",
                hot_value=str(item.get("hot", "")),
                category="微博热搜",
            )
            for item in raw_items
        ]
```

### Pattern 3: 跨平台去重
**What:** Pipeline 收集所有 HotTopic 后，先调用 difflib.SequenceMatcher 做组内去重，再调用 DB 层 find_similar_topics 做历史去重
**When to use:** 每次 pipeline 执行时
**Example:**
```python
import difflib

def dedup_topics(topics: list[HotTopic], threshold: float = 0.6) -> list[HotTopic]:
    """组内去重：按标题相似度分组，每组保留 hot_value 最高的"""
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

### Anti-Patterns to Avoid
- **在爬虫内部去重:** 去重应在 Pipeline 层统一执行，各爬虫只负责抓取
- **用 category 做来源标识:** category 是"热搜榜"等榜单名称，source 才是平台标识，两者语义不同
- **requests 裸调用不设超时:** 必须 `timeout=15`，否则 DailyHotApi 容器未启动时会无限阻塞
- **Protocol 用 ABC 替代:** Protocol 是 duck typing，无需 import 继承链，更符合 Python 风格

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 爬虫接口约束 | 自定义 ABC 基类 | typing.Protocol | 标准库，无需继承 |
| 数据结构 | TypedDict / dict 扩展 | @dataclass(frozen=True) | 类型安全 + 不可变 |
| 标题相似度 | 自写文本匹配算法 | difflib.SequenceMatcher | 标准库，稳定可靠 |
| HTTP 客户端 | socket 直连 | requests (已有依赖) | 连接池、超时、异常处理完善 |

**关键洞察:** 本阶段不引入任何新第三方依赖。所有功能均可通过 Python 3.13 标准库 + 已有依赖完成。

## Common Pitfalls

### Pitfall 1: Pipeline 签名变更导致 main.py 崩溃
**What goes wrong:** `create_pipeline(db)` 替换了 `create_pipeline(crawler, writer, db)`，但 `main.py` 的 `run_pipeline(db)` 仍创建旧的依赖注入
**Why it happens:** 函数签名变更未同步到所有调用点
**How to avoid:** 更新 `run_pipeline(db)` 内部不再创建 `DouyinCrawler()` 和 `ArticleGenerator()`，改为依赖注册列表；同时保持向后兼容（run_once 模式仍需工作）
**Warning signs:** 启动时报 TypeError 参数数量不匹配

### Pitfall 2: DailyHotApi 容器未启动时 pipeline 阻塞
**What goes wrong:** WeiboCrawler/ZhihuCrawler/BaiduCrawler 调用 DailyHotApi HTTP，容器未启动则 requests 默认阻塞
**Why it happens:** 没有设置 timeout 或没有处理 ConnectionError
**How to avoid:** `fetch_dailyhot()` 始终设置 `timeout=15`，抛出的异常由 pipeline 的 per-crawler try/except 捕获，不影响其他爬虫
**Warning signs:** pipeline 执行时间异常长，日志无输出

### Pitfall 3: 去重阈值过低导致不同热点被合并
**What goes wrong:** 0.6 阈值对某些短标题误匹配（如 "小米汽车" vs "小米手机"）
**Why it happens:** SequenceMatcher 是字符级比较，短字符串容易误判
**How to avoid:** 在测试中覆盖短标题边界 case；如发现误匹配可调整阈值至 0.7
**Warning signs:** 不同平台热点被错误跳过

### Pitfall 4: 数据库 schema 未添加 source 列
**What goes wrong:** HotTopic 有 `source` 字段但 `hot_topics` 表无对应列，insert 失败
**Why it happens:** `_init_tables()` 的 CREATE TABLE IF NOT EXISTS 不会修改已存在的表
**How to avoid:** 添加 `ALTER TABLE hot_topics ADD COLUMN source TEXT DEFAULT ''` 到 `_init_tables()`，或在 `insert_topic` 中加入 source 参数
**Warning signs:** INSERT 时报 OperationalError 列数不匹配

### Pitfall 5: 现有测试依赖旧 pipeline 签名
**What goes wrong:** `test_pipeline.py` 使用 `create_pipeline(mock_crawler, mock_writer, db)`，签名变更后全部失败
**Why it happens:** 测试直接调用工厂函数，未同步签名变更
**How to avoid:** 同步更新测试用例；或保持 `create_pipeline(db)` 为新签名，旧签名降级为兼容函数
**Warning signs:** pytest 执行报错 TypeError

## Code Examples

### 迁移 DouyinCrawler 到新协议
```python
# src/crawler/tophub.py — 修改后
from src.crawler.protocol import HotTopic

class DouyinCrawler:
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
```

### 新多源 Pipeline
```python
# src/scheduler/jobs.py — 修改后关键部分
from src.crawler import get_registered_crawlers
from src.crawler.protocol import HotTopic

def create_pipeline(db):
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

        # 组内去重
        unique_topics = dedup_topics(all_topics)

        # DB 历史去重 + 插入
        for topic in unique_topics:
            if not db.topic_exists(topic.title):
                topic_id = db.insert_topic(
                    title=topic.title,
                    url=topic.url,
                    hot_value=topic.hot_value,
                    category=topic.category,
                    source=topic.source,
                )
                # ... 后续文章生成流程
```

### Database.source 支持
```python
# src/storage/database.py — insert_topic 修改
def insert_topic(self, title, url="", hot_value="", category="", source=""):
    now = datetime.now().isoformat()
    cursor = self._execute_write(
        "INSERT INTO hot_topics (title, url, hot_value, category, source, fetched_at) VALUES (?, ?, ?, ?, ?, ?)",
        (title, url, hot_value, category, source, now)
    )
    return cursor.lastrowid
```

## State of the Art

| 旧方案 | 新方案 | 变更时间 | 影响 |
|--------|--------|---------|------|
| dict 返回值 | HotTopic frozen dataclass | Phase 3 | 类型安全，IDE 自动补全 |
| 无接口约束 | CrawlerProtocol Protocol | Phase 3 | 新爬虫必须实现 get_hot_list |
| 手动实例化爬虫 | 模块级 register_crawler() | Phase 3 | 新增爬虫自动被 pipeline 发现 |
| 单一 DouyinCrawler | 4 平台 + DailyHotApi | Phase 3 | 热点来源 4 倍扩大 |
| 精确 title 去重 | difflib.SequenceMatcher | Phase 3 | 跨平台相似事件识别 |

**Deprecated/outdated:**
- `create_pipeline(crawler, writer, db)` 三参签名 → 改为 `create_pipeline(db)`，爬虫从注册列表获取
- `DouyinCrawler` 直接实例化 → 通过 `register_crawler()` 自动注册

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | DailyHotApi 返回 JSON 格式为 `{"code":200,"data":[{"title","url","hot","desc"}]}` | DailyHotApi 适配器 | 适配器字段映射需调整；可在部署后用一个 curl 命令验证 |
| A2 | DailyHotApi Docker 容器可通过 `http://localhost:6688/{platform}` 访问 | Docker 部署 | 端口可能被占用，需 fallback 到 `DAILYHOT_BASE_URL` 配置项 |
| A3 | 0.6 相似度阈值对中文标题足够准确 | 去重策略 | 可能需要调整为 0.7；通过测试覆盖验证 |
| A4 | SQLite ALTER TABLE ADD COLUMN 在已有数据表上安全 | 数据库迁移 | 对空表无风险；已有数据表需确认 WAL 模式下无锁冲突 |

**如果此表为空:** 所有研究结论已验证或引用，无需用户确认。

## Open Questions

1. **DailyHotApi 响应格式确认**
   - 已知: 返回 code + data 数组，每个 item 有 title/url 字段
   - 不确定: hot 字段名（可能是 hot/hot_value/number），desc 字段是否存在
   - 建议: 部署 DailyHotApi 后用 `curl http://localhost:6688/weibo` 确认实际字段名；适配器代码使用 `.get()` 容错

2. **Database schema migration 策略**
   - 已知: `_init_tables()` 使用 `CREATE TABLE IF NOT EXISTS`，不会修改已有表
   - 不确定: 已有生产数据的表如何安全添加 source 列
   - 建议: `_init_tables()` 末尾添加 `ALTER TABLE hot_topics ADD COLUMN IF NOT EXISTS source TEXT DEFAULT ''`（SQLite 3.35.0+ 支持），或在 `__init__` 中做版本检测

3. **create_pipeline 签名向后兼容**
   - 已知: `main.py` 的 `run_pipeline(db)` 调用旧签名
   - 不确定: 是否需要保持旧签名用于特定场景
   - 建议: 直接改为 `create_pipeline(db)`，`run_pipeline(db)` 内部同步更新；旧签名无需保留

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.13 | 全部模块 | ✓ | 3.13 | — |
| requests | DailyHotApi HTTP 调用 | ✓ | >=2.31.0 | — |
| Docker | DailyHotApi 部署 | ✗ | — | 先用 `https://api-hot.imsyy.top/` 公共 API 测试，本地 Docker 延后 |
| difflib | 标题去重 | ✓ | 标准库 | — |
| typing.Protocol | 接口定义 | ✓ | 标准库 | — |

**Missing dependencies with no fallback:**
- 无

**Missing dependencies with fallback:**
- Docker: 可先使用公共 API `https://api-hot.imsyy.top/{platform}` 测试适配器逻辑，本地 Docker Compose 部署延后到 Phase 5

## Validation Architecture

> config.json 中 `workflow.nyquist_validation` 为 false，跳过详细验证架构分析。

### 现有测试基础设施
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | pyproject.toml [tool.pytest.ini_options] |
| Quick run command | `pytest tests/test_crawler*.py -x -v` |
| Full suite command | `pytest tests/ -x -v` |

### Phase 3 需要新增的测试
| 需求 ID | 行为 | 测试类型 | 命令 |
|---------|------|---------|------|
| MULTI-01 | CrawlerProtocol 类型检查 | 单元 | `pytest tests/test_protocol.py -x -v` |
| MULTI-02 | HotTopic frozen dataclass | 单元 | `pytest tests/test_models.py -x -v` |
| MULTI-03 | register_crawler / get_registered_crawlers | 单元 | `pytest tests/test_registry.py -x -v` |
| MULTI-05/06/07 | 各平台适配器字段映射 | 单元 (mock HTTP) | `pytest tests/test_adapters.py -x -v` |
| MULTI-08 | difflib 去重逻辑 | 单元 | `pytest tests/test_dedup.py -x -v` |
| MULTI-09 | 多源 pipeline 集成 | 集成 | `pytest tests/test_pipeline.py -x -v` |

### Wave 0 Gaps
- [ ] `tests/test_models.py` — HotTopic frozen 验证
- [ ] `tests/test_registry.py` — 注册机制测试
- [ ] `tests/test_adapters.py` — 各平台适配器 mock 测试
- [ ] `tests/test_dedup.py` — SequenceMatcher 去重测试
- [ ] `tests/test_protocol.py` — Protocol 兼容性测试

## Sources

### Primary (HIGH confidence)
- Python 3.13 typing.Protocol 文档 — 接口定义方式
- Python 3.13 dataclasses 文档 — frozen=True 不可变数据结构
- Python 3.13 difflib 文档 — SequenceMatcher ratio() 方法
- 项目现有代码 `src/crawler/tophub.py` — DouyinCrawler 实现参考
- 项目现有代码 `src/scheduler/jobs.py` — create_pipeline 工厂函数
- 项目现有代码 `src/storage/database.py` — insert_topic / topic_exists 接口
- CONTEXT.md — 19 个已确定的实现决策

### Secondary (MEDIUM confidence)
- DailyHotApi GitHub 页面 — 支持 30+ 平台，Docker 镜像 `imsyy/dailyhot-api:latest`，端口 6688
- DailyHotApi 在线 API `https://api-hot.imsyy.top/{platform}` — 公共实例可用于测试

### Tertiary (LOW confidence)
- DailyHotApi 响应 JSON 格式 (code/data/title/url/hot/desc) — 无法访问 API 验证，基于 GitHub 文档推断，部署后需实际确认

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — 全部使用标准库 + 已有依赖，零新依赖
- Architecture: HIGH — Protocol + 注册列表 + 去重是成熟 Python 模式
- Pitfalls: HIGH — 主要风险点（签名变更、DB schema）已明确识别
- DailyHotApi 集成: MEDIUM — 响应格式未实际验证，需部署后确认

**Research date:** 2026-05-09
**Valid until:** 2026-06-09 (30 天 — Phase 3 涉及的 API 和依赖变化不大)
