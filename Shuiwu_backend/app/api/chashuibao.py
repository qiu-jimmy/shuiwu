"""
查税宝经营风险报告 API 路由
提供查税宝第三方服务对接功能
"""
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.middleware.member_permission import require_member_features
from app.schemas.chashuibao import (
    ChashuibaoAuthorizationRequest,
    ChashuibaoAuthorizationResponse,
    ChashuibaoUploadReportRequest,
    ChashuibaoGetReportRequest,
    ChashuibaoReportData,
    ChashuibaoReportResponse,
    ChashuibaoReportNotifyData,
    ChashuibaoGeneratePanoramicRequest,
    ChashuibaoGeneratePanoramicResponse,
    ChashuibaoGetPanoramicRequest,
    ChashuibaoGetPanoramicResponse,
    ChashuibaoPanoramicData,
)
from app.services.chashuibao import chashuibao_service
from app.utils.response import response
from app.utils.dependencies import require_current_user, get_current_user
from app.infra.logging_config import get_logger

logger = get_logger("app.api.chashuibao")

router = APIRouter(prefix="/api/chashuibao", tags=["查税宝经营风险报告"])


@router.post(
    "/authorization",
    summary="获取授权链接",
    description="""
    自动生成-获取授权链接接口

    **功能说明：**
    - 获取税局账号授权的 H5 链接
    - 用户通过链接进行税局账号密码授权
    - 授权完成后自动生成报告

    **所需参数：**
    - taxpayerId: 纳税人识别号（加密）
    - companyName: 企业名称（加密）
    - cburl: 授权完成回调页面
    - reportType: 报告类型，默认 2（经营风险报告）
    - year: 年度（可选）
    - quarter: 季度（可选）

    **返回信息：**
    - orderNo: 订单号（唯一标识）
    - initialUrl: 授权链接（H5链接）

    **注意：**
    - 打开授权链接后切勿重复授权
    - 签名字段需要参与签名
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
    privileges=["business_risk"],
    quotas={"business_risk": 1}
)
async def get_authorization_url(
    request: Request,
    request_data: ChashuibaoAuthorizationRequest,
    current_user: str = Depends(require_current_user)
):
    """获取授权链接"""
    try:
        quarter_section_data = [qs.model_dump() for qs in request_data.quarter_section] if request_data.quarter_section else None
        logger.info(
            f"用户 {current_user} 请求获取授权链接, "
            f"taxpayer_id={request_data.taxpayer_id}, "
            f"company_name={request_data.company_name}, "
            f"report_type={request_data.report_type}, "
            f"cburl={request_data.cburl}, "
            f"quarterSection={quarter_section_data}"
        )

        result = await chashuibao_service.get_authorization_url(
            taxpayer_id=request_data.taxpayer_id,
            company_name=request_data.company_name,
            cburl=request_data.cburl,
            report_type=request_data.report_type,
            quarter_section=quarter_section_data,
            report_logo=request_data.report_logo,
            watermark=request_data.watermark,
            cover_url=request_data.cover_url,
            is_anonymity=request_data.is_anonymity,
        )

        # 授权成功后，将记录写入数据库
        order_no = result.get("orderNo")
        if order_no:
            from app.services.chashuibao.business_risk_repository import business_risk_repository
            business_risk_repository.create_report(
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


@router.post(
    "/upload_report",
    summary="手动上传报表",
    description="""
    手动生成-上传报表接口

    **功能说明：**
    - 手动上传税务报表文件
    - 上传后自动生成经营风险报告

    **所需参数：**
    - firmName: 企业名称
    - year: 年度
    - quarter: 季度
    - phone: 用户手机号
    - taxpayerNo: 纳税人识别号
    - reportNo: 报告编号（唯一，长度32）
    - accountingCriterionId: 会计准则编码
    - taxpayerType: 纳税人类型编码
    - taxpayerName: 企业名称
    - zzsFileBs/sdsFileBs/cbFileBs: 文件标识
    - 文件 URL（增值税、所得税、财报）

    **注意：**
    - 参与签名字段：firmName、taxpayerNo、thirdPartyId
    """,
    responses={
        200: {
            "description": "上传成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "上传报表成功",
                        "data": {
                            "success": True,
                            "message": "上传成功"
                        }
                    }
                }
            }
        }
    }
)
@require_member_features(
    privileges=["business_risk"],
    quotas={"business_risk": 1}
)
async def upload_report(
    request: Request,
    request_data: ChashuibaoUploadReportRequest,
    current_user: str = Depends(require_current_user)
):
    """手动上传报表"""
    try:
        logger.info(f"用户 {current_user} 请求上传报表: {request_data.report_no}")

        result = await chashuibao_service.upload_report(
            firm_name=request_data.firm_name,
            year=request_data.year,
            quarter=request_data.quarter,
            phone=request_data.phone,
            taxpayer_no=request_data.taxpayer_no,
            report_no=request_data.report_no,
            accounting_criterion_id=request_data.accounting_criterion_id,
            taxpayer_type=request_data.taxpayer_type,
            taxpayer_name=request_data.taxpayer_name,
            zzs_file_bs=request_data.zzs_file_bs,
            sds_file_bs=request_data.sds_file_bs,
            cb_file_bs=request_data.cb_file_bs,
            zzs=request_data.zzs,
            zzs_zb=request_data.zzs_zb,
            zzs_fb1=request_data.zzs_fb1,
            zzs_fb2=request_data.zzs_fb2,
            zzs_fb3=request_data.zzs_fb3,
            zzs_fb4=request_data.zzs_fb4,
            zzs_jmmx=request_data.zzs_jmmx,
            sds=request_data.sds,
            sds_zb=request_data.sds_zb,
            sds_fb1=request_data.sds_fb1,
            sds_fb2=request_data.sds_fb2,
            sds_fb3=request_data.sds_fb3,
            cb=request_data.cb,
            cb_zcfz=request_data.cb_zcfz,
            cb_lr=request_data.cb_lr,
            cb_xjll=request_data.cb_xjll,
        )

        return response.success(
            message="上传报表成功",
            data=result
        )

    except Exception as e:
        logger.error(f"上传报表失败: {e}")
        return response.fail(message=f"上传报表失败: {str(e)}")


@router.get(
    "/report_data",
    summary="获取指标报告数据",
    description="""
    获取指标报告数据接口

    **功能说明：**
    - 根据报告编号获取已生成的经营风险报告数据

    **所需参数：**
    - reportNo: 报告编号（上传报表接口传的报告编号/授权连接接口返回的orderNo）

    **返回数据：**
    - firmInfo: 企业概况
    - fxList: 风险列表
    - taxInfo: 申报纳税信息
    - cwzkfx: 财务状况分析
    - lrbfx: 利润表分析
    - xjll: 现金流量表分析
    - zcfzbfx: 资产负债表分析
    - reportUrl: 指标分析报告url
    - financialReport: 财务报表url

    **注意：**
    - 参与签名字段：reportNo、thirdPartyId
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
                            "firmInfo": {
                                "taxpayerName": "企业名称",
                                "taxpayerNo": "91330100MA2XXX00XX",
                                "industry": "行业"
                            },
                            "fxList": [],
                            "reportUrl": "https://example.com/report.pdf"
                        }
                    }
                }
            }
        }
    }
)
async def get_report_data(
    report_no: str,
    current_user: str = Depends(require_current_user)
):
    """获取指标报告数据"""
    try:
        logger.info(f"用户 {current_user} 请求获取报告数据: {report_no}")

        result = await chashuibao_service.get_report_data(report_no=report_no)

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
    报告生成完成通知接口（查税宝主动调用）

    **功能说明：**
    - 查税宝在报告生成完成后会主动调用此接口
    - 需要在查税宝后台配置回调地址

    **回调参数：**
    - orderNo: 订单号
    - state: 成功状态（0-失败，1-成功）
    - reportType: 报告类型（2-经营报告）

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
    notify_data: ChashuibaoReportNotifyData,
    request: Request
):
    """报告生成完成通知回调"""
    try:
        logger.info(
            f"收到报告生成完成通知: orderNo={notify_data.order_no}, "
            f"state={notify_data.state}, reportType={notify_data.report_type}"
        )

        # TODO: 验证签名（如果查税宝提供签名）
        # sign = request.query_params.get('sign')
        # if sign:
        #     public_key = os.getenv('CHASHUIBAO_PUBLIC_KEY', '')
        #     is_valid = chashuibao_service.verify_notify_signature(
        #         notify_data.dict(), sign, public_key
        #     )
        #     if not is_valid:
        #         logger.warning("回调签名验证失败")
        #         return {"code": "1", "message": "签名验证失败"}

        # 处理回调逻辑：根据 orderNo 更新数据库状态
        from app.services.chashuibao.business_risk_repository import business_risk_repository

        if notify_data.order_no:
            new_status = "success" if str(notify_data.state) == "1" else "failed"
            error_message = None if new_status == "success" else f"查税宝回调状态: {notify_data.state}"

            business_risk_repository.update_report_status(
                order_no=notify_data.order_no,
                status=new_status,
                error_message=error_message,
                callback_state=str(notify_data.state),
            )

        logger.info(f"报告生成完成通知处理成功: {notify_data.order_no}")

        return {"code": "0", "message": "success"}

    except Exception as e:
        logger.error(f"处理报告生成完成通知失败: {e}")
        return {"code": "1", "message": str(e)}


