"""
发票穿透报告 API 路由
提供发票穿透第三方服务对接功能
"""
from typing import Optional

from fastapi import APIRouter, Depends, Request, Query

from app.schemas.invoice_penetration import (
    InvoiceAuthorizationRequest,
    InvoiceAuthorizationResponse,
    InvoiceGetReportRequest,
    InvoiceReportData,
    InvoiceReportResponse,
    InvoiceReportNotifyData,
)
from app.services.invoice_penetration import invoice_penetration_service
from app.utils.response import response
from app.utils.dependencies import require_current_user
from app.middleware.member_permission import require_member_features
from app.infra.logging_config import get_logger

logger = get_logger("app.api.invoice_penetration")

router = APIRouter(prefix="/api/invoice-penetration", tags=["发票穿透报告"])


@router.post(
    "/authorization",
    summary="获取授权链接",
    description="""
    发票穿透报告获取授权链接接口

    **功能说明：**
    - 获取税局账号授权的 H5 链接
    - 用户通过链接进行税局账号密码授权
    - 授权完成后自动生成发票穿透报告

    **会员权益要求：**
    - 功能权限：enable_invoice_penetration（套餐配置）
    - 配额要求：每次消耗1次发票穿透配额

    **所需参数：**
    - taxpayerId: 纳税人识别号（明文，后端自动处理加密）
    - companyName: 企业名称（明文，后端自动处理加密）
    - cburl: 授权完成回调页面
    - reportType: 报告类型，默认 1（发票穿透）
    - beginDate: 开始时间（例202309）
    - overDate: 结束时间（例202408）

    **返回信息：**
    - orderNo: 订单号（唯一标识）
    - initialUrl: 授权链接（H5链接）

    **注意：**
    - 报告数据只取近36个月
    - 开始时间和结束时间间隔为12个月
    - 打开授权链接后切勿重复授权
    """,
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "获取授权链接成功",
                        "data": {
                            "orderNo": "unique_order_no",
                            "initialUrl": "https://example.com/authorize?..."
                        }
                    }
                }
            }
        }
    }
)
@require_member_features(
    privileges=["invoice_penetration"],
    quotas={"invoice_penetration": 1}
)
async def get_authorization_url(
    request: Request,
    request_data: InvoiceAuthorizationRequest,
    current_user: str = Depends(require_current_user)
):
    """获取授权链接"""
    try:
        logger.info(f"用户 {current_user} 请求获取发票穿透授权链接")

        # 获取配额检查结果
        quota_check = getattr(request.state, "member_quota_check", {})
        remaining = quota_check.get("remaining", -1)

        result = await invoice_penetration_service.get_authorization_url(
            taxpayer_id=request_data.taxpayer_id,
            company_name=request_data.company_name,
            cburl=request_data.cburl,
            report_type=request_data.report_type,
            begin_date=request_data.begin_date,
            over_date=request_data.over_date,
            report_logo=request_data.report_logo,
            watermark=request_data.watermark,
            cover_url=request_data.cover_url,
            is_anonymity=request_data.is_anonymity,
        )

        # 授权成功后，将记录写入数据库
        order_no = result.get("orderNo")
        if order_no:
            from app.services.invoice_penetration.invoice_penetration_repository import invoice_penetration_repository
            invoice_penetration_repository.create_report(
                user_id=current_user,
                taxpayer_no=request_data.taxpayer_id,
                company_name=request_data.company_name,
                order_no=order_no,
            )

        return response.success(
            message="获取授权链接成功",
            data=result
        )

    except Exception as e:
        logger.error(f"获取授权链接失败: {e}")
        return response.fail(message=f"获取授权链接失败: {str(e)}")


