"""知识库管理路由"""
import asyncio
from typing import Optional, Dict, Any

from fastapi import APIRouter, Query, Depends, Request

from app.schemas.knowledge import (
    BatchUploadRequest,
    CreateKnowledgeBaseRequest,
    ImportFilesFromSystemRequest,
    RemoveDocumentsFromKnowledgeBaseRequest,
    SearchRequest,
    UploadDocumentRequest,
)
from app.services.knowledge.knowledge_service import knowledge_service
from app.services.knowledge.knowledge_repository import knowledge_repository
from app.utils.response import response
from app.utils.dependencies import require_current_user, get_current_user_with_roles
from app.middleware.member_permission import (
    require_member_privilege,
    require_member_quota,
    require_member_features,
)

router = APIRouter(prefix="/api/knowledge-base", tags=["知识库管理"])


async def _run_sync(func, *args, **kwargs):
    """在线程池中执行同步函数"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))


@router.post(
    "/create",
    summary="创建知识库",
    description="""
创建新的知识库，支持指定知识库类型和分块配置。

**功能特性：**
- 支持关联知识库类型（type_id）
- 支持创建系统知识库（is_system=true）
- 可配置文档分块规则（fixed_size/semantic/recursive）
- 可自定义分块大小和重叠长度
- 支持选择不同的嵌入模型

**系统知识库说明：**
- 系统知识库（is_system=true）对所有用户可见
- 用户知识库（is_system=false）仅创建者可见
- 创建系统知识库通常需要管理员权限