@router.get(
    "/config",
    summary="获取查税宝配置信息",
    description="""
    获取查税宝服务配置信息（用于调试）

    **返回信息：**
    - baseUrl: 查税宝服务地址
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
    """获取查税宝配置信息"""
    try:
        return response.success(
            message="获取配置成功",
            data={
                "baseUrl": chashuibao_service.base_url,
                "thirdPartyId": chashuibao_service.third_party_id,
            }
        )
    except Exception as e:
        logger.error(f"获取配置失败: {e}")
        return response.fail(message=f"获取配置失败: {str(e)}")


# ============ 全景报告接口 ============

@router.post(
    "/panoramic/generate",
    summary="生成全景报告",
    description="""
    生成全景报告接口

    **功能说明：**
    - 根据纳税人识别号和企业名称生成全景报告
    - 报告生成完成后会通过回调接口通知

    **所需参数（至少填一个）：**
    - taxpayerNo: 纳税识别号（可选，与企业名称至少填一个）
    - taxpayerName: 公司名称（可选，与纳税人识别号至少填一个）
    - reportLogo: 封面logo URL（可选）
    - watermark: 水印 URL（可选）
    - coverUrl: 封面 URL（可选）
    - isAnonymity: 是否匿名（可选）

    **返回信息：**
    - reportId: 报告ID

    **注意：**
    - 签名字段需要参与签名
    """,
    responses={
        200: {
            "description": "生成成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "生成全景报告成功",
                        "data": {
                            "report_id": 123456
                        }
                    }
                }
            }
        }
    }
)
@require_member_features(
    privileges=["panorama"],
    quotas={"panorama": 1}
)
async def generate_panoramic_report(
    request: Request,
    request_data: ChashuibaoGeneratePanoramicRequest,
    current_user: str = Depends(require_current_user)
):
    """生成全景报告"""
    try:
        user_id = current_user  # current_user 已经是字符串类型的 user_id
        logger.info(f"用户 {user_id} (type: {type(user_id)}) 请求生成全景报告: {request_data.taxpayer_name}")

        result = await chashuibao_service.generate_panoramic_report(
            user_id=user_id,
            taxpayer_no=request_data.taxpayer_no,
            taxpayer_name=request_data.taxpayer_name,
            report_logo=request_data.report_logo,
            watermark=request_data.watermark,
            cover_url=request_data.cover_url,
            is_anonymity=request_data.is_anonymity,
        )

        logger.info(f"生成全景报告服务返回结果: {result}")

        return response.success(
            message="生成全景报告请求已提交，请使用返回的 id 轮询报告状态",
            data=result
        )

    except Exception as e:
        logger.error(f"生成全景报告失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return response.fail(message=f"生成全景报告失败: {str(e)}")


@router.post(
    "/panoramic/notify",
    summary="全景报告生成完成通知回调",
    description="""
    全景报告生成完成通知接口（查税宝主动调用）

    **功能说明：**
    - 查税宝在全景报告生成完成后会主动调用此接口
    - 需要在查税宝后台配置回调地址

    **回调参数：**
    - reportId: 报告id
    - state: 成功状态（0-失败，1-成功）
    - reportType: 报告类型（3-全景报告）
    - url: 报告url（可选）

    **返回格式：**
    - code: 1：失败，0：成功
    - message: 状态信息

    **注意：**
    - 此接口需要公网可访问
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
async def panoramic_report_notify_callback(request: Request):
    """全景报告生成完成通知回调（公开接口，无需认证）"""
    try:
        # 直接获取原始 JSON 数据，不进行验证
        notify_data = await request.json()

        logger.info(
            f"收到全景报告生成完成通知: {notify_data}"
        )

        # 调用服务层处理回调
        success = chashuibao_service.handle_panoramic_report_callback(
            chashuibao_report_id=int(str(notify_data.get("reportId"))),
            state=str(notify_data.get("state", "")),
            report_type=str(notify_data.get("reportType", "")),
            url=notify_data.get("url"),
        )

        if success:
            logger.info(f"全景报告生成完成通知处理成功: {notify_data.get('reportId')}")
            return {"code": "0", "message": "success"}
        else:
            logger.warning(f"全景报告生成完成通知处理失败: {notify_data.get('reportId')}")
            return {"code": "1", "message": "处理失败"}

    except Exception as e:
        logger.error(f"处理全景报告生成完成通知失败: {e}")
        return {"code": "1", "message": str(e)}


@router.get(
    "/panoramic/data",
    summary="获取全景报告数据",
    description="""
    获取全景报告数据接口

    **功能说明：**
    - 根据报告ID获取已生成的全景报告数据

    **所需参数：**
    - reportId: 报告id（生成全景报告返回的reportId）

    **返回数据：**
    - 评价信息（综合评价、评分、六维评价图）
    - 描述信息（企业标识、官网、介绍）
    - 登记信息（企业名称、法人、状态等）
    - 控制信息（实际控制人）
    - 统计信息（投资、变更、任职统计）
    - 详细列表（股东、人员、变更、抵押、清算等）

    **注意：**
    - 参与签名字段：reportId、thirdPartyId
    """,
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "获取全景报告数据成功",
                        "data": {
                            "evaluateSynthetical": "综合评价内容",
                            "registerName": "企业名称",
                            "shareholderList": []
                        }
                    }
                }
            }
        }
    }
)
async def get_panoramic_report_data(
    report_id: int,
    current_user: str = Depends(require_current_user)
):
    """获取全景报告数据"""
    try:
        logger.info(f"用户 {current_user} 请求获取全景报告数据: {report_id}")

        result = await chashuibao_service.get_panoramic_report_data(report_id=report_id)

        return response.success(
            message="获取全景报告数据成功",
            data=result
        )

    except Exception as e:
        logger.error(f"获取全景报告数据失败: {e}")
        return response.fail(message=f"获取全景报告数据失败: {str(e)}")


