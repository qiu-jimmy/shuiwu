"""
系统配置业务逻辑层
"""
from typing import Dict, Any, List, Optional
from app.services.config.config_repository import config_repository


class ConfigService:
    """系统配置业务逻辑"""

    def __init__(self):
        self.repo = config_repository

    def get_config(self, config_key: str, default: Any = None) -> Any:
        """获取配置值（带默认值）"""
        return self.repo.get_config_value(config_key, default)

    def get_all_configs(self) -> List[Dict[str, Any]]:
        """获取所有配置"""
        return self.repo.list_configs()

    def update_config(self, config_key: str, config_value: Any) -> Dict[str, Any]:
        """更新配置"""
        try:
            success = self.repo.update_config(config_key, config_value)
            if success:
                updated_config = self.repo.get_config(config_key)
                return {"success": True, "config": updated_config}
            return {"success": False, "error": "配置不存在"}
        except Exception as e:
            return {"success": False, "error": f"更新配置失败: {str(e)}"}

    def create_config(
        self,
        config_key: str,
        config_value: Any,
        config_type: str = "string",
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """创建配置"""
        try:
            success = self.repo.create_config(config_key, config_value, config_type, description)
            if success:
                new_config = self.repo.get_config(config_key)
                return {"success": True, "config": new_config}
            return {"success": False, "error": "创建配置失败（可能已存在）"}
        except Exception as e:
            return {"success": False, "error": f"创建配置异常: {str(e)}"}

    def delete_config(self, config_key: str) -> Dict[str, Any]:
        """删除配置"""
        try:
            success = self.repo.delete_config(config_key)
            if success:
                return {"success": True, "message": "删除成功"}
            return {"success": False, "error": "删除失败（可能不存在）"}
        except Exception as e:
            return {"success": False, "error": f"删除配置异常: {str(e)}"}

    # ==================== 分销相关便捷方法 ====================

    def get_distribution_config(self) -> Dict[str, Any]:
        """获取分销系统配置"""
        return {
            "commission_rate": self.get_config("distribution_commission_rate", 10),
            "min_withdraw_amount": self.get_config("distribution_min_withdraw_amount", 50),
            "settlement_days": self.get_config("distribution_settlement_days", 7),
            "enabled": self.get_config("distribution_enabled", True)
        }

    def is_distribution_enabled(self) -> bool:
        """检查分销系统是否开启"""
        return self.get_config("distribution_enabled", True)

    def get_commission_rate(self) -> float:
        """获取佣金比例（百分比）"""
        return self.get_config("distribution_commission_rate", 10)

    def get_min_withdraw_amount(self) -> float:
        """获取提现最低金额"""
        return self.get_config("distribution_min_withdraw_amount", 50)

    def get_settlement_days(self) -> int:
        """获取佣金结算天数"""
        return self.get_config("distribution_settlement_days", 7)

    def update_distribution_config(
        self,
        commission_rate: Optional[float] = None,
        min_withdraw_amount: Optional[float] = None,
        settlement_days: Optional[int] = None,
        enabled: Optional[bool] = None
    ) -> Dict[str, Any]:
        """更新分销配置"""
        errors = []

        if commission_rate is not None:
            if commission_rate < 0 or commission_rate > 100:
                errors.append("佣金比例必须在0-100之间")
            else:
                result = self.update_config("distribution_commission_rate", commission_rate)
                if not result.get("success"):
                    errors.append(result.get("error"))

        if min_withdraw_amount is not None:
            if min_withdraw_amount < 0:
                errors.append("提现最低金额不能为负数")
            else:
                result = self.update_config("distribution_min_withdraw_amount", min_withdraw_amount)
                if not result.get("success"):
                    errors.append(result.get("error"))

        if settlement_days is not None:
            if settlement_days < 0:
                errors.append("结算天数不能为负数")
            else:
                result = self.update_config("distribution_settlement_days", settlement_days)
                if not result.get("success"):
                    errors.append(result.get("error"))

        if enabled is not None:
            result = self.update_config("distribution_enabled", enabled)
            if not result.get("success"):
                errors.append(result.get("error"))

        if errors:
            return {"success": False, "error": "; ".join(errors)}

        return {
            "success": True,
            "message": "更新成功",
            "config": self.get_distribution_config()
        }


# 创建全局实例
config_service = ConfigService()
