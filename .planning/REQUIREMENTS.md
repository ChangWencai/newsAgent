# Requirements

## v1 Requirements

### 基础架构 (Foundation)

- [ ] **FOUND-01**: Flask Application Factory 模式，消除模块级全局 `_db` 变量，通过工厂函数创建 app 实例
- [ ] **FOUND-02**: Database 类补齐所有数据访问方法，路由层零 SQL 直接操作
- [ ] **FOUND-03**: Flask Blueprint 路由组织，按功能域拆分路由模块
- [ ] **FOUND-04**: SQLite WAL 模式 + threading.Lock 写锁序列化，解决并发写入死锁
- [ ] **FOUND-05**: pyproject.toml + conftest.py 测试基础设施，引入 pytest
- [ ] **FOUND-06**: gunicorn 替换 Werkzeug 开发服务器用于生产部署

### 安全加固 (Safety)

- [ ] **SAFE-01**: playwright-stealth 集成，添加浏览器反检测指纹伪装
- [x] **SAFE-02**: 发布频率控制，每日上限 ≤5 篇，发布间隔 30-120 分钟随机化
- [x] **SAFE-03**: Cookie 有效性检测 + 过期自动通知，防止发布失败静默
- [ ] **SAFE-04**: API 密钥从 .env 迁移到安全的环境变量管理
- [ ] **SAFE-05**: Web UI 登录认证 + CSRF 防护
- [ ] **SAFE-06**: 敏感词过滤引擎，AI 生成内容发布前自动检测违规词
- [ ] **SAFE-07**: 选择器健壮性改进，CSS class 选择器替换为 role 语义定位器
- [ ] **SAFE-08**: tenacity 重试机制，爬虫和 AI API 调用指数退避重试

### 多平台聚合 (Multi-Source)

- [ ] **MULTI-01**: CrawlerProtocol 协议接口定义，标准化爬虫行为
- [ ] **MULTI-02**: HotTopic 数据结构定义，统一各平台返回格式
- [ ] **MULTI-03**: 爬虫注册机制，平台适配器通过 Registry 自动注册
- [ ] **MULTI-04**: DailyHotApi Docker 部署，覆盖 45+ 平台热榜聚合
- [ ] **MULTI-05**: 微博热搜爬虫适配器
- [ ] **MULTI-06**: 知乎热榜爬虫适配器
- [ ] **MULTI-07**: 百度热搜爬虫适配器
- [ ] **MULTI-08**: 跨平台语义级去重，同一热点从不同角度生成文章
- [ ] **MULTI-09**: 流水线遍历所有注册爬虫，自动调度多源抓取

### 智能内容 (Intelligence)

- [ ] **INTEL-01**: 智能风格-话题匹配，LLM 分析话题性质自动选择写作风格
- [ ] **INTEL-02**: 多角度文章生成，同一热点从不同角度生成多篇
- [ ] **INTEL-03**: 热点话题分组与关联，识别跨平台同一事件
- [ ] **INTEL-04**: 24/7 调度优化，APScheduler + SQLAlchemyJobStore 持久化
- [ ] **INTEL-05**: DeepSeek fallback，MiniMax 不可用时自动切换

### 生产就绪 (Production)

- [ ] **PROD-01**: Dockerfile + docker-compose.yml 容器化部署
- [ ] **PROD-02**: 结构化日志（dictConfig + RotatingFileHandler）
- [ ] **PROD-03**: GitHub Actions CI/CD 流水线
- [ ] **PROD-04**: 80% 测试覆盖率（单元测试 + 集成测试）
- [ ] **PROD-05**: 健康检查端点 (/health)

## v2 Requirements

- [ ] 数据分析与收益追踪面板（阅读量、推荐量、收益趋势）
- [ ] 发布时间优化（根据头条推荐算法高峰时段发布）
- [ ] 更多平台爬虫（B站、36氪、澎湃等）
- [ ] AI 内容质量评分机制
- [ ] DailyHotApi 降级为直连 API fallback 策略

## Out of Scope

- 多平台同时发布（微信公众号、微博等） — 聚焦头条单平台
- 视频/图片自动生成 — 仅做文本内容生产
- 自动生成评论/互动 — 不涉及评论区运营
- 付费订阅功能 — 以广告流量变现为主
- 全自动无人工审核（已修正） — 高风险内容需合规检查

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 | Phase 1 | Pending |
| FOUND-02 | Phase 1 | Pending |
| FOUND-03 | Phase 1 | Pending |
| FOUND-04 | Phase 1 | Pending |
| FOUND-05 | Phase 1 | Pending |
| FOUND-06 | Phase 1 | Pending |
| SAFE-01 | Phase 2 | Pending |
| SAFE-02 | Phase 2 | Complete |
| SAFE-03 | Phase 2 | Complete |
| SAFE-04 | Phase 2 | Pending |
| SAFE-05 | Phase 2 | Pending |
| SAFE-06 | Phase 2 | Pending |
| SAFE-07 | Phase 2 | Pending |
| SAFE-08 | Phase 2 | Pending |
| MULTI-01 | Phase 3 | Pending |
| MULTI-02 | Phase 3 | Pending |
| MULTI-03 | Phase 3 | Pending |
| MULTI-04 | Phase 3 | Pending |
| MULTI-05 | Phase 3 | Pending |
| MULTI-06 | Phase 3 | Pending |
| MULTI-07 | Phase 3 | Pending |
| MULTI-08 | Phase 3 | Pending |
| MULTI-09 | Phase 3 | Pending |
| INTEL-01 | Phase 4 | Pending |
| INTEL-02 | Phase 4 | Pending |
| INTEL-03 | Phase 4 | Pending |
| INTEL-04 | Phase 4 | Pending |
| INTEL-05 | Phase 4 | Pending |
| PROD-01 | Phase 5 | Pending |
| PROD-02 | Phase 5 | Pending |
| PROD-03 | Phase 5 | Pending |
| PROD-04 | Phase 5 | Pending |
| PROD-05 | Phase 5 | Pending |

**Coverage: 33/33 requirements mapped (100%)**

---
*Last updated: 2026-05-09 after roadmap creation*