@router.get(
    "/report_data",
    summary="获取报告数据",
    description="""
    获取发票穿透报告数据接口

    **功能说明：**
    - 根据订单号获取已生成的发票穿透报告数据

    **所需参数：**
    - taxpayerId: 纳税人识别号（明文，后端自动处理加密）
    - companyName: 企业名称（明文，后端自动处理加密）
    - orderNo: 订单号
    - dataType: 数据类型（1-数据，2-报告url）

    **返回数据：**
    - invoiceFirmInfoAllMap: 企业基本信息
    - invoiceEnterpriseAllMap: 发票分析
    - invoiceFinancialAnalysisAllMap: 财务风险评估
    - invoiceTaxRiskAssessmentAllMap: 税务风险评估
    - invoiceIntegratedRiskAssessmentAllMap: 财税票综合风险评估

    **注意：**
    - 参与签名字段：thirdPartyId, taxpayerId, companyName, orderNo
    - 如选择 dataType=2，则直接返回 PDF 的 URL 链接
    """,
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "获取报告数据成功",
                        "data": {
                            "invoiceFirmInfoAllMap": {},
                            "invoiceEnterpriseAllMap": {}
                        }
                    }
                }
            }
        }
    }
)
async def get_report_data(
    taxpayer_id: str = Query(..., alias="taxpayerId", description="纳税人识别号（明文）"),
    company_name: str = Query(..., alias="companyName", description="企业名称（明文）"),
    order_no: str = Query(..., alias="orderNo", description="订单号"),
    data_type: int = Query(2, alias="dataType", description="数据类型：1-数据，2-报告url"),
    current_user: str = Depends(require_current_user)
):
    """获取报告数据"""
    try:
        logger.info(f"用户 {current_user} 请求获取发票穿透报告数据: {order_no}")

        result = await invoice_penetration_service.get_report_data(
            taxpayer_id=taxpayer_id,
            company_name=company_name,
            order_no=order_no,
            data_type=data_type
        )

        return response.success(
            message="获取报告数据成功",
            data=result
        )

    except Exception as e:
        logger.error(f"获取报告数据失败: {e}")
        return response.fail(message=f"获取报告数据失败: {str(e)}")


@router.post(
    "/notify/callback",
    summary="报告生成完成通知回调",
    description="""
    发票穿透报告生成完成通知接口（发票穿透服务主动调用）

    **功能说明：**
    - 发票穿透服务在报告生成完成后会主动调用此接口
    - 需要在发票穿透后台配置回调地址

    **回调参数：**
    - orderNo: 订单号
    - state: 成功状态（0-失败，1-成功）
    - reportType: 报告类型（1-发票穿透）

    **返回格式：**
    - code: 1：失败，0：成功
    - message: 状态信息

    **注意：**
    - 此接口需要公网可访问
    - 建议对回调进行验签
    """,
    responses={
        200: {
            "description": "处理成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": "0",
                        "message": "success"
                    }
                }
            }
        }
    }
)
async def report_notify_callback(
    request: Request
):
    """报告生成完成通知回调，兼容 JSON 和 form 表单两种提交方式"""
    try:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            data = await request.json()
        else:
            # form 表单提交
            form = await request.form()
            data = dict(form)

        logger.info(f"发票穿透回调原始数据: content_type={content_type}, data={data}")

        notify_data = InvoiceReportNotifyData(**data)

        logger.info(
            f"收到发票穿透报告生成完成通知: orderNo={notify_data.order_no}, "
            f"state={notify_data.state}, reportType={notify_data.report_type}"
        )

        # 处理回调逻辑：根据 orderNo 更新数据库状态
        from app.services.invoice_penetration.invoice_penetration_repository import invoice_penetration_repository

        if notify_data.order_no:
            new_status = "success" if str(notify_data.state) == "1" else "failed"
            error_message = None if new_status == "success" else f"查税宝回调状态: {notify_data.state}"
            report_url = None

            if new_status == "success":
                report_record = invoice_penetration_repository.get_report_by_order_no(notify_data.order_no)
                if report_record:
                    try:
                        report_data = await invoice_penetration_service.get_report_data(
                            taxpayer_id=report_record["taxpayer_no"],
                            company_name=report_record["company_name"],
                            order_no=notify_data.order_no,
                            data_type=2,
                        )
                        if isinstance(report_data, dict):
                            report_url = report_data.get("reportUrl") or report_data.get("url")
                        elif isinstance(report_data, str):
                            report_url = report_data
                        logger.info(f"回调成功后获取报告URL: order_no={notify_data.order_no}, report_url={report_url}")
                    except Exception as e:
                        logger.error(f"回调成功但获取报告数据失败: order_no={notify_data.order_no}, error={e}")
                        error_message = f"获取报告数据失败: {e}"
                else:
                    logger.warning(f"回调成功但未找到报告记录: order_no={notify_data.order_no}")

            invoice_penetration_repository.update_report_status(
                order_no=notify_data.order_no,
                status=new_status,
                report_url=report_url,
                error_message=error_message,
                callback_state=str(notify_data.state),
            )

        logger.info(f"发票穿透报告生成完成通知处理成功: {notify_data.order_no}")

        return {"code": "0", "message": "success"}

    except Exception as e:
        logger.error(f"处理报告生成完成通知失败: {e}")
        return {"code": "1", "message": str(e)}


