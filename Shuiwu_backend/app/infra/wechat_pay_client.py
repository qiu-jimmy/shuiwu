"""
微信支付 HTTP 客户端
封装微信支付 API v3 的 HTTP 请求
"""
import os
import time
import json
import uuid
import httpx
from typing import Dict, Any, Optional
from app.services.wechat_pay.signature import WechatPaySignature


class WechatPayClient:
    """微信支付客户端"""

    def __init__(self):
        """初始化微信支付客户端"""
        self.base_url = "https://api.mch.weixin.qq.com"
        self._initialized = False
        self.mchid = None
        self.appid = None
        self.api_v3_key = None
        self.private_key_path = None
        self.public_key_path = None
        self.cert_serial_no = None

    def _ensure_initialized(self):
        """确保配置已初始化"""
        if self._initialized:
            return

        self.mchid = os.getenv("WECHAT_PAY_MCHID")
        self.appid = os.getenv("WECHAT_PAY_APPID")
        self.api_v3_key = os.getenv("WECHAT_PAY_API_V3_KEY")
        self.private_key_path = os.getenv("WECHAT_PAY_PRIVATE_KEY_PATH")
        self.public_key_path = os.getenv("WECHAT_PAY_PUBLIC_KEY_PATH")
        self.cert_serial_no = os.getenv("WECHAT_PAY_CERT_SERIAL_NO")

        # 如果没有配置序列号，尝试从私钥证书中提取
        if not self.cert_serial_no and self.private_key_path:
            self.cert_serial_no = WechatPaySignature.get_cert_serial_no(self.private_key_path)

        # 验证必要配置
        if not all([self.mchid, self.appid, self.api_v3_key, self.private_key_path]):
            raise ValueError("微信支付配置不完整，请检查环境变量")

        self._initialized = True

    def _build_headers(
        self,
        http_method: str,
        url: str,
        body: str = ""
    ) -> Dict[str, str]:
        """
        构建请求头（包含签名）

        Args:
            http_method: HTTP方法
            url: 请求URL
            body: 请求体

        Returns:
            请求头字典
        """
        self._ensure_initialized()

        # 生成时间戳和随机串
        timestamp = str(int(time.time()))
        nonce_str = uuid.uuid4().hex

        # 构建签名消息
        # URL需要去掉域名部分
        url_path = url.replace(self.base_url, "")
        signature_message = WechatPaySignature.build_signature_message(
            http_method=http_method,
            url=url_path,
            timestamp=timestamp,
            nonce_str=nonce_str,
            body=body
        )

        # 使用私钥签名
        signature = WechatPaySignature.private_key_sign(
            message=signature_message,
            private_key_path=self.private_key_path
        )

        # 构建请求头
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"WechatPay-Apython-H5SDK/0.0.1 ({self.mchid})",
            "Authorization": (
                f"WECHATPAY2-SHA256-RSA2048 "
                f"mchid=\"{self.mchid}\","
                f"nonce_str=\"{nonce_str}\","
                f"signature=\"{signature}\","
                f"timestamp=\"{timestamp}\","
                f"serial_no=\"{self.cert_serial_no}\""
            )
        }

        return headers

    async def _request(
        self,
        http_method: str,
        url: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        发送HTTP请求

        Args:
            http_method: HTTP方法
            url: 请求URL
            data: 请求数据

        Returns:
            响应数据
        """
        # 准备请求体（使用紧凑格式，确保与签名一致）
        # 注意：必须使用 ensure_ascii=True，与微信 SDK 行为一致
        body = json.dumps(data, separators=(',', ':'), ensure_ascii=True) if data else ""

        # 构建请求头
        headers = self._build_headers(http_method, url, body)

        # 发送请求
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=http_method,
                url=url,
                headers=headers,
                content=body.encode('utf-8') if body else None,
                timeout=30.0
            )

            # 处理响应
            if response.status_code == 200:
                return response.json()
            else:
                error_msg = f"微信支付请求失败: {response.status_code} - {response.text}"
                raise Exception(error_msg)

    async def jsapi_order(
        self,
        description: str,
        out_trade_no: str,
        total_amount: int,
        openid: str,
        attach: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        JSAPI下单接口

        Args:
            description: 商品描述
            out_trade_no: 商户订单号
            total_amount: 订单总金额（单位：分）
            openid: 用户openid
            attach: 附加数据

        Returns:
            返回包含 prepay_id 的数据
        """
        url = f"{self.base_url}/v3/pay/transactions/jsapi"

        # 构建请求参数（按照微信支付 API 规范的字段顺序）
        request_data = {
            "appid": self.appid,
            "mchid": self.mchid,
            "description": description,
            "out_trade_no": out_trade_no,
            "notify_url": os.getenv("WECHAT_PAY_NOTIFY_URL", ""),
            "amount": {
                "total": total_amount,
                "currency": "CNY"
            },
            "payer": {
                "openid": openid
            }
        }

        if attach:
            # 在 notify_url 之后添加 attach，保持正确的字段顺序
            request_data = {
                "appid": self.appid,
                "mchid": self.mchid,
                "description": description,
                "out_trade_no": out_trade_no,
                "attach": attach,
                "notify_url": os.getenv("WECHAT_PAY_NOTIFY_URL", ""),
                "amount": {
                    "total": total_amount,
                    "currency": "CNY"
                },
                "payer": {
                    "openid": openid
                }
            }

        # 发送请求
        return await self._request("POST", url, request_data)

    async def query_order(
        self,
        out_trade_no: str
    ) -> Dict[str, Any]:
        """
        查询订单

        Args:
            out_trade_no: 商户订单号

        Returns:
            订单信息
        """
        url = f"{self.base_url}/v3/pay/transactions/out-trade-no/{out_trade_no}?mchid={self.mchid}"

        return await self._request("GET", url)

    async def close_order(
        self,
        out_trade_no: str
    ) -> Dict[str, Any]:
        """
        关闭订单

        Args:
            out_trade_no: 商户订单号

        Returns:
            关闭结果
        """
        url = f"{self.base_url}/v3/pay/transactions/out-trade-no/{out_trade_no}/close"

        return await self._request("POST", url, {})

    async def create_refund(
        self,
        out_trade_no: str,
        out_refund_no: str,
        total_amount: int,
        refund_amount: int,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        申请退款

        Args:
            out_trade_no: 商户订单号
            out_refund_no: 商户退款单号
            total_amount: 订单总金额（分）
            refund_amount: 退款金额（分）
            reason: 退款原因

        Returns:
            退款结果
        """
        url = f"{self.base_url}/v3/refund/domestic/refunds"

        request_data = {
            "out_trade_no": out_trade_no,
            "out_refund_no": out_refund_no,
            "amount": {
                "refund": refund_amount,
                "total": total_amount,
                "currency": "CNY"
            }
        }

        if reason:
            request_data["reason"] = reason

        return await self._request("POST", url, request_data)

    async def query_refund(
        self,
        out_refund_no: str
    ) -> Dict[str, Any]:
        """
        查询退款

        Args:
            out_refund_no: 商户退款单号

        Returns:
            退款信息
        """
        url = f"{self.base_url}/v3/refund/domestic/refunds/{out_refund_no}"

        return await self._request("GET", url)

    def build_mini_program_pay_params(
        self,
        prepay_id: str
    ) -> Dict[str, str]:
        """
        构建小程序支付所需参数

        Args:
            prepay_id: 预支付交易会话标识

        Returns:
            小程序支付所需的参数
        """
        self._ensure_initialized()

        # 生成时间戳和随机串
        timestamp = str(int(time.time()))
        nonce_str = uuid.uuid4().hex
        package = f"prepay_id={prepay_id}"

        # 构建签名消息
        # 小程序支付的签名规则不同于API请求
        signature_message = f"{self.appid}\n{timestamp}\n{nonce_str}\n{package}\n"

        # 签名
        signature = WechatPaySignature.private_key_sign(
            message=signature_message,
            private_key_path=self.private_key_path
        )

        # 返回小程序支付参数
        return {
            "appId": self.appid,
            "timeStamp": timestamp,
            "nonceStr": nonce_str,
            "package": package,
            "signType": "RSA",
            "paySign": signature
        }


# 全局实例
wechat_pay_client = WechatPayClient()
