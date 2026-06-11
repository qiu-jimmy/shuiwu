"""
会员订阅模块 - API路由
"""
from fastapi import APIRouter, Depends, Header, Body
from pydantic import BaseModel
from typing import Optional
from app.schemas.member import (
    MemberPackageCreate,
    MemberPackageUpdate,
    MemberPackageResponse,
    MemberPackageListResponse,
    OrderCreate,
    OrderUpdate,
    OrderResponse,
    OrderListResponse,
    OrderQueryParams,
    MemberUsageStatsResponse
)
from app.services.member.member_service import member_service
from app.utils.response import response
from app.utils.dependencies import get_current_user_info, require_current_admin

router = APIRouter(prefix="/api/member", tags=["会员订阅"])


class CompletePaymentRequest(BaseModel):
    """完成支付请求"""
    transaction_id: str


# ==================== 会员套餐管理（管理员） ====================

@router.post(
    "/packages",
    summary="创建会员套餐",
    description="""
    管理员创建新的会员套餐。

    **权限要求：** 管理员权限

    **创建流程：**
    1. 验证当前用户是否为管理员
    2. 验证套餐名称是否已存在
    3. 创建套餐并分配套餐ID
    4. 返回创建的套餐信息

    **套餐类型说明：**
    - free: 免费套餐
    - basic: 基础套餐
    - premium: 高级套餐
    - enterprise: 企业套餐

    **注意事项：**
    - 套餐名称必须唯一
    - 价格不能为负数
    - 有效期单位为天
    """,
    responses={
        200: {
            "description": "创建成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "创建套餐成功",
                        "data": {
                            "package_id": "pkg_premium_30days",
                            "name": "高级套餐-30天",
                            "description": "高级会员套餐，有效期30天",
                            "package_type": "premium",
                            "price": 29.9,
                            "original_price": 39.9,
                            "duration_days": 30,
                            "max_daily_chats": 100,
                            "max_kb_count": 10,
                            "max_kb_documents": 100,
                            "max_file_storage_mb": 1024,
                            "max_file_count": 50,
                            "enable_rag": True,
                            "enable_web_search": True,
                            "enable_mcp_tools": True,
                            "custom_config": {
                                "level": "premium",
                                "priority": 2,
                                "features": ["rag", "web_search", "ai_image"]
                            },
                            "benefits": [
                                {"title": "每日100次对话", "desc": "每天可使用100次AI智能对话"},
                                {"title": "10个知识库", "desc": "支持创建10个知识库进行分类管理"},
                                {"title": "RAG功能", "desc": "知识库检索增强生成，答案更精准"},
                                {"title": "网络搜索", "desc": "实时联网搜索，获取最新信息"}
                            ],
                            "status": "active",
                            "sort_order": 1,
                            "created_at": "2024-01-15T10:00:00"
                        }
                    }
                }
            }
        },
        400: {
            "description": "创建失败",
            "content": {
                "application/json": {
                    "examples": {
                        "package_exists": {
                            "summary": "套餐名称已存在",
                            "value": {
                                "code": 0,
                                "message": "套餐名称已存在",
                                "data": None
                            }
                        },
                        "invalid_price": {
                            "summary": "价格无效",
                            "value": {
                                "code": 0,
                                "message": "价格不能为负数",
                                "data": None
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "未授权",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "未提供认证token",
                        "data": None
                    }
                }
            }
        }
    }
)
async def create_package(
    package_data: MemberPackageCreate,
    admin_info: dict = Depends(require_current_admin)
):
    """创建会员套餐"""
    result = member_service.create_package(package_data.dict())

    if result.get("success"):
        return response.success(data=result.get("package"), message="创建套餐成功")
    return response.fail(message=result.get("error", "创建套餐失败"))


