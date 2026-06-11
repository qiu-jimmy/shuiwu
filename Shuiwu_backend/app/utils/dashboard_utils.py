"""Dashboard 工具函数"""
from datetime import datetime
from typing import Any, Dict, List


def format_time(dt: datetime) -> str:
    """格式化时间为友好显示格式"""
    now = datetime.now()
    diff = now - dt.replace(tzinfo=None) if dt.tzinfo else now - dt
    
    if diff.days == 0:
        hours = diff.seconds // 3600
        if hours == 0:
            minutes = diff.seconds // 60
            if minutes == 0:
                return "刚刚"
            return f"{minutes} 分钟前"
        return f"{hours} 小时前"
    elif diff.days == 1:
        return f"昨天 {dt.strftime('%H:%M')}"
    elif diff.days < 7:
        return f"{diff.days} 天前"
    else:
        return dt.strftime("%Y/%m/%d %H:%M")


def _get_session_metrics(session: Any) -> Dict[str, int]:
    """从 session 对象中提取 metrics"""
    try:
        session_data = session.session_data or {}
        metrics = session_data.get("session_metrics", {})
        
        if isinstance(metrics, dict):
            return {
                "total_tokens": metrics.get("total_tokens", 0) or 0,
                "input_tokens": metrics.get("input_tokens", 0) or 0,
                "output_tokens": metrics.get("output_tokens", 0) or 0,
            }
        return {"total_tokens": 0, "input_tokens": 0, "output_tokens": 0}
    except Exception:
        return {"total_tokens": 0, "input_tokens": 0, "output_tokens": 0}


def get_session_metrics_summary(sessions: List[Any]) -> Dict[str, int]:
    """统计会话的 token 使用量"""
    total_tokens = 0
    input_tokens = 0
    output_tokens = 0

    for session in sessions:
        metrics = _get_session_metrics(session)
        total_tokens += metrics["total_tokens"]
        input_tokens += metrics["input_tokens"]
        output_tokens += metrics["output_tokens"]

    return {
        "total_tokens": total_tokens,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }

