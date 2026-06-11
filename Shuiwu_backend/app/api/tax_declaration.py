"""
智能报税 API 路由
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel

from app.schemas.tax_declaration import (
    CreateTaxDeclarationRequest,
    TaxDeclarationDetailResponse,
    TaxDeclarationListQuery,
    ProcessTaxDeclarationRequest,
    TaxDeclarationStatsResponse,
)
from app.services.tax_declaration.tax_declaration_service import tax_declaration_service
from app.services.tax_declaration.tax_calculator import tax_calculator
from app.services.tax_declaration.tax_exporter import tax_exporter
from app.services.notification.notification_service import notification_service
from app.utils.response import response
from app.utils.dependencies import get_current_user_info, require_current_user, require_admin_role, get_current_user_with_roles

router = APIRouter(prefix="/api/tax-declaration", tags=["智能报税"])


# ============================================================================
# 用户端接口
# ============================================================================

@router.post(
    "/submit",
    summary="提交报税申报",
    description="""
    用户提交报税申报表单。

    **认证要求：** 需要在请求头中提供有效的 Bearer Token

    **业务流程：**
    1. 用户填写报税表单（纳税人信息、收入信息、扣除信息等）
    2. 提交后生成申报单号（格式：TD + YYYYMMDD + 6位序号）
    3. 初始状态为 "pending"（待处理）
    4. 管理员会在后台处理并更新状态

    **税种类型：**
    - pit: 个人所得税（综合所得）
    - vat: 增值税（一般纳税人/小规模纳税人）
    - cit: 企业所得税

    **税期格式：**
    - 季度: 2024Q1, 2024Q2, 2024Q3, 2024Q4
    - 月度: 2024-01, 2024-02, ...
    - 年度: 2024, 2025, ...

    **收入信息示例（个税）：**
    - salary: 工资薪金收入
    - bonus: 奖金收入
    - labor_income: 劳务报酬收入
    - author_income: 稿酬收入
    - royalty_income: 特许权使用费收入

    **扣除信息示例（个税）：**
    - basic_deduction: 基本减除费用（60000元/年）
    - special_deduction: 专项扣除（五险一金）
    - additional_deduction: 专项附加扣除
        * children_education: 子女教育
        * continuing_education: 继续教育
        * housing_loan: 住房贷款利息
        * housing_rent: 住房租金
        * elderly_support: 赡养老人
        * infant_care: 婴幼儿照护
    """,
    responses={
        200: {
            "description": "提交成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "申报提交成功，等待管理员处理",
                        "data": {
                            "id": 1,
                            "declaration_no": "TD2026012000001",
                            "created_at": "2026-01-20T10:00:00"
                        }
                    }
                }
            }
        },
        400: {
            "description": "请求参数错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "参数验证失败",
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
                        "code": "INVALID_TOKEN",
                        "message": "无效的认证token",
                        "data": None
                    }
                }
            }
        }
    }
)
async def submit_declaration(
    request: CreateTaxDeclarationRequest,
    current_user: dict = Depends(get_current_user_info)
):
    """提交报税申报"""
    result = tax_declaration_service.create_declaration(
        user_id=current_user["user_id"],
        taxpayer_name=request.taxpayer_name,
        taxpayer_phone=request.taxpayer_phone,
        tax_type=request.tax_type,
        tax_period=request.tax_period,
        income_info=request.income_info,
        taxpayer_id_card=request.taxpayer_id_card,
        taxpayer_type=request.taxpayer_type,
        deduction_info=request.deduction_info,
        user_remarks=request.user_remarks
    )

    if result.get("success"):
        declaration = result.get("declaration")

        # 发送通知
        notification_service.send_tax_declaration_notification(
            user_id=current_user["user_id"],
            user_phone=request.taxpayer_phone,
            notification_type="submit_success",
            declaration_data=declaration
        )

        return response.success(
            data=declaration,
            message="申报提交成功，等待管理员处理"
        )
    return response.fail(message=result.get("error", "提交失败"))


@router.get(
    "/list",
    summary="获取我的申报列表",
    description="""
    获取当前用户的报税申报列表。

    **认证要求：** 需要在请求头中提供有效的 Bearer Token

    **查询参数：**
    - status: 状态筛选（可选）- pending, processing, completed, rejected
    - tax_type: 税种筛选（可选）- pit, vat, cit
    - tax_period: 税期筛选（可选）- 2024Q1, 2024-01, 2024
    - page: 页码（默认1，最小1）
    - page_size: 每页数量（默认20，范围1-100）

    **返回信息：**
    - 申报列表（按创建时间倒序）
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
                            "total": 10,
                            "page": 1,
                            "page_size": 20,
                            "declarations": [
                                {
                                    "id": 1,
                                    "declaration_no": "TD2026012000001",
                                    "user_id": "user_123456",
                                    "taxpayer_name": "张三",
                                    "taxpayer_phone": "13800138000",
                                    "taxpayer_type": "individual",
                                    "tax_type": "pit",
                                    "tax_period": "2024Q1",
                                    "total_income": 75000.00,
                                    "tax_amount": 2500.00,
                                    "tax_refund": None,
                                    "status": "pending",
                                    "created_at": "2026-01-20T10:00:00",
                                    "processed_at": None
                                }
                            ]
                        }
                    }
                }
            }
        },
        401: {
            "description": "未授权"
        }
    }
)
async def list_my_declarations(
    status: Optional[str] = Query(None, description="状态筛选", example="pending"),
    tax_type: Optional[str] = Query(None, description="税种筛选", example="pit"),
    tax_period: Optional[str] = Query(None, description="税期筛选", example="2024Q1"),
    page: int = Query(1, ge=1, description="页码", example=1),
    page_size: int = Query(20, ge=1, le=100, description="每页数量", example=20),
    current_user: dict = Depends(get_current_user_info)
):
    """获取我的申报列表"""
    result = tax_declaration_service.list_declarations(
        user_id=current_user["user_id"],
        status=status,
        tax_type=tax_type,
        tax_period=tax_period,
        page=page,
        page_size=page_size
    )

    if result.get("success"):
        return response.success(data=result)
    return response.fail(message=result.get("error", "获取列表失败"))


