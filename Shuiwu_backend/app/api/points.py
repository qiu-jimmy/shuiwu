"""
用户积分相关API接口
"""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.points import PointBalanceResponse, PointRecordsListResponse, PointRecordResponse
from app.services.points.point_service import point_service


router = APIRouter(prefix="/api/user/points", tags=["用户积分"])


@router.get("/balance", response_model=PointBalanceResponse, summary="查询积分余额")
async def get_points_balance(
    request: Request
):
    """
    获取当前用户的积分余额

    返回用户当前可用积分总额
    """
    # 从JWT中间件设置的request.state中获取user_id
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        from app.utils.response import response
        return response.fail(message="未认证", code="UNAUTHORIZED")

    result = point_service.get_user_points_balance(user_id)
    return PointBalanceResponse(**result)


@router.get("/records", response_model=PointRecordsListResponse, summary="查询积分流水")
async def get_point_records(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小")
):
    """
    查询当前用户的积分获得记录（分页）

    返回积分流水列表，包括：
    - 订单支付获得的积分
    - 邀请用户获得的积分
    """
    # 从JWT中间件设置的request.state中获取user_id
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        from app.utils.response import response
        return response.fail(message="未认证", code="UNAUTHORIZED")

    result = point_service.get_point_records(
        user_id=user_id,
        page=page,
        page_size=page_size
    )

    # 转换为响应模型
    records = [
        PointRecordResponse(**record) for record in result["records"]
    ]

    return PointRecordsListResponse(
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        records=records
    )