**分块规则说明：**
- `fixed_size`: 固定大小分块，适合结构化文档
- `semantic`: 语义分块，根据内容智能切分
- `recursive`: 递归分块，多层结构处理
    """,
    responses={
        200: {
            "description": "创建成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "知识库 'test_kb' 创建成功",
                        "data": {
                            "kb_name": "test_kb",
                            "user_id": "user_123",
                            "type_id": "type_012",
                            "is_system": False
                        }
                    }
                }
            }
        },
        400: {
            "description": "请求参数错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "参数验证失败",
                        "data": {"errors": ["name: 知识库名称不能为空"]}
                    }
                }
            }
        }
    }
)
@require_member_quota("kb_count", consume=1)
async def create_knowledge_base(
    request: Request,
    kb_request: CreateKnowledgeBaseRequest,
    current_user: dict = Depends(get_current_user_with_roles)
):
    """创建知识库 - 需要知识库数量配额"""
    try:
        # 验证请求中的user_id与token中的用户是否一致
        if kb_request.user_id != current_user["user_id"]:
            # 如果是管理员，可以为其他用户创建知识库
            if not current_user.get("is_admin"):
                return response.fail(
                    message="无权为其他用户创建知识库",
                    code=0
                )

        # 如果要创建系统知识库，需要管理员权限
        if kb_request.is_system and not current_user.get("is_admin"):
            return response.fail(
                message="创建系统知识库需要管理员权限",
                code=0
            )

        kb = await _run_sync(
            knowledge_service.create_knowledge_base,
            name=kb_request.name,
            description=kb_request.description,
            user_id=kb_request.user_id,
            chunking_rule=kb_request.chunking_rule,
            chunk_size=kb_request.chunk_size,
            chunk_overlap=kb_request.chunk_overlap,
            embedder_model=kb_request.embedder_model,
            type_id=kb_request.type_id,
            is_system=kb_request.is_system,
        )
        return response.success(
            data={
                "kb_name": kb_request.name,
                "user_id": kb_request.user_id,
                "type_id": kb_request.type_id,
                "is_system": kb_request.is_system,
            },
            message=f"知识库 '{kb_request.name}' 创建成功"
        )
    except Exception as e:
        return response.fail(message=f"创建知识库失败: {str(e)}")


@router.get(
    "/list/system",
    summary="列出所有系统知识库",
    description="""
    获取所有系统知识库列表。

    **认证要求：** 需要在请求头中提供有效的 Bearer Token

    **说明：**
    - 返回所有系统知识库（is_system=true）
    - 所有用户都可以访问
    - 系统知识库由管理员创建，供所有用户使用

    **查询参数：**
    - type_id: 知识库类型ID（可选，用于筛选特定类型的系统知识库）

    **返回信息：**
    - 知识库列表
    - 每个知识库包含：名称、描述、类型、创建时间等信息
    """,
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "列出系统知识库成功",
                        "data": {
                            "knowledge_bases": [
                                {
                                    "kb_name": "税收政策库",
                                    "description": "包含各类税收政策和法规",
                                    "type_id": "type_001",
                                    "type_name": "税收知识",
                                    "is_system": True,
                                    "created_at": "2024-01-01T10:00:00",
                                    "created_by": "admin",
                                    "document_count": 150
                                },
                                {
                                    "kb_name": "财务会计知识库",
                                    "description": "财务会计相关知识和准则",
                                    "type_id": "type_002",
                                    "type_name": "财务知识",
                                    "is_system": True,
                                    "created_at": "2024-01-02T14:30:00",
                                    "created_by": "admin",
                                    "document_count": 200
                                }
                            ],
                            "total": 2
                        }
                    }
                }
            }
        },
        401: {
            "description": "未授权",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "未提供认证token",
                        "data": None
                    }
                }
            }
        }
    }
)
async def list_system_knowledge_bases(
    current_user_id: str = Depends(require_current_user),
    type_id: Optional[str] = Query(None, description="知识库类型ID（可选）")
):
    """列出所有系统知识库"""
    try:
        kb_list = await _run_sync(
            knowledge_repository.list_knowledge_bases_unified,
            user_id=current_user_id,
            type_id=type_id,
            is_system=True
        )
        return response.success(data=kb_list, message="列出系统知识库成功")
    except Exception as e:
        return response.fail(message=f"列出系统知识库失败: {str(e)}")


@router.get(
    "/list/user",
    summary="列出当前用户的个人知识库",
    description="""
    获取当前用户的个人知识库列表。

    **认证要求：** 需要在请求头中提供有效的 Bearer Token

    **说明：**
    - 只返回当前用户创建的个人知识库（is_system=false）
    - 不包括系统知识库
    - 支持按名称和类型筛选

    **查询参数：**
    - kb_name: 知识库名称（可选，精确匹配）
    - type_id: 知识库类型ID（可选，用于筛选特定类型的知识库）

    **返回信息：**
    - 个人知识库列表
    - 每个知识库包含：名称、描述、类型、创建时间、文档数量等信息
    """,
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "列出个人知识库成功",
                        "data": {
                            "knowledge_bases": [
                                {
                                    "kb_name": "我的税务文档",
                                    "description": "个人收集的税务相关文档",
                                    "type_id": "type_001",
                                    "type_name": "税收知识",
                                    "is_system": False,
                                    "created_at": "2024-01-15T10:00:00",
                                    "created_by": "user_123",
                                    "document_count": 25
                                },
                                {
                                    "kb_name": "公司财务资料",
                                    "description": "公司内部的财务资料和报表",
                                    "type_id": "type_002",
                                    "type_name": "财务知识",
                                    "is_system": False,
                                    "created_at": "2024-01-16T14:30:00",
                                    "created_by": "user_123",
                                    "document_count": 18
                                }
                            ],
                            "total": 2
                        }
                    }
                }
            }
        },
        401: {
            "description": "未授权",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "未提供认证token",
                        "data": None
                    }
                }
            }
        }
    }
)
async def list_user_knowledge_bases(
    current_user_id: str = Depends(require_current_user),
    kb_name: Optional[str] = Query(None, description="知识库名称（可选，精确匹配）"),
    type_id: Optional[str] = Query(None, description="知识库类型ID（可选）")
):
    """列出当前用户的个人知识库"""
    try:
        kb_list = await _run_sync(
            knowledge_repository.list_knowledge_bases_unified,
            user_id=current_user_id,
            kb_name=kb_name,
            type_id=type_id,
            is_system=False
        )
        return response.success(data=kb_list, message="列出个人知识库成功")
    except Exception as e:
        return response.fail(message=f"列出个人知识库失败: {str(e)}")


@router.post(
    "/upload",
    summary="上传文档到知识库",
    description="""
