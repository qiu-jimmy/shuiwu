"""
会员权限装饰器
用于在任何接口中快速添加会员权限校验

使用示例:
    @router.post("/chat/rag")
    @require_privilege("rag")
    @require_quota("daily_chats")
    async def rag_chat(message: str):
        # 直接写业务逻辑，不需要任何权限检查代码
        return execute_rag(message)
"""
from functools import wraps
from typing import Callable, Optional, List, Dict, Any
from fastapi import Request, HTTPException
from app.services.member.member_service import member_service
from app.utils.response import response


# ==================== 管理员权限装饰器 ====================

def require_admin(*, allow_roles: Optional[List[str]] = None):
    """
    管理员权限装饰器

    参数:
        allow_roles: 允许的角色列表（默认只允许 admin）
                    例如: ["admin", "super_admin", "tax_accountant"]

    使用示例:
        @router.get("/admin/list")
        @require_admin()
        async def admin_list():
            return get_all_users()

        @router.post("/tax/process")
        @require_admin(allow_roles=["admin", "tax_accountant"])
        async def process_tax():
            return process()
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从参数中获取 Request 对象
            request = _extract_request(args, kwargs)
            if not request:
                return response.fail(message="无法获取请求上下文", code=500)

            # 从 request.state 获取 user_id 和 role (由 JWT 中间件设置)
            user_id = getattr(request.state, "user_id", None)
            user_role = getattr(request.state, "role", None)

            if not user_id:
                return response.fail(message="未授权用户", code=401)

            # 检查是否为管理员
            allowed = allow_roles or ["admin"]

            if user_role not in allowed:
                return response.fail(
                    message=f"需要管理员权限，允许的角色: {', '.join(allowed)}",
                    code=403
                )

            # 权限检查通过，执行原函数
            return await func(*args, **kwargs)

        return wrapper
    return decorator


# ==================== 自定义权限检查注册表 ====================

_custom_privilege_checkers: Dict[str, Callable] = {}


def register_privilege_checker(privilege_type: str):
    """
    注册自定义权限检查器

    用于支持复杂的权限逻辑，例如：
    - 需要多条件组合检查
    - 需要查询其他数据源
    - 需要特殊的业务规则

    使用示例:
        @register_privilege_checker("team_collaboration")
        def check_team_collaboration(user_id: str) -> dict:
            # 自定义检查逻辑
            return {"has_privilege": True, "reason": ""}

        @router.post("/team/collaborate")
        @require_privilege("team_collaboration")
        async def collaborate():
            pass
    """
    def decorator(func: Callable):
        _custom_privilege_checkers[privilege_type] = func
        return func
    return decorator


# ==================== 权限装饰器 ====================

def require_privilege(privilege_type: str, auto_record: bool = True):
    """
    功能权限装饰器 - 检查用户是否有权使用某项功能

    参数:
        privilege_type: 权益类型
            - rag: RAG功能
            - web_search: 网络搜索
            - mcp_tools: MCP工具
            - 或自定义注册的权限类型
        auto_record: 是否自动记录使用（默认True）

    使用示例:
        @router.post("/chat/rag")
        @require_privilege("rag")
        async def rag_chat(message: str):
            return execute_rag(message)

        @router.post("/advanced/search")
        @require_any_privilege(["web_search", "rag"])
        async def advanced_search(query: str):
            return search(query)
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从参数中获取 Request 对象
            request = _extract_request(args, kwargs)
            if not request:
                return response.fail(message="无法获取请求上下文", code=500)

            # 从 request.state 获取 user_id (由 JWT 中间件设置)
            user_id = getattr(request.state, "user_id", None)
            if not user_id:
                return response.fail(message="未授权用户", code=401)

            # 检查是否有自定义检查器
            if privilege_type in _custom_privilege_checkers:
                # 使用自定义检查器
                checker = _custom_privilege_checkers[privilege_type]
                result = checker(user_id)
            else:
                # 使用标准权限检查
                result = member_service.check_privilege(user_id, privilege_type)

            if not result.get("success"):
                return response.fail(message=result.get("error", "权限检查失败"))

            if not result.get("has_privilege"):
                return response.fail(
                    message=result.get("reason", "权限不足"),
                    code="PERMISSION_DENIED"
                )

            # 自动记录使用
            if auto_record:
                member_service.record_usage(user_id, privilege_type, 1)

            # 将权限信息添加到 request.state 供后续使用
            request.state.privilege_check = result

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_quota(quota_type: str, consume: int = 1):
    """
    配额权限装饰器 - 检查用户是否有足够的配额

    参数:
        quota_type: 配额类型
            - daily_chats: 每日聊天次数
            - kb_count: 知识库数量
            - kb_documents: 知识库文档数
            - file_storage_mb: 文件存储(MB)
            - file_count: 文件数量
        consume: 消耗数量（默认1）

    使用示例:
        @router.post("/knowledge/create")
        @require_quota("kb_count")
        async def create_knowledge(name: str):
            return create_kb(name)

        @router.post("/file/upload")
        @require_quota("file_storage_mb", consume=10)
        async def upload_file(file: UploadFile):
            return save_file(file)
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = _extract_request(args, kwargs)
            if not request:
                return response.fail(message="无法获取请求上下文", code=500)

            user_id = getattr(request.state, "user_id", None)
            if not user_id:
                return response.fail(message="未授权用户", code=401)

            # 获取会员统计信息
            stats_result = member_service.get_member_stats(user_id)

            if not stats_result.get("success"):
                return response.fail(message="获取会员信息失败")

            stats = stats_result

            # 检查配额
            quota_mapping = {
                "daily_chats": ("today_chats", "max_daily_chats", "今日聊天次数"),
                "kb_count": ("kb_count", "max_kb_count", "知识库数量"),
                "kb_documents": ("kb_documents_count", "max_kb_documents", "知识库文档数"),
                "file_storage_mb": ("used_storage_mb", "max_file_storage_mb", "文件存储空间"),
                "file_count": ("file_count", "max_file_count", "文件数量"),
            }

            if quota_type not in quota_mapping:
                return response.fail(message=f"不支持的配额类型: {quota_type}")

            used_key, max_key, display_name = quota_mapping[quota_type]
            used = stats.get(used_key, 0)
            max_quota = stats.get(max_key, 0)

            # max_daily_chats 为 -1 表示无限制
            if max_key == "max_daily_chats" and max_quota == -1:
                pass  # 无限制，不需要检查
            elif used + consume > max_quota:
                remaining = max_quota - used
                return response.fail(
                    message=f"{display_name}不足，剩余: {remaining}，需要: {consume}",
                    code="QUOTA_EXCEEDED",
                    data={
                        "used": used,
                        "max": max_quota,
                        "remaining": remaining,
                        "required": consume
                    }
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_member_level(min_level: str = "basic"):
    """
    会员套餐装饰器 - 要求指定套餐

    新架构说明：
    - 不再使用等级概念（free < basic < premium < enterprise）
    - 套餐 ID（package_id）是完全自定义的，如：free, vip_month, premium_year
    - 所有权益都在套餐表中配置
    - 支持通过 priority 比较套餐优先级

    参数:
        min_level: 套餐 ID（如：vip_month, premium_year）
                  如果套餐设置了 custom_config.priority，
                  则支持优先级比较（当前优先级 >= 目标优先级）

    使用示例:
        @router.post("/advanced/feature")
        @require_member_level("vip_month")
        async def advanced_feature():
            return execute_advanced()

    优先级配置示例:
        在 member_packages 表的 custom_config 中：
        {
            "priority": 1  // 数字越大，等级越高
        }

        如果用户有 priority=2 的套餐，要求 min_level="vip_month"(priority=1)
        则会通过检查（2 >= 1）
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = _extract_request(args, kwargs)
            if not request:
                return response.fail(message="无法获取请求上下文", code=500)

            user_id = getattr(request.state, "user_id", None)
            if not user_id:
                return response.fail(message="未授权用户", code=401)

            # 管理员跳过检查
            user_type = getattr(request.state, "user_type", None)
            role = getattr(request.state, "role", None)
            if user_type == "admin" or role in ["admin", "super_admin"]:
                return await func(*args, **kwargs)

            # 获取会员信息
            member_info = member_service.get_member_info(user_id)

            if not member_info.get("success"):
                return response.fail(message="获取会员信息失败")

            # 检查会员是否有效
            if not member_info.get("is_member_valid"):
                return response.fail(
                    message="此功能需要会员权限，请先开通会员",
                    code="MEMBER_REQUIRED"
                )

            current_package_id = member_info.get("member_level", "")

            # 完全匹配
            if current_package_id == min_level:
                return await func(*args, **kwargs)

            # 尝试通过 priority 比较
            try:
                # 获取当前套餐优先级
                package_result = member_service.get_package(current_package_id)
                if package_result.get("success"):
                    current_pkg = package_result.get("package", {})
                    current_priority = current_pkg.get("custom_config", {}).get("priority", 0)
                else:
                    current_priority = 0

                # 获取目标套餐优先级
                target_result = member_service.get_package(min_level)
                if target_result.get("success"):
                    target_pkg = target_result.get("package", {})
                    target_priority = target_pkg.get("custom_config", {}).get("priority", 0)
                else:
                    target_priority = 0

                # 比较优先级（当前 >= 目标）
                if current_priority >= target_priority and current_priority > 0:
                    return await func(*args, **kwargs)

            except Exception:
                pass

            return response.fail(
                message=f"此功能需要 {min_level} 套餐（当前: {current_package_id}）",
                code="UPGRADE_REQUIRED"
            )

        return wrapper
    return decorator


