"""
问题反馈系统 - 用户端 API 路由
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, Query

from app.schemas.feedback import (
    FeedbackSubmitRequest,
    FeedbackResponse,
)
from app.services.feedback.feedback_service import feedback_service
from app.utils.response import response
from app.utils.dependencies import require_current_user

router = APIRouter(prefix="/api/feedback", tags=["问题反馈-用户端"])


# ============================================================================
# 用户端接口
# ============================================================================


@router.post(
    "/submit",
    summary="提交问题反馈",
    description="""
    用户提交问题反馈接口。

    **反馈类型：**
    - `bug`: 系统错误（登录失败、页面崩溃、数据异常等）
    - `feature`: 功能建议（希望添加的功能或优化建议）
    - `complaint`: 投诉（服务态度、响应速度等）
    - `other`: 其他问题

    **提交流程：**
    1. 用户选择问题类型
    2. 填写问题描述（1-5000字符）
    3. 可选上传相关截图（支持多张）
    4. 系统生成反馈ID
    5. 管理员会在后台收到通知

    **注意事项：**
    - 问题描述必填，建议详细描述问题复现步骤
    - 图片为可选项，建议提供问题截图以便快速定位
    - 提交后可在"我的反馈"中查看处理进度

    **认证要求：** 需要在请求头中携带有效的 JWT token
    """,
    responses={
        200: {
            "description": "提交成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "反馈提交成功，我们会尽快处理",
                        "data": {
                            "feedback_id": "FB1234567890ABCDE"
                        }
                    }
                }
            }
        },
        400: {
            "description": "提交失败",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_type": {
                            "summary": "问题类型无效",
                            "value": {
                                "code": 0,
                                "message": "提交反馈失败",
                                "data": None
                            }
                        },
                        "content_too_short": {
                            "summary": "描述内容过短",
                            "value": {
                                "code": 0,
                                "message": "提交反馈失败",
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
                        "message": "未提供认证token或token无效",
                        "data": None
                    }
                }
            }
        }
    }
)
async def submit_feedback(
    request: FeedbackSubmitRequest,
    user_id: str = Depends(require_current_user)
) -> Dict[str, Any]:
    result = feedback_service.submit_feedback(
        user_id=user_id,
        feedback_type=request.feedback_type,
        feedback_content=request.feedback_content,
        feedback_images=request.feedback_images
    )

    if not result.get("success"):
        return response.fail(message=result.get("error", "提交反馈失败"))

    return response.success(
        data={"feedback_id": result.get("feedback_id")},
        message=result.get("message", "提交成功")
    )


@router.get(
    "/my",
    summary="获取我的反馈列表",
    description="""
    获取当前用户的反馈列表，支持按状态筛选。

    **反馈状态说明：**
    - `pending`: 待处理 - 管理员尚未查看
    - `processing`: 处理中 - 管理员正在处理
    - `resolved`: 已解决 - 问题已修复
    - `closed`: 已关闭 - 反馈已完结

    **筛选条件：**
    - 支持按状态筛选
    - 按创建时间倒序排列（最新的在前）

    **注意事项：**
    - 分页查询，默认每页20条

    **认证要求：** 需要在请求头中携带有效的 JWT token
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
                            "total": 5,
                            "page": 1,
                            "page_size": 20,
                            "feedbacks": [
                                {
                                    "feedback_id": "FB1234567890ABCDE",
                                    "user_id": "user_001",
                                    "feedback_type": "bug",
                                    "feedback_content": "登录页面在移动端显示异常",
                                    "feedback_images": ["https://example.com/screenshot.png"],
                                    "admin_reply": "我们已收到您的问题，正在处理中",
                                    "admin_id": "admin_001",
                                    "replied_at": "2024-01-15T10:30:00",
                                    "status": "processing",
                                    "priority": "high",
                                    "created_at": "2024-01-14T08:00:00",
                                    "updated_at": "2024-01-15T10:30:00"
                                }
                            ]
                        }
                    }
                }
            }
        },
        400: {
            "description": "获取失败",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "获取反馈列表失败",
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
                        "message": "未提供认证token或token无效",
                        "data": None
                    }
                }
            }
        }
    }
)
async def get_my_feedbacks(
    user_id: str = Depends(require_current_user),
    status: str = Query(None, description="筛选状态：pending, processing, resolved, closed"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
) -> Dict[str, Any]:
    result = feedback_service.get_my_feedbacks(
        user_id=user_id,
        status=status,
        page=page,
        page_size=page_size
    )

    if not result.get("success"):
        return response.fail(message=result.get("error", "获取反馈列表失败"))

    return response.success(
        data={
            "total": result.get("total", 0),
            "page": result.get("page", 1),
            "page_size": result.get("page_size", 20),
            "feedbacks": result.get("feedbacks", [])
        }
    )


@router.get(
    "/{feedback_id}",
    summary="获取反馈详情",
    description="""
    获取指定反馈的详细信息。

    **返回信息包含：**
    - 反馈基本信息（类型、内容、图片）
    - 管理员回复内容（如有）
    - 处理状态和优先级
    - 创建和更新时间

    **注意事项：**
    - 只能查看自己提交的反馈
    - 反馈ID可通过"我的反馈列表"获取

    **认证要求：** 需要在请求头中携带有效的 JWT token
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
                            "feedback": {
                                "feedback_id": "FB1234567890ABCDE",
                                "user_id": "user_001",
                                "feedback_type": "bug",
                                "feedback_content": "登录页面在移动端显示异常，部分按钮无法点击",
                                "feedback_images": [
                                    "https://example.com/screenshot1.png",
                                    "https://example.com/screenshot2.png"
                                ],
                                "admin_reply": "您好，我们已收到您的反馈。该问题已确认，预计下周版本修复。",
                                "admin_id": "admin_001",
                                "replied_at": "2024-01-15T14:30:00",
                                "status": "processing",
                                "priority": "high",
                                "created_at": "2024-01-14T08:00:00",
                                "updated_at": "2024-01-15T14:30:00",
                                "user_nickname": "测试用户",
                                "user_phone": "138****8000"
                            }
                        }
                    }
                }
            }
        },
        404: {
            "description": "反馈不存在或无权访问",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "反馈不存在或无权访问",
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
                        "message": "未提供认证token或token无效",
                        "data": None
                    }
                }
            }
        }
    }
)
async def get_feedback_detail(
    feedback_id: str,
    user_id: str = Depends(require_current_user)
) -> Dict[str, Any]:
    result = feedback_service.get_feedback_detail(
        feedback_id=feedback_id,
        user_id=user_id
    )

    if not result.get("success"):
        return response.fail(message=result.get("error", "获取反馈详情失败"))

    return response.success(data=result.get("feedback"))