上传文档到知识库，支持多文件上传，使用base64编码。

**功能特性：**
- 支持多文件批量上传
- 文件内容使用 base64 编码传输
- 自动进行文档分块和向量化
- 支持 PDF、DOCX、TXT、PPTX、CSV/Excel 等格式

**请求参数：**
- `kb_name`: 目标知识库名称
- `user_id`: 用户ID
- `files`: 文件列表，每个文件包含 filename 和 file_base64
- `chunking_rule`: 分块规则（可选，默认 fixed_size）
- `chunk_size`: 分块大小（可选，默认 5000）
- `chunk_overlap`: 分块重叠（可选，默认 200）

**返回结果：**
- 每个文件的上传状态
- 文件名和处理结果
    """,
    responses={
        200: {
            "description": "上传成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "成功上传 2 个文档",
                        "data": {
                            "results": [
                                {
                                    "status": "success",
                                    "message": "文档 增值税政策.txt 已成功上传到知识库",
                                    "filename": "增值税政策.txt",
                                    "user_id": "user_123"
                                },
                                {
                                    "status": "success",
                                    "message": "文档 企业所得税.txt 已成功上传到知识库",
                                    "filename": "企业所得税.txt",
                                    "user_id": "user_123"
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
                        "message": "知识库不存在,请先创建知识库"
                    }
                }
            }
        }
    }
)
@require_member_features(quotas={"kb_documents": 1, "file_storage_mb": 10})
async def upload_document(
    request: Request,
    upload_request: UploadDocumentRequest
):
    """上传文档到知识库(兼容 Back 项目,多文件循环上传) - 需要知识库文档和文件存储配额"""
    try:
        # 使用 get_or_load_knowledge 自动加载知识库（避免重启后缓存失效）
        kb = knowledge_service.get_or_load_knowledge(
            user_id=upload_request.user_id,
            kb_name=upload_request.kb_name,
        )
        results = []
        for f in upload_request.files:
            result = await _run_sync(
                knowledge_service.upload_document_from_base64,
                knowledge=kb,
                file_base64=f["file_base64"],
                filename=f["filename"],
                user_id=upload_request.user_id,
                chunking_rule=upload_request.chunking_rule,
                chunk_size=upload_request.chunk_size,
                chunk_overlap=upload_request.chunk_overlap,
            )
            results.append(result)

        return response.success(
            data={"results": results},
            message=f"成功上传 {len(results)} 个文档"
        )
    except Exception as e:
        return response.fail(message=f"上传文档失败: {str(e)}")


@router.post(
    "/upload-batch",
    summary="批量上传文档",
    description="""
批量上传文档到知识库，对齐 Back 项目 /upload-batch 行为。

与 /upload 接口的区别：
- 优化了批量处理逻辑
- 使用异步批量处理提升性能
- 支持更大的文件批量上传
    """,
    responses={
        200: {
            "description": "成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "成功处理 10 个文档",
                        "data": {
                            "results": [
                                {
                                    "status": "success",
                                    "filename": "doc1.pdf"
                                }
                            ]
                        }
                    }
                }
            }
        }
    }
)
@require_member_features(quotas={"kb_documents": 1, "file_storage_mb": 10})
async def upload_documents_batch(
    request: Request,
    batch_request: BatchUploadRequest
):
    """批量上传文档,对齐 Back 项目 /upload-batch 行为 - 需要知识库文档和文件存储配额"""
    try:
        kb = knowledge_service.get_or_load_knowledge(
            user_id=batch_request.user_id,
            kb_name=batch_request.kb_name,
        )

        results = await knowledge_service.upload_documents_batch_async(
            knowledge=kb,
            files=batch_request.files,
            user_id=batch_request.user_id,
            chunking_rule=batch_request.chunking_rule,
            chunk_size=batch_request.chunk_size,
            chunk_overlap=batch_request.chunk_overlap,
            metadata=batch_request.metadata,
        )
        return response.success(
            data={"results": results},
            message=f"成功处理 {len(results)} 个文档"
        )
    except Exception as exc:
        return response.fail(message=str(exc))


@router.post(
    "/search",
    summary="搜索知识库",
    description="""
