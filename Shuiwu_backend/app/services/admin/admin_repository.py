"""
管理员数据访问层
处理管理员相关的数据库操作
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.engine import Engine


class AdminRepository:
    """管理员数据访问类"""

    def __init__(self):
        self.sync_engine = None

    def _get_sync_engine(self) -> Engine:
        """获取同步数据库引擎"""
        if self.sync_engine is None:
            from app.infra.db import get_sync_engine
            self.sync_engine = get_sync_engine()
        return self.sync_engine

    # ==================== 管理员操作 ====================

    def get_admin_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """通过用户名获取管理员"""
        engine = self._get_sync_engine()
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT
                        admin_id, username, password_hash, nickname, avatar_url,
                        email, phone, role, permissions, status,
                        last_login_time, last_login_ip, failed_login_count,
                        locked_until, created_at, updated_at, created_by
                    FROM business.admins
                    WHERE username = :username
                """),
                {"username": username}
            ).fetchone()

            if not result:
                return None

            return {
                "admin_id": result[0],
                "username": result[1],
                "password_hash": result[2],
                "nickname": result[3],
                "avatar_url": result[4],
                "email": result[5],
                "phone": result[6],
                "role": result[7],
                "permissions": result[8],  # 这是数组类型
                "status": result[9],
                "last_login_time": result[10],
                "last_login_ip": result[11],
                "failed_login_count": result[12],
                "locked_until": result[13],
                "created_at": result[14],
                "updated_at": result[15],
                "created_by": result[16]
            }

    def get_admin_by_id(self, admin_id: str) -> Optional[Dict[str, Any]]:
        """通过ID获取管理员"""
        engine = self._get_sync_engine()
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT
                        admin_id, username, password_hash, nickname, avatar_url,
                        email, phone, role, permissions, status,
                        last_login_time, last_login_ip, failed_login_count,
                        locked_until, created_at, updated_at, created_by
                    FROM business.admins
                    WHERE admin_id = :admin_id
                """),
                {"admin_id": admin_id}
            ).fetchone()

            if not result:
                return None

            return {
                "admin_id": result[0],
                "username": result[1],
                "password_hash": result[2],
                "nickname": result[3],
                "avatar_url": result[4],
                "email": result[5],
                "phone": result[6],
                "role": result[7],
                "permissions": result[8],
                "status": result[9],
                "last_login_time": result[10],
                "last_login_ip": result[11],
                "failed_login_count": result[12],
                "locked_until": result[13],
                "created_at": result[14],
                "updated_at": result[15],
                "created_by": result[16]
            }

    def update_admin_login(
        self,
        admin_id: str,
        last_login_time: datetime,
        last_login_ip: str,
        reset_failed_count: bool = True
    ) -> bool:
        """更新管理员登录信息"""
        engine = self._get_sync_engine()
        with engine.connect() as conn:
            update_fields = {
                "last_login_time": last_login_time,
                "last_login_ip": last_login_ip,
                "updated_at": datetime.now()
            }

            if reset_failed_count:
                update_fields["failed_login_count"] = 0
                update_fields["locked_until"] = None

            conn.execute(
                text("""
                    UPDATE business.admins
                    SET last_login_time = :last_login_time,
                        last_login_ip = :last_login_ip,
                        failed_login_count = :failed_login_count,
                        locked_until = :locked_until,
                        updated_at = :updated_at
                    WHERE admin_id = :admin_id
                """),
                {**update_fields, "admin_id": admin_id}
            )
            conn.commit()
            return True

    def increment_failed_login(self, admin_id: str) -> int:
        """增加登录失败次数"""
        engine = self._get_sync_engine()
        with engine.connect() as conn:
            conn.execute(
                text("""
                    UPDATE business.admins
                    SET failed_login_count = failed_login_count + 1,
                        updated_at = :updated_at
                    WHERE admin_id = :admin_id
                """),
                {"admin_id": admin_id, "updated_at": datetime.now()}
            )
            conn.commit()

            # 获取更新后的失败次数
            result = conn.execute(
                text("SELECT failed_login_count FROM business.admins WHERE admin_id = :admin_id"),
                {"admin_id": admin_id}
            ).fetchone()

            return result[0] if result else 0

    # ==================== 管理员操作日志 ====================

    def create_admin_action_log(
        self,
        admin_id: str,
        admin_name: str,
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
        """创建管理员操作日志"""
        import json
        import uuid

        engine = self._get_sync_engine()
        log_id = str(uuid.uuid4())

        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO business.admin_action_logs (
                        id, admin_id, admin_name, action_type, action_module,
                        action_detail, target_user_id, target_type, target_id,
                        ip_address, user_agent, request_method, request_path,
                        response_status, response_message, created_at
                    ) VALUES (
                        :id, :admin_id, :admin_name, :action_type, :action_module,
                        :action_detail, :target_user_id, :target_type, :target_id,
                        :ip_address, :user_agent, :request_method, :request_path,
                        :response_status, :response_message, :created_at
                    )
                """),
                {
                    "id": log_id,
                    "admin_id": admin_id,
                    "admin_name": admin_name,
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

    def get_admin_action_logs(
        self,
        admin_id: Optional[str] = None,
        action_module: Optional[str] = None,
        action_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """获取管理员操作日志"""
        engine = self._get_sync_engine()

        # 构建查询条件
        conditions = []
        params = {"limit": page_size, "offset": (page - 1) * page_size}

        if admin_id:
            conditions.append("admin_id = :admin_id")
            params["admin_id"] = admin_id

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
                    FROM business.admin_action_logs
                    WHERE {where_clause}
                """),
                params
            ).fetchone()

            total = count_result[0] if count_result else 0

            # 查询日志列表
            results = conn.execute(
                text(f"""
                    SELECT
                        id, admin_id, admin_name, action_type, action_module,
                        action_detail, target_user_id, target_type, target_id,
                        ip_address, request_method, request_path,
                        response_status, created_at
                    FROM business.admin_action_logs
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
                    "admin_id": row[1],
                    "admin_name": row[2],
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


# 全局管理员仓库实例
admin_repository = AdminRepository()
