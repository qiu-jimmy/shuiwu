"""
税务师入驻模块 - 用户端 API路由
处理用户申请入驻税务师、查看申请状态等功能
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Query

from app.schemas.tax_accountant import (
    TaxAccountantApplicationCreate,
    TaxAccountantApplicationStatusResponse,
    TaxAccountantDetailResponse
)
from app.schemas.common import ApiResponse
from app.services.tax_accountant.tax_accountant_service import tax_accountant_service
from app.utils.dependencies import get_current_user_info
from app.utils.response import response

router = APIRouter(prefix="/api/tax_accountant", tags=["税务师入驻"])


# ============================================================================
# 用户端功能
# ============================================================================


@router.post(
    "/apply",
    summary="申请成为税务师",
    description="""
    提交税务师入驻申请。

    **申请条件：**
    - 用户已注册并登录
    - 未有待审核或已通过的申请
    - 提供完整的个人信息和资质证明

    **所需材料：**
    - 真实姓名
    - 身份证号
    - 联系电话
    - 税务师证书编号
    - 证书图片URL（至少1张）
    - 工作年限
    - 专长领域（至少1个）
    - 个人简介（可选）

    **申请流程：**
    1. 用户提交申请
    2. 管理员审核
    3. 审核通过：自动创建税务师档案
    4. 审核拒绝：可查看拒绝原因后重新申请

    **状态说明：**
    - pending: 待审核
    - approved: 已通过
    - rejected: 已拒绝
    """,
    responses={
        200: {
            "description": "申请提交成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "申请提交成功，请等待审核",
                        "data": {
                            "application_id": "ta_1234567890"
                        }
                    }
                }
            }
        },
        400: {
            "description": "申请提交失败",
            "content": {
                "application/json": {
                    "examples": {
                        "already_pending": {
                            "summary": "已有待审核申请",
                            "value": {
                                "code": 0,
                                "message": "您已有待审核的申请，请等待审核结果",
                                "data": None
                            }
                        },
                        "already_approved": {
                            "summary": "已是税务师",
                            "value": {
                                "code": 0,
                                "message": "您已是认证税务师，无需重复申请",
                                "data": None
                            }
                        }
                    }
                }
            }
        }
    }
)
async def apply_tax_accountant(
    request: TaxAccountantApplicationCreate,
    current_user: dict = Depends(get_current_user_info)
) -> Dict[str, Any]:
    """
    申请成为税务师

    Args:
        request: 申请信息（前端表单结构）
        current_user: 当前认证用户信息

    Returns:
        包含申请ID的响应

    **前端表单字段映射：**
    - name → real_name
    - birthDate → birth_date
    - idCard → id_card
    - address → address
    - phone → phone
    - certificateNo → certificate_number
    - certificateDate → certificate_date
    - certificateImages → certificate_images
    - signatureImage → signature_image
    - experiences → work_experiences
    - expertise → specialty_area（转换为数组）
    - settledIndex → has_settled（0=否, 1=是）
    - additionalInfo → additional_info
    """
    # 使用to_internal_dict方法将前端表单转换为后端字段
    application_data = request.to_internal_dict()

    result = tax_accountant_service.submit_application(
        user_id=current_user["user_id"],
        application_data=application_data
    )

    if result.get("success"):
        return response.success(data={"application_id": result.get("application_id")}, message=result.get("message"))
    return response.fail(message=result.get("message"))


@router.get(
    "/my-application",
    summary="获取我的申请状态",
    description="""
    获取当前用户的税务师申请状态。

    **返回内容：**
    - has_applied: 是否已申请
    - application_id: 申请ID（如有）
    - status: 申请状态
    - reject_reason: 拒绝原因（如被拒绝）
    - created_at: 申请时间

    **状态说明：**
    - null: 未申请
    - pending: 待审核
    - approved: 已通过
    - rejected: 已拒绝

    **使用场景：**
    - 用户查看自己的申请进度
    - 被拒绝后查看拒绝原因
    - 判断是否可以重新申请
    """,
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "examples": {
                        "not_applied": {
                            "summary": "未申请",
                            "value": {
                                "code": 1,
                                "message": "获取成功",
                                "data": {
                                    "has_applied": False,
                                    "application_id": None,
                                    "status": None,
                                    "reject_reason": None,
                                    "created_at": None
                                }
                            }
                        },
                        "pending": {
                            "summary": "待审核",
                            "value": {
                                "code": 1,
                                "message": "获取成功",
                                "data": {
                                    "has_applied": True,
                                    "application_id": "ta_1234567890",
                                    "status": "pending",
                                    "reject_reason": None,
                                    "created_at": "2026-02-01T10:00:00"
                                }
                            }
                        },
                        "rejected": {
                            "summary": "已拒绝",
                            "value": {
                                "code": 1,
                                "message": "获取成功",
                                "data": {
                                    "has_applied": True,
                                    "application_id": "ta_1234567890",
                                    "status": "rejected",
                                    "reject_reason": "证书图片不清晰",
                                    "created_at": "2026-02-01T10:00:00"
                                }
                            }
                        }
                    }
                }
            }
        }
    }
)
async def get_my_application_status(
    current_user: dict = Depends(get_current_user_info)
) -> Dict[str, Any]:
    """
    获取我的申请状态

    Args:
        current_user: 当前认证用户信息

    Returns:
        包含申请状态的响应
    """
    result = tax_accountant_service.get_my_application_status(current_user["user_id"])
    return response.success(data=result)


@router.get(
    "/my-info",
    summary="获取我的税务师信息",
    description="""
    获取当前用户的税务师信息（仅限已认证的税务师）。

    **返回内容：**
    - accountant_id: 税务师ID
    - user_id: 用户ID
    - real_name: 真实姓名
    - certificate_number: 证书编号
    - specialty_area: 专长领域
    - introduction: 个人简介
    - status: 状态（active-正常, suspended-暂停）
    - service_count: 服务次数
    - rating: 评分
    - created_at: 认证时间

    **使用场景：**
    - 税务师查看自己的档案信息
    - 税务师查看自己的服务统计
    - 税务师个人中心展示

    **注意：** 仅认证税务师可调用此接口
    """,
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "获取成功",
                        "data": {
                            "accountant_id": "tac_1234567890",
                            "user_id": "user_1234567890",
                            "real_name": "张三",
                            "certificate_number": "TA20210001",
                            "specialty_area": ["企业所得税", "税务筹划"],
                            "introduction": "10年税务从业经验",
                            "status": "active",
                            "service_count": 50,
                            "rating": 4.8,
                            "created_at": "2026-01-01T10:00:00"
                        }
                    }
                }
            }
        },
        400: {
            "description": "不是税务师",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "您还不是认证税务师",
                        "data": None
                    }
                }
            }
        }
    }
)
async def get_my_accountant_info(
    current_user: dict = Depends(get_current_user_info)
) -> Dict[str, Any]:
    """
    获取我的税务师信息

    Args:
        current_user: 当前认证用户信息

    Returns:
        包含税务师信息的响应
    """
    accountant_info = tax_accountant_service.get_my_accountant_info(current_user["user_id"])

    if accountant_info:
        return response.success(data=accountant_info)
    return response.fail(message="您还不是认证税务师")


@router.get(
    "/list",
    summary="获取税务师列表",
    description="""
    获取平台上的税务师列表（公开接口）。

    **查询参数：**
    - page: 页码，从1开始
    - page_size: 每页数量，最大100
    - status: 状态筛选（active-正常, suspended-暂停）
    - keyword: 关键词搜索（姓名或手机号）

    **返回内容：**
    - 税务师基本信息
    - 专长领域
    - 服务统计
    - 评分信息

    **排序方式：** 按认证时间倒序

    **使用场景：**
    - 用户浏览税务师列表
    - 选择合适的税务师咨询
    """,
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "获取成功",
                        "data": {
                            "total": 50,
                            "page": 1,
                            "page_size": 20,
                            "accountants": [
                                {
                                    "accountant_id": "tac_1234567890",
                                    "real_name": "张三",
                                    "specialty_area": ["企业所得税", "税务筹划"],
                                    "introduction": "10年税务从业经验",
                                    "service_count": 50,
                                    "rating": 4.8,
                                    "status": "active"
                                }
                            ]
                        }
                    }
                }
            }
        }
    }
)
async def list_accountants(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="状态筛选"),
    keyword: Optional[str] = Query(None, description="关键词搜索")
) -> Dict[str, Any]:
    """
    获取税务师列表

    Args:
        page: 页码
        page_size: 每页数量
        status: 状态筛选
        keyword: 关键词搜索

    Returns:
        包含税务师列表的响应
    """
    result = tax_accountant_service.get_accountant_list(page, page_size, status, keyword)
    return response.success(data=result)


@router.get(
    "/{accountant_id}",
    summary="获取税务师详情",
    description="""
    获取指定税务师的详细信息（公开接口）。

    **返回内容：**
    - 税务师基本信息
    - 专长领域
    - 个人简介
    - 服务统计
    - 评分信息
    - 用户昵称、头像等

    **使用场景：**
    - 用户查看税务师详情
    - 了解税务师背景和专业领域
    - 决定是否选择该税务师咨询
    """,
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "获取成功",
                        "data": {
                            "accountant_id": "tac_1234567890",
                            "real_name": "张三",
                            "certificate_number": "TA20210001",
                            "specialty_area": ["企业所得税", "税务筹划"],
                            "introduction": "10年税务从业经验，擅长企业所得税筹划和税务风险防控",
                            "service_count": 50,
                            "rating": 4.8,
                            "status": "active",
                            "nickname": "张老师",
                            "avatar_url": "https://example.com/avatar.jpg",
                            "phone": "13800138000",
                            "created_at": "2026-01-01T10:00:00"
                        }
                    }
                }
            }
        },
        404: {
            "description": "税务师不存在",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "税务师不存在",
                        "data": None
                    }
                }
            }
        }
    }
)
async def get_accountant_detail(
    accountant_id: str
) -> Dict[str, Any]:
    """
    获取税务师详情

    Args:
        accountant_id: 税务师ID

    Returns:
        包含税务师详情的响应
    """
    accountant_info = tax_accountant_service.get_accountant_detail(accountant_id)

    if accountant_info:
        return response.success(data=accountant_info)
    return response.fail(message="税务师不存在")