在知识库中搜索相关内容，基于向量相似度进行语义搜索。

**搜索模式：**
- `similarity`: 向量相似度搜索（默认）
- `keyword`: 关键词搜索
- `hybrid`: 混合搜索（相似度+关键词）

**请求参数：**
- `user_id`: 用户ID
- `kb_name`: 知识库名称
- `query`: 搜索查询文本
- `top_k`: 返回结果数量（默认 5）
- `search_type`: 搜索类型（可选）

**返回结果：**
- `results`: 搜索结果列表，包含内容、相似度分数等
- `count`: 结果数量
    """,
    responses={
        200: {
            "description": "搜索成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "搜索知识库成功",
                        "data": {
                            "results": [
                                {
                                    "rank": 1,
                                    "id": "chunk_001",
                                    "name": "增值税政策.txt",
                                    "content": "增值税税率分为三档：17%、13%和零税率...",
                                    "score": 0.95,
                                    "meta_data": {
                                        "source": "增值税政策.txt",
                                        "page": 1
                                    }
                                },
                                {
                                    "rank": 2,
                                    "id": "chunk_002",
                                    "name": "增值税政策.txt",
                                    "content": "纳税人销售货物、提供加工修理修配劳务...",
                                    "score": 0.87,
                                    "meta_data": {
                                        "source": "增值税政策.txt",
                                        "page": 2
                                    }
                                }
                            ],
                            "count": 2
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
                        "message": "知识库不存在"
                    }
                }
            }
        }
    }
)
@require_member_privilege("rag")
async def search_knowledge_base(
    request: Request,
    search_request: SearchRequest
):
    """搜索知识库 - 需要RAG权限"""
    try:
        result = await _run_sync(
            knowledge_service.search_knowledge_base,
            user_id=search_request.user_id,
            kb_name=search_request.kb_name,
            query=search_request.query,
            top_k=search_request.top_k,
            search_type=search_request.search_type,
        )
        return response.success(data=result, message="搜索知识库成功")
    except Exception as e:
        return response.fail(message=f"搜索知识库失败: {str(e)}")


@router.get(
    "/documents",
    summary="获取知识库文档列表",
    description="""
获取知识库中的文档列表（支持分页和搜索）。

**查询参数：**
- `table_name`: 知识库表名（如 kb_user_123_abc12345）
- `page`: 页码（默认1）
- `page_size`: 每页数量（默认20，最大100）
- `search`: 搜索关键词（可选，用于搜索文件名）

**返回字段：**
- `documents`: 文档列表
  - `filename`: 文件名
  - `file_id`: 文件ID
  - `parse_status`: 解析状态
  - `created_at`: 上传时间
- `total_documents`: 文档总数
- `page`: 当前页码
- `page_size`: 每页数量
- `total_pages`: 总页数
- `kb_name`: 知识库名称
- `user_id`: 用户ID

