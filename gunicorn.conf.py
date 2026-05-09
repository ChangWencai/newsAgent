"""gunicorn 配置文件"""
from config.settings import RSS_HOST, RSS_PORT

# 绑定地址
bind = f"{RSS_HOST}:{RSS_PORT}"

# 单 worker + 多线程（避免 APScheduler 重复调度）
workers = 1
threads = 4
worker_class = "gthread"

# 日志
accesslog = "-"
errorlog = "-"
loglevel = "info"

# 超时（pipeline 可能执行较长时间）
timeout = 300
graceful_timeout = 30

# 进程名称
proc_name = "newsagent"
