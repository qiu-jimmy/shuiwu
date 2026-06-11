"""Dashboard 路由"""
import asyncio
from typing import Optional

from fastapi import APIRouter, Query

from app.schemas.dashboard import (
    DashboardStatsResponse,
    DashboardActivitiesResponse,
    TokenChartResponse,
    SessionTokenUsageResponse,
)
from app.services.dashboard.dashboard_service import dashboard_service
from app.utils.response import response

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


async def _run_sync(func, *args):
    """在线程池中执行同步函数"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, *args)


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(user_id: Optional[str] = None):
    """获取仪表盘统计数据"""
    try:
        user_id = user_id or "u123"
        result = await _run_sync(dashboard_service.get_dashboard_stats, user_id)
        return response.success(data=result, message="获取统计数据成功")
    except Exception as e:
        return response.fail(message=f"获取统计数据失败: {str(e)}")


@router.get("/token-chart", response_model=TokenChartResponse)
async def get_token_chart(
    user_id: Optional[str] = None,
    days: Optional[str] = Query("7", description="天数")
):
    """获取 token 趋势图表数据"""
    try:
        user_id = user_id or "u123"
        # 手动解析 days 参数
        try:
            parsed_days = int(days) if days else 7
            parsed_days = max(1, min(365, parsed_days))  # 限制在 1-365 天之间
        except (ValueError, TypeError):
            parsed_days = 7

        data = await _run_sync(dashboard_service.get_token_chart_data, user_id, parsed_days)
        return response.success(data={"data": data}, message="获取token图表数据成功")
    except Exception as e:
        return response.fail(message=f"获取 token 图表数据失败: {str(e)}")


@router.get("/session-tokens", response_model=SessionTokenUsageResponse)
async def get_session_token_usage(
    user_id: Optional[str] = None,
    limit: Optional[str] = Query("20", description="返回数量")
):
    """获取会话 token 消耗列表"""
    try:
        user_id = user_id or "u123"
        # 手动解析 limit 参数
        try:
            parsed_limit = int(limit) if limit else 20
            parsed_limit = max(1, min(100, parsed_limit))  # 限制在 1-100 之间
        except (ValueError, TypeError):
            parsed_limit = 20

        result = await _run_sync(dashboard_service.get_session_token_usage, user_id, parsed_limit)
        return response.success(data=result, message="获取会话token消耗成功")
    except Exception as e:
        return response.fail(message=f"获取会话 token 消耗失败: {str(e)}")


@router.get("/activities", response_model=DashboardActivitiesResponse)
async def get_recent_activities(
    user_id: Optional[str] = None,
    limit: Optional[str] = Query("10", description="返回数量")
):
    """获取最近活动记录"""
    try:
        user_id = user_id or "u123"
        # 手动解析 limit 参数
        try:
            parsed_limit = int(limit) if limit else 10
            parsed_limit = max(1, min(100, parsed_limit))  # 限制在 1-100 之间
        except (ValueError, TypeError):
            parsed_limit = 10

        activities = await _run_sync(dashboard_service.get_recent_activities, user_id, parsed_limit)
        return response.success(data={"activities": activities}, message="获取活动记录成功")
    except Exception as e:
        return response.fail(message=f"获取活动记录失败: {str(e)}")
