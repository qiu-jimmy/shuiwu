"""
会员权限装饰器使用示例
======================
展示如何在实际项目中使用会员权限认证系统

运行示例：
    # 将此路由注册到 main.py 即可测试
    from app.api.member_permission_examples import router as member_examples_router
    app.include_router(member_examples_router, prefix="/api/examples", tags=["会员权限示例"])
"""
from fastapi import APIRouter, Request, Depends
from app.middleware.member_permission import (
    require_member_privilege,
    require_any_member_privilege,
    require_all_member_privileges,
    require_member_quota,
    require_member_level,
    require_member_features,
    get_current_member_privileges,
)
from app.utils.response import response

router = APIRouter()


# ============================================================================
# 示例 0: 管理员跳过权限检查
# ============================================================================

@router.get("/example/admin-bypass")
@require_member_privilege("rag")
async def example_admin_bypass(request: Request):
    """
    管理员跳过权限检查示例

    说明：
    - 管理员（user_type=admin 或 role=admin/super_admin）自动跳过所有权限检查
    - 普通用户需要有 rag 权益才能访问

    管理员标识：
    - user_type = "admin"
    - role = "admin" 或 "super_admin"
    """
    # 检查是否为管理员访问
    is_admin_bypass = getattr(request.state, "is_admin_bypass", False)
    admin_check = getattr(request.state, "admin_privilege_check", None)

    if is_admin_bypass:
        return response.success(
            data={
                "message": "管理员访问：已跳过权限检查",
                "admin_info": admin_check,
                "note": "管理员可以访问所有功能，无需会员权限"
            }
        )

    # 普通用户访问
    member_info = get_current_member_privileges(request)
    privilege_check = getattr(request.state, "member_privilege_check", {})

    return response.success(
        data={
            "message": "RAG 功能已启用（普通用户）",
            "member_level": member_info.get("member_level") if member_info else None,
            "privilege_check": privilege_check
        }
    )


@router.get("/example/admin-check")
async def example_admin_check(request: Request):
    """
    检查当前用户是否为管理员

    使用场景：
    - 在业务逻辑中判断是否给予管理员特殊权限
    - 返回不同的数据或功能
    """
    from app.middleware.member_permission import is_admin_user

    is_admin = is_admin_user(request)

    user_id = getattr(request.state, "user_id", None)
    user_type = getattr(request.state, "user_type", None)
    role = getattr(request.state, "role", None)

    return response.success(
        data={
            "user_id": user_id,
            "is_admin": is_admin,
            "user_type": user_type,
            "role": role,
            "message": "管理员用户" if is_admin else "普通用户"
        }
    )


# ============================================================================
# 示例 1: 单个权益检查
# ============================================================================

@router.post("/example/rag-chat")
@require_member_privilege("rag")
async def example_rag_chat(request: Request):
    """
    RAG 聊天功能 - 需要 rag 权益

    权限检查流程：
    1. 从 JWT 获取 user_id
    2. 检查是否为管理员（管理员自动跳过）
    3. 查询用户会员套餐配置
    4. 检查套餐中 enable_rag 字段
    5. 如果为 True，通过验证并自动记录使用

    数据库对应：
    - member_packages.enable_rag = true
    - 或 custom_config = {"enable_rag": true}

    管理员：
    - 管理员自动跳过所有权限检查
    """
    # 检查是否为管理员访问
    is_admin_bypass = getattr(request.state, "is_admin_bypass", False)

    if is_admin_bypass:
        return response.success(
            data={
                "message": "管理员访问：已跳过 RAG 权限检查",
                "note": "管理员可以直接使用所有功能"
            }
        )

    # 普通用户访问
    member_info = get_current_member_privileges(request)
    return response.success(
        data={
            "message": "RAG 聊天功能已启用",
            "member_level": member_info.get("member_level"),
            "enable_rag": member_info.get("enable_rag")
        }
    )


@router.post("/example/web-search")
@require_member_privilege("web_search")
async def example_web_search(request: Request):
    """
    网络搜索功能 - 需要 web_search 权益

    数据库对应：
    - member_packages.enable_web_search = true
    """
    member_info = get_current_member_privileges(request)
    return response.success(
        data={
            "message": "网络搜索功能已启用",
            "enable_web_search": member_info.get("enable_web_search")
        }
    )


# ============================================================================
# 示例 2: OR 逻辑 - 满足任一权益即可
# ============================================================================

