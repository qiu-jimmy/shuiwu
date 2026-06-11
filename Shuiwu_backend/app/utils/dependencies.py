"""
FastAPI依赖注入
用于获取当前用户等
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db import get_db
from app.utils.jwt_utils import verify_token
from app.services.user.user_repository import user_repository


# HTTP Bearer认证
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """
    获取当前登录用户ID（可选认证）
    如果未提供token或token无效，返回None
    """
    if credentials is None:
        return None

    token = credentials.credentials
    user_id = verify_token(token)

    if user_id is None:
        return None

    return user_id


async def require_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """
    获取当前登录用户ID（必须认证）
    如果未认证，抛出401异常
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    user_id = verify_token(token)

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id


async def get_current_user_info(
    user_id: str = Depends(require_current_user)
) -> dict:
    """
    获取当前用户完整信息
    如果用户不存在，抛出401异常
    """
    user = user_repository.get_user_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"用户不存在: {user_id}"
        )

    if user.get("status") == "disabled":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )

    if user.get("status") == "banned":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被封禁"
        )

    # 调用分销服务获取分销商信息和佣金
    from app.services.distribution.distribution_service import distribution_service

    distributor_stats = distribution_service.get_distributor_stats(user_id)
    if distributor_stats.get("success"):
        user["is_distributor"] = True
        # 获取分销商推广码
        code_result = distribution_service.get_my_distributor_code(user_id)
        if code_result.get("success"):
            user["distributor_code"] = code_result.get("distributor_code")
        else:
            user["distributor_code"] = None
        user["total_commission"] = distributor_stats["stats"].get("total_commission", 0.0)
    else:
        user["is_distributor"] = False
        user["distributor_code"] = None
        user["total_commission"] = 0.0

    # 会员信息直接从 users 表返回
    # - member_level: 会员等级（package_id），对应 member_packages 表的套餐ID
    # - member_expire_at: 会员到期时间
    # 不再从订单表查询，直接使用 users 表中的原始值

    # 根据 member_level 查询套餐名称
    member_level = user.get("member_level")
    if member_level:
        from app.services.member.member_repository import member_repository
        package = member_repository.get_package_by_id(member_level)
        user["member_package_name"] = package.get("name") if package else None
    else:
        user["member_package_name"] = None

    # 企业认证状态默认为 false
    user["is_enterprise_verified"] = False

    # 检查是否是税务师
    from app.services.tax_accountant.tax_accountant_service import tax_accountant_service
    user["is_tax_accountant"] = tax_accountant_service.is_tax_accountant(user_id)

    return user


async def require_admin(
    user_info: dict = Depends(get_current_user_info)
) -> dict:
    """
    要求管理员权限
    如果用户不是管理员，抛出403异常
    """
    # TODO: 实现管理员权限检查逻辑
    # 可以在users表中添加is_admin字段
    # 或者通过user_tags表检查管理员标签

    # 暂时通过user_type判断
    if user_info.get("user_type") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )

    return user_info


# ============================================================================
# 新的角色权限系统依赖注入
# ============================================================================

