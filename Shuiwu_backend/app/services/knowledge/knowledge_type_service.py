"""知识库类型业务逻辑层"""
from typing import Any, Dict, List, Optional

from app.services.knowledge.knowledge_type_repository import knowledge_type_repository


class KnowledgeTypeService:
    """知识库类型业务逻辑类"""

    def __init__(self):
        self.repository = knowledge_type_repository

    def create_type(self, type_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建知识库类型"""
        # 检查类型代码是否已存在
        existing = self.repository.get_knowledge_type_by_code(type_data["type_code"])
        if existing:
            return {
                "success": False,
                "error": f"类型代码 '{type_data['type_code']}' 已存在"
            }

        # 创建类型
        result = self.repository.create_knowledge_type(type_data)
        if result:
            return {
                "success": True,
                "data": result
            }
        else:
            return {
                "success": False,
                "error": "创建知识库类型失败"
            }

    def get_type(self, type_id: str) -> Dict[str, Any]:
        """获取知识库类型详情"""
        result = self.repository.get_knowledge_type_by_id(type_id)
        if result:
            return {
                "success": True,
                "data": result
            }
        else:
            return {
                "success": False,
                "error": "知识库类型不存在"
            }

    def list_types(
        self,
        status: Optional[str] = None,
        is_system: Optional[bool] = None
    ) -> Dict[str, Any]:
        """获取知识库类型列表"""
        results = self.repository.list_knowledge_types(status=status, is_system=is_system)
        return {
            "success": True,
            "data": {
                "total": len(results),
                "items": results
            }
        }

    def update_type(self, type_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新知识库类型"""
        # 检查类型是否存在
        existing = self.repository.get_knowledge_type_by_id(type_id)
        if not existing:
            return {
                "success": False,
                "error": "知识库类型不存在"
            }

        # 如果更新 type_code，检查是否重复
        if "type_code" in update_data and update_data["type_code"] != existing["type_code"]:
            code_exists = self.repository.get_knowledge_type_by_code(update_data["type_code"])
            if code_exists:
                return {
                    "success": False,
                    "error": f"类型代码 '{update_data['type_code']}' 已存在"
                }

        # 更新
        success = self.repository.update_knowledge_type(type_id, update_data)
        if success:
            # 返回更新后的数据
            updated = self.repository.get_knowledge_type_by_id(type_id)
            return {
                "success": True,
                "data": updated
            }
        else:
            return {
                "success": False,
                "error": "更新知识库类型失败"
            }

    def delete_type(self, type_id: str, is_admin: bool = False) -> Dict[str, Any]:
        """删除知识库类型"""
        # 检查类型是否存在
        existing = self.repository.get_knowledge_type_by_id(type_id)
        if not existing:
            return {
                "success": False,
                "error": "知识库类型不存在"
            }

        # 检查是否是系统类型（管理员可删除系统类型）
        if existing.get("is_system") and not is_admin:
            return {
                "success": False,
                "error": "系统内置类型不允许删除"
            }

        # 删除（管理员可删除系统类型）
        success = self.repository.delete_knowledge_type(type_id, allow_system=is_admin)
        if success:
            return {
                "success": True,
                "message": "删除成功"
            }
        else:
            return {
                "success": False,
                "error": "删除知识库类型失败"
            }

    def search_content(
        self,
        keyword: str,
        user_id: Optional[str] = None,
        type_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """搜索知识库内容"""
        if not keyword or len(keyword.strip()) == 0:
            return {
                "success": False,
                "error": "搜索关键词不能为空"
            }

        results = self.repository.search_knowledge_content(
            keyword=keyword.strip(),
            user_id=user_id,
            type_id=type_id,
            limit=limit,
            offset=offset
        )

        return {
            "success": True,
            "data": {
                "keyword": keyword,
                "total": len(results),
                "items": results
            }
        }

    def search_knowledge_bases(
        self,
        keyword: str,
        user_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """搜索知识库（按名称）"""
        if not keyword or len(keyword.strip()) == 0:
            return {
                "success": False,
                "error": "搜索关键词不能为空"
            }

        result = self.repository.search_knowledge_bases(
            keyword=keyword.strip(),
            user_id=user_id,
            limit=limit,
            offset=offset
        )

        return {
            "success": True,
            "data": result
        }


# 全局实例
knowledge_type_service = KnowledgeTypeService()
