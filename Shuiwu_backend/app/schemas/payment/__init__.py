"""
支付相关的 Pydantic 模型
"""
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


# ==================== 支付请求模型 ====================

class CreatePaymentRequest(BaseModel):
    """创建支付请求"""
    order_id: str = Field(..., description="订单ID")
    openid: str = Field(..., description="微信用户OpenID")


class PaymentNotifyRequest(BaseModel):
    """支付回调通知请求"""
    id: Optional[str] = None
    create_time: Optional[str] = None
    resource_type: Optional[str] = None
    event_type: Optional[str] = None
    resource: Optional[dict] = None


class QueryPaymentRequest(BaseModel):
    """查询支付状态请求"""
    order_id: str = Field(..., description="订单ID")


class CreateRefundRequest(BaseModel):
    """申请退款请求"""
    order_id: str = Field(..., description="订单ID")
    reason: Optional[str] = Field(None, description="退款原因")


class CloseOrderRequest(BaseModel):
    """关闭订单请求"""
    order_id: str = Field(..., description="订单ID")


# ==================== 支付响应模型 ====================

class CreatePaymentResponse(BaseModel):
    """创建支付响应"""
    prepay_id: str = Field(..., description="预支付交易会话标识")
    pay_params: dict = Field(..., description="小程序支付参数")


class PaymentStatusResponse(BaseModel):
    """支付状态响应"""
    order_id: str = Field(..., description="订单ID")
    trade_state: str = Field(..., description="交易状态")
    transaction_id: Optional[str] = Field(None, description="微信支付交易号")


class RefundResponse(BaseModel):
    """退款响应"""
    refund_id: str = Field(..., description="退款单号")
    status: str = Field(..., description="退款状态")


# ==================== 微信支付参数模型 ====================

class WechatPayParams(BaseModel):
    """微信支付参数（小程序）"""
    appId: str = Field(..., description="小程序AppID")
    timeStamp: str = Field(..., description="时间戳")
    nonceStr: str = Field(..., description="随机字符串")
    package: str = Field(..., description="支付参数")
    signType: str = Field(..., description="签名类型")
    paySign: str = Field(..., description="签名")


# 导出所有模型
__all__ = [
    "CreatePaymentRequest",
    "PaymentNotifyRequest",
    "QueryPaymentRequest",
    "CreateRefundRequest",
    "CloseOrderRequest",
    "CreatePaymentResponse",
    "PaymentStatusResponse",
    "RefundResponse",
    "WechatPayParams"
]
