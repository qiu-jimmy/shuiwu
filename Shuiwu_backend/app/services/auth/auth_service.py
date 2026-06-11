"""
认证服务
处理用户登录、注册等认证相关业务逻辑
"""
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from app.services.user.user_repository import user_repository
from app.services.wechat_pay.wechat_mini_client import wechat_mini_client
from app.utils.jwt_utils import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from app.schemas.auth import UserInfo


class AuthService:
    """认证服务类"""

    def __init__(self):
        pass

    def login(self, username: str, password: str) -> Dict[str, Any]:
        """
        用户名密码登录
        支持手机号或邮箱作为用户名
        """
        # 尝试通过手机号查找用户
        user = user_repository.get_user_by_phone(username)

        # 如果找不到，尝试通过user_id查找（如果用户名就是user_id）
        if not user:
            user = user_repository.get_user_by_id(username)

        if not user:
            return {
                "success": False,
                "error": "用户不存在",
                "error_code": "USER_NOT_FOUND"
            }

        # 检查用户状态
        if user.get("status") == "disabled":
            return {
                "success": False,
                "error": "用户已被禁用",
                "error_code": "USER_DISABLED"
            }

        if user.get("status") == "banned":
            return {
                "success": False,
                "error": "用户已被封禁",
                "error_code": "USER_BANNED"
            }

        # 验证密码
        password_hash = user.get("password_hash", "")
        if not password_hash:
            return {
                "success": False,
                "error": "用户未设置密码",
                "error_code": "NO_PASSWORD"
            }

        if not verify_password(password, password_hash):
            return {
                "success": False,
                "error": "密码错误",
                "error_code": "INVALID_PASSWORD"
            }

        # 生成JWT token
        access_token = create_access_token(
            data={"sub": user["user_id"]},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        # 记录登录日志
        # user_repository.log_user_action(
        #     user_id=user["user_id"],
        #     action_type="login",
        #     action_module="auth",
        #     action_detail={"login_type": "password"}
        # )

        # 更新最后登录时间
        user_repository.update_user(user["user_id"], {"last_login_time": datetime.now()})

        return {
            "success": True,
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user_info": self._to_user_info(user)
        }

    def register(self, phone: str, password: str, nickname: Optional[str] = None, sms_code: Optional[str] = None, referral_code: Optional[str] = None) -> Dict[str, Any]:
        """
        用户注册
        """
        # 检查手机号是否已存在
        existing_user = user_repository.get_user_by_phone(phone)
        if existing_user:
            return {
                "success": False,
                "error": "手机号已被注册",
                "error_code": "PHONE_EXISTS"
            }

        # TODO: 验证短信验证码
        # if not self._verify_sms_code(phone, sms_code, "register"):
        #     return {
        #         "success": False,
        #         "error": "验证码错误或已过期",
        #         "error_code": "INVALID_SMS_CODE"
        #     }

        # 验证邀请码（如果提供）
        inviter_id = None
        if referral_code:
            # 临时简化版：直接从数据库查询
            from app.infra.db import get_sync_engine
            from sqlalchemy import text
            engine = get_sync_engine()
            with engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT user_id FROM business.distributors
                        WHERE distributor_code = :code AND status = 'active'
                    """),
                    {"code": referral_code}
                ).fetchone()
                
                if not result:
                    return {
                        "success": False,
                        "error": "推广码无效",
                        "error_code": "INVALID_REFERRAL_CODE"
                    }
                inviter_id = result[0]

        # 创建新用户
        user_id = f"user_{uuid.uuid4().hex[:16]}"
        password_hash = get_password_hash(password)

        user_data = {
            "user_id": user_id,
            "phone": phone,
            "nickname": nickname or f"用户{phone[-4:]}",
            "password_hash": password_hash,
            "status": "normal",
            "user_type": "individual",
            "member_level": "free",
            "inviter_id": inviter_id
        }

        created_user_id = user_repository.create_user(user_data)

        if not created_user_id:
            return {
                "success": False,
                "error": "创建用户失败",
                "error_code": "CREATE_USER_FAILED"
            }

        # 获取创建的用户信息
        user = user_repository.get_user_by_id(created_user_id)

        # 生成JWT token
        access_token = create_access_token(
            data={"sub": user_id},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        return {
            "success": True,
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user_info": self._to_user_info(user or user_data)
        }

    def get_user_info(self, user_id: str) -> Optional[UserInfo]:
        """
        获取用户信息
        """
        user = user_repository.get_user_by_id(user_id)

        if not user:
            return None

        return self._to_user_info(user)

    def change_password(self, user_id: str, old_password: str, new_password: str) -> Dict[str, Any]:
        """
        修改密码
        """
        user = user_repository.get_user_by_id(user_id)

        if not user:
            return {
                "success": False,
                "error": "用户不存在",
                "error_code": "USER_NOT_FOUND"
            }

        # 验证旧密码（如果用户已有密码）
        current_password_hash = user.get("password_hash", "")
        print(f"[DEBUG] change_password - user_id={user_id}, password_hash={repr(current_password_hash)}, type={type(current_password_hash)}")

        # 如果用户没有密码（如微信登录用户），直接设置新密码
        if not current_password_hash:
            # 无需验证旧密码，直接设置新密码
            new_password_hash = get_password_hash(new_password)
            user_repository.update_user(user_id, {"password_hash": new_password_hash})
            return {
                "success": True,
                "message": "密码设置成功"
            }

        # 用户有密码，验证旧密码
        if not verify_password(old_password, current_password_hash):
            return {
                "success": False,
                "error": "原密码错误",
                "error_code": "INVALID_OLD_PASSWORD"
            }

        # 更新密码
        new_password_hash = get_password_hash(new_password)
        user_repository.update_user(user_id, {"password_hash": new_password_hash})

        return {
            "success": True,
            "message": "密码修改成功"
        }

    def reset_password(self, phone: str, sms_code: str, new_password: str) -> Dict[str, Any]:
        """
        重置密码
        """
        user = user_repository.get_user_by_phone(phone)

        if not user:
            return {
                "success": False,
                "error": "用户不存在",
                "error_code": "USER_NOT_FOUND"
            }

        # TODO: 验证短信验证码
        # if not self._verify_sms_code(phone, sms_code, "reset_password"):
        #     return {
        #         "success": False,
        #         "error": "验证码错误或已过期",
        #         "error_code": "INVALID_SMS_CODE"
        #     }

        # 更新密码
        new_password_hash = get_password_hash(new_password)
        user_repository.update_user(user["user_id"], {"password_hash": new_password_hash})

        return {
            "success": True,
            "message": "密码重置成功"
        }

    def bind_invite_code(self, user_id: str, invite_code: str) -> Dict[str, Any]:
        """
        绑定邀请码

        业务规则：
        1. 验证邀请码是否有效（必须是有效的分销商推广码）
        2. 检查用户是否已绑定邀请人（已绑定的不能重复绑定）
        3. 防止用户绑定自己的邀请码
        4. 成功绑定后更新用户的 inviter_id 字段
        """
        # 获取当前用户信息
        user = user_repository.get_user_by_id(user_id)
        if not user:
            return {
                "success": False,
                "error": "用户不存在",
                "error_code": "USER_NOT_FOUND"
            }

        # 检查是否已绑定邀请人
        if user.get("inviter_id"):
            return {
                "success": False,
                "error": "您已绑定过邀请人，无法重复绑定",
                "error_code": "ALREADY_BOUND"
            }

        # 验证邀请码（从分销商表中查询）
        from app.infra.db import get_sync_engine
        from sqlalchemy import text
        engine = get_sync_engine()

        with engine.connect() as conn:
            # 查询分销商信息
            result = conn.execute(
                text("""
                    SELECT d.user_id, u.nickname
                    FROM business.distributors d
                    LEFT JOIN business.users u ON d.user_id = u.user_id
                    WHERE d.distributor_code = :code AND d.status = 'active'
                """),
                {"code": invite_code}
            ).fetchone()

            if not result:
                return {
                    "success": False,
                    "error": "邀请码无效或不存在",
                    "error_code": "INVALID_INVITE_CODE"
                }

            inviter_id, inviter_nickname = result[0], result[1]

        # 防止用户绑定自己的邀请码
        if inviter_id == user_id:
            return {
                "success": False,
                "error": "不能绑定自己的邀请码",
                "error_code": "CANNOT_BIND_SELF"
            }

        # 更新用户的邀请人ID
        update_success = user_repository.update_user(user_id, {"inviter_id": inviter_id})

        if not update_success:
            return {
                "success": False,
                "error": "绑定失败，请稍后重试",
                "error_code": "BIND_FAILED"
            }

        # 绑定成功后，更新分销商累计邀请人数
        try:
            from app.infra.db import get_sync_engine
            from sqlalchemy import text
            engine = get_sync_engine()
            with engine.connect() as conn:
                conn.execute(
                    text("""
                        UPDATE business.distributors
                        SET total_children_count = total_children_count + 1,
                            updated_at = NOW()
                        WHERE user_id = :inviter_id
                    """),
                    {"inviter_id": inviter_id}
                )
                conn.commit()
            print(f"[分销] 用户 {user_id} 绑定邀请人 {inviter_id}，累计邀请 +1")
        except Exception as e:
            # 统计更新失败不影响主流程
            print(f"[警告] 更新分销商邀请人数失败: {e}")

        # 返回绑定结果
        return {
            "success": True,
            "message": "绑定邀请码成功",
            "inviter_id": inviter_id,
            "inviter_nickname": inviter_nickname
        }

    async def wechat_login(
        self,
        code: str,
        encrypted_data: Optional[str] = None,
        iv: Optional[str] = None,
        referral_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        微信小程序登录

        业务流程：
        1. 使用 code 调用微信 code2Session 接口换取 openid 和 session_key
        2. 根据 openid 查找用户：
           - 如果用户存在，直接登录
           - 如果用户不存在，创建新用户并登录
        3. 验证邀请码（如果提供）
        4. 记录登录日志

        Args:
            code: 微信登录凭证
            encrypted_data: 加密数据（可选，用于获取手机号）
            iv: 加密算法的初始向量（可选）
            referral_code: 推广邀请码（可选）

        Returns:
            登录结果，包含 token 和用户信息
        """
        # 1. 使用 code 换取 openid 和 session_key
        try:
            wx_data = await wechat_mini_client.code2_session(code)
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_code": "WECHAT_LOGIN_FAILED"
            }

        openid = wx_data.get("openid")
        unionid = wx_data.get("unionid")

        if not openid:
            return {
                "success": False,
                "error": "未能获取微信 OpenID",
                "error_code": "NO_OPENID"
            }

        # 2. 根据 openid 查找用户
        user = user_repository.get_user_by_wx_openid(openid)

        # 3. 如果用户不存在，创建新用户
        if not user:
            # 验证邀请码（如果提供）
            inviter_id = None
            if referral_code:
                try:
                    from app.infra.db import get_sync_engine
                    from sqlalchemy import text
                    engine = get_sync_engine()
                    with engine.connect() as conn:
                        result = conn.execute(
                            text("""
                                SELECT user_id FROM business.distributors
                                WHERE distributor_code = :code AND status = 'active'
                            """),
                            {"code": referral_code}
                        ).fetchone()

                        if not result:
                            # 邀请码无效不阻止登录，只记录警告
                            print(f"[警告] 邀请码无效: {referral_code}，用户将继续正常登录")
                        else:
                            inviter_id = result[0]
                            print(f"[信息] 邀请码有效: {referral_code}，邀请人: {inviter_id}")
                except Exception as e:
                    # 验证邀请码出错不阻止登录
                    print(f"[警告] 验证邀请码时出错: {e}，用户将继续正常登录")

            # 创建新用户
            user_id = f"user_{uuid.uuid4().hex[:16]}"
            user_data = {
                "user_id": user_id,
                "wx_openid": openid,
                "wx_unionid": unionid,
                "nickname": f"微信用户{openid[-4:]}",
                "status": "normal",
                "user_type": "individual",
                "member_level": "free",
                "inviter_id": inviter_id
            }

            created_user_id = user_repository.create_user(user_data)

            if not created_user_id:
                return {
                    "success": False,
                    "error": "创建用户失败",
                    "error_code": "CREATE_USER_FAILED"
                }

            # 新用户注册成功且携带有效邀请码，更新分销商累计邀请人数
            if inviter_id:
                try:
                    from app.infra.db import get_sync_engine
                    from sqlalchemy import text
                    engine = get_sync_engine()
                    with engine.connect() as conn:
                        conn.execute(
                            text("""
                                UPDATE business.distributors
                                SET total_children_count = total_children_count + 1,
                                    updated_at = NOW()
                                WHERE user_id = :inviter_id
                            """),
                            {"inviter_id": inviter_id}
                        )
                        conn.commit()
                    print(f"[分销] 新用户注册，分销商 {inviter_id} 累计邀请 +1")
                except Exception as e:
                    # 统计更新失败不影响主流程
                    print(f"[警告] 更新分销商邀请人数失败: {e}")

            # 获取创建的用户信息
            user = user_repository.get_user_by_id(created_user_id)
            login_type = "register"
        else:
            # 用户已存在，检查用户状态
            if user.get("status") == "disabled":
                return {
                    "success": False,
                    "error": "用户已被禁用",
                    "error_code": "USER_DISABLED"
                }

            if user.get("status") == "banned":
                return {
                    "success": False,
                    "error": "用户已被封禁",
                    "error_code": "USER_BANNED"
                }

            # 老用户若尚未绑定邀请人，且本次携带了有效邀请码，则补充绑定
            if not user.get("inviter_id") and referral_code:
                try:
                    from app.infra.db import get_sync_engine
                    from sqlalchemy import text
                    engine = get_sync_engine()
                    with engine.connect() as conn:
                        inv_result = conn.execute(
                            text("""
                                SELECT user_id FROM business.distributors
                                WHERE distributor_code = :code AND status = 'active'
                            """),
                            {"code": referral_code}
                        ).fetchone()

                        if inv_result:
                            existing_inviter_id = inv_result[0]
                            # 不能绑定自己
                            if existing_inviter_id != user["user_id"]:
                                user_repository.update_user(user["user_id"], {"inviter_id": existing_inviter_id})
                                conn.execute(
                                    text("""
                                        UPDATE business.distributors
                                        SET total_children_count = total_children_count + 1,
                                            updated_at = NOW()
                                        WHERE user_id = :inviter_id
                                    """),
                                    {"inviter_id": existing_inviter_id}
                                )
                                conn.commit()
                                # 更新内存中的 user 对象，使返回的 user_info 包含最新 inviter_id
                                user = user_repository.get_user_by_id(user["user_id"]) or user
                                print(f"[分销] 老用户 {user['user_id']} 补充绑定邀请人 {existing_inviter_id}，累计邀请 +1")
                except Exception as e:
                    # 补绑失败不影响主流程
                    print(f"[警告] 老用户补充绑定邀请人失败: {e}")

            login_type = "login"

        # 4. 生成 JWT token
        access_token = create_access_token(
            data={"sub": user["user_id"]},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        # 5. 更新最后登录时间
        user_repository.update_user(user["user_id"], {"last_login_time": datetime.now()})

        # 6. 记录微信登录日志
        self._log_wechat_login(user["user_id"], openid, login_type)

        return {
            "success": True,
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user_info": self._to_user_info(user or user_data)
        }

    def _log_wechat_login(self, user_id: str, wx_openid: str, login_type: str):
        """记录微信登录日志"""
        from app.infra.db import get_sync_engine
        from sqlalchemy import text
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                conn.execute(
                    text("""
                        INSERT INTO business.wx_login_logs (user_id, wx_openid, login_type)
                        VALUES (:user_id, :wx_openid, :login_type)
                    """),
                    {"user_id": user_id, "wx_openid": wx_openid, "login_type": login_type}
                )
                conn.commit()
        except Exception as e:
            print(f"记录微信登录日志失败: {e}")

    def _to_user_info(self, user: Dict[str, Any]) -> UserInfo:
        """转换为UserInfo对象"""
        return UserInfo(
            user_id=user.get("user_id", ""),
            nickname=user.get("nickname"),
            avatar_url=user.get("avatar_url"),
            phone=user.get("phone"),
            status=user.get("status", "normal"),
            user_type=user.get("user_type", "individual"),
            member_level=user.get("member_level", "free"),
            member_expire_at=user.get("member_expire_at"),
            wx_openid=user.get("wx_openid"),
            wx_unionid=user.get("wx_unionid"),
            is_tax_accountant=user.get("is_tax_accountant", False)
        )


# 全局认证服务实例
auth_service = AuthService()
