"""知识库类型相关 Schema"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class KnowledgeTypeBase(BaseModel):
    """知识库类型基础模型"""
    type_id: str = Field(..., description="类型ID")
    type_name: str = Field(..., description="类型名称")
    type_code: str = Field(..., description="类型代码")
    description: Optional[str] = Field(None, description="类型描述")
    icon: Optional[str] = Field(None, description="图标")
    sort_order: int = Field(0, description="排序顺序")
    is_system: bool = Field(True, description="是否系统内置")
    status: str = Field("active", description="状态")


class KnowledgeTypeResponse(KnowledgeTypeBase):
    """知识库类型响应"""
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")


class CreateKnowledgeTypeRequest(BaseModel):
    """创建知识库类型请求"""
    type_name: str = Field(..., description="类型名称", min_length=1, max_length=100)
    type_code: str = Field(..., description="类型代码（英文标识）", min_length=1, max_length=50)
    description: Optional[str] = Field(None, description="类型描述")
    icon: Optional[str] = Field(None, description="图标")
    sort_order: int = Field(0, description="排序顺序")
    status: str = Field("active", description="状态")


class UpdateKnowledgeTypeRequest(BaseModel):
    """更新知识库类型请求"""
    type_name: Optional[str] = Field(None, description="类型名称", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="类型描述")
    icon: Optional[str] = Field(None, description="图标")
    sort_order: Optional[int] = Field(None, description="排序顺序")
    status: Optional[str] = Field(None, description="状态")


class KnowledgeTypeListResponse(BaseModel):
    """知识库类型列表响应"""
    total: int = Field(..., description="总数")
    items: List[KnowledgeTypeResponse] = Field(..., description="类型列表")


class CreateKnowledgeBaseWithTypeRequest(BaseModel):
    """创建知识库请求（带类型）"""
    name: str = Field(..., description="知识库名称", min_length=1, max_length=100)
    description: str = Field(..., description="知识库描述")
    user_id: str = Field(..., description="用户ID")
    type_id: Optional[str] = Field(None, description="知识库类型ID")
    chunking_rule: str = Field("fixed_size", description="分块规则")
    chunk_size: int = Field(5000, description="分块大小")
    chunk_overlap: int = Field(200, description="分块重叠")
    embedder_model: str = Field("text-embedding-3-small", description="嵌入模型")


# ============================================================================
# 搜索相关 Schema
# ============================================================================

class SearchResultItem(BaseModel):
    """搜索结果项"""
    id: str = Field(..., description="分块ID")
    name: str = Field(..., description="文档名称")
    filename: Optional[str] = Field(None, description="文件名")
    doc_id: Optional[str] = Field(None, description="文档ID")
    content_preview: str = Field(..., description="内容预览")
    rank: float = Field(..., description="相关度分数")
    table_name: str = Field(..., description="知识库表名")
    user_id: str = Field(..., description="用户ID")
    kb_name: str = Field(..., description="知识库名称")


class SearchContentResponse(BaseModel):
    """搜索内容响应"""
    keyword: str = Field(..., description="搜索关键词")
    total: int = Field(..., description="结果总数")
    items: List[SearchResultItem] = Field(..., description="搜索结果列表")


class KnowledgeBaseSearchItem(BaseModel):
    """知识库搜索结果项"""
    table_name: str = Field(..., description="表名")
    user_id: str = Field(..., description="用户ID")
    kb_name: str = Field(..., description="知识库名称")
    document_count: int = Field(..., description="文档数量")


class SearchKnowledgeBasesResponse(BaseModel):
    """搜索知识库响应"""
    total: int = Field(..., description="结果总数")
    items: List[KnowledgeBaseSearchItem] = Field(..., description="知识库列表")
    limit: int = Field(..., description="每页数量")
    offset: int = Field(..., description="偏移量")


class SearchContentRequest(BaseModel):
    """搜索内容请求"""
    keyword: str = Field(..., description="搜索关键词", min_length=1)
    user_id: Optional[str] = Field(None, description="用户ID（可选）")
    type_id: Optional[str] = Field(None, description="知识库类型ID（可选）")
    limit: int = Field(20, description="返回数量", ge=1, le=100)
    offset: int = Field(0, description="偏移量", ge=0)


class SearchKnowledgeBasesRequest(BaseModel):
    """搜索知识库请求"""
    keyword: str = Field(..., description="搜索关键词", min_length=1)
    user_id: Optional[str] = Field(None, description="用户ID（可选）")
    limit: int = Field(20, description="返回数量", ge=1, le=100)
    offset: int = Field(0, description="偏移量", ge=0)
