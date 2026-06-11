"""
管理端积分相关API接口
"""
from fastapi import APIRouter, Depends, Query
from typing import Optional
from datetime import datetime

from app.utils.dependencies import require_admin
from app.schemas.points import (
    PointsConfigResponse,
    PointsConfigUpdate,
    PointsStatisticsResponse,
    GrantPointsRequest,
    PointBalanceResponse,
    PointRecordsListResponse
)
from app.services.points.point_service import point_service


router = APIRouter(prefix="/api/admin/points", tags=["管理端-积分管理"])


@router.get("/config", response_model=PointsConfigResponse, summary="获取积分配置")
async def get_points_config(
    admin_info: dict = Depends(require_admin)
):
    """
    获取积分系统配置

    返回当前积分配置：
    - payment_points_rate: 支付积分比例（1元=N积分）
    - invitation_reward_points: 邀请奖励积分
    """
    config = point_service.get_points_config()
    return PointsConfigResponse(**config)


@router.put("/config", summary="更新积分配置")
async def update_points_config(
    config_update: PointsConfigUpdate,
    admin_info: dict = Depends(require_admin)
):
    """
    更新积分系统配置

    参数：
    - payment_points_rate: 支付积分比例（1-1000）
    - invitation_reward_points: 邀请奖励积分（0-10000）
    """
    result = point_service.update_points_config(
        payment_points_rate=config_update.payment_points_rate,
        invitation_reward_points=config_update.invitation_reward_points
    )

    if not result.get("success"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=result.get("error"))

    return {
        "message": "积分配置更新成功",
        "config": result["config"]
    }


@router.get("/users/{user_id}/balance", response_model=PointBalanceResponse, summary="查询用户积分余额")
async def get_user_points_balance(
    user_id: str,
    admin_info: dict = Depends(require_admin)
):
    """
    查询指定用户的积分余额

    参数：
    - user_id: 用户ID

    返回：
    - points_balance: 用户积分余额（如果用户没有积分记录，返回0）
    """
    result = point_service.get_user_points_balance(user_id)
    return PointBalanceResponse(**result)


@router.get("/users/{user_id}/records", response_model=PointRecordsListResponse, summary="查询用户积分流水")
async def get_user_point_records(
    user_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    admin_info: dict = Depends(require_admin)
):
    """
    查询指定用户的积分流水记录（分页）

    参数：
    - user_id: 用户ID
    - page: 页码，默认1
    - page_size: 每页大小，默认20

    返回：
    - total: 总记录数
    - page: 当前页码
    - page_size: 每页大小
    - records: 积分记录列表
    """
    result = point_service.get_point_records(
        user_id=user_id,
        page=page,
        page_size=page_size
    )

    # 转换为响应模型
    from app.schemas.points import PointRecordResponse
    records = [
        PointRecordResponse(**record) for record in result["records"]
    ]

    return PointRecordsListResponse(
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        records=records
    )


@router.get("/statistics", response_model=PointsStatisticsResponse, summary="获取积分统计")
async def get_points_statistics(
    start_date: Optional[str] = Query(None, description="开始日期（YYYY-MM-DD）"),
    end_date: Optional[str] = Query(None, description="结束日期（YYYY-MM-DD）"),
    admin_info: dict = Depends(require_admin)
):
    """
    获取积分统计数据

    返回：
    - total_users_with_points: 有积分的用户数
    - total_points_issued: 累计发放积分
    - points_by_type: 按类型统计的积分（order_payment/invitation_reward）
    """
    # 转换日期格式
    start_dt = None
    end_dt = None

    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="开始日期格式错误，请使用YYYY-MM-DD格式")

    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="结束日期格式错误，请使用YYYY-MM-DD格式")

    stats = point_service.get_points_statistics(start_dt, end_dt)
    return PointsStatisticsResponse(**stats)


@router.post("/grant", summary="手动赠送积分")
async def grant_points(
    request_data: GrantPointsRequest,
    admin_info: dict = Depends(require_admin)
):
    """
    手动赠送积分给用户

    参数：
    - user_id: 用户ID
    - points: 积分数量（1-1000000）
    - reason: 赠送原因（可选，默认"管理员手动赠送"）

    使用场景：
    - 活动奖励
    - 故障补偿
    - 手动补发

    示例：
    POST /api/admin/points/grant
    {
      "user_id": "user_1234567890",
      "points": 1000,
      "reason": "新用户注册奖励"
    }
    """
    result = point_service.add_points(
        user_id=request_data.user_id,
        points=request_data.points,
        change_type="manual_grant",
        change_reason=request_data.reason
    )

    if not result.get("success"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=result.get("error"))

    return {
        "message": "积分赠送成功",
        "user_id": request_data.user_id,
        "points": request_data.points,
        "new_balance": result.get("new_balance", 0),
        "reason": request_data.reason
    }
