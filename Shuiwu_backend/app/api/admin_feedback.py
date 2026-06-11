"""
问题反馈系统 - 管理员端 API 路由
供后台管理系统使用
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, Query
from app.services.feedback.feedback_service import feedback_service
from app.schemas.feedback import (
    FeedbackListResponse,
    FeedbackStatusUpdateRequest,
    FeedbackReplyRequest,
)
from app.utils.response import response
from app.utils.dependencies import require_current_admin

router = APIRouter(prefix="/api/admin/feedback", tags=["问题反馈-管理员端"])


# ============================================================================
# 管理员端接口
# ============================================================================


@router.get(
    "/list",
    summary="获取所有反馈列表",
    description="""
    获取所有用户反馈列表（后台管理系统使用）。

    **筛选条件：**
    - `status`: 按状态筛选（pending, processing, resolved, closed）
    - `feedback_type`: 按反馈类型筛选（bug, feature, complaint, other）
    - `priority`: 按优先级筛选（low, normal, high, urgent）

    **排序规则：**
    - 优先按优先级排序：urgent > high > normal > low
    - 同优先级按创建时间倒序（最新的在前）

    **认证要求：** 需要管理员权限
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
                                    "updated_at": "2024-01-15T10:30:00",
                                    "user_nickname": "测试用户",
                                    "user_phone": "138****8000",
                                    "admin_nickname": "管理员"
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
                        "message": "需要管理员权限",
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
async def list_all_feedbacks(
    admin_info: dict = Depends(require_current_admin),
    status: str = Query(None, description="筛选状态：pending, processing, resolved, closed"),
    feedback_type: str = Query(None, description="筛选反馈类型：bug, feature, complaint, other"),
    priority: str = Query(None, description="筛选优先级：low, normal, high, urgent"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
) -> Dict[str, Any]:
    # 从管理员信息中获取 admin_id
    admin_id = admin_info.get("admin_id") or admin_info.get("user_id")

    result = feedback_service.list_all_feedbacks(
        status=status,
        feedback_type=feedback_type,
        priority=priority,
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
    summary="获取反馈详情（管理员）",
    description="""
    获取反馈详细信息（后台管理系统使用）。

    **返回信息包含：**
    - 反馈基本信息（类型、内容、图片）
    - 用户信息（昵称、手机号、会员等级、状态）
    - 管理员回复历史
    - 处理状态和优先级
    - 时间信息

    **认证要求：** 需要管理员权限
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
                                "user_phone": "13800138000",
                                "user_status": "normal",
                                "user_member_level": "vip",
                                "admin_nickname": "管理员"
                            }
                        }
                    }
                }
            }
        },
        404: {
            "description": "反馈不存在",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "反馈不存在",
                        "data": None
                    }
                }
            }
        }
    }
)
async def get_feedback_detail_admin(
    feedback_id: str,
    admin_info: dict = Depends(require_current_admin)
) -> Dict[str, Any]:
    # 从管理员信息中获取 admin_id
    admin_id = admin_info.get("admin_id") or admin_info.get("user_id")

    from app.services.feedback.feedback_service import _get_engine
    from sqlalchemy import text

    engine = _get_engine()

    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT
                    f.feedback_id,
                    f.user_id,
                    f.feedback_type,
                    f.feedback_content,
                    f.feedback_images,
                    f.admin_reply,
                    f.admin_id,
                    f.replied_at,
                    f.status,
                    f.priority,
                    f.created_at,
                    f.updated_at,
                    u.nickname as user_nickname,
                    u.phone as user_phone,
                    u.status as user_status,
                    u.member_level as user_member_level,
                    a.nickname as admin_nickname
                FROM business.user_feedback f
                LEFT JOIN business.users u ON f.user_id = u.user_id
                LEFT JOIN business.users a ON f.admin_id = a.user_id
                WHERE f.feedback_id = :fid
            """),
            {"fid": feedback_id}
        ).fetchone()

        if not result:
            return response.fail(message="反馈不存在")

        feedback_data = {
            "feedback_id": result[0],
            "user_id": result[1],
            "feedback_type": result[2],
            "feedback_content": result[3],
            "feedback_images": result[4] if result[4] else [],
            "admin_reply": result[5],
            "admin_id": result[6],
            "replied_at": result[7].isoformat() if result[7] else None,
            "status": result[8],
            "priority": result[9],
            "created_at": result[10].isoformat() if result[10] else None,
            "updated_at": result[11].isoformat() if result[11] else None,
            "user_nickname": result[12],
            "user_phone": result[13],
            "user_status": result[14],
            "user_member_level": result[15],
            "admin_nickname": result[16]
        }

        return response.success(data={"feedback": feedback_data})


