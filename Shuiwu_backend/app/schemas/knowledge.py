"""知识库相关 Schema"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CreateKnowledgeBaseRequest(BaseModel):
    """创建知识库请求"""
    name: str
    description: str
    user_id: str
    type_id: Optional[str] = Field(None, description="知识库类型ID")
    is_system: bool = Field(False, description="是否为系统知识库（默认false）")
    chunking_rule: str = "fixed_size"  # fixed_size / semantic / recursive
    chunk_size: int = 5000
    chunk_overlap: int = 200
    embedder_model: str = "text-embedding-3-small"


class UploadDocumentRequest(BaseModel):
    """上传文档请求（单/多文件通用）"""
    kb_name: str
    user_id: str
    files: List[Dict[str, str]]  # [{filename, file_base64}]
    chunking_rule: str = "fixed_size"
    chunk_size: int = 5000
    chunk_overlap: int = 200
    metadata: Optional[Dict[str, Any]] = None


class BatchUploadRequest(UploadDocumentRequest):
    """批量上传文档请求"""
    pass


class SearchRequest(BaseModel):
    """知识库搜索请求"""
    user_id: str
    kb_name: str
    query: str
    top_k: int = 5
    search_type: Optional[str] = None  # "similarity", "keyword", "hybrid"


class KnowledgeBaseResponse(BaseModel):
    """知识库响应"""
    kb_name: str
    description: str
    user_id: str
    document_count: int
    type_id: Optional[str] = None
    is_system: bool = False


class SearchResultResponse(BaseModel):
    """搜索结果响应"""
    rank: int
    id: Optional[str] = None
    name: Optional[str] = None
    content: Optional[str] = None
    score: Optional[float] = None
    meta_data: Optional[Dict[str, Any]] = None
    content_id: Optional[str] = None


class ListKnowledgeBasesByTypeRequest(BaseModel):
    """根据类型列出知识库请求"""
    type_id: Optional[str] = Field(None, description="知识库类型ID（可选，为空则获取所有类型）")
    is_system: Optional[bool] = Field(None, description="是否为系统知识库（true=仅系统知识库，false=仅用户知识库，null=两者都获取）")
    status: str = Field("active", description="状态筛选")


class ImportFilesFromSystemRequest(BaseModel):
    """从文件系统导入文件到知识库请求"""
    kb_name: str = Field(..., description="知识库名称")
    user_id: str = Field(..., description="用户ID")
    file_ids: List[str] = Field(..., description="文件ID列表（从文件系统选择的文件）")
    chunking_rule: str = Field("fixed_size", description="分块规则")
    chunk_size: int = Field(5000, description="分块大小")
    chunk_overlap: int = Field(200, description="分块重叠")
    metadata: Optional[Dict[str, Any]] = Field(None, description="额外的元数据")


class RemoveDocumentsFromKnowledgeBaseRequest(BaseModel):
    """从知识库删除文档请求（管理员专用）"""
    kb_name: str = Field(..., description="知识库名称")
    user_id: str = Field(..., description="知识库所属用户ID")
    file_ids: Optional[List[str]] = Field(None, description="要删除的文件ID列表")
    filenames: Optional[List[str]] = Field(None, description="要删除的文件名列表（与file_ids二选一）")
    delete_from_file_system: bool = Field(False, description="是否同时从文件系统删除（business.files表）")

    class Config:
        schema_extra = {
            "example": {
                "kb_name": "测试知识库3",
                "user_id": "user_1234567890",
                "file_ids": ["file_abc123", "file_def456"],
                "delete_from_file_system": True
            }
        }

