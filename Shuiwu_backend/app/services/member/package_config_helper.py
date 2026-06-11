"""
会员套餐权限配置工具
====================
帮助开发者快速配置和管理套餐权益

功能：
1. 生成套餐配置 SQL
2. 验证配置格式
3. 查看所有可用权限类型
4. 批量更新套餐配置

使用示例：
    from app.services.member.package_config_helper import (
        generate_package_sql,
        validate_custom_config,
        get_all_privilege_types
    )
"""
from typing import Dict, Any, List, Optional
import json


# ============================================================================
# 标准权限类型定义
# ============================================================================

STANDARD_PRIVILEGES = {
    "rag": {
        "description": "RAG 知识库检索增强",
        "field": "enable_rag",
        "category": "AI功能"
    },
    "web_search": {
        "description": "实时网络搜索",
        "field": "enable_web_search",
        "category": "AI功能"
    },
    "mcp_tools": {
        "description": "MCP 工具集成",
        "field": "enable_mcp_tools",
        "category": "AI功能"
    },
}

STANDARD_QUOTAS = {
    "daily_chats": {
        "description": "每日聊天次数",
        "field": "max_daily_chats",
        "default": -1,  # -1 表示无限制
        "category": "配额"
    },
    "kb_count": {
        "description": "知识库数量",
        "field": "max_kb_count",
        "default": 5,
        "category": "配额"
    },
    "kb_documents": {
        "description": "每个知识库文档数",
        "field": "max_kb_documents",
        "default": 100,
        "category": "配额"
    },
    "file_storage_mb": {
        "description": "文件存储空间 (MB)",
        "field": "max_file_storage_mb",
        "default": 1024,
        "category": "配额"
    },
    "file_count": {
        "description": "文件数量",
        "field": "max_file_count",
        "default": 100,
        "category": "配额"
    },
    # 新增配额类型（按次计费的财税服务）
    "invoice_penetration": {
        "description": "发票穿透次数",
        "field": "max_invoice_penetration",
        "config_field": True,  # 存储在 custom_config 中
        "default": 0,
        "category": "财税服务"
    },
    "panorama": {
        "description": "全景报告次数",
        "field": "max_panorama",
        "config_field": True,  # 存储在 custom_config 中
        "default": 0,
        "category": "财税服务"
    },
    "business_risk": {
        "description": "经营风险查询次数",
        "field": "max_business_risk",
        "config_field": True,  # 存储在 custom_config 中
        "default": 0,
        "category": "财税服务"
    },
}

CUSTOM_PRIVILEGES_EXAMPLES = {
    "advanced_analytics": {
        "description": "高级数据分析",
        "config_key": "enable_advanced_analytics",
        "example_value": True,
        "category": "高级功能"
    },
    "team_collaboration": {
        "description": "团队协作",
        "config_key": "enable_team_collaboration",
        "example_value": True,
        "category": "协作功能"
    },
    "api_access": {
        "description": "API 访问权限",
        "config_key": "enable_api_access",
        "example_value": True,
        "category": "开发者"
    },
    "export_data": {
        "description": "数据导出",
        "config_key": "enable_export_data",
        "example_value": True,
        "category": "数据功能"
    },
    "ai_writing": {
        "description": "AI 写作助手",
        "config_key": "enable_ai_writing",
        "example_value": True,
        "category": "AI功能"
    },
    "voice_input": {
        "description": "语音输入",
        "config_key": "enable_voice_input",
        "example_value": True,
        "category": "交互功能"
    },
    "priority_support": {
        "description": "优先客服支持",
        "config_key": "enable_priority_support",
        "example_value": True,
        "category": "服务"
    },
    "custom_branding": {
        "description": "自定义品牌",
        "config_key": "enable_custom_branding",
        "example_value": True,
        "category": "企业功能"
    },
    # 新增权益（按次计费）
    "invoice_penetration": {
        "description": "发票穿透",
        "config_key": "enable_invoice_penetration",
        "quota_key": "max_invoice_penetration",
        "example_value": True,
        "example_quota": 10,
        "category": "财税服务",
        "quota_type": "按次计费"
    },
    "panorama": {
        "description": "全景报告",
        "config_key": "enable_panorama",
        "quota_key": "max_panorama",
        "example_value": True,
        "example_quota": 5,
        "category": "财税服务",
        "quota_type": "按次计费"
    },
    "business_risk": {
        "description": "经营风险",
        "config_key": "enable_business_risk",
        "quota_key": "max_business_risk",
        "example_value": True,
        "example_quota": 5,
        "category": "财税服务",
        "quota_type": "按次计费"
    },
}


