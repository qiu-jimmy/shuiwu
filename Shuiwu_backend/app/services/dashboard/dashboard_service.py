"""Dashboard 业务逻辑层"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.infra.db import create_postgres_db
from app.services.dashboard.dashboard_repository import dashboard_repository
from app.services.knowledge.knowledge_service import knowledge_service
from app.utils.dashboard_utils import format_time, get_session_metrics_summary, _get_session_metrics


class DashboardService:
    """仪表盘服务类"""

    def __init__(self):
        self.repository = dashboard_repository
        # 延迟初始化，避免在模块导入时阻塞
        self._db = None

    @property
    def db(self):
        """延迟加载PostgresDb实例"""
        if self._db is None:
            self._db = create_postgres_db(session_table="agent_sessions")
        return self._db
    
    def _get_all_sessions(self, user_id: Optional[str] = None, **kwargs) -> List[Any]:
        """获取所有类型的会话

        注意：Agno 的 get_sessions 方法只支持 'agent' 类型的会话
        'document' 和 'team' 类型目前不被支持，会抛出 'Invalid session type' 错误
        """
        all_sessions = []

        # 只获取 'agent' 类型的会话（Agno 目前唯一支持的类型）
        try:
            sessions = self.db.get_sessions(
                user_id=user_id,
                session_type="agent",
                **kwargs
            )
            all_sessions.extend(sessions)
        except Exception as e:
            print(f"获取 agent 类型会话失败: {e}")

        # 按创建时间排序（最新的在前）
        all_sessions.sort(key=lambda s: getattr(s, "created_at", 0) or 0, reverse=True)
        return all_sessions
    
    def get_dashboard_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """获取仪表盘统计数据"""
        try:
            today = datetime.now().date()
            today_start = int(datetime.combine(today, datetime.min.time()).timestamp())
            today_end = int(datetime.combine(today, datetime.max.time()).timestamp())
            
            sessions = self._get_all_sessions(
                user_id=user_id,
                start_timestamp=today_start,
                end_timestamp=today_end
            )
            today_requests = len(sessions)
            kb_docs = self._count_knowledge_base_documents(user_id)
            local_models = self.repository.count_models_by_type(is_local=True)
            api_models = self.repository.count_models_by_type(is_local=False)
            token_stats = self._get_today_token_stats(user_id, today_start, today_end)
            
            return {
                "today_requests": today_requests,
                "knowledge_base_docs": kb_docs,
                "local_models": local_models,
                "api_models": api_models,
                "today_total_tokens": token_stats["total_tokens"],
                "today_input_tokens": token_stats["input_tokens"],
                "today_output_tokens": token_stats["output_tokens"],
            }
        except Exception as e:
            print(f"获取仪表盘统计数据失败: {e}")
            return {
                "today_requests": 0,
                "knowledge_base_docs": 0,
                "local_models": 0,
                "api_models": 0,
                "today_total_tokens": 0,
                "today_input_tokens": 0,
                "today_output_tokens": 0,
            }
    
    def _count_knowledge_base_documents(self, user_id: Optional[str] = None) -> int:
        """统计知识库文档总数"""
        try:
            kb_list = knowledge_service.list_knowledge_bases(user_id)
            return sum(kb.get("document_count", 0) for kb in kb_list)
        except Exception as e:
            print(f"统计知识库文档总数失败: {e}")
            return 0
    
    def _get_today_token_stats(self, user_id: Optional[str], start: int, end: int) -> Dict[str, int]:
        """统计今日 token 使用量"""
        try:
            sessions = self._get_all_sessions(
                user_id=user_id,
                start_timestamp=start,
                end_timestamp=end
            )
            return get_session_metrics_summary(sessions)
        except Exception as e:
            print(f"统计今日 token 失败: {e}")
            return {"total_tokens": 0, "input_tokens": 0, "output_tokens": 0}
    
    def get_token_chart_data(self, user_id: Optional[str] = None, days: int = 7) -> List[Dict[str, Any]]:
        """获取 token 趋势图表数据（最近N天）"""
        try:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days - 1)
            
            data_points = []
            
            for i in range(days):
                current_date = start_date + timedelta(days=i)
                date_start = int(datetime.combine(current_date, datetime.min.time()).timestamp())
                date_end = int(datetime.combine(current_date, datetime.max.time()).timestamp())
                
                token_stats = self._get_today_token_stats(user_id, date_start, date_end)
                
                data_points.append({
                    "date": current_date.strftime("%Y-%m-%d"),
                    "total_tokens": token_stats["total_tokens"],
                    "input_tokens": token_stats["input_tokens"],
                    "output_tokens": token_stats["output_tokens"],
                })
            
            return data_points
        except Exception as e:
            print(f"获取 token 图表数据失败: {e}")
            return []
    
    def get_session_token_usage(self, user_id: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
        """获取会话 token 消耗列表"""
        try:
            all_sessions = self._get_all_sessions(user_id=user_id)
            sessions = all_sessions[:limit]
            sessions_data = []
            
            for session in sessions:
                metrics = _get_session_metrics(session)
                if not metrics or metrics.get("total_tokens", 0) <= 0:
                    continue
                
                session_data = session.session_data or {}
                created_at = session.created_at
                dt = datetime.fromtimestamp(created_at) if isinstance(created_at, int) else (
                    created_at if isinstance(created_at, datetime) else datetime.now()
                )
                
                session_metrics = session_data.get("session_metrics", {})
                
                sessions_data.append({
                    "session_id": session.session_id,
                    "session_name": session_data.get("name", "未命名会话"),
                    "session_type": getattr(session, "session_type", "agent"),
                    "created_at": dt.isoformat(),
                    "total_tokens": metrics["total_tokens"],
                    "input_tokens": metrics["input_tokens"],
                    "output_tokens": metrics["output_tokens"],
                    "duration": session_metrics.get("duration") if isinstance(session_metrics, dict) else None,
                })
            
            return {"sessions": sessions_data, "total": len(sessions_data)}
        except Exception as e:
            print(f"获取会话 token 消耗失败: {e}")
            return {"sessions": [], "total": 0}
    
    def get_recent_activities(self, user_id: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近活动记录"""
        try:
            activities = []
            all_sessions = self._get_all_sessions(user_id=user_id)
            sessions = all_sessions[:limit * 2]
            
            for session in sessions:
                activity = self._parse_session_to_activity(session, user_id)
                if activity:
                    activities.append(activity)
                    if len(activities) >= limit:
                        break
            
            if len(activities) < limit:
                kb_activities = self.repository.get_kb_upload_activities(
                    user_id, 
                    limit - len(activities)
                )
                activities.extend(kb_activities)
            
            return activities[:limit]
        except Exception as e:
            print(f"获取最近活动失败: {e}")
            return []
    
    def _parse_session_to_activity(self, session: Any, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """将会话记录解析为活动项"""
        try:
            session_type = getattr(session, "session_type", "agent")
            session_data = session.session_data or {}
            created_at = session.created_at
            
            dt = datetime.fromtimestamp(created_at) if isinstance(created_at, int) else (
                created_at if isinstance(created_at, datetime) else datetime.now()
            )
            time_str = format_time(dt)
            session_name = session_data.get("name", "")
            
            if session_type in ("agent", "chat-agent"):
                return {
                    "title": "对话会话完成",
                    "desc": session_name or "多 Agent 协作",
                    "time": time_str,
                    "type": "success",
                }
            elif session_type in ("document", "document-agent"):
                return {
                    "title": "文档编辑会话完成",
                    "desc": session_name or "多 Agent 协作撰写摘要（文档页）",
                    "time": time_str,
                    "type": "success",
                }
            elif session_type == "team":
                team_data = getattr(session, "team_data", None)
                if team_data and isinstance(team_data, dict):
                    return {
                        "title": "团队协作会话",
                        "desc": team_data.get("name", "团队协作"),
                        "time": time_str,
                        "type": "info",
                    }
            
            return None
        except Exception as e:
            print(f"解析会话活动失败: {e}")
            return None


# 全局服务实例
dashboard_service = DashboardService()
