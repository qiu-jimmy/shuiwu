"""
用户角色数据访问层
处理用户角色相关的数据库操作
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.engine import Engine


class RoleRepository:
    """用户角色数据访问类"""

    def __init__(self):
        self.sync_engine = None

    def _get_sync_engine(self) -> Engine:
        """获取同步数据库引擎"""
        if self.sync_engine is None:
            from app.infra.db import get_sync_engine
            self.sync_engine = get_sync_engine()
        return self.sync_engine

    # ==================== 用户角色操作 ====================

    def get_user_roles(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的所有角色"""
        engine = self._get_sync_engine()
        with engine.connect() as conn:
            results = conn.execute(
                text("""
                    SELECT
                        id, user_id, role, permissions, status,
                        created_at, updated_at, created_by
                    FROM business.user_roles
                    WHERE user_id = :user_id AND status = 'active'
                    ORDER BY created_at
                """),
                {"user_id": user_id}
            ).fetchall()

            roles = []
            for row in results:
                roles.append({
                    "id": row[0],
                    "user_id": row[1],
                    "role": row[2],
                    "permissions": row[3],  # 数组类型
                    "status": row[4],
                    "created_at": row[5],
                    "updated_at": row[6],
                    "created_by": row[7]
                })

            return roles

    def get_user_role_by_role(self, user_id: str, role: str) -> Optional[Dict[str, Any]]:
        """获取用户的指定角色"""
        engine = self._get_sync_engine()
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT
                        id, user_id, role, permissions, status,
                        created_at, updated_at, created_by
                    FROM business.user_roles
                    WHERE user_id = :user_id AND role = :role
                """),
                {"user_id": user_id, "role": role}
            ).fetchone()

            if not result:
                return None

            return {
                "id": result[0],
                "user_id": result[1],
                "role": result[2],
                "permissions": result[3],
                "status": result[4],
                "created_at": result[5],
                "updated_at": result[6],
                "created_by": result[7]
            }

    def assign_role_to_user(
        self,
        user_id: str,
        role: str,
        permissions: List[str],
        created_by: Optional[str] = None
    ) -> bool:
        """给用户分配角色"""
        engine = self._get_sync_engine()
        with engine.connect() as conn:
            try:
                conn.execute(
                    text("""
                        INSERT INTO business.user_roles (
                            user_id, role, permissions, created_by, created_at, updated_at
                        ) VALUES (
                            :user_id, :role, :permissions, :created_by, :created_at, :updated_at
                        )
                        ON CONFLICT (user_id, role) DO UPDATE SET
                            permissions = EXCLUDED.permissions,
                            updated_at = EXCLUDED.updated_at
                    """),
                    {
                        "user_id": user_id,
                        "role": role,
                        "permissions": permissions,
                        "created_by": created_by,
                        "created_at": datetime.now(),
                        "updated_at": datetime.now()
                    }
                )
                conn.commit()
                return True
            except Exception as e:
                conn.rollback()
                raise e

    def remove_role_from_user(self, user_id: str, role: str) -> bool:
        """移除用户的角色"""
        engine = self._get_sync_engine()
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    DELETE FROM business.user_roles
                    WHERE user_id = :user_id AND role = :role
                """),
                {"user_id": user_id, "role": role}
            )
            conn.commit()
            return result.rowcount > 0

    def update_user_permissions(
        self,
        user_id: str,
        role: str,
        permissions: List[str]
    ) -> bool:
        """更新用户的权限"""
        engine = self._get_sync_engine()
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    UPDATE business.user_roles
                    SET permissions = :permissions, updated_at = :updated_at
                    WHERE user_id = :user_id AND role = :role
                """),
                {
                    "user_id": user_id,
                    "role": role,
                    "permissions": permissions,
                    "updated_at": datetime.now()
                }
            )
            conn.commit()
            return result.rowcount > 0

    def check_user_permission(self, user_id: str, required_permission: str) -> bool:
        """检查用户是否拥有指定权限"""
        engine = self._get_sync_engine()
        with engine.connect() as conn:
            # 检查是否有 */* 通配符权限（超级管理员）
            wildcard_check = conn.execute(
                text("""
                    SELECT 1 FROM business.user_roles
                    WHERE user_id = :user_id
                    AND status = 'active'
                    AND ':permission' = ANY(permissions)
                    LIMIT 1
                """),
                {"user_id": user_id, "permission": "*/*"}
            ).fetchone()

            if wildcard_check:
                return True

            # 检查具体权限
            permission_check = conn.execute(
                text("""
                    SELECT 1 FROM business.user_roles
                    WHERE user_id = :user_id
                    AND status = 'active'
                    AND :required_permission = ANY(permissions)
                    LIMIT 1
                """),
                {"user_id": user_id, "required_permission": required_permission}
            ).fetchone()

            return permission_check is not None

    # ==================== 角色定义操作 ====================

    def get_role_definitions(self) -> List[Dict[str, Any]]:
        """获取所有角色定义"""
        engine = self._get_sync_engine()
        with engine.connect() as conn:
            results = conn.execute(
                text("""
                    SELECT
                        role, role_name, description, default_permissions,
                        is_system, created_at, updated_at
                    FROM business.role_definitions
                    ORDER BY role
                """)
            ).fetchall()

            definitions = []
            for row in results:
                definitions.append({
                    "role": row[0],
                    "role_name": row[1],
                    "description": row[2],
                    "default_permissions": row[3],
                    "is_system": row[4],
                    "created_at": row[5],
                    "updated_at": row[6]
                })

            return definitions

    def get_role_definition(self, role: str) -> Optional[Dict[str, Any]]:
        """获取指定角色的定义"""
        engine = self._get_sync_engine()
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT
                        role, role_name, description, default_permissions,
                        is_system, created_at, updated_at
                    FROM business.role_definitions
                    WHERE role = :role
                """),
                {"role": role}
            ).fetchone()

            if not result:
                return None

            return {
                "role": result[0],
                "role_name": result[1],
                "description": result[2],
                "default_permissions": result[3],
                "is_system": result[4],
                "created_at": result[5],
                "updated_at": result[6]
            }

    # ==================== 用户角色操作日志 ====================

    def create_action_log(
        self,
        user_id: str,
        username: str,
        action_type: str,
        action_module: str,
        action_detail: Optional[Dict[str, Any]] = None,
        target_user_id: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_method: Optional[str] = None,
        request_path: Optional[str] = None,
        response_status: Optional[int] = None,
        response_message: Optional[str] = None
    ) -> str:
        """创建用户角色操作日志"""
        import json
        import uuid

        engine = self._get_sync_engine()
        log_id = str(uuid.uuid4())

        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO business.user_role_action_logs (
                        id, user_id, username, action_type, action_module,
                        action_detail, target_user_id, target_type, target_id,
                        ip_address, user_agent, request_method, request_path,
                        response_status, response_message, created_at
                    ) VALUES (
                        :id, :user_id, :username, :action_type, :action_module,
                        :action_detail, :target_user_id, :target_type, :target_id,
                        :ip_address, :user_agent, :request_method, :request_path,
                        :response_status, :response_message, :created_at
                    )
                """),
                {
                    "id": log_id,
                    "user_id": user_id,
                    "username": username,
                    "action_type": action_type,
                    "action_module": action_module,
                    "action_detail": json.dumps(action_detail) if action_detail else None,
                    "target_user_id": target_user_id,
                    "target_type": target_type,
                    "target_id": target_id,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "request_method": request_method,
                    "request_path": request_path,
                    "response_status": response_status,
                    "response_message": response_message,
                    "created_at": datetime.now()
                }
            )
            conn.commit()

        return log_id

    def get_action_logs(
        self,
        user_id: Optional[str] = None,
        action_module: Optional[str] = None,
        action_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """获取用户角色操作日志"""
        engine = self._get_sync_engine()

        # 构建查询条件
        conditions = []
        params = {"limit": page_size, "offset": (page - 1) * page_size}

        if user_id:
            conditions.append("user_id = :user_id")
            params["user_id"] = user_id

        if action_module:
            conditions.append("action_module = :action_module")
            params["action_module"] = action_module

        if action_type:
            conditions.append("action_type = :action_type")
            params["action_type"] = action_type

        if start_date:
            conditions.append("created_at >= :start_date")
            params["start_date"] = start_date

        if end_date:
            conditions.append("created_at <= :end_date")
            params["end_date"] = end_date

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        with engine.connect() as conn:
            # 查询总数
            count_result = conn.execute(
                text(f"""
                    SELECT COUNT(*)
                    FROM business.user_role_action_logs
                    WHERE {where_clause}
                """),
                params
            ).fetchone()

            total = count_result[0] if count_result else 0

            # 查询日志列表
            results = conn.execute(
                text(f"""
                    SELECT
                        id, user_id, username, action_type, action_module,
                        action_detail, target_user_id, target_type, target_id,
                        ip_address, request_method, request_path,
                        response_status, created_at
                    FROM business.user_role_action_logs
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                    LIMIT :limit OFFSET :offset
                """),
                params
            ).fetchall()

            logs = []
            for row in results:
                logs.append({
                    "id": row[0],
                    "user_id": row[1],
                    "username": row[2],
                    "action_type": row[3],
                    "action_module": row[4],
                    "action_detail": row[5],
                    "target_user_id": row[6],
                    "target_type": row[7],
                    "target_id": row[8],
                    "ip_address": row[9],
                    "request_method": row[10],
                    "request_path": row[11],
                    "response_status": row[12],
                    "created_at": row[13]
                })

            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "logs": logs
            }


# 全局角色仓库实例
role_repository = RoleRepository()
