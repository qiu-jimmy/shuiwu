"""
Models 数据访问层（Repository）
处理所有与数据库相关的操作
"""
from typing import Any, Dict, Optional

from sqlalchemy import text

from app.infra.db import get_sync_engine


class ModelsRepository:
    """Models数据访问层"""
    
    def __init__(self, db_schema: str = "models"):
        self.db_schema = db_schema
        self._db_initialized = False
    
    def ensure_database_initialized(self):
        """初始化数据库（创建schema和表）"""
        if self._db_initialized:
            return
        
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                # 创建schema
                conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {self.db_schema}"))
                conn.commit()
                
                # 创建models表
                conn.execute(text(f"""
                    CREATE TABLE IF NOT EXISTS {self.db_schema}.models (
                        id VARCHAR(50) PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        provider VARCHAR(50),
                        model_url VARCHAR(500),
                        model_api_key VARCHAR(255),
                        description VARCHAR(500),
                        status VARCHAR(20),
                        context_window INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                conn.commit()
            
            self._db_initialized = True
        except Exception as e:
            print(f"初始化Models数据库时出错（可能已存在）: {e}")
    
    def _row_to_dict(self, row) -> Dict[str, Any]:
        """将数据库行转换为字典"""
        return {
            "id": row.id,
            "name": row.name,
            "provider": row.provider,
            "model_url": row.model_url,
            "model_api_key": row.model_api_key,
            "description": row.description,
            "status": row.status,
            "context_window": row.context_window,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
    
    def list_all_models(self) -> list[Dict[str, Any]]:
        """从数据库获取所有模型列表"""
        self.ensure_database_initialized()
        
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                rows = conn.execute(
                    text(f"SELECT * FROM {self.db_schema}.models ORDER BY created_at DESC")
                ).fetchall()
                return [self._row_to_dict(row) for row in rows]
        except Exception as e:
            print(f"获取模型列表失败: {e}")
            return []
    
    def get_model_by_id(self, model_id: str) -> Optional[Dict[str, Any]]:
        """从数据库获取单个模型"""
        self.ensure_database_initialized()
        
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                row = conn.execute(
                    text(f"SELECT * FROM {self.db_schema}.models WHERE id = :model_id"),
                    {"model_id": model_id}
                ).fetchone()
                
                if row:
                    return self._row_to_dict(row)
                return None
        except Exception as e:
            print(f"获取模型失败: {e}")
            return None
    
    def create_model(self, model_data: Dict[str, Any]) -> None:
        """创建新模型"""
        self.ensure_database_initialized()
        
        engine = get_sync_engine()
        with engine.connect() as conn:
            conn.execute(text(f"""
                INSERT INTO {self.db_schema}.models
                (id, name, provider, model_url, model_api_key, description, status, context_window)
                VALUES (:id, :name, :provider, :model_url, :model_api_key, :description, :status, :context_window)
            """), {
                "id": model_data["id"],
                "name": model_data["name"],
                "provider": model_data.get("provider"),
                "model_url": model_data.get("model_url"),
                "model_api_key": model_data.get("model_api_key"),
                "description": model_data.get("description"),
                "status": model_data.get("status"),
                "context_window": model_data.get("context_window")
            })
            conn.commit()
    
    def update_model(self, model_id: str, update_data: Dict[str, Any]) -> None:
        """更新模型"""
        self.ensure_database_initialized()
        
        engine = get_sync_engine()
        with engine.connect() as conn:
            update_fields = []
            params = {"id": model_id}
            
            for field in ["name", "provider", "model_url", "model_api_key", "description", "status", "context_window"]:
                if field in update_data and update_data[field] is not None:
                    update_fields.append(f"{field} = :{field}")
                    params[field] = update_data[field]
            
            if not update_fields:
                raise Exception("没有要更新的字段")
            
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            conn.execute(
                text(f"UPDATE {self.db_schema}.models SET {', '.join(update_fields)} WHERE id = :id"),
                params
            )
            conn.commit()
    
    def delete_model(self, model_id: str) -> None:
        """删除模型"""
        self.ensure_database_initialized()
        
        engine = get_sync_engine()
        with engine.connect() as conn:
            conn.execute(
                text(f"DELETE FROM {self.db_schema}.models WHERE id = :id"),
                {"id": model_id}
            )
            conn.commit()
    
    def model_exists(self, model_id: str) -> bool:
        """检查模型是否存在"""
        self.ensure_database_initialized()
        
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                row = conn.execute(
                    text(f"SELECT id FROM {self.db_schema}.models WHERE id = :id"),
                    {"id": model_id}
                ).fetchone()
                return row is not None
        except Exception:
            return False


# 全局Repository实例
models_repository = ModelsRepository()

