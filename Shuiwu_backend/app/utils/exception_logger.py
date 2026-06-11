"""
异常日志记录工具
提供统一的异常日志记录功能，包含详细的上下文信息
"""
import traceback
import sys
from typing import Optional, Any, Dict
from pathlib import Path
from datetime import datetime

from app.infra.logging_config import get_exception_logger


class ExceptionContext:
    """异常上下文信息"""

    def __init__(
        self,
        exc_type: type,
        exc_value: BaseException,
        exc_traceback: Any,
        request: Optional[Any] = None,
        extra_info: Optional[Dict[str, Any]] = None
    ):
        self.exc_type = exc_type
        self.exc_value = exc_value
        self.exc_traceback = exc_traceback
        self.request = request
        self.extra_info = extra_info or {}
        self.timestamp = datetime.now()

    def get_exception_info(self) -> Dict[str, Any]:
        """获取异常详细信息"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "exception_type": self.exc_type.__name__,
            "exception_message": str(self.exc_value),
            "exception_module": self.exc_type.__module__,
        }

    def get_traceback_info(self) -> Dict[str, Any]:
        """获取堆栈跟踪信息"""
        tb_list = traceback.format_exception(
            self.exc_type,
            self.exc_value,
            self.exc_traceback
        )

        return {
            "traceback": "".join(tb_list),
            "traceback_lines": len(tb_list)
        }

    def get_request_info(self) -> Dict[str, Any]:
        """获取请求相关信息"""
        if self.request is None:
            return {}

        try:
            # 尝试从FastAPI Request对象中提取信息
            request_info = {
                "method": getattr(self.request, "method", None),
                "url": str(getattr(self.request, "url", None)),
                "headers": dict(getattr(self.request, "headers", {})),
            }

            # 尝试获取客户端信息
            if hasattr(self.request, "client"):
                client = getattr(self.request, "client", None)
                if client:
                    request_info["client"] = {
                        "host": getattr(client, "host", None),
                        "port": getattr(client, "port", None)
                    }

            # 尝试获取路径参数
            if hasattr(self.request, "path_params"):
                request_info["path_params"] = getattr(self.request, "path_params", {})

            return request_info
        except Exception:
            return {"error": "Failed to extract request info"}

    def to_dict(self) -> Dict[str, Any]:
        """转换为完整的字典格式"""
        return {
            **self.get_exception_info(),
            **self.get_traceback_info(),
            "request": self.get_request_info(),
            "extra": self.extra_info
        }


def log_exception(
    exc: Exception,
    request: Optional[Any] = None,
    extra_info: Optional[Dict[str, Any]] = None,
    logger: Optional[Any] = None,
    level: str = "ERROR"
) -> None:
    """
    记录异常日志

    Args:
        exc: 异常对象
        request: FastAPI请求对象 (可选)
        extra_info: 额外信息字典 (可选)
        logger: 自定义logger (可选，默认使用exception logger)
        level: 日志级别 (ERROR, CRITICAL)
    """
    # 获取异常上下文
    exc_type, exc_value, exc_tb = sys.exc_info()
    if exc is not None:
        exc_type = type(exc)
        exc_value = exc
        exc_tb = exc.__traceback__

    context = ExceptionContext(exc_type, exc_value, exc_tb, request, extra_info)

    # 使用自定义logger或默认exception logger
    if logger is None:
        logger = get_exception_logger()

    # 构建日志消息
    log_message = f"""
{'='*80}
异常发生时间: {context.timestamp.isoformat()}
异常类型: {context.exc_type.__name__}
异常信息: {str(context.exc_value)}
{'='*80}
堆栈跟踪:
{context.get_traceback_info()['traceback']}
{'='*80}"""

    # 添加请求信息
    request_info = context.get_request_info()
    if request_info:
        log_message += f"""
请求信息:
    方法: {request_info.get('method', 'N/A')}
    URL: {request_info.get('url', 'N/A')}
    客户端: {request_info.get('client', {}).get('host', 'N/A')}
"""

    # 添加额外信息
    if context.extra_info:
        log_message += f"""
额外信息:
{format_dict(context.extra_info, indent=4)}
"""
    log_message += f"{'='*80}\n"

    # 根据级别记录日志
    log_func = getattr(logger, level.lower(), logger.error)
    log_func(log_message)


def log_exception_simple(
    message: str,
    exc: Optional[Exception] = None,
    level: str = "ERROR"
) -> None:
    """
    简单的异常日志记录

    Args:
        message: 日志消息
        exc: 异常对象 (可选)
        level: 日志级别
    """
    logger = get_exception_logger()
    log_func = getattr(logger, level.lower(), logger.error)

    if exc:
        log_func(f"{message}\n异常: {type(exc).__name__}: {str(exc)}")
    else:
        log_func(message)


def format_dict(data: Dict[str, Any], indent: int = 0) -> str:
    """
    格式化字典为字符串

    Args:
        data: 字典数据
        indent: 缩进空格数

    Returns:
        格式化后的字符串
    """
    prefix = " " * indent
    lines = []

    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(format_dict(value, indent + 4))
        elif isinstance(value, (list, tuple)):
            lines.append(f"{prefix}{key}: {value}")
        else:
            lines.append(f"{prefix}{key}: {value}")

    return "\n".join(lines)


def log_and_raise_exception(
    message: str,
    exception_class: type,
    request: Optional[Any] = None,
    extra_info: Optional[Dict[str, Any]] = None,
    **kwargs
) -> None:
    """
    记录异常日志并抛出异常

    Args:
        message: 错误消息
        exception_class: 异常类
        request: 请求对象
        extra_info: 额外信息
        **kwargs: 传递给异常类的参数
    """
    # 创建异常实例
    exc = exception_class(message, **kwargs)

    # 记录日志
    log_exception(exc, request, extra_info)

    # 抛出异常
    raise exc


# 便捷装饰器
def catch_and_log(
    default_return: Any = None,
    logger: Optional[Any] = None,
    reraise: bool = False,
    extra_info: Optional[Dict[str, Any]] = None
):
    """
    捕获并记录异常的装饰器

    Args:
        default_return: 异常时的默认返回值
        logger: 自定义logger
        reraise: 是否重新抛出异常
        extra_info: 额外信息字典

    Usage:
        @catch_and_log(default_return=None, reraise=False)
        def my_function():
            # 可能抛出异常的代码
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log_exception(e, extra_info=extra_info, logger=logger)

                if reraise:
                    raise
                return default_return
        return wrapper
    return decorator
