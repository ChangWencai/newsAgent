"""NewsAgent 主入口"""

import argparse
import logging
import sys
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
from config.settings import RSS_HOST, RSS_PORT, DB_PATH
from src.storage.database import Database
from src.scheduler.jobs import run_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app(db=None, db_path=None):
    """Application Factory：创建 Flask 应用

    无参调用时（gunicorn main:create_app）内部自动创建 db。
    传入 db 时复用同一 db 实例。
    """
    app = Flask(
        __name__,
        template_folder="src/web/templates",
        static_folder="src/web/static",
    )

    if db is None:
        db = Database(db_path or DB_PATH)

    from src.web.routes import create_web_bp, create_api_bp

    app.register_blueprint(create_web_bp(db))
    app.register_blueprint(create_api_bp(db))

    return app


def main():
    parser = argparse.ArgumentParser(description="NewsAgent - AI热点新闻自动生产系统")
    parser.add_argument("--run-once", action="store_true", help="执行一次流水线后退出")
    parser.add_argument("--port", type=int, default=RSS_PORT, help="服务端口")
    parser.add_argument("--host", default=RSS_HOST, help="服务监听地址")
    args = parser.parse_args()

    db = Database(DB_PATH)

    if args.run_once:
        logger.info("单次执行模式")
        run_pipeline(db)
        sys.exit(0)

    # 启动定时任务
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_pipeline,
        "interval",
        hours=6,
        args=[db],
        id="news_pipeline",
        name="新闻生产流水线",
    )
    scheduler.start()
    logger.info("定时任务已启动（每6小时执行一次）")

    # 启动 Web + RSS 服务
    app = create_app(db=db)
    logger.info("服务启动: http://%s:%s", args.host, args.port)
    logger.info("Web 管理: http://%s:%s/", args.host, args.port)
    logger.info("RSS 订阅: http://%s:%s/rss", args.host, args.port)
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
