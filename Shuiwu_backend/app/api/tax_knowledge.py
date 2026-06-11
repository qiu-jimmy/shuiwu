"""税务知识文档管理路由"""
import asyncio
from typing import Optional

from fastapi import APIRouter, Query, Depends, Request

from app.schemas.tax_knowledge import (
    CreateTaxKnowledgeRequest,
    UpdateTaxKnowledgeRequest,
)
from app.services.tax_knowledge.tax_knowledge_service import tax_knowledge_service
from app.utils.response import response
from app.utils.dependencies import get_current_user_with_roles

router = APIRouter(prefix="/api/tax-knowledge", tags=["税务知识文档管理"])


async def _run_sync(func, *args, **kwargs):
    """在线程池中执行同步函数"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))


# ============================================================================
# CRUD 接口
# ============================================================================

@router.post(
    "/create",
    summary="创建税务知识文档",
    description="""
创建新的税务知识文档，同时存储原始 markdown 内容和清洗后的 JSON 内容。

**请求参数：**
- docType: 文档类型
- lawId: 法规ID
- lawName: 法规名称
- lawStatus: 法规状态（默认：全文有效）
- promulgationAnnouncement: 发布公告信息（可选）
- approvalInfo: 审批信息（可选）
- timeInfo: 时间信息（可选）
- chapters: 章节列表（可选）
- lawSource: 法规来源（可选）
- remark: 备注（可选）
- rawContent: 原始 markdown 内容（可选）
    """,
)
async def create_document(
    request: Request,
    doc_request: CreateTaxKnowledgeRequest,
    current_user: dict = Depends(get_current_user_with_roles)
):
    """创建税务知识文档"""
    try:
        doc_id = await _run_sync(
            tax_knowledge_service.create_document,
            request=doc_request,
            created_by=current_user.get("user_id"),
        )
        if doc_id:
            return response.success(data={"docId": doc_id}, message="创建成功")
        return response.fail(message="创建失败")
    except Exception as e:
        return response.fail(message=f"创建失败: {str(e)}")


@router.get(
    "/list",
    summary="查询税务知识文档列表",
    description="""
查询税务知识文档列表，支持分页和筛选。

**查询参数：**
- docType: 文档类型筛选（可选）
- keyword: 关键词搜索（可选，搜索法规名称和编号）
- page: 页码（默认：1）
- pageSize: 每页数量（默认：20，最大：100）

**返回：**
- 列表仅包含基本字段（docId, docType, lawId, lawName），不包含完整jsonContent
- 如需完整内容，请使用 /detail/{doc_id} 接口
- 总记录数
- 分页信息
    """,
)
async def list_documents(
    docType: Optional[str] = Query(None, description="文档类型筛选"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    page: int = Query(1, description="页码", ge=1),
    pageSize: int = Query(20, description="每页数量", ge=1, le=100),
):
    """查询税务知识文档列表"""
    try:
        result = await _run_sync(
            tax_knowledge_service.list_documents,
            doc_type=docType,
            keyword=keyword,
            page=page,
            page_size=pageSize,
        )
        return response.success(data=result, message="查询成功")
    except Exception as e:
        return response.fail(message=f"查询失败: {str(e)}")


@router.get(
    "/detail/{doc_id}",
    summary="获取税务知识文档详情",
    description="""
根据文档ID获取完整的文档详情，包含 raw_content 和 json_content。
    """,
)
async def get_document_detail(doc_id: str):
    """获取税务知识文档详情"""
    try:
        result = await _run_sync(
            tax_knowledge_service.get_document_by_id,
            doc_id=doc_id,
        )
        if result:
            return response.success(data=result, message="查询成功")
        return response.fail(message="文档不存在", code=404)
    except Exception as e:
        return response.fail(message=f"查询失败: {str(e)}")


@router.put(
    "/update/{doc_id}",
    summary="更新税务知识文档",
    description="""
更新税务知识文档。

