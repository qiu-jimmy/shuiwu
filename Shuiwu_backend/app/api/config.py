"""
系统配置管理模块 - API路由
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, Body
from pydantic import BaseModel
from app.services.config.config_service import config_service
from app.utils.dependencies import get_current_user_info
from app.utils.response import response

router = APIRouter(prefix="/api/config", tags=["系统配置"])


class DistributionConfigUpdate(BaseModel):
    """分销配置更新"""
    commission_rate: float = Body(None, description="佣金比例（百分比，如 10 表示 10%）")
    min_withdraw_amount: float = Body(None, description="提现最低金额（元）")
    settlement_days: int = Body(None, description="佣金结算天数")
    enabled: bool = Body(None, description="是否开启分销系统")


# ==================== 分销配置管理 ====================

@router.get(
    "/distribution",
    summary="获取分销配置",
    description="""
    获取分销系统配置信息。

    **返回内容：**
    - commission_rate: 佣金比例（百分比）
    - min_withdraw_amount: 提现最低金额
    - settlement_days: 佣金结算天数
    - enabled: 分销系统开关

    **注意：** 此接口可公开访问（用于测试），生产环境建议添加认证
    """,
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "获取成功",
                        "data": {
                            "commission_rate": 10.0,
                            "min_withdraw_amount": 50.0,
                            "settlement_days": 7,
                            "enabled": True
                        }
                    }
                }
            }
        }
    }
)
async def get_distribution_config() -> Dict[str, Any]:
    config = config_service.get_distribution_config()
    return response.success(data=config)


@router.post(
    "/distribution",
    summary="更新分销配置",
    description="""
    更新分销系统配置（仅管理员）。

    **配置说明：**
    - commission_rate: 佣金比例，0-100之间的数字
    - min_withdraw_amount: 提现最低金额，>= 0
    - settlement_days: 结算天数，>= 0
    - enabled: 是否开启分销系统
    """,
    responses={
        200: {
            "description": "更新成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "更新成功",
                        "data": {
                            "commission_rate": 15.0,
                            "min_withdraw_amount": 50.0,
                            "settlement_days": 7,
                            "enabled": True
                        }
                    }
                }
            }
        },
        400: {
            "description": "参数错误"
        }
    }
)
async def update_distribution_config(
    config: DistributionConfigUpdate,
    current_user: dict = Depends(get_current_user_info)
) -> Dict[str, Any]:
    result = config_service.update_distribution_config(
        commission_rate=config.commission_rate,
        min_withdraw_amount=config.min_withdraw_amount,
        settlement_days=config.settlement_days,
        enabled=config.enabled
    )
    if result.get("success"):
        return response.success(data=result.get("config"), message=result.get("message"))
    return response.fail(message=result.get("error", "更新配置失败"))


# ==================== 全局配置管理 ====================

@router.get(
    "/all",
    summary="获取所有系统配置",
    description="""
    获取所有系统配置列表。

    **用途：**
    - 管理员查看所有配置项
    - 获取配置的类型和描述信息
    """,
    responses={
        200: {
            "description": "获取成功"
        }
    }
)
async def get_all_configs() -> Dict[str, Any]:
    configs = config_service.get_all_configs()
    return response.success(data={"configs": configs})


@router.post(
    "/{config_key}",
    summary="更新单个配置",
    description="""
    更新指定配置的值（仅管理员）。

    **参数说明：**
    - config_key: 配置键名（路径参数）
    - config_value: 配置值（请求体）
    """,
    responses={
        200: {
            "description": "更新成功"
        },
        400: {
            "description": "配置不存在"
        }
    }
)
async def update_config(
    config_key: str,
    config_value: Any = Body(..., description="配置值"),
    current_user: dict = Depends(get_current_user_info)
) -> Dict[str, Any]:
    result = config_service.update_config(config_key, config_value)
    if result.get("success"):
        return response.success(data=result.get("config"), message="更新成功")
    return response.fail(message=result.get("error", "更新失败"))