@router.get(
    "/packages",
    summary="获取套餐列表",
    description="""
    获取所有有效的会员套餐列表，支持按状态和类型筛选。

    **筛选参数：**
    - status: 套餐状态（active-启用, inactive-停用）
    - package_type: 套餐类型（free, basic, premium, enterprise）

    **返回信息：**
    - 套餐基本信息（名称、描述、价格）
    - 套餐权益（聊天次数、知识库数量、文件存储等）
    - 套餐状态和创建时间
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
                            "packages": [
                                {
                                    "package_id": "pkg_free",
                                    "name": "免费套餐",
                                    "description": "基础功能，每日有限次数",
                                    "package_type": "free",
                                    "price": 0,
                                    "original_price": 0,
                                    "duration_days": 365,
                                    "max_daily_chats": 10,
                                    "max_kb_count": 1,
                                    "max_kb_documents": 10,
                                    "max_file_storage_mb": 100,
                                    "max_file_count": 5,
                                    "enable_rag": False,
                                    "enable_web_search": False,
                                    "enable_mcp_tools": False,
                                    "custom_config": {},
                                    "benefits": [
                                        {"title": "每日10次对话", "desc": "每天可以免费使用10次AI对话"},
                                        {"title": "1个知识库", "desc": "支持创建1个个人知识库"},
                                        {"title": "10份文档", "desc": "最多可上传10份文档进行知识管理"},
                                        {"title": "100MB存储", "desc": "云端文件存储空间"}
                                    ],
                                    "status": "active",
                                    "sort_order": 0,
                                    "created_at": "2024-01-01T00:00:00"
                                },
                                {
                                    "package_id": "pkg_premium_30days",
                                    "name": "高级套餐-30天",
                                    "description": "高级会员套餐，有效期30天",
                                    "package_type": "premium",
                                    "price": 29.9,
                                    "original_price": 39.9,
                                    "duration_days": 30,
                                    "max_daily_chats": 100,
                                    "max_kb_count": 10,
                                    "max_kb_documents": 100,
                                    "max_file_storage_mb": 1024,
                                    "max_file_count": 50,
                                    "enable_rag": True,
                                    "enable_web_search": True,
                                    "enable_mcp_tools": True,
                                    "custom_config": {
                                        "level": "premium",
                                        "features": ["rag", "web_search"]
                                    },
                                    "benefits": [
                                        {"title": "每日100次对话", "desc": "每天可使用100次AI智能对话"},
                                        {"title": "10个知识库", "desc": "支持创建10个知识库进行分类管理"},
                                        {"title": "RAG功能", "desc": "知识库检索增强生成，答案更精准"}
                                    ],
                                    "status": "active",
                                    "sort_order": 1,
                                    "created_at": "2024-01-15T10:00:00"
                                }
                            ]
                        }
                    }
                }
            }
        }
    }
)
async def list_packages(
    status: Optional[str] = None,
    package_type: Optional[str] = None
):
    """获取套餐列表"""
    result = member_service.list_packages(status=status, package_type=package_type)

    if result.get("success"):
        return response.success(data={"packages": result.get("packages", [])})
    return response.fail(message=result.get("error", "获取套餐列表失败"))


@router.get(
    "/packages/{package_id}",
    summary="获取套餐详情",
    description="""
    根据套餐ID获取套餐详细信息。

    **路径参数：**
    - package_id: 套餐ID（如 pkg_premium_30days）

    **返回信息：**
    - 套餐完整配置信息
    - 所有权益限制和功能开关
    - 价格和有效期信息
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
                            "package_id": "pkg_premium_30days",
                            "name": "高级套餐-30天",
                            "description": "高级会员套餐，有效期30天",
                            "package_type": "premium",
                            "price": 29.9,
                            "original_price": 39.9,
                            "duration_days": 30,
                            "max_daily_chats": 100,
                            "max_kb_count": 10,
                            "max_kb_documents": 100,
                            "max_file_storage_mb": 1024,
                            "max_file_count": 50,
                            "enable_rag": True,
                            "enable_web_search": True,
                            "enable_mcp_tools": True,
                            "status": "active",
                            "created_at": "2024-01-15T10:00:00",
                            "updated_at": "2024-01-15T10:00:00"
                        }
                    }
                }
            }
        },
        404: {
            "description": "套餐不存在",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "套餐不存在",
                        "data": None
                    }
                }
            }
        }
    }
)
async def get_package(package_id: str):
    """获取套餐详情"""
    result = member_service.get_package(package_id)

    if result.get("success"):
        return response.success(data=result.get("package"))
    return response.fail(message=result.get("error", "获取套餐失败"))


@router.put(
    "/packages/{package_id}",
    summary="更新套餐",
    description="""
    管理员更新会员套餐信息。

    **权限要求：** 管理员权限

    **路径参数：**
    - package_id: 套餐ID

    **可更新字段：**
    - package_id: 套餐ID（通常不需要修改）
    - name: 套餐名称
    - description: 套餐描述
    - package_type: 套餐类型（month, quarter, year, lifetime）
    - price: 价格
    - original_price: 原价
    - duration_days: 有效期（天）
    - max_daily_chats: 每日最大聊天次数
    - max_kb_count: 最大知识库数量
    - max_kb_documents: 最大文档数量
    - max_file_storage_mb: 最大文件存储（MB）
    - max_file_count: 最大文件数量
    - enable_rag: 是否启用RAG
    - enable_web_search: 是否启用网络搜索
    - enable_mcp_tools: 是否启用MCP工具
    - custom_config: 自定义配置（JSON格式），用于存储扩展字段
    - benefits: 权益描述列表（JSON数组），供前端渲染展示
    - status: 套餐状态
    - sort_order: 排序顺序

    **注意事项：**
    - 只更新提供的字段，未提供的字段保持不变
    - 套餐ID通常不需要修改
    """,
    responses={
        200: {
            "description": "更新成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "更新套餐成功",
                        "data": {
                            "package_id": "pkg_premium_30days",
                            "name": "高级套餐-30天（新版）",
                            "price": 19.9,
                            "status": "active"
                        }
                    }
                }
            }
        },
        400: {
            "description": "更新失败",
            "content": {
                "application/json": {
                    "examples": {
                        "package_not_found": {
                            "summary": "套餐不存在",
                            "value": {
                                "code": 0,
                                "message": "套餐不存在",
                                "data": None
                            }
                        },
                        "invalid_price": {
                            "summary": "价格无效",
                            "value": {
                                "code": 0,
                                "message": "价格不能为负数",
                                "data": None
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "未授权",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "未提供认证token",
                        "data": None
                    }
                }
            }
        },
        403: {
            "description": "权限不足",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "需要管理员权限",
                        "data": None
                    }
                }
            }
        }
    }
)
async def update_package(
    package_id: str,
    package_data: MemberPackageUpdate,
    admin_info: dict = Depends(require_current_admin)
):
    """更新套餐"""
    result = member_service.update_package(
        package_id=package_id,
        update_data=package_data.dict(exclude_unset=True)
    )

    if result.get("success"):
        return response.success(data=result.get("package"), message="更新套餐成功")
    return response.fail(message=result.get("error", "更新套餐失败"))


