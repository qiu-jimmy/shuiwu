"""
用户个人中心相关的 Pydantic 模型
"""
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from datetime import datetime
import re
import base64


# ==================== 个人信息相关 ====================

class UserProfileResponse(BaseModel):
    """用户个人信息响应"""
    user_id: str = Field(..., description="用户ID")
    nickname: Optional[str] = Field(None, description="昵称")
    avatar_url: Optional[str] = Field(None, description="头像URL")
    phone: Optional[str] = Field(None, description="手机号")
    status: str = Field(..., description="用户状态: normal, disabled, deleted")
    user_type: str = Field(..., description="用户类型: individual, enterprise")
    member_level: str = Field(..., description="会员等级: free, basic, premium")
    member_expire_at: Optional[datetime] = Field(None, description="会员过期时间")
    register_time: Optional[datetime] = Field(None, description="注册时间")
    last_login_time: Optional[datetime] = Field(None, description="最后登录时间")
    total_commission: float = Field(default=0.0, description="总佣金")
    is_enterprise_verified: bool = Field(default=False, description="是否为企业认证用户")

    model_config = ConfigDict(from_attributes=True)


class UpdateNicknameRequest(BaseModel):
    """更新昵称请求"""
    nickname: str = Field(
        ...,
        description="昵称（1-50个字符）",
        min_length=1,
        max_length=50,
        examples=["新昵称", "测试用户123"]
    )

    @field_validator('nickname')
    @classmethod
    def validate_nickname(cls, v: str) -> str:
        """验证昵称不能包含特殊字符"""
        if not v or not v.strip():
            raise ValueError('昵称不能为空')
        # 检查是否包含控制字符或非法字符
        if re.search(r'[\x00-\x1f\x7f-\x9f]', v):
            raise ValueError('昵称不能包含特殊字符')
        return v.strip()


class UpdateAvatarRequest(BaseModel):
    """更新头像请求（接收Base64编码的图片数据）"""
    avatar_data: str = Field(
        ...,
        description="Base64编码的图片数据（支持data:image/xxx;base64,前缀或不带前缀）",
        examples=["iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="]
    )
    file_name: str = Field(
        ...,
        description="文件名（必须包含扩展名）",
        examples=["avatar.jpg", "profile.png", "user_avatar.gif"]
    )

    @field_validator('file_name')
    @classmethod
    def validate_file_extension(cls, v: str) -> str:
        """验证文件扩展名"""
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        if not v:
            raise ValueError('文件名不能为空')
        ext = '.' + v.rsplit('.', 1)[-1].lower() if '.' in v else ''
        if ext not in allowed_extensions:
            raise ValueError(f'不支持的文件格式，仅支持: {", ".join(allowed_extensions)}')
        return v

    @field_validator('avatar_data')
    @classmethod
    def validate_base64_data(cls, v: str) -> str:
        """验证Base64数据格式"""
        if not v or not v.strip():
            raise ValueError('头像数据不能为空')

        # 移除可能的数据前缀
        base64_data = v
        if ',' in v:
            prefix, data = v.split(',', 1)
            if not prefix.startswith('data:image/'):
                raise ValueError('无效的图片数据格式')
            base64_data = data

        # 验证Base64编码
        try:
            decoded = base64.b64decode(base64_data, validate=True)
            if len(decoded) < 100:
                raise ValueError('图片数据过小，请上传有效的头像图片')
            # 限制大小为5MB (5 * 1024 * 1024)
            if len(decoded) > 5 * 1024 * 1024:
                raise ValueError('图片大小不能超过5MB')
        except Exception as e:
            if 'invalid' in str(e).lower():
                raise ValueError('无效的Base64编码')
            raise ValueError(f'图片数据验证失败: {str(e)}')

        return v

    @field_validator('avatar_data')
    @classmethod
    def validate_image_size(cls, v: str) -> str:
        """验证图片大小（从base64解码后的实际大小）"""
        try:
            # 移除前缀
            base64_str = v.split(',')[-1] if ',' in v else v
            decoded_size = len(base64.b64decode(base64_str))
            max_size = 5 * 1024 * 1024  # 5MB
            if decoded_size > max_size:
                raise ValueError(f'图片大小不能超过5MB（当前大小: {decoded_size / 1024 / 1024:.2f}MB）')
        except Exception:
            pass  # 让其他验证器处理错误
        return v


