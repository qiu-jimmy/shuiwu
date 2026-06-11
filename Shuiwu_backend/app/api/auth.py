"""
认证路由
处理用户登录、注册等认证相关接口
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends

from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    UserInfo,
    ChangePasswordRequest,
    ResetPasswordRequest,
    WxLoginRequest,
)
from app.schemas.user import UserResponse
from app.schemas.common import ApiResponse
from app.services.auth.auth_service import auth_service
from app.utils.dependencies import get_current_user_info, require_current_user
from app.utils.response import response

router = APIRouter(prefix="/api/auth", tags=["认证"])


# ============================================================================
# 登录 & 注册
# ============================================================================


@router.post(
    "/login",
    summary="用户登录",
    description="""
    用户名密码登录接口，支持手机号或用户ID作为用户名。

    **登录流程：**
    1. 系统验证用户是否存在
    2. 检查用户状态（正常/禁用/封禁）
    3. 验证密码是否正确
    4. 生成JWT访问令牌
    5. 更新用户最后登录时间

    **返回信息：**
    - access_token: JWT访问令牌
    - token_type: 令牌类型（bearer）
    - expires_in: 过期时间（秒）
    - user_info: 用户基本信息
    """,
    responses={
        200: {
            "description": "登录成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "登录成功",
                        "data": {
                            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "token_type": "bearer",
                            "expires_in": 604800,
                            "user_info": {
                                "user_id": "user_1234567890abcdef",
                                "nickname": "测试用户",
                                "phone": "13800138000",
                                "status": "normal",
                                "user_type": "individual",
                                "member_level": "free",
                                "member_package_name": "免费版"
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "登录失败",
            "content": {
                "application/json": {
                    "examples": {
                        "user_not_found": {
                            "summary": "用户不存在",
                            "value": {
                                "code": 0,
                                "message": "用户不存在",
                                "data": None
                            }
                        },
                        "invalid_password": {
                            "summary": "密码错误",
                            "value": {
                                "code": 0,
                                "message": "密码错误",
                                "data": None
                            }
                        },
                        "user_disabled": {
                            "summary": "用户已被禁用",
                            "value": {
                                "code": 0,
                                "message": "用户已被禁用",
                                "data": None
                            }
                        },
                        "user_banned": {
                            "summary": "用户已被封禁",
                            "value": {
                                "code": 0,
                                "message": "用户已被封禁",
                                "data": None
                            }
                        }
                    }
                }
            }
        }
    }
)
async def login(request: LoginRequest) -> Dict[str, Any]:
    result = auth_service.login(request.username, request.password)

    if not result["success"]:
        error_code = result.get("error_code", "LOGIN_FAILED")
        error_msg = result.get("error", "登录失败")
        return response.fail(message=error_msg)

    return response.success(data=result, message="登录成功")


@router.post(
    "/register",
    summary="用户注册",
    description="""
    用户注册接口，通过手机号注册新用户。

    **注册流程：**
    1. 验证手机号是否已被注册
    2. 验证短信验证码（测试环境可跳过）
    3. 验证推广码（如提供）
    4. 创建用户并生成密码哈希
    5. 生成JWT访问令牌

    **注意事项：**
    - 手机号必须唯一
    - 密码会进行bcrypt哈希加密
    - 注册成功后自动登录
    - 可选填写推广码，绑定邀请人关系
    """,
    responses={
        200: {
            "description": "注册成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "注册成功",
                        "data": {
                            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "token_type": "bearer",
                            "expires_in": 604800,
                            "user_info": {
                                "user_id": "user_1234567890abcdef",
                                "nickname": "测试用户",
                                "phone": "13800138000",
                                "status": "normal",
                                "user_type": "individual",
                                "member_level": "free",
                                "member_package_name": "免费版"
                            }
                        }
                    }
                }
            }
        },
        400: {
            "description": "注册失败",
            "content": {
                "application/json": {
                    "examples": {
                        "phone_exists": {
                            "summary": "手机号已被注册",
                            "value": {
                                "code": 0,
                                "message": "手机号已被注册",
                                "data": None
                            }
                        },
                        "invalid_sms_code": {
                            "summary": "验证码错误或已过期",
                            "value": {
                                "code": 0,
                                "message": "验证码错误或已过期",
                                "data": None
                            }
                        }
                    }
                }
            }
        }
    }
)
async def register(request: RegisterRequest) -> Dict[str, Any]:
    result = auth_service.register(
        phone=request.phone,
        password=request.password,
        nickname=request.nickname,
        sms_code=request.sms_code,
        referral_code=request.referral_code
    )

    if not result["success"]:
        error_msg = result.get("error", "注册失败")
        return response.fail(message=error_msg)

    return response.success(data=result, message="注册成功")


@router.post(
    "/wechat-login",
    summary="微信小程序登录",
    description="""
    微信小程序登录接口。

    **登录流程：**
    1. 小程序端调用 wx.login() 获取临时登录凭证 code
    2. 将 code 传给后端
    3. 后端调用微信 code2Session 接口换取 openid 和 session_key
    4. 根据 openid 查找或创建用户
    5. 生成 JWT 访问令牌

    **小程序端示例：**
    ```javascript
    wx.login({
      success(res) {
        if (res.code) {
          wx.request({
            url: 'https://your-domain.com/api/auth/wechat-login',
            method: 'POST',
            data: { code: res.code },
            success(loginRes) {
              wx.setStorageSync('token', loginRes.data.access_token);
            }
          });
        }
      }
    });
    ```

    **返回信息：**
    - access_token: JWT访问令牌
    - token_type: 令牌类型（bearer）
    - expires_in: 过期时间（秒）
    - user_info: 用户基本信息
    """,
    responses={
        200: {
            "description": "登录成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "登录成功",
                        "data": {
                            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "token_type": "bearer",
                            "expires_in": 604800,
                            "user_info": {
                                "user_id": "user_1234567890abcdef",
                                "wx_openid": "oXXXX...",
                                "wx_unionid": None,
                                "nickname": "微信用户1234",
                                "avatar_url": None,
                                "status": "normal",
                                "user_type": "individual",
                                "member_level": "free",
                                "member_package_name": "免费版"
                            }
                        }
                    }
                }
            }
        },
        400: {
            "description": "登录失败",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_code": {
                            "summary": "code 无效",
                            "value": {
                                "code": 0,
                                "message": "code 无效",
                                "data": None
                            }
                        },
                        "system_error": {
                            "summary": "系统繁忙",
                            "value": {
                                "code": 0,
                                "message": "系统繁忙，请稍后重试",
                                "data": None
                            }
                        }
                    }
                }
            }
        }
    }
)
async def wechat_login(request: WxLoginRequest) -> Dict[str, Any]:
    result = await auth_service.wechat_login(
        code=request.code,
        encrypted_data=request.encrypted_data,
        iv=request.iv,
        referral_code=request.referral_code
    )

    if not result["success"]:
        error_msg = result.get("error", "微信登录失败")
        return response.fail(message=error_msg)

    return response.success(data=result, message="登录成功")


# ============================================================================
# 用户信息
# ============================================================================


@router.get(
    "/me",
    summary="获取当前用户信息",
    description="""
    获取当前登录用户的详细信息。

    **认证要求：** 需要在请求头中提供有效的 Bearer Token

    **请求头示例：**
    ```
    Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    ```
    """,
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "操作成功",
                        "data": {
                            "user_id": "user_1234567890abcdef",
                            "wx_openid": None,
                            "wx_unionid": None,
                            "phone": "13800138000",
                            "nickname": "测试用户",
                            "avatar_url": None,
                            "status": "normal",
                            "user_type": "individual",
                            "member_level": "v1_platinum_month",
                            "member_package_name": "白金月卡",
                            "member_expire_at": None,
                            "register_time": "2024-01-01T00:00:00",
                            "last_login_time": "2024-01-13T15:27:57",
                            "created_at": "2024-01-01T00:00:00",
                            "updated_at": "2024-01-13T15:27:57",
                            "is_distributor": True,
                            "distributor_code": "ABC123"
                        }
                    }
                }
            }
        },
        401: {
            "description": "未授权",
            "content": {
                "application/json": {
                    "examples": {
                        "no_token": {
                            "summary": "未提供认证token",
                            "value": {
                                "code": "NO_TOKEN",
                                "message": "未提供认证token",
                                "data": None
                            }
                        },
                        "invalid_token": {
                            "summary": "无效的认证token",
                            "value": {
                                "code": "INVALID_TOKEN",
                                "message": "无效的认证token",
                                "data": None
                            }
                        }
                    }
                }
            }
        }
    }
)
async def get_current_user(
    user_info: dict = Depends(get_current_user_info)
) -> Dict[str, Any]:
    # 使用 UserResponse schema 自动过滤敏感字段
    safe_user_info = UserResponse(**user_info).model_dump()
    return response.success(data=safe_user_info)


@router.get(
    "/verify-token",
    summary="验证Token",
    description="""
    验证当前 JWT Token 是否有效。

    **认证要求：** 需要在请求头中提供有效的 Bearer Token

    **返回信息：**
    - 如果 Token 有效，返回用户ID
    - 如果 Token 无效或已过期，返回 401 错误
    """,
    responses={
        200: {
            "description": "Token有效",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "操作成功",
                        "data": {
                            "user_id": "user_1234567890abcdef"
                        }
                    }
                }
            }
        },
        401: {
            "description": "Token无效或已过期",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "无效的认证token",
                        "data": None
                    }
                }
            }
        }
    }
)
async def verify_token(
    user_id: str = Depends(require_current_user)
) -> Dict[str, Any]:
    return response.success(data={"user_id": user_id})


# ============================================================================
# 密码管理
# ============================================================================


@router.post(
    "/change-password",
    summary="修改密码",
    description="""
    修改当前登录用户的密码。

    **认证要求：** 需要在请求头中提供有效的 Bearer Token

    **修改流程：**
    1. 验证旧密码是否正确
    2. 生成新密码的哈希值
    3. 更新数据库中的密码

    **安全建议：**
    - 新密码应与旧密码不同
    - 建议使用强密码（包含大小写字母、数字、特殊字符）
    """,
    responses={
        200: {
            "description": "修改成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "修改密码成功",
                        "data": None
                    }
                }
            }
        },
        400: {
            "description": "修改失败",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_old_password": {
                            "summary": "原密码错误",
                            "value": {
                                "code": 0,
                                "message": "原密码错误",
                                "data": None
                            }
                        },
                        "user_not_found": {
                            "summary": "用户不存在",
                            "value": {
                                "code": 0,
                                "message": "用户不存在",
                                "data": None
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "未授权",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "未提供认证token",
                        "data": None
                    }
                }
            }
        }
    }
)
async def change_password(
    request: ChangePasswordRequest,
    user_info: dict = Depends(get_current_user_info)
) -> Dict[str, Any]:
    result = auth_service.change_password(
        user_id=user_info["user_id"],
        old_password=request.old_password,
        new_password=request.new_password
    )

    if not result["success"]:
        error_msg = result.get("error", "修改密码失败")
        return response.fail(message=error_msg)

    return response.success(message="修改密码成功")


@router.post(
    "/reset-password",
    summary="重置密码",
    description="""
    通过手机号重置用户密码（忘记密码场景）。

    **重置流程：**
    1. 验证手机号对应的用户是否存在
    2. 验证短信验证码
    3. 生成新密码的哈希值
    4. 更新数据库中的密码

    **注意事项：**
    - 此接口不需要登录认证
    - 需要通过短信验证码验证身份
    - 测试环境可使用默认验证码 "123456"
    """,
    responses={
        200: {
            "description": "重置成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "重置密码成功",
                        "data": None
                    }
                }
            }
        },
        400: {
            "description": "重置失败",
            "content": {
                "application/json": {
                    "examples": {
                        "user_not_found": {
                            "summary": "用户不存在",
                            "value": {
                                "code": 0,
                                "message": "用户不存在",
                                "data": None
                            }
                        },
                        "invalid_sms_code": {
                            "summary": "验证码错误或已过期",
                            "value": {
                                "code": 0,
                                "message": "验证码错误或已过期",
                                "data": None
                            }
                        }
                    }
                }
            }
        }
    }
)
async def reset_password(request: ResetPasswordRequest) -> Dict[str, Any]:
    result = auth_service.reset_password(
        phone=request.phone,
        sms_code=request.sms_code,
        new_password=request.new_password
    )

    if not result["success"]:
        error_msg = result.get("error", "重置密码失败")
        return response.fail(message=error_msg)

    return response.success(message="重置密码成功")


# ============================================================================
# 登出
# ============================================================================


@router.post(
    "/logout",
    summary="用户登出",
    description="""
    用户登出接口。

    **认证要求：** 需要在请求头中提供有效的 Bearer Token

    **重要说明：**
    由于使用 JWT 无状态认证，后端不维护 token 黑名单。
    登出操作主要在前端完成：
    1. 前端删除本地存储的 token
    2. 清除用户相关缓存数据
    3. 跳转到登录页面

    后端此接口主要用于：
    - 验证 token 有效性
    - 记录登出日志（如需要）
    - 执行登出相关业务逻辑
    """,
    responses={
        200: {
            "description": "登出成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "登出成功",
                        "data": None
                    }
                }
            }
        },
        401: {
            "description": "未授权",
            "content": {
                "application/json": {
                    "examples": {
                        "no_token": {
                            "summary": "未提供认证token",
                            "value": {
                                "code": "NO_TOKEN",
                                "message": "未提供认证token",
                                "data": None
                            }
                        },
                        "invalid_token": {
                            "summary": "无效的认证token",
                            "value": {
                                "code": "INVALID_TOKEN",
                                "message": "无效的认证token",
                                "data": None
                            }
                        }
                    }
                }
            }
        }
    }
)
async def logout(
    user_id: str = Depends(require_current_user)
) -> Dict[str, Any]:
    return response.success(message="登出成功")
