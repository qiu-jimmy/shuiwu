"""
chashuibao_service.py — 查税宝业务服务层

职责：
  - 封装与查税宝外部 API 的所有交互（签名、授权、报告生成、状态查询）
  - 通过 SM2 非对称加密完成接口签名（见 sm2_signature.py）
  - 全景报告：支持仅凭企业名称自动查询税号后生成报告

关键接口：
  - get_taxpayer_no_by_name(ename): 通过企业名称查询税号（/openapi/obtainTaxNumBySearchName）
  - generate_panoramic_report(...): 生成全景报告，taxpayer_no 为空时自动调用上方接口补全
"""
import httpx
import os
from typing import Optional, Dict, Any
from app.infra.logging_config import get_logger
from dotenv import load_dotenv

# 确保环境变量已加载
load_dotenv()

logger = get_logger("app.services.chashuibao")


class ChashuibaoService:
    """查税宝经营风险报告服务"""

    def __init__(self):
        """初始化服务"""
        # 从环境变量获取配置
        self.base_url = os.getenv(
            'CHASHUIBAO_BASE_URL',
            'https://testcsbplus.dianzuanmao.com'  # 默认测试环境
        )
        # 工商 token（全景报告、企业名称查税号）
        self.third_party_id = os.getenv('CHASHUIBAO_THIRD_PARTY_ID', '')
        # 经营风险报告专用 token
        self.business_risk_third_party_id = os.getenv('CHASHUIBAO_BUSINESS_RISK_THIRD_PARTY_ID', '')
        self.timeout = 30

        # 设置 SM2 私钥
        private_key = os.getenv('CHASHUIBAO_PRIVATE_KEY', '')
        if private_key:
            from app.services.chashuibao.sm2_signature import ChashuibaoSignature
            ChashuibaoSignature.set_private_key(private_key)
            logger.info(f"SM2 私钥已配置 (长度: {len(private_key)})")

        logger.info(f"查税宝服务初始化完成，Base URL: {self.base_url}, ThirdPartyID: {self.third_party_id[:20]}...")

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """发送 HTTP 请求

        Args:
            method: 请求方法（GET/POST）
            path: 请求路径
            params: URL 参数
            data: 请求体数据
            headers: 请求头

        Returns:
            响应数据

        Raises:
            Exception: 请求失败
        """
        url = f"{self.base_url}{path}"

        # 默认请求头
        default_headers = {
            'Content-Type': 'application/json',
        }
        if headers:
            default_headers.update(headers)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                if method.upper() == 'GET':
                    response = await client.get(url, params=params, headers=default_headers)
                else:  # POST
                    response = await client.post(url, params=params, json=data, headers=default_headers)

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP 请求失败: {e.response.status_code} - {e.response.text}")
                raise Exception(f"查税宝 API 请求失败: {e.response.status_code}")
            except httpx.RequestError as e:
                logger.error(f"HTTP 请求异常: {e}")
                raise Exception(f"查税宝 API 请求异常: {str(e)}")

    async def get_authorization_url(
        self,
        taxpayer_id: str,
        company_name: str,
        cburl: str,
        report_type: str = "2",
        quarter_section: Optional[list] = None,
        report_logo: Optional[str] = None,
        watermark: Optional[str] = None,
        cover_url: Optional[str] = None,
        is_anonymity: Optional[int] = None
    ) -> Dict[str, Any]:
        """获取授权链接

        Args:
            taxpayer_id: 纳税人识别号（加密）
            company_name: 企业名称（加密）
            cburl: 授权完成回调页面
            report_type: 报告类型，默认 2（经营风险报告）
            quarter_section: 年度季度多选列表，如 [{"year":"2025","quarter":"1"},{"year":"2025","quarter":"2"}]
            report_logo: 封面logo URL
            watermark: 水印 URL
            cover_url: 封面 URL
            is_anonymity: 是否匿名

        Returns:
            包含 orderNo 和 initialUrl 的字典
        """
        import uuid

        # 生成 orderNo
        order_no = f"S_{uuid.uuid4().hex}"

        # 使用经营风险专用私钥签名
        private_key = os.getenv('CHASHUIBAO_BUSINESS_RISK_PRIVATE_KEY', '')

        # 构建远程签名请求参数
        sign_params = {
            'thirdPartyId': self.business_risk_third_party_id,
            'privateKey': private_key,
            'taxpayerId': taxpayer_id,
            'companyName': company_name,
        }

        # 获取远程签名
        sign_response = await self._request('GET', '/openapi/csb/ObtainCiphertext', params=sign_params)

        # 检查响应（查税宝 API 返回 '0' 或 0 表示成功）
        sign_code = sign_response.get('code')
        if str(sign_code) != '0':
            error_msg = sign_response.get('message', '获取签名失败')
            logger.error(f"获取远程签名失败: code={sign_code}, message={error_msg}")
            raise Exception(error_msg)

        sign = sign_response.get('data', {}).get('sign', '')
        if not sign:
            raise Exception("服务端返回的签名为空")

        # 构建授权链接请求参数
        params = {
            'thirdPartyId': self.business_risk_third_party_id,
            'taxpayerId': taxpayer_id,
            'companyName': company_name,
            'reportType': report_type,
            'cburl': cburl,
            'orderNo': order_no,
            'sign': sign,
        }

        # 添加可选参数
        if quarter_section:
            import json
            params['quarterSection'] = json.dumps(
                [{"year": qs["year"], "quarter": qs["quarter"]} for qs in quarter_section],
                ensure_ascii=False,
            )
            params['year'] = quarter_section[-1]['year']
            params['quarter'] = quarter_section[-1]['quarter']
        if report_logo:
            params['reportLogo'] = report_logo
        if watermark:
            params['watermark'] = watermark
        if cover_url:
            params['coverUrl'] = cover_url
        if is_anonymity is not None:
            params['isAnonymity'] = is_anonymity

        logger.info(f"请求获取授权链接: params={params}")

        # 发送请求
        response = await self._request('GET', '/openapi/csb/authorizationV2', params=params)

        # 检查响应
        logger.info(f"授权链接接口返回: code={response.get('code')}, message={response.get('message')}, data={response.get('data')}")
        if str(response.get('code')) == '0':
            logger.info(f"获取授权链接成功: orderNo={response.get('data', {}).get('orderNo')}")
            return response.get('data', {})
        else:
            error_msg = response.get('message', '获取授权链接失败')
            logger.error(f"获取授权链接失败: code={response.get('code')}, message={error_msg}, 完整响应={response}")
            raise Exception(error_msg)

    async def upload_report(
        self,
        firm_name: str,
        year: str,
        quarter: str,
        phone: str,
        taxpayer_no: str,
        report_no: str,
        accounting_criterion_id: str,
        taxpayer_type: str,
        taxpayer_name: str,
        zzs_file_bs: str = "0",
        sds_file_bs: str = "0",
        cb_file_bs: str = "0",
        # 增值税文件 URL
        zzs: Optional[str] = None,
        zzs_zb: Optional[str] = None,
        zzs_fb1: Optional[str] = None,
        zzs_fb2: Optional[str] = None,
        zzs_fb3: Optional[str] = None,
        zzs_fb4: Optional[str] = None,
        zzs_jmmx: Optional[str] = None,
        # 所得税文件 URL
        sds: Optional[str] = None,
        sds_zb: Optional[str] = None,
        sds_fb1: Optional[str] = None,
        sds_fb2: Optional[str] = None,
        sds_fb3: Optional[str] = None,
        # 财务报表文件 URL
        cb: Optional[str] = None,
        cb_zcfz: Optional[str] = None,
        cb_lr: Optional[str] = None,
        cb_xjll: Optional[str] = None,
    ) -> Dict[str, Any]:
        """手动上传报表

        Args:
            firm_name: 企业名称
            year: 年度
            quarter: 季度
            phone: 用户手机号
            taxpayer_no: 纳税人识别号
            report_no: 报告编号
            accounting_criterion_id: 会计准则编码
            taxpayer_type: 纳税人类型编码
            taxpayer_name: 企业名称
            zzs_file_bs: 增值税文件标识
            sds_file_bs: 所得税文件标识
            cb_file_bs: 财报文件标识
            zzs: 增值税文件URL（完整）
            zzs_zb: 增值税文件URL-主表
            zzs_fb1: 增值税文件URL-附一
            zzs_fb2: 增值税文件URL-附二
            zzs_fb3: 增值税文件URL-附三
            zzs_fb4: 增值税文件URL-附四
            zzs_jmmx: 增值税文件URL-减免明细
            sds: 所得税文件URL（完整）
            sds_zb: 所得税文件URL-主表
            sds_fb1: 所得税文件URL-附一
            sds_fb2: 所得税文件URL-附二
            sds_fb3: 所得税文件URL-附三
            cb: 财务报表文件URL（完整）
            cb_zcfz: 财报文件URL-资产负债
            cb_lr: 财报文件URL-利润
            cb_xjll: 财报文件URL-现金流量

        Returns:
            上传结果
        """
        # 使用远程签名接口获取签名
        private_key = os.getenv('CHASHUIBAO_BUSINESS_RISK_PRIVATE_KEY', '')

        # 构建远程签名请求参数
        sign_params = {
            'thirdPartyId': self.business_risk_third_party_id,
            'privateKey': private_key,
            'orderNo': report_no,
        }

        # 获取远程签名
        sign_response = await self._request('GET', '/openapi/csb/ObtainCiphertext', params=sign_params)

        # 检查响应（查税宝 API 返回 '0' 或 0 表示成功）
        sign_code = sign_response.get('code')
        if str(sign_code) != '0':
            error_msg = sign_response.get('message', '获取签名失败')
            logger.error(f"获取远程签名失败: code={sign_code}, message={error_msg}")
            raise Exception(error_msg)

        sign = sign_response.get('data', {}).get('sign', '')
        if not sign:
            raise Exception("服务端返回的签名为空")

        # 构建请求参数
        data = {
            'thirdPartyId': self.business_risk_third_party_id,
            'firmName': firm_name,
            'year': year,
            'quarter': quarter,
            'phone': phone,
            'taxpayerNo': taxpayer_no,
            'reportNo': report_no,
            'accountingCriterionId': accounting_criterion_id,
            'taxpayerType': taxpayer_type,
            'taxpayerName': taxpayer_name,
            'zzsFileBs': zzs_file_bs,
            'sdsFileBs': sds_file_bs,
            'cbFileBs': cb_file_bs,
            'sign': sign,
        }

        # 添加可选的增值税文件 URL
        if zzs:
            data['zzs'] = zzs
        if zzs_zb:
            data['zzsZb'] = zzs_zb
        if zzs_fb1:
            data['zzsFb1'] = zzs_fb1
        if zzs_fb2:
            data['zzsFb2'] = zzs_fb2
        if zzs_fb3:
            data['zzsFb3'] = zzs_fb3
        if zzs_fb4:
            data['zzsFb4'] = zzs_fb4
        if zzs_jmmx:
            data['zzsJmmx'] = zzs_jmmx

        # 添加可选的所得税文件 URL
        if sds:
            data['sds'] = sds
        if sds_zb:
            data['sdsZb'] = sds_zb
        if sds_fb1:
            data['sdsFb1'] = sds_fb1
        if sds_fb2:
            data['sdsFb2'] = sds_fb2
        if sds_fb3:
            data['sdsFb3'] = sds_fb3

        # 添加可选的财务报表文件 URL
        if cb:
            data['cb'] = cb
        if cb_zcfz:
            data['cbZcfz'] = cb_zcfz
        if cb_lr:
            data['cbLr'] = cb_lr
        if cb_xjll:
            data['cbXjll'] = cb_xjll

        logger.info(f"请求上传报表: report_no={report_no}, firm_name={firm_name}")

        # 发送请求
        response = await self._request('POST', '/openapi/uploadReportV2', data=data)

        # 检查响应
        if response.get('code') == '0':
            logger.info(f"上传报表成功: {report_no}")
            return {'success': True, 'message': response.get('message', '上传成功')}
        else:
            error_msg = response.get('message', '上传报表失败')
            logger.error(f"上传报表失败: {error_msg}")
            raise Exception(error_msg)

    async def get_report_data(self, report_no: str) -> Dict[str, Any]:
        """获取指标报告数据

        Args:
            report_no: 报告编号（上传报表接口传的报告编号/授权连接接口返回的orderNo）

        Returns:
            报告数据
        """
        # 使用远程签名接口获取签名
        private_key = os.getenv('CHASHUIBAO_BUSINESS_RISK_PRIVATE_KEY', '')

        # 构建远程签名请求参数
        sign_params = {
            'thirdPartyId': self.business_risk_third_party_id,
            'privateKey': private_key,
            'orderNo': report_no,
        }

        # 获取远程签名
        sign_response = await self._request('GET', '/openapi/csb/ObtainCiphertext', params=sign_params)

        # 检查响应（查税宝 API 返回 '0' 或 0 表示成功）
        sign_code = sign_response.get('code')
        if str(sign_code) != '0':
            error_msg = sign_response.get('message', '获取签名失败')
            logger.error(f"获取远程签名失败: code={sign_code}, message={error_msg}")
            raise Exception(error_msg)

        sign = sign_response.get('data', {}).get('sign', '')
        if not sign:
            raise Exception("服务端返回的签名为空")

        # 构建请求参数
        params = {
            'reportNo': report_no,
            'thirdPartyId': self.business_risk_third_party_id,
            'sign': sign,
        }

        logger.info(f"请求获取报告数据: report_no={report_no}")

        # 发送请求
        response = await self._request('GET', '/openapi/getReportDataV2', params=params)

        # 检查响应
        if response.get('code') == '0':
            logger.info(f"获取报告数据成功: {report_no}")
            return response.get('data', {})
        else:
            error_msg = response.get('message', '获取报告数据失败')
            logger.error(f"获取报告数据失败: {error_msg}")
            raise Exception(error_msg)

    def verify_notify_signature(self, params: Dict[str, Any], signature: str, public_key: str) -> bool:
        """验证回调通知签名

        Args:
            params: 回调参数
            signature: 签名
            public_key: 查税宝公钥

        Returns:
            验签是否成功
        """
        from app.services.chashuibao.sm2_signature import ChashuibaoSignature

        try:
            return ChashuibaoSignature.verify(params, signature, public_key)
        except Exception as e:
            logger.error(f"验签失败: {e}")
            return False

    async def get_taxpayer_no_by_name(self, ename: str) -> Optional[str]:
        """通过企业名称查询税号
        新接口无需 SM2 签名，直接传 thirdPartyId 和 eName
        
        Args:
            ename: 公司名称
            
        Returns:
            税号 (credit_no) 或 None
        """
        if not ename or len(ename) < 5:
            logger.warning(f"企业名称 '{ename}' 不符合查询条件(至少5个字)")
            return None

        params = {
            'thirdPartyId': self.third_party_id,
            'eName': ename
        }
        
        try:
            logger.info(f"开始通过企业名称查询税号: {ename}")
            response = await self._request('GET', '/openapi/obtainTaxNumBySearchName', params=params)
            
            # 把完整的原始响应打出来，方便排查对方接口到底返回了什么数据
            logger.info(f"查询税号完整响应: {response}")
            
            # 注意：查税宝的响应可能 code 是整数 0，也可能是字符串 '0'
            if str(response.get('code')) == '0':
                items = response.get('data', {}).get('items', [])
                if items and len(items) > 0:
                    credit_no = items[0].get('credit_no')
                    logger.info(f"查询税号成功: {ename} -> {credit_no}")
                    return credit_no
                else:
                    logger.warning(f"查询税号结果为空: {ename}")
                    return None
            else:
                error_msg = response.get('message', '查询税号失败')
                logger.error(f"查询税号失败: code={response.get('code')}, message={error_msg}")
                return None
        except Exception as e:
            logger.error(f"查询税号异常: {e}")
            return None

    async def generate_panoramic_report(
        self,
        user_id: str,
        taxpayer_no: Optional[str] = None,
        taxpayer_name: Optional[str] = None,
        report_logo: Optional[str] = None,
        watermark: Optional[str] = None,
        cover_url: Optional[str] = None,
        is_anonymity: Optional[int] = None,
    ) -> Dict[str, Any]:
        """生成全景报告

        Args:
            user_id: 用户ID（字符串格式）
            taxpayer_no: 纳税识别号（可选，与企业名称至少填一个）
            taxpayer_name: 公司名称（可选，与纳税人识别号至少填一个）
            report_logo: 封面logo URL
            watermark: 水印 URL
            cover_url: 封面 URL
            is_anonymity: 是否匿名（0-否，1-是）

        Returns:
            包含 id (数据库记录ID) 和 reportId (查税宝报告ID) 的字典
        """
        from app.services.chashuibao.panoramic_report_repository import panoramic_report_repository

        # 验证至少有一个参数
        if not taxpayer_no and not taxpayer_name:
            raise ValueError("纳税人识别号和企业名称至少需要填写一个")

        # 1. 先在数据库中创建记录（状态为 pending）
        report_record_id = panoramic_report_repository.create_report({
            'user_id': user_id,
            'taxpayer_no': taxpayer_no or '',  # 如果为 None 则存空字符串
            'taxpayer_name': taxpayer_name or '',  # 如果为 None 则存空字符串
            'report_logo': report_logo,
            'watermark': watermark,
            'cover_url': cover_url,
            'is_anonymity': is_anonymity,
            'status': 'pending',
        })

        if not report_record_id:
            raise Exception("创建报告记录失败")

        logger.info(f"创建报告记录成功: id={report_record_id}, user_id={user_id}, taxpayer_name={taxpayer_name}")

        # 自动通过企业名称获取税号 (如果在第一步没拿到，更新数据库状态并抛错)
        if not taxpayer_no and taxpayer_name:
            try:
                taxpayer_no = await self.get_taxpayer_no_by_name(taxpayer_name)
                if not taxpayer_no:
                    error_msg = f"无法通过企业名称“{taxpayer_name}”获取到税号，请检查企业名称是否准确"
                    panoramic_report_repository.update_report_status(
                        id=report_record_id, 
                        status='failed', 
                        error_message=error_msg
                    )
                    raise ValueError(error_msg)
                
                # 获取到税号后，将记录的 taxpayer_no 更新到数据库中
                panoramic_report_repository.update_report_status(
                    id=report_record_id,
                    status='pending',
                    taxpayer_no=taxpayer_no
                )
            except Exception as e:
                # 捕获可能的查询异常(如502)，将记录标记为失败
                error_msg = f"查询税号失败: {str(e)}"
                panoramic_report_repository.update_report_status(
                    id=report_record_id, 
                    status='failed', 
                    error_message=error_msg
                )
                raise e

        try:
            # 2. 调用查税宝 API 生成报告
            private_key = os.getenv('CHASHUIBAO_PRIVATE_KEY', '')

            # 构建远程签名请求参数
            sign_params = {
                'thirdPartyId': self.third_party_id,
                'privateKey': private_key,
            }
            # 只传递有值的参数
            if taxpayer_no:
                sign_params['taxpayerNo'] = taxpayer_no

            # 获取远程签名
            sign_response = await self._request('GET', '/openapi/csb/ObtainCiphertext', params=sign_params)

            # 检查响应（查税宝 API 返回 '0' 或 0 表示成功）
            sign_code = sign_response.get('code')
            if str(sign_code) != '0':
                error_msg = sign_response.get('message', '获取签名失败')
                logger.error(f"获取远程签名失败: code={sign_code}, message={error_msg}")
                # 更新数据库状态为失败
                panoramic_report_repository.update_report_status(
                    id=report_record_id, status='failed', error_message=error_msg
                )
                raise Exception(error_msg)

            sign = sign_response.get('data', {}).get('sign', '')
            if not sign:
                error_msg = "服务端返回的签名为空"
                panoramic_report_repository.update_report_status(
                    id=report_record_id, status='failed', error_message=error_msg
                )
                raise Exception(error_msg)

            # 构建请求参数
            params = {
                'thirdPartyId': self.third_party_id,
                'sign': sign,
            }
            # 只传递有值的参数
            if taxpayer_no:
                params['taxpayerNo'] = taxpayer_no
            if taxpayer_name:
                params['taxpayerName'] = taxpayer_name

            # 添加可选参数
            if report_logo:
                params['reportLogo'] = report_logo
            if watermark:
                params['watermark'] = watermark
            if cover_url:
                params['coverUrl'] = cover_url
            if is_anonymity is not None:
                params['isAnonymity'] = is_anonymity

            logger.info(f"请求生成全景报告: taxpayer_name={taxpayer_name}, taxpayer_no={taxpayer_no}")

            # 发送请求
            response = await self._request('GET', '/openapi/generatePanoramicReportV2', params=params)

            # 记录完整响应用于调试
            logger.info(f"查税宝 API 响应: code={response.get('code')}, message={response.get('message')}, data={response.get('data')}")

            # 检查响应（查税宝 API 返回 '0' 或 0 表示成功）
            response_code = response.get('code')
            if str(response_code) == '0':
                chashuibao_report_id = response.get('data', {}).get('reportId')
                if not chashuibao_report_id:
                    error_msg = "查税宝 API 返回成功但未提供 reportId"
                    logger.error(f"{error_msg}，完整响应: {response}")
                    panoramic_report_repository.update_report_status(
                        id=report_record_id, status='failed', error_message=error_msg
                    )
                    raise Exception(error_msg)

                # 3. 更新数据库记录，保存查税宝报告ID
                panoramic_report_repository.update_report_status(
                    id=report_record_id, status='pending', report_id=chashuibao_report_id
                )

                logger.info(f"生成全景报告请求成功: reportId={chashuibao_report_id}, id={report_record_id}")
                return {
                    'id': report_record_id,
                    'report_id': chashuibao_report_id
                }
            else:
                error_msg = response.get('message', '生成全景报告失败')
                logger.error(f"生成全景报告失败: code={response_code}, message={error_msg}")
                # 更新数据库状态为失败
                panoramic_report_repository.update_report_status(
                    id=report_record_id, status='failed', error_message=error_msg
                )
                raise Exception(error_msg)

        except Exception as e:
            # 发生异常时更新数据库状态为失败
            if "创建报告记录失败" not in str(e):
                panoramic_report_repository.update_report_status(
                    id=report_record_id, status='failed', error_message=str(e)
                )
            raise

    async def get_panoramic_report_data(self, report_id: int) -> Dict[str, Any]:
        """获取全景报告数据

        Args:
            report_id: 报告id（生成全景报告返回的reportId）

        Returns:
            全景报告数据
        """
        # 使用远程签名接口获取签名
        private_key = os.getenv('CHASHUIBAO_PRIVATE_KEY', '')

        # 构建远程签名请求参数
        sign_params = {
            'thirdPartyId': self.third_party_id,
            'privateKey': private_key,
            'reportId': str(report_id),
        }

        # 获取远程签名
        sign_response = await self._request('GET', '/openapi/csb/ObtainCiphertext', params=sign_params)

        # 检查响应（查税宝 API 返回 '0' 或 0 表示成功）
        sign_code = sign_response.get('code')
        if str(sign_code) != '0':
            error_msg = sign_response.get('message', '获取签名失败')
            logger.error(f"获取远程签名失败: code={sign_code}, message={error_msg}")
            raise Exception(error_msg)

        sign = sign_response.get('data', {}).get('sign', '')
        if not sign:
            raise Exception("服务端返回的签名为空")

        # 构建请求参数
        params = {
            'reportId': report_id,
            'thirdPartyId': self.third_party_id,
            'sign': sign,
        }

        logger.info(f"请求获取全景报告数据: reportId={report_id}")

        # 发送请求
        response = await self._request('GET', '/openapi/getPanoramicReportData', params=params)

        # 记录响应用于调试
        logger.info(f"查税宝 API 响应: code={response.get('code')}, message={response.get('message')}")

        # 检查响应（查税宝 API 返回 '0' 或 0 表示成功）
        response_code = response.get('code')
        if str(response_code) == '0':
            logger.info(f"获取全景报告数据成功: reportId={report_id}")
            return response.get('data', {})
        else:
            error_msg = response.get('message', '获取全景报告数据失败')
            logger.error(f"获取全景报告数据失败: code={response_code}, message={error_msg}")
            raise Exception(error_msg)

    def handle_panoramic_report_callback(
        self,
        chashuibao_report_id: int,
        state: str,
        report_type: str,
        url: Optional[str] = None,
    ) -> bool:
        """处理全景报告生成完成回调

        Args:
            chashuibao_report_id: 查税宝报告ID
            state: 成功状态（0-失败，1-成功）
            report_type: 报告类型（3-全景报告）
            url: 报告URL（可选）

        Returns:
            是否处理成功
        """
        from app.services.chashuibao.panoramic_report_repository import panoramic_report_repository

        try:
            # 根据查税宝报告ID找到数据库记录
            report = panoramic_report_repository.get_report_by_chashuibao_id(chashuibao_report_id)

            if not report:
                logger.warning(f"未找到查税宝报告ID对应的记录: {chashuibao_report_id}")
                return False

            # 确定状态
            status = 'success' if state == '1' else 'failed'

            # 如果成功且有URL，同时获取完整报告数据
            report_data = None
            if status == 'success' and url:
                # 可以在这里异步获取完整报告数据
                # 暂时只保存URL，完整数据在用户查询时获取
                pass

            # 更新数据库记录
            success = panoramic_report_repository.update_report_status(
                id=report['id'],
                status=status,
                report_url=url,
                report_data=report_data,
                callback_state=state,
            )

            if success:
                logger.info(
                    f"全景报告回调处理成功: chashuibao_report_id={chashuibao_report_id}, "
                    f"status={status}, url={url}"
                )
            return success

        except Exception as e:
            logger.error(f"处理全景报告回调失败: {e}")
            return False

    def get_panoramic_report_status(self, report_record_id: int) -> Optional[Dict[str, Any]]:
        """获取全景报告状态（用于前端轮询）

        Args:
            report_record_id: 数据库记录ID

        Returns:
            报告状态信息，如果记录不存在则返回 None
        """
        from app.services.chashuibao.panoramic_report_repository import panoramic_report_repository

        try:
            report = panoramic_report_repository.get_report_by_id(report_record_id)

            if not report:
                return None

            # 返回前端需要的状态信息
            return {
                'id': report['id'],
                'report_id': report['report_id'],
                'taxpayer_no': report['taxpayer_no'],
                'taxpayer_name': report['taxpayer_name'],
                'status': report['status'],
                'report_url': report['report_url'],
                'error_message': report['error_message'],
                'created_at': report['created_at'].isoformat() if report.get('created_at') else None,
                'completed_at': report['completed_at'].isoformat() if report.get('completed_at') else None,
                # 如果状态是成功且有完整数据，也返回
                'has_data': bool(report.get('report_data')),
            }

        except Exception as e:
            logger.error(f"获取全景报告状态失败: {e}")
            return None


# 创建全局服务实例
chashuibao_service = ChashuibaoService()