**路径参数：**
- doc_id: 文档ID

**请求参数：**
- 所有字段均为可选，仅更新提供的字段

**需要认证:** 需要提供有效的 JWT Token
    """,
)
async def update_document(
    doc_id: str,
    doc_request: UpdateTaxKnowledgeRequest,
    current_user: dict = Depends(get_current_user_with_roles)
):
    """更新税务知识文档（需要认证）"""
    try:
        success = await _run_sync(
            tax_knowledge_service.update_document,
            doc_id=doc_id,
            request=doc_request,
        )
        if success:
            return response.success(message="更新成功")
        return response.fail(message="文档不存在或更新失败", code=404)
    except Exception as e:
        return response.fail(message=f"更新失败: {str(e)}")


@router.delete(
    "/delete/{doc_id}",
    summary="删除税务知识文档",
    description="""
删除税务知识文档。

**路径参数：**
- doc_id: 文档ID

**查询参数：**
- hard_delete: 是否硬删除（默认：false，软删除）

**需要认证:** 需要提供有效的 JWT Token
    """,
)
async def delete_document(
    doc_id: str,
    hard_delete: bool = Query(False, description="是否硬删除"),
    current_user: dict = Depends(get_current_user_with_roles)
):
    """删除税务知识文档（需要认证）"""
    try:
        success = await _run_sync(
            tax_knowledge_service.delete_document,
            doc_id=doc_id,
            hard_delete=hard_delete,
        )
        if success:
            delete_type = "硬删除" if hard_delete else "软删除"
            return response.success(message=f"{delete_type}成功")
        return response.fail(message="文档不存在或删除失败", code=404)
    except Exception as e:
        return response.fail(message=f"删除失败: {str(e)}")


# ============================================================================
# 前端格式接口（完全匹配 taxKnowledge.js 结构）
# ============================================================================

@router.get(
    "/frontend/list",
    summary="获取前端格式文档列表",
    description="""
获取前端格式的文档列表（仅包含基本字段）。

**返回格式：**
{
    "code": 1,
    "message": "查询成功",
    "data": {
        "items": [
            {
                "docId": "tkd_xxx",
                "docType": "行业通知",
                "lawId": "cctaa_2017_013",
                "lawName": "...",
                "remark": "备注摘要内容"
            }
        ],
        "total": 10,
        "page": 1,
        "page_size": 20
    }
}

**注意：** 列表仅返回基本字段，不包含完整内容（chapters等）。如需完整内容，请使用 /frontend/detail/{doc_id} 接口。
    """,
)
async def get_frontend_list(
    docType: Optional[str] = Query(None, description="文档类型筛选"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    page: int = Query(1, description="页码", ge=1),
    pageSize: int = Query(20, description="每页数量", ge=1, le=100),
):
    """获取前端格式文档列表"""
    try:
        result = await _run_sync(
            tax_knowledge_service.get_frontend_list,
            doc_type=docType,
            keyword=keyword,
            page=page,
            page_size=pageSize,
        )
        return response.success(data=result, message="查询成功")
    except Exception as e:
        return response.fail(message=f"查询失败: {str(e)}")


@router.get(
    "/frontend/detail/{doc_id}",
    summary="获取前端格式文档详情",
    description="""
根据文档ID获取完全匹配前端 taxKnowledge.js 数据结构的文档详情。

**返回格式：**
{
    "code": 1,
    "message": "查询成功",
    "data": {
        "docType": "行业通知",
        "lawId": "cctaa_2017_013",
        "lawName": "...",
        ...
    }
}
    """,
)
async def get_frontend_detail(doc_id: str):
    """获取前端格式文档详情"""
    try:
        result = await _run_sync(
            tax_knowledge_service.get_frontend_by_id,
            doc_id=doc_id,
        )
        if result:
            return response.success(data=result, message="查询成功")
        return response.fail(message="文档不存在", code=404)
    except Exception as e:
        return response.fail(message=f"查询失败: {str(e)}")
