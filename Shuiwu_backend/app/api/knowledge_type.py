"""知识库类型API路由"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Depends

from app.schemas.common import ApiResponse, PageResponse
from app.schemas.knowledge_type import (
    CreateKnowledgeTypeRequest,
    CreateKnowledgeBaseWithTypeRequest,
    KnowledgeBaseSearchItem,
    KnowledgeTypeListResponse,
    KnowledgeTypeResponse,
    SearchContentRequest,
    SearchContentResponse,
    SearchKnowledgeBasesRequest,
    SearchKnowledgeBasesResponse,
    UpdateKnowledgeTypeRequest,
)
from app.services.knowledge.knowledge_type_service import knowledge_type_service
from app.utils.response import response
from app.utils.dependencies import get_current_user_with_roles

router = APIRouter(prefix="/api/knowledge-types", tags=["知识库类型"])


# ============================================================================
# 知识库类型管理接口
# ============================================================================


@router.get(
    "/list",
    summary="获取知识库类型列表",
    description="""
获取所有可用的知识库类型，支持按状态和系统类型筛选。

**查询参数：**
- `status`: 状态筛选（active-有效, inactive-无效）
- `is_system`: 是否系统类型（true-是, false-否, 不传-全部）

**预置类型包括：**
- 税收基础知识
- 政策文件
- 发票相关知识
- 税务筹划
- 税务会计
- 税务风险
- 税务优惠
- 税务稽查
- 国际税收
- 个人所得税
- 企业所得税
- 增值税
- 其他税种
- 税务实务
- 税务问答
    """,
    responses={
        200: {
            "description": "成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "获取成功",
                        "data": [
                            {
                                "type_id": "type_012",
                                "type_name": "增值税",
                                "type_code": "vat_tax",
                                "description": "增值税相关政策、计算、申报等",
                                "icon": "percent",
                                "sort_order": 12,
                                "is_system": True,
                                "status": "active",
                                "created_at": "2026-01-13T10:00:00"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def list_knowledge_types(
    status: Optional[str] = Query(None, description="状态筛选：active-有效, inactive-无效"),
    is_system: Optional[str] = Query(None, description="是否系统类型：true-是, false-否, 不传-全部")
):
    """获取知识库类型列表"""
    # 手动解析 is_system 参数
    parsed_is_system: Optional[bool] = None
    if is_system is not None:
        if is_system.lower() in ("true", "1", "yes"):
            parsed_is_system = True
        elif is_system.lower() in ("false", "0", "no"):
            parsed_is_system = False

    result = knowledge_type_service.list_types(status=status, is_system=parsed_is_system)
    if not result["success"]:
        return response.fail(message=result.get("error", "获取类型列表失败"))
    return response.success(data=result["data"]["items"], message="获取成功")


@router.get(
    "/{type_id}",
    summary="获取知识库类型详情",
    description="""
根据类型ID获取知识库类型的详细信息。

**路径参数：**
- `type_id`: 知识库类型ID

**返回字段包括：**
- 基本信息（类型名称、编码、描述）
- 显示配置（图标、排序）
- 系统标识（是否系统内置）
- 状态信息
    """,
    responses={
        200: {
            "description": "成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "获取成功",
                        "data": {
                            "type_id": "type_012",
                            "type_name": "增值税",
                            "type_code": "vat_tax",
                            "description": "增值税相关政策、计算、申报等",
                            "icon": "percent",
                            "sort_order": 12,
                            "is_system": True,
                            "status": "active"
                        }
                    }
                }
            }
        },
        404: {
            "description": "类型不存在",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "类型不存在"
                    }
                }
            }
        }
    }
)
async def get_knowledge_type(type_id: str):
    """获取知识库类型详情"""
    result = knowledge_type_service.get_type(type_id)
    if not result["success"]:
        return response.fail(message=result.get("error", "类型不存在"))
    return response.success(data=result["data"])


@router.post(
    "",
    summary="创建知识库类型",
    description="""
创建新的知识库类型（需要管理员权限）。

**请求参数：**
- `type_name`: 类型名称
- `type_code`: 类型编码（唯一标识）
- `description`: 类型描述
- `icon`: 图标名称
- `sort_order`: 排序顺序

**注意事项：**
- type_code 必须唯一
- 仅管理员可创建系统类型
    """,
    responses={
        200: {
            "description": "创建成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "创建成功",
                        "data": {
                            "type_id": "type_100",
                            "type_name": "自定义类型",
                            "type_code": "custom_type",
                            "is_system": False
                        }
                    }
                }
            }
        },
        400: {
            "description": "创建失败",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "类型编码已存在"
                    }
                }
            }
        }
    }
)
async def create_knowledge_type(request: CreateKnowledgeTypeRequest):
    """创建知识库类型"""
    result = knowledge_type_service.create_type(request.dict())
    if not result["success"]:
        return response.fail(message=result.get("error", "创建失败"))
    return response.success(data=result["data"], message="创建成功")


@router.put(
    "/{type_id}",
    summary="更新知识库类型",
    description="""
