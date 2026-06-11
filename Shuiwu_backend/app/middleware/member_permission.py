"""
增强版会员权限装饰器系统
==========================
基于 business.member_packages 表的声明式权限认证

特点：
1. 自动查询用户套餐配置进行权限验证
2. 支持 custom_config 中的动态权限扩展
3. 细粒度错误提示，明确告知缺少的权益
4. 支持组合条件（AND/OR）
5. 权限检查结果缓存，避免重复查询
6. 支持通过环境变量全局禁用权限系统（开发模式）

使用示例：
    # 方式1：检查单个权益
    @router.post("/chat/rag")
    @require_member_privilege("rag")
    async def rag_chat():
        pass

    # 方式2：检查多个权益（AND）
    @router.post("/advanced/feature")
    @require_member_features(
        privileges=["rag", "web_search"],
        quotas={"kb_count": 1}
    )
    async def advanced_feature():
        pass

    # 方式3：检查多个权益（OR）
    @router.post("/flexible/feature")
    @require_any_member_privilege(["rag", "web_search"])
    async def flexible_feature():
        pass

    # 方式4：检查 custom_config 中的动态权限
    @router.post("/custom/feature")
    @require_member_privilege("advanced_analytics")  # 自动从 custom_config.enable_advanced_analytics 读取
    async def custom_feature():
        pass

    # 方式5：配置套餐时添加自定义权限
    # 在 member_packages 表的 custom_config 中：
    # {"enable_advanced_analytics": true, "max_api_calls": 1000}

环境变量配置：
    ENABLE_MEMBER_PERMISSION=true   # 启用会员权限系统（默认）
    ENABLE_MEMBER_PERMISSION=false  # 禁用会员权限系统（开发/测试模式）
"""
import os
from functools import wraps
from typing import Callable, Optional, List, Dict, Any, Union, Literal
from fastapi import Request, HTTPException
from app.services.member.member_service import member_service
from app.utils.response import response
from datetime import datetime
import hashlib
import json


# ============================================================================
# 全局开关（通过环境变量控制）
# ============================================================================

def is_member_permission_enabled() -> bool:
    """
    检查会员权限系统是否启用

    通过环境变量 ENABLE_MEMBER_PERMISSION 控制：
    - true (默认): 启用会员权限系统
    - false: 禁用会员权限系统（开发/测试模式）

    禁用时，所有权限检查都将自动通过
    """
    return os.getenv("ENABLE_MEMBER_PERMISSION", "true").lower() == "true"


# ============================================================================
# 权限元数据定义
# ============================================================================

# 标准权益类型及其对应的套餐字段
STANDARD_PRIVILEGE_FIELDS = {
    "rag": "enable_rag",
    "web_search": "enable_web_search",
    "mcp_tools": "enable_mcp_tools",
    "advanced_analytics": "enable_advanced_analytics",  # 可通过 custom_config 扩展
    "team_collaboration": "enable_team_collaboration",
    "api_access": "enable_api_access",
    "export_data": "enable_export_data",
    "ai_writing": "enable_ai_writing",
    "voice_input": "enable_voice_input",
    # 新增权益（通过 custom_config 配置）
    "invoice_penetration": "enable_invoice_penetration",   # 发票穿透
    "panorama": "enable_panorama",                         # 全景报告
    "business_risk": "enable_business_risk",              # 经营风险
    # 合同审查相关权益
    "contract_screening": "enable_contract_screening",    # 合同筛查（基础版，3页内）
    "contract_review": "enable_contract_review",          # 合同审查（完整版，多页合同）
}

# 权益类型的中文名称映射（用于错误消息显示）
PRIVILEGE_DISPLAY_NAMES = {
    "rag": "知识库增强",
    "web_search": "联网搜索",
    "mcp_tools": "MCP工具",
    "advanced_analytics": "高级分析",
    "team_collaboration": "团队协作",
    "api_access": "API访问",
    "export_data": "数据导出",
    "ai_writing": "AI写作",
    "voice_input": "语音输入",
    "invoice_penetration": "发票穿透",
    "panorama": "全景报告",
    "business_risk": "经营风险查询",
    "contract_screening": "合同筛查",
    "contract_review": "合同审查",
}

