"""
客服管理相关的 Pydantic 模型
"""
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime


# ==================== 客服消息 ====================

class CustomerMessageCreate(BaseModel):
    """发送客服消息"""
    user_id: str
    session_id: Optional[str] = None
    message_type: str = "text"  # text, image, file
    content: str
    file_url: Optional[str] = None


class CustomerMessageResponse(BaseModel):
    """客服消息响应"""
    message_id: str
    user_id: str
    session_id: Optional[str] = None
    message_type: str
    sender_type: str  # user, system, customer_service
    sender_id: Optional[str] = None
    content: Optional[str] = None
    file_url: Optional[str] = None
    is_read: bool
    read_time: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CustomerMessageListResponse(BaseModel):
    """客服消息列表响应"""
    total: int
    messages: List[CustomerMessageResponse]


class MarkMessageReadRequest(BaseModel):
    """标记消息已读"""
    message_ids: List[str]


# ==================== 客服会话 ====================

class CustomerSessionCreate(BaseModel):
    """创建客服会话"""
    user_id: str


class CustomerSessionResponse(BaseModel):
    """客服会话响应"""
    session_id: str
    user_id: str
    customer_service_id: Optional[str] = None
    status: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    rating: Optional[int] = None
    feedback: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CustomerSessionListResponse(BaseModel):
    """客服会话列表响应"""
    total: int
    page: int
    page_size: int
    sessions: List[CustomerSessionResponse]


class CustomerSessionCloseRequest(BaseModel):
    """关闭客服会话"""
    session_id: str
    rating: Optional[int] = None
    feedback: Optional[str] = None


# ==================== 常见问题 ====================

class FAQCreate(BaseModel):
    """创建常见问题"""
    question: str
    answer: str
    category: Optional[str] = None
    sort_order: Optional[int] = 0


class FAQUpdate(BaseModel):
    """更新常见问题"""
    question: Optional[str] = None
    answer: Optional[str] = None
    category: Optional[str] = None
    sort_order: Optional[int] = None
    status: Optional[str] = None


class FAQResponse(BaseModel):
    """常见问题响应"""
    faq_id: str
    question: str
    answer: str
    category: Optional[str] = None
    sort_order: int
    view_count: int
    helpful_count: int
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class FAQListResponse(BaseModel):
    """常见问题列表响应"""
    total: int
    faqs: List[FAQResponse]


class FAQViewRequest(BaseModel):
    """FAQ浏览/点赞"""
    faq_id: str
    action: str  # view, helpful


# ==================== 客服统计 ====================

class CustomerServiceStatsResponse(BaseModel):
    """客服统计响应"""
    total_sessions: int
    active_sessions: int
    today_messages: int
    today_sessions: int
    avg_response_time: Optional[float] = None  # 平均响应时间（秒）
    total_messages: int