**认证要求：** 需要在请求头中提供有效的 Bearer Token
**权限说明：** 只能查询自己的知识库或系统知识库
    """,
    responses={
        200: {
            "description": "成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "获取文档列表成功",
                        "data": {
                            "kb_name": "政策税务法规",
                            "user_id": "user_2689ea75e1114ec4",
                            "total_documents": 50,
                            "page": 1,
                            "page_size": 20,
                            "total_pages": 3,
                            "documents": [
                                {
                                    "filename": "增值税政策.txt",
                                    "file_id": "file_abc123",
                                    "parse_status": "已解析",
                                    "created_at": "2026-01-13T10:00:00"
                                },
                                {
                                    "filename": "企业所得税.pdf",
                                    "file_id": "file_def456",
                                    "parse_status": "已解析",
                                    "created_at": "2026-01-13T11:00:00"
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
                        "message": "table_name 不能为空"
                    }
                }
            }
        },
        403: {
            "description": "权限不足",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "无权访问该知识库"
                    }
                }
            }
        }
    }
)
async def list_documents(
    table_name: str = Query(..., description="知识库表名"),
    page: int = Query(1, description="页码（默认1）", ge=1),
    page_size: int = Query(20, description="每页数量（默认20，最大100）", ge=1, le=100),
    search: Optional[str] = Query(None, description="搜索关键词（可选，用于搜索文件名）"),
    current_user: dict = Depends(get_current_user_with_roles)
):
    """获取知识库的文档列表（支持分页和搜索）"""
    try:
        user_id = current_user.get("user_id")
        is_admin = current_user.get("is_admin", False)

        result = await _run_sync(
            knowledge_service.list_documents_by_table_name,
            table_name=table_name,
            current_user_id=user_id,
            is_admin=is_admin,
            page=page,
            page_size=page_size,
            search=search,
        )
        return response.success(data=result, message="获取文档列表成功")
    except Exception as e:
        return response.fail(message=f"获取文档列表失败: {str(e)}")


@router.delete(
    "/{kb_name}",
    summary="删除知识库",
    description="""
删除指定的知识库。

**路径参数：**
- `kb_name`: 要删除的知识库名称

**认证要求：** 需要在请求头中提供有效的 Bearer Token

**权限说明：**
- 普通用户：软删除（标记 status='deleted'，保留数据和表结构，可恢复）
- 管理员：硬删除（物理删除表和记录，不可恢复）

**注意事项：**
- 普通用户只能删除自己创建的知识库
- 管理员可以硬删除任何知识库（包括其他用户的）
- 软删除的知识库不会在列表中显示，但数据可恢复
    """,
    responses={
        200: {
            "description": "删除成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "知识库 'test_kb' 删除成功",
                        "data": None
                    }
                }
            }
        },
        400: {
            "description": "知识库不存在",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "知识库 'test_kb' 不存在",
                        "data": None
                    }
                }
            }
        }
    }
)
async def delete_knowledge_base(
    kb_name: str,
    current_user: dict = Depends(get_current_user_with_roles)
):
    """
    删除知识库

    权限说明：
    - 普通用户：软删除（status -> deleted，保留数据可恢复）
    - 管理员：硬删除（DROP TABLE + 物理删除记录，不可恢复）
    """
    try:
        user_id = current_user.get("user_id")
        is_admin = current_user.get("is_admin", False)

        success = await _run_sync(
            knowledge_service.delete_knowledge_base,
            user_id=user_id,
            kb_name=kb_name,
            hard_delete=is_admin,  # 管理员硬删除，普通用户软删除
            is_admin=is_admin,     # 传递管理员标识用于权限检查
        )
        if success:
            delete_type = "硬删除" if is_admin else "软删除"
            return response.success(message=f"知识库 '{kb_name}' {delete_type}成功")
        # 未删除成功,视为知识库不存在
        return response.fail(message=f"知识库 '{kb_name}' 不存在或无权删除")
    except Exception as e:
        return response.fail(message=f"删除知识库失败: {str(e)}")


@router.post(
    "/import-files",
    summary="从文件系统导入文件到知识库",
    description="""
从文件系统选择已上传的文件，批量导入到指定知识库。

