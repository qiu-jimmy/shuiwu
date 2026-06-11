"""
个体户工商申报 API 路由。

职责：
  - 用户端：提交申报、查看列表与详情、查看自己的统计
  - 管理员端：查看所有申报列表、处理申报、查看全局统计
  - 辅助：申报类型/状态元数据查询

核心改动（v1.1 工商引擎改版）：
  - /submit 新增 license_application 分支：对新字段做服务端必填校验，
    并将新字段映射到数据库通用列（business_name/operator_name 等）
    和 declaration_info JSON，不改动数据库结构。
  - 旧申报类型（annual_report 等）流程不变，向后兼容。
"""
import re
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel

from app.schemas.business_declaration import (
    CreateBusinessDeclarationRequest,
    BusinessDeclarationDetailResponse,
    BusinessDeclarationListQuery,
    BusinessDeclarationListResponse,
    BusinessDeclarationStatsResponse,
    ProcessBusinessDeclarationRequest,
    DeclarationType,
    DeclarationStatus,
)
from app.services.business_declaration.business_declaration_service import business_declaration_service
from app.services.notification.notification_service import notification_service
from app.utils.response import response
from app.utils.dependencies import get_current_user_info, require_admin_role, get_current_user_with_roles

router = APIRouter(prefix="/api/business-declaration", tags=["个体户工商申报"])


# ============================================================================
# 用户端接口
# ============================================================================

@router.post(
    "/submit",
    summary="提交工商申报",
    description="""
    用户提交个体户工商申报表单。

    **认证要求：** 需要在请求头中提供有效的 Bearer Token

    **申报类型：**
    - annual_report: 年报
    - change_registration: 变更登记
    - deregistration: 注销登记
    - tax_registration: 税务登记
    - invoice_application: 发票申请
    - license_application: 工商执照申请（新增，使用新版字段体系）

    **执照申请必填字段：**
    license_store_name, id_card_number, id_card_valid_type,
    id_card_front_url, id_card_back_url, applicant_name,
    applicant_phone, political_status, education_level, agree_protocol
    """,
    responses={
        200: {
            "description": "提交成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "工商申报提交成功，等待管理员处理",
                        "data": {
                            "id": 1,
                            "declaration_no": "BD2026030300001",
                            "created_at": "2026-03-03T10:00:00"
                        }
                    }
                }
            }
        },
        400: {"description": "请求参数错误"},
        401: {"description": "未授权"},
    }
)
async def submit_business_declaration(
    request: CreateBusinessDeclarationRequest,
    current_user: dict = Depends(get_current_user_info)
):
    """提交工商申报（支持旧类型与新版执照申请）"""

    if request.declaration_type == DeclarationType.LICENSE_APPLICATION:
        # ---- 执照申请：服务端必填校验 ----
        required_fields = {
            "license_store_name": request.license_store_name,
            "id_card_number": request.id_card_number,
            "id_card_valid_type": request.id_card_valid_type,
            "id_card_front_url": request.id_card_front_url,
            "id_card_back_url": request.id_card_back_url,
            "applicant_name": request.applicant_name,
            "applicant_phone": request.applicant_phone,
            "political_status": request.political_status,
            "education_level": request.education_level,
        }
        missing = [k for k, v in required_fields.items() if not v]
        if missing:
            return response.fail(message=f"缺少必填字段：{', '.join(missing)}")

        # agree_protocol 必须为 True
        if not request.agree_protocol:
            return response.fail(message="必须同意用户协议")

        # 有效期为 range 时，起止日期必填
        if request.id_card_valid_type == "range":
            if not request.id_card_valid_start or not request.id_card_valid_end:
                return response.fail(message="证件有效期类型为 range 时，id_card_valid_start 和 id_card_valid_end 必填")

        # 邮箱非空时做格式校验
        if request.email:
            if not re.match(r"^[\w\.\-]+@[\w\.\-]+\.\w+$", request.email):
                return response.fail(message="邮箱格式不正确")

        # ---- 执照申请：字段映射 ----
        # 主字段映射到数据库通用列（不改表结构）
        business_name = request.license_store_name
        operator_name = request.applicant_name
        operator_phone = request.applicant_phone
        operator_id_card = request.id_card_number

        # 执照申请专属信息打包存入 declaration_info（JSONB）
        declaration_info = {
            "license_store_name_list": request.license_store_name_list or [],
            "id_card_valid_type": request.id_card_valid_type,
            "id_card_valid_start": request.id_card_valid_start,
            "id_card_valid_end": request.id_card_valid_end,
            "id_card_front_url": request.id_card_front_url,
            "id_card_back_url": request.id_card_back_url,
            "political_status": request.political_status,
            "education_level": request.education_level,
            "email": request.email or "",
            "agree_protocol": request.agree_protocol,
        }
        # extra_attachments 映射到通用 attachments 列
        attachments = request.extra_attachments
        notify_phone = request.applicant_phone

    else:
        # ---- 旧类型：必填校验（保持原逻辑） ----
        if not request.business_name or not request.operator_name or not request.operator_phone:
            return response.fail(message="business_name、operator_name、operator_phone 为旧类型申报的必填字段")

        business_name = request.business_name
        operator_name = request.operator_name
        operator_phone = request.operator_phone
        operator_id_card = request.operator_id_card
        declaration_info = request.declaration_info
        attachments = request.attachments
        notify_phone = request.operator_phone

    # ---- 调用服务层落库 ----
    result = business_declaration_service.create_declaration(
        user_id=current_user["user_id"],
        business_name=business_name,
        operator_name=operator_name,
        operator_phone=operator_phone,
        declaration_type=request.declaration_type,
        business_license_no=request.business_license_no,
        business_address=request.business_address,
        business_type=request.business_type,
        business_scope=request.business_scope,
        operator_id_card=operator_id_card,
        declaration_info=declaration_info,
        attachments=attachments,
        user_remarks=request.user_remarks,
    )

    if result.get("success"):
        declaration = result.get("declaration")
        notification_service.send_tax_declaration_notification(
            user_id=current_user["user_id"],
            user_phone=notify_phone,
            notification_type="submit_success",
            declaration_data=declaration,
        )
        return response.success(
            data=declaration,
            message="工商申报提交成功，等待管理员处理",
        )
    return response.fail(message=result.get("error", "提交失败"))