# ============================================================================
# 配置生成器
# ============================================================================

class PackageConfigBuilder:
    """套餐配置构建器"""

    def __init__(self, package_id: str, name: str):
        self.package_id = package_id
        self.name = name
        self.config = {
            "package_id": package_id,
            "name": name,
            "description": "",
            "package_type": "month",
            "price": 0,
            "original_price": None,
            "duration_days": 30,
            # 标准权益
            "max_daily_chats": -1,
            "max_kb_count": 5,
            "max_kb_documents": 100,
            "max_file_storage_mb": 1024,
            "max_file_count": 100,
            "enable_rag": True,
            "enable_web_search": False,
            "enable_mcp_tools": False,
            # 其他
            "status": "active",
            "sort_order": 0,
            # 扩展配置
            "custom_config": {},
            "benefits": [],
        }

    def set_description(self, description: str):
        """设置描述"""
        self.config["description"] = description
        return self

    def set_pricing(
        self,
        price: float,
        package_type: str = "month",
        duration_days: Optional[int] = None,
        original_price: Optional[float] = None
    ):
        """设置价格信息"""
        self.config["price"] = price
        self.config["package_type"] = package_type
        if duration_days:
            self.config["duration_days"] = duration_days
        if original_price:
            self.config["original_price"] = original_price
        return self

    def enable_privilege(self, privilege: str):
        """启用标准权益"""
        if privilege in STANDARD_PRIVILEGES:
            field = STANDARD_PRIVILEGES[privilege]["field"]
            self.config[field] = True
        return self

    def disable_privilege(self, privilege: str):
        """禁用标准权益"""
        if privilege in STANDARD_PRIVILEGES:
            field = STANDARD_PRIVILEGES[privilege]["field"]
            self.config[field] = False
        return self

    def set_quota(self, quota_type: str, value: int):
        """设置配额"""
        if quota_type in STANDARD_QUOTAS:
            field = STANDARD_QUOTAS[quota_type]["field"]
            self.config[field] = value
        return self

    def set_custom_privilege(self, privilege: str, value: Any):
        """设置自定义权益（写入 custom_config）"""
        self.config["custom_config"][f"enable_{privilege}"] = value
        return self

    def set_custom_config(self, config: Dict[str, Any]):
        """设置整个 custom_config"""
        self.config["custom_config"].update(config)
        return self

    def add_benefit(self, title: str, desc: str):
        """添加权益描述"""
        self.config["benefits"].append({"title": title, "desc": desc})
        return self

    def build(self) -> Dict[str, Any]:
        """构建配置"""
        return self.config.copy()

    def generate_sql(self) -> str:
        """生成插入/更新 SQL"""
        config = self.build()

        # 构建 SQL
        columns = []
        values = []

        for key, value in config.items():
            if key == "benefits":
                columns.append(key)
                values.append(f"'{json.dumps(value, ensure_ascii=False)}'::jsonb")
            elif key == "custom_config":
                columns.append(key)
                json_str = json.dumps(value, ensure_ascii=False)
                values.append(f"'{json_str}'::jsonb")
            elif isinstance(value, str):
                columns.append(key)
                values.append(f"'{value}'")
            elif isinstance(value, bool):
                columns.append(key)
                values.append("TRUE" if value else "FALSE")
            elif value is None:
                columns.append(key)
                values.append("NULL")
            else:
                columns.append(key)
                values.append(str(value))

        sql = f"""
-- {self.name}
INSERT INTO business.member_packages ({', '.join(columns)})
VALUES ({', '.join(values)})
ON CONFLICT (package_id) DO UPDATE SET
    {', '.join([f'{col} = EXCLUDED.{col}' for col in columns if col not in ['package_id']])};
"""
        return sql


# ============================================================================
# 套餐模板
# ============================================================================

