"""
积分系统相关的 Pydantic 模型
"""
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


# ==================== 用户积分相关 ====================

class PointBalanceResponse(BaseModel):
    """积分余额响应"""
    points_balance: int = Field(..., description="积分余额", ge=0)


class PointRecordResponse(BaseModel):
    """积分记录响应"""
    record_id: str = Field(..., description="记录ID")
    points: int = Field(..., description="积分数量", gt=0)
    change_type: str = Field(..., description="变化类型: order_payment-订单支付, invitation_reward-邀请奖励")
    change_reason: str = Field(..., description="变化说明")
    related_order_id: Optional[str] = Field(None, description="关联订单ID")
    related_user_id: Optional[str] = Field(None, description="关联用户ID（邀请奖励时）")
    related_user_nickname: Optional[str] = Field(None, description="关联用户昵称")
    order_amount: Optional[float] = Field(None, description="订单金额（支付积分时）")
    balance_after: int = Field(..., description="变动后余额")
    created_at: datetime = Field(..., description="创建时间")

    model_config = {"from_attributes": True}


class PointRecordsListResponse(BaseModel):
    """积分记录列表响应"""
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")
    records: List[PointRecordResponse] = Field(..., description="积分记录列表")


# ==================== 管理端积分配置相关 ====================

class PointsConfigResponse(BaseModel):
    """积分配置响应"""
    payment_points_rate: int = Field(..., description="支付积分比例（1元=N积分）", ge=1)
    invitation_reward_points: int = Field(..., description="邀请奖励积分", ge=0)


class PointsConfigUpdate(BaseModel):
    """积分配置更新"""
    payment_points_rate: int = Field(..., description="支付积分比例（1元=N积分）", ge=1, le=1000)
    invitation_reward_points: int = Field(..., description="邀请奖励积分", ge=0, le=10000)


class PointsStatisticsResponse(BaseModel):
    """积分统计响应"""
    total_users_with_points: int = Field(..., description="有积分的用户数")
    total_points_issued: int = Field(..., description="累计发放积分")
    points_by_type: dict = Field(..., description="按类型统计的积分")


class GrantPointsRequest(BaseModel):
    """手动赠送积分请求"""
    user_id: str = Field(..., description="用户ID")
    points: int = Field(..., description="积分数量", ge=1, le=1000000)
    reason: str = Field("管理员手动赠送", description="赠送原因", max_length=200)
