"""
分销推广相关的 Pydantic 模型
"""
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime


# ==================== 推广活动 ====================

class PromotionActivityCreate(BaseModel):
    """创建推广活动"""
    name: str
    description: Optional[str] = None
    activity_type: str  # register, order, custom
    reward_type: str  # cash, points, member_days
    reward_amount: Optional[float] = None
    reward_points: Optional[int] = None
    reward_member_days: Optional[int] = None
    min_order_amount: Optional[float] = None
    max_reward_per_user: Optional[float] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class PromotionActivityUpdate(BaseModel):
    """更新推广活动"""
    name: Optional[str] = None
    description: Optional[str] = None
    reward_amount: Optional[float] = None
    reward_points: Optional[int] = None
    reward_member_days: Optional[int] = None
    min_order_amount: Optional[float] = None
    max_reward_per_user: Optional[float] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: Optional[str] = None


class PromotionActivityResponse(BaseModel):
    """推广活动响应"""
    activity_id: str
    name: str
    description: Optional[str] = None
    activity_type: str
    reward_type: str
    reward_amount: Optional[float] = None
    reward_points: Optional[int] = None
    reward_member_days: Optional[int] = None
    min_order_amount: Optional[float] = None
    max_reward_per_user: Optional[float] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PromotionActivityListResponse(BaseModel):
    """推广活动列表响应"""
    activities: List[PromotionActivityResponse]


    # ==================== 分销商 ====================

class DistributorResponse(BaseModel):
    """分销商响应"""
    user_id: str
    distributor_code: str
    parent_id: Optional[str] = None
    distributor_level: int
    status: str
    total_children_count: int
    total_order_count: int
    total_commission: float
    available_commission: float
    frozen_commission: float
    total_withdrawn: float
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DistributorListResponse(BaseModel):
    """分销商列表响应"""
    total: int
    page: int
    page_size: int
    distributors: List[DistributorResponse]


class DistributorStatsResponse(BaseModel):
    """分销商统计响应"""
    user_id: str
    distributor_code: str
    nickname: Optional[str] = None
    phone: Optional[str] = None
    # 推广统计
    total_children_count: int
    total_order_count: int
    total_amount: float
    # 佣金统计
    total_commission: float
    available_commission: float
    frozen_commission: float
    total_withdrawn: float
    # 本月统计
    month_children_count: int
    month_order_count: int
    month_commission: float


# ==================== 分销记录 ====================

class DistributionRecordResponse(BaseModel):
    """分销记录响应"""
    record_id: str
    promoter_id: str
    new_user_id: str
    order_id: Optional[str] = None
    activity_id: Optional[str] = None
    commission_amount: float
    commission_status: str
    commission_type: str
    commission_rate: float
    order_amount: float
    available_time: Optional[datetime] = None
    settled_time: Optional[datetime] = None
    expire_time: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DistributionRecordListResponse(BaseModel):
    """分销记录列表响应"""
    total: int
    page: int
    page_size: int
    records: List[DistributionRecordResponse]


# ==================== 提现申请 ====================

class WithdrawalRequestCreate(BaseModel):
    """创建提现申请"""
    user_id: str
    amount: float
    withdrawal_method: str  # wechat, alipay, bank
    account_name: str
    account_number: str
    bank_name: Optional[str] = None
    bank_branch: Optional[str] = None


class WithdrawalRequestUpdate(BaseModel):
    """更新提现申请（审核）"""
    withdrawal_id: str
    action: str  # approve, reject
    reject_reason: Optional[str] = None
    transaction_id: Optional[str] = None


class WithdrawalRequestResponse(BaseModel):
    """提现申请响应"""
    withdrawal_id: str
    user_id: str
    amount: float
    withdrawal_method: str
    account_name: str
    account_number: str
    bank_name: Optional[str] = None
    bank_branch: Optional[str] = None
    status: str
    reject_reason: Optional[str] = None
    processed_by: Optional[str] = None
    processed_at: Optional[datetime] = None
    transaction_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class WithdrawalRequestListResponse(BaseModel):
    """提现申请列表响应"""
    total: int
    page: int
    page_size: int
    withdrawals: List[WithdrawalRequestResponse]


# ==================== 推广码 ====================

class DistributorCodeResponse(BaseModel):
    """推广码响应"""
    distributor_code: str
    qrcode_url: Optional[str] = None
    share_link: Optional[str] = None
    share_text: Optional[str] = None


class MiniQRCodeRequest(BaseModel):
    """生成小程序码请求"""
    page: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "page": "pages/index/index"
            }
        }
    )
