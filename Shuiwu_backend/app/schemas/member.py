"""
会员订阅相关的 Pydantic 模型
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime


# ==================== 权益描述模型 ====================

class BenefitItem(BaseModel):
    """权益描述项"""
    title: str = Field(..., description="权益标题")
    desc: str = Field(..., description="权益描述")

    model_config = ConfigDict(from_attributes=True)


# ==================== 会员套餐 ====================

class MemberPackageCreate(BaseModel):
    """创建会员套餐"""
    package_id: str
    name: str
    description: Optional[str] = None
    package_type: str  # month, quarter, year, lifetime
    price: float
    original_price: Optional[float] = None
    duration_days: Optional[int] = None
    # 权益配置
    max_daily_chats: Optional[int] = -1
    max_kb_count: Optional[int] = 5
    max_kb_documents: Optional[int] = 100
    max_file_storage_mb: Optional[int] = 1024
    max_file_count: Optional[int] = 100
    enable_rag: Optional[bool] = True
    enable_web_search: Optional[bool] = False
    enable_mcp_tools: Optional[bool] = False
    sort_order: Optional[int] = 0
    # 扩展字段
    custom_config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="自定义配置（JSON格式）")
    benefits: Optional[List[BenefitItem]] = Field(default_factory=list, description="权益描述列表")


class MemberPackageUpdate(BaseModel):
    """更新会员套餐"""
    package_id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    package_type: Optional[str] = None  # month, quarter, year, lifetime
    price: Optional[float] = None
    original_price: Optional[float] = None
    duration_days: Optional[int] = None
    # 权益配置
    max_daily_chats: Optional[int] = None
    max_kb_count: Optional[int] = None
    max_kb_documents: Optional[int] = None
    max_file_storage_mb: Optional[int] = None
    max_file_count: Optional[int] = None
    enable_rag: Optional[bool] = False
    enable_web_search: Optional[bool] = False
    enable_mcp_tools: Optional[bool] = False
    status: Optional[str] = None
    sort_order: Optional[int] = None
    # 扩展字段
    custom_config: Optional[Dict[str, Any]] = Field(default=None, description="自定义配置（JSON格式）")
    benefits: Optional[List[BenefitItem]] = Field(default=None, description="权益描述列表")


class MemberPackageResponse(BaseModel):
    """会员套餐响应"""
    package_id: str
    name: str
    description: Optional[str] = None
    package_type: str
    price: float
    original_price: Optional[float] = None
    duration_days: Optional[int] = None
    max_daily_chats: int
    max_kb_count: int
    max_kb_documents: int
    max_file_storage_mb: int
    max_file_count: int
    enable_rag: bool
    enable_web_search: bool
    enable_mcp_tools: bool
    status: str
    sort_order: int
    custom_config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="自定义配置（JSON格式）")
    benefits: Optional[List[BenefitItem]] = Field(default_factory=list, description="权益描述列表")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MemberPackageListResponse(BaseModel):
    """会员套餐列表响应"""
    packages: List[MemberPackageResponse]


# ==================== 订单管理 ====================

class OrderCreate(BaseModel):
    """创建订单"""
    user_id: Optional[str] = None  # 可选，如果未提供则从当前用户获取
    package_id: str
    order_type: str = "subscription"  # subscription, renewal, upgrade
    payment_method: str = "wechat"  # wechat, alipay, balance


class OrderUpdate(BaseModel):
    """更新订单"""
    payment_status: Optional[str] = None  # paid, failed, refunded
    status: Optional[str] = None  # cancelled


class OrderResponse(BaseModel):
    """订单响应"""
    order_id: str
    user_id: str
    package_id: str
    order_type: str
    amount: float
    actual_amount: Optional[float] = None
    payment_method: str
    payment_status: str
    payment_time: Optional[datetime] = None
    transaction_id: Optional[str] = None
    package_name: Optional[str] = None
    duration_days: Optional[int] = None
    original_expire_at: Optional[datetime] = None
    new_expire_at: Optional[datetime] = None
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class OrderListResponse(BaseModel):
    """订单列表响应"""
    total: int
    page: int
    page_size: int
    orders: List[OrderResponse]


class OrderQueryParams(BaseModel):
    """订单查询参数"""
    user_id: Optional[str] = None
    payment_status: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    page: int = 1
    page_size: int = 20


# ==================== 会员权益使用 ====================

class MemberUsageResponse(BaseModel):
    """会员权益使用响应"""
    user_id: str
    usage_type: str
    usage_amount: int
    usage_date: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MemberUsageStatsResponse(BaseModel):
    """会员使用统计响应"""
    user_id: str
    member_level: str
    member_expire_at: Optional[datetime] = None
    # 今日使用情况
    today_chats: int
    max_daily_chats: int
    # 知识库
    kb_count: int
    max_kb_count: int
    kb_documents_count: int
    max_kb_documents: int
    # 文件存储
    used_storage_mb: float
    max_file_storage_mb: int
    file_count: int
    max_file_count: int
    # 权益
    enable_rag: bool
    enable_web_search: bool
    enable_mcp_tools: bool