def create_free_package() -> PackageConfigBuilder:
    """创建免费套餐模板"""
    return (
        PackageConfigBuilder("free", "免费版")
        .set_description("基础功能体验")
        .set_pricing(0, "lifetime", None)
        .enable_privilege("rag")
        .disable_privilege("web_search")
        .disable_privilege("mcp_tools")
        .set_quota("daily_chats", 20)
        .set_quota("kb_count", 2)
        .set_quota("kb_documents", 20)
        .set_quota("file_storage_mb", 100)
        .add_benefit("每日20次对话", "每天可以免费使用20次AI对话")
        .add_benefit("2个知识库", "支持创建2个个人知识库")
        .add_benefit("基础RAG功能", "知识库检索增强生成")
    )


def create_basic_month_package() -> PackageConfigBuilder:
    """创建基础月卡套餐模板"""
    return (
        PackageConfigBuilder("basic_month", "基础月卡")
        .set_description("月度会员，解锁更多功能")
        .set_pricing(29.9, "month", 30, 39.9)
        .enable_privilege("rag")
        .enable_privilege("web_search")
        .disable_privilege("mcp_tools")
        .set_quota("daily_chats", -1)  # 无限制
        .set_quota("kb_count", 10)
        .set_quota("kb_documents", 500)
        .set_quota("file_storage_mb", 2048)
        .set_custom_config({
            "level": "basic",
            "priority": 1,
            # 新增权益配置
            "enable_invoice_penetration": True,
            "max_invoice_penetration": 10,
            "enable_panorama": True,
            "max_panorama": 5,
            "enable_business_risk": True,
            "max_business_risk": 5,
        })
        .add_benefit("无限对话", "每日无限制AI对话次数")
        .add_benefit("10个知识库", "支持创建10个知识库")
        .add_benefit("网络搜索", "支持实时网络搜索功能")
        .add_benefit("2GB存储", "云端文件存储空间")
        .add_benefit("发票穿透", "深度分析发票关联关系，支持10次/月")
        .add_benefit("全景报告", "企业全景数据报告，支持5次/月")
        .add_benefit("经营风险", "企业经营风险评估，支持5次/月")
    )


def create_premium_month_package() -> PackageConfigBuilder:
    """创建高级月卡套餐模板"""
    return (
        PackageConfigBuilder("premium_month", "高级月卡")
        .set_description("月度会员，全功能解锁")
        .set_pricing(59.9, "month", 30, 79.9)
        .enable_privilege("rag")
        .enable_privilege("web_search")
        .enable_privilege("mcp_tools")
        .set_quota("daily_chats", -1)
        .set_quota("kb_count", 20)
        .set_quota("kb_documents", 2000)
        .set_quota("file_storage_mb", 5120)
        .set_custom_config({
            "level": "premium",
            "priority": 2,
            "features": ["rag", "web_search", "mcp_tools"],
            # 新增权益配置
            "enable_invoice_penetration": True,
            "max_invoice_penetration": 50,
            "enable_panorama": True,
            "max_panorama": 30,
            "enable_business_risk": True,
            "max_business_risk": 30,
        })
        .add_benefit("无限对话", "每日无限制AI对话次数")
        .add_benefit("20个知识库", "支持创建20个知识库")
        .add_benefit("网络搜索", "支持实时网络搜索功能")
        .add_benefit("MCP工具", "支持丰富的MCP工具集成")
        .add_benefit("5GB存储", "云端文件存储空间")
        .add_benefit("发票穿透", "深度分析发票关联关系，支持50次/月")
        .add_benefit("全景报告", "企业全景数据报告，支持30次/月")
        .add_benefit("经营风险", "企业经营风险评估，支持30次/月")
    )


def create_enterprise_year_package() -> PackageConfigBuilder:
    """创建企业年卡套餐模板"""
    return (
        PackageConfigBuilder("enterprise_year", "企业年卡")
        .set_description("年度会员，最佳性价比，全功能解锁")
        .set_pricing(299.9, "year", 365, 399.9)
        .enable_privilege("rag")
        .enable_privilege("web_search")
        .enable_privilege("mcp_tools")
        .set_quota("daily_chats", -1)
        .set_quota("kb_count", 100)
        .set_quota("kb_documents", 10000)
        .set_quota("file_storage_mb", 51200)
        .set_custom_config({
            "level": "enterprise",
            "priority": 3,
            "features": ["rag", "web_search", "mcp_tools"],
            "max_team_members": 50,
            "enable_priority_support": True,
            "enable_custom_branding": True,
            "enable_api_access": True,
            # 新增权益配置（无限使用）
            "enable_invoice_penetration": True,
            "max_invoice_penetration": -1,
            "enable_panorama": True,
            "max_panorama": -1,
            "enable_business_risk": True,
            "max_business_risk": -1,
        })
        .add_benefit("无限对话", "每日无限制AI对话次数")
        .add_benefit("100个知识库", "支持创建100个知识库")
        .add_benefit("全功能解锁", "RAG、网络搜索、MCP工具全开")
        .add_benefit("团队协作", "支持50人团队协作")
        .add_benefit("优先支持", "专属客服支持")
        .add_benefit("API访问", "开放API接口")
        .add_benefit("50GB存储", "超大云端文件存储空间")
        .add_benefit("发票穿透", "深度分析发票关联关系，无限次使用")
        .add_benefit("全景报告", "企业全景数据报告，无限次使用")
        .add_benefit("经营风险", "企业经营风险评估，无限次使用")
    )