async def get_current_user_with_roles(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """
    获取当前用户信息（包含角色和权限）

    Returns:
        dict: 包含用户信息和角色权限的字典
        {
            "user_id": str,
            "username": str,
            "nickname": str,
            "email": str,
            "roles": List[str],
            "permissions": List[str],
            "is_admin": bool,
            "is_distributor": bool
        }
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    user_id = verify_token(token)

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 获取用户基本信息
    user = user_repository.get_user_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在"
        )

    if user.get("status") == "disabled":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )

    if user.get("status") == "banned":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被封禁"
        )

    # 获取用户角色和权限
    from app.services.role.role_service import role_service

    roles = role_service.get_user_roles(user_id)
    role_names = [r["role"] for r in roles]
    permissions = role_service.get_user_all_permissions(user_id)

    # 检查是否是管理员
    is_admin = role_service.check_user_is_admin(user_id)

    # 检查是否是税务师
    from app.services.tax_accountant.tax_accountant_service import tax_accountant_service
    is_tax_accountant = tax_accountant_service.is_tax_accountant(user_id)

    # 查询分销商信息
    from app.infra.db import get_sync_engine

    try:
        engine = get_sync_engine()
        with engine.connect() as conn:
            # 转义 user_id 中的单引号
            safe_user_id = user_id.replace("'", "''")

            # 使用原始 DBAPI 连接执行 SQL
            raw_conn = conn.connection
            cursor = raw_conn.cursor()
            cursor.execute(
                """
                    SELECT user_id, distributor_code, status
                    FROM business.distributors
                    WHERE user_id = %s AND status = 'active'
                """,
                (safe_user_id,)
            )
            result = cursor.fetchone()

            if result:
                user["is_distributor"] = True
                user["distributor_code"] = result[1]
            else:
                user["is_distributor"] = False
                user["distributor_code"] = None
    except Exception:
        user["is_distributor"] = False
        user["distributor_code"] = None

    # 返回完整的用户信息
    return {
        "user_id": user_id,
        "username": user.get("username"),
        "nickname": user.get("nickname"),
        "email": user.get("email"),
        "phone": user.get("phone"),
        "avatar_url": user.get("avatar_url"),
        "status": user.get("status"),
        "roles": role_names,
        "permissions": permissions,
        "is_admin": is_admin,
        "is_distributor": user.get("is_distributor", False),
        "distributor_code": user.get("distributor_code"),
        "is_tax_accountant": is_tax_accountant
    }


async def require_current_admin(
    user_info: dict = Depends(get_current_user_with_roles)
) -> dict:
    """
    要求管理员身份（使用新的角色权限系统）

    此依赖注入函数会：
    1. 验证用户token
    2. 检查用户是否拥有管理员角色（admin或super_admin）
    3. 返回包含用户信息和角色权限的字典

    Returns:
        dict: 包含用户信息和角色权限的字典
        {
            "user_id": str,
            "username": str,
            "nickname": str,
            "email": str,
            "roles": List[str],
            "permissions": List[str],
            "is_admin": bool
        }
    """
    # 检查是否是管理员
    if not user_info.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )

    # 为了向后兼容，返回格式保持与旧版本相似
    # 但使用新的字段名和结构
    return {
        "user_id": user_info.get("user_id"),
        "admin_id": user_info.get("user_id"),  # 向后兼容：admin_id = user_id
        "username": user_info.get("username"),
        "nickname": user_info.get("nickname"),
        "email": user_info.get("email"),
        "phone": user_info.get("phone"),
        "avatar_url": user_info.get("avatar_url"),
        "status": user_info.get("status"),
        "roles": user_info.get("roles", []),
        "role": user_info.get("roles", [])[0] if user_info.get("roles") else None,  # 向后兼容：主角色
        "permissions": user_info.get("permissions", []),
        "is_admin": user_info.get("is_admin", False),
        "is_distributor": user_info.get("is_distributor", False),
        "distributor_code": user_info.get("distributor_code")
    }


async def check_admin_permission(permission: str):
    """
    检查管理员权限的依赖工厂函数（使用新的角色权限系统）

    使用方法:
    @router.get("/some-path")
    async def some_endpoint(
        admin_info: dict = Depends(check_admin_permission("user.manage"))
    ):
        ...

    Args:
        permission: 需要的权限代码（如 "user.manage", "knowledge.view"）
    """
    async def _check_permission(
        admin_info: dict = Depends(require_current_admin)
    ) -> dict:
        permissions = admin_info.get("permissions", [])
        if permission not in permissions and "*/*" not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"缺少权限: {permission}"
            )
        return admin_info

    return _check_permission


async def require_role(required_role: str):
    """
    要求用户拥有指定角色的依赖工厂函数

    使用方法:
    @router.get("/admin-only")
    async def admin_only_endpoint(
        user_id: str = Depends(require_role("admin"))
    ):
        ...

    支持的角色: super_admin, admin, operator, vip_user等
    """
    async def _check_role(
        user_id: str = Depends(require_current_user)
    ) -> str:
        from app.services.role.role_service import role_service

        if not role_service.check_user_has_role(user_id, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要 {required_role} 角色权限"
            )

        return user_id

    return _check_role


async def require_permission(required_permission: str):
    """
    要求用户拥有指定权限的依赖工厂函数

    使用方法:
    @router.post("/create-user")
    async def create_user(
        user_id: str = Depends(require_permission("user.manage"))
    ):
        ...

    权限格式: module.action (如: user.manage, knowledge.view)
    """
    async def _check_permission(
        user_id: str = Depends(require_current_user)
    ) -> str:
        from app.services.role.role_service import role_service

        if not role_service.check_user_has_permission(user_id, required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"缺少权限: {required_permission}"
            )

        return user_id

    return _check_permission


async def require_admin_role(
    user_info: dict = Depends(get_current_user_with_roles)
) -> dict:
    """
    要求管理员角色（admin或super_admin）

    使用方法:
    @router.get("/admin-endpoint")
    async def admin_endpoint(
        user_info: dict = Depends(require_admin_role)
    ):
        ...

    Returns:
        dict: 包含用户信息的字典
    """
    if not user_info.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )

    return user_info
