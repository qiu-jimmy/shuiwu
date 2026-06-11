"""
Models 服务
处理模型管理的业务逻辑（使用repository进行数据库操作）
"""
from typing import Any, Dict, Optional

from app.services.models.models_repository import models_repository
from app.schemas.models import ModelCreateRequest, ModelUpdateRequest
from app.utils.model_validator import model_validator
from app.services.models.model_cache import model_cache


class ModelsService:
    """模型管理服务类"""
    
    def list_models(self) -> Dict[str, Any]:
        """获取模型列表"""
        models = models_repository.list_all_models()
        return {
            "status": "success",
            "total": len(models),
            "models": models
        }
    
    def get_model(self, model_id: str) -> Dict[str, Any]:
        """获取单个模型详情"""
        model = models_repository.get_model_by_id(model_id)
        if not model:
            raise Exception("模型不存在")
        return {
            "status": "success",
            "model": model
        }
    
    def create_model(self, request: ModelCreateRequest) -> Dict[str, Any]:
        """创建模型"""
        if models_repository.model_exists(request.id):
            raise Exception("模型ID已存在")

        model_data = {
            "id": request.id,
            "name": request.name,
            "provider": request.provider,
            "model_url": request.model_url,
            "model_api_key": request.model_api_key,
            "description": request.description,
            "status": request.status,
            "context_window": request.context_window
        }

        models_repository.create_model(model_data)

        # 同步更新缓存
        model_cache.add_model(model_data)

        return {
            "status": "success",
            "message": "模型创建成功",
            "model_id": request.id
        }
    
    def update_model(self, model_id: str, request: ModelUpdateRequest) -> Dict[str, Any]:
        """更新模型"""
        if not models_repository.model_exists(model_id):
            raise Exception("模型不存在")

        update_data = {}
        for field in ["name", "provider", "model_url", "model_api_key", "description", "status", "context_window"]:
            value = getattr(request, field, None)
            if value is not None:
                update_data[field] = value

        if not update_data:
            raise Exception("没有要更新的字段")

        models_repository.update_model(model_id, update_data)

        # 同步更新缓存
        model_cache.update_model(model_id, update_data)

        return {
            "status": "success",
            "message": "模型更新成功",
            "model_id": model_id
        }
    
    def delete_model(self, model_id: str) -> Dict[str, Any]:
        """删除模型"""
        if not models_repository.model_exists(model_id):
            raise Exception("模型不存在")

        models_repository.delete_model(model_id)

        # 同步更新缓存
        model_cache.delete_model(model_id)

        return {
            "status": "success",
            "message": "模型删除成功",
            "model_id": model_id
        }
    
    def get_model_from_db(self, model_id: str) -> Optional[Dict[str, Any]]:
        """从数据库获取模型配置（用于Agent创建）"""
        return models_repository.get_model_by_id(model_id)

    def validate_model_config(self, model_id: str) -> Dict[str, Any]:
        """验证模型配置是否可用"""
        model = models_repository.get_model_by_id(model_id)
        if not model:
            return {
                "status": "error",
                "valid": False,
                "message": "模型不存在",
                "model_id": model_id
            }

        return model_validator.validate_model_config(model)


# 全局服务实例
models_service = ModelsService()

