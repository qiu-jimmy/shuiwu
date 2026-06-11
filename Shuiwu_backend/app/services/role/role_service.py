"""
用户角色服务层
处理用户角色相关的业务逻辑
"""
from typing import Dict, Any, Optional, List
from app.services.role.role_repository import role_repository
from app.services.user.user_repository import user_repository


class RoleService:
    """用户角色服务类"""

    def __init__(self):
        self.repository = role_repository

    def get_user_roles(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的所有角色"""
        return self.repository.get_user_roles(user_id)

    def get_user_all_permissions(self, user_id: str) -> List[str]:
        """获取用户的所有权限（合并所有角色的权限）"""
        roles = self.repository.get_user_roles(user_id)

        # 合并所有权限并去重
        all_permissions = set()
        for role in roles:
            permissions = role.get("permissions", [])
            if permissions:
                if isinstance(permissions, list):
                    all_permissions.update(permissions)
                elif isinstance(permissions, str):
                    # 处理可能是字符串的情况
                    pass

        return list(all_permissions)

    def check_user_has_permission(self, user_id: str, required_permission: str) -> bool:
        """检查用户是否拥有指定权限"""
        return self.repository.check_user_permission(user_id, required_permission)

    def check_user_has_role(self, user_id: str, required_role: str) -> bool:
        """检查用户是否拥有指定角色"""
        user_role = self.repository.get_user_role_by_role(user_id, required_role)
        return user_role is not None and user_role.get("status") == "active"

    def check_user_is_admin(self, user_id: str) -> bool:
        """检查用户是否是管理员（拥有admin或super_admin角色）"""
        return (
            self.check_user_has_role(user_id, "admin") or
            self.check_user_has_role(user_id, "super_admin")
        )

    def assign_role_to_user(
        self,
        user_id: str,
        role: str,
        created_by: Optional[str] = None,
        custom_permissions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """给用户分配角色

        Args:
            user_id: 用户ID
            role: 角色代码
            created_by: 操作人用户ID
            custom_permissions: 自定义权限列表（可选，如果不提供则使用角色默认权限）

        Returns:
            操作结果
        """
        # 验证用户是否存在
        user = user_repository.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"用户不存在: {user_id}")

        # 获取角色定义
        role_def = self.repository.get_role_definition(role)
        if not role_def:
            raise ValueError(f"角色不存在: {role}")

        # 使用自定义权限或默认权限
        permissions = custom_permissions if custom_permissions is not None else role_def.get("default_permissions", [])

        # 分配角色
        success = self.repository.assign_role_to_user(
            user_id=user_id,
            role=role,
            permissions=permissions,
            created_by=created_by
        )

        if not success:
            raise Exception("分配角色失败")

        return {
            "user_id": user_id,
            "role": role,
            "permissions": permissions
        }

    def remove_role_from_user(
        self,
        user_id: str,
        role: str
    ) -> bool:
        """移除用户的角色"""
        return self.repository.remove_role_from_user(user_id, role)

    def update_user_permissions(
        self,
        user_id: str,
        role: str,
        permissions: List[str]
    ) -> bool:
        """更新用户的权限"""
        return self.repository.update_user_permissions(user_id, role, permissions)

    def get_role_definitions(self) -> List[Dict[str, Any]]:
        """获取所有角色定义"""
        return self.repository.get_role_definitions()

    def get_role_definition(self, role: str) -> Optional[Dict[str, Any]]:
        """获取指定角色的定义"""
        return self.repository.get_role_definition(role)

    # ==================== 操作日志 ====================

    def create_action_log(
        self,
        user_id: str,
        action_type: str,
        action_module: str,
        action_detail: Optional[Dict[str, Any]] = None,
        target_user_id: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_method: Optional[str] = None,
        request_path: Optional[str] = None,
        response_status: Optional[int] = None,
        response_message: Optional[str] = None
    ) -> str:
        """创建用户角色操作日志"""
        # 获取用户名
        user = user_repository.get_user_by_id(user_id)
        username = user.get("username") if user else user_id

        return self.repository.create_action_log(
            user_id=user_id,
            username=username,
            action_type=action_type,
            action_module=action_module,
            action_detail=action_detail,
            target_user_id=target_user_id,
            target_type=target_type,
            target_id=target_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_method=request_method,
            request_path=request_path,
            response_status=response_status,
            response_message=response_message
        )

    def get_action_logs(
        self,
        user_id: Optional[str] = None,
        action_module: Optional[str] = None,
        action_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """获取用户角色操作日志"""
        return self.repository.get_action_logs(
            user_id=user_id,
            action_module=action_module,
            action_type=action_type,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size
        )


# 全局角色服务实例
role_service = RoleService()
