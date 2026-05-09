# Architecture Research: Multi-Source AI Content Pipeline

**Project:** NewsAgent
**Researched:** 2026/05/09
**Confidence:** HIGH (based on complete codebase audit + official docs)

---

## 1. Plugin/Adapter Pattern for Multi-Source Crawling

### Recommended: Protocol + Registry Pattern

Use Python `Protocol` (structural subtyping) to define the crawler interface, and a simple registry dict for discovery. This is more Pythonic than abstract base classes and avoids the complexity of a full plugin framework.

**Why Protocol over ABC:**
- No inheritance required -- any class with `get_hot_list()` satisfies the interface
- Testable by duck typing -- mock crawlers trivially
- Aligns with `rules/python/patterns.md` recommendation for Protocol-based design

**Target structure:**

```
src/crawler/
    __init__.py          # CrawlerProtocol + registry
    base.py              # CrawlerProtocol definition, dataclasses
    douyin.py            # DouyinCrawler (extracted from tophub.py)
    weibo.py             # WeiboCrawler (new)
    zhihu.py             # ZhihuCrawler (new)
    baidu.py             # BaiduCrawler (new)
```

**Core interface:**

```python
from typing import Protocol, TypedDict

class HotTopic(TypedDict):
    title: str
    url: str
    hot_value: str
    category: str
    source: str          # "douyin", "weibo", etc.

class CrawlerProtocol(Protocol):
    source_name: str

    def get_hot_list(self) -> list[HotTopic]: ...
```

**Registry approach:** A module-level dict `CRAWLERS: dict[str, CrawlerProtocol]` populated at import time. The pipeline iterates `CRAWLERS.values()` instead of hardcoding `DouyinCrawler()`.

**Why not entry_points / pluginlib:**
- Overkill for 4 crawlers maintained in the same repo
- Entry points are for third-party extensibility; this is internal modularity
- Import-time registration is simpler and debuggable

**Confidence:** HIGH -- Protocol pattern is standard Python 3.12+ practice, and the codebase already uses TypedDict-like dicts in crawler output.

---

## 2. Queue-Based Architecture for Reliable Pipeline Processing

### Decision: Do NOT introduce Celery/RQ/Dramatiq yet

The current pipeline processes 5 topics every 6 hours. Introducing a full task queue (Redis broker, worker processes) would be massive over-engineering for this scale. The constraint document confirms: "单机部署，无需考虑水平扩展."

**Instead: In-process queue with retry via tenacity**

The immediate reliability problems are:
1. No retry on transient API failures (crawler HTTP, MiniMax API)
2. Silent topic loss on individual failure (logged but not retried)
3. No transaction wrapping (topic inserted, article generation fails = orphan)

**Phase-appropriate solution:**

| Concern | Solution | Complexity |
|---------|----------|------------|
| API retry | `tenacity` library with exponential backoff | Low |
| Failed topic tracking | Add `status='failed'` to hot_topics, retry on next run | Low |
| Transaction safety | Wrap topic+article insert in SQLite transaction | Low |
| Async web trigger | `threading.Thread` for background pipeline run | Low |

**When to introduce a real task queue:**
- If pipeline frequency increases beyond once per hour
- If multiple workers need to process tasks concurrently
- If pipeline steps need to be independently scalable
- If you need task result tracking across process restarts

At that point, **Dramatiq** (with Redis broker) is preferred over Celery because:
- Simpler API (decorator-based actors, less boilerplate)
- Built-in retry and middleware
- No need for Celery's complex configuration (result backends, task routes)
- Dramatiq officially supports Python 3.10+

**Confidence:** HIGH -- tenacity is well-documented, Dramatiq recommendation is based on official docs.

---

## 3. Separation of Concerns: Storage vs Business Logic vs Presentation

### Current Problems (from CONCERNS.md)

| Problem | Location | Severity |
|---------|----------|----------|
| Raw SQL in routes | `routes.py:43-54, 70-76, 82-98, 103-111, 127-135` | HIGH |
| Global mutable `_db` | `routes.py:20` | HIGH |
| Pipeline logic instantiates its own dependencies | `jobs.py:16-17` | MEDIUM |
| No service layer between routes and database | entire codebase | MEDIUM |

### Target Architecture: 3-Layer with Service Layer

```
Presentation Layer
  Flask routes (thin -- only HTTP concerns)
  Templates (display only, no business logic)
         |
         v
Service Layer (NEW)
  PipelineService: orchestrates crawl->write->store
  ArticleService: article CRUD + business rules
  TopicService: topic management + dedup logic
         |
         v
Data Access Layer
  Database class: ALL SQL lives here
  No raw SQL anywhere else
```

**Key rules:**
1. Routes do HTTP things only: parse request, call service, return response
2. Services contain business logic: pipeline orchestration, dedup rules, style detection
3. Database contains ALL SQL: routes must NEVER call `._get_conn()` directly

**Flask Application Factory pattern** (from Flask official docs) to eliminate global state:

```python
def create_app(db: Database) -> Flask:
    app = Flask(__name__)
    app.config['db'] = db           # store on app context
    app.register_blueprint(web_bp)  # routes use current_app.config['db']
    app.register_blueprint(api_bp)
    return app
```

Routes access the database via `current_app.config['db']` instead of module-level `_db`. This enables testing with injected mock databases.

**Confidence:** HIGH -- Flask application factory is the officially recommended pattern, and the 3-layer architecture is standard Python web practice.

---

## 4. Error Handling and Retry Strategies for External API Failures

### Current State: No retry anywhere

From CONCERNS.md: `src/crawler/tophub.py:34` catches bare `Exception` and returns `[]`. `src/writer/generator.py:59` catches bare `Exception` and returns `None`. Failed topics are silently skipped at `jobs.py:59,70`.

### Recommended Strategy with tenacity

**Retry tiers by error type:**

| Error Type | Retry? | Strategy |
|------------|--------|----------|
| Network timeout | YES | Exponential backoff, 3 attempts, 1s/2s/4s |
| HTTP 5xx | YES | Exponential backoff, 3 attempts |
| HTTP 429 (rate limit) | YES | Respect `Retry-After` header, max 2 retries |
| HTTP 4xx (non-429) | NO | Permanent error, log and skip |
| AI API error (5xx) | YES | Exponential backoff, 3 attempts |
| AI API error (4xx) | NO | Bad request, log and skip |
| Parse failure | NO | Log warning, skip topic |

**Implementation approach:**

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout)),
    reraise=True,
)
def fetch_with_retry(url: str, headers: dict) -> requests.Response:
    resp = requests.get(url, headers=headers, timeout=15)
    if resp.status_code >= 500:
        raise requests.HTTPError(f"Server error: {resp.status_code}")
    resp.raise_for_status()
    return resp
```

**Failed topic tracking:**

Add a `status` column flow to `hot_topics`:
- `pending` -> `generating` -> `done` (article created)
- `pending` -> `generating` -> `failed` (with `error_message` column)

On each pipeline run, retry topics with `status='failed'` before fetching new ones.

**Database transaction safety:**

Wrap topic insert + article insert in a single transaction:

```python
conn = db._get_conn()
try:
    conn.execute("INSERT INTO hot_topics ...")
    conn.execute("INSERT INTO articles ...")
    conn.commit()
except Exception:
    conn.rollback()
    raise
```

**Confidence:** HIGH -- tenacity retry patterns are from official documentation. Transaction pattern is standard SQLite practice.

---

## 5. Scalability Considerations

### Current Scale: Single process, 5 topics per 6 hours

This is the key constraint: the system does NOT need horizontal scaling. It needs **reliability** at its current scale.

| Concern | At Current Scale | At 10x Scale | At 100x Scale |
|---------|-----------------|-------------|---------------|
| Concurrency | SQLite WAL + serialized writes | SQLite with connection pooling | PostgreSQL |
| Web server | Flask dev server -> gunicorn | gunicorn with 4 workers | gunicorn + nginx |
| Pipeline execution | Background thread (APScheduler) | Thread pool | Dramatiq workers |
| Storage | SQLite (sufficient) | SQLite (still fine) | PostgreSQL |
| Deployment | Docker container | docker-compose | Kubernetes (unlikely needed) |

### Immediate Scalability Fixes (no new infrastructure)

**1. Replace Werkzeug dev server with gunicorn:**

```bash
pip install gunicorn
gunicorn -w 2 -b 0.0.0.0:5000 "main:create_app(db)"
```

This requires fixing the global `_db` state first (use application factory).

**2. SQLite concurrency with WAL mode:**

```python
conn = sqlite3.connect(db_path, check_same_thread=False)
conn.execute("PRAGMA journal_mode=WAL")
```

WAL mode allows concurrent reads while a write is in progress. For this workload (mostly reads from web UI, infrequent writes from pipeline), this is sufficient.

**3. Serialize writes through a threading.Lock:**

```python
import threading

class Database:
    def __init__(self, db_path):
        self._write_lock = threading.Lock()

    def insert_topic(self, ...):
        with self._write_lock:
            # ... insert logic
```

This prevents "database is locked" errors when APScheduler and Flask both try to write.

**4. Background pipeline trigger from web UI:**

Replace synchronous `run_pipeline(_db)` in the API route with a thread:

```python
import threading

def api_run_pipeline():
    thread = threading.Thread(target=run_pipeline, args=(db,))
    thread.start()
    return jsonify({"success": True, "message": "流水线已在后台启动"})
