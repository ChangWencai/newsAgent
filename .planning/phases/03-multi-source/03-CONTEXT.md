# Phase 3: Multi-Source - Context

**Gathered:** 2026-05-09
**Mode:** --auto (自动选择推荐方案)

<domain>
## Phase Boundary

热点来源从抖音单一平台扩展到微博、知乎、百度，多源自动调度与去重。涵盖 9 个子系统：爬虫协议接口、统一数据结构、爬虫注册机制、DailyHotApi 部署、微博/知乎/百度适配器、跨平台去重、多源流水线调度。

Phase 1+2 已完成：Application Factory + Blueprint + Database 重构 + 安全加固（认证、CSRF、频率控制、敏感词、重试、反检测）。现有 DouyinCrawler 通过 `get_hot_list()` 返回 `List[Dict]`，pipeline 只需爬虫实现此方法即可。hot_topics 表已有 `category` 字段，无需修改 schema 即可支持多源。

</domain>

<decisions>
## Implementation Decisions

### CrawlerProtocol 协议接口 (MULTI-01)
- **D-01:** 使用 Python `typing.Protocol` 定义 `CrawlerProtocol`，声明 `get_hot_list() -> list[HotTopic]` 方法。Protocol 优于 ABC，因为无需继承即可获得类型检查，符合现有 duck typing 风格。
- **D-02:** 协议方法签名：`def get_hot_list(self) -> list[HotTopic]: ...`。返回值从 `list[dict]` 升级为 `list[HotTopic]` dataclass，提供类型安全和字段自动补全。

### HotTopic 统一数据结构 (MULTI-02)
- **D-03:** 使用 `@dataclass(frozen=True)` 定义 `HotTopic`，字段：`title: str`, `url: str`, `source: str`, `hot_value: str = ""`, `category: str = ""`, `fetched_at: str = ""`。frozen=True 保证不可变性，符合项目编码规范。
- **D-04:** `source` 字段标识数据来源平台（如 "douyin", "weibo", "zhihu", "baidu", "dailyhot"），用于去重和统计。`fetched_at` 可选填充，pipeline 插入 DB 时自动设置。
- **D-05:** HotTopic 定义在 `src/crawler/models.py` 新文件中，所有爬虫和 pipeline 共同引用。

### 爬虫注册机制 (MULTI-03)
- **D-06:** 使用模块级 `CRAWLERS` 列表 + `register_crawler()` 函数的注册模式。每个爬虫模块末尾调用 `register_crawler(WeiboCrawler())` 自动注册。Pipeline 通过 `get_registered_crawlers()` 获取所有已注册爬虫。
- **D-07:** 注册中心定义在 `src/crawler/__init__.py` 中，包含 `CRAWLERS: list[CrawlerProtocol] = []`、`register_crawler(crawler)`、`get_registered_crawlers()` 三个导出。
- **D-08:** 现有 DouyinCrawler 也需迁移到新协议，在 `tophub.py` 末尾调用 `register_crawler()`，返回值升级为 `list[HotTopic]`。

### DailyHotApi 部署 (MULTI-04)
- **D-09:** 使用 Docker Compose 集成 DailyHotApi 服务。在 `docker-compose.yml` 中添加 DailyHotApi 容器，暴露端口 6688。应用通过 HTTP API (`http://dailyhot:6688/{platform}`) 获取各平台热榜。
- **D-10:** 创建 `src/crawler/dailyhot.py` 适配器，封装 DailyHotApi HTTP 调用，实现 CrawlerProtocol，支持按平台参数获取不同热榜。作为原生爬虫的补充数据源。

### 平台适配器 (MULTI-05/06/07)
- **D-11:** 微博热搜适配器 `src/crawler/weibo.py`：通过 DailyHotApi `/weibo` 端点获取数据，返回 `list[HotTopic]`，source="weibo"。
- **D-12:** 知乎热榜适配器 `src/crawler/zhihu.py`：通过 DailyHotApi `/zhihu` 端点获取数据，返回 `list[HotTopic]`，source="zhihu"。
- **D-13:** 百度热搜适配器 `src/crawler/baidu.py`：通过 DailyHotApi `/baidu` 端点获取数据，返回 `list[HotTopic]`，source="baidu"。
- **D-14:** 所有适配器统一通过 DailyHotApi 获取（降低被封风险），后续如需直连可扩展为双模式。