@router.get(
    "/panoramic/status/{report_record_id}",
    summary="轮询全景报告状态",
    description="""
    轮询全景报告生成状态接口

    **功能说明：**
    - 前端使用此接口轮询报告生成状态
    - 返回报告当前状态、URL等信息

    **路径参数：**
    - report_record_id: 数据库记录ID（生成全景报告接口返回的 id）

    **返回状态：**
    - pending: 生成中
    - success: 生成成功
    - failed: 生成失败

    **轮询建议：**
    - 每 3-5 秒轮询一次
    - 如果状态不是 pending，停止轮询
    - 如果超过 5 分钟仍是 pending，视为超时
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
                            "id": 1,
                            "report_id": 123456,
                            "taxpayer_no": "91330100MA2XXX00XX",
                            "taxpayer_name": "企业名称",
                            "status": "success",
                            "report_url": "https://example.com/report.pdf",
                            "error_message": None,
                            "created_at": "2024-01-01T00:00:00",
                            "completed_at": "2024-01-01T00:05:00",
                            "has_data": True
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
async def get_panoramic_report_status(
    report_record_id: int,
    current_user: str = Depends(require_current_user)
):
    """轮询全景报告生成状态"""
    try:
        status_info = chashuibao_service.get_panoramic_report_status(report_record_id)

        if not status_info:
            return response.fail(message="报告记录不存在")

        return response.success(
            message="获取状态成功",
            data=status_info
        )

    except Exception as e:
        logger.error(f"获取全景报告状态失败: {e}")
        return response.fail(message=f"获取全景报告状态失败: {str(e)}")


@router.get(
    "/panoramic/list",
    summary="获取用户的全景报告列表",
    description="""
    获取当前用户的全景报告列表

    **查询参数：**
    - page: 页码（默认 1）
    - page_size: 每页数量（默认 20）
    - status: 状态筛选（可选：pending、success、failed）
    - taxpayer_no: 纳税人识别号筛选（可选）
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
                            "total": 10,
                            "page": 1,
                            "page_size": 20,
                            "reports": [
                                {
                                    "id": 1,
                                    "user_id": 123,
                                    "taxpayer_no": "91330100MA2XXX00XX",
                                    "taxpayer_name": "企业名称",
                                    "report_id": 123456,
                                    "status": "success",
                                    "created_at": "2024-01-01T00:00:00"
                                }
                            ]
                        }
                    }
                }
            }
        }
    }
)
async def list_panoramic_reports(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    taxpayer_no: Optional[str] = None,
    current_user: str = Depends(require_current_user)
):
    """获取用户的全景报告列表"""
    try:
        from app.services.chashuibao.panoramic_report_repository import panoramic_report_repository

        user_id = current_user  # current_user 已经是字符串类型的 user_id
        result = panoramic_report_repository.list_reports_by_user(
            user_id=user_id,
            page=page,
            page_size=page_size,
            status=status,
            taxpayer_no=taxpayer_no,
        )

        return response.success(
            message="获取报告列表成功",
            data=result
        )

    except Exception as e:
        logger.error(f"获取全景报告列表失败: {e}")
        return response.fail(message=f"获取全景报告列表失败: {str(e)}")


