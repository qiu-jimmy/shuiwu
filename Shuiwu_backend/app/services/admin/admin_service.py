"""
管理员服务
处理管理员登录、用户管理、系统统计等业务逻辑

**新版管理员系统说明**：
- 用户基本信息存储在 business.users 表
- 角色权限信息存储在 business.user_roles 表
- 管理员身份通过拥有 admin 或 super_admin 角色来确定
- 登录时使用 user_id 作为标识符（admin_id 向后兼容 = user_id）
"""
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, date
from sqlalchemy import text

from app.services.user.user_repository import user_repository
from app.services.member.member_service import member_service
from app.services.knowledge.knowledge_repository import knowledge_repository
from app.services.distribution.distribution_service import distribution_service
from app.services.role.role_service import role_service
from app.utils.jwt_utils import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from app.schemas.admin import AdminInfo


def _get_engine():
    """延迟导入 get_sync_engine，避免模块级别导入"""
    from app.infra.db import get_sync_engine
    return get_sync_engine()


class AdminService:
    """管理员服务类 - 使用新的 user_roles 表系统"""

    def __init__(self):
        # 备用默认管理员账户（数据库不可用时使用）
        self.fallback_admin = {
            "user_id": "admin_001",
            "username": "admin",
            "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5ND7y.Ks0qW0m",  # admin123
            "nickname": "系统管理员",
            "role": "super_admin",
            "permissions": [
                "user.manage", "user.view",
                "member.manage", "member.view",
                "knowledge.manage", "knowledge.view",
                "mcp.manage", "mcp.view",
                "distribution.manage", "distribution.view",
                "order.view", "order.manage",
                "system.manage", "system.view",
                "log.view",
                "admin.manage",
                "*/*"  # 超级管理员通配符
            ],
            "created_at": datetime.now(),
            "last_login_time": None
        }

    def _get_user_by_username_for_login(self, username: str) -> Optional[Dict[str, Any]]:
        """
        通过手机号获取用户（用于登录）
        从 users 表获取基本信息，从 user_roles 表获取角色权限

        Returns:
            包含用户信息和角色权限的字典，如果用户不存在返回 None
        """
        try:
            engine = _get_engine()
            with engine.connect() as conn:
                # 1. 先查询 users 表获取基本信息
                # 只查询实际存在的字段（没有username和email字段）
                user = conn.execute(
                    text("""
                        SELECT
                            user_id, password_hash, nickname,
                            phone, avatar_url, status,
                            created_at, updated_at
                        FROM business.users
                        WHERE phone = :identifier
                        LIMIT 1
                    """),
                    {"identifier": username}
                ).fetchone()

                if not user:
                    return None

                # 2. 查询用户角色（从 user_roles 表）
                roles = conn.execute(
                    text("""
                        SELECT
                            role, permissions, status
                        FROM business.user_roles
                        WHERE user_id = :user_id AND status = 'active'
                        ORDER BY created_at
                    """),
                    {"user_id": user[0]}  # user_id
                ).fetchall()

                # 3. 检查是否有管理员角色
                role_list = []
                permissions_list = set()
                has_admin_role = False

                for role_row in roles:
                    role_name = role_row[0]
                    role_permissions = role_row[1]
                    role_status = role_row[2]

                    role_list.append(role_name)

                    # 合并权限
                    if role_permissions:
                        if isinstance(role_permissions, list):
                            permissions_list.update(role_permissions)

                    # 检查是否是管理员
                    if role_name in ("admin", "super_admin"):
                        has_admin_role = True

                # 如果没有管理员角色，返回 None（不是管理员）
                if not has_admin_role:
                    return None

                # 返回合并后的用户信息
                # 字段索引：0:user_id, 1:password_hash, 2:nickname, 3:phone, 4:avatar_url, 5:status, 6:created_at, 7:updated_at
                return {
                    "user_id": user[0],
                    "username": user[3],  # 使用 phone 作为 username
                    "password_hash": user[1],
                    "nickname": user[2],
                    "email": None,  # users表没有email字段
                    "phone": user[3],
                    "avatar_url": user[4],
                    "status": user[5],
                    "created_at": user[6],
                    "updated_at": user[7],
                    "roles": role_list,
                    "permissions": list(permissions_list),
                    "primary_role": role_list[0] if role_list else None
                }

        except Exception as e:
            # 发生错误时记录日志
            from app.utils.exception_logger import log_exception
            log_exception(e, extra_info={"operation": "get_user_for_login", "username": username}, level="WARNING")
            return None

    def login(self, username: str, password: str, ip_address: Optional[str] = None) -> Dict[str, Any]:
        """
        管理员登录（使用新的 user_roles 系统）

        Args:
            username: 用户名（实际是手机号）
            password: 密码
            ip_address: 登录IP地址（可选）

        Returns:
            登录结果，包含 access_token 和 admin_info
        """
        try:
            # 1. 尝试从数据库获取用户信息（users + user_roles）
            admin = self._get_user_by_username_for_login(username)

            if not admin:
                # 数据库中没有,尝试备用管理员
                if username == self.fallback_admin["username"]:
                    admin = self.fallback_admin
                else:
                    return {
                        "success": False,
                        "error": "用户名或密码错误",
                        "error_code": "INVALID_CREDENTIALS"
                    }

            # 2. 检查用户状态
            if admin.get("status") == "disabled":
                return {
                    "success": False,
                    "error": "管理员账户已被禁用",
                    "error_code": "ADMIN_DISABLED"
                }

            if admin.get("status") == "banned":
                return {
                    "success": False,
                    "error": "管理员账户已被封禁",
                    "error_code": "ADMIN_BANNED"
                }

            # 3. 验证密码
            password_hash = admin.get("password_hash", "")
            if not password_hash or not verify_password(password, password_hash):
                return {
                    "success": False,
                    "error": "用户名或密码错误",
                    "error_code": "INVALID_CREDENTIALS"
                }

            # 4. 获取用户标识符
            user_id = admin.get("user_id") or admin.get("admin_id")
            primary_role = admin.get("primary_role") or admin.get("role")

            # 5. 生成JWT token
            access_token = create_access_token(
                data={
                    "sub": user_id,
                    "role": primary_role,
                    "is_admin": True  # 向后兼容
                },
                expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            )

            # 6. 更新最后登录时间（仅对于数据库用户）
            login_time = datetime.now()

            if user_id != self.fallback_admin.get("user_id"):
                try:
                    engine = _get_engine()
                    with engine.connect() as conn:
                        conn.execute(
                            text("""
                                UPDATE business.users
                                SET last_login_time = :login_time,
                                    updated_at = :updated_at
                                WHERE user_id = :user_id
                            """),
                            {
                                "user_id": user_id,
                                "login_time": login_time,
                                "updated_at": login_time
                            }
                        )
                        conn.commit()
                except Exception:
                    pass  # 更新失败不影响登录

                # 7. 记录登录日志（使用新的 user_role_action_logs 表）
                try:
                    role_service.create_action_log(
                        user_id=user_id,
                        action_type="login",
                        action_module="auth",
                        action_detail={"login_time": login_time.isoformat()},
                        ip_address=ip_address
                    )
                except Exception:
                    pass  # 记录日志失败不影响登录

            # 8. 构建管理员信息
            permissions = admin.get("permissions", [])
            if isinstance(permissions, str):
                permissions = []

            admin_info = AdminInfo(
                admin_id=user_id,  # admin_id = user_id
                username=admin["username"],
                nickname=admin.get("nickname"),
                role=primary_role,
                permissions=permissions,
                created_at=admin.get("created_at"),
                last_login_time=login_time
            )

            return {
                "success": True,
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                "admin_info": admin_info
            }

        except Exception as e:
            # 发生异常时,尝试使用备用管理员
            if username == self.fallback_admin["username"] and verify_password(password, self.fallback_admin["password_hash"]):
                access_token = create_access_token(
                    data={
                        "sub": self.fallback_admin["user_id"],
                        "role": self.fallback_admin["role"],
                        "is_admin": True
                    },
                    expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
                )

                admin_info = AdminInfo(
                    admin_id=self.fallback_admin["user_id"],
                    username=self.fallback_admin["username"],
                    nickname=self.fallback_admin["nickname"],
                    role=self.fallback_admin["role"],
                    permissions=self.fallback_admin["permissions"],
                    created_at=self.fallback_admin["created_at"],
                    last_login_time=datetime.now()
                )

                return {
                    "success": True,
                    "access_token": access_token,
                    "token_type": "bearer",
                    "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                    "admin_info": admin_info
                }

            # 记录异常日志并重新抛出
            from app.utils.exception_logger import log_exception
            log_exception(e, extra_info={"operation": "admin_login", "username": username}, level="ERROR")
            raise

    # ==================== 用户管理 ====================

    def create_user(
        self,
        phone: str,
        nickname: Optional[str] = None,
        password: Optional[str] = None,
        status: str = "normal",
        user_type: str = "individual",
        member_level: str = "free",
        member_expire_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        管理员创建用户

        Args:
            phone: 手机号（必填）
            nickname: 昵称
            password: 密码（不填则默认123456）
            status: 用户状态
            user_type: 用户类型
            member_level: 会员等级
            member_expire_at: 会员到期时间

        Returns:
            创建结果，包含 user_id 和初始密码
        """
        # 1. 检查手机号是否已存在
        existing_user = user_repository.get_user_by_phone(phone)
        if existing_user:
            return {
                "success": False,
                "error": "该手机号已被注册",
                "error_code": "PHONE_EXISTS"
            }

        # 2. 验证状态值
        valid_statuses = ["normal", "disabled", "banned"]
        if status not in valid_statuses:
            return {
                "success": False,
                "error": f"无效的状态值，必须是: {', '.join(valid_statuses)}",
                "error_code": "INVALID_STATUS"
            }

        # 3. 验证用户类型
        valid_types = ["individual", "enterprise", "admin"]
        if user_type not in valid_types:
            return {
                "success": False,
                "error": f"无效的用户类型，必须是: {', '.join(valid_types)}",
                "error_code": "INVALID_USER_TYPE"
            }

        # 4. 验证会员等级 - 从套餐系统中获取有效的套餐ID
        packages_result = member_service.list_packages(status="active")
        if packages_result.get("success"):
            valid_levels = [pkg["package_id"] for pkg in packages_result.get("packages", [])]
        else:
            valid_levels = ["free", "basic", "premium", "enterprise"]

        if member_level not in valid_levels:
            return {
                "success": False,
                "error": f"无效的会员等级，必须是: {', '.join(valid_levels)}",
                "error_code": "INVALID_MEMBER_LEVEL"
            }

        # 5. 设置默认密码
        if not password:
            password = "123456"

        # 6. 生成密码哈希
        password_hash = get_password_hash(password)

        # 7. 生成用户ID
        import time
        user_id = f"user_{int(time.time() * 1000)}"

        # 8. 构建用户数据
        user_data = {
            "user_id": user_id,
            "phone": phone,
            "password_hash": password_hash,
            "nickname": nickname or phone[:4] + "****",  # 默认昵称
            "status": status,
            "user_type": user_type,
            "member_level": member_level,
            "member_expire_at": member_expire_at,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }

        # 9. 创建用户
        created_user_id = user_repository.create_user(user_data)

        if not created_user_id:
            return {
                "success": False,
                "error": "创建用户失败",
                "error_code": "CREATE_FAILED"
            }

        # 同步角色：如果 user_type 是 admin，自动添加 admin 角色
        # 直接在 user_roles 表中操作，不依赖 role_definitions
        if user_type == "admin":
            try:
                from app.infra.db import get_sync_engine
                from sqlalchemy import text
                engine = get_sync_engine()
                with engine.connect() as conn:
                    # 使用 */* 权限（超级管理员权限）
                    conn.execute(text("""
                        INSERT INTO business.user_roles (
                            user_id, role, permissions, status, created_at, updated_at
                        ) VALUES (
                            :user_id, 'admin', ARRAY['*/*'], 'active', :now, :now
                        )
                        ON CONFLICT (user_id, role) DO UPDATE SET
                            status = 'active',
                            updated_at = EXCLUDED.updated_at
                    """), {"user_id": created_user_id, "now": datetime.now()})
                    conn.commit()
            except Exception as e:
                # 角色同步失败，但不影响用户创建
                print(f"警告: 同步管理员角色失败 - {e}")

        # TODO: 记录管理员操作日志

        return {
            "success": True,
            "message": "用户创建成功",
            "user_id": created_user_id,
            "initial_password": password
        }

    def get_users(
        self,
        keyword: Optional[str] = None,
        status: Optional[str] = None,
        user_type: Optional[str] = None,
        member_level: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        获取用户列表（管理员视角）
        """
        # 调用用户仓库获取用户列表
        # UserRepository.list_users() 支持: page, page_size, status, member_level, user_type, keyword
        result = user_repository.list_users(
        page=page,

        page_size=page_size,

        status=status,

        member_level=member_level,

        user_type=user_type,

        keyword=keyword

        # 注意: start_date 和 end_date 当前不被 UserRepository.list_users() 支持

        # 如需日期范围过滤，需要扩展 UserRepository

        )

        return {
        "success": True,

        **result

        }


    def update_user_status(self, user_id: str, status: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """
        更新用户状态
        """
        # 验证状态值
        valid_statuses = ["normal", "disabled", "banned"]

        if status not in valid_statuses:

                return {
                    "success": False,
                    "error": f"无效的状态值，必须是: {', '.join(valid_statuses)}",
                    "error_code": "INVALID_STATUS"
                }

        # 检查用户是否存在

        user = user_repository.get_user_by_id(user_id)

        if not user:

                return {
                    "success": False,
                    "error": "用户不存在",
                    "error_code": "USER_NOT_FOUND"
                }

        # 更新用户状态

        user_repository.update_user(user_id, {"status": status})


        # TODO: 记录管理员操作日志


        return {

                "success": True,
                "message": f"用户状态已更新为: {status}"
        }



    def update_user_type(self, user_id: str, user_type: str) -> Dict[str, Any]:
        """
        更新用户类型
        当 user_type 设置为 admin 时，自动添加 admin 角色
        当 user_type 从 admin 改为其他值时，自动移除 admin 角色
        """
        # 验证用户类型值
        valid_types = ["individual", "enterprise", "admin"]

        if user_type not in valid_types:

                return {
                    "success": False,
                    "error": f"无效的用户类型，必须是: {', '.join(valid_types)}",
                    "error_code": "INVALID_USER_TYPE"
                }

        # 检查用户是否存在

        user = user_repository.get_user_by_id(user_id)

        if not user:

                return {
                    "success": False,
                    "error": "用户不存在",
                    "error_code": "USER_NOT_FOUND"
                }

        # 获取当前用户类型
        old_user_type = user.get("user_type", "individual")

        # 更新用户类型
        user_repository.update_user(user_id, {"user_type": user_type})

        # 同步角色：user_type 和 admin 角色保持一致
        # 直接在 user_roles 表中操作，不依赖 role_definitions
        from app.infra.db import get_sync_engine
        engine = get_sync_engine()

        try:
            with engine.connect() as conn:
                if user_type == "admin" and old_user_type != "admin":
                    # 从非管理员变为管理员：添加 admin 角色
                    # 使用 */* 权限（超级管理员权限）
                    conn.execute(text("""
                        INSERT INTO business.user_roles (
                            user_id, role, permissions, status, created_at, updated_at
                        ) VALUES (
                            :user_id, 'admin', ARRAY['*/*'], 'active', :now, :now
                        )
                        ON CONFLICT (user_id, role) DO UPDATE SET
                            status = 'active',
                            updated_at = EXCLUDED.updated_at
                    """), {"user_id": user_id, "now": datetime.now()})
                    conn.commit()

                elif user_type != "admin" and old_user_type == "admin":
                    # 从管理员变为非管理员：移除 admin 角色
                    conn.execute(text("""
                        DELETE FROM business.user_roles
                        WHERE user_id = :user_id AND role = 'admin'
                    """), {"user_id": user_id})
                    conn.commit()

        except Exception as e:
            # 角色同步失败，但不影响 user_type 更新
            print(f"警告: 同步角色失败 - {e}")

        # TODO: 记录管理员操作日志


        return {

                "success": True,
                "message": f"用户类型已更新为: {user_type}"
        }



    # ==================== 会员管理 ====================

    def update_user_member(
        self,
        user_id: str,
        member_level: str,
        member_expire_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        更新用户会员信息（管理员特权）
        """
        # 检查用户是否存在
        user = user_repository.get_user_by_id(user_id)

        if not user:

                return {
                    "success": False,
                    "error": "用户不存在",
                    "error_code": "USER_NOT_FOUND"
                }

        # 验证会员等级 - 从套餐系统中获取有效的套餐ID
        packages_result = member_service.list_packages(status="active")
        if packages_result.get("success"):
            valid_levels = [pkg["package_id"] for pkg in packages_result.get("packages", [])]
        else:
            valid_levels = ["free", "basic", "premium", "enterprise"]

        if member_level not in valid_levels:

                return {
                    "success": False,
                    "error": f"无效的会员等级，必须是: {', '.join(valid_levels)}",
                    "error_code": "INVALID_MEMBER_LEVEL"
                }

        # 更新会员信息
        # 如果是免费用户，member_expire_at 设置为 NULL
        # 注意：直接执行 SQL 而不是使用 user_repository.update_user
        # 因为 update_user 会跳过 None 值，无法清空 member_expire_at
        try:
            engine = _get_engine()
            with engine.connect() as conn:
                conn.execute(
                    text("""
                        UPDATE business.users
                        SET member_level = :member_level,
                            member_expire_at = :member_expire_at,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = :user_id
                    """),
                    {
                        "user_id": user_id,
                        "member_level": member_level,
                        "member_expire_at": member_expire_at
                    }
                )
                conn.commit()
        except Exception as e:
            from app.utils.exception_logger import log_exception
            log_exception(e, extra_info={"operation": "update_user_member", "user_id": user_id}, level="ERROR")
            return {
                "success": False,
                "error": "更新会员信息失败",
                "error_code": "UPDATE_FAILED"
            }


        # TODO: 记录管理员操作日志


        return {

                "success": True,
                "message": "会员信息已更新"
        }



    def get_all_orders(
        self,
        keyword: Optional[str] = None,
        payment_status: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        获取所有订单（管理员视角）
        """
        from app.services.member.member_repository import member_repository

        try:
            engine = _get_engine()
            with engine.connect() as conn:
                conditions = []
                params = {
                    "limit": page_size,
                    "offset": (page - 1) * page_size
                }

                # 关键词搜索（订单号或用户ID）
                if keyword:
                    conditions.append("(order_id LIKE :keyword OR user_id LIKE :keyword)")
                    params["keyword"] = f"%{keyword}%"

                # 支付状态筛选
                if payment_status:
                    conditions.append("payment_status = :payment_status")
                    params["payment_status"] = payment_status

                # 订单状态筛选
                if status:
                    conditions.append("status = :status")
                    params["status"] = status

                # 日期范围筛选
                if start_date:
                    conditions.append("created_at >= :start_date")
                    params["start_date"] = start_date
                if end_date:
                    conditions.append("created_at <= :end_date")
                    params["end_date"] = end_date

                where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

                # 查询总数
                count_sql = f"""
                    SELECT COUNT(*) FROM business.orders
                    {where_clause}
                """
                total = conn.execute(text(count_sql), params).scalar()

                # 查询订单列表
                list_sql = f"""
                    SELECT
                        order_id, user_id, package_id, order_type,
                        amount, actual_amount, payment_method, payment_status,
                        payment_time, transaction_id, package_name, duration_days,
                        original_expire_at, new_expire_at, status,
                        created_at, updated_at
                    FROM business.orders
                    {where_clause}
                    ORDER BY created_at DESC
                    LIMIT :limit OFFSET :offset
                """
                rows = conn.execute(text(list_sql), params).fetchall()

                orders = []
                for row in rows:
                    orders.append({
                        "order_id": row[0],
                        "user_id": row[1],
                        "package_id": row[2],
                        "order_type": row[3],
                        "amount": float(row[4]) if row[4] else 0,
                        "actual_amount": float(row[5]) if row[5] else None,
                        "payment_method": row[6],
                        "payment_status": row[7],
                        "payment_time": row[8].isoformat() if row[8] else None,
                        "transaction_id": row[9],
                        "package_name": row[10],
                        "duration_days": row[11],
                        "original_expire_at": row[12].isoformat() if row[12] else None,
                        "new_expire_at": row[13].isoformat() if row[13] else None,
                        "status": row[14],
                        "created_at": row[15].isoformat() if row[15] else None,
                        "updated_at": row[16].isoformat() if row[16] else None,
                    })

                return {
                    "success": True,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "orders": orders
                }

        except Exception as e:
            from app.utils.exception_logger import log_exception
            log_exception(e, extra_info={"operation": "get_all_orders"}, level="ERROR")
            return {
                "success": False,
                "error": "获取订单列表失败",
                "error_code": "GET_ORDERS_FAILED",
                "total": 0,
                "page": page,
                "page_size": page_size,
                "orders": []
            }

    def get_order_detail(
        self,
        order_id: int
    ) -> Dict[str, Any]:
        """
        获取订单详情（管理员视角）
        """
        try:
            engine = _get_engine()
            with engine.connect() as conn:
                # 查询订单详情
                sql = text("""
                    SELECT
                        o.order_id, o.order_no, o.user_id, u.nickname, u.phone,
                        o.package_id, o.package_name, o.duration_days,
                        o.amount, o.actual_amount, o.payment_method, o.payment_status,
                        o.payment_time, o.transaction_id, o.status,
                        o.order_type, o.original_expire_at, o.new_expire_at,
                        o.created_at, o.updated_at
                    FROM business.orders o
                    LEFT JOIN business.users u ON o.user_id = u.user_id
                    WHERE o.order_id = :order_id
                """)

                row = conn.execute(sql, {"order_id": order_id}).fetchone()

                if not row:
                    return {
                        "success": False,
                        "error": "订单不存在",
                        "error_code": "ORDER_NOT_FOUND"
                    }

                return {
                    "success": True,
                    "order": {
                        "id": row[0],
                        "order_no": row[1],
                        "user_id": row[2],
                        "username": row[3],
                        "phone": row[4],
                        "package_id": row[5],
                        "package_name": row[6],
                        "duration_days": row[7],
                        "amount": float(row[8]) if row[8] else 0,
                        "actual_amount": float(row[9]) if row[9] else 0,
                        "payment_method": row[10],
                        "payment_status": row[11],
                        "payment_time": row[12].isoformat() if row[12] else None,
                        "transaction_id": row[13],
                        "status": row[14],
                        "order_type": row[15],
                        "original_expire_at": row[16].isoformat() if row[16] else None,
                        "new_expire_at": row[17].isoformat() if row[17] else None,
                        "created_at": row[18].isoformat() if row[18] else None,
                        "updated_at": row[19].isoformat() if row[19] else None,
                    }
                }

        except Exception as e:
            from app.utils.exception_logger import log_exception
            log_exception(e, extra_info={"operation": "get_order_detail", "order_id": order_id}, level="ERROR")
            return {
                "success": False,
                "error": "获取订单详情失败",
                "error_code": "GET_ORDER_DETAIL_FAILED"
            }

    def update_order_status(
        self,
        order_id: int,
        status: str
    ) -> Dict[str, Any]:
        """
        更新订单状态（管理员视角）
        """
        # 验证状态值
        valid_statuses = ['pending', 'completed', 'cancelled', 'failed']
        if status not in valid_statuses:
            return {
                "success": False,
                "error": f"无效的状态值，必须是: {', '.join(valid_statuses)}",
                "error_code": "INVALID_STATUS"
            }

        try:
            engine = _get_engine()
            with engine.connect() as conn:
                # 检查订单是否存在
                order = conn.execute(
                    text("SELECT order_id, status FROM business.orders WHERE order_id = :order_id"),
                    {"order_id": order_id}
                ).fetchone()

                if not order:
                    return {
                        "success": False,
                        "error": "订单不存在",
                        "error_code": "ORDER_NOT_FOUND"
                    }

                old_status = order[1]

                # 更新状态
                conn.execute(
                    text("""
                        UPDATE business.orders
                        SET status = :status, updated_at = CURRENT_TIMESTAMP
                        WHERE order_id = :order_id
                    """),
                    {"status": status, "order_id": order_id}
                )
                conn.commit()

                return {
                    "success": True,
                    "message": f"订单状态已从 {old_status} 更新为 {status}"
                }

        except Exception as e:
            from app.utils.exception_logger import log_exception
            log_exception(e, extra_info={"operation": "update_order_status", "order_id": order_id}, level="ERROR")
            return {
                "success": False,
                "error": "更新订单状态失败",
                "error_code": "UPDATE_ORDER_STATUS_FAILED"
            }

    def update_order_payment_status(
        self,
        order_id: int,
        payment_status: str
    ) -> Dict[str, Any]:
        """
        更新订单支付状态（管理员视角）
        """
        # 验证支付状态值
        valid_statuses = ['unpaid', 'paid', 'refunded']
        if payment_status not in valid_statuses:
            return {
                "success": False,
                "error": f"无效的支付状态值，必须是: {', '.join(valid_statuses)}",
                "error_code": "INVALID_PAYMENT_STATUS"
            }

        try:
            engine = _get_engine()
            with engine.connect() as conn:
                # 检查订单是否存在
                order = conn.execute(
                    text("SELECT order_id, payment_status FROM business.orders WHERE order_id = :order_id"),
                    {"order_id": order_id}
                ).fetchone()

                if not order:
                    return {
                        "success": False,
                        "error": "订单不存在",
                        "error_code": "ORDER_NOT_FOUND"
                    }

                old_payment_status = order[1]

                # 更新支付状态
                conn.execute(
                    text("""
                        UPDATE business.orders
                        SET payment_status = :payment_status, updated_at = CURRENT_TIMESTAMP
                        WHERE order_id = :order_id
                    """),
                    {"payment_status": payment_status, "order_id": order_id}
                )
                conn.commit()

                return {
                    "success": True,
                    "message": f"支付状态已从 {old_payment_status} 更新为 {payment_status}"
                }

        except Exception as e:
            from app.utils.exception_logger import log_exception
            log_exception(e, extra_info={"operation": "update_order_payment_status", "order_id": order_id}, level="ERROR")
            return {
                "success": False,
                "error": "更新支付状态失败",
                "error_code": "UPDATE_PAYMENT_STATUS_FAILED"
            }

    def update_order_status_by_no(
        self,
        order_no: str,
        status: str
    ) -> Dict[str, Any]:
        """
        通过订单ID（字符串）更新订单状态
        注意：orders 表的 order_id 是字符串类型，如 'ORDFF421DAFCCCA410B'
        """
        # 验证状态值
        valid_statuses = ['pending', 'completed', 'cancelled', 'failed']
        if status not in valid_statuses:
            return {
                "success": False,
                "error": f"无效的状态值，必须是: {', '.join(valid_statuses)}",
                "error_code": "INVALID_STATUS"
            }

        try:
            engine = _get_engine()
            with engine.connect() as conn:
                # 检查订单是否存在
                order = conn.execute(
                    text("SELECT order_id, status FROM business.orders WHERE order_id = :order_id"),
                    {"order_id": order_no}
                ).fetchone()

                if not order:
                    return {
                        "success": False,
                        "error": "订单不存在",
                        "error_code": "ORDER_NOT_FOUND"
                    }

                old_status = order[1]

                # 更新状态
                conn.execute(
                    text("""
                        UPDATE business.orders
                        SET status = :status, updated_at = CURRENT_TIMESTAMP
                        WHERE order_id = :order_id
                    """),
                    {"status": status, "order_id": order_no}
                )
                conn.commit()

                return {
                    "success": True,
                    "message": f"订单 {order_no} 状态已从 {old_status} 更新为 {status}"
                }

        except Exception as e:
            from app.utils.exception_logger import log_exception
            log_exception(e, extra_info={"operation": "update_order_status_by_no", "order_no": order_no}, level="ERROR")
            return {
                "success": False,
                "error": "更新订单状态失败",
                "error_code": "UPDATE_ORDER_STATUS_FAILED"
            }

    def update_order_payment_status_by_no(
        self,
        order_no: str,
        payment_status: str
    ) -> Dict[str, Any]:
        """
        通过订单ID（字符串）更新订单支付状态
        注意：orders 表的 order_id 是字符串类型，如 'ORDFF421DAFCCCA410B'
        """
        # 验证支付状态值
        valid_statuses = ['unpaid', 'paid', 'refunded']
        if payment_status not in valid_statuses:
            return {
                "success": False,
                "error": f"无效的支付状态值，必须是: {', '.join(valid_statuses)}",
                "error_code": "INVALID_PAYMENT_STATUS"
            }

        try:
            engine = _get_engine()
            with engine.connect() as conn:
                # 检查订单是否存在
                order = conn.execute(
                    text("SELECT order_id, payment_status FROM business.orders WHERE order_id = :order_id"),
                    {"order_id": order_no}
                ).fetchone()

                if not order:
                    return {
                        "success": False,
                        "error": "订单不存在",
                        "error_code": "ORDER_NOT_FOUND"
                    }

                old_payment_status = order[1]

                # 更新支付状态
                conn.execute(
                    text("""
                        UPDATE business.orders
                        SET payment_status = :payment_status, updated_at = CURRENT_TIMESTAMP
                        WHERE order_id = :order_id
                    """),
                    {"payment_status": payment_status, "order_id": order_no}
                )
                conn.commit()

                return {
                    "success": True,
                    "message": f"订单 {order_no} 支付状态已从 {old_payment_status} 更新为 {payment_status}"
                }

        except Exception as e:
            from app.utils.exception_logger import log_exception
            log_exception(e, extra_info={"operation": "update_order_payment_status_by_no", "order_no": order_no}, level="ERROR")
            return {
                "success": False,
                "error": "更新支付状态失败",
                "error_code": "UPDATE_PAYMENT_STATUS_FAILED"
            }


    # ==================== 知识库管理 ====================

    def get_all_knowledge_bases(
        self,
        keyword: Optional[str] = None,
        is_system: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        获取所有知识库（管理员视角）
        """
        # 调用知识库仓库获取所有知识库
        result = knowledge_repository.list_all_knowledge_bases(

                keyword=keyword,
                is_system=is_system,
                page=page,
                page_size=page_size
        )


        return {

                "success": True,
                **result
        }



    # ==================== 分销管理 ====================

    def get_all_distributors(
        self,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        获取所有分销商（管理员视角）
        """
        # 调用分销服务获取所有分销商
        result = distribution_service.list_all_distributors(

                status=status,
                page=page,
                page_size=page_size
        )


        return {

                "success": True,
                **result
        }



    def handle_withdrawal(
        self,
        withdrawal_id: str,
        status: str,
        handle_result: Optional[str] = None,
        transaction_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        处理提现申请
        """
        # 验证状态
        valid_statuses = ["approved", "rejected"]

        if status not in valid_statuses:

                return {
                    "success": False,
                    "error": f"无效的状态，必须是: {', '.join(valid_statuses)}",
                    "error_code": "INVALID_STATUS"
                }

        # 调用分销服务处理提现

        result = distribution_service.handle_withdrawal(

                withdrawal_id=withdrawal_id,
                status=status,
                handle_result=handle_result,
                transaction_id=transaction_id
        )


        return result



    # ==================== 系统统计 ====================

    def get_system_stats(self) -> Dict[str, Any]:
        """
        获取系统统计数据（实际查询数据库）
        """
        try:
            engine = _get_engine()
            with engine.connect() as conn:
                # 今天的开始时间
                today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

                # 1. 总用户数
                try:
                    total_users = conn.execute(
                        text("SELECT COUNT(*) FROM business.users")
                    ).fetchone()[0]
                except Exception as e:
                    print(f"[统计错误] 查询总用户数失败: {e}")
                    total_users = 0

                # 2. 总会员数（从 users 表统计）
                # 统计所有 member_level 非 'free' 且未过期的用户
                try:
                    total_members = conn.execute(
                        text("""
                            SELECT COUNT(*) FROM business.users
                            WHERE member_level IS NOT NULL
                              AND member_level <> 'free'
                              AND (member_expire_at IS NULL OR member_expire_at > CURRENT_TIMESTAMP)
                        """)
                    ).fetchone()[0]
                except Exception as e:
                    print(f"[统计错误] 查询总会员数失败: {e}")
                    total_members = 0

                # 3. 总知识库数量（使用 knowledge schema）
                try:
                    total_knowledge_bases = conn.execute(
                        text("""
                            SELECT COUNT(*) FROM knowledge.knowledge_base_registry
                            WHERE deleted_at IS NULL
                        """)
                    ).fetchone()[0]
                except Exception as e:
                    print(f"[统计错误] 查询总知识库数失败: {e}")
                    total_knowledge_bases = 0

                # 4. 总订单数和总收入
                try:
                    order_stats = conn.execute(
                        text("""
                            SELECT
                                COUNT(*) as total_orders,
                                COALESCE(SUM(CASE WHEN payment_status = 'paid' THEN amount ELSE 0 END), 0) as total_revenue
                            FROM business.orders
                        """)
                    ).fetchone()
                    total_orders = order_stats[0]
                    total_revenue = float(order_stats[1]) if order_stats[1] else 0
                except Exception as e:
                    print(f"[统计错误] 查询订单统计失败: {e}")
                    total_orders = 0
                    total_revenue = 0.0

                # 5. 今日新增用户
                try:
                    today_new_users = conn.execute(
                        text("""
                            SELECT COUNT(*) FROM business.users
                            WHERE created_at >= :today_start
                        """),
                        {"today_start": today_start}
                    ).fetchone()[0]
                except Exception as e:
                    print(f"[统计错误] 查询今日新增用户失败: {e}")
                    today_new_users = 0

                # 6. 今日新增订单
                try:
                    today_order_stats = conn.execute(
                        text("""
                            SELECT
                                COUNT(*) as today_new_orders,
                                COALESCE(SUM(CASE WHEN payment_status = 'paid' THEN amount ELSE 0 END), 0) as today_revenue
                            FROM business.orders
                            WHERE created_at >= :today_start
                        """),
                        {"today_start": today_start}
                    ).fetchone()
                    today_new_orders = today_order_stats[0]
                    today_revenue = float(today_order_stats[1]) if today_order_stats[1] else 0
                except Exception as e:
                    print(f"[统计错误] 查询今日订单统计失败: {e}")
                    today_new_orders = 0
                    today_revenue = 0.0

                # 7. 活跃分销商数
                try:
                    active_distributors = conn.execute(
                        text("""
                            SELECT COUNT(*) FROM business.distributors
                            WHERE status = 'active'
                        """)
                    ).fetchone()[0]
                except Exception as e:
                    print(f"[统计错误] 查询活跃分销商数失败: {e}")
                    active_distributors = 0

                # 8. 本月新增用户
                month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                try:
                    month_new_users = conn.execute(
                        text("""
                            SELECT COUNT(*) FROM business.users
                            WHERE created_at >= :month_start
                        """),
                        {"month_start": month_start}
                    ).fetchone()[0]
                except Exception as e:
                    print(f"[统计错误] 查询本月新增用户失败: {e}")
                    month_new_users = 0

                # 9. 本月新增订单
                try:
                    month_order_stats = conn.execute(
                        text("""
                            SELECT
                                COUNT(*) as month_new_orders,
                                COALESCE(SUM(CASE WHEN payment_status = 'paid' THEN amount ELSE 0 END), 0) as month_revenue
                            FROM business.orders
                            WHERE created_at >= :month_start
                        """),
                        {"month_start": month_start}
                    ).fetchone()
                    month_new_orders = month_order_stats[0]
                    month_revenue = float(month_order_stats[1]) if month_order_stats[1] else 0
                except Exception as e:
                    print(f"[统计错误] 查询本月订单统计失败: {e}")
                    month_new_orders = 0
                    month_revenue = 0.0

                return {
                    "success": True,
                    # 总体统计
                    "total_users": total_users,
                    "total_members": total_members,
                    "total_knowledge_bases": total_knowledge_bases,
                    "total_orders": total_orders,
                    "total_revenue": total_revenue,
                    # 今日统计
                    "today_new_users": today_new_users,
                    "today_new_orders": today_new_orders,
                    "today_revenue": today_revenue,
                    # 本月统计
                    "month_new_users": month_new_users,
                    "month_new_orders": month_new_orders,
                    "month_revenue": month_revenue,
                    # 分销统计
                    "active_distributors": active_distributors
                }

        except Exception as e:
            # 记录详细错误信息
            from app.utils.exception_logger import log_exception
            log_exception(e, extra_info={"operation": "get_system_stats"}, level="ERROR")
            print(f"[统计错误] 获取系统统计数据失败: {e}")
            import traceback
            traceback.print_exc()

            return {
                "success": False,
                "error": str(e),
                "error_code": "STATS_QUERY_FAILED",
                "total_users": 0,
                "total_members": 0,
                "total_knowledge_bases": 0,
                "total_orders": 0,
                "total_revenue": 0.0,
                "today_new_users": 0,
                "today_new_orders": 0,
                "today_revenue": 0.0,
                "month_new_users": 0,
                "month_new_orders": 0,
                "month_revenue": 0.0,
                "active_distributors": 0
            }




# 全局管理员服务实例
admin_service = AdminService()