@router.get(
    "/config",
    summary="获取发票穿透配置信息",
    description="""
    获取发票穿透服务配置信息（用于调试）

    **返回信息：**
    - baseUrl: 发票穿透服务地址
    - thirdPartyId: 第三方 ID
    """,
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "获取配置成功",
                        "data": {
                            "baseUrl": "https://testcsbplus.dianzuanmao.com",
                            "thirdPartyId": "your_token"
                        }
                    }
                }
            }
        }
    }
)
async def get_config(current_user: str = Depends(require_current_user)):
    """获取发票穿透配置信息"""
    try:
        return response.success(
            message="获取配置成功",
            data={
                "baseUrl": invoice_penetration_service.base_url,
                "thirdPartyId": invoice_penetration_service.third_party_id,
            }
        )
    except Exception as e:
        logger.error(f"获取配置失败: {e}")
        return response.fail(message=f"获取配置失败: {str(e)}")


# ============ 前端对接新增接口 ============


@router.get(
    "/status/{order_no}",
    summary="查询发票穿透报告状态",
    description="""
    轮询发票穿透报告生成状态

    **路径参数：**
    - order_no: 订单号（来自授权接口返回的 orderNo）

    **返回状态：**
    - pending: 生成中
    - success: 生成成功
    - failed: 生成失败

    **轮询建议：**
    - 每 5 秒轮询一次
    - 如果状态不是 pending，停止轮询
    - 超过 10 分钟仍是 pending，视为超时
    """,
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "获取状态成功",
                        "data": {
                            "order_no": "S_xxxxx",
                            "company_name": "企业名称",
                            "taxpayer_no": "91330100MA2XXX00XX",
                            "status": "success",
                            "report_url": "https://example.com/report.pdf",
                            "created_at": "2024-01-01T00:00:00",
                            "completed_at": "2024-01-01T00:05:00"
                        }
                    }
                }
            }
        },
        404: {
            "description": "报告记录不存在",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "报告记录不存在"
                    }
                }
            }
        }
    }
)
async def get_report_status(
    order_no: str,
    current_user: str = Depends(require_current_user)
):
    """查询发票穿透报告状态"""
    try:
        from app.services.invoice_penetration.invoice_penetration_repository import invoice_penetration_repository

        report = invoice_penetration_repository.get_report_by_order_no(order_no)
        if not report:
            return response.fail(message="报告记录不存在")

        return response.success(
            message="获取状态成功",
            data={
                "order_no": report.get("order_no"),
                "company_name": report.get("company_name"),
                "taxpayer_no": report.get("taxpayer_no"),
                "status": report.get("status"),
                "report_url": report.get("report_url"),
                "created_at": report.get("created_at"),
                "completed_at": report.get("completed_at"),
            }
        )

    except Exception as e:
        logger.error(f"获取发票穿透报告状态失败: {e}")
        return response.fail(message=f"获取报告状态失败: {str(e)}")


@router.get(
    "/list",
    summary="获取用户的发票穿透报告列表",
    description="""
    获取当前用户的发票穿透报告历史列表

    **查询参数：**
    - page: 页码（默认 1）
    - page_size: 每页条数（默认 20）
    - status: 状态筛选（可选：pending / success / failed，空则全部）
    """,
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "获取报告列表成功",
                        "data": {
                            "reports": [
                                {
                                    "id": 1,
                                    "order_no": "S_xxxxx",
                                    "company_name": "企业名称",
                                    "taxpayer_no": "91330100MA2XXX00XX",
                                    "status": "success",
                                    "report_url": "https://example.com/report.pdf",
                                    "created_at": "2024-01-01T00:00:00"
                                }
                            ],
                            "total": 100,
                            "page": 1,
                            "page_size": 20
                        }
                    }
                }
            }
        }
    }
)
async def list_reports(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    current_user: str = Depends(require_current_user)
):
    """获取用户的发票穿透报告列表"""
    try:
        from app.services.invoice_penetration.invoice_penetration_repository import invoice_penetration_repository

        result = invoice_penetration_repository.list_reports_by_user(
            user_id=current_user,
            page=page,
            page_size=page_size,
            status=status,
        )

        return response.success(
            message="获取报告列表成功",
            data=result
        )

    except Exception as e:
        logger.error(f"获取发票穿透报告列表失败: {e}")
        return response.fail(message=f"获取报告列表失败: {str(e)}")
