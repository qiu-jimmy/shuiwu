"""
模型配置缓存管理
在内存中缓存所有模型配置,避免频繁查询数据库
"""
from typing import Any, Dict, Optional
from app.services.models.models_repository import models_repository


class ModelCache:
    """模型配置缓存管理器"""

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}

    def load_all_models(self) -> None:
        """
        从数据库加载所有模型配置到缓存
        在应用启动时调用
        """
        try:
            models = models_repository.list_all_models()
            self._cache = {}

            for model in models:
                model_id = model.get("id")
                if model_id:
                    self._cache[model_id] = model

            print(f"[ModelCache] 成功加载 {len(self._cache)} 个模型配置到缓存")
        except Exception as e:
            print(f"[ModelCache] 加载模型配置失败: {str(e)}")
            self._cache = {}

    def get_model_config(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        从缓存获取模型配置

        Args:
            model_id: 模型ID

        Returns:
            模型配置字典,如果不存在返回 None
        """
        return self._cache.get(model_id)

    def add_model(self, model: Dict[str, Any]) -> None:
        """
        添加模型配置到缓存

        Args:
            model: 模型配置字典
        """
        model_id = model.get("id")
        if model_id:
            self._cache[model_id] = model
            print(f"[ModelCache] 添加模型 {model_id} 到缓存")

    def update_model(self, model_id: str, model_data: Dict[str, Any]) -> None:
        """
        更新缓存中的模型配置

        Args:
            model_id: 模型ID
            model_data: 更新的模型数据
        """
        if model_id in self._cache:
            # 合并更新
            self._cache[model_id].update(model_data)
            print(f"[ModelCache] 更新模型 {model_id} 缓存")

    def delete_model(self, model_id: str) -> None:
        """
        从缓存删除模型配置

        Args:
            model_id: 模型ID
        """
        if model_id in self._cache:
            del self._cache[model_id]
            print(f"[ModelCache] 从缓存删除模型 {model_id}")

    def clear_cache(self) -> None:
        """清空所有缓存"""
        self._cache.clear()
        print("[ModelCache] 清空所有缓存")

    def get_all_models(self) -> Dict[str, Dict[str, Any]]:
        """获取所有缓存的模型配置"""
        return self._cache.copy()

    def is_model_loaded(self, model_id: str) -> bool:
        """检查模型是否在缓存中"""
        return model_id in self._cache


# 全局缓存实例
model_cache = ModelCache()