# 标准配额类型
QUOTA_FIELDS = {
    "daily_chats": ("today_chats", "max_daily_chats", "每日聊天次数"),
    "kb_count": ("kb_count", "max_kb_count", "知识库数量"),
    "kb_documents": ("kb_documents_count", "max_kb_documents", "知识库文档数"),
    "file_storage_mb": ("used_storage_mb", "max_file_storage_mb", "文件存储空间(MB)"),
    "file_count": ("file_count", "max_file_count", "文件数量"),
    # 新增配额类型（通过 custom_config 配置，按次计费）
    "invoice_penetration": ("invoice_penetration_used", "max_invoice_penetration", "发票穿透次数"),
    "panorama": ("panorama_used", "max_panorama", "全景报告次数"),
    "business_risk": ("business_risk_used", "max_business_risk", "经营风险查询次数"),
    # 合同审查配额（通过 custom_config 配置，按次计费）
    "contract_review_count": ("contract_review_count_used", "max_contract_review_count", "合同审查次数"),
    # 合同审查配额（通过 custom_config 配置，按页数计费）
    "contract_screening_pages": ("contract_screening_pages_used", "contract_screening_pages", "合同筛查页数"),
    "multi_page_contract_pages": ("multi_page_contract_pages_used", "multi_page_contract_pages", "多页合同审查页数"),
}

# 注意：不再使用固定的等级列表
# 套餐 ID（package_id）是完全自定义的，如：free, vip_month, premium_year 等
# 所有权益都在套餐表的 enable_xxx 字段和 custom_config 中配置


# ============================================================================
# 缓存机制
# ============================================================================

class MemberInfoCache:
    """会员信息缓存（进程级别）"""

    def __init__(self, ttl_seconds: int = 300):
        self.cache: Dict[str, tuple] = {}
        self.ttl = ttl_seconds

    def get(self, user_id: str) -> Optional[Dict[str, Any]]:
        if user_id in self.cache:
            data, timestamp = self.cache[user_id]
            if (datetime.now() - timestamp).total_seconds() < self.ttl:
                return data
            else:
                del self.cache[user_id]
        return None

    def set(self, user_id: str, data: Dict[str, Any]):
        self.cache[user_id] = (data, datetime.now())

    def clear(self, user_id: Optional[str] = None):
        if user_id:
            self.cache.pop(user_id, None)
        else:
            self.cache.clear()


# 全局缓存实例（60秒TTL）
_member_info_cache = MemberInfoCache(ttl_seconds=60)


def clear_member_cache(user_id: Optional[str] = None):
    """清除会员信息缓存"""
    _member_info_cache.clear(user_id)


# ============================================================================
# 核心检查函数
# ============================================================================