@router.put(
    "/{feedback_id}/status",
    summary="更新反馈状态",
    description="""
    更新反馈状态或优先级（后台管理系统使用）。

    **状态说明：**
    - `pending`: 待处理 - 新提交的反馈
    - `processing`: 处理中 - 正在处理
    - `resolved`: 已解决 - 问题已修复
    - `closed`: 已关闭 - 反馈完结

    **优先级说明：**
    - `urgent`: 紧急 - 系统崩溃、数据丢失、安全漏洞
    - `high`: 高 - 核心功能异常
    - `normal`: 中 - 一般性bug
    - `low`: 低 - UI优化、小改进

    **认证要求：** 需要管理员权限
    """,
    responses={
        200: {
            "description": "更新成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "状态已更新",
                        "data": None
                    }
                }
            }
        },
        400: {
            "description": "请求参数错误",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_status": {
                            "summary": "无效的状态值",
                            "value": {
                                "code": 0,
                                "message": "无效的状态值，必须是: pending, processing, resolved, closed",
                                "data": None
                            }
                        },
                        "invalid_priority": {
                            "summary": "无效的优先级",
                            "value": {
                                "code": 0,
                                "message": "无效的优先级，必须是: low, normal, high, urgent",
                                "data": None
                            }
                        }
                    }
                }
            }
        },
        404: {
            "description": "反馈不存在",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "反馈不存在",
                        "data": None
                    }
                }
            }
        }
    }
)
async def update_feedback_status(
    feedback_id: str,
    request: FeedbackStatusUpdateRequest,
    admin_info: dict = Depends(require_current_admin)
) -> Dict[str, Any]:
    # 从管理员信息中获取 admin_id
    admin_id = admin_info.get("admin_id") or admin_info.get("user_id")

    result = feedback_service.update_feedback_status(
        feedback_id=feedback_id,
        status=request.status,
        priority=request.priority
    )

    if not result.get("success"):
        return response.fail(message=result.get("error", "更新状态失败"))

    return response.success(
        data=None,
        message=result.get("message", "状态已更新")
    )


@router.post(
    "/{feedback_id}/reply",
    summary="管理员回复反馈",
    description="""
    管理员回复用户反馈（后台管理系统使用）。

    **回复说明：**
    - 回复后反馈状态会自动变为"处理中"(processing)
    - 会记录管理员ID和回复时间
    - 用户可以在"我的反馈"中查看回复

    **认证要求：** 需要管理员权限
    """,
    responses={
        200: {
            "description": "回复成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "回复成功",
                        "data": None
                    }
                }
            }
        },
        400: {
            "description": "回复失败",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "回复失败",
                        "data": None
                    }
                }
            }
        },
        404: {
            "description": "反馈不存在",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "反馈不存在",
                        "data": None
                    }
                }
            }
        }
    }
)
async def reply_feedback(
    feedback_id: str,
    request: FeedbackReplyRequest,
    admin_info: dict = Depends(require_current_admin)
) -> Dict[str, Any]:
    # 从管理员信息中获取 admin_id
    admin_id = admin_info.get("admin_id") or admin_info.get("user_id")

    result = feedback_service.reply_feedback(
        feedback_id=feedback_id,
        admin_id=admin_id,
        admin_reply=request.admin_reply
    )

    if not result.get("success"):
        return response.fail(message=result.get("error", "回复失败"))

    return response.success(
        data=None,
        message=result.get("message", "回复成功")
    )


