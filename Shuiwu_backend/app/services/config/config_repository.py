"""
系统配置数据库操作层
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy import text
from app.infra.db import get_sync_engine


class ConfigRepository:
    """系统配置数据库操作"""

    def __init__(self, db_schema: str = "business"):
        self.db_schema = db_schema

    def get_config(self, config_key: str) -> Optional[Dict[str, Any]]:
        """获取单个配置"""
        engine = get_sync_engine()
        with engine.connect() as conn:
            result = conn.execute(
                text(f"""
                SELECT config_key, config_value, config_type, description, created_at, updated_at
                FROM {self.db_schema}.system_configs
                WHERE config_key = :config_key
                """),
                {"config_key": config_key}
            ).fetchone()

            if not result:
                return None

            return {
                "config_key": result[0],
                "config_value": result[1],
                "config_type": result[2],
                "description": result[3],
                "created_at": result[4],
                "updated_at": result[5]
            }

    def get_config_value(self, config_key: str, default: Any = None) -> Any:
        """获取配置值（带类型转换）"""
        config = self.get_config(config_key)
        if not config:
            return default

        value = config["config_value"]
        config_type = config["config_type"]

        if config_type == "number":
            try:
                return float(value)
            except (ValueError, TypeError):
                return default
        elif config_type == "boolean":
            return value.lower() in ("true", "1", "yes", "on")
        elif config_type == "json":
            import json
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return default
        else:
            return value

    def list_configs(self, config_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取所有配置或按类型筛选"""
        engine = get_sync_engine()
        with engine.connect() as conn:
            if config_type:
                result = conn.execute(
                    text(f"""
                    SELECT config_key, config_value, config_type, description, created_at, updated_at
                    FROM {self.db_schema}.system_configs
                    WHERE config_type = :config_type
                    ORDER BY config_key
                    """),
                    {"config_type": config_type}
                ).fetchall()
            else:
                result = conn.execute(
                    text(f"""
                    SELECT config_key, config_value, config_type, description, created_at, updated_at
                    FROM {self.db_schema}.system_configs
                    ORDER BY config_key
                    """)
                ).fetchall()

            return [
                {
                    "config_key": row[0],
                    "config_value": row[1],
                    "config_type": row[2],
                    "description": row[3],
                    "created_at": row[4],
                    "updated_at": row[5]
                }
                for row in result
            ]

    def update_config(self, config_key: str, config_value: Any) -> bool:
        """更新配置"""
        engine = get_sync_engine()
        with engine.connect() as conn:
            # 先获取现有配置的type
            result = conn.execute(
                text(f"SELECT config_type FROM {self.db_schema}.system_configs WHERE config_key = :config_key"),
                {"config_key": config_key}
            ).fetchone()

            if not result:
                return False

            config_type = result[0]

            # 根据类型转换值
            if config_type == "json":
                import json
                value_to_store = json.dumps(config_value, ensure_ascii=False)
            else:
                value_to_store = str(config_value)

            # 更新配置
            conn.execute(
                text(f"""
                UPDATE {self.db_schema}.system_configs
                SET config_value = :config_value, updated_at = :updated_at
                WHERE config_key = :config_key
                """),
                {
                    "config_value": value_to_store,
                    "updated_at": datetime.now(),
                    "config_key": config_key
                }
            )
            conn.commit()
            return True

    def create_config(
        self,
        config_key: str,
        config_value: Any,
        config_type: str = "string",
        description: Optional[str] = None
    ) -> bool:
        """创建新配置"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                # 根据类型转换值
                if config_type == "json":
                    import json
                    value_to_store = json.dumps(config_value, ensure_ascii=False)
                else:
                    value_to_store = str(config_value)

                conn.execute(
                    text(f"""
                    INSERT INTO {self.db_schema}.system_configs (config_key, config_value, config_type, description)
                    VALUES (:config_key, :config_value, :config_type, :description)
                    """),
                    {
                        "config_key": config_key,
                        "config_value": value_to_store,
                        "config_type": config_type,
                        "description": description
                    }
                )
                conn.commit()
                return True
        except Exception:
            return False

    def delete_config(self, config_key: str) -> bool:
        """删除配置"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                conn.execute(
                    text(f"DELETE FROM {self.db_schema}.system_configs WHERE config_key = :config_key"),
                    {"config_key": config_key}
                )
                conn.commit()
                return True
        except Exception:
            return False


# 创建全局实例
config_repository = ConfigRepository()