@router.get(
    "/{declaration_id}",
    summary="获取申报详情",
    description="""
    获取报税申报的详细信息。

    **认证要求：** 需要在请求头中提供有效的 Bearer Token

    **路径参数：**
    - declaration_id: 申报ID（整数）

    **权限说明：**
    - 普通用户只能查看自己的申报
    - 管理员可以查看所有申报

    **返回信息：**
    - 完整的申报信息（包括纳税人信息、收入、扣除、计算结果等）
    - 处理状态和历史记录
    - 管理员处理结果（如果已处理）
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
                            "declaration_no": "TD2026012000001",
                            "user_id": "user_123456",
                            "taxpayer_name": "张三",
                            "taxpayer_id_card": "110101199001011234",
                            "taxpayer_phone": "13800138000",
                            "taxpayer_type": "individual",
                            "tax_type": "pit",
                            "tax_period": "2024Q1",
                            "income_info": {
                                "salary": 60000,
                                "bonus": 10000,
                                "labor_income": 5000
                            },
                            "deduction_info": {
                                "special_deduction": 5000,
                                "additional_deduction": {
                                    "children_education": 12000,
                                    "housing_loan": 12000
                                }
                            },
                            "total_income": 75000.00,
                            "total_deduction": 77000.00,
                            "taxable_income": 0.00,
                            "tax_amount": 0.00,
                            "tax_paid": None,
                            "tax_refund": None,
                            "status": "completed",
                            "process_result": "已自动计算并完成申报",
                            "declaration_serial_no": "WS2026012000001",
                            "declaration_date": "2026-01-20",
                            "declaration_proof_url": None,
                            "processed_by": "user_admin_001",
                            "processed_at": "2026-01-20T15:30:00",
                            "process_notes": "系统自动计算",
                            "user_remarks": "请帮我核算季度个税",
                            "created_at": "2026-01-20T10:00:00",
                            "updated_at": "2026-01-20T15:30:00"
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
                        "message": "申报不存在或无权访问",
                        "data": None
                    }
                }
            }
        },
        404: {
            "description": "申报不存在"
        }
    }
)
async def get_declaration_detail(
    declaration_id: int,
    current_user: dict = Depends(get_current_user_with_roles)
):
    """获取申报详情"""
    # 用户只能看自己的，管理员可以看所有
    user_id = current_user["user_id"]
    if not current_user.get("is_admin"):
        result = tax_declaration_service.get_declaration(declaration_id, user_id)
    else:
        result = tax_declaration_service.get_declaration(declaration_id)

    if result.get("success"):
        return response.success(data=result.get("declaration"))
    return response.fail(message=result.get("error", "获取详情失败"))


@router.get(
    "/stats/my",
    summary="获取我的报税统计",
    description="""
    获取当前用户的报税统计信息。

    **认证要求：** 需要在请求头中提供有效的 Bearer Token

    **返回信息：**
    - 总申报数
    - 各状态申报数（待处理、处理中、已完成、已拒绝）
    - 总应纳税额（已完成申报的）
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
                            "total_count": 10,
                            "pending_count": 2,
                            "processing_count": 1,
                            "completed_count": 6,
                            "rejected_count": 1,
                            "total_tax_amount": 15000.00
                        }
                    }
                }
            }
        },
        401: {
            "description": "未授权"
        }
    }
)
async def get_my_stats(
    current_user: dict = Depends(get_current_user_info)
):
    """获取我的报税统计"""
    result = tax_declaration_service.get_stats(user_id=current_user["user_id"])

    if result.get("success"):
        return response.success(data=result.get("stats"))
    return response.fail(message=result.get("error", "获取统计失败"))