@router.delete(
    "/packages/{package_id}",
    summary="删除套餐",
    description="""
    管理员删除会员套餐（软删除）。

    **权限要求：** 管理员权限

    **路径参数：**
    - package_id: 套餐ID

    **删除说明：**
    - 采用软删除机制，套餐状态标记为 deleted
    - 已购买该套餐的用户不受影响
    - 删除后的套餐不再显示在套餐列表中
    - 可通过数据库恢复已删除的套餐
    """,
    responses={
        200: {
            "description": "删除成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "删除套餐成功",
                        "data": None
                    }
                }
            }
        },
        404: {
            "description": "套餐不存在",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "套餐不存在",
                        "data": None
                    }
                }
            }
        },
        401: {
            "description": "未授权",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "未提供认证token",
                        "data": None
                    }
                }
            }
        },
        403: {
            "description": "权限不足",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "需要管理员权限",
                        "data": None
                    }
                }
            }
        }
    }
)
async def delete_package(
    package_id: str,
    admin_info: dict = Depends(require_current_admin)
):
    """删除套餐"""
    result = member_service.delete_package(package_id)

    if result.get("success"):
        return response.success(message=result.get("message", "删除套餐成功"))
    return response.fail(message=result.get("error", "删除套餐失败"))


# ==================== 订单管理 ====================

@router.post(
    "/orders",
    summary="创建订单",
    description="""
    用户购买会员套餐，创建订单。

    **认证要求：** 需要在请求头中提供有效的 Bearer Token

    **创建流程：**
    1. 验证用户身份和套餐有效性
    2. 计算订单金额
    3. 生成唯一订单ID
    4. 创建待支付订单
    5. 返回支付信息

    **订单类型说明：**
    - new: 新购
    - renew: 续费
    - upgrade: 升级

    **支付方式：**
    - wechat: 微信支付
    - alipay: 支付宝
    """,
    responses={
        200: {
            "description": "订单创建成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "创建订单成功",
                        "data": {
                            "order_id": "ord_202401151234567890",
                            "user_id": "user_1234567890abcdef",
                            "package_id": "pkg_premium_30days",
                            "package_name": "高级套餐-30天",
                            "order_type": "new",
                            "amount": 29.9,
                            "payment_method": "wechat",
                            "payment_status": "unpaid",
                            "status": "pending",
                            "created_at": "2024-01-15T12:00:00",
                            "expires_at": "2024-01-15T12:30:00"
                        }
                    }
                }
            }
        },
        400: {
            "description": "创建失败",
            "content": {
                "application/json": {
                    "examples": {
                        "package_not_found": {
                            "summary": "套餐不存在",
                            "value": {
                                "code": 0,
                                "message": "套餐不存在",
                                "data": None
                            }
                        },
                        "package_inactive": {
                            "summary": "套餐已停用",
                            "value": {
                                "code": 0,
                                "message": "套餐已停用",
                                "data": None
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "未授权",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "未提供认证token",
                        "data": None
                    }
                }
            }
        }
    }
)
async def create_order(
    order_data: OrderCreate,
    current_user: dict = Depends(get_current_user_info)
):
    """创建订单"""
    # 从认证信息中获取用户ID
    user_id = current_user.get("user_id", order_data.user_id)

    result = member_service.create_order(
        user_id=user_id,
        package_id=order_data.package_id,
        order_type=order_data.order_type,
        payment_method=order_data.payment_method
    )

    if result.get("success"):
        return response.success(data=result.get("order"), message="创建订单成功")
    return response.fail(message=result.get("error", "创建订单失败"))


