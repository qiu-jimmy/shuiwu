"""
管理员系统路由
处理管理员登录、用户管理、系统统计等接口
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Query

from app.schemas.admin import (
    AdminLoginRequest,
    AdminLoginResponse,
    AdminInfo,
    UserQueryParams,
    UserManageResponse,
    UserListManageResponse,
    UserCreateRequest,
    UserStatusUpdateRequest,
    UserTypeUpdateRequest,
    UserMemberInfoUpdateRequest,
    MemberPackageManageRequest,
    OrderQueryParams,
    KnowledgeBaseManageResponse,
    KnowledgeBaseListManageResponse,
    DistributorManageResponse,
    DistributorListManageResponse,
    WithdrawalHandleRequest,
    SystemStatsResponse,
)
from app.services.admin.admin_service import admin_service
from app.utils.dependencies import require_current_admin
from app.utils.response import response

router = APIRouter(prefix="/api/admin", tags=["管理系统"])


# ============================================================================
# 管理员认证
# ============================================================================


@router.post(
    "/login",
    summary="管理员登录",
    description="""
    管理员登录接口,支持使用用户名或手机号登录。

    **登录方式:**
    - 用户名登录：使用 username 字段
    - 手机号登录：使用 phone 字段（当 username 不存在时）

    **默认账户:**
    - 用户名: admin (如果存在)
    - 手机号: 138xxxx (如果配置)
    - 密码: admin123

    **返回信息:**
    - access_token: JWT访问令牌
    - token_type: 令牌类型(bearer)
    - expires_in: 过期时间(秒)
    - admin_info: 管理员基本信息

    **注意:**
    - 管理员必须是 users 表中的用户，且在 user_roles 表中有 admin 或 super_admin 角色
    - 生产环境请修改默认密码
    """,
    responses={
        200: {
            "description": "登录成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "登录成功",
                        "data": {
                            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "token_type": "bearer",
                            "expires_in": 604800,
                            "admin_info": {
                                "admin_id": "admin_001",
                                "username": "admin",
                                "nickname": "系统管理员",
                                "role": "super_admin",
                                "permissions": [
                                    "user.manage", "user.view",
                                    "member.manage", "member.view",
                                    "knowledge.manage", "knowledge.view",
                                    "mcp.manage", "mcp.view",
                                    "distribution.manage", "distribution.view",
                                    "order.view", "order.manage",
                                    "system.manage", "system.view",
                                    "log.view"
                                ]
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "登录失败",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "用户名或密码错误",
                        "data": None
                    }
                }
            }
        }
    }
)
async def admin_login(request: AdminLoginRequest) -> Dict[str, Any]:
    """管理员登录"""
    result = admin_service.login(request.username, request.password)

    if not result["success"]:
        error_msg = result.get("error", "登录失败")
        return response.fail(message=error_msg)

    # 转换admin_info为dict
    admin_info = result["admin_info"]
    if hasattr(admin_info, 'model_dump'):
        admin_info_dict = admin_info.model_dump()
    else:
        admin_info_dict = admin_info

    result["admin_info"] = admin_info_dict
    return response.success(data=result, message="登录成功")


@router.get(
    "/me",
    summary="获取当前管理员信息",
    description="""
    获取当前登录管理员的详细信息。

    **认证要求:** 需要在请求头中提供有效的管理员Bearer Token
    """,
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "操作成功",
                        "data": {
                            "admin_id": "admin_001",
                            "username": "admin",
                            "nickname": "系统管理员",
                            "role": "super_admin",
                            "permissions": ["user.manage", "user.view", "..."]
                        }
                    }
                }
            }
        }
    }
)
async def get_current_admin(
    admin_info: dict = Depends(require_current_admin)
) -> Dict[str, Any]:
    """获取当前管理员信息"""
    return response.success(data=admin_info)


# ============================================================================
# 用户管理
# ============================================================================


@router.post(
    "/users",
    summary="管理员创建用户",
    description="""
    管理员创建新用户。

    **认证要求:** 管理员权限

    **功能说明:**
    - 创建指定手机号的用户
    - 可设置昵称、状态、用户类型、会员等级
    - 密码可选，不填则默认为 123456

    **参数说明:**
    - phone: 手机号（必填）
    - nickname: 昵称（可选）
    - password: 密码（可选，默认123456）
    - status: 用户状态（normal/disabled/banned，默认normal）
    - user_type: 用户类型（individual/enterprise/admin，默认individual）
    - member_level: 会员等级（free/basic/premium/enterprise，默认free）
    - member_expire_at: 会员到期时间（可选）
    """,
    responses={
        200: {
            "description": "创建成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "用户创建成功",
                        "data": {
                            "user_id": "user_1234567890",
                            "initial_password": "123456"
                        }
                    }
                }
            }
        },
        400: {
            "description": "创建失败",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "该手机号已被注册",
                        "data": None
                    }
                }
            }
        }
    }
)
async def create_user(
    request: UserCreateRequest,
    admin_info: dict = Depends(require_current_admin)
) -> Dict[str, Any]:
    """管理员创建用户"""
    result = admin_service.create_user(
        phone=request.phone,
        nickname=request.nickname,
        password=request.password,
        status=request.status,
        user_type=request.user_type,
        member_level=request.member_level,
        member_expire_at=request.member_expire_at
    )

    if not result["success"]:
        return response.fail(message=result.get("error", "创建用户失败"))

    return response.success(
        data={
            "user_id": result.get("user_id"),
            "initial_password": result.get("initial_password")
        },
        message=result.get("message", "用户创建成功")
    )


@router.get(
    "/users",
    summary="获取用户列表",
    description="""
    获取系统中的用户列表,支持多种筛选条件。

    **认证要求:** 管理员权限

    **查询参数:**
    - keyword: 搜索关键词(手机号、昵称、用户ID)
    - status: 用户状态(normal, disabled, banned)
    - user_type: 用户类型(individual, enterprise, admin)
    - member_level: 会员等级(free, basic, premium, enterprise)
    - start_date: 注册开始日期(YYYY-MM-DD)
    - end_date: 注册结束日期(YYYY-MM-DD)
    - page: 页码(默认1)
    - page_size: 每页数量(默认20,最大100)

    **返回信息:**
    - 用户列表及分页信息
    """,
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "操作成功",
                        "data": {
                            "total": 100,
                            "page": 1,
                            "page_size": 20,
                            "users": [
                                {
                                    "user_id": "user_1234567890",
                                    "phone": "13800138000",
                                    "nickname": "测试用户",
                                    "status": "normal",
                                    "user_type": "individual",
                                    "member_level": "premium",
                                    "register_time": "2024-01-01T00:00:00"
                                }
                            ]
                        }
                    }
                }
            }
        }
    }
)
async def get_users(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    status: Optional[str] = Query(None, description="用户状态"),
    user_type: Optional[str] = Query(None, description="用户类型"),
    member_level: Optional[str] = Query(None, description="会员等级"),
    start_date: Optional[str] = Query(None, description="注册开始日期"),
    end_date: Optional[str] = Query(None, description="注册结束日期"),
    page: int = Query(1, description="页码", ge=1),
    page_size: int = Query(20, description="每页数量", ge=1, le=100),
    admin_info: dict = Depends(require_current_admin)
) -> Dict[str, Any]:
    """获取用户列表"""
    result = admin_service.get_users(
        keyword=keyword,
        status=status,
        user_type=user_type,
        member_level=member_level,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size
    )

    if not result["success"]:
        return response.fail(message=result.get("error", "获取用户列表失败"))

    return response.success(data=result)


@router.put(
    "/users/{user_id}/status",
    summary="更新用户状态",
    description="""
    更新指定用户的状态。

    **认证要求:** 管理员权限

    **状态说明:**
    - normal: 正常
    - disabled: 禁用
    - banned: 封禁
    """,
    responses={
        200: {
            "description": "更新成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "用户状态已更新为: disabled",
                        "data": None
                    }
                }
            }
        }
    }
)
async def update_user_status(
    user_id: str,
    request: UserStatusUpdateRequest,
    admin_info: dict = Depends(require_current_admin)
) -> Dict[str, Any]:
    """更新用户状态"""
    result = admin_service.update_user_status(
        user_id=user_id,
        status=request.status,
        reason=request.reason
    )

    if not result["success"]:
        return response.fail(message=result.get("error", "更新用户状态失败"))

    return response.success(message=result.get("message", "用户状态已更新"))


@router.put(
    "/users/{user_id}/type",
    summary="更新用户类型",
    description="""
    更新指定用户的类型。

    **认证要求:** 管理员权限

    **类型说明:**
    - individual: 个人用户
    - enterprise: 企业用户
    - admin: 管理员
    """,
    responses={
        200: {
            "description": "更新成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "用户类型已更新为: enterprise",
                        "data": None
                    }
                }
            }
        }
    }
)
async def update_user_type(
    user_id: str,
    request: UserTypeUpdateRequest,
    admin_info: dict = Depends(require_current_admin)
) -> Dict[str, Any]:
    """更新用户类型"""
    result = admin_service.update_user_type(user_id, request.user_type)

    if not result["success"]:
        return response.fail(message=result.get("error", "更新用户类型失败"))

    return response.success(message=result.get("message", "用户类型已更新"))


@router.put(
    "/users/{user_id}/member",
    summary="更新用户会员信息",
    description="""
    更新指定用户的会员信息(管理员特权功能)。

    **认证要求:** 管理员权限

    **功能说明:**
    - 手动设置用户的会员等级
    - 手动设置会员到期时间
    - 用于特殊情况下的会员调整
    """,
    responses={
        200: {
            "description": "更新成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "会员信息已更新",
                        "data": None
                    }
                }
            }
        }
    }
)
async def update_user_member(
    user_id: str,
    request: UserMemberInfoUpdateRequest,
    admin_info: dict = Depends(require_current_admin)
) -> Dict[str, Any]:
    """更新用户会员信息"""
    result = admin_service.update_user_member(
        user_id=user_id,
        member_level=request.member_level,
        member_expire_at=request.member_expire_at
    )

    if not result["success"]:
        return response.fail(message=result.get("error", "更新会员信息失败"))

    return response.success(message=result.get("message", "会员信息已更新"))


# ============================================================================
# 订单管理
# ============================================================================


@router.get(
    "/orders",
    summary="获取订单列表",
    description="""
    获取系统中所有订单列表,支持多种筛选条件。

    **认证要求:** 管理员权限

    **查询参数:**
    - keyword: 搜索关键词(订单号、用户ID)
    - payment_status: 支付状态(unpaid, paid, refunded)
    - status: 订单状态(pending, completed, cancelled, failed)
    - start_date: 开始日期(YYYY-MM-DD)
    - end_date: 结束日期(YYYY-MM-DD)
    - page: 页码(默认1)
    - page_size: 每页数量(默认20,最大100)
    """,
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "操作成功",
                        "data": {
                            "total": 50,
                            "page": 1,
                            "page_size": 20,
                            "orders": []
                        }
                    }
                }
            }
        }
    }
)
async def get_all_orders(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    payment_status: Optional[str] = Query(None, description="支付状态"),
    status: Optional[str] = Query(None, description="订单状态"),
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    page: int = Query(1, description="页码", ge=1),
    page_size: int = Query(20, description="每页数量", ge=1, le=100),
    admin_info: dict = Depends(require_current_admin)
) -> Dict[str, Any]:
    """获取订单列表"""
    result = admin_service.get_all_orders(
        keyword=keyword,
        payment_status=payment_status,
        status=status,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size
    )

    if not result["success"]:
        return response.fail(message=result.get("error", "获取订单列表失败"))

    return response.success(data=result)


@router.get(
    "/orders/{order_id}",
    summary="获取订单详情",
    description="""
    获取指定订单的详细信息。

    **认证要求:** 管理员权限

    **返回信息包括:**
    - 订单基本信息(订单号、金额、状态等)
    - 用户信息(用户ID、昵称、手机号)
    - 商品信息(套餐名称、描述)
    - 支付信息(支付状态、支付时间、支付方式)
    - 会员信息(会员等级、到期时间)

    **路径参数:**
    - order_id: 订单ID
    """,
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "操作成功",
                        "data": {
                            "id": 1,
                            "order_no": "ORD2026012000001",
                            "user_id": "user_123456",
                            "username": "张三",
                            "phone": "13800138000",
                            "package_id": "premium",
                            "package_name": "高级会员套餐",
                            "amount": 299.00,
                            "payment_status": "paid",
                            "status": "completed",
                            "payment_time": "2026-01-20T10:30:00",
                            "created_at": "2026-01-20T10:00:00"
                        }
                    }
                }
            }
        },
        404: {
            "description": "订单不存在",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "订单不存在",
                        "data": None
                    }
                }
            }
        }
    }
)
async def get_order_detail(
    order_id: int,
    admin_info: dict = Depends(require_current_admin)
) -> Dict[str, Any]:
    """获取订单详情"""
    result = admin_service.get_order_detail(order_id)

    if not result["success"]:
        return response.fail(message=result.get("error", "获取订单详情失败"))

    return response.success(data=result)


@router.put(
    "/orders/{order_id}/status",
    summary="更新订单状态",
    description="""
    更新订单的状态。

    **认证要求:** 管理员权限

    **路径参数:**
    - order_id: 订单ID

    **查询参数:**
    - status: 新状态

    **状态说明:**
    - pending: 待处理
    - completed: 已完成
    - cancelled: 已取消
    - failed: 失败
    """,
    responses={
        200: {
            "description": "更新成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "订单状态已更新",
                        "data": None
                    }
                }
            }
        },
        404: {
            "description": "订单不存在",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "订单不存在",
                        "data": None
                    }
                }
            }
        }
    }
)
async def update_order_status(
    order_no: str,
    status: str = Query(..., description="订单状态: pending/completed/cancelled/failed"),
    admin_info: dict = Depends(require_current_admin)
) -> Dict[str, Any]:
    """更新订单状态（通过订单号）"""
    result = admin_service.update_order_status_by_no(order_no, status)

    if not result["success"]:
        return response.fail(message=result.get("error", "更新订单状态失败"))

    return response.success(message=result.get("message", "订单状态已更新"))


@router.put(
    "/orders/by-id/{order_id}/status",
    summary="更新订单状态（通过订单ID）",
    description="""
    通过订单ID更新订单的状态。

    **认证要求:** 管理员权限

    **路径参数:**
    - order_id: 订单ID（整数）

    **查询参数:**
    - status: 新状态
    """,
    responses={
        200: {
            "description": "更新成功"
        }
    }
)
async def update_order_status_by_id(
    order_id: int,
    status: str = Query(..., description="订单状态: pending/completed/cancelled/failed"),
    admin_info: dict = Depends(require_current_admin)
) -> Dict[str, Any]:
    """更新订单状态（通过订单ID）"""
    result = admin_service.update_order_status(order_id, status)

    if not result["success"]:
        return response.fail(message=result.get("error", "更新订单状态失败"))

    return response.success(message=result.get("message", "订单状态已更新"))


@router.put(
    "/orders/{order_no}/payment-status",
    summary="更新订单支付状态",
    description="""
    更新订单的支付状态（通过订单号）。

    **认证要求:** 管理员权限

    **路径参数:**
    - order_no: 订单号（字符串）

    **查询参数:**
    - payment_status: 新支付状态

    **支付状态说明:**
    - unpaid: 未支付
    - paid: 已支付
    - refunded: 已退款
    """,
    responses={
        200: {
            "description": "更新成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "支付状态已更新",
                        "data": None
                    }
                }
            }
        },
        404: {
            "description": "订单不存在",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "订单不存在",
                        "data": None
                    }
                }
            }
        }
    }
)
async def update_order_payment_status(
    order_no: str,
    payment_status: str = Query(..., description="支付状态: unpaid/paid/refunded"),
    admin_info: dict = Depends(require_current_admin)
) -> Dict[str, Any]:
    """更新订单支付状态（通过订单号）"""
    result = admin_service.update_order_payment_status_by_no(order_no, payment_status)

    if not result["success"]:
        return response.fail(message=result.get("error", "更新支付状态失败"))

    return response.success(message=result.get("message", "支付状态已更新"))


@router.put(
    "/orders/by-id/{order_id}/payment-status",
    summary="更新订单支付状态（通过订单ID）",
    description="""
    通过订单ID更新订单的支付状态。

    **认证要求:** 管理员权限

    **路径参数:**
    - order_id: 订单ID（整数）

    **查询参数:**
    - payment_status: 新支付状态
    """,
    responses={
        200: {
            "description": "更新成功"
        }
    }
)
async def update_order_payment_status_by_id(
    order_id: int,
    payment_status: str = Query(..., description="支付状态: unpaid/paid/refunded"),
    admin_info: dict = Depends(require_current_admin)
) -> Dict[str, Any]:
    """更新订单支付状态（通过订单ID）"""
    result = admin_service.update_order_payment_status(order_id, payment_status)

    if not result["success"]:
        return response.fail(message=result.get("error", "更新支付状态失败"))

    return response.success(message=result.get("message", "支付状态已更新"))


# ============================================================================
# 知识库管理
# ============================================================================


@router.get(
    "/knowledge-bases",
    summary="获取知识库列表",
    description="""
    获取系统中所有知识库列表。

    **认证要求:** 管理员权限

    **查询参数:**
    - keyword: 搜索关键词
    - is_system: 是否为系统知识库
    - page: 页码
    - page_size: 每页数量
    """,
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "操作成功",
                        "data": {
                            "total": 50,
                            "page": 1,
                            "page_size": 20,
                            "knowledge_bases": []
                        }
                    }
                }
            }
        }
    }
)
async def get_all_knowledge_bases(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    is_system: Optional[bool] = Query(None, description="是否为系统知识库"),
    page: int = Query(1, description="页码", ge=1),
    page_size: int = Query(20, description="每页数量", ge=1, le=100),
    admin_info: dict = Depends(require_current_admin)
) -> Dict[str, Any]:
    """获取知识库列表"""
    result = admin_service.get_all_knowledge_bases(
        keyword=keyword,
        is_system=is_system,
        page=page,
        page_size=page_size
    )

    if not result["success"]:
        return response.fail(message=result.get("error", "获取知识库列表失败"))

    return response.success(data=result)


# ============================================================================
# 分销管理
# ============================================================================


@router.get(
    "/distributors",
    summary="获取分销商列表",
    description="""
    获取系统中所有分销商列表。

    **认证要求:** 管理员权限

    **查询参数:**
    - status: 状态
    - page: 页码
    - page_size: 每页数量
    """,
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "操作成功",
                        "data": {
                            "total": 30,
                            "page": 1,
                            "page_size": 20,
                            "distributors": []
                        }
                    }
                }
            }
        }
    }
)
async def get_all_distributors(
    status: Optional[str] = Query(None, description="状态"),
    page: int = Query(1, description="页码", ge=1),
    page_size: int = Query(20, description="每页数量", ge=1, le=100),
    admin_info: dict = Depends(require_current_admin)
) -> Dict[str, Any]:
    """获取分销商列表"""
    result = admin_service.get_all_distributors(
        status=status,
        page=page,
        page_size=page_size
    )

    if not result["success"]:
        return response.fail(message=result.get("error", "获取分销商列表失败"))

    return response.success(data=result)


@router.put(
    "/withdrawals/{withdrawal_id}/handle",
    summary="处理提现申请",
    description="""
    处理分销商的提现申请。

    **认证要求:** 管理员权限

    **处理结果:**
    - approved: 通过
    - rejected: 拒绝
    """,
    responses={
        200: {
            "description": "处理成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "提现申请已处理",
                        "data": None
                    }
                }
            }
        }
    }
)
async def handle_withdrawal(
    withdrawal_id: str,
    request: WithdrawalHandleRequest,
    admin_info: dict = Depends(require_current_admin)
) -> Dict[str, Any]:
    """处理提现申请"""
    result = admin_service.handle_withdrawal(
        withdrawal_id=withdrawal_id,
        status=request.status,
        handle_result=request.handle_result,
        transaction_id=request.transaction_id
    )

    if not result["success"]:
        return response.fail(message=result.get("error", "处理提现申请失败"))

    return response.success(message=result.get("message", "提现申请已处理"))


# ============================================================================
# 系统统计
# ============================================================================


@router.get(
    "/stats",
    summary="获取系统统计",
    description="""
    获取系统整体统计数据。

    **认证要求:** 管理员权限

    **统计内容:**
    - 总用户数、会员数
    - 总知识库数、订单数
    - 总收入、今日数据
    - 活跃分销商数
    """,
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "操作成功",
                        "data": {
                            "total_users": 1000,
                            "total_members": 150,
                            "total_knowledge_bases": 200,
                            "total_orders": 500,
                            "total_revenue": 50000.0,
                            "today_new_users": 20,
                            "today_new_orders": 15,
                            "today_revenue": 1500.0,
                            "active_distributors": 30
                        }
                    }
                }
            }
        }
    }
)
async def get_system_stats(
    admin_info: dict = Depends(require_current_admin)
) -> Dict[str, Any]:
    """获取系统统计"""
    result = admin_service.get_system_stats()

    if not result["success"]:
        return response.fail(message=result.get("error", "获取系统统计失败"))

    return response.success(data=result)


# ============================================================================
# 税务师管理
# ============================================================================


from app.schemas.tax_accountant import (
    TaxAccountantApplicationListResponse,
    TaxAccountantReviewRequest,
    TaxAccountantListResponse,
    TaxAccountantUpdateRequest,
    TaxAccountantStatsResponse,
)
from app.services.tax_accountant.tax_accountant_service import tax_accountant_service
from pydantic import BaseModel


class TaxAccountantReviewRequestModel(BaseModel):
    """税务师审核请求模型"""
    application_id: str
    action: str  # approve-通过, reject-拒绝
    reject_reason: Optional[str] = None


class TaxAccountantUpdateRequestModel(BaseModel):
    """税务师更新请求模型"""
    status: Optional[str] = None
    specialty_area: Optional[list] = None
    introduction: Optional[str] = None


@router.get(
    "/tax-accountant/applications",
    summary="获取税务师申请列表",
    description="""
    获取税务师入驻申请列表（仅管理员）。

    **认证要求:** 管理员权限

    **查询参数:**
    - status: 申请状态筛选（pending-待审核, approved-已通过, rejected-已拒绝）
    - keyword: 搜索关键词（姓名、手机号、证书编号）
    - page: 页码
    - page_size: 每页数量

    **排序方式:** 按申请时间倒序
    """,
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "操作成功",
                        "data": {
                            "total": 50,
                            "page": 1,
                            "page_size": 20,
                            "applications": []
                        }
                    }
                }
            }
        }
    }
)
async def get_tax_accountant_applications(
    status: Optional[str] = Query(None, description="申请状态"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, description="页码", ge=1),
    page_size: int = Query(20, description="每页数量", ge=1, le=100),
    admin_info: dict = Depends(require_current_admin)
) -> Dict[str, Any]:
    """获取税务师申请列表"""
    result = tax_accountant_service.get_application_list(
        page=page,
        page_size=page_size,
        status=status,
        keyword=keyword
    )

    return response.success(data=result)


@router.get(
    "/tax-accountant/applications/{application_id}",
    summary="获取税务师申请详情",
    description="""
    获取指定税务师申请的详细信息（仅管理员）。

    **认证要求:** 管理员权限

    **返回内容:**
    - 申请基本信息
    - 申请人信息
    - 证书信息
    """,
    responses={
        200: {
            "description": "获取成功"
        },
        404: {
            "description": "申请不存在"
        }
    }
)
async def get_tax_accountant_application_detail(
    application_id: str,
    admin_info: dict = Depends(require_current_admin)
) -> Dict[str, Any]:
    """获取税务师申请详情"""
    result = tax_accountant_service.get_application_detail(application_id)

    if result:
        return response.success(data=result)
    return response.fail(message="申请不存在")


@router.post(
    "/tax-accountant/review",
    summary="审核税务师申请",
    description="""
    审核税务师入驻申请（仅管理员）。

    **认证要求:** 管理员权限

    **审核操作:**
    - approve: 通过审核，自动创建税务师档案
    - reject: 拒绝申请，需要填写拒绝原因

    **业务流程:**
    - 审核通过：申请状态更新为approved，同时创建tax_accountants记录
    - 审核拒绝：申请状态更新为rejected，记录拒绝原因
    """,
    responses={
        200: {
            "description": "审核成功",
            "content": {
                "application/json": {
                    "examples": {
                        "approved": {
                            "summary": "审核通过",
                            "value": {
                                "code": 1,
                                "message": "审核通过，税务师已入驻",
                                "data": {
                                    "accountant_id": "tac_1234567890"
                                }
                            }
                        },
                        "rejected": {
                            "summary": "审核拒绝",
                            "value": {
                                "code": 1,
                                "message": "已拒绝该申请",
                                "data": None
                            }
                        }
                    }
                }
            }
        },
        400: {
            "description": "审核失败"
        }
    }
)
async def review_tax_accountant_application(
    request: TaxAccountantReviewRequestModel,
    admin_info: dict = Depends(require_current_admin)
) -> Dict[str, Any]:
    """审核税务师申请"""
    result = tax_accountant_service.review_application(
        application_id=request.application_id,
        action=request.action,
        reviewed_by=admin_info["user_id"],
        reject_reason=request.reject_reason
    )

    if result.get("success"):
        return response.success(
            data={"accountant_id": result.get("accountant_id")} if result.get("accountant_id") else None,
            message=result.get("message")
        )
    return response.fail(message=result.get("message"))


@router.get(
    "/tax-accountant/list",
    summary="获取税务师列表",
    description="""
    获取税务师列表（仅管理员）。

    **认证要求:** 管理员权限

    **查询参数:**
    - status: 状态筛选（active-正常, suspended-暂停）
    - keyword: 搜索关键词（姓名、手机号）
    - page: 页码
    - page_size: 每页数量
    """,
    responses={
        200: {
            "description": "获取成功"
        }
    }
)
async def get_tax_accountants_list(
    status: Optional[str] = Query(None, description="状态筛选"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, description="页码", ge=1),
    page_size: int = Query(20, description="每页数量", ge=1, le=100),
    admin_info: dict = Depends(require_current_admin)
) -> Dict[str, Any]:
    """获取税务师列表"""
    result = tax_accountant_service.get_accountant_list(
        page=page,
        page_size=page_size,
        status=status,
        keyword=keyword
    )

    return response.success(data=result)


@router.get(
    "/tax-accountant/stats",
    summary="获取税务师统计",
    description="""
    获取税务师模块统计数据（仅管理员）。

    **认证要求:** 管理员权限

    **统计内容:**
    - total_applications: 总申请数
    - pending_count: 待审核数
    - approved_count: 已通过数
    - rejected_count: 已拒绝数
    - active_accountants: 活跃税务师数
    """,
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "操作成功",
                        "data": {
                            "total_applications": 100,
                            "pending_count": 10,
                            "approved_count": 80,
                            "rejected_count": 10,
                            "active_accountants": 75
                        }
                    }
                }
            }
        }
    }
)
async def get_tax_accountant_stats(
    admin_info: dict = Depends(require_current_admin)
) -> Dict[str, Any]:
    """获取税务师统计"""
    result = tax_accountant_service.get_statistics()
    return response.success(data=result)


@router.get(
    "/tax-accountant/{accountant_id}",
    summary="获取税务师详情",
    description="""
    获取指定税务师的详细信息（仅管理员）。

    **认证要求:** 管理员权限
    """,
    responses={
        200: {
            "description": "获取成功"
        },
        404: {
            "description": "税务师不存在"
        }
    }
)
async def get_tax_accountant_detail_admin(
    accountant_id: str,
    admin_info: dict = Depends(require_current_admin)
) -> Dict[str, Any]:
    """获取税务师详情"""
    result = tax_accountant_service.get_accountant_detail(accountant_id)

    if result:
        return response.success(data=result)
    return response.fail(message="税务师不存在")


@router.put(
    "/tax-accountant/{accountant_id}",
    summary="更新税务师信息",
    description="""
    更新税务师信息（仅管理员）。

    **认证要求:** 管理员权限

    **可更新字段:**
    - status: 状态（active-正常, suspended-暂停）
    - specialty_area: 专长领域
    - introduction: 个人简介
    """,
    responses={
        200: {
            "description": "更新成功"
        },
        404: {
            "description": "税务师不存在"
        }
    }
)
async def update_tax_accountant(
    accountant_id: str,
    request: TaxAccountantUpdateRequestModel,
    admin_info: dict = Depends(require_current_admin)
) -> Dict[str, Any]:
    """更新税务师信息"""
    result = tax_accountant_service.update_accountant(
        accountant_id=accountant_id,
        status=request.status,
        specialty_area=request.specialty_area,
        introduction=request.introduction
    )

    if result.get("success"):
        return response.success(message=result.get("message"))
    return response.fail(message=result.get("message"))


@router.delete(
    "/tax-accountant/{accountant_id}",
    summary="删除税务师",
    description="""
    删除税务师（暂停服务）（仅管理员）。

    **认证要求:** 管理员权限

    **注意:** 此操作会将税务师状态设为suspended，而非物理删除
    """,
    responses={
        200: {
            "description": "删除成功"
        },
        404: {
            "description": "税务师不存在"
        }
    }
)
async def delete_tax_accountant(
    accountant_id: str,
    admin_info: dict = Depends(require_current_admin)
) -> Dict[str, Any]:
    """删除税务师（暂停服务）"""
    result = tax_accountant_service.delete_accountant(accountant_id)

    if result.get("success"):
        return response.success(message=result.get("message"))
    return response.fail(message=result.get("message"))
