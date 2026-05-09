# Phase 3: Multi-Source - Discussion Log

**Date:** 2026-05-09
**Mode:** --auto

## Areas Discussed

### 1. CrawlerProtocol 设计
- **Question:** 爬虫协议用什么方式定义?
- **Options:** Python Protocol / ABC 抽象基类 / duck typing（无显式协议）
- **Selected:** Python Protocol (recommended) — 无需继承即可类型检查，符合项目 duck typing 风格

### 2. HotTopic 统一格式
- **Question:** 统一数据结构用 dataclass 还是 dict?
- **Options:** frozen dataclass / TypedDict / 保持 dict
- **Selected:** frozen dataclass (recommended) — 类型安全 + 不可变性 + 字段自动补全

### 3. 爬虫注册机制
- **Question:** 新爬虫如何注册到系统?
- **Options:** 模块级列表 + register_crawler() / 装饰器自动扫描 / 配置文件声明
- **Selected:** 模块级列表 + register_crawler() (recommended) — 简单直观，无魔法

### 4. DailyHotApi 部署方式
- **Question:** DailyHotApi 怎么部署?
- **Options:** Docker Compose 集成 / 独立部署 / 不部署直接用在线 API
- **Selected:** Docker Compose 集成 (recommended) — 与主应用一起管理

### 5. 跨平台去重策略
- **Question:** 用什么方式去重?
- **Options:** 标题相似度 (difflib) / 语义向量 (sentence-transformers) / 精确匹配
- **Selected:** 标题相似度 difflib (recommended) — 纯标准库，无重型依赖，0.6 阈值

### 6. 数据源调度策略
- **Question:** 原生爬虫和 DailyHotApi 的优先级?
- **Options:** 原生爬虫优先 + DailyHotApi 补充 / 仅用 DailyHotApi / 仅用原生爬虫
- **Selected:** 原生爬虫优先 + DailyHotApi 补充 (recommended) — 数据更实时，兜底防故障

## Deferred Ideas
- 语义向量去重 → Phase 4 Intelligence
- DailyHotApi 降级为直连 API → v2 Requirements
- 更多平台爬虫（B站、36氪等）→ v2 Requirements

---
*Auto mode: all gray areas auto-resolved with recommended defaults*
