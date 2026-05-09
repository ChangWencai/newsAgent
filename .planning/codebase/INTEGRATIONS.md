# External Integrations

**Analysis Date:** 2026/05/09

## APIs & External Services

### 抖音热榜 (Douyin Hot Search)

- **Purpose:** Fetch real-time trending topics as news source material
- **Endpoint:** `https://www.douyin.com/aweme/v1/web/hot/search/list/`
- **Client:** `requests.get()` in `src/crawler/tophub.py:19`
- **Auth:** None (public API, spoofed User-Agent + Referer headers)
- **Headers:** Chrome UA string + `Referer: https://www.douyin.com/` (`src/crawler/tophub.py:9-12`)
- **Response:** JSON with `data.word_list[]` containing `word`, `hot_value`
- **Risk:** No official API; uses web scraping with header spoofing. Subject to anti-bot detection.

### MiniMax AI (Article Generation)

- **Purpose:** Generate articles from hot topics using MiniMax-M2.7 model
- **Endpoint:** `https://api.minimaxi.com/anthropic` (Anthropic-compatible)
- **SDK:** `anthropic` Python SDK, instantiated with custom `base_url` (`src/writer/generator.py:17-20`)
- **Auth:** `MINIMAX_API_KEY` environment variable
- **Model:** `MiniMax-M2.7` (hardcoded in `src/writer/generator.py:11`)
- **Max tokens:** 2000 per request (`src/writer/generator.py:45`)
- **System prompts:** 3 styles defined in `src/writer/styles.py` - news, comment, entertainment
- **Style detection:** Keyword-based auto-matching (`src/writer/styles.py:55-75`)
- **Output format:** Structured response with title, content, summary sections parsed by line prefix (`src/writer/generator.py:63-103`)

### 头条号 (Toutiao) Publishing

- **Purpose:** Auto-publish generated articles to Toutiao content platform
- **Platform URLs:**
  - Publish: `https://mp.toutiao.com/profile_v4/graphic/publish`
  - Login: `https://mp.toutiao.com/auth/page/login`
- **Client:** Playwright Chromium browser automation (`src/publisher/toutiao_publisher.py`)
- **Auth:** Cookie-based session persisted to `data/cookies/toutiao_state.json` via Playwright `storage_state`
- **Login flow:** Opens headful browser -> waits for manual login (up to 300s) -> saves cookies (`src/publisher/toutiao_publisher.py:75-96`)
- **Publish flow (`_do_publish`, line 98-149):**
  1. Navigate to publish page
  2. Fill title in `textarea`
  3. Fill content in `.ProseMirror` editor
  4. Optionally select cover image from material library
  5. Click `button.publish-btn-last`
  6. Confirm if dialog appears
- **Timing:** Random delays (1-6 seconds) between steps to mimic human behavior
- **Reference:** Based on `InterestWatcher-Xiaofeng/toutiao-auto-publisher` (noted in module docstring)

### 今日热榜 API (TOPHUB) - UNUSED

- **Config:** `TOPHUB_API_KEY` and `TOPHUB_BASE_URL` defined in `config/settings.py:9-11`
- **Status:** NOT USED by any code. The crawler module is named `tophub.py` but contains `DouyinCrawler` that directly scrapes Douyin.
- **Config display:** Imported in `src/web/routes.py` for settings page display only
- **Issue:** Dead configuration - variables exist with no consumer

## Data Storage

**Databases:**
- SQLite3 (embedded, no server)
  - Path: `data/newsagent.db` (derived in `config/settings.py:28`)
  - Client: stdlib `sqlite3` (`src/storage/database.py`)
  - Schema:
    - `hot_topics`: id, title, url, hot_value, category, fetched_at, status
    - `articles`: id, topic_id (FK), title, content, style, generated_at, published_at, status
  - Indexes: `idx_topics_title`, `idx_articles_status`
  - Connection model: open-per-operation, no pooling, no WAL mode

**File Storage:**
- Local filesystem only
  - `data/cookies/toutiao_state.json` - Playwright browser session state
  - `data/newsagent.db` - SQLite database

**Caching:**
- None. Deduplication via `SELECT 1 FROM hot_topics WHERE title = ?` query per topic.

## Authentication & Identity

**Toutiao (头条号):**
- Cookie-based browser session via Playwright `storage_state`
- First login requires `headless=False` with manual user interaction
- Session file: `data/cookies/toutiao_state.json`
- Re-auth: delete cookie file to force re-login
- No OAuth, no JWT, no token refresh mechanism

## Monitoring & Observability

**Error Tracking:** None (no Sentry, Datadog, etc.)

**Logging:**
- Python `logging` module, `INFO` level, stdout
- Format: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`
- Configured in `main.py:14-17` and `publish.py:18-21`

## RSS Feed

**Endpoint:** `/rss` (`src/publisher/rss_feed.py`)
- Format: RSS 2.0 XML
- Content: Last 20 articles with title, link, HTML-formatted description, pubDate
- MIME type: `application/rss+xml; charset=utf-8`
- Date format: RFC 822 with +0800 timezone

**Health check:** `/health` - Returns `{"status": "ok"}`

## Web Management UI

**Framework:** Flask + Jinja2 templates (`src/web/templates/`)
**Static assets:** None (CSS/JS inline in `base.html`)

| Route | Method | Purpose | File |
|-------|--------|---------|------|
| `/` | GET | Dashboard (stats + recent articles) | `src/web/routes.py:41` |
| `/topics` | GET | Hot topics list (last 50) | `src/web/routes.py:68` |
| `/articles` | GET | Articles with status filter | `src/web/routes.py:79` |
| `/article/<id>` | GET | Article detail | `src/web/routes.py:101` |
| `/settings` | GET | Config display (secrets masked) | `src/web/routes.py:138` |
| `/api/run-pipeline` | POST | Trigger pipeline manually | `src/web/routes.py:114` |
| `/api/article/<id>/delete` | POST | Delete article | `src/web/routes.py:124` |
| `/rss` | GET | RSS feed | `src/publisher/rss_feed.py:14` |
| `/health` | GET | Health check | `src/publisher/rss_feed.py:20` |

## CI/CD & Deployment

**Hosting:** Direct execution (`python main.py` or `python publish.py`)
**Process manager:** None (no systemd, supervisor, gunicorn)
**Containerization:** None (no Dockerfile)
**CI Pipeline:** None

## Webhooks & Callbacks

**Incoming:** None
**Outgoing:** None

## Known Issues

1. **Config/code mismatch:** `TOPHUB_API_KEY`, `TOPHUB_BASE_URL`, and `DOUYIN_NODE_HASHID` are configured but have no code consumer. The settings page displays them, creating false impression they are active.

2. **Module naming confusion:** `src/crawler/tophub.py` filename suggests 今日热榜 integration but contains `DouyinCrawler` class that directly scrapes Douyin.

3. **Missing Playwright setup step:** `requirements.txt` includes `playwright>=1.40.0` but there is no documented step for `playwright install chromium`, which is required before first use.

4. **SQLite concurrency:** No connection pooling or WAL mode. Each request opens/closes a new connection. Concurrent Flask requests could experience lock contention.

5. **Anti-bot risk:** Douyin crawler uses only User-Agent/Referer spoofing with no rotation, rate limiting, or retry logic. High risk of IP blocking.

6. **No dependency pinning:** `requirements.txt` uses `>=` version ranges with no upper bound and no lockfile, risking breaking changes from dependency updates.

---

*Integration audit: 2026/05/09*
