# Codebase Concerns

**Analysis Date:** 2026/05/09

## Tech Debt

### Global Mutable State for Database

- **Severity:** HIGH
- **Issue:** `src/web/routes.py:20` uses a module-level global variable `_db` initialized via `init_web()`. All route handlers access this global directly, making the code untestable and non-thread-safe.
- **Files:** `src/web/routes.py` (line 20, 25, 43, 70, 82, 103, 126)
- **Impact:** Cannot run multiple Flask workers (e.g., gunicorn with threads) safely. Cannot inject mock database for testing.
- **Fix approach:** Use Flask's `g` object or application context to store the database instance. Or refactor routes into a Flask Blueprint with dependency injection.

### Raw SQL in Route Handlers

- **Severity:** HIGH
- **Issue:** `src/web/routes.py` embeds raw SQL queries directly in route handler functions (lines 43-54, 71-73, 85-92, 104-106, 127-134). This duplicates data access logic that already exists in `src/storage/database.py`.
- **Files:** `src/web/routes.py`
- **Impact:** Business logic and data access are tightly coupled. Changes to the schema require updating both the Database class AND the route handlers independently.
- **Fix approach:** Move all database queries into `src/storage/database.py` methods. Route handlers should call `db.get_dashboard_stats()`, `db.delete_article(id)`, etc.

### No Connection Pooling

- **Severity:** MEDIUM
- **Issue:** `src/storage/database.py:14-17` creates a new SQLite connection on every `_get_conn()` call. Every single database operation opens and closes a connection.
- **Files:** `src/storage/database.py`
- **Impact:** Performance overhead under concurrent access. SQLite connections are not thread-safe by default -- concurrent reads/writes from the scheduler and Flask handlers can cause `database is locked` errors.
- **Fix approach:** Use a single connection with `check_same_thread=False` or implement connection pooling via SQLAlchemy or a thread-local pattern.

### Fragile AI Response Parser

- **Severity:** MEDIUM
- **Issue:** `src/writer/generator.py:63-103` parses AI output by splitting on Chinese prefix strings (`标题：`, `正文：`, `摘要：`). If the AI model changes its output format even slightly, all article generation breaks silently.
- **Files:** `src/writer/generator.py`
- **Impact:** Silent failures produce empty or malformed articles that get stored in the database.
- **Fix approach:** Use structured output (JSON mode) from the API, or add strict validation that rejects articles missing title or content.

### Publisher Relies on Fragile CSS Selectors

- **Severity:** HIGH
- **Issue:** `src/publisher/toutiao_publisher.py:107-180` uses hardcoded CSS selectors (`textarea`, `.ProseMirror`, `button.publish-btn-last`, `.byte-drawer .img-span`) to interact with Toutiao's web UI. Any UI update by Toutiao will break the entire publishing pipeline.
- **Files:** `src/publisher/toutiao_publisher.py`
- **Impact:** Publishing silently fails when selectors no longer match. No fallback or detection mechanism exists.
- **Fix approach:** Add explicit selector-not-found error messages. Consider using accessibility labels or data attributes. Add monitoring/alerting for publish failures.

### Duplicated Login Logic

- **Severity:** MEDIUM
- **Issue:** `publish.py:25-54` re-implements the entire login flow that already exists in `src/publisher/toutiao_publisher.py:75-96`. The two implementations diverge in subtle ways (e.g., `login_only()` in publish.py does not use `_create_context`).
- **Files:** `publish.py`, `src/publisher/toutiao_publisher.py`
- **Impact:** Bug fixes in one copy may not be applied to the other.
- **Fix approach:** Remove the duplicated logic from `publish.py`. Reuse `ToutiaoPublisher._wait_login()` with a flag to control browser headless mode.

### No Database Migrations

- **Severity:** MEDIUM
- **Issue:** `src/storage/database.py:19-48` uses `CREATE TABLE IF NOT EXISTS` for schema definition. There is no migration system -- schema changes require manual table drops or ALTER TABLE commands.
- **Files:** `src/storage/database.py`
- **Impact:** Adding columns or changing schema requires manual intervention and risks data loss.
- **Fix approach:** Adopt Alembic for migration management, or at minimum add a version tracking table.

## Security Considerations

### CRITICAL: .env File Contains Real API Keys