```

**When to migrate beyond SQLite:**
- If you need more than ~100 writes per second (not going to happen)
- If you need concurrent writes from multiple processes
- If you need full-text search (SQLite FTS5 extension may suffice)

**Confidence:** HIGH -- SQLite WAL mode and gunicorn are well-established solutions for this scale.

---

## 6. Suggested Build Order for Incremental Improvement

The build order is driven by dependencies: you cannot add multi-source crawlers without fixing the architecture, and you cannot fix the architecture without eliminating global state.

### Phase 1: Foundation -- Eliminate Global State and Raw SQL
**Goal:** Make the codebase testable and maintainable
**Blocks:** Everything else

| Task | Why First |
|------|-----------|
| Add missing methods to `Database` class (get_dashboard_stats, get_topics, delete_article, etc.) | Eliminates raw SQL in routes |
| Convert routes to Flask Blueprint | Eliminates global `_db` |
| Adopt Flask application factory (`create_app` pattern) | Enables DI for testing |
| Add `pyproject.toml` with pytest + ruff config | Foundation for tests and linting |
| Add `conftest.py` with fixtures (db, app, client) | Foundation for tests |

**Validation:** All routes use `Database` methods, zero raw SQL in routes, can run `pytest` successfully.

### Phase 2: Reliability -- Retry, Transactions, Error Handling
**Goal:** Pipeline does not silently lose data
**Depends on:** Phase 1 (needs testable code)

| Task | Why |
|------|-----|
| Add `tenacity` dependency, wrap crawler HTTP calls | Stop losing topics to transient failures |
| Add `tenacity` to AI generation calls | Stop losing articles to API hiccups |
| Wrap topic+article insert in SQLite transaction | Prevent orphaned topics |
| Add `failed` status tracking to hot_topics | Enable retry of failed topics |
| Add specific exception types (catch `requests.RequestError` not bare `Exception`) | Better error diagnosis |
| Add graceful shutdown (`atexit` handler for scheduler) | Prevent inconsistent state on kill |
| Add unit tests for retry logic, parser, style detection | Verify reliability improvements |

**Validation:** Kill the process mid-pipeline, restart, orphaned topics are retried. API timeout triggers retry with backoff.

### Phase 3: Multi-Source Crawlers
**Goal:** Support Weibo, Zhihu, Baidu hot lists
**Depends on:** Phase 1 (Protocol pattern), Phase 2 (retry infrastructure)

| Task | Why |
|------|-----|
| Define `CrawlerProtocol` and `HotTopic` TypedDict | Common interface |
| Extract `DouyinCrawler` from `tophub.py` to `douyin.py` | Refactor to new pattern |
| Add `source` field to `hot_topics` table (migration) | Track which platform each topic came from |
| Implement `WeiboCrawler` | First new source |
| Implement `ZhihuCrawler` | Second new source |
| Implement `BaiduCrawler` | Third new source |
| Update pipeline to iterate all registered crawlers | Use all sources |
| Add dedup across sources (same topic from multiple platforms) | Avoid duplicate articles |
| Integration tests for each crawler | Verify each source works |

**Validation:** Pipeline fetches from all 4 platforms, deduplicates across sources, new crawlers can be added by creating one file.

### Phase 4: Smart Features -- Style Matching, Dedup, Scheduling
**Goal:** Intelligent content production
**Depends on:** Phase 3 (multi-source data)

| Task | Why |
|------|-----|
| Smart style matching (keyword analysis -> style selection) | Better content quality |
| Cross-source dedup with angle differentiation | Same hot topic, different article angle |
| 24/7 scheduling optimization (adaptive intervals) | More content production |
| Security: add authentication to web UI | Protect admin interface |
| Add CSRF protection (Flask-WTF) | Security hardening |
| Migrate API keys from `.env` to proper secret management | Security hardening |

### Phase 5: Production Readiness
**Goal:** Deployable, observable system
**Depends on:** Phase 1-4

| Task | Why |
|------|-----|
| Dockerfile + docker-compose.yml | Reproducible deployment |
| Structured logging (dictConfig with rotation) | Production observability |
| Health check endpoint improvements | Monitoring |
| CI/CD pipeline (GitHub Actions) | Automated quality gates |
| 80% test coverage verification | Confidence in changes |

---

## Component Boundary Summary

| Component | Owns | Does NOT Own |
|-----------|------|--------------|
| `src/crawler/` | HTTP requests to platforms, response parsing, `HotTopic` dict creation | Dedup logic, storage, scheduling |
| `src/writer/` | AI prompt construction, API call, response parsing, style templates | Storage, scheduling, publishing |
| `src/storage/` | ALL SQL, connection management, migrations | Business rules, HTTP handling |
| `src/scheduler/` | Pipeline orchestration (crawl -> dedup -> write -> store) | Individual step logic, web serving |
| `src/publisher/` | Platform-specific publishing (Playwright automation), RSS generation | Content generation, scheduling |
| `src/web/` | HTTP request/response, template rendering, input validation | Business logic, raw SQL |
| `config/` | Environment variable loading, constant definition | Runtime behavior |

---

## Sources

- Flask Application Factory: https://flask.palletsprojects.com/en/latest/patterns/appfactories/
- tenacity retry library: https://tenacity.readthedocs.io/en/latest/
- Dramatiq (for future reference): https://dramatiq.io/
- Python Protocol (PEP 544): Python 3.12+ documentation
- SQLite WAL mode: https://www.sqlite.org/wal.html
- Current codebase: `.planning/codebase/ARCHITECTURE.md`
- Current concerns: `.planning/codebase/CONCERNS.md`