@router.get(
    "/orders/{order_id}",
    summary="获取订单详情",
    description="""
    根据订单ID获取订单详细信息。

    **认证要求：** 需要在请求头中提供有效的 Bearer Token

    **路径参数：**
    - order_id: 订单ID

    **权限说明：**
    用户只能查看自己的订单详情

    **返回信息：**
    - 订单基本信息（订单号、套餐、金额）
    - 支付状态和订单状态
    - 创建和支付时间
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
                            "order_id": "ord_202401151234567890",
                            "user_id": "user_1234567890abcdef",
                            "package_id": "pkg_premium_30days",
                            "package_name": "高级套餐-30天",
                            "order_type": "new",
                            "amount": 29.9,
                            "payment_method": "wechat",
                            "payment_status": "paid",
                            "status": "completed",
                            "transaction_id": "wx_202401151234567890",
                            "paid_at": "2024-01-15T12:05:00",
                            "created_at": "2024-01-15T12:00:00"
                        }
                    }
                }
            }
        },
        403: {
            "description": "无权访问",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "无权访问此订单",
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
async def get_order(
    order_id: str,
    current_user: dict = Depends(get_current_user_info)
):
    """获取订单详情"""
    result = member_service.get_order(order_id)

    if result.get("success"):
        order = result.get("order")
        # 验证订单是否属于当前用户
        if order.get("user_id") != current_user.get("user_id"):
            return response.fail(message="无权访问此订单")
        return response.success(data=order)
    return response.fail(message=result.get("error", "获取订单失败"))


@router.get(
    "/orders",
    summary="获取订单列表",
    description="""
    获取用户的订单列表，支持分页和筛选。

    **认证要求：** 需要在请求头中提供有效的 Bearer Token

    **查询参数：**
    - payment_status: 支付状态筛选（unpaid-未支付, paid-已支付, refunded-已退款）
    - status: 订单状态筛选（pending-待处理, completed-已完成, cancelled-已取消, failed-失败）
    - start_date: 开始日期（YYYY-MM-DD）
    - end_date: 结束日期（YYYY-MM-DD）
    - page: 页码（从1开始）
    - page_size: 每页数量（默认20，最大100）

    **返回信息：**
    - 订单列表（按创建时间倒序）
    - 分页信息（总数、当前页、每页数量）
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
                            "orders": [
                                {
                                    "order_id": "ord_202401151234567890",
                                    "package_name": "高级套餐-30天",
                                    "order_type": "new",
                                    "amount": 29.9,
                                    "payment_status": "paid",
                                    "status": "completed",
                                    "created_at": "2024-01-15T12:00:00"
                                }
                            ]
                        }
                    }
                }
            }
        },
        401: {
            "description": "未授权",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "未提供认证token",
                        "data": None
                    }
                }
            }
        }
    }
)
async def list_orders(
    payment_status: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(get_current_user_info)
):
    """获取订单列表"""
    user_id = current_user.get("user_id")

    result = member_service.list_orders(
        user_id=user_id,
        payment_status=payment_status,
        status=status,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size
    )

    if result.get("success"):
        return response.success(data={
            "total": result.get("total", 0),
            "page": result.get("page", page),
            "page_size": result.get("page_size", page_size),
            "orders": result.get("orders", [])
        })
    return response.fail(message=result.get("error", "获取订单列表失败"))


@router.post(
    "/orders/{order_id}/payment",
    summary="完成支付",
    description="""
    模拟支付完成，激活会员。

    **认证要求：** 需要在请求头中提供有效的 Bearer Token

    **路径参数：**
    - order_id: 订单ID

    **请求参数：**
    - transaction_id: 支付平台交易流水号

    **支付流程：**
    1. 验证订单是否存在且属于当前用户
    2. 验证订单状态（只能支付待支付订单）
    3. 更新订单支付状态
    4. 激活或延长会员有效期
    5. 记录交易流水号
    6. 返回新的会员到期时间

    **重要说明：**
    - 实际项目中应通过支付平台回调接口处理
    - 此接口用于测试环境模拟支付
    - 生产环境应关闭此接口
    """,
    responses={
        200: {
            "description": "支付成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "支付成功",
                        "data": {
                            "new_expire_at": "2025-01-15T00:00:00"
                        }
                    }
                }
            }
        },
        400: {
            "description": "支付失败",
            "content": {
                "application/json": {
                    "examples": {
                        "order_not_found": {
                            "summary": "订单不存在",
                            "value": {
                                "code": 0,
                                "message": "订单不存在",
                                "data": None
                            }
                        },
                        "order_already_paid": {
                            "summary": "订单已支付",
                            "value": {
                                "code": 0,
                                "message": "订单已支付",
                                "data": None
                            }
                        },
                        "order_expired": {
                            "summary": "订单已过期",
                            "value": {
                                "code": 0,
                                "message": "订单已过期",
                                "data": None
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "未授权",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "未提供认证token",
                        "data": None
                    }
                }
            }
        }
    }
)
async def complete_payment(
    order_id: str,
    request: CompletePaymentRequest,
    current_user: dict = Depends(get_current_user_info)
):
    """完成支付"""
    result = member_service.complete_payment(
        order_id=order_id,
        transaction_id=request.transaction_id
    )

    if result.get("success"):
        return response.success(
            data={"new_expire_at": result.get("new_expire_at")},
            message=result.get("message", "支付成功")
        )
    return response.fail(message=result.get("error", "支付失败"))