- **Severity:** CRITICAL
- **Issue:** The `.env` file contains real API keys (TOPHUB_API_KEY and MINIMAX_API_KEY with actual secret values). While `.env` is listed in `.gitignore`, the file currently exists on disk with live credentials.
- **Files:** `.env`, `.gitignore`
- **Risk:** Accidental commit or exposure of API keys. If the `.gitignore` entry is ever removed or the file is copied elsewhere, secrets leak.
- **Current mitigation:** `.gitignore` includes `.env`.
- **Recommendations:** Rotate the exposed API keys immediately. Use a secrets manager (e.g., AWS Secrets Manager, Vault) instead of flat files. At minimum, ensure `.env.example` is the only version-controlled config.

### No Authentication on Web Interface

- **Severity:** HIGH
- **Issue:** The Flask web application at `src/web/routes.py` has zero authentication. Anyone who can reach the server can view all articles, trigger the pipeline, delete articles, and view configuration.
- **Files:** `src/web/routes.py` (all routes)
- **Risk:** Unauthorized data access, pipeline abuse, data deletion.
- **Fix approach:** Add Flask-Login or basic HTTP authentication. At minimum, add IP allowlisting for admin endpoints.

### No CSRF Protection

- **Severity:** HIGH
- **Issue:** The API endpoints `/api/run-pipeline` (POST) and `/api/article/<id>/delete` (POST) at `src/web/routes.py:114-135` have no CSRF tokens. A malicious site can trigger these actions via cross-site requests.
- **Files:** `src/web/routes.py`
- **Risk:** Cross-site request forgery -- an attacker can trigger pipeline execution or delete articles.
- **Fix approach:** Use Flask-WTF for CSRF protection, or add CSRF tokens to all POST forms and verify them server-side.

### Unencrypted Cookie Storage

- **Severity:** MEDIUM
- **Issue:** `src/publisher/toutiao_publisher.py:88-89` saves login cookies (containing session tokens) as plain JSON to `data/cookies/toutiao_state.json`. This file contains sensitive authentication credentials.
- **Files:** `src/publisher/toutiao_publisher.py`, `data/cookies/`
- **Risk:** Session hijacking if the cookie file is accessed by other processes or users.
- **Fix approach:** Restrict file permissions to `600`. Consider encrypting the cookie file at rest.

### No Input Validation

- **Severity:** MEDIUM
- **Issue:** Route handlers in `src/web/routes.py` do not validate input. The `status_filter` parameter at line 81 is checked against a whitelist, but `article_id` at line 101 is only validated by Flask's `int()` converter.
- **Files:** `src/web/routes.py`
- **Risk:** While SQLite parameterized queries prevent SQL injection, lack of explicit validation can lead to unexpected behavior.
- **Fix approach:** Use a validation library (marshmallow, pydantic) for all user-facing inputs.

### Settings Page Exposes Configuration

- **Severity:** LOW
- **Issue:** `src/web/routes.py:138-149` displays configuration values on the settings page (masked API key shows `***`, but other config like DB_PATH, RSS_BASE_URL is exposed).
- **Files:** `src/web/routes.py`
- **Risk:** Information disclosure -- server paths and configuration details are visible to any visitor.
- **Fix approach:** Gate the settings page behind authentication.

## Reliability Concerns

### No Retry Logic for External API Calls

- **Severity:** HIGH
- **Issue:** `src/writer/generator.py:42-61` calls the MiniMax API with no retry logic. `src/crawler/tophub.py:19` makes HTTP requests with no retry or backoff. Transient network failures cause silent data loss -- topics are skipped with `continue` at `src/scheduler/jobs.py:59`.
- **Files:** `src/writer/generator.py`, `src/crawler/tophub.py`, `src/scheduler/jobs.py`
- **Impact:** A single network blip during a pipeline run causes that topic to be permanently skipped (it will be marked as existing in the database via `topic_exists` check, but no article is generated).
- **Fix approach:** Implement retry with exponential backoff using `tenacity` or similar. Distinguish between retryable errors (network timeout, 5xx) and permanent errors (4xx).

### Pipeline Swallows Individual Topic Failures

- **Severity:** MEDIUM
- **Issue:** `src/scheduler/jobs.py:70-71` catches `Exception` for each topic and logs it, then continues. There is no failure tracking, no retry queue, and no alerting.
- **Files:** `src/scheduler/jobs.py`
- **Impact:** Failed topics are silently lost. The operator has no visibility into partial pipeline failures without manually reading logs.
- **Fix approach:** Add a `failed` status to topics. Implement a dead-letter queue or failure counter. Add health metrics.

