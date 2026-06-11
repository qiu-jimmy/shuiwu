import os
import warnings

# 必须在导入任何模块之前设置,才能禁用第三方库的警告
os.environ["PYDANTIC_DISABLE_WARNINGS"] = "1"
warnings.filterwarnings("ignore", category=UserWarning)

import uvicorn

if __name__ == "__main__":
    # 后端入口，统一从这里启动 uvicorn，指向 app.main:app
    # 命令：python main.py
    print(" 启动服务器...")
    print(" API文档: http://127.0.0.1:8001/docs")
    print(" ReDoc文档: http://127.0.0.1:8001/redoc")
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
        port=8001,
        reload=False,
        log_config=log_config,
        log_level="info",
        # 关键配置：提升并发处理能力
        workers=1,  # 开发环境使用单进程（reload=True时不支持多进程）
        limit_concurrency=100,  # 最大并发连接数
        limit_max_requests=1000,  # 每个worker处理的最大请求数（防止内存泄漏）
        timeout_keep_alive=30,  # 保持连接的超时时间（秒）
        # ssl_keyfile="/etc/letsencrypt/live/dragon.cishoon.top/privkey.pem",    # 私钥路径
        # ssl_certfile="/etc/letsencrypt/live/dragon.cishoon.top/fullchain.pem"  # 证书路径
    )

