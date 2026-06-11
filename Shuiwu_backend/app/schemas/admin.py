"""
管理系统相关的 Pydantic 模型
包含管理员登录、用户管理、系统统计等功能
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


# ==================== 管理员认证 ====================

class AdminLoginRequest(BaseModel):
    """管理员登录请求"""
    username: str = Field(..., description="管理员用户名", examples=["admin"])
    password: str = Field(..., description="管理员密码", examples=["admin123"])


class AdminLoginResponse(BaseModel):
    """管理员登录响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    admin_info: "AdminInfo"


class AdminInfo(BaseModel):
    """管理员基本信息"""
    admin_id: str
    username: str
    nickname: Optional[str] = None
    role: str
    permissions: List[str]
    created_at: Optional[datetime] = None
    last_login_time: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ==================== 用户管理 ====================

class UserQueryParams(BaseModel):
    """用户查询参数"""
    keyword: Optional[str] = Field(None, description="搜索关键词（手机号、昵称、用户ID）")
    status: Optional[str] = Field(None, description="用户状态（normal, disabled, banned）")
    user_type: Optional[str] = Field(None, description="用户类型（individual, enterprise, admin）")
    member_level: Optional[str] = Field(None, description="会员等级（free, basic, premium, enterprise）")
    start_date: Optional[str] = Field(None, description="注册开始日期（YYYY-MM-DD）")
    end_date: Optional[str] = Field(None, description="注册结束日期（YYYY-MM-DD）")
    page: int = Field(1, description="页码", ge=1)
    page_size: int = Field(20, description="每页数量", ge=1, le=100)


class UserManageResponse(BaseModel):
    """用户管理响应"""
    user_id: str
    phone: Optional[str] = None
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    status: str
    user_type: str
    member_level: str
    member_expire_at: Optional[datetime] = None
    register_time: Optional[datetime] = None
    last_login_time: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserListManageResponse(BaseModel):
    """用户列表响应"""
    total: int
    page: int
    page_size: int
    users: List[UserManageResponse]


class UserStatusUpdateRequest(BaseModel):
    """更新用户状态请求"""
    status: str = Field(..., description="用户状态（normal, disabled, banned）")
    reason: Optional[str] = Field(None, description="原因说明")


class UserCreateRequest(BaseModel):
    """管理员创建用户请求"""
    phone: str = Field(..., description="手机号", examples=["13800138000"])
    nickname: Optional[str] = Field(None, description="昵称")
    password: Optional[str] = Field(None, description="密码（不填则生成默认密码123456）")
    status: str = Field("normal", description="用户状态（normal, disabled, banned）")
    user_type: str = Field("individual", description="用户类型（individual, enterprise, admin）")
    member_level: str = Field("free", description="会员套餐ID（从 /api/member/packages 获取）")
    member_expire_at: Optional[datetime] = Field(None, description="会员到期时间")


class UserTypeUpdateRequest(BaseModel):
    """更新用户类型请求"""
    user_type: str = Field(..., description="用户类型（individual, enterprise, admin）")


# ==================== 会员管理 ====================

class MemberPackageManageRequest(BaseModel):
    """创建/更新会员套餐"""
    name: str = Field(..., description="套餐名称")
    description: Optional[str] = Field(None, description="套餐描述")
    package_type: str = Field(..., description="套餐类型（free, basic, premium, enterprise）")
    price: float = Field(..., description="价格", ge=0)
    original_price: Optional[float] = Field(None, description="原价", ge=0)
    duration_days: int = Field(..., description="有效期（天）", ge=1)
    max_daily_chats: int = Field(..., description="每日最大聊天次数", ge=0)
    max_kb_count: int = Field(..., description="最大知识库数量", ge=0)
    max_kb_documents: int = Field(..., description="最大文档数量", ge=0)
    max_file_storage_mb: int = Field(..., description="最大文件存储（MB）", ge=0)
    max_file_count: int = Field(..., description="最大文件数量", ge=0)
    enable_rag: bool = Field(False, description="是否启用RAG")
    enable_web_search: bool = Field(False, description="是否启用网络搜索")
    enable_mcp_tools: bool = Field(False, description="是否启用MCP工具")
    status: str = Field("active", description="套餐状态（active, inactive）")


