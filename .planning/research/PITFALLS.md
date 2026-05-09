# Domain Pitfalls

**Domain:** AI 新闻自动化流水线（中国平台爬取 + AI 生成 + 头条号发布）
**Researched:** 2026-05-09

---

## Critical Pitfalls

### Pitfall 1: 头条号账号永久封禁

**What goes wrong:** 头条号检测到自动化发布行为后，直接永久封禁账号。这不是警告，是直接封号。被封后所有已发布的文章消失，流量变现收入归零。

**Why it happens:**
- 发布频率异常（人类不可能一天发布 20+ 篇文章）
- 发布时间过于规律（精确的整点发布模式）
- 内容被标记为 AI 生成（重复模板、缺乏个性、事实性错误）
- 同一 IP 在短时间内大量请求发布接口
- Cookie 文件被重复使用但登录态已过期，触发异常登录检测

**Consequences:**
- 账号永久封禁，无法申诉
- 所有已发布的文章被删除
- 累积的流量和收入归零
- 可能影响同一实名认证下的其他头条号

**Prevention:**
- 限制每天发布数量（不超过 5 篇）
- 发布时间加入随机延迟（当前已有 1-6 秒随机延迟，但需更长，如 30-120 分钟间隔）
- 发布前人工抽检文章质量
- 监控账号状态，发现异常立即暂停所有自动发布
- 绝不在同一 IP 上使用多个头条号

**Detection:**
- 每次发布后检查返回页面是否包含"审核中"字样
- 定期检查账号后台是否有异常提示
- 监控发布成功率，成功率骤降立即警报

**Phase:** Phase 2（安全加固）— 发布策略必须在添加更多平台爬取之前建立

---

### Pitfall 2: Playwright CSS 选择器全面失效

**What goes wrong:** 头条号前端代码更新后，`toutiao_publisher.py` 中硬编码的 CSS 选择器全部失效。发布流程静默失败——点击了错误的按钮，填写了错误的字段，或者根本无法找到元素。

**当前代码中的脆弱选择器（`src/publisher/toutiao_publisher.py`）：**
- `textarea` — 太宽泛，任何新增 textarea 都会匹配
- `.ProseMirror` — ProseMirror 编辑器的 class 名可能被重构
- `button.publish-btn-last` — 内部 class 名随时可能变
- `.byte-drawer .img-span` — 基于内部 UI 组件库的 class

**Why it happens:**
- 字节跳动（头条母公司）频繁进行 A/B 测试，不同用户看到不同 UI
- 前端框架升级（如从 Vue 2 到 Vue 3）会重写所有 class 名
- 产品迭代调整按钮位置和表单结构

**Consequences:**
- 发布静默失败，文章堆积在数据库中 status 永远是 draft
- 可能误操作（点击了"删除"而非"发布"）
- 无任何错误通知，直到人工检查才发现

**Prevention:**
- 添加选择器失败检测：每个 wait_for_selector 后检查返回值
- 使用 `page.screenshot()` 在关键步骤截图存档
- 添加 "data-testid" 或 role 属性作为备选选择器
- 实现健康检查：每次发布前用已知选择器测试页面结构
- 建立选择器更新的告警机制

**Detection:**
- 每次发布后验证最终 URL 是否包含 "success" 或文章 ID
- 定期截图对比页面结构变化
- 监控连续发布失败次数

**Phase:** Phase 2（安全加固）— 必须在增加更多功能之前加固发布流程

---

### Pitfall 3: AI 幻觉导致发布虚假新闻

**What goes wrong:** MiniMax-M2.7 生成的文章包含事实性错误、编造的事件细节、不存在的引用来源。头条号用户发现内容不实后举报，平台介入处罚。

**当前代码中的问题（`src/writer/styles.py` 和 `src/writer/generator.py`）：**
- System prompt 仅告诉模型"不要编造不存在的事实"，但没有强制事实核查机制
- 没有任何验证 AI 输出真实性的环节
- 模型仅基于热点标题生成，没有真实新闻来源作为参考

**Why it happens:**
- LLM 天然存在幻觉问题，越是要求"写得详细"越容易编造
- 热点标题信息量有限，模型需要"填充"细节来满足字数要求
- 中文模型在事实性方面的训练数据质量参差不齐