更新知识库类型信息（需要管理员权限）。

**路径参数：**
- `type_id`: 知识库类型ID

**可更新字段：**
- `type_name`: 类型名称
- `description`: 类型描述
- `icon`: 图标
- `sort_order`: 排序
- `status`: 状态

**注意事项：**
- 系统内置类型的某些字段可能不允许修改
- type_code 创建后不可修改
    """,
    responses={
        200: {
            "description": "更新成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "更新成功",
                        "data": {
                            "type_id": "type_012",
                            "type_name": "增值税（更新）"
                        }
                    }
                }
            }
        },
        404: {
            "description": "类型不存在",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "类型不存在"
                    }
                }
            }
        }
    }
)
async def update_knowledge_type(type_id: str, request: UpdateKnowledgeTypeRequest):
    """更新知识库类型"""
    # 只获取提供的字段
    update_data = request.dict(exclude_unset=True)
    result = knowledge_type_service.update_type(type_id, update_data)
    if not result["success"]:
        return response.fail(message=result.get("error", "更新失败"))
    return response.success(data=result["data"], message="更新成功")


@router.delete(
    "/{type_id}",
    summary="删除知识库类型",
    description="""
删除知识库类型。

**路径参数：**
- `type_id`: 知识库类型ID

**权限说明：**
- 普通用户：只能删除非系统内置类型
- 管理员：可以删除任何类型，包括系统内置类型

**注意事项：**
- 如果类型下有关联的知识库，需要先处理
- 删除操作不可逆
    """,
    responses={
        200: {
            "description": "删除成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "删除成功",
                        "data": None
                    }
                }
            }
        },
        400: {
            "description": "删除失败",
            "content": {
                "application/json": {
                    "examples": {
                        "system_type": {
                            "summary": "系统内置类型（非管理员）",
                            "value": {
                                "code": 0,
                                "message": "系统内置类型不允许删除"
                            }
                        },
                        "not_found": {
                            "summary": "类型不存在",
                            "value": {
                                "code": 0,
                                "message": "知识库类型不存在"
                            }
                        }
                    }
                }
            }
        }
    }
)
async def delete_knowledge_type(
    type_id: str,
    current_user: dict = Depends(get_current_user_with_roles)
):
    """删除知识库类型（管理员可删除系统类型）"""
    result = knowledge_type_service.delete_type(
        type_id,
        is_admin=current_user.get("is_admin", False)
    )
    if not result["success"]:
        return response.fail(message=result.get("error", "删除失败"))
    return response.success(message=result.get("message", "删除成功"))


# ============================================================================
# 知识库搜索接口
# ============================================================================


@router.post(
    "/search/content",
    summary="搜索知识库内容",
    description="""
全局搜索知识库中的文档内容。

**核心功能：**
- 输入关键词进行搜索
- 支持用户筛选（只搜索指定用户的知识库）
- 支持类型筛选（按知识库类型筛选）
- 返回搜索结果列表，按相关度排序
- 展示内容预览（200字符）
- 支持点击跳转至详情

**搜索范围：**
- 文档内容（使用 PostgreSQL 全文搜索）
- 文档名称
- 文件名

**请求参数：**
- `keyword`: 搜索关键词（必需）
- `user_id`: 用户ID（可选）
- `type_id`: 知识库类型ID（可选）
- `limit`: 返回数量（默认 20，最大 100）
- `offset`: 偏移量（默认 0，用于分页）
    """,
    responses={
        200: {
            "description": "搜索成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "搜索成功",
                        "data": {
                            "keyword": "增值税",
                            "total": 15,
                            "items": [
                                {
                                    "kb_name": "vat_kb_001",
                                    "filename": "增值税政策.txt",
                                    "content_preview": "增值税税率分为三档：17%、13%和零税率。纳税人销售货物...",
                                    "rank": 0.95
                                },
                                {
                                    "kb_name": "vat_kb_002",
                                    "filename": "税收优惠政策.docx",
                                    "content_preview": "农业生产者销售的自产农业产品免征增值税...",
                                    "rank": 0.87
                                }
                            ]
                        }
                    }
                }
            }
        },
        400: {
            "description": "请求错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "关键词不能为空"
                    }
                }
            }
        }
    }
)
async def search_knowledge_content(request: SearchContentRequest):
    """搜索知识库内容"""
    result = knowledge_type_service.search_content(
        keyword=request.keyword,
        user_id=request.user_id,
        type_id=request.type_id,
        limit=request.limit,
        offset=request.offset
    )
    if not result["success"]:
        return response.fail(message=result.get("error", "搜索失败"))
    return response.success(data=result["data"], message="搜索成功")


@router.get(
    "/search/content",
    summary="搜索知识库内容（GET方式）",
    description="""