### No Graceful Shutdown for Scheduler

- **Severity:** MEDIUM
- **Issue:** `main.py:60-69` starts an APScheduler `BackgroundScheduler` but does not register a shutdown hook. If the process is killed (SIGTERM), running jobs may be interrupted mid-execution, leaving the database in an inconsistent state.
- **Files:** `main.py`
- **Impact:** Partial article inserts (topic created but article not generated). Orphaned data.
- **Fix approach:** Register `atexit` handler or signal handler to call `scheduler.shutdown(wait=True)`.

### Database Operations Not Atomic

- **Severity:** MEDIUM
- **Issue:** `src/scheduler/jobs.py:45-67` performs multiple database operations (insert_topic, then insert_article) without a transaction. If the process crashes between these two calls, the database contains a topic with no corresponding article.
- **Files:** `src/scheduler/jobs.py`, `src/storage/database.py`
- **Impact:** Orphaned topics in the database.
- **Fix approach:** Wrap the topic+article insert in a single database transaction.

### Synchronous Pipeline Blocks Flask

- **Severity:** MEDIUM
- **Issue:** `src/web/routes.py:117` calls `run_pipeline(_db)` synchronously inside a Flask request handler. This blocks the web server for the entire duration of the pipeline (potentially minutes), making all other endpoints unresponsive.
- **Files:** `src/web/routes.py`
- **Impact:** Clicking "Run Pipeline" in the web UI freezes the entire web application.
- **Fix approach:** Run the pipeline in a background thread or use Celery/RQ for async task execution.

## Scalability Issues

### SQLite Single-Writer Limitation

- **Severity:** HIGH
- **Issue:** SQLite (`src/storage/database.py`) supports only one writer at a time. The APScheduler background thread and Flask request handlers can both attempt writes concurrently, causing `database is locked` errors.
- **Files:** `src/storage/database.py`, `main.py`
- **Impact:** Under concurrent access (scheduler running + web user deleting an article), database operations will fail with locking errors.
- **Fix approach:** Migrate to PostgreSQL or MySQL for production use. Alternatively, serialize all writes through a single queue/thread.

### Single-Process Flask Development Server

- **Severity:** HIGH
- **Issue:** `main.py:77` runs `app.run()` which starts the Werkzeug development server. This is explicitly documented as not suitable for production. It handles one request at a time.
- **Files:** `main.py`
- **Impact:** Cannot handle concurrent web requests. The pipeline trigger endpoint blocks all other requests.
- **Fix approach:** Use gunicorn or uvicorn as a production WSGI server: `gunicorn -w 4 main:create_app`.

### No Horizontal Scaling Path

- **Severity:** MEDIUM
- **Issue:** The architecture ties the web server, scheduler, and database to a single process on a single machine. There is no way to scale components independently.
- **Files:** `main.py`, `src/scheduler/jobs.py`
- **Impact:** Cannot scale beyond a single machine.
- **Fix approach:** Separate the scheduler from the web server. Use a distributed task queue (Celery) and an external database.

## Missing Infrastructure

### No Tests

- **Severity:** CRITICAL
- **Issue:** Zero test files exist in the project. No `test_*.py`, no `conftest.py`, no `pytest.ini`, no `pyproject.toml`. There is no test coverage of any kind.
- **Files:** Entire project
- **Impact:** No safety net for refactoring. No regression detection. Any change risks breaking existing functionality without notice.
- **Fix approach:** Add pytest with at minimum: unit tests for `detect_style()` and `_parse_response()`, integration tests for database operations, and a basic API test for the Flask routes.

### No CI/CD Pipeline

- **Severity:** HIGH
- **Issue:** No `.github/workflows/`, no `Makefile`, no `pyproject.toml`, no CI configuration of any kind exists.
- **Files:** Project root
- **Impact:** No automated testing, no automated deployment, no code quality gates.
- **Fix approach:** Add GitHub Actions workflow for: lint (ruff), type-check (mypy), test (pytest), and deploy.

### No Linting or Formatting Configuration

- **Severity:** HIGH
- **Issue:** No `.flake8`, `ruff.toml`, `pyproject.toml`, `.prettierrc`, or any linter/formatter configuration exists. No pre-commit hooks.
- **Files:** Project root
- **Impact:** Inconsistent code style. No automated detection of common bugs (unused imports, undefined variables, etc.).
- **Fix approach:** Add `pyproject.toml` with ruff configuration. Add `.pre-commit-config.yaml` for automated checks.