**Consequences:**
- 单篇文章被举报：文章被删除，扣信用分
- 多篇文章不实：账号降权，推荐量暴跌
- 严重虚假新闻：账号封禁，可能面临法律追责
- 传播不实信息涉及《网络信息内容生态治理规定》

**Prevention:**
- 生成文章后增加事实核查步骤（对比多个信息源）
- 限制 AI "创造性"：在 prompt 中明确要求"仅基于已知事实"
- 对敏感话题（政治、医疗、灾害）自动标记，要求人工审核
- 使用更保守的 temperature 参数
- 建立文章质量评分机制

**Detection:**
- 收集用户评论中的负面反馈
- 监控文章举报率
- 定期人工抽检生成的文章

**Phase:** Phase 3（智能匹配与内容优化）— 这是内容质量的核心问题

---

### Pitfall 4: 抖音爬虫 IP 封禁

**What goes wrong:** 抖音检测到异常请求后封禁 IP。当前代码使用固定的 User-Agent 和 Referer 头（`src/crawler/tophub.py:9-12`），没有任何反检测措施。

**当前代码问题：**
- 固定 User-Agent：`Chrome/120.0.0.0`，不轮换
- 无代理 IP 池
- 无请求间隔控制
- 无 Cookie 管理
- 无 TLS 指纹伪装

**Why it happens:**
- 抖音（字节跳动）的反爬系统是业界最复杂的之一
- 检测手段包括：IP 频率分析、TLS 指纹（JA3/JA4）、请求头一致性检查、JavaScript 挑战
- 一旦被标记，同一 IP 段可能都被封禁

**Consequences:**
- 抖音热点源完全中断
- 整条流水线因无数据源而停摆
- 如果在服务器上运行，服务器 IP 被封影响其他服务

**Prevention:**
- 使用代理 IP 池（至少 10+ 个节点轮换）
- 随机化 User-Agent（使用 fake-useragent 库）
- 添加请求间隔（至少 3-10 秒随机延迟）
- 考虑改用第三方 API（今日热榜等聚合平台）而非直接爬取
- 实现 IP 封禁自动检测和代理切换

**Detection:**
- 监控请求失败率（HTTP 403/429）
- 检测返回数据是否为空或异常
- 设置连续失败告警

**Phase:** Phase 1（多平台支持）— 添加微博/知乎/百度爬取时必须同时解决

---

### Pitfall 5: SQLite 并发写入死锁

**What goes wrong:** APScheduler 后台线程和 Flask 请求处理线程同时写入 SQLite，触发 `database is locked` 错误。当前代码每次操作都开新连接（`src/storage/database.py:14-17`），无连接池、无 WAL 模式。

**Why it happens:**
- SQLite 只支持一个 writer 同时写入
- APScheduler 在后台线程中运行 pipeline，Flask 在主线程中处理请求
- 当 pipeline 在写入时，Web UI 的删除操作会阻塞
- 极端情况下会引发连锁锁等待

**Consequences:**
- Pipeline 写入 topic 但写入 article 时锁死，留下孤立的 topic
- Web UI 操作超时
- 数据库文件损坏（极端情况）

**Prevention:**
- 启用 WAL 模式：`PRAGMA journal_mode=WAL;`
- 使用单一写入队列序列化所有写操作
- 或迁移到 PostgreSQL（推荐用于生产环境）
- 使用 `check_same_thread=False` 配合线程锁

**Detection:**
- 捕获 `sqlite3.OperationalError` 并记录
- 监控数据库锁等待时间

**Phase:** Phase 1（基础架构加固）— 这是最先需要解决的底层问题

---

## Moderate Pitfalls

### Pitfall 6: AI 响应解析静默失败

**What goes wrong:** `_parse_response()`（`src/writer/generator.py:63-103`）依赖中文前缀字符串（`标题：`、`正文：`、`摘要：`）解析 AI 输出。当模型输出格式变化时，解析失败但不报错，生成空标题或空正文的文章。

**Why it happens:**
- MiniMax 模型更新可能改变输出格式
- 有时模型会输出多余的内容（如"好的，我来为您撰写..."）
- 模型可能使用不同标点（半角冒号 vs 全角冒号）

**Prevention:**
- 添加解析结果验证：标题和正文都不能为空
- 解析失败时记录原始输出以便调试
- 考虑要求模型输出 JSON 格式（更可靠的解析）

