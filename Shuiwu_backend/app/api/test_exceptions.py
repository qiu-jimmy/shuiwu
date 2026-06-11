"""
测试API端点 - 用于触发各种异常
这个文件可以添加到app/api/目录下，然后在main.py中注册
"""
from fastapi import APIRouter, HTTPException
from app.exceptions.exceptions import (
    NotFoundException,
    ValidationException,
    DatabaseException,
    AIServiceException
)
from app.infra.logging_config import get_logger

router = APIRouter(prefix="/api/test", tags=["测试"])
logger = get_logger(__name__)


@router.get("/error/not-found")
async def test_not_found():
    """测试404异常"""
    raise NotFoundException("测试资源不存在")


@router.get("/error/validation")
async def test_validation():
    """测试参数验证异常"""
    raise ValidationException("测试参数验证失败")


@router.get("/error/database")
async def test_database():
    """测试数据库异常"""
    raise DatabaseException("测试数据库连接失败")


@router.get("/error/ai-service")
async def test_ai_service():
    """测试AI服务异常"""
    raise AIServiceException("测试AI服务调用超时")


@router.get("/error/http")
async def test_http():
    """测试HTTP异常"""
    raise HTTPException(status_code=500, detail="测试HTTP 500错误")


@router.get("/error/unexpected")
async def test_unexpected():
    """测试未捕获的异常"""
    # 故意触发一个未捕获的异常
    result = 1 / 0
    return {"result": result}


@router.get("/error/key-error")
async def test_key_error():
    """测试KeyError"""
    data = {"key": "value"}
    _ = data["nonexistent_key"]  # 这会触发KeyError
    return {"data": data}


@router.get("/logs")
async def test_logs():
    """测试不同级别的日志"""
    logger.debug("这是DEBUG级别日志")
    logger.info("这是INFO级别日志")
    logger.warning("这是WARNING级别日志")
    logger.error("这是ERROR级别日志")
    logger.critical("这是CRITICAL级别日志")

    return {
        "message": "日志已输出到控制台和文件",
        "check": "查看服务器控制台和logs/app.log"
    }


@router.get("/")
async def test_index():
    """测试端点首页"""
    return {
        "message": "测试API端点",
        "endpoints": {
            "/api/test/error/not-found": "测试404异常",
            "/api/test/error/validation": "测试参数验证异常",
            "/api/test/error/database": "测试数据库异常",
            "/api/test/error/ai-service": "测试AI服务异常",
            "/api/test/error/http": "测试HTTP异常",
            "/api/test/error/unexpected": "测试未捕获异常（除零错误）",
            "/api/test/error/key-error": "测试KeyError",
            "/api/test/logs": "测试不同级别的日志输出"
        }
    }