**功能特性：**
- 支持多文件批量导入
- 自动从OSS下载文件内容
- 自动进行文档分块和向量化
- 自动更新文件的kb_name关联
- 支持自定义分块规则
- 部分失败不影响其他文件导入

**请求参数：**
- `kb_name`: 目标知识库名称
- `user_id`: 用户ID
- `file_ids`: 文件ID列表（从文件系统选择）
- `chunking_rule`: 分块规则（可选，默认 fixed_size）
- `chunk_size`: 分块大小（可选，默认 5000）
- `chunk_overlap`: 分块重叠（可选，默认 200）
- `metadata`: 额外的元数据（可选）

**返回结果：**
- 每个文件的导入状态
- 文件名和处理结果
- 成功/失败统计

**认证要求：** 需要在请求头中提供有效的 Bearer Token

**使用场景：**
- 先通过文件管理接口上传文件到OSS
- 然后通过此接口将文件导入到知识库进行向量化
- 适用于文件已存在于系统中的场景
    """,
    responses={
        200: {
            "description": "导入成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "成功导入 3 个文件",
                        "data": {
                            "results": [
                                {
                                    "status": "success",
                                    "message": "文档 增值税政策.pdf 已成功导入知识库",
                                    "filename": "增值税政策.pdf",
                                    "file_id": "file_1234567890abcdef",
                                    "user_id": "user_123"
                                },
                                {
                                    "status": "success",
                                    "message": "文档 企业所得税.docx 已成功导入知识库",
                                    "filename": "企业所得税.docx",
                                    "file_id": "file_2345678901bcdef",
                                    "user_id": "user_123"
                                },
                                {
                                    "status": "success",
                                    "message": "文档 个人所得税.txt 已成功导入知识库",
                                    "filename": "个人所得税.txt",
                                    "file_id": "file_3456789012cdefg",
                                    "user_id": "user_123"
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
                    "examples": {
                        "empty_file_ids": {
                            "summary": "文件ID列表为空",
                            "value": {
                                "code": 0,
                                "message": "file_ids 不能为空",
                                "data": None
                            }
                        },
                        "kb_not_found": {
                            "summary": "知识库不存在",
                            "value": {
                                "code": 0,
                                "message": "知识库 'tax_kb' 不存在",
                                "data": None
                            }
                        },
                        "partial_failure": {
                            "summary": "部分文件导入失败",
                            "value": {
                                "code": 1,
                                "message": "导入完成，成功 2 个，失败 1 个",
                                "data": {
                                    "results": [
                                        {
                                            "status": "success",
                                            "message": "文档 增值税政策.pdf 已成功导入知识库",
                                            "filename": "增值税政策.pdf",
                                            "file_id": "file_1234567890abcdef",
                                            "user_id": "user_123"
                                        },
                                        {
                                            "status": "error",
                                            "message": "文件不存在或无权访问",
                                            "file_id": "file_invalid_id",
                                            "user_id": "user_123"
                                        }
                                    ]
                                }
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "未授权",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "未提供认证token",
                        "data": None
                    }
                }
            }
        }
    }
)
@require_member_features(quotas={"kb_documents": 1, "file_storage_mb": 10})
async def import_files_from_file_system(
    request: Request,
    import_request: ImportFilesFromSystemRequest,
    current_user: dict = Depends(get_current_user_with_roles)
):
    """从文件系统导入文件到知识库 - 需要知识库文档和文件存储配额

    权限说明：
    - 普通用户：只能导入自己上传的文件
    - 管理员：可以导入任何用户的文件
    """
    try:
        # 验证file_ids不为空
        if not import_request.file_ids or len(import_request.file_ids) == 0:
            return response.fail(message="file_ids 不能为空")

        # 获取用户信息
        user_id = current_user.get("user_id")
        is_admin = current_user.get("is_admin", False)

        # 调用service层方法
        results = await _run_sync(
            knowledge_service.import_files_from_file_system,
            user_id=user_id,
            kb_name=import_request.kb_name,
            file_ids=import_request.file_ids,
            chunking_rule=import_request.chunking_rule,
            chunk_size=import_request.chunk_size,
            chunk_overlap=import_request.chunk_overlap,
            metadata=import_request.metadata,
            is_admin=is_admin,  # 传递管理员标识
        )

        # 统计成功和失败数量
        success_count = sum(1 for r in results if r.get("status") == "success")
        failed_count = len(results) - success_count

        # 返回结果
        if success_count == 0:
            return response.fail(
                data={"results": results},
                message=f"导入失败，{failed_count} 个文件均无法导入"
            )
        elif failed_count == 0:
            return response.success(
                data={"results": results},
                message=f"成功导入 {success_count} 个文件"
            )
        else:
            return response.success(
                data={"results": results},
                message=f"导入完成，成功 {success_count} 个，失败 {failed_count} 个"
            )

    except Exception as e:
        return response.fail(message=f"导入文件失败: {str(e)}")


@router.post(
    "/admin/remove-documents",
    summary="从知识库删除文档（管理员专用）",
    description="""
