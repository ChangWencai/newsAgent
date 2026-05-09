# Phase 01 Plan 05: gunicorn 生产部署 Summary

**一句话总结：** gunicorn 替代 Werkzeug 开发服务器，单 worker + 4 线程 + atexit/signal 安全退出机制

---

| 项目 | 值 |
|------|-----|
| Phase | 01-foundation |
| Plan | 05 |
| Subsystem | 部署 / 运行时 |
| 需求覆盖 | FOUND-06 |
| 依赖 | Plan 04 (Pipeline 构造函数注入) |
| 提供 | 生产 WSGI 服务器、安全退出机制 |
| 技术栈 | gunicorn 23.0.0, gthread worker, Python signal/atexit |
| 关键文件 | gunicorn.conf.py (新建), main.py (修改), requirements.txt (修改) |
| 关键决策 | 单 worker 避免 APScheduler 重复调度；gthread 多线程提升 Web 并发 |

---

## 完成任务

| # | 任务 | Commit | 状态 |
|---|------|--------|------|
| 1 | 创建 gunicorn.conf.py 配置文件 | e5b1f26 | DONE |
| 2 | main.py 添加信号处理和双模式兼容 | 70e8cf2 | DONE |
| 3 | requirements.txt 添加 gunicorn>=23.0.0 | 2a315a0 | DONE |

## 关键实现

### gunicorn.conf.py
- `bind`: 使用 `config.settings.RSS_HOST:RSS_PORT`（当前 0.0.0.0:8081）
- `workers = 1`: 单进程避免 APScheduler 在多个 worker 中重复调度
- `threads = 4`: gthread worker 多线程提升 Web 并发
- `timeout = 300`: 适配 pipeline 可能的长时间执行
- `proc_name = "newsagent"`: 进程名称标识

### main.py 信号处理
- `import atexit` + `import signal` 新增导入
- `atexit.register(lambda: scheduler.shutdown(wait=True))`: 进程正常退出时关闭调度器
- `SIGTERM`/`SIGINT` 信号处理器: 捕获终止信号，优雅关闭 scheduler 后退出
- `create_app` 保持模块级函数: gunicorn 通过 `main:create_app` 导入
- `if __name__ == "__main__": main()` 保持不变: `python main.py` 开发模式兼容

### 启动方式
```bash
# 生产模式
gunicorn -c gunicorn.conf.py main:create_app

# 开发模式（保持兼容）
python main.py
```

## 验证结果

- [x] gunicorn.conf.py 存在，workers=1, threads=4, worker_class=gthread
- [x] main.py 包含 import atexit 和 import signal
- [x] atexit.register 已注册 scheduler.shutdown
- [x] SIGTERM/SIGINT 信号处理器已注册
- [x] create_app 是模块级函数
- [x] gunicorn 可启动并正常关闭（端口 18081 验证通过）
- [x] python main.py 开发模式仍正常工作
- [x] requirements.txt 包含 gunicorn>=23.0.0
- [x] 全部 40 个测试通过

## 偏差

无。计划完全按设计执行。

## 已知存根

无。

## 威胁标记

无新增安全表面。gunicorn 配置不引入新的网络端点或认证路径。

---

## Self-Check: PASSED

- gunicorn.conf.py 存在: OK
- main.py 修改（atexit + signal）: OK
- requirements.txt 包含 gunicorn: OK
- Commit e5b1f26 存在: OK
- Commit 70e8cf2 存在: OK
- Commit 2a315a0 存在: OK
- 40 个测试全部通过: OK
