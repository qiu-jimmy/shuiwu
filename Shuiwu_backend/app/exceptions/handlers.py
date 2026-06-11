"""
全局异常处理器
统一处理所有异常并返回标准格式的响应
"""
import traceback
import sys
from typing import Union
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.utils.response import response
from app.exceptions.exceptions import BaseAPIException
from app.utils.exception_logger import log_exception, log_exception_simple


def print_exception_to_console(exc: Exception, title: str = "异常发生"):
    """将异常信息打印到控制台（使用stderr确保在uvicorn下可见）"""
    # 使用stderr确保输出始终可见，即使在uvicorn环境下
    output = [
        "\n" + "=" * 80,
        f"[{title}]",
        "=" * 80,
        f"异常类型: {type(exc).__name__}",
        f"异常信息: {str(exc)}",
        "=" * 80,
        "堆栈跟踪:"
    ]

    # 输出基本信息
    for line in output:
        print(line, file=sys.stderr, flush=True)

    # 输出堆栈跟踪
    traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stderr)

    # 输出结束标记
    print("=" * 80 + "\n", file=sys.stderr, flush=True)


async def api_exception_handler(request: Request, exc: BaseAPIException) -> JSONResponse:
    """处理自定义API异常"""
    # 打印异常到控制台（使用stderr）
    print_exception_to_console(exc, f"API异常 - {exc.code}")

    # 记录到日志文件
    log_exception(
        exc,
        request=request,
        extra_info={
            "exception_code": exc.code,
            "status_code": exc.status_code,
            "detail": exc.detail,
            "request_url": str(request.url),
            "request_method": request.method
        },
        level="ERROR"
    )

    # 额外输出到 stderr 确保在控制台可见
    import sys
    print(f"\n API异常 [{exc.code}]: {exc.message}", file=sys.stderr, flush=True)
    if exc.detail:
        print(f"详细信息: {exc.detail}", file=sys.stderr, flush=True)
    print(f"请求路径: {request.method} {request.url}", file=sys.stderr, flush=True)
    print("", file=sys.stderr, flush=True)

    return JSONResponse(
        status_code=exc.status_code,
        content=response.fail(
            message=exc.message,
            code=0,
            data=exc.detail
        )
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """处理FastAPI/Starlette的HTTPException"""
    # 打印异常到控制台（使用stderr）
    print(f"\n HTTP异常 | 状态码: {exc.status_code} | 信息: {str(exc.detail)}", file=sys.stderr, flush=True)
    print(f"请求路径: {request.method} {request.url}\n", file=sys.stderr, flush=True)

    # 记录HTTP异常日志
    log_exception_simple(
        f"HTTP异常: {exc.status_code} - {str(exc.detail)} | 路径: {request.url}",
        level="WARNING"
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=response.fail(
            message=str(exc.detail),
            code=0
        )
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """处理请求参数验证异常"""
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        errors.append(f"{field}: {error['msg']}")

    # 打印验证异常到控制台（使用stderr）
    print(f"\n 参数验证失败", file=sys.stderr, flush=True)
    for error in errors:
        print(f"   {error}", file=sys.stderr, flush=True)
    print(f"请求路径: {request.method} {request.url}\n", file=sys.stderr, flush=True)

    # 记录验证异常日志
    log_exception(
        exc,
        request=request,
        extra_info={
            "validation_errors": exc.errors(),
            "formatted_errors": errors,
            "request_url": str(request.url)
        },
        level="WARNING"
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=response.fail(
            message="参数验证失败",
            code=0,
            data={"errors": errors}
        )
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理所有未捕获的异常"""
    # 打印异常到控制台
    exception_title = "未捕获异常"
    if isinstance(exc, SQLAlchemyError):
        exception_title = " 数据库异常"
    elif isinstance(exc, StarletteHTTPException):
        exception_title = "HTTP异常"
    else:
        exception_title = " 服务器内部错误"

    print_exception_to_console(exc, exception_title)

    # 额外输出请求信息
    print(f" 请求路径: {request.method} {request.url}", file=sys.stderr, flush=True)
    print(f" 客户端: {request.client.host if request.client else 'unknown'}\n", file=sys.stderr, flush=True)

    # 记录详细异常日志
    extra_info = {}

    # 根据异常类型判断返回的状态码
    if isinstance(exc, SQLAlchemyError):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        message = "数据库操作失败"
        extra_info["exception_category"] = "database_error"
    elif isinstance(exc, StarletteHTTPException):
        status_code = exc.status_code
        message = str(exc.detail)
        extra_info["exception_category"] = "http_error"
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        message = "服务器内部错误"
        extra_info["exception_category"] = "unknown_error"

    # 添加请求信息到日志
    extra_info.update({
        "request_url": str(request.url),
        "request_method": request.method,
        "client_host": request.client.host if request.client else "unknown"
    })

    # 使用日志系统记录异常
    log_exception(
        exc,
        request=request,
        extra_info=extra_info,
        level="ERROR"
    )

    return JSONResponse(
        status_code=status_code,
        content=response.fail(
            message=message,
            code=0
        )
    )


def setup_exception_handlers(app: FastAPI):
    """注册所有异常处理器到FastAPI应用"""
    # 自定义API异常（优先级最高，必须在通用异常之前）
    app.add_exception_handler(BaseAPIException, api_exception_handler)

    # FastAPI/Starlette的HTTPException
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)

    # 请求参数验证异常
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # 所有未捕获的异常
    app.add_exception_handler(Exception, general_exception_handler)