@router.post("/example/advanced-chat-or")
@require_any_member_privilege(["rag", "web_search"])
async def example_advanced_chat_or(request: Request):
    """
    高级聊天（OR）- 有 RAG 或网络搜索任一权限即可

    使用场景：
    - 用户只要有 RAG 权限，就可以使用
    - 或者只要有网络搜索权限，也可以使用
    - 两个都有也没关系

    数据库对应：
    - member_packages.enable_rag = true
    - 或 member_packages.enable_web_search = true
    """
    member_info = get_current_member_privileges(request)
    granted_privilege = getattr(request.state, "granted_privilege", "unknown")

    return response.success(
        data={
            "message": f"使用 {granted_privilege} 权限访问高级聊天",
            "granted_privilege": granted_privilege
        }
    )


# ============================================================================
# 示例 3: AND 逻辑 - 需要同时满足所有权益
# ============================================================================

@router.post("/example/advanced-chat-and")
@require_all_member_privileges(["rag", "web_search"])
async def example_advanced_chat_and(request: Request):
    """
    高级聊天（AND）- 需要同时有 RAG 和网络搜索权限

    使用场景：
    - 用户必须同时拥有 RAG 和网络搜索权限
    - 适合需要多种功能组合的高级场景

    数据库对应：
    - member_packages.enable_rag = true
    - 且 member_packages.enable_web_search = true
    """
    member_info = get_current_member_privileges(request)
    checks = getattr(request.state, "member_privilege_checks", {})

    return response.success(
        data={
            "message": "已同时启用 RAG 和网络搜索",
            "privilege_checks": checks
        }
    )


# ============================================================================
# 示例 4: 配额检查
# ============================================================================

@router.post("/example/create-knowledge")
@require_member_quota("kb_count", consume=1)
async def example_create_knowledge(request: Request):
    """
    创建知识库 - 需要消耗 1 个知识库配额

    权限检查：
    1. 检查用户当前知识库数量
    2. 对比套餐的 max_kb_count 限制
    3. 如果未达上限，允许创建

    数据库对应：
    - member_packages.max_kb_count = 10

    错误示例：
    - 当前有 10 个知识库，套餐限制 10 个
    - 返回：知识库数量不足（剩余: 0，需要: 1）
    """
    quota_check = getattr(request.state, "member_quota_check", {})
    member_info = get_current_member_privileges(request)

    return response.success(
        data={
            "message": "知识库创建成功",
            "kb_count": member_info.get("kb_count"),
            "max_kb_count": member_info.get("max_kb_count"),
            "remaining": quota_check.get("remaining")
        }
    )


@router.post("/example/upload-large-file")
@require_member_quota("file_storage_mb", consume=50)
async def example_upload_large_file(request: Request):
    """
    上传大文件 - 需要消耗 50MB 存储空间

    数据库对应：
    - member_packages.max_file_storage_mb = 1024

    检查逻辑：
    - 当前已用 800MB，套餐限制 1024MB
    - 剩余 224MB，需要 50MB
    - 通过验证 ✅
    """
    quota_check = getattr(request.state, "member_quota_check", {})

    return response.success(
        data={
            "message": "文件上传成功",
            "used_storage_mb": quota_check.get("used"),
            "max_file_storage_mb": quota_check.get("max"),
            "remaining_mb": quota_check.get("remaining")
        }
    )


# ============================================================================
# 示例 5: 会员等级检查
# ============================================================================

@router.post("/example/premium-feature")
@require_member_level("vip_month")
async def example_premium_feature(request: Request):
    """
    VIP 月卡专属功能 - 需要 vip_month 套餐

    新架构说明：
    - 不再使用等级概念（free < basic < premium < enterprise）
    - 直接检查套餐 ID（package_id）
    - 如果套餐设置了 custom_config.priority，则支持优先级比较

    数据库对应：
    - users.member_level = "vip_month"
    - 或 member_level = "premium_year"（如果 priority 更高）

    优先级配置：
    在 member_packages 表的 custom_config 中设置：
    {
        "priority": 1  // 数字越大，等级越高
    }

    系统会比较优先级：
    - 当前套餐 priority >= 目标套餐 priority → 通过
    """
    package_check = getattr(request.state, "member_package_check", {})
    member_info = get_current_member_privileges(request)

    return response.success(
        data={
            "message": "欢迎 VIP 会员",
            "current_package": member_info.get("member_level") if member_info else None,
            "required_package": "vip_month",
            "priority_check": package_check.get("priority_check", False)
        }
    )


# ============================================================================
# 示例 6: 组合检查（推荐）- 同时检查多个条件
# ============================================================================

