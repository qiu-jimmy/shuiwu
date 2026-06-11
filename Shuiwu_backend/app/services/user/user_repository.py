"""
用户管理 - 数据访问层
"""
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import text
from app.infra.db import get_sync_engine


class UserRepository:
    """用户数据访问层"""

    def __init__(self, db_schema: str = "business"):
        self.db_schema = db_schema

    def create_user(self, user_data: Dict[str, Any]) -> Optional[str]:
        """创建用户"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                # 构建动态SQL，只插入提供的字段
                columns = []
                values = []

                for key, value in user_data.items():
                    if value is not None:
                        columns.append(key)
                        values.append(f":{key}")

                sql = f"""
                    INSERT INTO {self.db_schema}.users
                    ({', '.join(columns)})
                    VALUES ({', '.join(values)})
                    RETURNING user_id
                """

                result = conn.execute(text(sql), user_data)
                row = result.fetchone()
                conn.commit()
                return row[0] if row else None
        except Exception as e:
            print(f"创建用户失败: {e}")
            return None

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """根据用户ID获取用户"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                row = conn.execute(text(f"""
                    SELECT * FROM {self.db_schema}.users WHERE user_id = :user_id
                """), {"user_id": user_id}).fetchone()

                if row:
                    return dict(row._mapping)
                return None
        except Exception as e:
            print(f"获取用户失败: {e}")
            return None

    def get_user_by_wx_openid(self, wx_openid: str) -> Optional[Dict[str, Any]]:
        """根据微信OpenID获取用户"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                row = conn.execute(text(f"""
                    SELECT * FROM {self.db_schema}.users WHERE wx_openid = :wx_openid
                """), {"wx_openid": wx_openid}).fetchone()

                if row:
                    return dict(row._mapping)
                return None
        except Exception as e:
            print(f"根据微信OpenID获取用户失败: {e}")
            return None

    def get_user_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """根据手机号获取用户"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                row = conn.execute(text(f"""
                    SELECT * FROM {self.db_schema}.users WHERE phone = :phone
                """), {"phone": phone}).fetchone()

                if row:
                    return dict(row._mapping)
                return None
        except Exception as e:
            print(f"根据手机号获取用户失败: {e}")
            return None

    def update_user(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        """更新用户信息"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                update_fields = []
                params = {"user_id": user_id}

                for key, value in update_data.items():
                    if value is not None:
                        update_fields.append(f"{key} = :{key}")
                        params[key] = value

                if update_fields:
                    params["updated_at"] = datetime.now()
                    update_fields.append("updated_at = :updated_at")

                    sql = f"""
                        UPDATE {self.db_schema}.users
                        SET {', '.join(update_fields)}
                        WHERE user_id = :user_id
                    """
                    conn.execute(text(sql), params)
                    conn.commit()
                    return True
            return False
        except Exception as e:
            print(f"更新用户失败: {e}")
            return False

    def update_user_status(self, user_id: str, status: str, reason: Optional[str] = None) -> bool:
        """更新用户状态"""
        return self.update_user(user_id, {"status": status})

    def list_users(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        member_level: Optional[str] = None,
        user_type: Optional[str] = None,
        keyword: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取用户列表"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                # 构建查询条件
                conditions = []
                params = {"limit": page_size, "offset": (page - 1) * page_size}

                if status:
                    conditions.append("status = :status")
                    params["status"] = status
                if member_level:
                    conditions.append("member_level = :member_level")
                    params["member_level"] = member_level
                if user_type:
                    conditions.append("user_type = :user_type")
                    params["user_type"] = user_type
                if keyword:
                    conditions.append("(nickname ILIKE :keyword OR phone ILIKE :keyword)")
                    params["keyword"] = f"%{keyword}%"

                where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

                # 查询总数
                count_sql = f"""
                    SELECT COUNT(*) FROM {self.db_schema}.users
                    {where_clause}
                """
                total = conn.execute(text(count_sql), params).scalar()

                # 查询列表
                list_sql = f"""
                    SELECT * FROM {self.db_schema}.users
                    {where_clause}
                    ORDER BY created_at DESC
                    LIMIT :limit OFFSET :offset
                """
                rows = conn.execute(text(list_sql), params).fetchall()

                return {
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "users": [dict(row._mapping) for row in rows]
                }
        except Exception as e:
            print(f"获取用户列表失败: {e}")
            return {"total": 0, "page": page, "page_size": page_size, "users": []}

    def add_user_tag(self, user_id: str, tag_name: str, tag_type: str = "custom") -> bool:
        """添加用户标签"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                conn.execute(text(f"""
                    INSERT INTO {self.db_schema}.user_tags (user_id, tag_name, tag_type)
                    VALUES (:user_id, :tag_name, :tag_type)
                    ON CONFLICT (user_id, tag_name) DO NOTHING
                """), {"user_id": user_id, "tag_name": tag_name, "tag_type": tag_type})
                conn.commit()
                return True
        except Exception as e:
            print(f"添加用户标签失败: {e}")
            return False

    def get_user_tags(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户标签"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                rows = conn.execute(text(f"""
                    SELECT * FROM {self.db_schema}.user_tags
                    WHERE user_id = :user_id
                    ORDER BY created_at DESC
                """), {"user_id": user_id}).fetchall()
                return [dict(row._mapping) for row in rows]
        except Exception as e:
            print(f"获取用户标签失败: {e}")
            return []

    def remove_user_tag(self, user_id: str, tag_name: str) -> bool:
        """删除用户标签"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                conn.execute(text(f"""
                    DELETE FROM {self.db_schema}.user_tags
                    WHERE user_id = :user_id AND tag_name = :tag_name
                """), {"user_id": user_id, "tag_name": tag_name})
                conn.commit()
                return True
        except Exception as e:
            print(f"删除用户标签失败: {e}")
            return False

    def log_user_action(
        self,
        user_id: str,
        action_type: str,
        action_module: str,
        action_detail: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """记录用户行为日志"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                conn.execute(text(f"""
                    INSERT INTO {self.db_schema}.user_action_logs
                    (user_id, action_type, action_module, action_detail, ip_address, user_agent)
                    VALUES (:user_id, :action_type, :action_module, :action_detail, :ip_address, :user_agent)
                """), {
                    "user_id": user_id,
                    "action_type": action_type,
                    "action_module": action_module,
                    "action_detail": json.dumps(action_detail) if action_detail else None,
                    "ip_address": ip_address,
                    "user_agent": user_agent
                })
                conn.commit()
                return True
        except Exception as e:
            print(f"记录用户行为日志失败: {e}")
            return False

    def get_user_action_logs(
        self,
        user_id: Optional[str] = None,
        action_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """获取用户行为日志"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                conditions = []
                params = {"limit": page_size, "offset": (page - 1) * page_size}

                if user_id:
                    conditions.append("user_id = :user_id")
                    params["user_id"] = user_id
                if action_type:
                    conditions.append("action_type = :action_type")
                    params["action_type"] = action_type

                where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

                # 查询总数
                count_sql = f"""
                    SELECT COUNT(*) FROM {self.db_schema}.user_action_logs
                    {where_clause}
                """
                total = conn.execute(text(count_sql), params).scalar()

                # 查询列表
                list_sql = f"""
                    SELECT * FROM {self.db_schema}.user_action_logs
                    {where_clause}
                    ORDER BY created_at DESC
                    LIMIT :limit OFFSET :offset
                """
                rows = conn.execute(text(list_sql), params).fetchall()

                # 解析JSON字段
                logs = []
                for row in rows:
                    log_dict = dict(row._mapping)
                    if log_dict.get("action_detail"):
                        try:
                            log_dict["action_detail"] = json.loads(log_dict["action_detail"])
                        except:
                            pass
                    logs.append(log_dict)

                return {
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "logs": logs
                }
        except Exception as e:
            print(f"获取用户行为日志失败: {e}")
            return {"total": 0, "page": page, "page_size": page_size, "logs": []}


# 全局实例
user_repository = UserRepository()
