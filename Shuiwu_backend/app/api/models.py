"""模型管理路由"""
from fastapi import APIRouter

from app.schemas.models import ModelCreateRequest, ModelUpdateRequest, ModelValidateRequest
from app.services.models.models_service import models_service
from app.utils.response import response

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("/")
async def list_models():
    """获取模型列表"""
    try:
        result = models_service.list_models()
        return response.success(data=result, message="获取模型列表成功")
    except Exception as e:
        return response.fail(message=str(e))


@router.get("/{model_id}")
async def get_model(model_id: str):
    """获取单个模型详情"""
    try:
        result = models_service.get_model(model_id)
        return response.success(data=result, message="获取模型详情成功")
    except Exception as e:
        return response.fail(message=str(e))


@router.post("/")
async def create_model(request: ModelCreateRequest):
    """创建模型"""
    try:
        result = models_service.create_model(request)
        return response.success(data=result, message="创建模型成功")
    except Exception as e:
        return response.fail(message=str(e))


@router.put("/{model_id}")
async def update_model(model_id: str, request: ModelUpdateRequest):
    """更新模型"""
    try:
        result = models_service.update_model(model_id, request)
        return response.success(data=result, message="更新模型成功")
    except Exception as e:
        return response.fail(message=str(e))


@router.delete("/{model_id}")
async def delete_model(model_id: str):
    """删除模型"""
    try:
        result = models_service.delete_model(model_id)
        return response.success(data=result, message="删除模型成功")
    except Exception as e:
        return response.fail(message=str(e))


@router.post("/validate")
async def validate_model(request: ModelValidateRequest):
    """
    验证模型配置是否可用

    通过发送测试请求来验证模型的 API Key、base URL 等配置是否正确

    请求体：
    - model_id: 模型ID
    """
    try:
        result = models_service.validate_model_config(request.model_id)
        if result.get("valid"):
            return response.success(data=result, message=result.get("message", "模型配置验证成功"))
        else:
            return response.fail(message=result.get("message", "模型配置验证失败"))
    except Exception as e:
        return response.fail(message=f"验证模型配置时出错: {str(e)}")