管理员从指定用户的知识库中删除文档。

**功能特性：**
- 管理员可以删除任何用户知识库中的文档
- 支持按 file_id 或 filename 删除
- 自动从知识库表删除对应的文档记录
- 自动更新 knowledge_base_registry 的 document_ids 字段
- 可选择是否同时从文件系统删除（business.files表）

**权限要求：** 管理员权限

**请求参数：**
- `kb_name`: 知识库名称
- `user_id`: 知识库所属用户ID
- `file_ids`: 要删除的文件ID列表（与filenames二选一）
- `filenames`: 要删除的文件名列表（与file_ids二选一）
- `delete_from_file_system`: 是否同时从文件系统删除（默认false）

**使用场景：**
- 管理员帮用户删除错误上传的文件
- 管理员清理违规或不当内容
- 管理员维护知识库数据质量
    """,
    responses={
        200: {
            "description": "删除成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "删除完成，成功 2 个，失败 0 个",
                        "data": {
                            "results": [
                                {
                                    "status": "success",
                                    "message": "文件 增值税政策.docx 已从知识库删除",
                                    "file_id": "file_abc123",
                                    "filename": "增值税政策.docx"
                                }
                            ]
                        }
                    }
                }
            }
        },
        401: {
            "description": "未授权",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "未提供认证token",
                        "data": None
                    }
                }
            }
        },
        403: {
            "description": "权限不足",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "需要管理员权限",
                        "data": None
                    }
                }
            }
        }
    }
)
async def remove_documents_from_knowledge_base(
    request: RemoveDocumentsFromKnowledgeBaseRequest,
    current_user: dict = Depends(get_current_user_with_roles)
):
    """从知识库删除文档（管理员专用）"""
    # 权限检查：只允许管理员操作
    if not current_user.get("is_admin", False):
        return response.fail(message="需要管理员权限", code=403)

    try:
        results = await _run_sync(
            knowledge_service.remove_documents_from_knowledge_base,
            user_id=request.user_id,
            kb_name=request.kb_name,
            file_ids=request.file_ids,
            filenames=request.filenames,
            delete_from_file_system=request.delete_from_file_system,
        )

        # 统计成功和失败数量
        success_count = sum(1 for r in results if r.get("status") == "success")
        failed_count = len(results) - success_count

        # 返回结果
        if success_count == 0:
            return response.fail(
                data={"results": results},
                message=f"删除失败，{failed_count} 个文件均无法删除"
            )
        elif failed_count == 0:
            return response.success(
                data={"results": results},
                message=f"成功删除 {success_count} 个文件"
            )
        else:
            return response.success(
                data={"results": results},
                message=f"删除完成，成功 {success_count} 个，失败 {failed_count} 个"
            )

    except Exception as e:
        return response.fail(message=f"删除文档失败: {str(e)}")

