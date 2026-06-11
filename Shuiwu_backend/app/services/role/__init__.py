"""用户角色服务模块"""
from app.services.role.role_service import role_service
from app.services.role.role_repository import role_repository

__all__ = [
    "role_service",
    "role_repository",
]