# ============================================================================
# 管理员接口
# ============================================================================

@router.get(
    "/admin/list",
    summary="获取所有申报列表（管理员）",
    description="""
    管理员获取所有用户的报税申报列表。

    **权限要求：** 管理员权限（user_type = admin）

    **查询参数：**
    - user_id: 用户ID筛选（可选）
    - status: 状态筛选（可选）
    - tax_type: 税种筛选（可选）
    - tax_period: 税期筛选（可选）
    - page: 页码（默认1，最小1）
    - page_size: 每页数量（默认20，范围1-100）

    **返回信息：**
    - 所有用户的申报列表
    - 分页信息
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
                            "declarations": [
                                {
                                    "id": 1,
                                    "declaration_no": "TD2026012000001",
                                    "user_id": "user_123456",
                                    "taxpayer_name": "张三",
                                    "taxpayer_phone": "13800138000",
                                    "taxpayer_type": "individual",
                                    "tax_type": "pit",
                                    "tax_period": "2024Q1",
                                    "total_income": 75000.00,
                                    "tax_amount": 2500.00,
                                    "tax_refund": None,
                                    "status": "pending",
                                    "created_at": "2026-01-20T10:00:00",
                                    "processed_at": None
                                }
                            ]
                        }
                    }
                }
            }
        },
        401: {
            "description": "未授权或无权限",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "需要管理员权限",
                        "data": None
                    }
                }
            }
        },
        403: {
            "description": "权限不足"
        }
    }
)
async def list_all_declarations(
    user_id: Optional[str] = Query(None, description="用户ID筛选"),
    status: Optional[str] = Query(None, description="状态筛选"),
    tax_type: Optional[str] = Query(None, description="税种筛选"),
    tax_period: Optional[str] = Query(None, description="税期筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: dict = Depends(require_admin_role)
):
    """获取所有申报列表（管理员）"""

    result = tax_declaration_service.list_declarations(
        user_id=user_id,
        status=status,
        tax_type=tax_type,
        tax_period=tax_period,
        page=page,
        page_size=page_size
    )

    if result.get("success"):
        return response.success(data=result)
    return response.fail(message=result.get("error", "获取列表失败"))


@router.post(
    "/admin/{declaration_id}/process",
    summary="处理报税申报（管理员）",
    description="""
    管理员处理用户的报税申报。

    **权限要求：** 管理员权限（user_type = admin）

    **业务流程：**
    1. 管理员查看申报详情
    2. 计算税额（收入、扣除、应纳税额等）
    3. 完成税务局申报
    4. 录入申报流水号和凭证
    5. 更新状态

    **自动计算功能：**
    如果管理员不填写计算结果（total_income、tax_amount等），
    系统会根据申报信息自动计算税额。

    **状态流转：**
    - pending → processing（开始处理）
    - processing → completed（处理完成）
    - processing → rejected（拒绝申报）

    **请求参数：**
    - status: 处理状态（必填）
    - total_income: 收入总额（可选，不填则自动计算）
    - total_deduction: 扣除总额（可选，不填则自动计算）
    - taxable_income: 应纳税所得额（可选，不填则自动计算）
    - tax_amount: 应纳税额（可选，不填则自动计算）
    - tax_paid: 已缴税额（可选）
    - tax_refund: 应退税额（可选，不填则自动计算）
    - declaration_serial_no: 申报流水号
    - declaration_date: 申报日期
    - declaration_proof_url: 申报凭证URL
    - process_result: 处理结果说明
    - process_notes: 处理备注
    """,
    responses={
        200: {
            "description": "处理成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "申报 TD2026012000001 状态已更新为 completed",
                        "data": {
                            "declaration_id": 1,
                            "declaration_no": "TD2026012000001",
                            "status": "completed"
                        }
                    }
                }
            }
        },
        400: {
            "description": "请求参数错误或自动计算失败"
        },
        401: {
            "description": "未授权或无权限",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "需要管理员权限",
                        "data": None
                    }
                }
            }
        },
        404: {
            "description": "申报不存在",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "申报不存在",
                        "data": None
                    }
                }
            }
        }
    }
)
async def process_declaration(
    declaration_id: int,
    request: ProcessTaxDeclarationRequest,
    current_user: dict = Depends(require_admin_role)
):
    """处理报税申报（管理员）"""

    # 获取申报详情（用于自动计算和通知）
    declaration_detail = tax_declaration_service.get_declaration(declaration_id)

    # 如果管理员没有手动填写计算结果，系统自动计算
    if request.total_income is None and declaration_detail.get("success"):
        declaration_data = declaration_detail.get("declaration")
        tax_type = declaration_data.get("tax_type")
        income_info = declaration_data.get("income_info") or {}
        deduction_info = declaration_data.get("deduction_info") or {}

        try:
            # 自动计算税额
            calculation = tax_calculator.calculate(
                tax_type=tax_type,
                income_info=income_info,
                deduction_info=deduction_info
            )

            # 使用计算结果
            request.total_income = calculation.get("total_income")
            request.total_deduction = calculation.get("total_deduction")
            request.taxable_income = calculation.get("taxable_income")
            request.tax_amount = calculation.get("tax_amount")

            # 如果没有填写退税额，自动计算
            if request.tax_refund is None and request.tax_paid:
                request.tax_refund = max(request.tax_paid - request.tax_amount, 0)

        except Exception as e:
            return response.fail(message=f"自动计算失败: {str(e)}")

    result = tax_declaration_service.process_declaration(
        declaration_id=declaration_id,
        processed_by=current_user["user_id"],
        total_income=request.total_income,
        total_deduction=request.total_deduction,
        taxable_income=request.taxable_income,
        tax_amount=request.tax_amount,
        tax_paid=request.tax_paid,
        tax_refund=request.tax_refund,
        declaration_serial_no=request.declaration_serial_no,
        declaration_date=request.declaration_date,
        declaration_proof_url=request.declaration_proof_url,
        status=request.status,
        process_result=request.process_result,
        process_notes=request.process_notes
    )

    if result.get("success"):
        # 发送通知给用户
        declaration_data = {
            "declaration_no": result.get("declaration_no"),
            "status": result.get("status"),
            "tax_amount": request.tax_amount,
            "tax_refund": request.tax_refund,
            "process_result": request.process_result
        }

        # 获取用户ID
        if declaration_detail.get("success"):
            user_id = declaration_detail.get("declaration", {}).get("user_id")
            notification_type = "completed" if request.status == "completed" else "rejected"
            notification_service.send_tax_declaration_notification(
                user_id=user_id,
                notification_type=notification_type,
                declaration_data=declaration_data
            )

        return response.success(
            data={
                "declaration_id": result.get("declaration_id"),
                "declaration_no": result.get("declaration_no"),
                "status": result.get("status")
            },
            message=result.get("message")
        )
    return response.fail(message=result.get("error", "处理失败"))


@router.get(
    "/admin/stats",
    summary="获取全局报税统计（管理员）",
    description="""
    管理员获取全局报税统计信息。

    **权限要求：** 管理员权限（user_type = admin）

    **返回信息：**
    - 全局申报统计总数
    - 各状态申报数
    - 总应纳税额（已完成申报的）
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
                            "total_count": 100,
                            "pending_count": 20,
                            "processing_count": 10,
                            "completed_count": 65,
                            "rejected_count": 5,
                            "total_tax_amount": 150000.00
                        }
                    }
                }
            }
        },
        401: {
            "description": "未授权或无权限"
        },
        403: {
            "description": "权限不足"
        }
    }
)
async def get_global_stats(
    current_user: dict = Depends(require_admin_role)
):
    """获取全局报税统计（管理员）"""

    result = tax_declaration_service.get_stats()

    if result.get("success"):
        return response.success(data=result.get("stats"))
    return response.fail(message=result.get("error", "获取统计失败"))


