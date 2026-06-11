"""
发票穿透报告服务
独立实现，不依赖查税宝模块，通过远程签名接口 ObtainCiphertext 获取 sign
"""
import httpx
import os
from typing import Optional, Dict, Any
from app.infra.logging_config import get_logger
from dotenv import load_dotenv

# 确保环境变量已加载
load_dotenv()

logger = get_logger("app.services.invoice_penetration")


class InvoicePenetrationService:
    """发票穿透报告服务"""

    def __init__(self):
        """初始化服务"""
        self.base_url = os.getenv(
            'CHASHUIBAO_BASE_URL',
            'https://testcsbplus.dianzuanmao.com'
        )
        self.third_party_id = os.getenv('CHASHUIBAO_INVOICE_THIRD_PARTY_ID', '')
        self.private_key = os.getenv('CHASHUIBAO_INVOICE_PRIVATE_KEY', '')
        self.timeout = 30

        logger.info(
            f"发票穿透服务初始化完成，Base URL: {self.base_url}, "
            f"ThirdPartyID: {self.third_party_id[:20]}..."
        )

    async def _request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """发送 HTTP 请求"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                if method.upper() == 'GET':
                    response = await client.get(url, params=params)
                else:
                    response = await client.post(url, params=params)

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP 请求失败: {e.response.status_code} - {e.response.text}")
                raise Exception(f"发票穿透 API 请求失败: {e.response.status_code}")
            except httpx.RequestError as e:
                logger.error(f"HTTP 请求异常: {e}")
                raise Exception(f"发票穿透 API 请求异常: {str(e)}")

    async def _obtain_sign(
        self,
        taxpayer_id: Optional[str] = None,
        company_name: Optional[str] = None,
        order_no: Optional[str] = None,
    ) -> str:
        """调用远程签名接口 /openapi/csb/ObtainCiphertext 获取 sign

        Args:
            taxpayer_id: 纳税人识别号（可选）
            company_name: 企业名称（可选）
            order_no: 订单号（可选）

        Returns:
            签名字符串
        """
        params: Dict[str, Any] = {
            'thirdPartyId': self.third_party_id,
            'privateKey': self.private_key,
        }
        if taxpayer_id:
            params['taxpayerId'] = taxpayer_id
        if company_name:
            params['companyName'] = company_name
        if order_no:
            params['orderNo'] = order_no

        logger.info(f"请求远程签名: taxpayerId={taxpayer_id}, companyName={company_name}, orderNo={order_no}")

        url = f"{self.base_url}/openapi/csb/ObtainCiphertext"
        result = await self._request('POST', url, params=params)

        code = result.get('code')
        if str(code) != '0':
            error_msg = result.get('message', '获取签名失败')
            logger.error(f"远程签名失败: code={code}, message={error_msg}")
            raise Exception(error_msg)

        sign = None
        data = result.get('data')
        if isinstance(data, dict):
            sign = data.get('sign')
        elif isinstance(data, str):
            sign = data

        if not sign:
            sign = result.get('sign')

        if not sign:
            logger.error(f"签名为空，完整响应: {result}")
            raise Exception("服务端返回的签名为空")

        logger.info("远程签名获取成功")
        return sign

    async def get_authorization_url(
        self,
        taxpayer_id: str,
        company_name: str,
        cburl: str,
        report_type: str = "1",
        begin_date: Optional[str] = None,
        over_date: Optional[str] = None,
        report_logo: Optional[str] = None,
        watermark: Optional[str] = None,
        cover_url: Optional[str] = None,
        is_anonymity: Optional[int] = None,
    ) -> Dict[str, Any]:
        """获取授权链接

        流程：
            1. 调用 ObtainCiphertext 获取 sign
            2. 携带 sign 调用 /openapi/csb/authorizationV2
        """
        # 获取远程签名
        sign = await self._obtain_sign(
            taxpayer_id=taxpayer_id,
            company_name=company_name,
        )

        # 构建授权请求参数
        params: Dict[str, Any] = {
            'thirdPartyId': self.third_party_id,
            'taxpayerId': taxpayer_id,
            'companyName': company_name,
            'reportType': report_type,
            'cburl': cburl,
            'sign': sign,
        }

        if begin_date:
            params['beginDate'] = begin_date
        if over_date:
            params['overDate'] = over_date
        if report_logo:
            params['reportLogo'] = report_logo
        if watermark:
            params['watermark'] = watermark
        if cover_url:
            params['coverUrl'] = cover_url
        if is_anonymity is not None:
            params['isAnonymity'] = is_anonymity

        logger.info(f"请求获取发票穿透授权链接: company_name={company_name}")

        url = f"{self.base_url}/openapi/csb/authorizationV2"
        response = await self._request('GET', url, params=params)

        if response.get('code') in ('0', 0):
            logger.info(f"response: {response}")
            logger.info(f"获取授权链接成功: {response.get('data', {}).get('orderNo')}")
            return response.get('data', {})
        else:
            error_msg = response.get('message', '获取授权链接失败')
            logger.error(f"获取授权链接失败: {error_msg}, response: {response}")
            raise Exception(error_msg)

    async def get_report_data(
        self,
        taxpayer_id: str,
        company_name: str,
        order_no: str,
        data_type: int = 2,
    ) -> Dict[str, Any]:
        """获取报告数据

        流程：
            1. 调用 ObtainCiphertext 获取 sign
            2. 携带 sign 调用 /openapi/csb/openInvoiceReportV2
        """
        # 获取远程签名
        sign = await self._obtain_sign(
            taxpayer_id=taxpayer_id,
            company_name=company_name,
            order_no=order_no,
        )

        # 构建请求参数
        params: Dict[str, Any] = {
            'thirdPartyId': self.third_party_id,
            'taxpayerId': taxpayer_id,
            'companyName': company_name,
            'orderNo': order_no,
            'sign': sign,
            'dataType': data_type,
        }

        logger.info(
            f"请求获取发票穿透报告数据: order_no={order_no}, dataType={data_type}, "
            f"taxpayerId={taxpayer_id}, companyName={company_name}, "
            f"thirdPartyId={self.third_party_id[:20]}..., sign={sign[:20]}..."
        )

        url = f"{self.base_url}/openapi/csb/openInvoiceReportV2"
        logger.info(f"完整请求URL: {url}, 参数: {params}")
        result = await self._request('GET', url, params=params)

        logger.info(f"报告接口完整响应: order_no={order_no}, response={result}")

        if result.get('code') in ('0', 0):
            data = result.get('data')
            if data is None:
                msg = result.get('message', '报告数据为空')
                logger.warning(f"接口返回code=0但data为空: order_no={order_no}, message={msg}")
                raise Exception(f"报告数据为空: {msg}")
            logger.info(f"获取报告数据成功: {order_no}")
            return data
        else:
            error_msg = result.get('message', '获取报告数据失败')
            logger.error(f"获取报告数据失败: order_no={order_no}, code={result.get('code')}, message={error_msg}, 完整响应={result}")
            raise Exception(error_msg)


# 创建全局服务实例
invoice_penetration_service = InvoicePenetrationService()
