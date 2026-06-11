"""
会员套餐权限配置管理 API
========================
提供套餐配置的管理接口，包括：
1. 查看所有可用权限类型
2. 生成套餐配置 SQL
3. 验证配置格式
4. 批量更新套餐

使用场景：
- 管理员配置套餐权益
- 开发者快速生成配置 SQL
- 运营人员调整套餐参数

访问地址：/api/package-config/*
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.services.member.package_config_helper import (
    PackageConfigBuilder,
    create_free_package,
    create_basic_month_package,
    create_premium_month_package,
    create_enterprise_year_package,
    get_all_privilege_types,
    validate_custom_config,
    generate_batch_sql,
    STANDARD_PRIVILEGES,
    STANDARD_QUOTAS,
    CUSTOM_PRIVILEGES_EXAMPLES,
)
from app.utils.response import response

router = APIRouter()


# ============================================================================
# 请求/响应模型
# ============================================================================

class CustomConfigRequest(BaseModel):
    """自定义配置请求"""
    package_id: str = Field(..., description="套餐ID")
    custom_config: Dict[str, Any] = Field(..., description="自定义配置")


class PackageConfigRequest(BaseModel):
    """套餐配置请求"""
    package_id: str = Field(..., description="套餐ID")
    name: str = Field(..., description="套餐名称")
    description: Optional[str] = Field(None, description="套餐描述")
    package_type: str = Field("month", description="套餐类型: month, quarter, year, lifetime")
    price: float = Field(..., description="价格")
    original_price: Optional[float] = Field(None, description="原价")
    duration_days: Optional[int] = Field(None, description="有效天数")
    # 权益
    enable_rag: bool = Field(True, description="启用RAG")
    enable_web_search: bool = Field(False, description="启用网络搜索")
    enable_mcp_tools: bool = Field(False, description="启用MCP工具")
    # 新增权益（财税服务）
    enable_invoice_penetration: bool = Field(False, description="启用发票穿透")
    enable_panorama: bool = Field(False, description="启用全景报告")
    enable_business_risk: bool = Field(False, description="启用经营风险")
    # 配额
    max_daily_chats: int = Field(-1, description="每日聊天次数(-1为无限制)")
    max_kb_count: int = Field(5, description="知识库数量")
    max_kb_documents: int = Field(100, description="知识库文档数")
    max_file_storage_mb: int = Field(1024, description="文件存储MB")
    max_file_count: int = Field(100, description="文件数量")
    # 新增配额（按次计费）
    max_invoice_penetration: int = Field(0, description="发票穿透次数(-1为无限制)")
    max_panorama: int = Field(0, description="全景报告次数(-1为无限制)")
    max_business_risk: int = Field(0, description="经营风险查询次数(-1为无限制)")
    # 扩展
    custom_config: Dict[str, Any] = Field(default_factory=dict, description="自定义配置")
    benefits: List[Dict[str, str]] = Field(default_factory=list, description="权益描述")


class BatchUpdateRequest(BaseModel):
    """批量更新请求"""
    packages: List[PackageConfigRequest] = Field(..., description="套餐配置列表")


# ============================================================================
# 查询接口
# ============================================================================

@router.get("/privilege-types")
async def get_privilege_types():
    """
    获取所有可用的权限类型

    返回：
    - 标准权益：rag, web_search, mcp_tools
    - 自定义权益示例：advanced_analytics, team_collaboration 等
    - 配额类型：daily_chats, kb_count, kb_documents 等
    """
    return response.success(
        data={
            "standard_privileges": STANDARD_PRIVILEGES,
            "custom_privileges": CUSTOM_PRIVILEGES_EXAMPLES,
            "quotas": STANDARD_QUOTAS
        }
    )


@router.get("/templates")
async def get_package_templates():
    """
    获取套餐配置模板

    返回预设的套餐配置模板：
    - free: 免费版
    - basic_month: 基础月卡
    - premium_month: 高级月卡
    - enterprise_year: 企业年卡
    """
    templates = {
        "free": create_free_package().build(),
        "basic_month": create_basic_month_package().build(),
        "premium_month": create_premium_month_package().build(),
        "enterprise_year": create_enterprise_year_package().build(),
    }

    # 移除 JSON 序列化问题
    for template in templates.values():
        if "benefits" not in template or template["benefits"] is None:
            template["benefits"] = []
        if "custom_config" not in template or template["custom_config"] is None:
            template["custom_config"] = {}

    return response.success(data={"templates": templates})


@router.get("/template/{template_name}")
async def get_package_template(template_name: str):
    """
    获取指定套餐模板

    参数：
        template_name: 模板名称 (free, basic_month, premium_month, enterprise_year)
    """
    templates = {
        "free": create_free_package,
        "basic_month": create_basic_month_package,
        "premium_month": create_premium_month_package,
        "enterprise_year": create_enterprise_year_package,
    }

    if template_name not in templates:
        return response.fail(message=f"模板不存在: {template_name}")

    builder = templates[template_name]()
    config = builder.build()

    if config.get("benefits") is None:
        config["benefits"] = []
    if config.get("custom_config") is None:
        config["custom_config"] = {}

    return response.success(data={"template": config})


# ============================================================================
# 配置生成接口
# ============================================================================

@router.post("/generate-sql")
async def generate_package_sql(request: PackageConfigRequest):
    """
    生成套餐配置的 SQL 语句

    请求体包含完整的套餐配置，返回对应的 INSERT/UPDATE SQL
    """
    try:
        builder = (
            PackageConfigBuilder(request.package_id, request.name)
            .set_description(request.description or "")
            .set_pricing(
                price=request.price,
                package_type=request.package_type,
                duration_days=request.duration_days,
                original_price=request.original_price
            )
        )

        # 设置权益
        if request.enable_rag:
            builder.enable_privilege("rag")
        else:
            builder.disable_privilege("rag")

        if request.enable_web_search:
            builder.enable_privilege("web_search")
        else:
            builder.disable_privilege("web_search")

        if request.enable_mcp_tools:
            builder.enable_privilege("mcp_tools")
        else:
            builder.disable_privilege("mcp_tools")

        # 设置新增权益（写入 custom_config）
        custom_config_updates = {}
        if request.enable_invoice_penetration:
            custom_config_updates["enable_invoice_penetration"] = True
        if request.enable_panorama:
            custom_config_updates["enable_panorama"] = True
        if request.enable_business_risk:
            custom_config_updates["enable_business_risk"] = True

        # 设置配额
        builder.set_quota("daily_chats", request.max_daily_chats)
        builder.set_quota("kb_count", request.max_kb_count)
        builder.set_quota("kb_documents", request.max_kb_documents)
        builder.set_quota("file_storage_mb", request.max_file_storage_mb)
        builder.set_quota("file_count", request.max_file_count)

        # 设置新增配额（写入 custom_config）
        if request.max_invoice_penetration != 0:
            custom_config_updates["max_invoice_penetration"] = request.max_invoice_penetration
        if request.max_panorama != 0:
            custom_config_updates["max_panorama"] = request.max_panorama
        if request.max_business_risk != 0:
            custom_config_updates["max_business_risk"] = request.max_business_risk

        # 合并自定义配置
        if custom_config_updates:
            merged_config = {**request.custom_config, **custom_config_updates}
            builder.set_custom_config(merged_config)
        elif request.custom_config:
            builder.set_custom_config(request.custom_config)

        # 添加权益描述
        for benefit in request.benefits:
            builder.add_benefit(benefit.get("title", ""), benefit.get("desc", ""))

        # 生成 SQL
        sql = builder.generate_sql()

        return response.success(
            data={
                "sql": sql.strip(),
                "config": builder.build()
            }
        )

    except Exception as e:
        return response.fail(message=f"生成 SQL 失败: {str(e)}")


@router.post("/generate-batch-sql")
async def generate_batch_package_sql(request: BatchUpdateRequest):
    """
    批量生成套餐配置的 SQL 语句

    请求体包含多个套餐配置，返回对应的批量 INSERT/UPDATE SQL
    """
    try:
        configs = []
        for pkg_request in request.packages:
            builder = (
                PackageConfigBuilder(pkg_request.package_id, pkg_request.name)
                .set_description(pkg_request.description or "")
                .set_pricing(
                    price=pkg_request.price,
                    package_type=pkg_request.package_type,
                    duration_days=pkg_request.duration_days,
                    original_price=pkg_request.original_price
                )
            )

            # 设置权益
            if pkg_request.enable_rag:
                builder.enable_privilege("rag")
            else:
                builder.disable_privilege("rag")

            if pkg_request.enable_web_search:
                builder.enable_privilege("web_search")
            else:
                builder.disable_privilege("web_search")

            if pkg_request.enable_mcp_tools:
                builder.enable_privilege("mcp_tools")
            else:
                builder.disable_privilege("mcp_tools")

            # 设置新增权益（写入 custom_config）
            custom_config_updates = {}
            if pkg_request.enable_invoice_penetration:
                custom_config_updates["enable_invoice_penetration"] = True
            if pkg_request.enable_panorama:
                custom_config_updates["enable_panorama"] = True
            if pkg_request.enable_business_risk:
                custom_config_updates["enable_business_risk"] = True

            # 设置配额
            builder.set_quota("daily_chats", pkg_request.max_daily_chats)
            builder.set_quota("kb_count", pkg_request.max_kb_count)
            builder.set_quota("kb_documents", pkg_request.max_kb_documents)
            builder.set_quota("file_storage_mb", pkg_request.max_file_storage_mb)
            builder.set_quota("file_count", pkg_request.max_file_count)

            # 设置新增配额（写入 custom_config）
            if pkg_request.max_invoice_penetration != 0:
                custom_config_updates["max_invoice_penetration"] = pkg_request.max_invoice_penetration
            if pkg_request.max_panorama != 0:
                custom_config_updates["max_panorama"] = pkg_request.max_panorama
            if pkg_request.max_business_risk != 0:
                custom_config_updates["max_business_risk"] = pkg_request.max_business_risk

            # 合并自定义配置
            if custom_config_updates:
                merged_config = {**pkg_request.custom_config, **custom_config_updates}
                builder.set_custom_config(merged_config)
            elif pkg_request.custom_config:
                builder.set_custom_config(pkg_request.custom_config)

            # 添加权益描述
            for benefit in pkg_request.benefits:
                builder.add_benefit(benefit.get("title", ""), benefit.get("desc", ""))

            configs.append(builder.build())

        # 生成 SQL
        sql = generate_batch_sql(configs)

        return response.success(
            data={
                "sql": sql.strip(),
                "count": len(configs)
            }
        )

    except Exception as e:
        return response.fail(message=f"生成批量 SQL 失败: {str(e)}")


# ============================================================================
# 配置验证接口
# ============================================================================

@router.post("/validate-config")
async def validate_custom_config_endpoint(request: CustomConfigRequest):
    """
    验证 custom_config 配置格式

    检查：
    - 是否为有效的 JSON 对象
    - enable_* 字段是否为布尔值
    - 是否与标准字段重复
    """
    result = validate_custom_config(request.custom_config)

    if result["valid"]:
        return response.success(
            data={
                "valid": True,
                "warnings": result.get("warnings", [])
            }
        )
    else:
        return response.fail(
            message="配置验证失败",
            data={
                "errors": result.get("errors", []),
                "warnings": result.get("warnings", [])
            }
        )


# ============================================================================
# 快速配置接口
# ============================================================================

@router.post("/quick-enable-privilege")
async def quick_enable_privilege(request: CustomConfigRequest):
    """
    快速为套餐启用自定义权益

    在 custom_config 中添加 enable_{privilege} = true

    示例：
    {
        "package_id": "premium_month",
        "custom_config": {
            "enable_advanced_analytics": true,
            "enable_team_collaboration": true
        }
    }
    """
    try:
        # 获取现有套餐
        from app.services.member.member_service import member_service
        package_result = member_service.get_package(request.package_id)

        if not package_result.get("success"):
            return response.fail(message="套餐不存在")

        package = package_result.get("package", {})
        existing_config = package.get("custom_config", {})

        # 合并配置
        merged_config = {**existing_config, **request.custom_config}

        # 更新套餐
        update_result = member_service.update_package(
            request.package_id,
            {"custom_config": merged_config}
        )

        if update_result.get("success"):
            return response.success(
                data={
                    "message": "权益启用成功",
                    "custom_config": merged_config
                }
            )
        else:
            return response.fail(message="更新套餐失败")

    except Exception as e:
        return response.fail(message=f"操作失败: {str(e)}")


@router.post("/quick-set-quota")
async def quick_set_quota(
    package_id: str,
    quota_type: str,
    value: int
):
    """
    快速设置套餐配额

    参数：
        package_id: 套餐ID
        quota_type: 配额类型 (daily_chats, kb_count, kb_documents, file_storage_mb, file_count)
        value: 配额值 (-1 表示无限制)
    """
    try:
        from app.services.member.member_service import member_service

        # 验证配额类型
        if quota_type not in STANDARD_QUOTAS:
            return response.fail(message=f"不支持的配额类型: {quota_type}")

        field_name = STANDARD_QUOTAS[quota_type]["field"]

        # 更新套餐
        update_result = member_service.update_package(
            package_id,
            {field_name: value}
        )

        if update_result.get("success"):
            return response.success(
                data={
                    "message": f"{quota_type} 配额已更新为 {value}",
                    "quota_type": quota_type,
                    "value": value
                }
            )
        else:
            return response.fail(message="更新套餐失败")

    except Exception as e:
        return response.fail(message=f"操作失败: {str(e)}")


# ============================================================================
# 导出接口
# ============================================================================

@router.get("/export-code")
async def export_privilege_check_code():
    """
    导出权益检查代码示例

    返回可在 API 路由中直接使用的代码示例
    """
    from app.services.member.package_config_helper import export_privilege_check_code

    return response.success(
        data={
            "code": export_privilege_check_code(),
            "description": "权益检查代码示例，可直接复制到您的 API 路由中使用"
        }
    )


@router.get("/export-all-sql")
async def export_all_packages_sql():
    """
    导出所有预设套餐的 SQL

    生成免费版、基础月卡、高级月卡、企业年卡的完整 SQL
    """
    sql_parts = []

    # 生成所有预设套餐的 SQL
    for template_func in [create_free_package, create_basic_month_package,
                          create_premium_month_package, create_enterprise_year_package]:
        builder = template_func()
        sql_parts.append(builder.generate_sql())

    return response.success(
        data={
            "sql": "\n".join(sql_parts),
            "description": "所有预设套餐的 SQL 脚本"
        }
    )
