# Phase 2: Safety - Discussion Log

**Date:** 2026-05-09
**Mode:** --auto

## Areas Discussed

### 1. 发布频率持久化
- **Question:** 频率计数器存储在哪里?
- **Options:** SQLite 计数器 / 独立速率管理器 / APScheduler 内置
- **Selected:** SQLite 计数器 (recommended) — 利用已有 Database 类，无需新组件

### 2. Cookie 过期通知
- **Question:** 如何检测 cookie 过期并通知用户?
- **Options:** 主动健康检查 / 被动失败检测
- **Selected:** 主动健康检查端点 (recommended) — /health 返回 cookie_status，Web UI 轮询

### 3. 密钥管理
- **Question:** 如何安全存储 API 密钥?
- **Options:** .env + dotenv / secrets manager / 完全自定义
- **Selected:** .env + dotenv + .env.example (recommended) — 项目已有此模式，添加启动验证

### 4. Web UI 认证
- **Question:** Web UI 用什么认证方案?
- **Options:** HTTP Basic Auth / 密码表单 + Flask session / Flask-Login
- **Selected:** 密码表单 + Flask session (recommended) — 单用户场景，简单够用

### 5. CSRF 防护
- **Question:** 如何实现 CSRF 保护?
- **Options:** Flask-WTF CSRFProtect / 自定义 token
- **Selected:** Flask-WTF CSRFProtect (recommended) — 自动注入和验证

### 6. 敏感词数据源
- **Question:** 敏感词列表如何管理?
- **Options:** 外部文件 / 硬编码列表 / 在线 API
- **Selected:** 外部文件 data/sensitive_words.txt (recommended) — 可热更新

### 7. 重试策略
- **Question:** tenacity 怎么配?
- **Options:** 指数退避 3 次 / 固定间隔 / 仅网络错误
- **Selected:** 指数退避 3 次 (recommended) — retry=3, wait=exponential(1,10)

### 8. 选择器健壮性
- **Question:** 怎么改选择器?
- **Options:** 优先 role 语义定位器 / 混合策略 / 仅加错误处理
- **Selected:** 优先 role 语义定位器 (recommended) — Playwright get_by_role 替代 CSS class

## Deferred Ideas
None

---
*Auto mode: all gray areas auto-resolved with recommended defaults*
