"""
模型管理相关的 Pydantic 模型
"""
from typing import Optional
from pydantic import BaseModel


class ModelCreateRequest(BaseModel):
    """创建模型请求"""
    id: str  # 模型ID
    name: str  # 模型名称
    provider: Optional[str] = None  # 提供商
    model_url: Optional[str] = None  # API地址
    model_api_key: Optional[str] = None  # API密钥
    description: Optional[str] = None  # 描述
    status: Optional[str] = None  # 状态
    context_window: Optional[int] = None  # 上下文长度


class ModelUpdateRequest(BaseModel):
    """更新模型请求"""
    name: Optional[str] = None
    provider: Optional[str] = None
    model_url: Optional[str] = None
    model_api_key: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    context_window: Optional[int] = None


class ModelValidateRequest(BaseModel):
    """验证模型配置请求"""
    model_id: str  # 模型ID


class ModelResponse(BaseModel):
    """模型响应"""
    id: str
    name: str
    provider: Optional[str] = None
    model_url: Optional[str] = None
    model_api_key: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    context_window: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

