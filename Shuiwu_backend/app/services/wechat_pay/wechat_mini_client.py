"""
微信小程序 HTTP 客户端
封装微信小程序 API 的 HTTP 请求，包括：
- 获取 access_token
- 生成不限制的小程序码
- 微信登录 code2Session
"""
import os
import time
import json
import httpx
from typing import Dict, Any, Optional


class WechatMiniClient:
    """微信小程序客户端"""

    def __init__(self):
        """初始化微信小程序客户端"""
        self._initialized = False
        self.appid = None
        self.secret = None
        self._access_token = None
        self._token_expires_at = 0

    def _ensure_initialized(self):
        """确保配置已初始化"""
        if self._initialized:
            return

        self.appid = os.getenv("WECHAT_MINI_APPID")
        self.secret = os.getenv("WECHAT_MINI_APPSECRET")

        # 验证必要配置
        if not all([self.appid, self.secret]):
            raise ValueError("微信小程序配置不完整，请检查环境变量 WECHAT_MINI_APPID 和 WECHAT_MINI_APPSECRET")

        self._initialized = True

    async def get_access_token(self, force_refresh: bool = False) -> str:
        """
        获取 access_token

        Args:
            force_refresh: 是否强制刷新

        Returns:
            access_token

        Raises:
            Exception: 获取失败时抛出异常
        """
        self._ensure_initialized()

        # 检查是否需要刷新
        current_time = int(time.time())
        if not force_refresh and self._access_token and current_time < self._token_expires_at:
            return self._access_token

        # 获取新的 access_token
        url = "https://api.weixin.qq.com/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": self.appid,
            "secret": self.secret
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=30.0)

            if response.status_code != 200:
                raise Exception(f"获取 access_token 失败: HTTP {response.status_code}")

            data = response.json()

            if "access_token" not in data:
                errcode = data.get("errcode", -1)
                errmsg = data.get("errmsg", "未知错误")
                raise Exception(f"获取 access_token 失败: [{errcode}] {errmsg}")

            # 缓存 access_token（提前5分钟过期）
            self._access_token = data["access_token"]
            expires_in = data.get("expires_in", 7200)
            self._token_expires_at = current_time + expires_in - 300

            return self._access_token

    async def get_unlimited_qrcode(
        self,
        scene: str,
        page: Optional[str] = None,
        check_path: bool = True,
        env_version: str = "release",
        width: int = 430,
        auto_color: bool = False,
        line_color: Optional[Dict[str, int]] = None,
        is_hyaline: bool = False
    ) -> bytes:
        """
        获取不限制的小程序码

        Args:
            scene: 场景值（最大32个可见字符）
            page: 页面路径（如 pages/index/index），默认主页
            check_path: 是否检查页面存在
            env_version: 要打开的小程序版本（release/trial/develop）
            width: 二维码宽度（px），280-1280
            auto_color: 是否自动配置线条颜色
            line_color: 线条颜色 RGB，如 {"r": 0, "g": 0, "b": 0}
            is_hyaline: 是否透明底色

        Returns:
            小程序码图片二进制数据

        Raises:
            Exception: 生成失败时抛出异常
        """
        self._ensure_initialized()

        # 获取 access_token
        access_token = await self.get_access_token()

        # 构建 URL
        url = f"https://api.weixin.qq.com/wxa/getwxacodeunlimit?access_token={access_token}"

        # 构建请求参数
        request_data = {
            "scene": scene,
            "check_path": check_path,
            "env_version": env_version,
            "width": width,
            "auto_color": auto_color,
            "is_hyaline": is_hyaline
        }

        if page:
            request_data["page"] = page

        if line_color:
            request_data["line_color"] = line_color

        # 发送请求
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=request_data,
                timeout=30.0
            )

            # 检查响应
            if response.status_code != 200:
                raise Exception(f"生成小程序码失败: HTTP {response.status_code}")

            # 检查是否返回错误（JSON）
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                error_data = response.json()
                errcode = error_data.get("errcode", -1)
                errmsg = error_data.get("errmsg", "未知错误")
                raise Exception(f"生成小程序码失败: [{errcode}] {errmsg}")

            # 返回图片二进制数据
            return response.content

    async def code2_session(self, js_code: str) -> Dict[str, Any]:
        """
        微信小程序登录凭证校验
        通过 wx.login 获得临时登录凭证 code 后，调用此接口完成登录流程

        Args:
            js_code: 登录时获取的 code，可通过 wx.login 获取

        Returns:
            包含 openid, session_key, unionid 的字典

        Raises:
            Exception: 登录失败时抛出异常
        """
        self._ensure_initialized()

        url = "https://api.weixin.qq.com/sns/jscode2session"
        params = {
            "appid": self.appid,
            "secret": self.secret,
            "js_code": js_code,
            "grant_type": "authorization_code"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=30.0)

            if response.status_code != 200:
                raise Exception(f"code2Session 请求失败: HTTP {response.status_code}")

            data = response.json()

            # 检查是否有错误
            errcode = data.get("errcode")
            if errcode:
                errmsg = data.get("errmsg", "未知错误")
                # 错误码映射
                error_messages = {
                    -1: "系统繁忙，请稍后重试",
                    40029: "code 无效",
                    40226: "高风险等级用户，小程序登录拦截",
                    45011: "API 调用太频繁，请稍后重试"
                }
                error_msg = error_messages.get(errcode, f"[{errcode}] {errmsg}")
                raise Exception(f"code2Session 失败: {error_msg}")

            return {
                "openid": data.get("openid"),
                "session_key": data.get("session_key"),
                "unionid": data.get("unionid")
            }


# 全局实例
wechat_mini_client = WechatMiniClient()
