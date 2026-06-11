"""
用户管理相关的 Pydantic 模型
"""
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime


# ==================== 用户相关 ====================

class UserBase(BaseModel):
    """用户基础信息"""
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None


class UserCreate(BaseModel):
    """创建用户（微信登录）"""
    wx_openid: str
    wx_unionid: Optional[str] = None
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None


class UserUpdate(BaseModel):
    """更新用户信息"""
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None


class UserResponse(BaseModel):
    """用户响应"""
    user_id: str
    wx_openid: Optional[str] = None
    wx_unionid: Optional[str] = None
    phone: Optional[str] = None
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    status: str
    user_type: str
    member_level: str
    member_package_name: Optional[str] = None  # 套餐名称
    member_expire_at: Optional[datetime] = None
    register_time: Optional[datetime] = None
    last_login_time: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_distributor: bool = False
    distributor_code: Optional[str] = None
    total_commission: float = 0.0
    is_enterprise_verified: bool = False
    is_tax_accountant: bool = False

    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    """用户列表响应"""
    total: int
    page: int
    page_size: int
    users: List[UserResponse]


class UserStatusUpdate(BaseModel):
    """更新用户状态"""
    user_id: str
    status: str  # normal, disabled, banned, pending_review
    reason: Optional[str] = None


# ==================== 用户标签 ====================

class UserTagCreate(BaseModel):
    """创建用户标签"""
    user_id: str
    tag_name: str
    tag_type: Optional[str] = "custom"  # system, custom


class UserTagResponse(BaseModel):
    """用户标签响应"""
    id: int
    user_id: str
    tag_name: str
    tag_type: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ==================== 用户审核 ====================

class UserViolationCreate(BaseModel):
    """创建用户违规记录"""
    user_id: str
    violation_type: str
    violation_content: Optional[str] = None
    report_source: Optional[str] = "system"
    reporter_id: Optional[str] = None


class UserViolationHandle(BaseModel):
    """处理用户违规"""
    violation_id: str
    handle_status: str  # warning, banned, ignored
    handle_result: Optional[str] = None
    penalty_days: Optional[int] = None


class UserViolationResponse(BaseModel):
    """用户违规记录响应"""
    violation_id: str
    user_id: str
    violation_type: str
    violation_content: Optional[str] = None
    report_source: Optional[str] = None
    reporter_id: Optional[str] = None
    handle_status: str
    handle_result: Optional[str] = None
    penalty_days: Optional[int] = None
    penalty_expire_at: Optional[datetime] = None
    handled_by: Optional[str] = None
    handled_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserAppealCreate(BaseModel):
    """用户申诉申请"""
    user_id: str
    violation_id: str
    appeal_reason: str
    appeal_evidence: Optional[List[str]] = None  # 证据文件URL列表


class UserAppealHandle(BaseModel):
    """处理用户申诉"""
    appeal_id: str
    status: str  # approved, rejected
    review_result: Optional[str] = None


class UserAppealResponse(BaseModel):
    """用户申诉响应"""
    appeal_id: str
    user_id: str
    violation_id: str
    appeal_reason: str
    appeal_evidence: Optional[List[str]] = None
    status: str
    review_result: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ==================== 用户行为日志 ====================

class UserActionLogResponse(BaseModel):
    """用户行为日志响应"""
    id: int
    user_id: str
    action_type: str
    action_module: Optional[str] = None
    action_detail: Optional[dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserActionLogListResponse(BaseModel):
    """用户行为日志列表响应"""
    total: int
    page: int
    page_size: int
    logs: List[UserActionLogResponse]
