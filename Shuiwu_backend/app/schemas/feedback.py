"""
问题反馈系统 Schema 定义
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ==================== 请求模型 ====================

class FeedbackSubmitRequest(BaseModel):
    """提交问题反馈请求"""
    feedback_type: str = Field(..., description="问题类型: bug-系统错误, feature-功能建议, complaint-投诉, other-其他")
    feedback_content: str = Field(..., min_length=1, max_length=5000, description="问题描述")
    feedback_images: Optional[List[str]] = Field(default=None, description="反馈图片URL列表")


class FeedbackStatusUpdateRequest(BaseModel):
    """更新反馈状态请求"""
    status: str = Field(..., description="状态: pending-待处理, processing-处理中, resolved-已解决, closed-已关闭")
    priority: Optional[str] = Field(default=None, description="优先级: low-低, normal-中, high-高, urgent-紧急")


class FeedbackReplyRequest(BaseModel):
    """管理员回复请求"""
    admin_reply: str = Field(..., min_length=1, max_length=2000, description="管理员回复内容")


# ==================== 响应模型 ====================

class FeedbackResponse(BaseModel):
    """问题反馈响应"""
    feedback_id: str
    user_id: str
    feedback_type: str
    feedback_content: str
    feedback_images: Optional[List[str]] = None
    admin_reply: Optional[str] = None
    admin_id: Optional[str] = None
    replied_at: Optional[datetime] = None
    status: str
    priority: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FeedbackDetailResponse(FeedbackResponse):
    """问题反馈详情响应（包含用户信息）"""
    user_nickname: Optional[str] = None
    user_phone: Optional[str] = None
    admin_nickname: Optional[str] = None


class FeedbackListResponse(BaseModel):
    """问题反馈列表响应"""
    total: int
    page: int
    page_size: int
    feedbacks: List[FeedbackResponse]


class FeedbackStatsResponse(BaseModel):
    """问题反馈统计响应"""
    pending_count: int = Field(description="待处理数量")
    processing_count: int = Field(description="处理中数量")
    resolved_count: int = Field(description="已解决数量")
    closed_count: int = Field(description="已关闭数量")
    urgent_count: int = Field(description="紧急问题数量")


# ==================== 查询参数模型 ====================

class FeedbackQueryParams(BaseModel):
    """问题反馈查询参数"""
    status: Optional[str] = None
    feedback_type: Optional[str] = None
    priority: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