@router.post(
    "/orders/{order_id}/complete-payment",
    summary="完成支付（别名）",
    description="""
    完成支付的别名接口，与 /payment 端点功能相同。

    **认证要求：** 需要在请求头中提供有效的 Bearer Token

    **路径参数：**
    - order_id: 订单ID

    **请求参数：**
    - transaction_id: 支付平台交易流水号
    """,
    responses={
        200: {
            "description": "支付成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "支付成功",
                        "data": {
                            "new_expire_at": "2025-01-15T00:00:00"
                        }
                    }
                }
            }
        },
        400: {
            "description": "支付失败",
            "content": {
                "application/json": {
                    "examples": {
                        "order_not_found": {
                            "summary": "订单不存在",
                            "value": {
                                "code": 0,
                                "message": "订单不存在",
                                "data": None
                            }
                        },
                        "order_already_paid": {
                            "summary": "订单已支付",
                            "value": {
                                "code": 0,
                                "message": "订单已支付",
                                "data": None
                            }
                        },
                        "order_expired": {
                            "summary": "订单已过期",
                            "value": {
                                "code": 0,
                                "message": "订单已过期",
                                "data": None
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "未授权",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "未提供认证token",
                        "data": None
                    }
                }
            }
        }
    }
)
async def complete_payment_alias(
    order_id: str,
    request: CompletePaymentRequest,
    current_user: dict = Depends(get_current_user_info)
):
    """完成支付（别名）"""
    result = member_service.complete_payment(
        order_id=order_id,
        transaction_id=request.transaction_id
    )

    if result.get("success"):
        return response.success(
            data={"new_expire_at": result.get("new_expire_at")},
            message=result.get("message", "支付成功")
        )
    return response.fail(message=result.get("error", "支付失败"))


@router.post(
    "/orders/{order_id}/cancel",
    summary="取消订单",
    description="""
    取消未支付的订单。

    **认证要求：** 需要在请求头中提供有效的 Bearer Token

    **路径参数：**
    - order_id: 订单ID

    **取消规则：**
    - 只能取消未支付的订单
    - 只能取消自己的订单
    - 已支付订单不能取消，只能申请退款

    **取消后操作：**
    - 订单状态更新为 cancelled
    - 订单不能再进行支付
    """,
    responses={
        200: {
            "description": "取消成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "取消订单成功",
                        "data": None
                    }
                }
            }
        },
        400: {
            "description": "取消失败",
            "content": {
                "application/json": {
                    "examples": {
                        "order_not_found": {
                            "summary": "订单不存在",
                            "value": {
                                "code": 0,
                                "message": "订单不存在",
                                "data": None
                            }
                        },
                        "order_already_paid": {
                            "summary": "订单已支付，不能取消",
                            "value": {
                                "code": 0,
                                "message": "订单已支付，不能取消",
                                "data": None
                            }
                        },
                        "order_expired": {
                            "summary": "订单已过期",
                            "value": {
                                "code": 0,
                                "message": "订单已过期",
                                "data": None
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "未授权",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "未提供认证token",
                        "data": None
                    }
                }
            }
        }
    }
)
async def cancel_order(
    order_id: str,
    current_user: dict = Depends(get_current_user_info)
):
    """取消订单"""
    result = member_service.cancel_order(order_id)

    if result.get("success"):
        return response.success(message=result.get("message", "取消订单成功"))
    return response.fail(message=result.get("error", "取消订单失败"))


# ==================== 会员权益管理 ====================