@router.get("/debug/user")
async def debug_user(current_user: str = Depends(require_current_user)):
    """调试：返回当前用户信息"""
    return response.success(
        message="调试信息",
        data={
            "current_user": current_user,
            "type": str(type(current_user)),
            "repr": repr(current_user)
        }
    )


# ============ 经营风险报告状态/列表接口 ============


@router.get(
    "/business-risk/status/{order_no}",
    summary="查询经营风险报告状态",
    description="""
    轮询经营风险报告生成状态

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
async def get_business_risk_status(
    order_no: str,
    current_user: str = Depends(require_current_user)
):
    """查询经营风险报告状态"""
    try:
        from app.services.chashuibao.business_risk_repository import business_risk_repository

        report = business_risk_repository.get_report_by_order_no(order_no)
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
        logger.error(f"获取经营风险报告状态失败: {e}")
        return response.fail(message=f"获取报告状态失败: {str(e)}")


@router.get(
    "/business-risk/list",
    summary="获取用户的经营风险报告列表",
    description="""
    获取当前用户的经营风险报告历史列表

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
async def list_business_risk_reports(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    current_user: str = Depends(require_current_user)
):
    """获取用户的经营风险报告列表"""
    try:
        from app.services.chashuibao.business_risk_repository import business_risk_repository

        result = business_risk_repository.list_reports_by_user(
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
        logger.error(f"获取经营风险报告列表失败: {e}")
        return response.fail(message=f"获取报告列表失败: {str(e)}")
