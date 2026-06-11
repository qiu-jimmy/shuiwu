"""
日志配置模块
提供统一的日志配置和logger获取功能
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import Optional


# 日志级别映射
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

# 默认日志格式
DETAILED_FORMAT = (
    "[%(asctime)s] [%(levelname)s] [%(name)s:%(funcName)s:%(lineno)d] "
    "%(message)s"
)
SIMPLE_FORMAT = "[%(asctime)s] [%(levelname)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class LoggingConfig:
    """日志配置类"""

    def __init__(
        self,
        log_dir: str = "logs",
        level: str = "INFO",
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        enable_console: bool = True,
        enable_file: bool = True,
        use_time_rotation: bool = False
    ):
        """
        初始化日志配置

        Args:
            log_dir: 日志文件目录
            level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            max_bytes: 单个日志文件最大字节数
            backup_count: 保留的备份文件数量
            enable_console: 是否输出到控制台
            enable_file: 是否输出到文件
            use_time_rotation: 是否使用时间轮转 (否则使用大小轮转)
        """
        self.log_dir = Path(log_dir)
        self.level = LOG_LEVELS.get(level.upper(), logging.INFO)
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.enable_console = enable_console
        self.enable_file = enable_file
        self.use_time_rotation = use_time_rotation

        # 创建日志目录
        if self.enable_file:
            self.log_dir.mkdir(parents=True, exist_ok=True)

    def get_logger(
        self,
        name: str,
        log_file: Optional[str] = None,
        level: Optional[int] = None,
        format_string: Optional[str] = None
    ) -> logging.Logger:
        """
        获取配置好的logger实例

        Args:
            name: logger名称
            log_file: 日志文件名 (可选，不指定则使用通用日志)
            level: 覆盖默认日志级别 (可选)
            format_string: 自定义格式字符串 (可选)

        Returns:
            配置好的logger实例
        """
        logger = logging.getLogger(name)

        # 避免重复添加handler
        if logger.handlers:
            return logger

        logger.setLevel(level or self.level)
        log_format = format_string or DETAILED_FORMAT
        formatter = logging.Formatter(log_format, datefmt=DATE_FORMAT)

        # 控制台处理器（同时输出到 stdout 和 stderr）
        if self.enable_console:
            # stdout handler - 正常日志
            stdout_handler = logging.StreamHandler(sys.stdout)
            stdout_handler.setLevel(level or self.level)
            stdout_handler.setFormatter(formatter)
            logger.addHandler(stdout_handler)

            # stderr handler - 错误和警告（确保异常信息可见）
            stderr_handler = logging.StreamHandler(sys.stderr)
            stderr_handler.setLevel(logging.WARNING)  # 只输出 WARNING 及以上级别
            stderr_handler.setFormatter(formatter)
            logger.addHandler(stderr_handler)

        # 文件处理器
        if self.enable_file:
            if log_file:
                file_path = self.log_dir / log_file
            else:
                file_path = self.log_dir / "app.log"

            if self.use_time_rotation:
                # 按时间轮转 (每天午夜创建新文件)
                file_handler = TimedRotatingFileHandler(
                    file_path,
                    when="midnight",
                    interval=1,
                    backupCount=self.backup_count,
                    encoding="utf-8"
                )
                file_handler.suffix = "%Y-%m-%d"
            else:
                # 按大小轮转
                file_handler = RotatingFileHandler(
                    file_path,
                    maxBytes=self.max_bytes,
                    backupCount=self.backup_count,
                    encoding="utf-8"
                )

            file_handler.setLevel(level or self.level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        # 防止日志传播到root logger
        logger.propagate = False

        return logger


# 全局日志配置实例
_logging_config: Optional[LoggingConfig] = None


def init_logging(
    log_dir: str = "logs",
    level: str = "INFO",
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
    enable_console: bool = True,
    enable_file: bool = True
) -> LoggingConfig:
    """
    初始化全局日志配置

    Args:
        log_dir: 日志目录
        level: 日志级别
        max_bytes: 单文件最大大小
        backup_count: 备份文件数量
        enable_console: 是否启用控制台输出
        enable_file: 是否启用文件输出

    Returns:
        LoggingConfig实例
    """
    global _logging_config
    _logging_config = LoggingConfig(
        log_dir=log_dir,
        level=level,
        max_bytes=max_bytes,
        backup_count=backup_count,
        enable_console=enable_console,
        enable_file=enable_file
    )

    # 配置root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(_logging_config.level)

    # 清除root logger的默认handlers
    root_logger.handlers.clear()

    return _logging_config


def get_logger(
    name: str,
    log_file: Optional[str] = None,
    level: Optional[int] = None,
    silent: bool = False
) -> logging.Logger:
    """
    获取logger实例

    Args:
        name: logger名称 (通常使用 __name__)
        log_file: 特定日志文件名 (可选)
        level: 覆盖日志级别 (可选)
        silent: 如果True，在未初始化时返回默认logger而不警告

    Returns:
        logger实例
    """
    global _logging_config

    if _logging_config is None:
        if not silent:
            # 自动初始化默认配置
            init_logging()
        else:
            # 返回未配置的logger
            return logging.getLogger(name)

    return _logging_config.get_logger(name, log_file=log_file, level=level)


# 预定义的logger获取函数
def get_exception_logger() -> logging.Logger:
    """获取异常日志专用logger"""
    return get_logger("app.exception", log_file="exception.log", level=logging.ERROR)


def get_api_logger() -> logging.Logger:
    """获取API请求日志专用logger"""
    return get_logger("app.api", log_file="api.log")


def get_db_logger() -> logging.Logger:
    """获取数据库操作日志专用logger"""
    return get_logger("app.database", log_file="database.log")


def get_mcp_logger() -> logging.Logger:
    """获取MCP服务日志专用logger"""
    return get_logger("app.mcp", log_file="mcp.log")


def get_agent_logger() -> logging.Logger:
    """获取Agent运行日志专用logger"""
    return get_logger("app.agent", log_file="agent.log")


def get_payment_logger() -> logging.Logger:
    """获取支付回调日志专用logger"""
    return get_logger("app.payment", log_file="payment.log")