@router.get(
    "/info",
    summary="获取会员信息",
    description="""
    获取当前用户的会员信息和权益详情。

    **认证要求：** 需要在请求头中提供有效的 Bearer Token

    **返回信息：**
    - 会员等级和到期时间
    - 会员有效性状态
    - 当前套餐信息
    - 权益使用统计

    **会员等级说明：**
    - free: 免费用户
    - basic: 基础会员
    - premium: 高级会员
    - enterprise: 企业会员
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
                            "user_id": "user_1234567890abcdef",
                            "member_level": "premium",
                            "member_expire_at": "2025-01-15T00:00:00",
                            "is_member_valid": True,
                            "package_info": {
                                "package_id": "pkg_premium_30days",
                                "name": "高级套餐-30天",
                                "description": "高级会员套餐，有效期30天"
                            },
                            "usage_stats": {
                                "daily_chats_used": 45,
                                "daily_chats_max": 100,
                                "kb_count": 5,
                                "kb_max": 10,
                                "file_storage_used_mb": 512,
                                "file_storage_max_mb": 1024
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "未授权",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "未提供认证token",
                        "data": None
                    }
                }
            }
        }
    }
)
async def get_member_info(current_user: dict = Depends(get_current_user_info)):
    """获取会员信息"""
    user_id = current_user.get("user_id")

    result = member_service.get_member_info(user_id)

    if result.get("success"):
        return response.success(data={
            "user_id": result.get("user_id"),
            "member_level": result.get("member_level"),
            "member_expire_at": result.get("member_expire_at"),
            "is_member_valid": result.get("is_member_valid"),
            "package_info": result.get("package_info"),
            "usage_stats": result.get("usage_stats")
        })
    return response.fail(message=result.get("error", "获取会员信息失败"))


@router.get(
    "/stats",
    summary="获取会员使用统计",
    description="""
    获取当前用户的会员权益使用统计。

    **认证要求：** 需要在请求头中提供有效的 Bearer Token

    **返回信息：**
    - 今日聊天次数使用情况
    - 知识库数量使用情况
    - 文件存储使用情况
    - 各项权益的使用率和剩余额度
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
                            "daily_chats": {
                                "used": 45,
                                "max": 100,
                                "remaining": 55,
                                "usage_percent": 45.0
                            },
                            "knowledge_base": {
                                "used": 5,
                                "max": 10,
                                "remaining": 5,
                                "usage_percent": 50.0
                            },
                            "documents": {
                                "used": 62,
                                "max": 100,
                                "remaining": 38,
                                "usage_percent": 62.0
                            },
                            "file_storage": {
                                "used_mb": 512,
                                "max_mb": 1024,
                                "remaining_mb": 512,
                                "usage_percent": 50.0
                            },
                            "file_count": {
                                "used": 25,
                                "max": 50,
                                "remaining": 25,
                                "usage_percent": 50.0
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "未授权",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "未提供认证token",
                        "data": None
                    }
                }
            }
        }
    }
)
async def get_member_stats(current_user: dict = Depends(get_current_user_info)):
    """获取会员使用统计"""
    user_id = current_user.get("user_id")

    result = member_service.get_member_stats(user_id)

    if result.get("success"):
        return response.success(data=result)
    return response.fail(message=result.get("error", "获取会员统计失败"))


@router.get(
    "/privileges/check",
    summary="检查会员权益",
    description="""
    检查指定会员权益是否可用。

    **认证要求：** 需要在请求头中提供有效的 Bearer Token

    **查询参数：**
    - privilege_type: 权益类型
      - daily_chat: 每日聊天
      - knowledge_base: 知识库
      - document_upload: 文档上传
      - file_storage: 文件存储
      - rag: RAG功能
      - web_search: 网络搜索
      - mcp_tools: MCP工具

    **返回信息：**
    - has_privilege: 是否有权限
    - reason: 无权限的原因
    - used: 已使用数量
    - max: 最大数量
    """,
    responses={
        200: {
            "description": "检查成功",
            "content": {
                "application/json": {
                    "examples": {
                        "has_privilege": {
                            "summary": "有权限",
                            "value": {
                                "code": 1,
                                "message": "操作成功",
                                "data": {
                                    "has_privilege": True,
                                    "reason": "",
                                    "used": 45,
                                    "max": 100
                                }
                            }
                        },
                        "no_privilege": {
                            "summary": "无权限-已用完",
                            "value": {
                                "code": 1,
                                "message": "操作成功",
                                "data": {
                                    "has_privilege": False,
                                    "reason": "今日聊天次数已达上限",
                                    "used": 100,
                                    "max": 100
                                }
                            }
                        },
                        "no_privilege_expired": {
                            "summary": "无权限-会员已过期",
                            "value": {
                                "code": 1,
                                "message": "操作成功",
                                "data": {
                                    "has_privilege": False,
                                    "reason": "会员已过期",
                                    "used": 0,
                                    "max": 0
                                }
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "未授权",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "未提供认证token",
                        "data": None
                    }
                }
            }
        }
    }
)
async def check_privilege(
    privilege_type: str,
    current_user: dict = Depends(get_current_user_info)
):
    """检查会员权益"""
    user_id = current_user.get("user_id")

    result = member_service.check_privilege(user_id, privilege_type)

    if result.get("success"):
        return response.success(data={
            "has_privilege": result.get("has_privilege"),
            "reason": result.get("reason", ""),
            "used": result.get("used"),
            "max": result.get("max")
        })
    return response.fail(message=result.get("error", "检查权益失败"))


@router.post(
    "/privileges/record",
    summary="记录权益使用",
    description="""
    记录会员权益的使用情况。

    **认证要求：** 需要在请求头中提供有效的 Bearer Token

    **请求参数：**
    - usage_type: 使用类型（daily_chat, document_upload, file_upload等）
    - usage_amount: 使用数量（默认1）

    **使用场景：**
    - 用户发送聊天消息时记录
    - 用户上传文档时记录
    - 用户使用其他权益时记录
    """,
    responses={
        200: {
            "description": "记录成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "记录成功",
                        "data": None
                    }
                }
            }
        },
        400: {
            "description": "记录失败",
            "content": {
                "application/json": {
                    "examples": {
                        "limit_exceeded": {
                            "summary": "超出权益限制",
                            "value": {
                                "code": 0,
                                "message": "今日聊天次数已达上限",
                                "data": None
                            }
                        },
                        "member_expired": {
                            "summary": "会员已过期",
                            "value": {
                                "code": 0,
                                "message": "会员已过期",
                                "data": None
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "未授权",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "未提供认证token",
                        "data": None
                    }
                }
            }
        }
    }
)
async def record_usage(
    usage_type: str,
    usage_amount: int = 1,
    current_user: dict = Depends(get_current_user_info)
):
    """记录权益使用"""
    user_id = current_user.get("user_id")

    result = member_service.record_usage(user_id, usage_type, usage_amount)

    if result.get("success"):
        return response.success(message=result.get("message", "记录成功"))
    return response.fail(message=result.get("error", "记录失败"))


# ==================== 会员续费和升级 ====================

@router.post(
    "/renew",
    summary="续费会员",
    description="""
    续费当前会员套餐。

    **认证要求：** 需要在请求头中提供有效的 Bearer Token

    **请求参数：**
    - package_id: 套餐ID
    - payment_method: 支付方式（wechat-微信, alipay-支付宝，默认wechat）

    **续费规则：**
    - 在当前会员到期时间基础上延长有效期
    - 如果会员已过期，从今天开始计算
    - 创建续费订单，支付后生效
    """,
    responses={
        200: {
            "description": "续费订单创建成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "续费订单创建成功",
                        "data": {
                            "order_id": "ord_202401151234567890",
                            "package_id": "pkg_premium_30days",
                            "package_name": "高级套餐-30天",
                            "order_type": "renew",
                            "amount": 29.9,
                            "payment_method": "wechat",
                            "payment_status": "unpaid",
                            "status": "pending",
                            "created_at": "2024-01-15T12:00:00"
                        }
                    }
                }
            }
        },
        400: {
            "description": "续费失败",
            "content": {
                "application/json": {
                    "examples": {
                        "package_not_found": {
                            "summary": "套餐不存在",
                            "value": {
                                "code": 0,
                                "message": "套餐不存在",
                                "data": None
                            }
                        },
                        "invalid_package": {
                            "summary": "无效的套餐",
                            "value": {
                                "code": 0,
                                "message": "当前会员等级高于所选套餐",
                                "data": None
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "未授权",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "未提供认证token",
                        "data": None
                    }
                }
            }
        }
    }
)
async def renew_membership(
    package_id: str,
    payment_method: str = "wechat",
    current_user: dict = Depends(get_current_user_info)
):
    """续费会员"""
    user_id = current_user.get("user_id")

    result = member_service.renew_membership(
        user_id=user_id,
        package_id=package_id,
        payment_method=payment_method
    )

    if result.get("success"):
        return response.success(data=result.get("order"), message="续费订单创建成功")
    return response.fail(message=result.get("error", "续费失败"))