### No Type Annotations

- **Severity:** MEDIUM
- **Issue:** Only `src/web/routes.py:20` uses a type annotation (`_db: Database`). No other function in the project has type hints. No `mypy` or `pyright` configuration exists.
- **Files:** All Python files
- **Impact:** Harder to catch type-related bugs. IDE support is limited.
- **Fix approach:** Add type annotations to all function signatures. Configure mypy in `pyproject.toml`.

### No Production Deployment Configuration

- **Severity:** MEDIUM
- **Issue:** No `Dockerfile`, `docker-compose.yml`, `Procfile`, `systemd` service file, or any deployment configuration exists.
- **Files:** Project root
- **Impact:** Manual, error-prone deployment process. No reproducible environments.
- **Fix approach:** Add `Dockerfile` and `docker-compose.yml` for containerized deployment.

## Anti-Patterns and Code Smells

### Bare Exception Catching

- **Severity:** MEDIUM
- **Issue:** Multiple locations catch bare `Exception`, hiding the specific error type:
  - `src/crawler/tophub.py:34` -- catches all exceptions from HTTP requests
  - `src/writer/generator.py:59` -- catches all exceptions from API calls
  - `src/scheduler/jobs.py:70` -- catches all exceptions per topic
  - `src/web/routes.py:119` -- catches all exceptions from pipeline execution
  - `src/publisher/toutiao_publisher.py:72, 122, 144` -- catches all exceptions
- **Files:** Multiple
- **Impact:** Specific errors (authentication failure, rate limit, malformed response) are not distinguished. Cannot implement targeted recovery.
- **Fix approach:** Catch specific exceptions (`requests.RequestError`, `anthropic.APIError`, etc.). Use bare `Exception` only at top-level boundaries with re-raise or logging.

### Inconsistent API Response Format

- **Severity:** MEDIUM
- **Issue:** API responses have no consistent envelope. `api_run_pipeline` returns `{"success": True, "message": "..."}`, `api_delete_article` returns `{"success": False, "message": "..."}`, and error pages return raw HTML strings.
- **Files:** `src/web/routes.py`
- **Impact:** Frontend code must handle each endpoint differently. No standard error format.
- **Fix approach:** Define a standard API response schema and apply it to all endpoints.

### DELETE via POST Instead of DELETE Method

- **Severity:** LOW
- **Issue:** `src/web/routes.py:33-37` uses `POST` method for the delete endpoint (`/api/article/<id>/delete`) instead of the HTTP `DELETE` method.
- **Files:** `src/web/routes.py`
- **Impact:** Violates REST conventions. Minor concern but reduces API clarity.
- **Fix approach:** Change to `methods=["DELETE"]` on `/api/article/<int:article_id>`.

### Inline CSS and JavaScript

- **Severity:** LOW
- **Issue:** `src/web/templates/base.html:7-49` embeds all CSS styles inline. `src/web/templates/base.html:64-82` embeds JavaScript inline.
- **Files:** `src/web/templates/base.html`
- **Impact:** Cannot leverage browser caching. Templates are harder to maintain as they grow.
- **Fix approach:** Extract CSS to `src/web/static/style.css` and JS to `src/web/static/app.js`.

### Config Module Uses Mixed Concerns

- **Severity:** LOW
- **Issue:** `config/settings.py` loads environment variables, defines constants, and computes file paths. The `DOUYIN_NODE_HASHID` variable is loaded but never used anywhere in the codebase.
- **Files:** `config/settings.py` (line 11)
- **Impact:** Dead configuration creates confusion. Mixing concerns makes the config harder to audit.
- **Fix approach:** Remove unused config variables. Separate environment loading from constant definition.

### No Logging Configuration for Production

- **Severity:** LOW
- **Issue:** Both `main.py:14-17` and `publish.py:18-21` configure logging with `basicConfig` at module level. The format includes timestamps but no log level filtering, no file rotation, and no structured logging.
- **Files:** `main.py`, `publish.py`
- **Impact:** Logs are lost on process restart. No log aggregation capability.
- **Fix approach:** Use `dictConfig` or YAML-based logging configuration. Add file handler with rotation for production.

---

*Concerns audit: 2026/05/09*