**Phase:** Phase 3（内容质量优化）

---

### Pitfall 7: Cookie 过期但系统继续尝试发布

**What goes wrong:** 头条号 Cookie 有效期通常为 7-30 天。Cookie 过期后，`_check_login()` 检测到需要登录但系统只是返回失败，没有主动通知用户需要重新登录。

**Current code issue (`src/publisher/toutiao_publisher.py:64-73`):**
- `_check_login()` 返回 False 时，`publish()` 方法尝试 `_wait_login()`，但 `_wait_login()` 只在 headless=False 模式下弹出浏览器
- headless=True（生产环境）时，等待登录会直接超时

**Prevention:**
- Cookie 过期前主动刷新（在发布前检测 cookie 剩余有效期）
- 过期时发送通知（邮件、微信、短信）
- 支持扫码登录而非仅账号密码

**Phase:** Phase 2（安全加固）

---

### Pitfall 8: 无重试机制导致数据丢失

**What goes wrong:** 网络抖动导致 API 请求失败（MiniMax API 超时、抖音请求失败），当前代码直接跳过（`continue`），不重试。热点被标记为"已存在"但没有文章。

**Current code issue:**
- `src/crawler/tophub.py:34` — 异常后返回空列表，不做重试
- `src/writer/generator.py:59` — API 失败返回 None，不做重试
- `src/scheduler/jobs.py:70` — 异常被吞掉，继续下一条

**Prevention:**
- 使用 tenacity 或类似库实现指数退避重试
- 区分可重试错误（超时、5xx）和不可重试错误（4xx、认证失败）
- 实现死信队列，失败的任务进入队列待后续处理

**Phase:** Phase 1（基础架构加固）

---

### Pitfall 9: 敏感内容触发审核或封号

**What goes wrong:** AI 生成的内容碰巧涉及政治敏感话题、社会争议事件、虚假信息等，触发头条号的内容审核机制。

**高风险话题类别：**
- 政治类（领导人、政策争议、外交事件）
- 灾害事故类（地震、事故伤亡）
- 医疗健康类（治疗方法、药物推荐）
- 金融理财类（投资建议、股市预测）
- 法律案件类（司法判决、嫌疑人报道）

**Prevention:**
- 建立敏感词库，匹配后自动跳过或转人工审核
- 敏感类别文章设置更高的生成质量门槛
- 在 prompt 中明确禁止讨论政治敏感话题
- 定期更新敏感词库

**Phase:** Phase 3（智能匹配与内容优化）

---

### Pitfall 10: 热点去重机制过于简单

**What goes wrong:** 当前去重基于精确标题匹配（`db.topic_exists(title)`）。同一事件不同来源的标题略有不同就会重复生成文章。

**Example:**
- "某明星官宣结婚" vs "某明星发布结婚喜讯" — 被视为不同热点
- 结果：同一件事生成多篇角度相似的文章

**Prevention:**
- 使用语义相似度做去重（如 sentence-transformers）
- 或使用关键词 + 时间窗口的模糊匹配
- 实现同一热点从不同角度生成文章的机制（当前 PROJECT.md 中已列为 Active 需求）

**Phase:** Phase 3（智能匹配与内容优化）

---

### Pitfall 11: API 密钥泄露

**What goes wrong:** `.env` 文件包含真实 API 密钥（`MINIMAX_API_KEY`），如果意外提交到 Git 或服务器被入侵，密钥泄露。

**Current status:** `.gitignore` 已包含 `.env`，但密钥以明文存储在磁盘上。CONCERNS.md 标记为 CRITICAL 级别。

**Prevention:**
- 立即轮换已暴露的密钥
- 使用 secrets manager（如 1Password CLI、Vault）
- 添加 pre-commit hook 检测密钥提交
- 环境变量注入而非文件存储

**Phase:** Phase 2（安全加固）

---

### Pitfall 12: 生产环境使用 Flask 开发服务器

**What goes wrong:** `main.py:77` 使用 `app.run()` 启动 Werkzeug 开发服务器。这是单线程的，不支持并发，不适合生产环境。

**Consequences:**
- 点击"执行流水线"按钮后，整个 Web 界面冻结直到 pipeline 完成
- 无法处理并发请求
- 无自动重启机制

