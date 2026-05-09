# Technology Stack

**Analysis Date:** 2026/05/09

## Languages

**Primary:**
- Python 3.13.2 - All application logic, scheduling, crawling, AI generation, publishing, web UI
  - Runtime: CPython (`/Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13`)
  - Virtual environment: `venv/` (created via `python -m venv`)

**Secondary:**
- HTML/Jinja2 - Server-side rendered web templates (`src/web/templates/*.html`)
- Inline CSS/JS in `base.html` (no static assets, no build toolchain)

## Runtime

**Environment:**
- CPython 3.13.2 (from `venv/pyvenv.cfg`)
- Platform: macOS (Darwin 25.3.0)

**Package Manager:**
- pip (Python standard)
- Lockfile: absent (no `requirements.lock`, `poetry.lock`, or `pip freeze` output)

## Frameworks

**Core Web:**
- Flask >=3.0.0 - HTTP server, management UI, RSS feed endpoint
  - App creation: `main.py:21-42`
  - Routes: `src/web/routes.py`
  - Templates: `src/web/templates/` (Jinja2, server-side rendering)

**Task Scheduling:**
- APScheduler >=3.10.0 - `BackgroundScheduler`, pipeline runs every 6 hours
  - Config: `main.py:60-69`
  - Job: `src/scheduler/jobs.py:run_pipeline()`

**Browser Automation:**
- Playwright >=1.40.0 - Chromium-based automation for Toutiao publishing
  - Async API: `src/publisher/toutiao_publisher.py`
  - Also used directly in `publish.py` for standalone publishing

**HTTP Client:**
- requests >=2.31.0 - Douyin hot search API (`src/crawler/tophub.py:19`)

**AI SDK:**
- anthropic >=0.20.0 - Used as client for MiniMax API (Anthropic-compatible endpoint)
  - `src/writer/generator.py:17-20`

## Key Dependencies (from `requirements.txt`)

| Package | Version | Purpose | File |
|---------|---------|---------|------|
| `anthropic` | >=0.20.0 | MiniMax AI article generation | `src/writer/generator.py` |
| `requests` | >=2.31.0 | Douyin hot search scraping | `src/crawler/tophub.py` |
| `flask` | >=3.0.0 | Web UI + RSS | `main.py`, `src/web/routes.py` |
| `apscheduler` | >=3.10.0 | Scheduled pipeline execution | `main.py` |
| `python-dotenv` | >=1.0.0 | Environment variable loading | `config/settings.py` |
| `playwright` | >=1.40.0 | Toutiao publishing automation | `src/publisher/toutiao_publisher.py` |

**Standard Library (no install needed):**
- `sqlite3` - Database (`src/storage/database.py`)
- `xml.etree.ElementTree` - RSS XML generation (`src/publisher/rss_feed.py`)
- `argparse` - CLI parsing (`main.py`, `publish.py`)
- `logging` - Application logging (all modules)
- `asyncio` - Async Playwright execution (`publish.py`)
- `html` - Content escaping for RSS (`src/publisher/rss_feed.py:50`)

## Database

**Engine:** SQLite3 (Python stdlib `sqlite3`)
- File: `data/newsagent.db`
- No ORM - raw SQL via `sqlite3` module
- Connection: new connection per operation, no pooling (`src/storage/database.py:14-16`)
- Row factory: `sqlite3.Row` for dict-like access
- Tables: `hot_topics`, `articles` (FK relationship)
- Indexes: `idx_topics_title`, `idx_articles_status`
- WAL mode: not enabled

## Configuration

**Module:** `config/settings.py`
- Loads `.env` via `python-dotenv`
- All config centralized in one module

**Required environment variables:**
- `MINIMAX_API_KEY` - MiniMax AI API key (required for article generation)

**Optional environment variables:**
- `RSS_HOST` - Default `0.0.0.0`
- `RSS_PORT` - Default `5000`
- `RSS_BASE_URL` - Default `http://localhost:5000`
- `DEFAULT_STYLE` - Default `auto` (options: `news`, `comment`, `entertainment`, `auto`)
- `MAX_TOPICS_PER_RUN` - Default `5`

**Configured but unused by current code:**
- `TOPHUB_API_KEY` - Defined in config, displayed on settings page, but no consumer
- `DOUYIN_NODE_HASHID` - Same situation

## Build & Tooling

**Formatting:** Not configured (no `pyproject.toml`, `ruff.toml`, `.prettierrc`, `black` config)
**Linting:** Not configured
**Type Checking:** Not configured (no mypy/pyright)
**Testing:** Not configured (no pytest, no test files)
**CI/CD:** Not configured

## Platform Requirements

**Development:**
- Python 3.13+
- Playwright Chromium binary (`playwright install chromium` required after pip install)
- macOS or Linux (Windows untested)

**Production:**
- Python 3.13+
- Persistent filesystem for `data/` directory (SQLite DB + cookie state)
- Headful browser environment for first-time Playwright login (`headless=False`)

---

*Stack analysis: 2026/05/09*