def require_any_privilege(privilege_types: List[str], auto_record: bool = True):
    """
    多权限OR装饰器 - 满足任一权限即可

    参数:
        privilege_types: 权限类型列表
        auto_record: 是否自动记录使用

    使用示例:
        @router.post("/chat/advanced")
        @require_any_privilege(["rag", "web_search"])
        async def advanced_chat(message: str):
            # 只要有RAG或网络搜索任一权限即可
            return execute_advanced(message)
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = _extract_request(args, kwargs)
            if not request:
                return response.fail(message="无法获取请求上下文", code=500)

            user_id = getattr(request.state, "user_id", None)
            if not user_id:
                return response.fail(message="未授权用户", code=401)

            # 检查所有权限
            has_any = False
            granted_privilege = None

            for privilege_type in privilege_types:
                # 优先使用自定义检查器
                if privilege_type in _custom_privilege_checkers:
                    result = _custom_privilege_checkers[privilege_type](user_id)
                else:
                    result = member_service.check_privilege(user_id, privilege_type)

                if result.get("has_privilege"):
                    has_any = True
                    granted_privilege = privilege_type
                    break

            if not has_any:
                return response.fail(
                    message=f"需要以下任一权限: {', '.join(privilege_types)}",
                    code="PERMISSION_DENIED"
                )

            # 自动记录使用
            if auto_record:
                member_service.record_usage(user_id, granted_privilege, 1)

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_all_privileges(privilege_types: List[str], auto_record: bool = True):
    """
    多权限AND装饰器 - 需要同时满足所有权限

    参数:
        privilege_types: 权限类型列表
        auto_record: 是否自动记录使用

    使用示例:
        @router.post("/chat/full-featured")
        @require_all_privileges(["rag", "web_search", "mcp_tools"])
        async def full_chat(message: str):
            # 需要同时具备RAG、网络搜索、MCP工具权限
            return execute_full(message)
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = _extract_request(args, kwargs)
            if not request:
                return response.fail(message="无法获取请求上下文", code=500)

            user_id = getattr(request.state, "user_id", None)
            if not user_id:
                return response.fail(message="未授权用户", code=401)

            # 检查所有权限
            missing_privileges = []

            for privilege_type in privilege_types:
                # 优先使用自定义检查器
                if privilege_type in _custom_privilege_checkers:
                    result = _custom_privilege_checkers[privilege_type](user_id)
                else:
                    result = member_service.check_privilege(user_id, privilege_type)

                if not result.get("has_privilege"):
                    missing_privileges.append(privilege_type)

            if missing_privileges:
                return response.fail(
                    message=f"缺少以下权限: {', '.join(missing_privileges)}",
                    code="PERMISSION_DENIED"
                )

            # 自动记录使用
            if auto_record:
                for privilege_type in privilege_types:
                    member_service.record_usage(user_id, privilege_type, 1)

            return await func(*args, **kwargs)
        return wrapper
    return decorator


# ==================== 工具函数 ====================

def _extract_request(args: tuple, kwargs: dict) -> Optional[Request]:
    """从函数参数中提取 Request 对象"""
    # 从 kwargs 中查找
    if "request" in kwargs:
        return kwargs["request"]

    # 从 args 中查找
    for arg in args:
        if isinstance(arg, Request):
            return arg

    return None
