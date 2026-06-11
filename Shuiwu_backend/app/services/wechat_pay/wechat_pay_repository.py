"""
微信支付配置管理 - Repository层
"""
import os
from typing import Dict, Any, Optional


class WechatPayConfig:
    """微信支付配置类"""

    def __init__(self):
        """初始化配置"""
        self._config = None

    async def load_config(self) -> None:
        """加载配置"""
        self._config = {
            "appid": os.getenv("WECHAT_PAY_APPID"),
            "mchid": os.getenv("WECHAT_PAY_MCHID"),
            "api_v3_key": os.getenv("WECHAT_PAY_API_V3_KEY"),
            "cert_serial_no": os.getenv("WECHAT_PAY_CERT_SERIAL_NO"),
            "private_key_path": os.getenv("WECHAT_PAY_PRIVATE_KEY_PATH"),
            "public_key_path": os.getenv("WECHAT_PAY_PUBLIC_KEY_PATH"),
            "notify_url": os.getenv("WECHAT_PAY_NOTIFY_URL")
        }

    def get_config(self) -> Dict[str, Any]:
        """获取配置"""
        if self._config is None:
            raise ValueError("配置未加载，请先调用 load_config()")
        return self._config

    def get(self, key: str, default: Any = None) -> Any:
        """获取单个配置项"""
        config = self.get_config()
        return config.get(key, default)

    def is_loaded(self) -> bool:
        """检查配置是否已加载"""
        return self._config is not None


# 全局实例
wechat_pay_config = WechatPayConfig()
