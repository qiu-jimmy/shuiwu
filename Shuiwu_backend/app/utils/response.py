"""API响应工具类"""
from typing import Any, Generic, List, Optional, TypeVar

from app.schemas.common import ApiResponse, PageData, PageResponse

T = TypeVar('T')


class ResponseHelper:
    """API响应辅助类"""

    @staticmethod
    def success(data: Any = None, message: str = "操作成功") -> dict:
        """创建成功响应

        Args:
            data: 响应数据
            message: 响应消息

        Returns:
            标准响应字典
        """
        return {
            "code": 1,
            "message": message,
            "data": data
        }

    @staticmethod
    def fail(message: str = "操作失败", code: int = 0, data: Any = None) -> dict:
        """创建失败响应

        Args:
            message: 错误消息
            code: 错误码，默认0
            data: 附加数据

        Returns:
            标准响应字典
        """
        return {
            "code": code,
            "message": message,
            "data": data
        }

    @staticmethod
    def success_with_pagination(
        items: List[Any],
        total: int,
        page: int = 1,
        page_size: int = 20,
        message: str = "查询成功"
    ) -> dict:
        """创建分页成功响应

        Args:
            items: 数据列表
            total: 总记录数
            page: 当前页码
            page_size: 每页记录数
            message: 响应消息

        Returns:
            标准分页响应字典
        """
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

        return {
            "code": 1,
            "message": message,
            "data": {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages
            }
        }

    @staticmethod
    def error_handler(detail: str = "请求处理失败", code: int = 0) -> dict:
        """处理异常并返回错误响应

        Args:
            detail: 错误详情
            code: 错误码

        Returns:
            错误响应字典
        """
        return {
            "code": code,
            "message": detail,
            "data": None
        }

    @staticmethod
    def not_found(resource: str = "资源") -> dict:
        """资源不存在响应

        Args:
            resource: 资源名称

        Returns:
            404响应字典
        """
        return {
            "code": 0,
            "message": f"{resource}不存在",
            "data": None
        }

    @staticmethod
    def unauthorized(message: str = "未授权访问") -> dict:
        """未授权响应

        Args:
            message: 错误消息

        Returns:
            401响应字典
        """
        return {
            "code": 0,
            "message": message,
            "data": None
        }

    @staticmethod
    def forbidden(message: str = "无权访问") -> dict:
        """禁止访问响应

        Args:
            message: 错误消息

        Returns:
            403响应字典
        """
        return {
            "code": 0,
            "message": message,
            "data": None
        }

    @staticmethod
    def validation_error(errors: List[str]) -> dict:
        """参数验证失败响应

        Args:
            errors: 错误列表

        Returns:
            验证错误响应字典
        """
        return {
            "code": 0,
            "message": "参数验证失败",
            "data": {
                "errors": errors
            }
        }


# 全局实例
response = ResponseHelper()
