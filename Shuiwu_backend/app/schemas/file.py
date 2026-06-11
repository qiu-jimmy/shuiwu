"""
文件管理相关的 Pydantic 模型
"""
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime


# ==================== 文件管理 ====================

class FileUploadFromUrlRequest(BaseModel):
    """从URL上传文件请求（用于已经上传到OSS的情况）"""
    file_name: str
    file_size: int
    file_type: str
    file_path: str  # OSS路径
    file_url: str  # 完整URL
    mime_type: Optional[str] = None
    category: Optional[str] = "document"
    folder_path: Optional[str] = None
    kb_name: Optional[str] = None


class OSSConfigRequest(BaseModel):
    """OSS配置请求"""
    access_key_id: str
    access_key_secret: str
    region: str = Field(default="cn-hangzhou", description="OSS区域")
    bucket: str
    endpoint: Optional[str] = Field(default=None, description="自定义endpoint（可选）")


class OSSConfigResponse(BaseModel):
    """OSS配置响应"""
    configured: bool
    bucket: Optional[str] = None
    region: Optional[str] = None
    message: Optional[str] = None


class FileUpdateRequest(BaseModel):
    """更新文件信息（file_id 从 URL 路径获取，不在请求体中）"""
    file_name: Optional[str] = None
    folder_path: Optional[str] = None
    kb_name: Optional[str] = None


class FileResponse(BaseModel):
    """文件响应"""
    file_id: str
    user_id: str
    file_name: str
    file_type: str
    file_size: int
    file_path: str
    file_url: str
    mime_type: Optional[str] = None
    category: Optional[str] = None
    folder_path: Optional[str] = None
    kb_name: Optional[str] = None
    status: str
    is_deleted: bool
    download_count: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class FileListResponse(BaseModel):
    """文件列表响应"""
    total: int
    page: int
    page_size: int
    files: List[FileResponse]


class FileQueryParams(BaseModel):
    """文件查询参数"""
    user_id: Optional[str] = None
    file_type: Optional[str] = None
    category: Optional[str] = None
    folder_path: Optional[str] = None
    kb_name: Optional[str] = None
    status: Optional[str] = None
    keyword: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    page: int = 1
    page_size: int = 20


class FileDeleteRequest(BaseModel):
    """删除文件请求"""
    file_ids: List[str]
    permanent: bool = False  # 是否永久删除


class FileBatchUpdateRequest(BaseModel):
    """批量更新文件"""
    file_ids: List[str]
    folder_path: Optional[str] = None
    kb_name: Optional[str] = None


# ==================== 文件分享 ====================

class FileShareCreate(BaseModel):
    """创建文件分享"""
    file_id: str
    share_type: str = "private"  # private, public, password
    password: Optional[str] = None
    expire_days: Optional[int] = None
    max_access_count: Optional[int] = None


class FileShareResponse(BaseModel):
    """文件分享响应"""
    share_id: str
    file_id: str
    user_id: str
    share_code: str
    share_type: str
    expire_time: Optional[datetime] = None
    access_count: int
    max_access_count: Optional[int] = None
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class FileShareAccessRequest(BaseModel):
    """访问分享文件"""
    share_code: str
    password: Optional[str] = None


class FileShareInfoResponse(BaseModel):
    """分享文件信息响应"""
    share_id: str
    file: FileResponse
    share_type: str
    is_expired: bool
    access_count: int
    max_access_count: Optional[int] = None


# ==================== 文件统计 ====================

class FileStorageStatsResponse(BaseModel):
    """文件存储统计响应"""
    user_id: str
    total_files: int
    total_size_mb: float
    file_type_stats: List[dict]  # [{file_type: "pdf", count: 10, size_mb: 5.2}]
    category_stats: List[dict]  # [{category: "document", count: 20, size_mb: 10.5}]
    today_uploads: int
    month_uploads: int


class FileAdminStatsResponse(BaseModel):
    """后台文件管理统计响应"""
    total_users: int
    total_files: int
    total_storage_mb: float
    today_uploads: int
    today_storage_mb: float
    file_type_distribution: List[dict]
    active_files: int
    deleted_files: int
