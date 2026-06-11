"""通用API响应模型"""
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field


T = TypeVar('T')


class ApiResponse(BaseModel, Generic[T]):
    """通用API响应模型

    标准响应格式:
    {
        "code": 1,           # 状态码：1-成功，0-失败
        "message": "成功",    # 响应消息
        "data": {...}         # 响应数据
    }
    """

    code: int = Field(1, description="状态码：1-成功，0-失败")
    message: str = Field("success", description="响应消息")
    data: Optional[T] = Field(None, description="响应数据")

    @classmethod
    def success(cls, data: Any = None, message: str = "操作成功") -> "ApiResponse[T]":
        """创建成功响应"""
        return cls(code=1, message=message, data=data)

    @classmethod
    def fail(cls, message: str = "操作失败", code: int = 0, data: Any = None) -> "ApiResponse[T]":
        """创建失败响应"""
        return cls(code=code, message=message, data=data)


class PageData(BaseModel, Generic[T]):
    """分页数据模型"""

    items: List[T] = Field(default_factory=list, description="数据列表")
    total: int = Field(0, description="总记录数")
    page: int = Field(1, description="当前页码")
    page_size: int = Field(20, description="每页记录数")
    total_pages: int = Field(0, description="总页数")

    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int = 1,
        page_size: int = 20
    ) -> "PageData[T]":
        """创建分页数据"""
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )


class PageResponse(BaseModel, Generic[T]):
    """分页响应模型"""

    code: int = Field(1, description="状态码：1-成功，0-失败")
    message: str = Field("success", description="响应消息")
    data: PageData[T] = Field(..., description="分页数据")

    @classmethod
    def success(
        cls,
        items: List[T],
        total: int,
        page: int = 1,
        page_size: int = 20,
        message: str = "查询成功"
    ) -> "PageResponse[T]":
        """创建成功分页响应"""
        return cls(
            code=1,
            message=message,
            data=PageData.create(items, total, page, page_size)
        )

    @classmethod
    def fail(cls, message: str = "查询失败", code: int = 0) -> "PageResponse[T]":
        """创建失败分页响应"""
        return cls(code=code, message=message, data=PageData())


# ============================================================================
# 常用响应别名
# ============================================================================

# 无数据的成功响应
SuccessResponse = ApiResponse[None]

# 字符串数据响应
StringResponse = ApiResponse[str]

# 列表数据响应
ListResponse = ApiResponse[List[Any]]

# 字典数据响应
DictResponse = ApiResponse[dict]