@router.post(
    "/upgrade",
    summary="升级会员",
    description="""
    升级到更高级的会员套餐。

    **认证要求：** 需要在请求头中提供有效的 Bearer Token

    **请求参数：**
    - package_id: 目标套餐ID（必须高于当前套餐等级）
    - payment_method: 支付方式（wechat-微信, alipay-支付宝，默认wechat）

    **升级规则：**
    - 只能升级到更高等级的套餐
    - 套餐等级：free < basic < premium < enterprise
    - 升级后剩余天数按新套餐计算
    - 支付差价（如果需要）
    """,
    responses={
        200: {
            "description": "升级订单创建成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "升级订单创建成功",
                        "data": {
                            "order_id": "ord_202401151234567890",
                            "package_id": "pkg_enterprise_90days",
                            "package_name": "企业套餐-90天",
                            "order_type": "upgrade",
                            "amount": 199.9,
                            "payment_method": "wechat",
                            "payment_status": "unpaid",
                            "status": "pending",
                            "created_at": "2024-01-15T12:00:00"
                        }
                    }
                }
            }
        },
        400: {
            "description": "升级失败",
            "content": {
                "application/json": {
                    "examples": {
                        "package_not_found": {
                            "summary": "套餐不存在",
                            "value": {
                                "code": 0,
                                "message": "套餐不存在",
                                "data": None
                            }
                        },
                        "invalid_upgrade": {
                            "summary": "无效的升级",
                            "value": {
                                "code": 0,
                                "message": "目标套餐等级不高于当前套餐",
                                "data": None
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "未授权",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "未提供认证token",
                        "data": None
                    }
                }
            }
        }
    }
)
async def upgrade_membership(
    package_id: str,
    payment_method: str = "wechat",
    current_user: dict = Depends(get_current_user_info)
):
    """升级会员"""
    user_id = current_user.get("user_id")

    result = member_service.upgrade_membership(
        user_id=user_id,
        package_id=package_id,
        payment_method=payment_method
    )

    if result.get("success"):
        return response.success(data=result.get("order"), message="升级订单创建成功")
    return response.fail(message=result.get("error", "升级失败"))


