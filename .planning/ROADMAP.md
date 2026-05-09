# NewsAgent Roadmap

**Version:** 1.0
**Created:** 2026-05-09
**Granularity:** coarse
**Mode:** yolo
**Requirements:** 33 v1

---

## Phases

- [ ] **Phase 1: Foundation** — 消除全局状态，建立分层架构与测试基础设施
- [ ] **Phase 2: Safety** — 安全加固与发布策略，扩展前解决账号与合规风险
- [ ] **Phase 3: Multi-Source** — 多平台热点聚合，统一爬虫协议与去重
- [ ] **Phase 4: Intelligence** — 智能风格匹配、多角度生成、调度持久化
- [ ] **Phase 5: Production** — 容器化部署、CI/CD、结构化日志、健康检查

---

## Phase Details

### Phase 1: Foundation
**Goal**: 代码库可测试、可扩展、可维护，消除架构技术债
**Depends on**: Nothing
**Requirements**: FOUND-01, FOUND-02, FOUND-03, FOUND-04, FOUND-05, FOUND-06

**Success Criteria** (what must be TRUE):
1. Flask app 通过工厂函数创建，模块级 `_db` 全局变量完全消除，任意模块可独立导入和测试
2. 所有数据访问通过 Database 类方法完成，路由层不包含任何 SQL 语句
3. 路由按功能域组织为独立 Blueprint，新增功能不影响已有路由结构
4. SQLite 并发写入不再死锁，多线程调度可稳定运行
5. `pytest test/` 可执行，conftest.py 提供测试 fixture，首次覆盖率基线可度量
6. 生产环境通过 gunicorn 启动，不再使用 Werkzeug 开发服务器

**Plans**: 5 plans in 5 waves

Plans:
- [ ] 01-01-PLAN.md — 测试基础设施（pytest + conftest.py + smoke test）
- [ ] 01-02-PLAN.md — Database 重构（单连接 + Lock + WAL + 补齐 5 个方法）
- [ ] 01-03-PLAN.md — Application Factory + Blueprint 拆分（create_app + web_bp + api_bp）
- [ ] 01-04-PLAN.md — Pipeline 构造函数注入（create_pipeline + publish.py 适配）
- [ ] 01-05-PLAN.md — gunicorn 部署（gunicorn.conf.py + 信号处理 + 双模式兼容）

### Phase 2: Safety
**Goal**: 发布行为安全可控，账号风险降到最低，内容合规有保障
**Depends on**: Phase 1
**Requirements**: SAFE-01, SAFE-02, SAFE-03, SAFE-04, SAFE-05, SAFE-06, SAFE-07, SAFE-08

**Success Criteria** (what must be TRUE):
1. Playwright 发布时集成 playwright-stealth，头条平台无法检测自动化特征，发布流程不触发风控
2. 单日发布量硬上限 5 篇，发布间隔 30-120 分钟随机化，超限自动停止而非静默失败
3. Cookie 过期时 Web UI 自动弹出通知，用户可及时重新登录，不再发生发布静默失败
4. 敏感词过滤引擎在文章发布前自动扫描，违规内容拦截并通知用户
5. Web 管理界面要求登录，所有 POST 表单携带 CSRF token，未认证请求返回 401
6. 爬虫和 AI API 调用失败时自动指数退避重试，单次网络波动不导致流水线中断

**Plans**: TBD

### Phase 3: Multi-Source
**Goal**: 热点来源从抖音单一平台扩展到微博、知乎、百度，多源自动调度与去重
**Depends on**: Phase 2
**Requirements**: MULTI-01, MULTI-02, MULTI-03, MULTI-04, MULTI-05, MULTI-06, MULTI-07, MULTI-08, MULTI-09

**Success Criteria** (what must be TRUE):
1. 新增爬虫只需实现 CrawlerProtocol 接口并注册到 Registry，无需修改调度和流水线代码
2. 微博、知乎、百度三个平台的热搜可通过各自适配器独立抓取，返回统一 HotTopic 格式
3. DailyHotApi 服务容器化部署并可访问，作为热点数据的补充来源
4. 同一热点事件在不同平台被识别为重复，流水线自动去重并从不同角度生成差异化文章
5. 调度流水线遍历所有已注册爬虫，自动完成多源抓取，用户无需手动指定平台

**Plans**: TBD

### Phase 4: Intelligence
**Goal**: AI 生成内容质量提升，风格更匹配，热点覆盖更全面
**Depends on**: Phase 3
**Requirements**: INTEL-01, INTEL-02, INTEL-03, INTEL-04, INTEL-05

**Success Criteria** (what must be TRUE):
1. 系统自动分析热点话题性质（娱乐/科技/社会/财经），选择最匹配的写作风格生成文章，无需人工指定
2. 同一热点话题可从多个角度生成多篇差异化文章，每篇内容和立场明显不同
3. 跨平台同一事件被识别并关联，生成统一的话题分组，避免重复生产
4. 调度器任务持久化到数据库，服务重启后任务不丢失，24/7 运行可靠
5. MiniMax API 不可用时，系统自动切换到 DeepSeek 生成文章，用户感知到的中断时间小于 1 分钟

**Plans**: TBD

### Phase 5: Production
**Goal**: 系统可容器化部署，有 CI/CD 保障，日志可观测，健康状态可监控
**Depends on**: Phase 4
**Requirements**: PROD-01, PROD-02, PROD-03, PROD-04, PROD-05

**Success Criteria** (what must be TRUE):
1. `docker-compose up` 一键启动全部服务（应用 + DailyHotApi），无需手动配置环境
2. 日志输出为结构化格式，包含时间戳、模块名，日志级别，按大小自动轮转，可通过日志追踪一次完整流水线执行
3. GitHub Actions 在每次 push 时自动运行测试和 lint，失败时阻止合并
4. 项目测试覆盖率达到 80% 以上，覆盖所有核心模块
5. `/health` 端点返回服务状态、数据库连接状态、调度器运行状态，外部监控可探测

**Plans**: TBD

---

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 0/5 | Ready to execute | - |
| 2. Safety | 0/8 | Not started | - |
| 3. Multi-Source | 0/9 | Not started | - |
| 4. Intelligence | 0/5 | Not started | - |
| 5. Production | 0/5 | Not started | - |

---

## Requirement Coverage Map

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 | Phase 1 | Pending |
| FOUND-02 | Phase 1 | Pending |
| FOUND-03 | Phase 1 | Pending |
| FOUND-04 | Phase 1 | Pending |
| FOUND-05 | Phase 1 | Pending |
| FOUND-06 | Phase 1 | Pending |
| SAFE-01 | Phase 2 | Pending |
| SAFE-02 | Phase 2 | Pending |
| SAFE-03 | Phase 2 | Pending |
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

## Dependency Chain

```
Phase 1 (Foundation)    — 无依赖，立即开始
  └─→ Phase 2 (Safety)  — 依赖架构重构完成
       └─→ Phase 3 (Multi-Source)  — 依赖安全加固完成
            └─→ Phase 4 (Intelligence)  — 依赖多平台爬虫就绪
                 └─→ Phase 5 (Production)  — 依赖全部功能完成
```

---

*Next command: `/gsd-execute-phase 01-foundation`*
