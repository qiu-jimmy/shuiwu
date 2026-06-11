"""
企查查 API Tool
用于查询企业税务信息、统一社会信用代码等
"""
import hashlib
import time
import httpx
from typing import Optional, Dict, Any
from urllib.parse import quote

from app.infra.logging_config import get_logger

logger = get_logger("app.agno.tools.qichacha")


class QichachaTool:
    """企查查 API 工具类"""

    def __init__(self):
        """初始化工具"""
        self.api_key = None
        self.api_secret = None
        self.credit_code_url = "https://api.qichacha.com/ECICreditCode/GetCreditCodeNew"
        self.risk_scan_url = "https://api.qichacha.com/RiskControl/Scan"
        self._load_config()

    def _load_config(self):
        """从环境变量加载配置"""
        import os
        from dotenv import load_dotenv

        # 确保 .env 文件已加载
        load_dotenv()

        self.api_key = os.getenv("QICHACHA_API_KEY")
        self.api_secret = os.getenv("QICHACHA_API_SECRET")

        if not self.api_key or not self.api_secret:
            logger.warning("企查查 API 配置未找到,请检查环境变量 QICHACHA_API_KEY 和 QICHACHA_API_SECRET")
        else:
            logger.info("企查查 API 配置加载成功")

    def _generate_token(self, timestamp: int) -> str:
        """生成验证 Token

        Args:
            timestamp: Unix 时间戳

        Returns:
            MD5 加密后的 Token (32位大写)
        """
        # Token = MD5(key + Timespan + SecretKey)
        sign_string = f"{self.api_key}{timestamp}{self.api_secret}"
        md5_hash = hashlib.md5(sign_string.encode('utf-8')).hexdigest()
        return md5_hash.upper()

    async def get_company_info(
        self,
        company_name: str,
        credit_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """查询企业信息

        Args:
            company_name: 企业名称
            credit_code: 统一社会信用代码(可选,用于精确匹配)

        Returns:
            企业信息字典,包含:
            - Name: 企业名称
            - CreditCode: 统一社会信用代码
            - EconKind: 企业类型
            - Status: 企业状态
            - Address: 地址
            - Tel: 联系电话
            - Bank: 开户行
            - BankAccount: 开户行账号
        """
        if not company_name:
            raise ValueError("企业名称不能为空")

        if not self.api_key or not self.api_secret:
            raise ValueError("企查查 API 配置缺失,无法查询企业信息")

        # 生成时间戳(精确到秒)
        timestamp = int(time.time())

        # 生成 Token
        token = self._generate_token(timestamp)

        # URL 编码企业名称
        encoded_keyword = quote(company_name)

        # 构建请求 URL
        url = f"{self.credit_code_url}?key={self.api_key}&keyWord={encoded_keyword}"

        # 设置请求头
        headers = {
            "Token": token,
            "Timespan": str(timestamp),
            "Content-Type": "application/json"
        }

        logger.info(f"查询企业信息: {company_name}")

        try:
            # 发送 HTTP 请求
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()

                data = response.json()

                # 检查响应状态
                if data.get("Status") == "200":
                    result = data.get("Result", {})
                    logger.info(f"成功查询到企业信息: {result.get('Name')}")
                    return result
                else:
                    error_msg = data.get("Message", "未知错误")
                    logger.error(f"企查查 API 返回错误: {error_msg}")
                    raise Exception(f"API 查询失败: {error_msg}")

        except httpx.HTTPError as e:
            logger.error(f"HTTP 请求失败: {e}")
            raise Exception(f"网络请求失败: {str(e)}")
        except Exception as e:
            logger.error(f"查询企业信息失败: {e}")
            raise

    def format_company_info(self, company_info: Dict[str, Any]) -> str:
        """将企业信息格式化为 Markdown 文本

        Args:
            company_info: 企业信息字典

        Returns:
            格式化的 Markdown 文本
        """
        if not company_info:
            return "未查询到企业信息"

        lines = [
            "## 企业基本信息",
            "",
            f"- **企业名称**: {company_info.get('Name', '未知')}",
            f"- **统一社会信用代码**: {company_info.get('CreditCode', '未知')}",
            f"- **企业类型**: {company_info.get('EconKind', '未知')}",
            f"- **企业状态**: {company_info.get('Status', '未知')}",
            f"- **注册地址**: {company_info.get('Address', '未知')}",
            f"- **联系电话**: {company_info.get('Tel', '未知')}",
        ]

        # 银行信息可能不存在或脱敏
        if company_info.get('Bank') and company_info.get('Bank') != 'XXXXXXXXX':
            lines.append(f"- **开户行**: {company_info.get('Bank', '未知')}")
        if company_info.get('BankAccount') and company_info.get('BankAccount') != 'XXXXXX':
            lines.append(f"- **银行账号**: {company_info.get('BankAccount', '未知')}")

        lines.append("")

        return "\n".join(lines)

    async def get_risk_scan(
        self,
        search_key: str
    ) -> Dict[str, Any]:
        """综合风险排查

        Args:
            search_key: 搜索关键词(企业名称或统一社会信用代码)

        Returns:
            企业全面信息字典,包含:
            - 基本信息: Name, CreditCode, OperName, Status, StartDate等
            - 风险信息: ShiXin(失信), ZhiXing(被执行), AdminPenalty(行政处罚)等
            - 经营信息: PartnerList(股东), EmployeeList(人员), InvestmentList(投资)等
        """
        if not search_key:
            raise ValueError("搜索关键词不能为空")

        if not self.api_key or not self.api_secret:
            raise ValueError("企查查 API 配置缺失,无法查询风险信息")

        # 生成时间戳(精确到秒)
        timestamp = int(time.time())

        # 生成 Token
        token = self._generate_token(timestamp)

        # URL 编码搜索关键词
        encoded_keyword = quote(search_key)

        # 构建请求 URL
        url = f"{self.risk_scan_url}?key={self.api_key}&searchKey={encoded_keyword}"

        # 设置请求头
        headers = {
            "Token": token,
            "Timespan": str(timestamp),
            "Content-Type": "application/json"
        }

        logger.info(f"综合风险排查: {search_key}")

        try:
            # 发送 HTTP 请求
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()

                data = response.json()

                # 检查响应状态
                if data.get("Status") == "200":
                    result = data.get("Result", {})
                    company_data = result.get("Data", {})
                    logger.info(f"成功查询到企业风险信息: {company_data.get('Name')}")
                    return company_data
                else:
                    error_msg = data.get("Message", "未知错误")
                    logger.error(f"企查查 API 返回错误: {error_msg}")
                    raise Exception(f"API 查询失败: {error_msg}")

        except httpx.HTTPError as e:
            logger.error(f"HTTP 请求失败: {e}")
            raise Exception(f"网络请求失败: {str(e)}")
        except Exception as e:
            logger.error(f"查询风险信息失败: {e}")
            raise

    def format_risk_scan_info(self, risk_data: Dict[str, Any]) -> str:
        """将风险排查数据格式化为 Markdown 文本

        Args:
            risk_data: 风险排查数据字典

        Returns:
            格式化的 Markdown 文本
        """
        if not risk_data:
            return "未查询到企业风险信息"

        lines = []

        # 1. 基本信息
        lines.append("## 一、企业基本信息")
        lines.append("")
        lines.append(f"- **企业名称**: {risk_data.get('Name', '未知')}")
        lines.append(f"- **统一社会信用代码**: {risk_data.get('CreditCode', '未知')}")
        lines.append(f"- **法定代表人**: {risk_data.get('OperName', '未知')}")
        lines.append(f"- **登记状态**: {risk_data.get('Status', '未知')}")
        lines.append(f"- **成立日期**: {risk_data.get('StartDate', '未知')}")
        lines.append(f"- **注册资本**: {risk_data.get('RegistCapi', '未知')}")
        lines.append(f"- **实缴资本**: {risk_data.get('RealCapi', '未知')}")
        lines.append(f"- **企业类型**: {risk_data.get('EconKind', '未知')}")
        lines.append(f"- **纳税人资质**: {risk_data.get('TaxpayerType', '未知')}")
        lines.append(f"- **人员规模**: {risk_data.get('PersonScope', '未知')}")
        lines.append(f"- **参保人数**: {risk_data.get('InsuredCount', '未知')}")
        lines.append(f"- **所属地区**: {risk_data.get('Area', {}).get('Province', '')} {risk_data.get('Area', {}).get('City', '')}")
        lines.append(f"- **注册地址**: {risk_data.get('Address', '未知')}")
        lines.append("")

        # 2. 行业信息
        industry = risk_data.get('Industry', {})
        if industry:
            lines.append("## 二、行业信息")
            lines.append("")
            lines.append(f"- **行业门类**: {industry.get('Industry', '未知')}")
            lines.append(f"- **行业大类**: {industry.get('SubIndustry', '未知')}")
            lines.append(f"- **行业中类**: {industry.get('MiddleCategory', '未知')}")
            lines.append(f"- **行业小类**: {industry.get('SmallCategory', '未知')}")
            lines.append("")

        # 3. 经营范围
        scope = risk_data.get('Scope', '')
        if scope:
            lines.append("## 三、经营范围")
            lines.append("")
            lines.append(scope)
            lines.append("")

        # 4. 风险信息汇总
        lines.append("## 四、风险信息汇总")
        lines.append("")

        # 失信被执行人
        shixin = risk_data.get('ShiXin', {})
        if shixin and shixin.get('TotalCount', '0') != '0':
            lines.append(f"### 4.1 失信被执行人")
            lines.append("")
            lines.append(f"- **总条目**: {shixin.get('TotalCount', '0')}")
            lines.append(f"- **涉案总金额**: {shixin.get('TotalAmount', '0')} 万元")
            lines.append("")

        # 被执行人
        zhixing = risk_data.get('ZhiXing', {})
        if zhixing and zhixing.get('TotalCount', '0') != '0':
            lines.append(f"### 4.2 被执行人")
            lines.append("")
            lines.append(f"- **总条目**: {zhixing.get('TotalCount', '0')}")
            lines.append(f"- **被执行总金额**: {zhixing.get('TotalAmount', '0')} 万元")
            lines.append("")

        # 行政处罚
        admin_penalty = risk_data.get('AdminPenalty', {})
        if admin_penalty and admin_penalty.get('TotalCount', '0') != '0':
            lines.append(f"### 4.3 行政处罚")
            lines.append("")
            lines.append(f"- **总条目**: {admin_penalty.get('TotalCount', '0')}")
            lines.append(f"- **罚款总金额**: {admin_penalty.get('TotalAmount', '0')} 万元")
            lines.append("")

        # 经营异常
        exception = risk_data.get('Exception', {})
        if exception and exception.get('TotalCount', '0') != '0':
            lines.append(f"### 4.4 经营异常")
            lines.append("")
            lines.append(f"- **总条目**: {exception.get('TotalCount', '0')}")
            lines.append("")

        # 股权出质
        equity_pledge = risk_data.get('EquityPledge', {})
        if equity_pledge and equity_pledge.get('TotalCount', '0') != '0':
            lines.append(f"### 4.5 股权出质")
            lines.append("")
            lines.append(f"- **总条目**: {equity_pledge.get('TotalCount', '0')}")
            lines.append("")

        # 股权冻结
        equity_freeze = risk_data.get('EquityFreeze', {})
        if equity_freeze and equity_freeze.get('TotalCount', '0') != '0':
            lines.append(f"### 4.6 股权冻结")
            lines.append("")
            lines.append(f"- **总条目**: {equity_freeze.get('TotalCount', '0')}")
            lines.append("")

        # 限制高消费
        sumptuary = risk_data.get('Sumptuary', {})
        if sumptuary and sumptuary.get('TotalCount', '0') != '0':
            lines.append(f"### 4.7 限制高消费")
            lines.append("")
            lines.append(f"- **总条目**: {sumptuary.get('TotalCount', '0')}")
            lines.append(f"- **涉案总金额**: {sumptuary.get('TotalAmount', '0')} 万元")
            lines.append("")

        # 5. 股东信息(最多显示前5个)
        partners = risk_data.get('PartnerList', [])
        if partners:
            lines.append("## 五、股东信息")
            lines.append("")
            for i, partner in enumerate(partners[:5], 1):
                lines.append(f"{i}. **{partner.get('StockName', '未知')}**")
                lines.append(f"   - 持股比例: {partner.get('StockPercent', '未知')}")
                lines.append(f"   - 认缴出资额: {partner.get('ShouldCapi', '未知')} {partner.get('SubscribedCapitalUnit', '')}")
            lines.append("")

        # 6. 主要人员(最多显示前5个)
        employees = risk_data.get('EmployeeList', [])
        if employees:
            lines.append("## 六、主要人员")
            lines.append("")
            for i, employee in enumerate(employees[:5], 1):
                lines.append(f"{i}. **{employee.get('Name', '未知')}** - {employee.get('Job', '未知')}")
            lines.append("")

        # 7. 对外投资(最多显示前3个)
        investments = risk_data.get('InvestmentList', [])
        if investments:
            lines.append("## 七、对外投资")
            lines.append("")
            for i, inv in enumerate(investments[:3], 1):
                lines.append(f"{i}. **{inv.get('Name', '未知')}**")
                lines.append(f"   - 持股比例: {inv.get('FundedRatio', '未知')}")
                lines.append(f"   - 认缴出资额: {inv.get('ShouldCapi', '未知')}")
                lines.append(f"   - 状态: {inv.get('Status', '未知')}")
            lines.append("")

        # 8. 财务信息
        financial = risk_data.get('FinancialInformation', {})
        if financial:
            lines.append("## 八、财务信息")
            lines.append("")
            lines.append(f"- **科目名称**: {financial.get('AccountTitle', '未知')}")
            lines.append(f"- **数额**: {financial.get('Amount', '未知')}")
            lines.append(f"- **年份**: {financial.get('Year', '未知')}")
            lines.append("")

        # 9. 变更信息(最多显示前3条)
        changes = risk_data.get('ChangeList', [])
        if changes:
            lines.append("## 九、变更信息(最近3条)")
            lines.append("")
            for i, change in enumerate(changes[:3], 1):
                lines.append(f"{i}. **{change.get('ProjectName', '未知')}** ({change.get('ChangeDate', '未知')})")
                lines.append(f"   - 变更项目: {change.get('ChangeSubject', '未知')}")
            lines.append("")

        return "\n".join(lines)


# 创建全局工具实例
qichacha_tool = QichachaTool()
