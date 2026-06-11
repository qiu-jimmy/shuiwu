"""
认证相关的 Pydantic 模型
"""
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


# ==================== 登录相关 ====================

class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., description="用户名（手机号或邮箱）", examples=["13800138000"])
    password: str = Field(..., description="密码", examples=["password123"])


class RegisterRequest(BaseModel):
    """注册请求"""
    phone: str = Field(..., description="手机号", examples=["13800138000"])
    password: str = Field(..., description="密码", examples=["password123"])
    nickname: Optional[str] = Field(None, description="昵称")
    sms_code: str = Field(..., description="短信验证码")
    referral_code: Optional[str] = Field(None, description="推广邀请码")


class LoginResponse(BaseModel):
    """登录响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # 过期时间（秒）
    user_info: "UserInfo"


class TokenResponse(BaseModel):
    """Token响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# ==================== 用户信息 ====================

class UserInfo(BaseModel):
    """用户基本信息"""
    user_id: str
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    status: str
    user_type: str
    member_level: str
    member_expire_at: Optional[datetime] = None
    wx_openid: Optional[str] = None
    wx_unionid: Optional[str] = None
    is_tax_accountant: bool = False

    model_config = ConfigDict(from_attributes=True)


# ==================== 密码相关 ====================

class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., description="新密码")


class ResetPasswordRequest(BaseModel):
    """重置密码请求"""
    phone: str = Field(..., description="手机号")
    sms_code: str = Field(..., description="短信验证码")
    new_password: str = Field(..., description="新密码")


# ==================== 验证码相关 ====================

class SendSmsCodeRequest(BaseModel):
    """发送短信验证码请求"""
    phone: str = Field(..., description="手机号")
    code_type: str = Field(..., description="验证码类型: register, login, reset_password")


class CaptchaResponse(BaseModel):
    """验证码响应"""
    captcha_key: str
    captcha_image: str  # base64编码的图片


# ==================== 微信登录相关 ====================

class WxLoginRequest(BaseModel):
    """微信登录请求"""
    code: str = Field(..., description="微信授权code")
    encrypted_data: Optional[str] = Field(None, description="加密数据（获取手机号）")
    iv: Optional[str] = Field(None, description="加密算法的初始向量")
    referral_code: Optional[str] = Field(None, description="推广邀请码")


class WxBindPhoneRequest(BaseModel):
    """微信绑定手机号请求"""
    user_id: str = Field(..., description="用户ID")
    phone: str = Field(..., description="手机号")
    sms_code: str = Field(..., description="短信验证码")


# ==================== 邀请码相关 ====================

class BindInviteCodeRequest(BaseModel):
    """绑定邀请码请求"""
    invite_code: str = Field(..., description="邀请码", min_length=1, max_length=20)


class BindInviteCodeResponse(BaseModel):
    """绑定邀请码响应"""
    inviter_id: str = Field(..., description="邀请人ID")
    inviter_nickname: Optional[str] = Field(None, description="邀请人昵称")