@router.post("/example/enterprise-feature")
@require_member_features(
    privileges=["rag", "web_search", "mcp_tools"],
    quotas={"kb_count": 1, "daily_chats": 1},
    min_package="vip_month"
)
async def example_enterprise_feature(request: Request):
    """
    企业级功能 - 综合权限检查

    要求：
    1. 权益：RAG、网络搜索、MCP 工具（同时满足）
    2. 配额：至少 1 个知识库、1 次每日对话
    3. 套餐：vip_month 或更高优先级的套餐

    数据库对应：
    - member_packages:
      - enable_rag = true
      - enable_web_search = true
      - enable_mcp_tools = true
      - max_kb_count = 10
      - max_daily_chats = -1 (无限制)
    - custom_config = {"priority": 1}

    错误场景示例：
    - 缺少 MCP 工具权限 → 返回详细错误
    - 知识库已满 → 返回配额不足
    - 套餐不够 → 返回需要升级套餐

    优先级说明：
    如果套餐 A 的 priority=1，套餐 B 的 priority=2
    要求 min_package="vip_month"（priority=1）
    - 用户有套餐 A → 通过
    - 用户有套餐 B → 通过（priority 2 >= 1）
    """
    privilege_checks = getattr(request.state, "member_privilege_checks", {})
    quota_checks = getattr(request.state, "member_quota_checks", {})
    package_check = getattr(request.state, "member_package_check", {})

    return response.success(
        data={
            "message": "所有权限检查通过",
            "privilege_checks": privilege_checks,
            "quota_checks": quota_checks,
            "package_check": package_check
        }
    )


# ============================================================================
# 示例 7: 可选功能 - 权限不足时返回 None 而非错误
# ============================================================================

@router.get("/example/optional-feature")
@require_member_privilege("advanced_analytics", on_fail="return_none")
async def example_optional_feature(request: Request):
    """
    可选功能 - 高级分析

    如果用户有权限，返回高级分析数据
    如果用户无权限，返回 None（不报错）

    使用场景：
    - 功能性增强，非核心功能
    - 根据权限动态调整 UI
    """
    member_info = get_current_member_privileges(request)
    privilege_check = getattr(request.state, "member_privilege_check", {})

    if not privilege_check.get("has_privilege"):
        # 返回基础版本
        return response.success(
            data={
                "message": "基础功能",
                "has_advanced": False,
                "data": "基础分析数据..."
            }
        )

    # 返回高级版本
    return response.success(
        data={
            "message": "高级功能",
            "has_advanced": True,
            "data": "高级分析数据（包含更多维度）..."
        }
    )


# ============================================================================
# 示例 8: 自定义权限（custom_config）
# ============================================================================

@router.post("/example/custom-feature")
@require_member_privilege("team_collaboration")
async def example_custom_feature(request: Request):
    """
    自定义权限功能 - 团队协作

    此权限不是标准字段，而是通过 custom_config 定义：

    在数据库中配置：
    UPDATE business.member_packages
    SET custom_config = '{"enable_team_collaboration": true, "max_team_members": 10}'
    WHERE package_id = 'enterprise';

    装饰器会自动：
    1. 检查 custom_config.enable_team_collaboration
    2. 如果为 true，通过验证

    扩展性：
    - 无需修改代码即可添加新权限
    - 只需在数据库的 custom_config 中添加配置
    """
    member_info = get_current_member_privileges(request)
    custom_config = member_info.get("custom_config", {})

    return response.success(
        data={
            "message": "团队协作功能已启用",
            "team_config": {
                "max_team_members": custom_config.get("max_team_members", 0)
            }
        }
    )


# ============================================================================
# 示例 9: 查询当前用户的所有会员权益
# ============================================================================

@router.get("/example/my-privileges")
async def example_get_my_privileges(request: Request):
    """
    获取当前用户的所有会员权益

    返回：
    - 会员等级和到期时间
    - 所有可用的功能权益
    - 配额使用情况
    """
    from app.services.member.member_service import member_service

    # 从 JWT 获取 user_id
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        return response.fail(message="未授权", code=401)

    # 获取完整的会员信息
    member_info = member_service.get_member_stats(user_id)

    if not member_info.get("success"):
        return response.fail(message="获取会员信息失败")

    data = member_info.copy()

    # 添加权限状态说明
    data["privileges_summary"] = {
        "rag_enabled": data.get("enable_rag", False),
        "web_search_enabled": data.get("enable_web_search", False),
        "mcp_tools_enabled": data.get("enable_mcp_tools", False),
        "unlimited_chats": data.get("max_daily_chats") == -1,
    }

    return response.success(data=data)


# ============================================================================
# 示例 10: 实际业务场景 - 知识库管理
# ============================================================================

