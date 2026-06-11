"""Dashboard 数据访问层"""
import sqlalchemy
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import text

from app.infra.db import get_sync_engine
from app.utils.dashboard_utils import format_time


class DashboardRepository:
    """仪表盘数据访问层"""
    
    def __init__(self, db_schema: str = "ai"):
        self.db_schema = db_schema
        self.engine = get_sync_engine()
    
    def count_models_by_type(self, is_local: bool) -> int:
        """按类型统计模型数"""
        try:
            inspector = sqlalchemy.inspect(self.engine)
            if not inspector.get_table_names(schema="models"):
                return 0
            
            with self.engine.connect() as conn:
                if is_local:
                    sql = text("""
                        SELECT COUNT(*) as count
                        FROM models.models
                        WHERE provider = 'local' OR provider IS NULL
                    """)
                else:
                    sql = text("""
                        SELECT COUNT(*) as count
                        FROM models.models
                        WHERE provider IS NOT NULL AND provider != 'local'
                    """)
                result = conn.execute(sql)
                return result.scalar() or 0
        except Exception as e:
            print(f"统计模型数失败: {e}")
            return 0
    
    def get_kb_upload_activities(
        self, 
        user_id: Optional[str] = None, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """从知识库表中提取上传活动"""
        activities = []
        try:
            from app.services.knowledge.knowledge_service import knowledge_service
            kb_list = knowledge_service.list_knowledge_bases(user_id)
            
            for kb in kb_list[:limit]:
                kb_name = kb.get("kb_name")
                kb_user_id = kb.get("user_id", user_id or "default")
                table_name = f"kb_{kb_user_id}_{kb_name}"
                
                try:
                    with self.engine.connect() as conn:
                        sql = text(f"""
                            SELECT 
                                COALESCE(meta_data->>'filename', filters->>'filename', name) as filename,
                                created_at
                            FROM {self.db_schema}."{table_name}"
                            WHERE COALESCE(meta_data->>'filename', filters->>'filename', name) IS NOT NULL
                            ORDER BY created_at DESC
                            LIMIT 1
                        """)
                        row = conn.execute(sql).fetchone()
                        
                        if row and row.created_at:
                            dt = datetime.fromtimestamp(row.created_at) if isinstance(row.created_at, int) else (
                                row.created_at if isinstance(row.created_at, datetime) else datetime.now()
                            )
                            filename = row.filename or "未知文件"
                            activities.append({
                                "title": "知识库文档上传",
                                "desc": f"『{filename}』已添加到知识库『{kb_name}』",
                                "time": format_time(dt),
                                "type": "info",
                            })
                except Exception as e:
                    print(f"提取知识库 {kb_name} 上传活动失败: {e}")
                    continue
        except Exception as e:
            print(f"提取知识库上传活动失败: {e}")
        
        return activities


# 全局实例
dashboard_repository = DashboardRepository()
