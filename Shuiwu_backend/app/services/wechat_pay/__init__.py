"""
微信支付服务模块
"""
from app.services.wechat_pay.wechat_pay_repository import wechat_pay_config
from app.services.wechat_pay.wechat_pay_service import wechat_pay_service

__all__ = [
    "wechat_pay_config",
    "wechat_pay_service"
]
