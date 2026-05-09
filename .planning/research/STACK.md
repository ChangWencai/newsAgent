# Technology Stack Research — 多源热点聚合 + AI 写作流水线

**Research Date:** 2026-05-09
**Overall Confidence:** MEDIUM-HIGH

---

## 1. 多平台热点抓取库

### 推荐方案：统一聚合 API（首选）+ 直连 API（备选）

#### 方案 A：DailyHotApi（推荐 - 开源聚合）

| 属性 | 值 |
|------|-----|
| 项目 | [imsyy/DailyHotApi](https://github.com/imsyy/DailyHotApi) |
| 支持平台 | 45+ 个国内热榜（微博、知乎、百度、抖音、B站、头条、36氪等） |
| 部署方式 | Node.js / Docker / Vercel / Railway / Zeabur |
| 数据格式 | JSON + RSS |
| 缓存 | 默认 60 分钟，可配置 |
| 优势 | 自建部署，无需 API Key，无调用限制，覆盖几乎所有目标平台 |

**关键接口：**
- 微博热搜：`/weibo`
- 知乎热榜：`/zhihu`
- 百度热搜：`/baidu`
- 抖音热点：`/douyin`
- 36氪热榜：`/36kr`

**使用方式：** 自建 Docker 部署到本地或服务器，Python 通过 `requests` 调用即可。

#### 方案 B：TophubData API（当前项目的上游）

| 属性 | 值 |
|------|-----|
| 项目 | [tophubdata.com](https://www.tophubdata.com/) |
| 支持平台 | 10,000+ 数据源 |
| 计费 | 需注册，有付费计划 |
| 接口 | `Tophub.nodes()` / `Tophub.node(hashid)` / `Tophub.node.historys()` / `Tophub.search()` |
| 格式 | JSON |

**注意：** 当前项目配置了 `TOPHUB_API_KEY` 和 `DOUYIN_NODE_HASHID` 但在代码中未使用（直接抓取抖音 API）。如需扩展到微博/知乎/百度，TophubData 是一个选项但需要付费。

#### 方案 C：直连各平台 API（底层方案）

| 平台 | API 端点 | 反爬难度 | 推荐 |
|------|----------|----------|------|
| 抖音 | `https://www.douyin.com/aweme/v1/web/hot/search/list/` | 低（当前已实现） | 已有 |
| 微博 | `https://m.weibo.cn/api/container/getIndex?containerid=106003...` | 中（需 visitor cookie） | 不推荐直接抓 |
| 知乎 | `https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total` | 中（需认证） | 不推荐直接抓 |
| 百度 | `https://top.baidu.com/board?tab=realtime`（HTML 解析） | 低 | 可用 BeautifulSoup |

**结论：** 推荐方案 A（DailyHotApi 自建），原因：
1. 开源免费，无 API Key 依赖
2. 一个部署覆盖 45+ 平台，无需逐个适配
3. Docker 一键部署，和现有 Flask 应用共存
4. JSON 格式统一，Python `requests` 即可调用

**替代方案：** 如果不想引入 Node.js 服务，可用 TophubData API（需付费）或直接 HTML 解析百度热榜（最低成本）。

---

## 2. 中国 AI 写作 API 替代方案

### 当前方案：MiniMax-M2.7（通过 Anthropic SDK 兼容接口）

| 属性 | 值 |
|------|-----|
| Base URL | `https://api.minimaxi.com/anthropic` |
| SDK | `anthropic` Python SDK |
| 模型 | `MiniMax-M2.7` |
| 兼容性 | Anthropic Messages API |

### 推荐替代/备用方案

| 提供商 | API 兼容 | Base URL | 推荐模型 | 优势 | 劣势 |
|--------|----------|----------|----------|------|------|
| **DeepSeek** | OpenAI + Anthropic 双兼容 | `https://api.deepseek.com` (OpenAI) / `https://api.deepseek.com/anthropic` (Anthropic) | `deepseek-v4-flash`, `deepseek-v4-pro` | 国内访问稳定，性价比极高，双协议兼容 | 高峰期可能限流 |
| **Moonshot (Kimi)** | OpenAI 兼容 | `https://api.moonshot.cn/v1` | `moonshot-v1-8k/32k/128k` | 长上下文优秀，中文写作质量高 | 价格偏高 |
| **智谱 (ChatGLM)** | OpenAI 兼容 | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-flash`, `glm-4` | 免费额度大，国内稳定 | 模型更新较慢 |
| **通义千问 (Qwen)** | OpenAI 兼容 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus`, `qwen-turbo` | 阿里云生态，稳定性高 | 需阿里云账号 |
| **MiniMax** (当前) | Anthropic 兼容 | `https://api.minimaxi.com/anthropic` | `MiniMax-M2.7` | 已集成，无需改代码 | — |

### 推荐策略

**保留 MiniMax 作为主模型，增加 DeepSeek 作为 fallback：**

```python
# 推荐的多模型切换架构
AI_PROVIDERS = [
    {
        "name": "minimax",
        "base_url": "https://api.minimaxi.com/anthropic",
        "api_key_env": "MINIMAX_API_KEY",
        "model": "MiniMax-M2.7",
        "sdk": "anthropic",  # 使用 anthropic SDK
    },
    {
        "name": "deepseek",
        "base_url": "https://api.deepseek.com/anthropic",
        "api_key_env": "DEEPSEEK_API_KEY",
        "model": "deepseek-v4-flash",
        "sdk": "anthropic",  # 同样兼容 Anthropic SDK
    },
]
```

**关键发现：** DeepSeek 提供了 Anthropic 兼容端点（`https://api.deepseek.com/anthropic`），意味着现有 `anthropic` SDK 代码无需修改即可切换，只需更换 base_url 和 api_key。这是最省力的扩展路径。

**One API 统一网关（可选进阶方案）：**
- 项目：[songquanpeng/one-api](https://github.com/songquanpeng/one-api)
- 将所有国内 AI 提供商统一到一个 OpenAI 兼容端点
- 支持负载均衡、密钥管理、用量统计
- 适合未来需要多模型切换的场景

---

## 3. APScheduler 替代方案评估

### 当前方案：APScheduler 3.11.2

| 属性 | 值 |
|------|-----|
| 调度器 | `BackgroundScheduler` |
| 触发器 | `interval`（每 6 小时） |
| 持久化 | 无（内存中，进程重启丢失） |
| 执行器 | 默认 `ThreadPoolExecutor`（10 线程） |

### 对比分析

| 维度 | APScheduler 3.x | Celery + Beat | Huey 3.0 |
|------|-----------------|---------------|----------|
| **复杂度** | 低，直接嵌入 Flask | 高，需 Redis/RabbitMQ + Worker 进程 | 低-中，支持 SQLite 后端 |
| **部署** | 单进程即可 | 需额外 Redis + celery worker | 单进程可用 SQLite |
| **持久化** | 可选 SQLAlchemy/Redis | 天然持久化（Redis） | 支持 SQLite/Redis/文件 |
| **任务重试** | 手动实现 | 内置 retry 机制 | 内置 retry + pipeline |
| **监控** | 无内置 | Flower 监控面板 | 无内置 |
| **适用场景** | 简单定时任务 | 分布式任务队列 | 轻量级任务队列 |
| **生产可靠性** | 中（无持久化则丢失） | 高 | 中-高 |

### 推荐：继续使用 APScheduler，但添加持久化

**原因：**
1. 项目是单机部署，无需分布式
2. 当前只有 1 个定时任务（流水线），复杂度低
3. APScheduler 已集成，切换成本不值得
4. Celery 对本项目来说过度工程（需要 Redis + Worker 进程 + Beat 进程）

**必须改进：**
- 启用 SQLAlchemyJobStore 持久化任务状态（进程重启后恢复）
- 添加 `misfire_grace_time` 处理错过的执行
- 添加 `coalesce=True` 合并错过的执行

```python
# 推荐的 APScheduler 配置改进
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

jobstores = {
    'default': SQLAlchemyJobStore(url=f'sqlite:///{DB_PATH}')
}
executors = {
    'default': ThreadPoolExecutor(20)
}
job_defaults = {
    'coalesce': True,           # 合并错过的执行
    'max_instances': 1,         # 同一任务不并发
    'misfire_grace_time': 3600  # 错过 1 小时内仍可执行
}

scheduler = BackgroundScheduler(
    jobstores=jobstores,
    executors=executors,
    job_defaults=job_defaults,
)
```

**何时考虑切换：**
- 如果未来需要任务链（抓取 → 写作 → 发布 串联）→ 考虑 Huey（内置 pipeline/chord 支持）
- 如果需要多机分布式 → 考虑 Celery（但当前约束明确是单机）

---

## 4. 数据库选型

### 当前方案：SQLite3（stdlib，无 ORM）

| 属性 | 值 |
|------|-----|
| 引擎 | SQLite 3（Python stdlib） |
| ORM | 无，直接 SQL |
| 文件 | `data/newsagent.db` |
| WAL 模式 | 未启用 |
| 连接池 | 无（每次新建连接） |

### 对比分析

| 维度 | SQLite | PostgreSQL | MongoDB |
|------|--------|------------|---------|
| **部署复杂度** | 零（内嵌） | 高（需独立服务） | 高（需独立服务） |
| **并发读** | 优秀 | 优秀 | 优秀 |
| **并发写** | 受限（WAL 模式可改善） | 优秀 | 优秀 |
| **适合数据量** | < 100GB | 不限 | 不限 |
| **事务支持** | 完整 ACID | 完整 ACID | 文档级 |
| **JSON 支持** | 有限（JSON1 扩展） | 原生 JSONB | 原生 BSON |
| **运维成本** | 零 | 中 | 中 |
| **适用场景** | 单用户/单机 | 多用户/高并发 | 非结构化数据 |

### 推荐：继续使用 SQLite，但必须优化

**原因：**
1. 项目约束明确：单用户、单机部署
2. 热点 + 文章数据量极小（每天几十条，一年不到 2 万条）
3. 无需 PostgreSQL 的并发能力和运维开销
4. MongoDB 对结构化的关系数据（热点 → 文章）不是最佳选择

**必须改进：**

```python
# 1. 启用 WAL 模式（关键性能提升）
conn.execute("PRAGMA journal_mode=WAL")

# 2. 启用连接复用（当前每次新建连接，浪费资源）
# 使用连接上下文管理器或 aiosqlite（异步场景）

# 3. 推荐迁移到 SQLAlchemy（轻量 ORM，APScheduler 也用它）
# 不需要完整 Django/SQLAlchemy 重量级用法，只用 Core 层即可
```

**何时考虑切换：**
- 需要 Web UI 多用户同时访问 → PostgreSQL
- 需要存储大量非结构化内容（如 JSON 格式的原始抓取数据）→ MongoDB
- 数据量超过 100GB → PostgreSQL

---

## 5. Playwright 发布自动化最佳实践

### 当前方案分析

| 属性 | 值 |
|------|-----|
| SDK | `playwright` 1.59.0（async API） |
| 反检测措施 | 无（标准 Chromium，容易被识别） |
| Cookie 管理 | 保存/加载 `storage_state` JSON |
| 登录方式 | 手动扫码（`headless=False`） |
| 错误处理 | 基础 try/except |
| 重试机制 | 无 |

### 必须添加的改进

#### 1. 反检测：playwright-stealth（关键）

```python
# pip install playwright-stealth
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async with async_playwright() as p:
    stealth = Stealth()
    async with stealth.use_async(p.chromium.launch(headless=True)) as browser:
        context = await browser.new_context()
        page = await context.new_page()
        # 此时 page 已通过 stealth 注入反检测脚本
```

**playwright-stealth 2.0.3**（2026-04-04 发布）：
- Fork 自 puppeteer-extra-plugin-stealth 的 Python 移植版
- 自动掩盖 `navigator.webdriver`、`chrome.runtime` 等自动化指纹
- 支持自定义配置（如 `navigator_languages_override`）
- 要求 Python 3.9+

**注意：** 这是"起点级"反检测，不是银弹。头条的风控系统可能需要额外措施。

#### 2. Cookie 有效性检测与自动刷新

当前问题：Cookie 保存后无有效性检测，过期后发布失败。

```python
async def _check_login(self, page):
    """检查登录状态，同时验证 cookie 是否真正有效"""
    try:
        await page.goto(PUBLISH_URL, wait_until="domcontentloaded", timeout=15000)
        # 不仅检查 URL，还要检查页面元素是否正常加载
        await page.wait_for_selector("textarea", timeout=10000)
        return True
    except Exception:
        return False
```

#### 3. 发布操作添加重试机制

```python
import tenacity

@tenacity.retry(
    stop=tenacity.stop_after_attempt(3),
    wait=tenacity.wait_exponential(multiplier=1, min=4, max=10),
    retry=tenacity.retry_if_exception_type((Exception,)),
)
async def _do_publish(self, page, title, content):
    # 发布逻辑
```

#### 4. 选择器健壮性

当前使用 CSS 选择器（如 `textarea`, `.ProseMirror`, `button.publish-btn-last`），头条改版后容易失效。

**改进方向：**
- 优先使用 Playwright 的角色定位器：`page.get_by_role("textbox")`
- 添加多选择器回退机制
- 使用 `page.get_by_placeholder()` 等语义定位

#### 5. 频率控制与行为模拟

当前已有 `random.uniform()` 延迟，这是好的。进一步改进：

```python
# 模拟人类打字速度（逐字输入而非直接 fill）
await page.type("textarea", title, delay=random.uniform(50, 150))

# 滚动页面模拟自然行为
await page.mouse.wheel(0, random.randint(100, 300))

# 随机化操作间隔
await asyncio.sleep(random.gauss(mu=3, sigma=1))
```

#### 6. headless 模式策略

| 场景 | headless | 说明 |
|------|----------|------|
| 首次登录/cookie 过期 | `False` | 需要用户扫码 |
| 日常发布 | `True` | 无头模式，配合 stealth |
| 调试问题 | `False` | 观察实际操作 |

---

## 6. 工具链补充建议

### 当前缺失的工具

| 类别 | 推荐工具 | 用途 |
|------|----------|------|
| **代码格式化** | `ruff`（替代 black + isort + flake8） | 统一代码风格 |
| **类型检查** | `mypy` 或 `pyright` | 静态类型检查 |
| **测试** | `pytest` + `pytest-cov` + `pytest-asyncio` | 测试框架 |
| **依赖管理** | `pip-tools`（pip-compile） | 生成 requirements.lock |
| **安全扫描** | `bandit` | Python 安全漏洞扫描 |
| **HTTP 重试** | `tenacity` | Playwright 和 API 调用的重试 |
| **日志增强** | `structlog`（可选） | 结构化日志 |

### 安装命令

```bash
# 核心依赖（新增）
pip install playwright-stealth tenacity

# 开发工具链
pip install ruff mypy pytest pytest-cov pytest-asyncio bandit pip-tools

# 生成锁文件
pip-compile requirements.in -o requirements.lock
```

---

## 7. 完整推荐栈

### 核心栈（保持 + 优化）

| 层 | 当前 | 推荐 | 变更 |
|----|------|------|------|
| **Web 框架** | Flask 3.1.1 | Flask 3.1.1 | 不变 |
| **定时调度** | APScheduler 3.11.2 | APScheduler 3.11.2 + SQLAlchemyJobStore | 添加持久化 |
| **数据库** | SQLite（stdlib） | SQLite + WAL + 连接管理 | 优化，不换 |
| **AI SDK** | anthropic SDK -> MiniMax | anthropic SDK -> MiniMax + DeepSeek fallback | 添加备用 |
| **浏览器自动化** | playwright 1.59.0 | playwright + playwright-stealth | 添加反检测 |
| **HTTP 客户端** | requests | requests + tenacity 重试 | 添加重试 |

### 新增依赖

| 包 | 版本 | 用途 |
|----|------|------|
| `playwright-stealth` | >=2.0.3 | Playwright 反检测 |
| `tenacity` | >=8.0 | 智能重试 |
| `beautifulsoup4` | >=4.12 | HTML 解析（百度等直连方案备选） |
| `ruff` | >=0.4 | 代码格式化 + lint（开发工具） |
| `pytest` | >=8.0 | 测试框架（开发工具） |
| `pytest-cov` | >=5.0 | 测试覆盖率（开发工具） |
| `pytest-asyncio` | >=0.23 | 异步测试支持（开发工具） |

### 外部服务（自建 Docker）

| 服务 | 用途 | 部署方式 |
|------|------|----------|
| DailyHotApi | 多平台热点聚合 | `docker run -d -p 3000:3000 imsyy/dailyhot-api` |

---

## Confidence Assessment

| 领域 | 信心 | 说明 |
|------|------|------|
| 热点抓取 API | HIGH | DailyHotApi 有详细文档，覆盖 45+ 平台 |
| AI API 替代 | HIGH | DeepSeek Anthropic 兼容端点有官方文档确认 |
| APScheduler 评估 | HIGH | 官方文档明确，有实际使用经验 |
| SQLite 优化 | HIGH | WAL 模式、连接管理是标准最佳实践 |
| Playwright 反检测 | MEDIUM | playwright-stealth 是 PoC 级别，不保证绕过所有检测 |

---

## Sources

- [DailyHotApi GitHub](https://github.com/imsyy/DailyHotApi) — 45+ 平台热榜聚合 API
- [DeepSeek API Docs](https://api-docs.deepseek.com/) — Anthropic 兼容端点确认
- [One API GitHub](https://github.com/songquanpeng/one-api) — 多模型统一网关
- [playwright-stealth PyPI](https://pypi.org/project/playwright-stealth/) — 反检测插件 v2.0.3
- [Huey PyPI](https://pypi.org/project/huey/) — 轻量任务队列 v3.0.0
- [APScheduler Docs](https://apscheduler.readthedocs.io/en/3.x/) — 调度器文档
- [Playwright Python Docs](https://playwright.dev/python/) — 浏览器自动化文档
- [TophubData](https://www.tophubdata.com/) — 热榜数据 API 服务商