# ============================================================================
# 导出接口
# ============================================================================

@router.get(
    "/{declaration_id}/export",
    summary="导出申报表",
    description="""
    导出报税申报表为Excel或CSV格式。

    **认证要求：** 需要在请求头中提供有效的 Bearer Token

    **路径参数：**
    - declaration_id: 申报ID（整数）

    **查询参数：**
    - format: 导出格式（支持: xlsx, csv），默认 xlsx

    **权限说明：**
    - 用户只能导出自己的申报
    - 管理员可以导出所有申报

    **返回：**
    - 文件流（可直接下载）
    - Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet (xlsx) 或 text/csv (csv)
    - Content-Disposition: attachment; filename="tax_declaration_TD2026012000001.xlsx"
    """,
    responses={
        200: {
            "description": "导出成功",
            "content": {
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {
                    "example": "二进制文件流"
                },
                "text/csv": {
                    "example": "CSV文本文件"
                }
            }
        },
        403: {
            "description": "无权访问",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "无权访问此申报",
                        "data": None
                    }
                }
            }
        },
        404: {
            "description": "申报不存在"
        }
    }
)
async def export_declaration(
    declaration_id: int,
    format: str = Query("xlsx", description="导出格式: xlsx, csv"),
    current_user: dict = Depends(get_current_user_with_roles)
):
    """导出申报表"""
    # 获取申报详情
    if not current_user.get("is_admin"):
        result = tax_declaration_service.get_declaration(declaration_id, current_user["user_id"])
    else:
        result = tax_declaration_service.get_declaration(declaration_id)

    if not result.get("success"):
        return response.fail(message=result.get("error", "获取申报失败"))

    declaration_data = result.get("declaration")

    # 导出文件
    try:
        if format.lower() == "csv":
            file_content = tax_exporter.export_to_csv(declaration_data)
            media_type = "text/csv"
            filename = f"tax_declaration_{declaration_data.get('declaration_no')}.csv"
        else:
            file_content = tax_exporter.export_to_excel(declaration_data)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"tax_declaration_{declaration_data.get('declaration_no')}.xlsx"

        return Response(
            content=file_content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        return response.fail(message=f"导出失败: {str(e)}")
