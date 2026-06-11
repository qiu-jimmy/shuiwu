"""
微信支付官方 SDK 客户端
使用微信支付官方 Python SDK (wechatpayv3) 处理支付请求
"""
import os
import json
from typing import Dict, Any, Optional
from wechatpayv3 import WeChatPay, WeChatPayType


class WechatPaySDKClient:
    """微信支付官方 SDK 客户端"""

    def __init__(self):
        """初始化微信支付客户端"""
        self._initialized = False
        self.wechat_pay = None
        self.mchid = None
        self.appid = None

    def _ensure_initialized(self):
        """确保配置已初始化"""
        if self._initialized:
            return

        self.mchid = os.getenv("WECHAT_PAY_MCHID")
        self.appid = os.getenv("WECHAT_PAY_APPID")
        private_key_path = os.getenv("WECHAT_PAY_PRIVATE_KEY_PATH")
        merchant_serial_no = os.getenv("WECHAT_PAY_CERT_SERIAL_NO")
        api_v3_key = os.getenv("WECHAT_PAY_API_V3_KEY")
        notify_url = os.getenv("WECHAT_PAY_NOTIFY_URL", "")
        public_key_path = os.getenv("WECHAT_PAY_PUBLIC_KEY_PATH")
        public_key_id = os.getenv("WECHAT_PAY_PUBLIC_KEY_ID")

        # 验证必要配置
        if not all([self.mchid, self.appid, private_key_path, merchant_serial_no, api_v3_key]):
            raise ValueError("微信支付配置不完整，请检查环境变量")

        # 读取私钥文件
        with open(private_key_path, 'r') as f:
            private_key = f.read()

        # 读取平台公钥（如果配置了）
        public_key = None
        if public_key_path:
            with open(public_key_path, 'r') as f:
                public_key = f.read()

        # 初始化官方 SDK
        # 如果配置了平台公钥，使用 public_key 和 public_key_id 参数
        # 这样可以绕过 SDK 的证书下载逻辑，避免 PUB_KEY_ID 格式的 bug
        if public_key:
            if not public_key_id:
                raise ValueError("配置了 WECHAT_PAY_PUBLIC_KEY_PATH 但未配置 WECHAT_PAY_PUBLIC_KEY_ID")

            self.wechat_pay = WeChatPay(
                wechatpay_type=WeChatPayType.JSAPI,
                mchid=self.mchid,
                private_key=private_key,
                cert_serial_no=merchant_serial_no,
                appid=self.appid,
                apiv3_key=api_v3_key,
                notify_url=notify_url,
                public_key=public_key,
                public_key_id=public_key_id,
            )
        else:
            # 没有配置平台公钥，使用 cert_dir 方式（需要处理 PUB_KEY_ID 格式问题）
            # 这里设置为 None，让 SDK 尝试自动下载证书
            # 注意：这种方式可能会遇到 PUB_KEY_ID 格式的 bug
            cert_dir = os.getenv("WECHAT_PAY_CERT_DIR")
            self.wechat_pay = WeChatPay(
                wechatpay_type=WeChatPayType.JSAPI,
                mchid=self.mchid,
                private_key=private_key,
                cert_serial_no=merchant_serial_no,
                appid=self.appid,
                apiv3_key=api_v3_key,
                notify_url=notify_url,
                cert_dir=cert_dir,
            )

        self._initialized = True

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
        self._ensure_initialized()

        try:
            # 调用官方 SDK 的 pay 方法
            # SDK 返回格式: (status_code, response_text)
            status_code, response_text = self.wechat_pay.pay(
                description=description,
                out_trade_no=out_trade_no,
                amount={"total": total_amount, "currency": "CNY"},
                payer={"openid": openid},
                attach=attach if attach else ""
            )

            # 检查状态码
            if status_code != 200:
                raise Exception(f"微信支付返回错误状态码: {status_code}, 响应: {response_text}")

            # 解析 JSON 响应
            result = json.loads(response_text)
            return result

        except json.JSONDecodeError as e:
            raise Exception(f"解析微信支付响应失败: {e}, 响应内容: {response_text}")
        except Exception as e:
            raise Exception(f"微信支付请求失败: {e}")

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
        self._ensure_initialized()

        try:
            status_code, response_text = self.wechat_pay.query(out_trade_no=out_trade_no, mchid=self.mchid)
            if status_code != 200:
                raise Exception(f"微信支付返回错误状态码: {status_code}, 响应: {response_text}")
            return json.loads(response_text)
        except Exception as e:
            raise Exception(f"微信支付查询失败: {e}")

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
        self._ensure_initialized()

        try:
            status_code, response_text = self.wechat_pay.close(out_trade_no=out_trade_no, mchid=self.mchid)
            if status_code != 200 and status_code != 204:
                raise Exception(f"微信支付返回错误状态码: {status_code}, 响应: {response_text}")
            # 204 No Content 可能没有响应体
            return {} if status_code == 204 or not response_text else json.loads(response_text)
        except Exception as e:
            raise Exception(f"微信支付关闭订单失败: {e}")

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
        self._ensure_initialized()

        try:
            params = {
                "out_trade_no": out_trade_no,
                "out_refund_no": out_refund_no,
                "amount": {
                    "refund": refund_amount,
                    "total": total_amount,
                    "currency": "CNY"
                }
            }

            if reason:
                params["reason"] = reason

            status_code, response_text = self.wechat_pay.refund(**params)
            if status_code != 200:
                raise Exception(f"微信支付返回错误状态码: {status_code}, 响应: {response_text}")
            return json.loads(response_text)
        except Exception as e:
            raise Exception(f"微信支付退款失败: {e}")

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
        self._ensure_initialized()

        try:
            status_code, response_text = self.wechat_pay.query_refund(out_refund_no=out_refund_no)
            if status_code != 200:
                raise Exception(f"微信支付返回错误状态码: {status_code}, 响应: {response_text}")
            return json.loads(response_text)
        except Exception as e:
            raise Exception(f"微信支付查询退款失败: {e}")

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
        import time
        import uuid

        self._ensure_initialized()

        try:
            # 生成小程序支付参数
            timeStamp = str(int(time.time()))
            nonceStr = uuid.uuid4().hex
            package = f"prepay_id={prepay_id}"

            # 使用 SDK 的 sign 方法签名，传入列表 [appId, timeStamp, nonceStr, package]
            paySign = self.wechat_pay.sign([self.appid, timeStamp, nonceStr, package])

            return {
                "appId": self.appid,
                "timeStamp": timeStamp,
                "nonceStr": nonceStr,
                "package": package,
                "signType": "RSA",
                "paySign": paySign
            }
        except Exception as e:
            raise Exception(f"生成小程序支付参数失败: {e}")


# 全局实例
wechat_pay_sdk_client = WechatPaySDKClient()