def _get_user_member_info(user_id: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
    """
    获取用户会员信息（含缓存）

    Returns:
        包含用户会员权益配置的字典，结构：
        {
            "member_level": str,
            "member_expire_at": datetime,
            "is_member_valid": bool,
            # 套餐权益配置
            "max_daily_chats": int,
            "max_kb_count": int,
            "enable_rag": bool,
            "enable_web_search": bool,
            "custom_config": dict,
            # 使用统计
            "today_chats": int,
            "kb_count": int,
            ...
        }
    """
    if use_cache:
        cached = _member_info_cache.get(user_id)
        if cached:
            return cached

    # 从数据库获取
    stats_result = member_service.get_member_stats(user_id)
    if not stats_result.get("success"):
        return None

    # 同时获取套餐信息
    member_info = member_service.member_repo.get_user_member_info(user_id)
    if member_info:
        stats_result.update({
            "custom_config": member_info.get("custom_config") or {},
            "benefits": member_info.get("benefits", []),
        })

    # 检查会员有效性
    is_valid = member_service.member_repo.is_member_valid(user_id)
    stats_result["is_member_valid"] = is_valid

    if use_cache:
        _member_info_cache.set(user_id, stats_result)

    return stats_result


def _check_privilege_from_config(
    member_info: Dict[str, Any],
    privilege_type: str
) -> Dict[str, Any]:
    """
    从套餐配置中检查权益

    支持动态权限检查顺序：
    1. 检查标准字段（enable_rag, enable_web_search 等）
    2. 检查 custom_config.enable_{privilege_type}
    3. 检查 custom_config.{privilege_type}
    """
    # 1. 检查标准字段
    if privilege_type in STANDARD_PRIVILEGE_FIELDS:
        field_name = STANDARD_PRIVILEGE_FIELDS[privilege_type]
        has_privilege = member_info.get(field_name, False)
        display_name = _get_privilege_display_name(privilege_type)

        return {
            "has_privilege": has_privilege,
            "reason": "" if has_privilege else f"当前套餐不支持{display_name}功能",
            "source": "standard_field",
            "field": field_name
        }

    # 2. 检查 custom_config
    custom_config = member_info.get("custom_config") or {}
    if isinstance(custom_config, dict):
        # 2a. 检查 enable_{privilege_type}
        config_key = f"enable_{privilege_type}"
        if config_key in custom_config:
            has_privilege = bool(custom_config.get(config_key, False))
            display_name = _get_privilege_display_name(privilege_type)
            return {
                "has_privilege": has_privilege,
                "reason": "" if has_privilege else f"当前套餐不支持{display_name}功能",
                "source": "custom_config",
                "field": config_key
            }

        # 2b. 检查直接用 privilege_type 作为 key
        if privilege_type in custom_config:
            has_privilege = bool(custom_config.get(privilege_type, False))
            display_name = _get_privilege_display_name(privilege_type)
            return {
                "has_privilege": has_privilege,
                "reason": "" if has_privilege else f"当前套餐不支持{display_name}功能",
                "source": "custom_config",
                "field": privilege_type
            }

    # 3. 尝试动态查找表字段 enable_{privilege_type}
    field_name = f"enable_{privilege_type}"
    if field_name in member_info:
        has_privilege = bool(member_info.get(field_name, False))
        display_name = _get_privilege_display_name(privilege_type)
        return {
            "has_privilege": has_privilege,
            "reason": "" if has_privilege else f"当前套餐不支持{display_name}功能",
            "source": "dynamic_field",
            "field": field_name
        }

    # 4. 未找到该权益配置
    display_name = _get_privilege_display_name(privilege_type)
    return {
        "has_privilege": False,
        "reason": f"未知的权益类型: {privilege_type}",
        "source": "unknown"
    }


def _check_quota_from_config(
    member_info: Dict[str, Any],
    quota_type: str,
    consume: int = 1
) -> Dict[str, Any]:
    """
    检查配额是否足够

    支持两种配额来源：
    1. 标准字段（如 max_daily_chats）
    2. custom_config 中的自定义配额（如 max_invoice_penetration）
    """
    if quota_type not in QUOTA_FIELDS:
        return {
            "has_quota": False,
            "reason": f"不支持的配额类型: {quota_type}"
        }

    used_key, max_key, display_name = QUOTA_FIELDS[quota_type]
    used = member_info.get(used_key, 0)

    # 优先从 member_info 直接获取，如果没有则从 custom_config 获取
    max_quota = member_info.get(max_key)
    if max_quota is None:
        # 从 custom_config 中查找
        custom_config = member_info.get("custom_config") or {}
        if isinstance(custom_config, dict):
            max_quota = custom_config.get(max_key, 0)
        else:
            max_quota = 0

    # -1 表示无限制（支持所有配额类型）
    if max_quota == -1:
        return {
            "has_quota": True,
            "reason": "",
            "used": used,
            "max": -1,
            "remaining": -1,
            "required": consume
        }

    if used + consume > max_quota:
        remaining = max_quota - used
        return {
            "has_quota": False,
            "reason": f"{display_name}不足（剩余: {remaining}，需要: {consume}）",
            "used": used,
            "max": max_quota,
            "remaining": remaining,
            "required": consume
        }

    return {
        "has_quota": True,
        "reason": "",
        "used": used,
        "max": max_quota,
        "remaining": max_quota - used,
        "required": consume
    }


def _check_member_package(
    member_info: Dict[str, Any],
    required_package_id: str
) -> Dict[str, Any]:
    """
    检查用户是否拥有指定套餐

    新架构说明：
    - 不再使用等级概念（free < basic < premium < enterprise）
    - 套餐 ID（package_id）是完全自定义的，如：free, vip_month, premium_year
    - 所有权益都在套餐表中配置

    参数：
        member_info: 用户会员信息
        required_package_id: 需要的套餐 ID

    返回：
        has_package: 是否拥有该套餐
    """
    # 检查会员是否有效
    if not member_info.get("is_member_valid", False):
        return {
            "has_package": False,
            "reason": "需要开通会员才能使用此功能"
        }

    current_package_id = member_info.get("member_level", "")

    if not current_package_id:
        return {
            "has_package": False,
            "reason": "未开通会员"
        }

    # 检查是否为指定套餐
    if current_package_id == required_package_id:
        return {
            "has_package": True,
            "reason": "",
            "current_package": current_package_id,
            "required_package": required_package_id
        }

    # 可选：支持检查"及更高等级"套餐
    # 如果 custom_config 中设置了 priority，可以比较优先级
    try:
        current_config = member_info.get("custom_config") or {}
        current_priority = current_config.get("priority", 0)

        # 获取目标套餐信息
        from app.services.member.member_service import member_service
        target_package = member_service.get_package(required_package_id)

        if target_package.get("success"):
            target_config = target_package.get("package", {}).get("custom_config", {})
            target_priority = target_config.get("priority", 0)

            # 如果当前套餐优先级 >= 目标套餐优先级，则通过
            if current_priority >= target_priority and current_priority > 0:
                return {
                    "has_package": True,
                    "reason": "",
                    "current_package": current_package_id,
                    "required_package": required_package_id,
                    "priority_check": True
                }
    except Exception:
        pass

    return {
        "has_package": False,
        "reason": f"此功能需要 {required_package_id} 套餐（当前: {current_package_id}）",
        "current_package": current_package_id,
        "required_package": required_package_id
    }


# 兼容旧版本的函数别名
_check_member_level = _check_member_package


# ============================================================================
# 工具函数
# ============================================================================

def _get_privilege_display_name(privilege_type: str) -> str:
    """
    获取权益类型的中文显示名称

    参数：
        privilege_type: 权益类型（英文）

    返回：
        权益的中文名称，如果未找到则返回原英文名称
    """
    return PRIVILEGE_DISPLAY_NAMES.get(privilege_type, privilege_type)


def _extract_request(args: tuple, kwargs: dict) -> Optional[Request]:
    """从函数参数中提取 Request 对象"""
    if "request" in kwargs:
        return kwargs["request"]

    for arg in args:
        if isinstance(arg, Request):
            return arg

    return None


def _is_admin(request: Request) -> bool:
    """
    检查用户是否为管理员

    管理员可以跳过会员权限检查

    支持的管理员标识：
    - user_type = "admin"
    - role = "admin" 或 "super_admin"
    """
    user_type = getattr(request.state, "user_type", None)
    role = getattr(request.state, "role", None)

    # 检查是否为管理员
    if user_type == "admin":
        return True

    if role in ["admin", "super_admin"]:
        return True

    return False


def _is_admin_user_id(user_id: str) -> bool:
    """
    通过 user_id 检查是否为管理员（备用方法）

    用于某些场景下 request.state 中没有角色信息的情况
    """
    try:
        from app.services.user.user_repository import user_repository
        user = user_repository.get_user_by_id(user_id)
        if not user:
            return False

        user_type = user.get("user_type", "user")
        role = user.get("role", user_type)

        return user_type == "admin" or role in ["admin", "super_admin"]
    except Exception:
        return False


def _format_error_message(
    privilege_errors: List[str] = None,
    quota_errors: List[str] = None,
    level_errors: List[str] = None
) -> str:
    """格式化错误消息"""
    errors = []

    if privilege_errors:
        errors.extend(privilege_errors)
    if quota_errors:
        errors.extend(quota_errors)
    if level_errors:
        errors.extend(level_errors)

    if not errors:
        return "权限检查失败"

    if len(errors) == 1:
        return errors[0]

    return "权限不足：\n" + "\n".join(f"  - {e}" for e in errors)


# ============================================================================
# 装饰器定义
# ============================================================================

def require_member_privilege(
    privilege_type: str,
    auto_record: bool = True,
    on_fail: Literal["error", "return_none"] = "error",
    skip_admin: bool = True
):
    """
    要求指定权益的装饰器（基于套餐配置）

    参数：
        privilege_type: 权益类型
            - 标准权益: rag, web_search, mcp_tools
            - 动态权益: 自动从 custom_config.enable_{privilege_type} 读取
        auto_record: 是否自动记录使用（管理员不记录）
        on_fail: 失败时的处理方式
            - "error": 返回错误响应
            - "return_none": 返回 None（用于可选功能）
        skip_admin: 管理员是否跳过权限检查（默认 True）

    使用示例：
        @router.post("/chat/rag")
        @require_member_privilege("rag")
        async def rag_chat():
            return {"message": "RAG chat enabled"}

    管理员说明：
        管理员（user_type=admin 或 role=admin/super_admin）自动跳过权限检查

    环境变量说明：
        当 ENABLE_MEMBER_PERMISSION=false 时，自动跳过所有权限检查
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = _extract_request(args, kwargs)
            if not request:
                if on_fail == "error":
                    return response.fail(message="无法获取请求上下文", code=500)
                return None

            # 检查全局权限开关
            if not is_member_permission_enabled():
                request.state.permission_disabled = True
                return await func(*args, **kwargs)

            user_id = getattr(request.state, "user_id", None)
            if not user_id:
                if on_fail == "error":
                    return response.fail(message="未授权用户", code=401)
                return None

            # 检查是否为管理员，管理员跳过权限检查，但仍记录使用
            is_admin = False
            if skip_admin and _is_admin(request):
                is_admin = True
                # 标记为管理员访问
                request.state.is_admin_bypass = True
                request.state.admin_privilege_check = {
                    "is_admin": True,
                    "bypassed_privilege": privilege_type,
                    "reason": "管理员跳过权限检查"
                }
                # 注意：不直接返回，继续执行后面的 usage 记录逻辑

            # 获取会员信息（管理员如果没有会员信息，创建一个空的 member_info 用于后续逻辑）
            member_info = _get_user_member_info(user_id)
            if not member_info:
                if is_admin:
                    # 管理员没有会员信息时，创建一个空的 member_info
                    member_info = {
                        "member_level": "admin",
                        "is_member_valid": True,
                        "custom_config": {},
                    }
                else:
                    if on_fail == "error":
                        return response.fail(message="获取会员信息失败", code=500)
                    return None

            # 检查会员是否有效（管理员跳过此检查）
            if not is_admin and not member_info.get("is_member_valid", False):
                if on_fail == "error":
                    return response.fail(
                        message="此功能需要开通会员，请先升级会员",
                        code="MEMBER_REQUIRED"
                    )
                return None

            # 检查权益（管理员跳过权益检查）
            privilege_check = _check_privilege_from_config(member_info, privilege_type)

            if not is_admin and not privilege_check["has_privilege"]:
                if on_fail == "error":
                    return response.fail(
                        message=privilege_check["reason"],
                        code="PRIVILEGE_REQUIRED",
                        data={
                            "privilege_type": privilege_type,
                            "source": privilege_check.get("source")
                        }
                    )
                return None

            # 自动记录使用（管理员也会记录使用）
            if auto_record:
                member_service.record_usage(user_id, privilege_type, 1)

            # 将检查结果存入 request.state
            request.state.member_privilege_check = privilege_check
            request.state.member_info = member_info

            return await func(*args, **kwargs)

        return wrapper
    return decorator


def require_any_member_privilege(
    privilege_types: List[str],
    auto_record: bool = True,
    on_fail: Literal["error", "return_none"] = "error",
    skip_admin: bool = True
):
    """
    要求任一权益的装饰器（OR 逻辑）

    只要满足其中一个权益即可通过

    管理员自动跳过权限检查

    使用示例：
        @router.post("/chat/advanced")
        @require_any_member_privilege(["rag", "web_search"])
        async def advanced_chat():
            return {"message": "Advanced chat enabled"}
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

            # 检查全局权限开关
            if not is_member_permission_enabled():
                request.state.permission_disabled = True
                return await func(*args, **kwargs)

            # 管理员跳过权限检查
            if skip_admin and _is_admin(request):
                request.state.is_admin_bypass = True
                request.state.admin_privilege_check = {
                    "is_admin": True,
                    "bypassed_privileges": privilege_types,
                    "reason": "管理员跳过权限检查"
                }
                return await func(*args, **kwargs)

            # 获取会员信息
            member_info = _get_user_member_info(user_id)
            if not member_info:
                return response.fail(message="获取会员信息失败", code=500)

            # 检查会员是否有效
            if not member_info.get("is_member_valid", False):
                return response.fail(
                    message="此功能需要开通会员，请先升级会员",
                    code="MEMBER_REQUIRED"
                )

            # 检查权益（任一通过即可）
            for privilege_type in privilege_types:
                privilege_check = _check_privilege_from_config(member_info, privilege_type)
                if privilege_check["has_privilege"]:
                    # 自动记录使用
                    if auto_record:
                        member_service.record_usage(user_id, privilege_type, 1)

                    request.state.member_privilege_check = privilege_check
                    request.state.member_info = member_info
                    request.state.granted_privilege = privilege_type

                    return await func(*args, **kwargs)

            # 所有权益都不满足
            # 将权益类型转换为中文显示名称
            display_names = [_get_privilege_display_name(p) for p in privilege_types]
            return response.fail(
                message=f"此功能需要以下任一权益: {', '.join(display_names)}",
                code="PRIVILEGE_REQUIRED",
                data={"required_privileges": privilege_types}
            )

        return wrapper
    return decorator


def require_all_member_privileges(
    privilege_types: List[str],
    auto_record: bool = True,
    on_fail: Literal["error", "return_none"] = "error",
    skip_admin: bool = True
):
    """
    要求所有权益的装饰器（AND 逻辑）

    必须同时满足所有权益才能通过

    管理员自动跳过权限检查

    使用示例：
        @router.post("/chat/full")
        @require_all_member_privileges(["rag", "web_search", "mcp_tools"])
        async def full_chat():
            return {"message": "Full featured chat"}
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

            # 检查全局权限开关
            if not is_member_permission_enabled():
                request.state.permission_disabled = True
                return await func(*args, **kwargs)

            # 管理员跳过权限检查
            if skip_admin and _is_admin(request):
                request.state.is_admin_bypass = True
                request.state.admin_privilege_check = {
                    "is_admin": True,
                    "bypassed_privileges": privilege_types,
                    "reason": "管理员跳过权限检查"
                }
                return await func(*args, **kwargs)

            # 获取会员信息
            member_info = _get_user_member_info(user_id)
            if not member_info:
                return response.fail(message="获取会员信息失败", code=500)

            # 检查会员是否有效
            if not member_info.get("is_member_valid", False):
                return response.fail(
                    message="此功能需要开通会员，请先升级会员",
                    code="MEMBER_REQUIRED"
                )

            # 检查所有权益
            missing_privileges = []
            privilege_checks = {}

            for privilege_type in privilege_types:
                privilege_check = _check_privilege_from_config(member_info, privilege_type)
                privilege_checks[privilege_type] = privilege_check

                if not privilege_check["has_privilege"]:
                    missing_privileges.append(privilege_type)

            if missing_privileges:
                # 将权益类型转换为中文显示名称
                display_names = [_get_privilege_display_name(p) for p in missing_privileges]
                return response.fail(
                    message=f"缺少以下权益: {', '.join(display_names)}",
                    code="PRIVILEGE_REQUIRED",
                    data={
                        "missing_privileges": missing_privileges,
                        "privilege_checks": privilege_checks
                    }
                )

            # 自动记录使用
            if auto_record:
                for privilege_type in privilege_types:
                    member_service.record_usage(user_id, privilege_type, 1)

            request.state.member_privilege_checks = privilege_checks
            request.state.member_info = member_info

            return await func(*args, **kwargs)

        return wrapper
    return decorator


def require_member_quota(
    quota_type: str,
    consume: int = 1,
    on_fail: Literal["error", "return_none"] = "error",
    skip_admin: bool = True,
    auto_record: bool = True
):
    """
    要求配额的装饰器

    管理员自动跳过配额检查

    参数：
        quota_type: 配额类型（daily_chats, kb_count, file_storage_mb 等）
        consume: 消耗配额数量（默认 1）
        on_fail: 失败时的处理方式
        skip_admin: 管理员是否跳过检查（默认 True）
        auto_record: 是否自动记录使用量（默认 True）

    使用示例：
        @router.post("/knowledge/create")
        @require_member_quota("kb_count")
        async def create_knowledge():
            return {"message": "Knowledge created"}

        @router.post("/file/upload")
        @require_member_quota("file_storage_mb", consume=10)
        async def upload_file():
            return {"message": "File uploaded"}

    配额为 -1 时表示无限使用（不限制）

    环境变量说明：
        当 ENABLE_MEMBER_PERMISSION=false 时，自动跳过所有配额检查
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = _extract_request(args, kwargs)
            if not request:
                return response.fail(message="无法获取请求上下文", code=500)

            # 检查全局权限开关
            if not is_member_permission_enabled():
                request.state.permission_disabled = True
                return await func(*args, **kwargs)

            user_id = getattr(request.state, "user_id", None)
            if not user_id:
                return response.fail(message="未授权用户", code=401)

            # 管理员跳过配额检查，但仍记录使用
            is_admin = False
            if skip_admin and _is_admin(request):
                is_admin = True
                request.state.is_admin_bypass = True
                request.state.admin_quota_check = {
                    "is_admin": True,
                    "bypassed_quota": quota_type,
                    "consume": consume,
                    "reason": "管理员跳过配额检查"
                }
                # 注意：不直接返回，继续执行后面的 usage 记录逻辑

            # 获取会员信息（管理员如果没有会员信息，创建一个空的 member_info 用于后续逻辑）
            member_info = _get_user_member_info(user_id)
            if not member_info:
                if is_admin:
                    # 管理员没有会员信息时，创建一个空的 member_info
                    member_info = {
                        "member_level": "admin",
                        "is_member_valid": True,
                        "custom_config": {},
                    }
                else:
                    return response.fail(message="获取会员信息失败", code=500)

            # 检查配额（管理员跳过配额检查）
            quota_check = _check_quota_from_config(member_info, quota_type, consume)

            if not is_admin and not quota_check["has_quota"]:
                if on_fail == "error":
                    return response.fail(
                        message=quota_check["reason"],
                        code="QUOTA_EXCEEDED",
                        data={
                            "quota_type": quota_type,
                            "used": quota_check.get("used"),
                            "max": quota_check.get("max"),
                            "remaining": quota_check.get("remaining"),
                            "required": quota_check.get("required")
                        }
                    )
                return None

            # 自动记录使用量（配额检查通过后，管理员也会记录）
            if auto_record:
                member_service.record_usage(user_id, quota_type, consume)

            # 将检查结果存入 request.state
            request.state.member_quota_check = quota_check
            request.state.member_info = member_info

            return await func(*args, **kwargs)

        return wrapper
    return decorator


def require_member_level(
    package_id: str,
    on_fail: Literal["error", "return_none"] = "error",
    skip_admin: bool = True,
    allow_higher_priority: bool = True
):
    """
    要求指定套餐的装饰器

    新架构说明：
    - 不再使用等级概念（free < basic < premium < enterprise）
    - 套餐 ID（package_id）是完全自定义的，如：free, vip_month, premium_year
    - 所有权益都在套餐表中配置

    参数：
        package_id: 需要的套餐 ID（如：vip_month, premium_year）
            注意：这里的参数名虽然还是叫 package_id，但为了向后兼容，
                 函数名保持为 require_member_level
        on_fail: 失败时的处理方式
        skip_admin: 管理员是否跳过检查
        allow_higher_priority: 是否允许更高优先级的套餐通过
                              （需要套餐在 custom_config 中设置 priority）

    使用示例：
        @router.post("/premium/feature")
        @require_member_level("vip_month")
        async def premium_feature():
            return {"message": "Premium feature"}

        @router.post("/enterprise/feature")
        @require_member_level("enterprise_year")
        async def enterprise_feature():
            return {"message": "Enterprise feature"}

    管理员自动跳过检查

    优先级说明：
    - 如果 allow_higher_priority=True（默认）：
      - 系统会比较套餐的 custom_config.priority
      - 当前套餐优先级 >= 目标套餐优先级即可通过
    - 如果 allow_higher_priority=False：
      - 必须完全匹配套餐 ID
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
            if skip_admin and _is_admin(request):
                request.state.is_admin_bypass = True
                request.state.admin_package_check = {
                    "is_admin": True,
                    "bypassed_package": package_id,
                    "reason": "管理员跳过套餐检查"
                }
                return await func(*args, **kwargs)

            # 获取会员信息
            member_info = _get_user_member_info(user_id)
            if not member_info:
                return response.fail(message="获取会员信息失败", code=500)

            # 检查套餐
            if allow_higher_priority:
                # 使用新的套餐检查函数（支持优先级比较）
                package_check = _check_member_package(member_info, package_id)
            else:
                # 简单的套餐 ID 匹配检查
                current_package_id = member_info.get("member_level", "")
                package_check = {
                    "has_package": current_package_id == package_id,
                    "reason": f"此功能需要 {package_id} 套餐" if current_package_id != package_id else "",
                    "current_package": current_package_id,
                    "required_package": package_id
                }

            if not package_check.get("has_package"):
                if on_fail == "error":
                    return response.fail(
                        message=package_check.get("reason", "权限不足"),
                        code="PACKAGE_REQUIRED",
                        data={
                            "current_package": package_check.get("current_package"),
                            "required_package": package_id
                        }
                    )
                return None

            # 将检查结果存入 request.state
            request.state.member_package_check = package_check
            request.state.member_level_check = package_check  # 兼容旧版本
            request.state.member_info = member_info

            return await func(*args, **kwargs)

        return wrapper
    return decorator


# 套餐检查装饰器的别名（更直观的命名）
require_member_package = require_member_level


def require_member_features(
    privileges: Optional[List[str]] = None,
    quotas: Optional[Dict[str, int]] = None,
    min_package: Optional[str] = None,
    auto_record: bool = True,
    on_fail: Literal["error", "return_none"] = "error",
    skip_admin: bool = True
):
    """
    组合功能检查装饰器（推荐使用）

    可以同时检查多个权益、配额、套餐要求

    管理员自动跳过所有权限检查

    参数：
        privileges: 权益列表（AND 逻辑，需同时满足）
        quotas: 配额字典 {"quota_type": consume_amount}
        min_package: 最低套餐 ID（如：vip_month）
                      如果套餐设置了 custom_config.priority，
                      则支持优先级比较（当前优先级 >= 目标优先级）
        auto_record: 是否自动记录使用
        on_fail: 失败处理方式
        skip_admin: 管理员是否跳过权限检查

    使用示例：
        @router.post("/advanced/feature")
        @require_member_features(
            privileges=["rag", "web_search"],
            quotas={"kb_count": 1},
            min_package="vip_month"
        )
        async def advanced_feature():
            return {"message": "Access granted"}

    优先级说明：
    - 如果套餐设置了 custom_config.priority：
      - 系统会比较优先级
      - 当前套餐优先级 >= 目标套餐优先级即可通过
    - 如果未设置 priority：
      - 必须完全匹配套餐 ID
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

            # 检查全局权限开关
            if not is_member_permission_enabled():
                request.state.permission_disabled = True
                return await func(*args, **kwargs)

            # 管理员跳过所有权限检查，但仍记录使用
            is_admin = False
            if skip_admin and _is_admin(request):
                is_admin = True
                request.state.is_admin_bypass = True
                request.state.admin_features_check = {
                    "is_admin": True,
                    "bypassed_privileges": privileges or [],
                    "bypassed_quotas": list(quotas.keys()) if quotas else [],
                    "bypassed_package": min_package,
                    "reason": "管理员跳过所有权限检查"
                }
                # 注意：不直接返回，继续执行后面的 usage 记录逻辑

            # 获取会员信息（管理员如果没有会员信息，创建一个空的 member_info 用于后续逻辑）
            member_info = _get_user_member_info(user_id)
            if not member_info:
                if is_admin:
                    # 管理员没有会员信息时，创建一个空的 member_info
                    member_info = {
                        "member_level": "admin",
                        "is_member_valid": True,
                        "custom_config": {},
                    }
                else:
                    return response.fail(message="获取会员信息失败", code=500)

            # 收集所有错误（管理员跳过所有错误检查）
            privilege_errors = []
            quota_errors = []
            package_errors = []
            privilege_checks = {}
            quota_checks = {}
            package_check = None

            # 非管理员才进行权益/配额/套餐检查
            if not is_admin:
                # 检查权益
                if privileges:
                    for privilege_type in privileges:
                        check = _check_privilege_from_config(member_info, privilege_type)
                        privilege_checks[privilege_type] = check
                        if not check["has_privilege"]:
                            privilege_errors.append(check["reason"])

                # 检查配额
                if quotas:
                    for quota_type, consume in quotas.items():
                        check = _check_quota_from_config(member_info, quota_type, consume)
                        quota_checks[quota_type] = check
                        if not check["has_quota"]:
                            quota_errors.append(check["reason"])

                # 检查套餐
                if min_package:
                    package_check = _check_member_package(member_info, min_package)
                    if not package_check.get("has_package"):
                        package_errors.append(package_check["reason"])

            # 如果有错误，返回
            if privilege_errors or quota_errors or package_errors:

                if on_fail == "error":
                    # 组合错误消息
                    all_errors = privilege_errors + quota_errors + package_errors
                    error_message = all_errors[0] if all_errors else "权限不足"

                    return response.fail(
                        message=error_message,
                        code="PERMISSION_DENIED",
                        data={
                            "privilege_checks": privilege_checks if privileges else {},
                            "quota_checks": quota_checks if quotas else {},
                            "package_check": package_check
                        }
                    )
                return None

            # 自动记录使用（管理员也会记录使用）
            if auto_record:
                # 记录权益使用
                if privileges:
                    for privilege_type in privileges:
                        member_service.record_usage(user_id, privilege_type, 1)
                # 记录配额使用
                if quotas:
                    for quota_type, consume in quotas.items():
                        member_service.record_usage(user_id, quota_type, consume)

            # 将检查结果存入 request.state
            request.state.member_privilege_checks = privilege_checks
            request.state.member_quota_checks = quota_checks
            request.state.member_package_check = package_check
            request.state.member_level_check = package_check  # 兼容旧版本
            request.state.member_info = member_info

            return await func(*args, **kwargs)

        return wrapper
    return decorator


# ============================================================================
# 辅助函数：获取当前用户会员信息（在路由中使用）
# ============================================================================

def get_current_member_privileges(request: Request) -> Optional[Dict[str, Any]]:
    """
    从 request.state 获取当前用户的会员信息

    使用示例：
        @router.get("/api/my-privileges")
        async def get_my_privileges(request: Request):
            member_info = get_current_member_privileges(request)
            if not member_info:
                return response.fail(message="未获取到会员信息")

            return response.success(data={
                "member_level": member_info.get("member_level"),
                "enable_rag": member_info.get("enable_rag"),
                "max_daily_chats": member_info.get("max_daily_chats"),
                ...
            })
    """
    return getattr(request.state, "member_info", None)


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    # 装饰器
    "require_member_privilege",
    "require_any_member_privilege",
    "require_all_member_privileges",
    "require_member_quota",
    "require_member_level",  # 改为检查套餐 ID
    "require_member_package",  # 套餐检查的别名（更直观）
    "require_member_features",
    # 辅助函数
    "get_current_member_privileges",
    "clear_member_cache",
    "is_admin_user",  # 检查是否为管理员用户
    # 常量
    "STANDARD_PRIVILEGE_FIELDS",
    "QUOTA_FIELDS",
]


# ============================================================================
# 公开的管理员检查函数（供外部使用）
# ============================================================================

def is_admin_user(request: Request) -> bool:
    """
    检查当前请求用户是否为管理员

    使用场景：
    - 在业务逻辑中判断用户是否为管理员
    - 管理员可以跳过某些限制

    使用示例：
        @router.get("/api/some-endpoint")
        async def some_endpoint(request: Request):
            from app.middleware.member_permission import is_admin_user

            if is_admin_user(request):
                return {"message": "管理员访问"}
            else:
                return {"message": "普通用户访问"}
    """
    return _is_admin(request)