@router.post("/example/knowledge/create-full")
@require_member_features(
    privileges=["rag"],
    quotas={"kb_count": 1}
)
async def example_create_knowledge_full(request: Request, name: str, description: str = ""):
    """
    完整的知识库创建流程

    权限要求：
    1. 需要 RAG 功能
    2. 至少剩余 1 个知识库配额

    验证通过后：
    1. 执行实际的知识库创建逻辑
    2. 返回创建结果

    新架构：不再要求特定会员等级，只检查权益和配额
    """
    # 这里调用实际的知识库创建服务
    # from app.services.knowledge.knowledge_service import knowledge_service
    # result = knowledge_service.create_knowledge(user_id, name, description)

    return response.success(
        data={
            "message": "知识库创建成功",
            "knowledge": {
                "kb_id": "kb_123",
                "name": name,
                "description": description,
                "created_at": "2025-01-20T10:00:00Z"
            }
        }
    )


# ============================================================================
# 辅助接口：测试不同套餐的权限
# ============================================================================

@router.get("/example/privileges-by-package/{package_id}")
async def example_get_privileges_by_package(package_id: str):
    """
    查看指定套餐的权益配置（用于测试）

    使用示例：
    GET /api/examples/privileges-by-package/vip_month
    GET /api/examples/privileges-by-package/free
    """
    from app.services.member.member_service import member_service

    package_result = member_service.get_package(package_id)

    if not package_result.get("success"):
        return response.fail(message="套餐不存在")

    package = package_result.get("package", {})

    return response.success(
        data={
            "package_id": package.get("package_id"),
            "name": package.get("name"),
            "privileges": {
                "rag": package.get("enable_rag"),
                "web_search": package.get("enable_web_search"),
                "mcp_tools": package.get("enable_mcp_tools"),
            },
            "quotas": {
                "daily_chats": package.get("max_daily_chats"),
                "kb_count": package.get("max_kb_count"),
                "kb_documents": package.get("max_kb_documents"),
                "file_storage_mb": package.get("max_file_storage_mb"),
                "file_count": package.get("max_file_count"),
            },
            "custom_config": package.get("custom_config", {}),
            "benefits": package.get("benefits", [])
        }
    )


@router.post("/example/simulate-package")
async def example_simulate_package(
    request: Request,
    package_id: str,
    expire_days: int = 365
):
    """
    测试辅助接口：模拟当前用户使用指定套餐（仅用于测试）

    **使用示例：**
    POST /api/examples/simulate-package?package_id=vip_month
    POST /api/examples/simulate-package?package_id=premium_year
    POST /api/examples/simulate-package?package_id=enterprise_year

    **注意事项：**
    - 此接口仅用于测试环境
    - 会真正修改数据库中的用户套餐
    - 需要登录认证
    """
    from app.services.member.member_service import member_service
    from datetime import datetime, timedelta

    # 获取当前用户 ID
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        return response.fail(message="未登录或 token 无效")

    try:
        # 使用同步数据库连接更新用户套餐
        from app.infra.db import SyncSessionLocal

        with SyncSessionLocal() as db:
            from app.models.user import User

            # 查询用户
            user = db.query(User).filter(User.user_id == user_id).first()
            if not user:
                return response.fail(message="用户不存在")

            # 更新用户套餐
            user.member_level = package_id
            user.member_expire_at = datetime.now() + timedelta(days=expire_days)
            db.commit()

        return response.success(
            message=f"已更新套餐: {package_id}，有效期 {expire_days} 天",
            data={
                "user_id": user_id,
                "member_level": package_id,
                "member_expire_at": (datetime.now() + timedelta(days=expire_days)).isoformat()
            }
        )

    except Exception as e:
        return response.fail(message=f"更新套餐失败: {str(e)}")


@router.post("/example/reset-package")
async def example_reset_package(request: Request):
    """
    测试辅助接口：重置当前用户为免费套餐（仅用于测试）

    **使用示例：**
    POST /api/examples/reset-package

    **注意事项：**
    - 此接口仅用于测试环境
    - 会真正修改数据库中的用户套餐
    - 需要登录认证
    """
    from app.infra.db import SyncSessionLocal
    from app.models.user import User

    # 获取当前用户 ID
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        return response.fail(message="未登录或 token 无效")

    try:
        # 使用同步数据库连接更新用户套餐
        with SyncSessionLocal() as db:
            # 查询用户
            user = db.query(User).filter(User.user_id == user_id).first()
            if not user:
                return response.fail(message="用户不存在")

            # 重置为免费套餐
            user.member_level = "free"
            user.member_expire_at = None
            db.commit()

        return response.success(
            message="已重置为免费套餐",
            data={
                "user_id": user_id,
                "member_level": "free"
            }
        )

    except Exception as e:
        return response.fail(message=f"重置套餐失败: {str(e)}")