通过GET请求搜索知识库内容，方便快速测试。

**查询参数：**
- `keyword`: 搜索关键词（必需）
- `user_id`: 用户ID（可选）
- `type_id`: 知识库类型ID（可选）
- `limit`: 返回数量（默认 20）
- `offset`: 偏移量（默认 0）
    """,
    responses={
        200: {
            "description": "成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "搜索成功",
                        "data": {
                            "keyword": "增值税",
                            "total": 5,
                            "items": []
                        }
                    }
                }
            }
        }
    }
)
async def search_knowledge_content_get(
    keyword: str = Query(..., description="搜索关键词"),
    user_id: Optional[str] = Query(None, description="用户ID"),
    type_id: Optional[str] = Query(None, description="知识库类型ID"),
    limit: Optional[str] = Query("20", description="返回数量"),
    offset: Optional[str] = Query("0", description="偏移量")
):
    """搜索知识库内容（GET方式）"""
    # 手动解析 limit 和 offset 参数
    try:
        parsed_limit = int(limit) if limit else 20
        parsed_limit = max(1, min(100, parsed_limit))  # 限制在 1-100 之间
    except (ValueError, TypeError):
        parsed_limit = 20

    try:
        parsed_offset = int(offset) if offset else 0
        parsed_offset = max(0, parsed_offset)  # 不能小于 0
    except (ValueError, TypeError):
        parsed_offset = 0

    result = knowledge_type_service.search_content(
        keyword=keyword,
        user_id=user_id,
        type_id=type_id,
        limit=parsed_limit,
        offset=parsed_offset
    )
    if not result["success"]:
        return response.fail(message=result.get("error", "搜索失败"))
    return response.success(data=result["data"], message="搜索成功")


@router.post(
    "/search/bases",
    summary="搜索知识库",
    description="""
按知识库名称搜索知识库。

**核心功能：**
- 输入关键词搜索知识库名称
- 支持用户筛选
- 返回知识库列表及其文档数量
- 支持分页查询

**请求参数：**
- `keyword`: 搜索关键词（必需）
- `user_id`: 用户ID（可选）
- `limit`: 返回数量（默认 20）
- `offset`: 偏移量（默认 0）
    """,
    responses={
        200: {
            "description": "搜索成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "搜索成功",
                        "data": {
                            "keyword": "增值税",
                            "total": 3,
                            "items": [
                                {
                                    "kb_name": "增值税政策库",
                                    "description": "增值税相关政策文档",
                                    "document_count": 10,
                                    "type_name": "增值税"
                                }
                            ]
                        }
                    }
                }
            }
        }
    }
)
async def search_knowledge_bases(request: SearchKnowledgeBasesRequest):
    """搜索知识库"""
    result = knowledge_type_service.search_knowledge_bases(
        keyword=request.keyword,
        user_id=request.user_id,
        limit=request.limit,
        offset=request.offset
    )
    if not result["success"]:
        return response.fail(message=result.get("error", "搜索失败"))
    return response.success(data=result["data"], message="搜索成功")


@router.get(
    "/search/bases",
    summary="搜索知识库（GET方式）",
    description="""
通过GET请求搜索知识库，方便快速测试。

**查询参数：**
- `keyword`: 搜索关键词（必需）
- `user_id`: 用户ID（可选）
- `limit`: 返回数量（默认 20）
- `offset`: 偏移量（默认 0）
    """,
    responses={
        200: {
            "description": "成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "搜索成功",
                        "data": {
                            "keyword": "税收",
                            "total": 10,
                            "items": []
                        }
                    }
                }
            }
        }
    }
)
async def search_knowledge_bases_get(
    keyword: str = Query(..., description="搜索关键词"),
    user_id: Optional[str] = Query(None, description="用户ID"),
    limit: Optional[str] = Query("20", description="返回数量"),
    offset: Optional[str] = Query("0", description="偏移量")
):
    """搜索知识库（GET方式）"""
    # 手动解析 limit 和 offset 参数
    try:
        parsed_limit = int(limit) if limit else 20
        parsed_limit = max(1, min(100, parsed_limit))  # 限制在 1-100 之间
    except (ValueError, TypeError):
        parsed_limit = 20

    try:
        parsed_offset = int(offset) if offset else 0
        parsed_offset = max(0, parsed_offset)  # 不能小于 0
    except (ValueError, TypeError):
        parsed_offset = 0

    result = knowledge_type_service.search_knowledge_bases(
        keyword=keyword,
        user_id=user_id,
        limit=parsed_limit,
        offset=parsed_offset
    )
    if not result["success"]:
        return response.fail(message=result.get("error", "搜索失败"))
    return response.success(data=result["data"], message="搜索成功")
