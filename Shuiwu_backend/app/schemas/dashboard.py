"""Dashboard 相关的 Pydantic 模型"""
from typing import List, Optional
from pydantic import BaseModel


class DashboardStatsResponse(BaseModel):
    """仪表盘统计响应"""
    today_requests: int  # 今日会话数（包含对话、RAG、文档）
    knowledge_base_docs: int  # 知识库文档总数
    local_models: int  # 本地模型数
    api_models: int  # API 模型数
    today_total_tokens: int  # 今日总 token 数
    today_input_tokens: int  # 今日输入 token 数
    today_output_tokens: int  # 今日输出 token 数


class TokenChartDataPoint(BaseModel):
    """Token 图表数据点"""
    date: str  # 日期 (YYYY-MM-DD)
    total_tokens: int
    input_tokens: int
    output_tokens: int


class TokenChartResponse(BaseModel):
    """Token 趋势图表响应"""
    data: List[TokenChartDataPoint]  # 最近N天的数据


class SessionTokenUsage(BaseModel):
    """会话 Token 消耗"""
    session_id: str
    session_name: str
    session_type: str
    created_at: str
    total_tokens: int
    input_tokens: int
    output_tokens: int
    duration: Optional[float] = None


class SessionTokenUsageResponse(BaseModel):
    """会话 Token 消耗响应"""
    sessions: List[SessionTokenUsage]
    total: int  # 总会话数


class ActivityItem(BaseModel):
    """活动项"""
    title: str
    desc: str
    time: str
    type: str  # info / success / warning / error


class DashboardActivitiesResponse(BaseModel):
    """最近活动响应"""
    activities: List[ActivityItem]
