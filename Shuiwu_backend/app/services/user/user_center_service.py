"""
用户个人中心服务
处理个人信息的查看、编辑、头像上传、手机号管理、密码修改、账号注销、隐私设置等业务逻辑
"""
import io
import base64
import uuid
import alibabacloud_oss_v2 as oss
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy import text

from app.services.user.user_repository import user_repository
from app.utils.jwt_utils import verify_password, get_password_hash
from app.infra.oss_client import oss_client_manager
from app.infra.db import get_sync_engine


class UserCenterService:
    """用户个人中心服务类"""

    def __init__(self):
        self.db_schema = "business"

    def get_profile(self, user_id: str) -> Dict[str, Any]:
        """获取用户个人信息"""
        user = user_repository.get_user_by_id(user_id)
        if not user:
            return {
                "success": False,
                "error": "用户不存在",
                "error_code": "USER_NOT_FOUND"
            }

        # 获取总佣金（从分销商表）
        total_commission = 0.0
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                distributor = conn.execute(text("""
                    SELECT total_commission FROM business.distributors
                    WHERE user_id = :user_id
                """), {"user_id": user_id}).fetchone()
                if distributor and distributor[0] is not None:
                    total_commission = float(distributor[0])
        except Exception as e:
            print(f"获取总佣金失败: {e}")

        profile = {
            "user_id": user["user_id"],
            "nickname": user.get("nickname"),
            "avatar_url": user.get("avatar_url"),
            "phone": user.get("phone"),
            "status": user["status"],
            "user_type": user["user_type"],
            "member_level": user["member_level"],
            "member_expire_at": user.get("member_expire_at"),
            "register_time": user.get("register_time"),
            "last_login_time": user.get("last_login_time"),
            "total_commission": total_commission,
            "is_enterprise_verified": False  # 默认 false
        }

        return {
            "success": True,
            "data": profile
        }

    def update_nickname(self, user_id: str, nickname: str) -> Dict[str, Any]:
        """更新用户昵称"""
        user = user_repository.get_user_by_id(user_id)
        if not user:
            return {
                "success": False,
                "error": "用户不存在",
                "error_code": "USER_NOT_FOUND"
            }

        success = user_repository.update_user(
            user_id=user_id,
            update_data={"nickname": nickname}
        )

        if not success:
            return {
                "success": False,
                "error": "更新昵称失败",
                "error_code": "UPDATE_FAILED"
            }

        return {
            "success": True,
            "message": "昵称更新成功"
        }

    def update_avatar(self, user_id: str, avatar_data: str, file_name: str) -> Dict[str, Any]:
        """更新用户头像"""
        user = user_repository.get_user_by_id(user_id)
        if not user:
            return {
                "success": False,
                "error": "用户不存在",
                "error_code": "USER_NOT_FOUND"
            }

        try:
            # 获取旧头像URL，用于后续删除
            old_avatar_url = getattr(user, 'avatar_url', None)

            # 解码Base64数据
            if "base64," in avatar_data:
                avatar_data = avatar_data.split("base64,")[1]

            image_bytes = base64.b64decode(avatar_data)

            # 验证文件大小（最大5MB）
            if len(image_bytes) > 5 * 1024 * 1024:
                return {
                    "success": False,
                    "error": "图片大小不能超过5MB",
                    "error_code": "FILE_TOO_LARGE"
                }

            # 生成唯一的文件名
            file_ext = self._get_file_extension(file_name)
            unique_filename = f"avatars/{user_id}/{uuid.uuid4().hex}{file_ext}"

            # 上传到OSS
            oss_client = oss_client_manager.client
            if not oss_client:
                return {
                    "success": False,
                    "error": "OSS服务未初始化",
                    "error_code": "OSS_NOT_INITIALIZED"
                }

            bucket = oss_client_manager.bucket
            result = oss_client.put_object(oss.PutObjectRequest(
                bucket=bucket,
                key=unique_filename,
                body=io.BytesIO(image_bytes)
            ))

            # 构建访问URL
            region = oss_client_manager._config.get('region', 'cn-heyuan')
            endpoint = oss_client_manager._config.get('endpoint')

            if endpoint and endpoint.strip():
                # 使用自定义endpoint（去除协议前缀）
                endpoint_clean = endpoint.replace('https://', '').replace('http://', '').strip()
                avatar_url = f"https://{bucket}.{endpoint_clean}/{unique_filename}"
            else:
                # 使用标准endpoint格式：bucket.oss-region.aliyuncs.com
                avatar_url = f"https://{bucket}.oss-{region}.aliyuncs.com/{unique_filename}"

            # 更新数据库中的头像URL
            success = user_repository.update_user(
                user_id=user_id,
                update_data={"avatar_url": avatar_url}
            )

            if not success:
                return {
                    "success": False,
                    "error": "更新头像失败",
                    "error_code": "UPDATE_FAILED"
                }

            # 如果新头像上传成功且数据库更新成功，删除旧头像
            if old_avatar_url:
                try:
                    # 从URL中提取OSS的key
                    # URL格式: https://bucket.endpoint/key 或 https://bucket.oss-region.aliyuncs.com/key
                    if '/' in old_avatar_url:
                        # 找到第三个斜杠后的部分作为key
                        parts = old_avatar_url.split('/', 3)
                        if len(parts) >= 4:
                            old_avatar_key = parts[3]
                            # 删除OSS中的旧头像
                            oss_client.delete_object(oss.DeleteObjectRequest(
                                bucket=bucket,
                                key=old_avatar_key
                            ))
                except Exception as e:
                    # 删除旧头像失败不影响新头像的使用，记录日志即可
                    print(f"删除旧头像失败（可忽略）: {e}")

            return {
                "success": True,
                "message": "头像更新成功",
                "avatar_url": avatar_url
            }

        except base64.binascii.Error:
            return {
                "success": False,
                "error": "无效的Base64数据",
                "error_code": "INVALID_BASE64"
            }
        except Exception as e:
            print(f"上传头像失败: {e}")
            return {
                "success": False,
                "error": f"上传头像失败: {str(e)}",
                "error_code": "UPLOAD_FAILED"
            }

    def bind_phone(self, user_id: str, phone: str, sms_code: str) -> Dict[str, Any]:
        """绑定/更换手机号"""
        user = user_repository.get_user_by_id(user_id)
        if not user:
            return {
                "success": False,
                "error": "用户不存在",
                "error_code": "USER_NOT_FOUND"
            }

        # 检查新手机号是否已被其他用户使用
        existing_user = user_repository.get_user_by_phone(phone)
        if existing_user and existing_user["user_id"] != user_id:
            return {
                "success": False,
                "error": "该手机号已被其他用户绑定",
                "error_code": "PHONE_ALREADY_BOUND"
            }

        # TODO: 验证短信验证码
        # 临时跳过验证码验证

        # 更新手机号
        success = user_repository.update_user(
            user_id=user_id,
            update_data={"phone": phone}
        )

        if not success:
            return {
                "success": False,
                "error": "绑定手机号失败",
                "error_code": "BIND_FAILED"
            }

        return {
            "success": True,
            "message": "手机号绑定成功"
        }

    def change_password(self, user_id: str, old_password: str, new_password: str) -> Dict[str, Any]:
        """修改密码"""
        user = user_repository.get_user_by_id(user_id)
        if not user:
            return {
                "success": False,
                "error": "用户不存在",
                "error_code": "USER_NOT_FOUND"
            }

        # 验证旧密码（如果用户已有密码）
        password_hash = user.get("password_hash", "")

        # 如果用户没有密码（如微信登录用户），直接设置新密码
        if not password_hash:
            # 无需验证旧密码，直接设置新密码
            new_password_hash = get_password_hash(new_password)
            success = user_repository.update_user(
                user_id=user_id,
                update_data={"password_hash": new_password_hash}
            )
            if not success:
                return {
                    "success": False,
                    "error": "设置密码失败",
                    "error_code": "SET_PASSWORD_FAILED"
                }
            return {
                "success": True,
                "message": "密码设置成功"
            }

        # 用户有密码，验证旧密码
        if not verify_password(old_password, password_hash):
            return {
                "success": False,
                "error": "旧密码错误",
                "error_code": "INVALID_OLD_PASSWORD"
            }

        # 更新密码
        new_password_hash = get_password_hash(new_password)
        success = user_repository.update_user(
            user_id=user_id,
            update_data={"password_hash": new_password_hash}
        )

        if not success:
            return {
                "success": False,
                "error": "修改密码失败",
                "error_code": "UPDATE_FAILED"
            }

        return {
            "success": True,
            "message": "密码修改成功"
        }

    def deactivate_account(self, user_id: str, password: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """账号注销"""
        user = user_repository.get_user_by_id(user_id)
        if not user:
            return {
                "success": False,
                "error": "用户不存在",
                "error_code": "USER_NOT_FOUND"
            }

        # 验证密码
        password_hash = user.get("password_hash", "")
        if password_hash and not verify_password(password, password_hash):
            return {
                "success": False,
                "error": "密码错误",
                "error_code": "INVALID_PASSWORD"
            }

        # 软删除：将用户状态设置为 disabled
        success = user_repository.update_user(
            user_id=user_id,
            update_data={"status": "disabled"}
        )

        if not success:
            return {
                "success": False,
                "error": "账号注销失败",
                "error_code": "DEACTIVATION_FAILED"
            }

        # 注销成功后，删除用户的头像（如果存在）
        avatar_url = getattr(user, 'avatar_url', None)
        if avatar_url:
            try:
                # 从URL中提取OSS的key
                if '/' in avatar_url:
                    parts = avatar_url.split('/', 3)
                    if len(parts) >= 4:
                        avatar_key = parts[3]
                        # 删除OSS中的头像
                        oss_client = oss_client_manager.client
                        if oss_client:
                            bucket = oss_client_manager.bucket
                            oss_client.delete_object(oss.DeleteObjectRequest(
                                bucket=bucket,
                                key=avatar_key
                            ))
            except Exception as e:
                # 删除头像失败不影响账号注销，记录日志即可
                print(f"删除用户头像失败（可忽略）: {e}")

        return {
            "success": True,
            "message": "账号已成功注销"
        }

    def get_privacy_settings(self, user_id: str) -> Dict[str, Any]:
        """获取隐私设置"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                row = conn.execute(text("""
                    SELECT show_phone, show_member_info, allow_search
                    FROM business.user_privacy_settings
                    WHERE user_id = :user_id
                """), {"user_id": user_id}).fetchone()

                if not row:
                    # 如果不存在隐私设置，创建默认设置
                    conn.execute(text("""
                        INSERT INTO business.user_privacy_settings (user_id)
                        VALUES (:user_id)
                    """), {"user_id": user_id})
                    conn.commit()

                    return {
                        "success": True,
                        "data": {
                            "show_phone": False,
                            "show_member_info": False,
                            "allow_search": True
                        }
                    }

                return {
                    "success": True,
                    "data": {
                        "show_phone": row[0],
                        "show_member_info": row[1],
                        "allow_search": row[2]
                    }
                }
        except Exception as e:
            print(f"获取隐私设置失败: {e}")
            return {
                "success": False,
                "error": "获取隐私设置失败",
                "error_code": "GET_PRIVACY_FAILED"
            }

    def update_privacy_settings(self, user_id: str, show_phone: bool, show_member_info: bool, allow_search: bool) -> Dict[str, Any]:
        """更新隐私设置"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO business.user_privacy_settings (user_id, show_phone, show_member_info, allow_search, updated_at)
                    VALUES (:user_id, :show_phone, :show_member_info, :allow_search, :updated_at)
                    ON CONFLICT (user_id) DO UPDATE
                    SET show_phone = :show_phone,
                        show_member_info = :show_member_info,
                        allow_search = :allow_search,
                        updated_at = :updated_at
                """), {
                    "user_id": user_id,
                    "show_phone": show_phone,
                    "show_member_info": show_member_info,
                    "allow_search": allow_search,
                    "updated_at": datetime.now()
                })
                conn.commit()

                return {
                    "success": True,
                    "message": "隐私设置更新成功"
                }
        except Exception as e:
            print(f"更新隐私设置失败: {e}")
            return {
                "success": False,
                "error": "更新隐私设置失败",
                "error_code": "UPDATE_PRIVACY_FAILED"
            }

    def _get_file_extension(self, filename: str) -> str:
        """获取文件扩展名"""
        if '.' in filename:
            ext = filename.rsplit('.', 1)[1].lower()
            return f'.{ext}'
        return '.jpg'


# 全局服务实例
user_center_service = UserCenterService()
