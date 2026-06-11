"""
生产环境启动脚本

使用多进程模式提升并发处理能力

启动命令：
python main_production.py
"""
import os
import warnings

# 必须在导入任何模块之前设置,才能禁用第三方库的警告
os.environ["PYDANTIC_DISABLE_WARNINGS"] = "1"
warnings.filterwarnings("ignore", category=UserWarning)

import uvicorn

if __name__ == "__main__":
    print(" 启动生产环境服务器...")
    print(" API文档: http://127.0.0.1:8000/docs")
    print(" ReDoc文档: http://127.0.0.1:8000/redoc")
    print(" 多进程模式：启用 4 个工作进程")
    print()

    # 配置 uvicorn 日志
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "uvicorn.logging.DefaultFormatter",
                "fmt": "%(levelprefix)s %(message)s",
                "use_colors": True,
            },
            "access": {
                "()": "uvicorn.logging.AccessFormatter",
                "fmt": '%(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
            "access": {
                "formatter": "access",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": "INFO"},
            "uvicorn.error": {"level": "INFO"},
            "uvicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": False},
        },
    }

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # 生产环境关闭自动重载
        log_config=log_config,
        log_level="info",
        # 生产环境关键配置
        workers=4,  # 4个工作进程（推荐设置为 CPU 核心数）
        limit_concurrency=200,  # 每个worker最大并发连接数（总共可处理 800 个并发）
        limit_max_requests=10000,  # 每个worker处理的最大请求数后自动重启（防止内存泄漏）
        timeout_keep_alive=30,  # 保持连接的超时时间（秒）
        backlog=2048,  # 最大等待连接数
    )