### 跨平台去重 (MULTI-08)
- **D-15:** 使用 `difflib.SequenceMatcher` 实现标题相似度去重，阈值 0.6（即 60% 相似度视为同一事件）。纯标准库实现，无需安装 sentence-transformers 等重型依赖。
- **D-16:** 去重在 pipeline 层执行：收集所有爬虫的 HotTopic 后，按标题相似度分组，每组保留热度最高的条目，其余标记为去重跳过。
- **D-17:** Database 类添加 `find_similar_topics(title, threshold=0.6) -> list[dict]` 方法，查询已存在的话题中与给定标题相似的记录。Pipeline 在 insert_topic 前调用检查。

### 多源调度 (MULTI-09)
- **D-18:** Pipeline 从单一爬虫调用改为遍历 `get_registered_crawlers()`，收集所有平台的 HotTopic 后统一去重和处理。`create_pipeline(db)` 签名变更：不再接收 `crawler` 参数，改为内部获取注册爬虫列表。
- **D-19:** 每个爬虫独立 try/except，单个平台失败不影响其他平台。失败时记录日志并继续。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 项目文档
- `.planning/PROJECT.md` — 项目整体上下文、技术栈、已知问题
- `.planning/REQUIREMENTS.md` — MULTI-01~09 需求定义
- `.planning/STATE.md` — 当前进度和关键决策

### Phase 1+2 产出（本阶段依赖）
- `src/crawler/tophub.py` — 现有 DouyinCrawler 实现（get_hot_list 返回格式参考）
- `src/scheduler/jobs.py` — 现有 pipeline 编排（create_pipeline 工厂函数）
- `src/storage/database.py` — Database 类（topic_exists, insert_topic 等方法）
- `src/writer/generator.py` — ArticleGenerator（generate_article 接口）

### 外部服务
- DailyHotApi — GitHub: imsyy/DailyHotApi，Docker 镜像可用，覆盖 45+ 平台热榜

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- DouyinCrawler.get_hot_list() 返回 `List[Dict]`，已有 title/url/hot_value/category 字段，可直接映射到 HotTopic dataclass
- create_pipeline(crawler, writer, db) 工厂函数已建立，可扩展为多源遍历
- Database 类 topic_exists(title) 方法可直接用于基础去重
- hot_topics 表已有 category 字段，天然支持多源标识

### Established Patterns
- 工厂函数注入：`create_pipeline(crawler, writer, db)`, `create_web_bp(db)`
- Database 方法模式：`_execute_read` / `_execute_write` 统一封装
- 常量配置：`config/settings.py` 大写蛇形常量，`os.getenv()` 带默认值
- 测试模式：conftest.py 提供 db/app fixtures，pytest -x -v 验证

### Integration Points
- `main.py` 中 `run_pipeline(db)` 调用 pipeline，需适配新的多源 pipeline
- `config/settings.py` 需新增 DailyHotApi 相关配置项
- Docker Compose 文件需新建

</code_context>

<specifics>
## Specific Ideas

- DailyHotApi 作为补充数据源，原生爬虫优先（数据更实时），DailyHotApi 在原生爬虫失败时兜底
- 去重先实现标题相似度方案（标准库），如后续需要语义级去重可在 Phase 4 Intelligence 中升级
- 爬虫注册使用简单的列表模式，不引入复杂的插件系统
- Docker Compose 文件可先创建骨架，Phase 5 Production 中完善

</specifics>

<deferred>
## Deferred Ideas

- 语义向量去重（需 sentence-transformers 等重型依赖）→ 延后到 Phase 4 Intelligence
- DailyHotApi 降级为直连 API fallback 策略 → 已在 v2 Requirements 中
- 更多平台爬虫（B站、36氪、澎湃等）→ 已在 v2 Requirements 中

</deferred>

---

*Phase: 3-Multi-Source*
*Context gathered: 2026-05-09 (auto mode)*