@router.get(
    "/list",
    summary="获取我的工商申报列表",
    description="""
    获取当前用户的工商申报列表。

    **认证要求：** 需要在请求头中提供有效的 Bearer Token

    **查询参数：**
    - status: 状态筛选（可选）- pending/processing/completed/rejected/need_supplement
    - declaration_type: 类型筛选（可选）- annual_report/change_registration/
      deregistration/tax_registration/invoice_application/license_application
    - page: 页码（默认1）
    - page_size: 每页数量（默认20，最大100）
    """,
    responses={
        200: {"description": "获取成功"},
        401: {"description": "未授权"},
    }
)
async def list_my_business_declarations(
    status: Optional[str] = Query(None, description="状态筛选", example="pending"),
    declaration_type: Optional[str] = Query(None, description="申报类型筛选", example="license_application"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: dict = Depends(get_current_user_info)
):
    """获取我的工商申报列表"""
    result = business_declaration_service.list_declarations(
        user_id=current_user["user_id"],
        status=status,
        declaration_type=declaration_type,
        page=page,
        page_size=page_size,
    )
    if result.get("success"):
        return response.success(data=result)
    return response.fail(message=result.get("error", "获取列表失败"))


@router.get(
    "/{declaration_id}",
    summary="获取工商申报详情",
    description="""
    获取工商申报的详细信息。

    **认证要求：** 需要在请求头中提供有效的 Bearer Token

    **权限说明：**
    - 普通用户只能查看自己的申报
    - 管理员可以查看所有申报

    **执照申请类型说明：**
    declaration_type = license_application 时，执照专属字段（证件有效期、
    政治面貌、学历等）存储在 declaration_info JSON 中，
    补充材料通过 attachments 字段返回。
    """,
    responses={
        200: {"description": "获取成功"},
        403: {"description": "无权访问"},
        404: {"description": "申报不存在"},
    }
)
async def get_business_declaration_detail(
    declaration_id: int,
    current_user: dict = Depends(get_current_user_with_roles)
):
    """获取工商申报详情"""
    user_id = current_user["user_id"]
    if not current_user.get("is_admin"):
        result = business_declaration_service.get_declaration(declaration_id, user_id)
    else:
        result = business_declaration_service.get_declaration(declaration_id)

    if result.get("success"):
        return response.success(data=result.get("declaration"))
    return response.fail(message=result.get("error", "获取详情失败"))


@router.get(
    "/stats/my",
    summary="获取我的工商申报统计",
    description="""
    获取当前用户的工商申报统计信息。

    **认证要求：** 需要在请求头中提供有效的 Bearer Token

    **返回信息：**
    各状态申报数及各类型申报数（含 license_application_count）
    """,
    responses={
        200: {"description": "获取成功"},
        401: {"description": "未授权"},
    }
)
async def get_my_business_stats(
    current_user: dict = Depends(get_current_user_info)
):
    """获取我的工商申报统计"""
    result = business_declaration_service.get_stats(user_id=current_user["user_id"])
    if result.get("success"):
        return response.success(data=result.get("stats"))
    return response.fail(message=result.get("error", "获取统计失败"))


# ============================================================================
# 管理员接口
# ============================================================================

@router.get(
    "/admin/list",
    summary="获取所有工商申报列表（管理员）",
    description="""
    管理员获取所有用户的工商申报列表。

    **权限要求：** 管理员权限（user_type = admin）

    **查询参数：**
    - user_id: 用户ID筛选（可选）
    - status: 状态筛选（可选）
    - declaration_type: 类型筛选（可选）- annual_report/change_registration/
      deregistration/tax_registration/invoice_application/license_application
    - page: 页码（默认1）
    - page_size: 每页数量（默认20，最大100）
    """,
    responses={
        200: {"description": "获取成功"},
        401: {"description": "未授权或无权限"},
        403: {"description": "权限不足"},
    }
)
async def list_all_business_declarations(
    user_id: Optional[str] = Query(None, description="用户ID筛选"),
    status: Optional[str] = Query(None, description="状态筛选"),
    declaration_type: Optional[str] = Query(None, description="申报类型筛选，支持 license_application"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: dict = Depends(require_admin_role)
):
    """获取所有工商申报列表（管理员）"""
    result = business_declaration_service.list_declarations(
        user_id=user_id,
        status=status,
        declaration_type=declaration_type,
        page=page,
        page_size=page_size,
    )
    if result.get("success"):
        return response.success(data=result)
    return response.fail(message=result.get("error", "获取列表失败"))


@router.post(
    "/admin/{declaration_id}/process",
    summary="处理工商申报（管理员）",
    description="""
    管理员处理用户的工商申报。

    **权限要求：** 管理员权限（user_type = admin）

    **状态流转：**
    - pending → processing → completed / rejected / need_supplement
    """,
    responses={
        200: {"description": "处理成功"},
        400: {"description": "请求参数错误"},
        401: {"description": "未授权或无权限"},
        404: {"description": "申报不存在"},
    }
)
async def process_business_declaration(
    declaration_id: int,
    request: ProcessBusinessDeclarationRequest,
    current_user: dict = Depends(require_admin_role)
):
    """处理工商申报（管理员）"""
    declaration_detail = business_declaration_service.get_declaration(declaration_id)

    result = business_declaration_service.process_declaration(
        declaration_id=declaration_id,
        processed_by=current_user["user_id"],
        status=request.status,
        approval_no=request.approval_no,
        approval_date=request.approval_date,
        approval_proof_url=request.approval_proof_url,
        process_result=request.process_result,
        process_notes=request.process_notes,
    )

    if result.get("success"):
        declaration_data = {
            "declaration_no": result.get("declaration_no"),
            "status": result.get("status"),
            "process_result": request.process_result,
        }
        if declaration_detail.get("success"):
            user_id = declaration_detail.get("declaration", {}).get("user_id")
            notification_type = "completed" if request.status == "completed" else request.status
            notification_service.send_tax_declaration_notification(
                user_id=user_id,
                notification_type=notification_type,
                declaration_data=declaration_data,
            )
        return response.success(
            data={
                "declaration_id": result.get("declaration_id"),
                "declaration_no": result.get("declaration_no"),
                "status": result.get("status"),
            },
            message=result.get("message"),
        )
    return response.fail(message=result.get("error", "处理失败"))


@router.get(
    "/admin/stats",
    summary="获取全局工商申报统计（管理员）",
    description="""
    管理员获取全局工商申报统计信息。

    **权限要求：** 管理员权限（user_type = admin）

    **返回信息：**
    各状态申报数及各类型申报数（含 license_application_count）
    """,
    responses={
        200: {"description": "获取成功"},
        401: {"description": "未授权或无权限"},
        403: {"description": "权限不足"},
    }
)
async def get_global_business_stats(
    current_user: dict = Depends(require_admin_role)
):
    """获取全局工商申报统计（管理员）"""
    result = business_declaration_service.get_stats()
    if result.get("success"):
        return response.success(data=result.get("stats"))
    return response.fail(message=result.get("error", "获取统计失败"))


# ============================================================================
# 辅助接口
# ============================================================================

@router.get(
    "/meta/types",
    summary="获取申报类型列表",
    description="获取支持的申报类型列表，包含 license_application（工商执照申请）。",
    responses={
        200: {"description": "获取成功"},
        401: {"description": "未授权"},
    }
)
async def get_declaration_types(
    current_user: dict = Depends(get_current_user_info)
):
    """获取申报类型列表（含新增 license_application）"""
    types = [
        {"code": code, "name": DeclarationType.get_name(code)}
        for code in DeclarationType.all()
    ]
    return response.success(data={"types": types})


@router.get(
    "/meta/statuses",
    summary="获取申报状态列表",
    description="获取支持的申报状态列表。",
    responses={
        200: {"description": "获取成功"},
        401: {"description": "未授权"},
    }
)
async def get_declaration_statuses(
    current_user: dict = Depends(get_current_user_info)
):
    """获取申报状态列表"""
    statuses = [
        {"code": code, "name": DeclarationStatus.get_name(code)}
        for code in DeclarationStatus.all()
    ]
    return response.success(data={"statuses": statuses})