@router.get(
    "/stats/overview",
    summary="获取反馈统计信息",
    description="""
    获取反馈统计信息（后台管理系统首页数据展示）。

    **统计项：**
    - `pending_count`: 待处理数量
    - `processing_count`: 处理中数量
    - `resolved_count`: 已解决数量
    - `closed_count`: 已关闭数量
    - `urgent_count`: 紧急问题数量

    **使用场景：**
    - 后台管理首页数据看板
    - 实时监控反馈处理情况
    - 工作量统计

    **认证要求：** 需要管理员权限
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
                            "pending_count": 5,
                            "processing_count": 3,
                            "resolved_count": 20,
                            "closed_count": 10,
                            "urgent_count": 2
                        }
                    }
                }
            }
        }
    }
)
async def get_feedback_stats(
    admin_info: dict = Depends(require_current_admin)
) -> Dict[str, Any]:
    result = feedback_service.get_feedback_stats()

    if not result.get("success"):
        return response.fail(message=result.get("error", "获取统计信息失败"))

    return response.success(data=result.get("stats"))


@router.delete(
    "/{feedback_id}",
    summary="删除反馈（管理员）",
    description="""
    删除反馈（后台管理系统使用）。

    **删除限制：**
    - 只能删除已关闭(closed)状态的反馈
    - 删除操作不可逆

    **使用场景：**
    - 清理无效反馈
    - 清理测试数据

    **认证要求：** 需要管理员权限
    """,
    responses={
        200: {
            "description": "删除成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "删除成功",
                        "data": None
                    }
                }
            }
        },
        400: {
            "description": "删除失败",
            "content": {
                "application/json": {
                    "examples": {
                        "not_found": {
                            "summary": "反馈不存在",
                            "value": {
                                "code": 0,
                                "message": "反馈不存在",
                                "data": None
                            }
                        },
                        "not_closed": {
                            "summary": "只能删除已关闭的反馈",
                            "value": {
                                "code": 0,
                                "message": "只能删除已关闭的反馈",
                                "data": None
                            }
                        }
                    }
                }
            }
        }
    }
)
async def delete_feedback(
    feedback_id: str,
    admin_info: dict = Depends(require_current_admin)
) -> Dict[str, Any]:
    from app.services.feedback.feedback_service import _get_engine
    from sqlalchemy import text

    engine = _get_engine()

    with engine.connect() as conn:
        # 检查反馈状态
        feedback = conn.execute(
            text("SELECT status FROM business.user_feedback WHERE feedback_id = :fid"),
            {"fid": feedback_id}
        ).fetchone()

        if not feedback:
            return response.fail(message="反馈不存在")

        if feedback[0] != 'closed':
            return response.fail(message="只能删除已关闭的反馈")

        # 删除反馈
        conn.execute(
            text("DELETE FROM business.user_feedback WHERE feedback_id = :fid"),
            {"fid": feedback_id}
        )

        conn.commit()

        return response.success(
            data=None,
            message="删除成功"
        )


@router.post(
    "/{feedback_id}/close",
    summary="关闭反馈",
    description="""
    关闭反馈（后台管理系统使用）。

    **使用场景：**
    - 问题已解决，用户无异议
    - 用户主动撤回反馈
    - 反馈无效或重复

    **注意事项：**
    - 关闭后不可再次修改
    - 关闭不是删除，反馈记录仍保留

    **认证要求：** 需要管理员权限
    """,
    responses={
        200: {
            "description": "关闭成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "反馈已关闭",
                        "data": None
                    }
                }
            }
        },
        404: {
            "description": "反馈不存在",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "反馈不存在",
                        "data": None
                    }
                }
            }
        }
    }
)
async def close_feedback(
    feedback_id: str,
    admin_info: dict = Depends(require_current_admin)
) -> Dict[str, Any]:
    result = feedback_service.update_feedback_status(
        feedback_id=feedback_id,
        status="closed"
    )

    if not result.get("success"):
        return response.fail(message=result.get("error", "关闭反馈失败"))

    return response.success(
        data=None,
        message=result.get("message", "反馈已关闭")
    )


@router.get(
    "/export/excel",
    summary="导出反馈数据（Excel）",
    description="""
    导出反馈数据为Excel文件（后台管理系统使用）。

    **筛选条件：**
    - 支持按状态、类型、日期范围筛选
    - 导出包含完整的反馈信息和用户信息

    **使用场景：**
    - 定期报表生成
    - 数据分析和归档

    **认证要求：** 需要管理员权限

    **注意：** 此功能待实现
    """,
    responses={
        200: {
            "description": "导出成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "导出成功",
                        "data": {
                            "download_url": "https://example.com/exports/feedback_20240115.xlsx"
                        }
                    }
                }
            }
        },
        400: {
            "description": "导出失败",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "Excel导出功能待实现",
                        "data": None
                    }
                }
            }
        }
    }
)
async def export_feedbacks_excel(
    admin_info: dict = Depends(require_current_admin),
    status: str = Query(None, description="筛选状态"),
    feedback_type: str = Query(None, description="筛选反馈类型"),
    start_date: str = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(None, description="结束日期 YYYY-MM-DD"),
) -> Dict[str, Any]:
    # TODO: 实现Excel导出功能
    return response.fail(message="Excel导出功能待实现")
