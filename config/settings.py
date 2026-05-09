"""项目配置：从环境变量读取所有配置项"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

# 今日热榜 API
TOPHUB_API_KEY = os.getenv("TOPHUB_API_KEY", "")
TOPHUB_BASE_URL = "https://api.tophubdata.com"
DOUYIN_NODE_HASHID = os.getenv("DOUYIN_NODE_HASHID", "")

# MiniMax API
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")
MINIMAX_BASE_URL = "https://api.minimax.io/v1"
MINIMAX_MODEL = "MiniMax-M2.7"

# RSS 服务
RSS_HOST = os.getenv("RSS_HOST", "0.0.0.0")
RSS_PORT = int(os.getenv("RSS_PORT", "5000"))
RSS_BASE_URL = os.getenv("RSS_BASE_URL", "http://localhost:5000")

# 文章风格
DEFAULT_STYLE = os.getenv("DEFAULT_STYLE", "auto")
MAX_TOPICS_PER_RUN = int(os.getenv("MAX_TOPICS_PER_RUN", "5"))

# 数据库
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "newsagent.db")

# Web 管理认证
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

# 环境变量校验
REQUIRED_VARS = ["MINIMAX_API_KEY", "TOPHUB_API_KEY"]
OPTIONAL_VARS = ["ADMIN_PASSWORD", "SECRET_KEY", "DOUYIN_NODE_HASHID"]


def validate_config():
    """启动时校验必填环境变量，缺失则退出"""
    missing = [v for v in REQUIRED_VARS if not os.getenv(v)]
    if missing:
        for var in missing:
            print(f"[FATAL] 缺少必填环境变量: {var}")
        sys.exit(1)

    unset = [v for v in OPTIONAL_VARS if not os.getenv(v)]
    for var in unset:
        print(f"[WARN] 未设置可选环境变量: {var}")