# ============================================================================
# 工具函数
# ============================================================================

def get_all_privilege_types() -> Dict[str, Any]:
    """获取所有可用的权益类型"""
    return {
        "standard": STANDARD_PRIVILEGES,
        "custom": CUSTOM_PRIVILEGES_EXAMPLES,
        "quotas": STANDARD_QUOTAS
    }


def validate_custom_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """验证 custom_config 格式"""
    errors = []
    warnings = []

    if not isinstance(config, dict):
        return {"valid": False, "errors": ["custom_config 必须是对象类型"]}

    # 检查自定义权益格式
    for key, value in config.items():
        if key.startswith("enable_"):
            privilege_name = key.replace("enable_", "")
            if not isinstance(value, bool):
                errors.append(f"{key}: 应该是布尔值")

            # 检查是否为已知权益
            if privilege_name in STANDARD_PRIVILEGES:
                warnings.append(f"{key}: 与标准字段 {STANDARD_PRIVILEGES[privilege_name]['field']} 重复")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def generate_batch_sql(packages: List[Dict[str, Any]]) -> str:
    """生成批量插入套餐的 SQL"""
    sql_parts = []

    for package in packages:
        builder = PackageConfigBuilder(package["package_id"], package["name"])

        if "description" in package:
            builder.set_description(package["description"])

        if "pricing" in package:
            p = package["pricing"]
            builder.set_pricing(
                price=p.get("price", 0),
                package_type=p.get("package_type", "month"),
                duration_days=p.get("duration_days"),
                original_price=p.get("original_price")
            )

        for privilege in package.get("enable_privileges", []):
            builder.enable_privilege(privilege)

        for privilege in package.get("disable_privileges", []):
            builder.disable_privilege(privilege)

        for quota_type, value in package.get("quotas", {}).items():
            builder.set_quota(quota_type, value)

        if "custom_config" in package:
            builder.set_custom_config(package["custom_config"])

        for benefit in package.get("benefits", []):
            builder.add_benefit(benefit["title"], benefit["desc"])

        sql_parts.append(builder.generate_sql())

    return "\n".join(sql_parts)


def export_privilege_check_code() -> str:
    """导出权益检查代码示例"""
    return '''
# 在您的 API 路由中使用权限装饰器

from fastapi import APIRouter
from app.middleware.member_permission import (
    require_member_privilege,
    require_member_features
)

router = APIRouter()

# 示例 1: 检查单个权益
@router.post("/chat/rag")
@require_member_privilege("rag")
async def rag_chat():
    return {"message": "RAG 功能已启用"}

# 示例 2: 组合检查
@router.post("/advanced/feature")
@require_member_features(
    privileges=["rag", "web_search"],
    quotas={"kb_count": 1},
    min_level="premium"
)
async def advanced_feature():
    return {"message": "所有权限检查通过"}

# 示例 3: 自定义权限（需要在 custom_config 中配置）
@router.post("/custom/feature")
@require_member_privilege("team_collaboration")
async def custom_feature():
    return {"message": "团队协作功能已启用"}
'''


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    # 构建器
    "PackageConfigBuilder",
    # 模板
    "create_free_package",
    "create_basic_month_package",
    "create_premium_month_package",
    "create_enterprise_year_package",
    # 工具
    "get_all_privilege_types",
    "validate_custom_config",
    "generate_batch_sql",
    "export_privilege_check_code",
    # 常量
    "STANDARD_PRIVILEGES",
    "STANDARD_QUOTAS",
    "CUSTOM_PRIVILEGES_EXAMPLES",
]