class BindPhoneRequest(BaseModel):
    """绑定手机号请求"""
    phone: str = Field(
        ...,
        description="手机号（11位数字）",
        pattern=r'^\d{11}$',
        examples=["13800138000", "15912345678"]
    )
    sms_code: Optional[str] = Field(
        None,
        description="短信验证码（6位数字，可选）",
        pattern=r'^\d{6}$',
        examples=["123456", "789012"]
    )

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """验证手机号格式"""
        if not v or not v.isdigit():
            raise ValueError('手机号必须为数字')
        if len(v) != 11:
            raise ValueError('手机号必须为11位')
        # 验证手机号段
        if not v.startswith(('13', '14', '15', '16', '17', '18', '19')):
            raise ValueError('请输入正确的手机号')
        return v


# ==================== 密码管理 ====================

class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str = Field(
        ...,
        description="旧密码（6-50个字符）",
        min_length=6,
        max_length=50,
        examples=["password123"]
    )
    new_password: str = Field(
        ...,
        description="新密码（6-50个字符，建议包含字母、数字和特殊字符）",
        min_length=6,
        max_length=50,
        examples=["newPassword456", "Secure@Pass123"]
    )

    @field_validator('old_password', 'new_password')
    @classmethod
    def validate_password(cls, v: str, info) -> str:
        """验证密码格式"""
        if not v or not v.strip():
            raise ValueError('密码不能为空')
        if len(v) < 6:
            raise ValueError('密码长度不能少于6个字符')
        if len(v) > 50:
            raise ValueError('密码长度不能超过50个字符')
        # 检查是否包含空白字符
        if re.search(r'\s', v):
            raise ValueError('密码不能包含空格或空白字符')
        return v

    @model_validator(mode='after')
    def validate_passwords_different(self):
        """验证新旧密码不能相同"""
        if self.old_password == self.new_password:
            raise ValueError('新密码不能与旧密码相同')
        return self


# ==================== 账号管理 ====================

class AccountDeactivationRequest(BaseModel):
    """账号注销请求"""
    password: str = Field(
        ...,
        description="密码（用于验证身份）",
        min_length=6,
        examples=["password123"]
    )
    reason: Optional[str] = Field(
        None,
        description="注销原因（可选）",
        max_length=500,
        examples=["不再使用", "隐私顾虑", "其他原因"]
    )

    @field_validator('reason')
    @classmethod
    def validate_reason(cls, v: Optional[str]) -> Optional[str]:
        """验证注销原因"""
        if v is not None:
            if v and len(v.strip()) == 0:
                return None
            if len(v) > 500:
                raise ValueError('注销原因不能超过500个字符')
            return v.strip()
        return v


# ==================== 隐私设置 ====================

class PrivacySettingsResponse(BaseModel):
    """隐私设置响应"""
    show_phone: bool = Field(..., description="是否公开手机号")
    show_member_info: bool = Field(..., description="是否公开会员信息")
    allow_search: bool = Field(..., description="是否允许通过手机号搜索")

    model_config = ConfigDict(from_attributes=True)


class PrivacySettingsRequest(BaseModel):
    """隐私设置请求"""
    show_phone: bool = Field(
        False,
        description="是否公开手机号（开启后其他用户可以查看您的手机号）",
        examples=[False, True]
    )
    show_member_info: bool = Field(
        False,
        description="是否公开会员信息（开启后其他用户可以查看您的会员等级和到期时间）",
        examples=[False, True]
    )
    allow_search: bool = Field(
        True,
        description="是否允许通过手机号搜索（关闭后其他用户无法通过手机号找到您）",
        examples=[True, False]
    )


# ==================== 响应封装 ====================

class AvatarUploadResponse(BaseModel):
    """头像上传响应"""
    avatar_url: str = Field(..., description="头像URL地址", examples=["https://bucket.oss-cn-hangzhou.aliyuncs.com/avatars/user_123/avatar.jpg"])


class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str = Field(..., description="响应消息", examples=["操作成功", "更新成功"])
