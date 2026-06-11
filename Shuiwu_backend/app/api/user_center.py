"""
用户个人中心路由
处理用户个人信息的查看、编辑、头像上传、手机号管理、密码修改、账号注销、隐私设置等接口
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.user_center import (
    UserProfileResponse,
    UpdateNicknameRequest,
    UpdateAvatarRequest,
    BindPhoneRequest,
    ChangePasswordRequest,
    AccountDeactivationRequest,
    PrivacySettingsRequest,
    PrivacySettingsResponse,
    AvatarUploadResponse,
    MessageResponse,
)
from app.schemas.common import ApiResponse
from app.services.user.user_center_service import user_center_service
from app.utils.dependencies import require_current_user
from app.utils.response import response

router = APIRouter(prefix="/api/user/center", tags=["用户个人中心"])


# ============================================================================
# 个人信息查看与编辑
# ============================================================================


@router.get(
    "",
    summary="获取个人信息",
    description="获取当前登录用户的个人信息",
    response_model=ApiResponse[UserProfileResponse],
    responses={
        200: {"description": "获取成功"},
        401: {"description": "未授权"}
    }
)
async def get_profile(
    current_user: str = Depends(require_current_user)
) -> Dict[str, Any]:
    """获取当前用户的个人信息"""
    result = user_center_service.get_profile(current_user)

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("error", "获取个人信息失败")
        )

    return response.success(data=result["data"])


@router.put(
    "/nickname",
    summary="更新昵称",
    description="更新当前用户的昵称（1-50个字符）",
    response_model=ApiResponse[MessageResponse],
    responses={
        200: {"description": "更新成功"},
        400: {"description": "参数错误"},
        401: {"description": "未授权"}
    }
)
async def update_nickname(
    request: UpdateNicknameRequest,
    current_user: str = Depends(require_current_user)
) -> Dict[str, Any]:
    """更新用户昵称"""
    result = user_center_service.update_nickname(
        user_id=current_user,
        nickname=request.nickname
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "更新昵称失败")
        )

    return response.success(message=result.get("message", "昵称更新成功"))


@router.put(
    "/avatar",
    summary="更新头像",
    description="更新当前用户的头像，支持 Base64 编码的图片数据（最大5MB）",
    response_model=ApiResponse[AvatarUploadResponse],
    responses={
        200: {"description": "更新成功"},
        400: {"description": "参数错误或文件过大"},
        401: {"description": "未授权"},
        500: {"description": "OSS服务异常"}
    }
)
async def update_avatar(
    request: UpdateAvatarRequest,
    current_user: str = Depends(require_current_user)
) -> Dict[str, Any]:
    """更新用户头像"""
    result = user_center_service.update_avatar(
        user_id=current_user,
        avatar_data=request.avatar_data,
        file_name=request.file_name
    )

    if not result.get("success"):
        error_code = result.get("error_code")
        status_code = status.HTTP_400_BAD_REQUEST

        if error_code == "OSS_NOT_INITIALIZED":
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        elif error_code == "USER_NOT_FOUND":
            status_code = status.HTTP_404_NOT_FOUND

        raise HTTPException(
            status_code=status_code,
            detail=result.get("error", "更新头像失败")
        )

    return response.success(
        message=result.get("message", "头像更新成功"),
        data={"avatar_url": result.get("avatar_url")}
    )


# ============================================================================
# 手机号管理
# ============================================================================


@router.put(
    "/phone",
    summary="绑定/更换手机号",
    description="绑定或更换当前用户的手机号（需要短信验证码）",
    response_model=ApiResponse[MessageResponse],
    responses={
        200: {"description": "绑定成功"},
        400: {"description": "手机号已被使用或验证码错误"},
        401: {"description": "未授权"}
    }
)
async def bind_phone(
    request: BindPhoneRequest,
    current_user: str = Depends(require_current_user)
) -> Dict[str, Any]:
    """绑定或更换手机号"""
    result = user_center_service.bind_phone(
        user_id=current_user,
        phone=request.phone,
        sms_code=request.sms_code
    )

    if not result.get("success"):
        error_code = result.get("error_code")
        status_code = status.HTTP_400_BAD_REQUEST

        if error_code == "USER_NOT_FOUND":
            status_code = status.HTTP_404_NOT_FOUND

        raise HTTPException(
            status_code=status_code,
            detail=result.get("error", "绑定手机号失败")
        )

    return response.success(message=result.get("message", "手机号绑定成功"))


# ============================================================================
# 密码管理
# ============================================================================


@router.put(
    "/password",
    summary="修改密码",
    description="修改当前用户的密码（需要提供旧密码验证）",
    response_model=ApiResponse[MessageResponse],
    responses={
        200: {"description": "修改成功"},
        400: {"description": "旧密码错误"},
        401: {"description": "未授权"}
    }
)
async def change_password(
    request: ChangePasswordRequest,
    current_user: str = Depends(require_current_user)
) -> Dict[str, Any]:
    """修改密码"""
    result = user_center_service.change_password(
        user_id=current_user,
        old_password=request.old_password,
        new_password=request.new_password
    )

    if not result.get("success"):
        error_code = result.get("error_code")
        status_code = status.HTTP_400_BAD_REQUEST

        if error_code == "USER_NOT_FOUND":
            status_code = status.HTTP_404_NOT_FOUND

        raise HTTPException(
            status_code=status_code,
            detail=result.get("error", "修改密码失败")
        )

    return response.success(message=result.get("message", "密码修改成功"))


# ============================================================================
# 账号注销
# ============================================================================


@router.delete(
    "",
    summary="账号注销",
    description="注销当前用户的账号（软删除，将用户状态设置为 disabled）",
    response_model=ApiResponse[MessageResponse],
    responses={
        200: {"description": "注销成功"},
        400: {"description": "密码错误"},
        401: {"description": "未授权"}
    }
)
async def deactivate_account(
    request: AccountDeactivationRequest,
    current_user: str = Depends(require_current_user)
) -> Dict[str, Any]:
    """账号注销"""
    result = user_center_service.deactivate_account(
        user_id=current_user,
        password=request.password,
        reason=request.reason
    )

    if not result.get("success"):
        error_code = result.get("error_code")
        status_code = status.HTTP_400_BAD_REQUEST

        if error_code == "USER_NOT_FOUND":
            status_code = status.HTTP_404_NOT_FOUND

        raise HTTPException(
            status_code=status_code,
            detail=result.get("error", "账号注销失败")
        )

    return response.success(message=result.get("message", "账号已成功注销"))


# ============================================================================
# 隐私设置
# ============================================================================


@router.get(
    "/privacy",
    summary="获取隐私设置",
    description="获取当前用户的隐私设置",
    response_model=ApiResponse[PrivacySettingsResponse],
    responses={
        200: {"description": "获取成功"},
        401: {"description": "未授权"}
    }
)
async def get_privacy_settings(
    current_user: str = Depends(require_current_user)
) -> Dict[str, Any]:
    """获取隐私设置"""
    result = user_center_service.get_privacy_settings(current_user)

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "获取隐私设置失败")
        )

    return response.success(data=result["data"])


@router.put(
    "/privacy",
    summary="更新隐私设置",
    description="更新当前用户的隐私设置",
    response_model=ApiResponse[MessageResponse],
    responses={
        200: {"description": "更新成功"},
        401: {"description": "未授权"}
    }
)
async def update_privacy_settings(
    request: PrivacySettingsRequest,
    current_user: str = Depends(require_current_user)
) -> Dict[str, Any]:
    """更新隐私设置"""
    result = user_center_service.update_privacy_settings(
        user_id=current_user,
        show_phone=request.show_phone,
        show_member_info=request.show_member_info,
        allow_search=request.allow_search
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "更新隐私设置失败")
        )

    return response.success(message=result.get("message", "隐私设置更新成功"))