@router.get(
    "/packages/recommended",
    summary="获取推荐套餐",
    description="""
    根据当前会员等级推荐合适的套餐。

    **认证要求：** 需要在请求头中提供有效的 Bearer Token

    **推荐规则：**
    - 免费用户推荐基础或高级套餐
    - 基础会员推荐高级套餐
    - 高级会员推荐企业套餐
    - 企业会员不显示推荐

    **返回信息：**
    - 当前会员等级
    - 推荐的套餐列表（按价格排序）
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
                            "current_level": "basic",
                            "recommended_packages": [
                                {
                                    "package_id": "pkg_premium_30days",
                                    "name": "高级套餐-30天",
                                    "description": "高级会员套餐，有效期30天",
                                    "price": 29.9,
                                    "original_price": 39.9,
                                    "discount": "7.5折"
                                },
                                {
                                    "package_id": "pkg_premium_90days",
                                    "name": "高级套餐-90天",
                                    "description": "高级会员套餐，有效期90天",
                                    "price": 79.9,
                                    "original_price": 119.7,
                                    "discount": "6.7折"
                                }
                            ]
                        }
                    }
                }
            }
        },
        401: {
            "description": "未授权",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "未提供认证token",
                        "data": None
                    }
                }
            }
        }
    }
)
async def get_recommended_packages(current_user: dict = Depends(get_current_user_info)):
    """获取推荐套餐"""
    user_id = current_user.get("user_id")

    result = member_service.get_recommended_packages(user_id)

    if result.get("success"):
        return response.success(data={
            "current_level": result.get("current_level"),
            "recommended_packages": result.get("recommended_packages", [])
        })
    return response.fail(message=result.get("error", "获取推荐套餐失败"))


# ==================== 会员权益展示 ====================

@router.get(
    "/benefits",
    summary="获取会员权益列表",
    description="""
    展示所有会员等级的权益详情。

    **返回信息：**
    - 按套餐类型分组的权益列表
    - 每个等级的详细权益对比
    - 价格和有效期信息
    - 功能开关状态

    **用途：**
    - 展示会员权益对比页
    - 帮助用户选择合适的套餐
    - 营销推广使用
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
                            "benefits": {
                                "free": {
                                    "package_id": "pkg_free",
                                    "name": "免费套餐",
                                    "description": "基础功能，每日有限次数",
                                    "price": 0,
                                    "original_price": 0,
                                    "benefits": {
                                        "max_daily_chats": 10,
                                        "max_kb_count": 1,
                                        "max_kb_documents": 10,
                                        "max_file_storage_mb": 100,
                                        "max_file_count": 5,
                                        "enable_rag": False,
                                        "enable_web_search": False,
                                        "enable_mcp_tools": False
                                    }
                                },
                                "premium": {
                                    "package_id": "pkg_premium_30days",
                                    "name": "高级套餐-30天",
                                    "description": "高级会员套餐，有效期30天",
                                    "price": 29.9,
                                    "original_price": 39.9,
                                    "benefits": {
                                        "max_daily_chats": 100,
                                        "max_kb_count": 10,
                                        "max_kb_documents": 100,
                                        "max_file_storage_mb": 1024,
                                        "max_file_count": 50,
                                        "enable_rag": True,
                                        "enable_web_search": True,
                                        "enable_mcp_tools": True
                                    }
                                },
                                "enterprise": {
                                    "package_id": "pkg_enterprise_90days",
                                    "name": "企业套餐-90天",
                                    "description": "企业级会员套餐，有效期90天",
                                    "price": 199.9,
                                    "original_price": 299.9,
                                    "benefits": {
                                        "max_daily_chats": 1000,
                                        "max_kb_count": 100,
                                        "max_kb_documents": 1000,
                                        "max_file_storage_mb": 10240,
                                        "max_file_count": 500,
                                        "enable_rag": True,
                                        "enable_web_search": True,
                                        "enable_mcp_tools": True
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        404: {
            "description": "暂无套餐",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "暂无可用套餐",
                        "data": None
                    }
                }
            }
        }
    }
)
async def get_member_benefits():
    """获取会员权益列表"""
    # 获取所有有效套餐
    result = member_service.list_packages(status="active")

    if result.get("success"):
        packages = result.get("packages", [])

        # 按套餐类型分组展示权益
        benefits_by_type = {}
        for package in packages:
            pkg_type = package.get("package_type", "unknown")
            benefits_by_type[pkg_type] = {
                "package_id": package.get("package_id"),
                "name": package.get("name"),
                "description": package.get("description"),
                "price": package.get("price"),
                "original_price": package.get("original_price"),
                "benefits": {
                    "max_daily_chats": package.get("max_daily_chats"),
                    "max_kb_count": package.get("max_kb_count"),
                    "max_kb_documents": package.get("max_kb_documents"),
                    "max_file_storage_mb": package.get("max_file_storage_mb"),
                    "max_file_count": package.get("max_file_count"),
                    "enable_rag": package.get("enable_rag"),
                    "enable_web_search": package.get("enable_web_search"),
                    "enable_mcp_tools": package.get("enable_mcp_tools")
                }
            }

        return response.success(data={"benefits": benefits_by_type})
    return response.fail(message="获取会员权益失败")
