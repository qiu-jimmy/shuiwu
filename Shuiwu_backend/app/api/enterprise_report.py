"""
企业体检报告 API 路由
提供企业体检报告生成功能
"""
from typing import Optional

from fastapi import APIRouter, Depends

from app.schemas.enterprise_report import (
    EnterpriseReportGenerateRequest,
    EnterpriseReportResponse,
    EnterpriseReportStatusResponse,
)
from app.services.enterprise_report import enterprise_report_service
from app.utils.response import response
from app.utils.dependencies import require_current_user
from app.infra.logging_config import get_logger

logger = get_logger("app.api.enterprise_report")

router = APIRouter(prefix="/api/enterprise_report", tags=["企业体检报告"])

# 状态变量已废弃，解决多进程下状态不一致的问题
# _active_generations = 0

@router.post(
    "/generate",
    summary="生成企业体检报告",
    description="""
根据企业名称自动查询企查查API并生成完整的企业体检报告Word文档并上传到OSS。

**功能特性：**
- 自动调用企查查API查询企业信息
- 基于 Qwen Plus AI 模型的企业体检报告生成（11个专业 Agent 并行协作）
- 包含8个主要章节：企业概述、重点事项、评估标准、改进建议等
- 自动生成报告编号（UUID格式，支持并发）
- 自动上传到阿里云OSS
- 返回OSS文件URL
- 支持多用户同时生成报告

**所需参数：**
- company_name: 企业名称（必填）
- credit_code: 统一社会信用代码（可选，用于精确匹配）

**返回信息：**
- report_number: 报告编号
- file_url: OSS文件URL（可直接下载）
- file_name: 文件名
- project_name: 企业名称
- generated_at: 生成时间
""",
    responses={
        200: {
            "description": "生成成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "企业体检报告生成成功",
                        "data": {
                            "report_number": "DragonAI-202601-S-ce9e72c0",
                            "file_url": "https://bucket.oss-cn-hangzhou.aliyuncs.com/enterprise_reports/user123/2026/01/企业名称_DragonAI-202601-S-ce9e72c0.docx",
                            "file_name": "企业名称_DragonAI-202601-S-ce9e72c0.docx",
                            "project_name": "企业名称",
                            "generated_at": "2026-01-21 14:30:00"
                        }
                    }
                }
            }
        },
        400: {
            "description": "请求参数错误",
            "content": {
                "application/json": {
                    "examples": {
                        "empty_content": {
                            "summary": "企业资料内容为空",
                            "value": {
                                "code": 0,
                                "message": "企业资料内容不能为空",
                                "data": None
                            }
                        },
                        "no_api_key": {
                            "summary": "未配置API Key",
                            "value": {
                                "code": 0,
                                "message": "未配置 Qwen Plus API Key",
                                "data": None
                            }
                        }
                    }
                }
            }
        },
        500: {
            "description": "服务器内部错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "生成企业体检报告时发生错误",
                        "data": None
                    }
                }
            }
        }
    }
)
async def generate_enterprise_report(
        request: EnterpriseReportGenerateRequest,
        current_user: str = Depends(require_current_user)
):
    """生成企业体检报告（支持并发）"""
    try:
        logger.info(f"用户 {current_user} 请求生成企业体检报告: {request.company_name}")

        # 生成报告（传入 user_id 用于 OSS 存储路径）
        result = await enterprise_report_service.generate_report(
            company_name=request.company_name,
            credit_code=request.credit_code,
            user_id=current_user
        )

        logger.info(f"企业体检报告生成成功: {result['report_number']}")

        return response.success(
            message="企业体检报告生成成功",
            data=result
        )

    except ValueError as e:
        logger.warning(f"生成企业体检报告失败（参数错误）: {e}")
        return response.fail(message=str(e))

    except Exception as e:
        logger.error(f"生成企业体检报告失败: {e}")
        from app.utils.exception_logger import log_exception
        log_exception(e, extra_info={"company_name": request.company_name})
        return response.fail(message="生成企业体检报告时发生错误")


@router.get(
    "/status",
    summary="获取报告生成状态",
    description="""
获取当前报告生成状态，包括正在生成的任务数量。

**返回信息：**
- active_generations: 正在生成的报告数量
- is_generating: 是否正在生成
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
                            "active_generations": 0,
                            "is_generating": False
                        }
                    }
                }
            }
        }
    }
)
async def get_report_status(current_user: str = Depends(require_current_user)):
    """获取报告生成状态 (由于多进程架构，已废弃简单的内存计数器，前端直接轮询具体的生成任务即可)"""
    try:
        return response.success(
            message="获取状态成功",
            data={
                "active_generations": 0,
                "is_generating": False
            }
        )
    except Exception as e:
        logger.error(f"获取报告状态失败: {e}")
        return response.fail(message="获取报告状态时发生错误")