**Prevention:**
- 使用 gunicorn 或 uvicorn 作为 WSGI 服务器
- Pipeline 执行改为后台异步任务

**Phase:** Phase 1（基础架构加固）

---

## Minor Pitfalls

### Pitfall 13: requests 库阻塞事件循环

**What goes wrong:** `src/crawler/tophub.py` 使用同步的 `requests.get()`，但在异步环境中（如果未来使用 async Flask）会阻塞事件循环。

**Prevention:** 使用 `httpx.AsyncClient` 或 `aiohttp` 替代 requests。

**Phase:** 低优先级，当前同步架构下不影响，但重构为异步时需注意。

---

### Pitfall 14: 没有依赖版本锁定

**What goes wrong:** `requirements.txt` 使用 `>=` 无上限版本范围。依赖库更新引入 breaking change 导致系统崩溃。

**Prevention:**
- 使用 `pip freeze > requirements.lock` 生成锁定文件
- 或使用 poetry/pipenv 管理依赖

**Phase:** Phase 1（基础架构加固）

---

### Pitfall 15: 缺少 Playwright Chromium 安装步骤

**What goes wrong:** `requirements.txt` 包含 `playwright>=1.40.0` 但未记录 `playwright install chromium` 步骤。新环境部署时 Chromium 未安装导致发布失败。

**Prevention:** 在 requirements.txt 中添加注释，或在 `main.py` 中自动检测并提示。

**Phase:** Phase 1（基础架构加固）

---

### Pitfall 16: 日志配置不适合生产环境

**What goes wrong:** 当前使用 `basicConfig`，日志输出到 stdout，无文件轮转。进程重启后日志丢失。

**Prevention:**
- 使用 `dictConfig` 配置日志
- 添加 `RotatingFileHandler`
- 结构化日志格式（JSON）便于后续分析

**Phase:** Phase 1（基础架构加固）

---

### Pitfall 17: Style 关键词匹配大小写不一致

**What goes wrong:** `src/writer/styles.py:70` 对标题做 `lower()` 但中文没有大小写概念。第 73 行用未 lower 的原始标题做关键词匹配。这虽然不导致 bug（因为关键词都是中文），但逻辑不一致。

**Prevention:** 删除不必要的 `lower()` 调用，或统一处理逻辑。

**Phase:** Phase 3（代码质量 / 测试）

---

## Phase-Specific Warnings

| Phase | Likely Pitfall | Mitigation |
|-------|---------------|------------|
| Phase 1: 基础架构加固 | SQLite 并发锁、无重试、开发服务器 | 启用 WAL、添加 tenacity、切换 gunicorn |
| Phase 2: 安全加固 | Cookie 过期、密钥泄露、账号封禁 | Cookie 刷新机制、secrets manager、发布频率控制 |
| Phase 3: 多平台爬取 | IP 封禁、反爬检测、数据源断裂 | 代理池、User-Agent 轮换、聚合 API 备用 |
| Phase 3: 智能风格匹配 | AI 幻觉、敏感内容、解析失败 | 事实核查、敏感词过滤、JSON 输出格式 |
| Phase 4: 全天候运行 | 进程崩溃、无优雅关闭、内存泄漏 | systemd/supervisor、信号处理、定期重启 |
| Phase 5: 测试覆盖 | 以上所有问题因无测试而难以发现 | TDD 流程、80% 覆盖率、集成测试 |

---

## Sources

- 代码库分析：`src/publisher/toutiao_publisher.py`, `src/crawler/tophub.py`, `src/writer/generator.py`, `src/storage/database.py`
- 项目审计：`.planning/codebase/CONCERNS.md`
- 集成分析：`.planning/codebase/INTEGRATIONS.md`
- Playwright 官方文档：https://playwright.dev/python/docs/library
- 头条号开源自动发布参考：https://github.com/InterestWatcher-Xiaofeng/toutiao-auto-publisher

**Confidence notes:**
- 平台反爬措施和头条号封号政策基于行业经验和开源项目中的 issue 讨论，非官方文档确认（LOW confidence 部分，需实际验证）
- SQLite 并发问题和 Playwright 选择器脆弱性是经过验证的技术事实（HIGH confidence）
- AI 幻觉风险是 LLM 领域的已知问题（HIGH confidence）
- 法律合规部分建议咨询专业法律顾问（非法律专业意见）