class OrderQueryParams(BaseModel):
    """订单查询参数"""
    keyword: Optional[str] = Field(None, description="搜索关键词（订单号、用户ID）")
    payment_status: Optional[str] = Field(None, description="支付状态（unpaid, paid, refunded）")
    status: Optional[str] = Field(None, description="订单状态（pending, completed, cancelled, failed）")
    start_date: Optional[str] = Field(None, description="开始日期（YYYY-MM-DD）")
    end_date: Optional[str] = Field(None, description="结束日期（YYYY-MM-DD）")
    page: int = Field(1, description="页码", ge=1)
    page_size: int = Field(20, description="每页数量", ge=1, le=100)


class UserMemberInfoUpdateRequest(BaseModel):
    """更新用户会员信息请求"""
    member_level: str = Field(..., description="会员套餐ID（从 /api/member/packages 获取）")
    member_expire_at: Optional[datetime] = Field(None, description="会员到期时间")


# ==================== 知识库管理 ====================

class KnowledgeBaseManageResponse(BaseModel):
    """知识库管理响应"""
    kb_name: str
    user_id: str
    description: Optional[str] = None
    type_id: Optional[str] = None
    type_name: Optional[str] = None
    is_system: bool
    chunking_rule: Optional[str] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    embedder_model: Optional[str] = None
    document_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class KnowledgeBaseListManageResponse(BaseModel):
    """知识库列表响应"""
    total: int
    page: int
    page_size: int
    knowledge_bases: List[KnowledgeBaseManageResponse]


# ==================== MCP服务管理 ====================

class MCPServiceManageRequest(BaseModel):
    """创建/更新MCP服务"""
    service_id: str = Field(..., description="服务ID")
    service_name: str = Field(..., description="服务名称")
    description: Optional[str] = Field(None, description="服务描述")
    service_type: str = Field(..., description="服务类型（stdio, sse）")
    command: Optional[str] = Field(None, description="启动命令")
    args: Optional[List[str]] = Field(None, description="命令参数")
    env: Optional[Dict[str, str]] = Field(None, description="环境变量")
    url: Optional[str] = Field(None, description="服务URL")
    status: str = Field("active", description="服务状态（active, inactive）")


# ==================== 分销管理 ====================

class DistributorManageResponse(BaseModel):
    """分销商管理响应"""
    user_id: str
    distributor_code: str
    status: str
    total_commission: float
    available_commission: float
    total_orders: int
    total_referrals: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DistributorListManageResponse(BaseModel):
    """分销商列表响应"""
    total: int
    page: int
    page_size: int
    distributors: List[DistributorManageResponse]


class WithdrawalQueryParams(BaseModel):
    """提现查询参数"""
    status: Optional[str] = Field(None, description="状态（pending, approved, rejected, completed）")
    start_date: Optional[str] = Field(None, description="开始日期（YYYY-MM-DD）")
    end_date: Optional[str] = Field(None, description="结束日期（YYYY-MM-DD）")
    page: int = Field(1, description="页码", ge=1)
    page_size: int = Field(20, description="每页数量", ge=1, le=100)


class WithdrawalHandleRequest(BaseModel):
    """处理提现申请"""
    status: str = Field(..., description="处理状态（approved, rejected）")
    handle_result: Optional[str] = Field(None, description="处理结果说明")
    transaction_id: Optional[str] = Field(None, description="支付交易号（approved时需要）")


# ==================== 系统统计 ====================

class SystemStatsResponse(BaseModel):
    """系统统计响应"""
    total_users: int
    total_members: int
    total_knowledge_bases: int
    total_orders: int
    total_revenue: float
    today_new_users: int
    today_new_orders: int
    today_revenue: float
    active_distributors: int


class DashboardChartData(BaseModel):
    """仪表盘图表数据"""
    dates: List[str]
    values: List[float]


# ==================== 操作日志 ====================

class AdminActionLogCreate(BaseModel):
    """创建管理员操作日志"""
    action_type: str = Field(..., description="操作类型")
    action_module: str = Field(..., description="操作模块")
    action_detail: Optional[Dict[str, Any]] = Field(None, description="操作详情")
    target_user_id: Optional[str] = Field(None, description="目标用户ID")


class AdminActionLogResponse(BaseModel):
    """管理员操作日志响应"""
    id: int
    admin_id: str
    admin_name: str
    action_type: str
    action_module: str
    action_detail: Optional[Dict[str, Any]] = None
    target_user_id: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AdminActionLogListResponse(BaseModel):
    """管理员操作日志列表响应"""
    total: int
    page: int
    page_size: int
    logs: List[AdminActionLogResponse]
