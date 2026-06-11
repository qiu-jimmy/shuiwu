"""
MCP 数据访问层（Repository）
处理所有与数据库相关的操作
"""
import json
from typing import Any, Dict, Optional

from sqlalchemy import text

from app.infra.db import get_sync_engine


class MCPRepository:
    """MCP数据访问层"""
    
    def __init__(self, db_schema: str = "mcp"):
        self.db_schema = db_schema
        self._db_initialized = False
    
    def ensure_database_initialized(self):
        """初始化数据库（创建schema和表）"""
        if self._db_initialized:
            return

        import time
        start_time = time.time()

        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                # 创建schema
                conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {self.db_schema}"))
                conn.commit()
                
                # 创建MCP服务配置表
                conn.execute(text(f"""
                    CREATE TABLE IF NOT EXISTS {self.db_schema}.services (
                        service_id VARCHAR(50) PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        transport VARCHAR(20) NOT NULL,
                        command TEXT,
                        url TEXT,
                        env JSONB,
                        include_tools JSONB,
                        exclude_tools JSONB,
                        timeout_seconds INTEGER DEFAULT 30,
                        config JSONB NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                conn.commit()
                
                # 初始化默认服务配置
                self._init_default_services(conn)
            
            self._db_initialized = True

            elapsed = time.time() - start_time
            print(f"MCP数据库初始化完成，耗时: {elapsed:.2f}秒")

        except Exception as e:
            elapsed = time.time() - start_time
            print(f"初始化MCP数据库时出错（耗时: {elapsed:.2f}秒）: {e}")
    
    def _init_default_services(self, conn):
        """初始化默认的MCP服务配置"""
        fixed_service_id = "enterprise-risk-service"
        old_service_id = "bid-tender-service"
        fixed_config = {
            "name": "企业风险查询服务",
            "transport": "streamable-http",
            "url": "https://dashscope.aliyuncs.com/api/v1/mcps/market-cmapi00071991/mcp",
            "aliyun_api_key": "sk-c9b8659683a541bfaa8580448ca67766",
            "timeout_seconds": 180
        }
        
        check_sql = text(f"SELECT service_id FROM {self.db_schema}.services WHERE service_id = :service_id")
        existing_new = conn.execute(check_sql, {"service_id": fixed_service_id}).fetchone()
        existing_old = conn.execute(check_sql, {"service_id": old_service_id}).fetchone()
        
        if existing_old and not existing_new:
            # 迁移：将旧服务更新为新服务
            conn.execute(text(f"""
                UPDATE {self.db_schema}.services
                SET service_id = :new_service_id, name = :name, transport = :transport,
                    url = :url, env = :env, timeout_seconds = :timeout_seconds,
                    config = :config, updated_at = CURRENT_TIMESTAMP
                WHERE service_id = :old_service_id
            """), {
                "new_service_id": fixed_service_id,
                "old_service_id": old_service_id,
                "name": fixed_config["name"],
                "transport": fixed_config["transport"],
                "url": fixed_config["url"],
                "env": json.dumps({}),
                "timeout_seconds": fixed_config["timeout_seconds"],
                "config": json.dumps(fixed_config)
            })
            conn.commit()
        elif not existing_new:
            # 插入新的企业风险查询服务
            conn.execute(text(f"""
                INSERT INTO {self.db_schema}.services
                (service_id, name, transport, url, env, timeout_seconds, config)
                VALUES (:service_id, :name, :transport, :url, :env, :timeout_seconds, :config)
            """), {
                "service_id": fixed_service_id,
                "name": fixed_config["name"],
                "transport": fixed_config["transport"],
                "url": fixed_config["url"],
                "env": json.dumps({}),
                "timeout_seconds": fixed_config["timeout_seconds"],
                "config": json.dumps(fixed_config)
            })
            conn.commit()
        
        if existing_old and existing_new:
            # 删除旧服务
            conn.execute(
                text(f"DELETE FROM {self.db_schema}.services WHERE service_id = :old_service_id"),
                {"old_service_id": old_service_id}
            )
            conn.commit()
    
    def get_service_config(self, service_id: str) -> Optional[Dict[str, Any]]:
        """从数据库获取MCP服务配置"""
        self.ensure_database_initialized()
        
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                row = conn.execute(
                    text(f"SELECT config FROM {self.db_schema}.services WHERE service_id = :service_id"),
                    {"service_id": service_id}
                ).fetchone()
                
                if row:
                    return json.loads(row.config) if isinstance(row.config, str) else row.config
                return None
        except Exception as e:
            print(f"获取MCP服务配置失败: {e}")
            return None
    
    def list_all_services(self) -> Dict[str, Dict[str, Any]]:
        """从数据库列出所有服务及其配置"""
        self.ensure_database_initialized()
        
        result = {}
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                rows = conn.execute(
                    text(f"SELECT service_id, config FROM {self.db_schema}.services ORDER BY created_at DESC")
                ).fetchall()
            
            for row in rows:
                config = json.loads(row.config) if isinstance(row.config, str) else row.config
                result[row.service_id] = {
                    "config": config,
                    "status": "created"  # 默认状态，实际状态由服务管理器管理
                }
        except Exception as e:
            print(f"列出MCP服务失败: {e}")
        
        return result
    
    def init_schema_only(self):
        """仅初始化数据库schema（用于测试服务）"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {self.db_schema}"))
                conn.commit()
        except Exception as e:
            print(f"初始化MCP数据库schema时出错（可能已存在）: {e}")


# 全局Repository实例
mcp_repository = MCPRepository()

