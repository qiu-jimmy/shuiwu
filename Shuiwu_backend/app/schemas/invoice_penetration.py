"""
发票穿透报告相关的 Schema 定义
"""
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field


# ============ 请求 Schemas ============

class InvoiceAuthorizationRequest(BaseModel):
    """发票穿透获取授权链接请求"""

    # 注意：thirdPartyId 和 sign 由后端自动处理，前端不需要传递
    taxpayer_id: str = Field(..., description="纳税人识别号（明文，后端会加密）", alias="taxpayerId")
    company_name: str = Field(..., description="企业名称（明文，后端会加密）", alias="companyName")
    report_type: str = Field(default="1", description="报告类型 1：发票穿透", alias="reportType")
    cburl: str = Field(..., description="授权完成回调页面", alias="cburl")
    begin_date: Optional[str] = Field(None, description="开始时间（例202309）", alias="beginDate")
    over_date: Optional[str] = Field(None, description="结束时间（例202408）", alias="overDate")
    is_anonymity: Optional[int] = Field(None, description="是否匿名（0-否，1-是）", alias="isAnonymity")
    report_logo: Optional[str] = Field(None, description="封面logo(网络地址url)", alias="reportLogo")
    watermark: Optional[str] = Field(None, description="水印(网络地址url)")
    cover_url: Optional[str] = Field(None, description="封面(网络地址url)", alias="coverUrl")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "taxpayerId": "91330382556157804A",
                "companyName": "乐清市琪源电气科技有限公司",
                "reportType": "1",
                "cburl": "https://example.com/callback",
                "beginDate": "202309",
                "overDate": "202408"
            }
        }


class InvoiceReportNotifyData(BaseModel):
    """发票穿透报告生成完成通知数据"""

    order_no: Optional[str] = Field(None, description="订单号", alias="orderNo")
    state: Union[str, int] = Field(..., description="成功状态：0-失败，1-成功")
    report_type: Union[str, int] = Field(..., description="报告类型：1-发票穿透", alias="reportType")

    class Config:
        populate_by_name = True


class InvoiceGetReportRequest(BaseModel):
    """获取发票穿透报告数据请求（查询参数，不用 Body）"""

    # 注意：此请求使用 GET 方法，参数通过 query string 传递
    # thirdPartyId 和 sign 由后端自动处理
    taxpayer_id: str = Field(..., description="纳税人识别号（明文）", alias="taxpayerId")
    company_name: str = Field(..., description="企业名称（明文）", alias="companyName")
    order_no: str = Field(..., description="订单号", alias="orderNo")
    data_type: Optional[int] = Field(None, description="数据类型：1-数据，2-报告url", alias="dataType")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "taxpayerId": "91330382556157804A",
                "companyName": "乐清市琪源电气科技有限公司",
                "orderNo": "S_xxxxx",
                "dataType": 1
            }
        }


# ============ 响应 Schemas ============

class InvoiceAuthorizationResponse(BaseModel):
    """获取授权链接响应"""

    order_no: str = Field(..., description="订单号（唯一标识）", alias="orderNo")
    initial_url: str = Field(..., description="授权链接（H5链接）", alias="initialUrl")

    class Config:
        populate_by_name = True


# ============ 报告数据 Schemas ============

class InvoiceFirmInfo(BaseModel):
    """企业基本信息"""
    taxpayer_name: Optional[str] = Field(None, description="企业名称", alias="taxpayerName")
    taxpayer_no: Optional[str] = Field(None, description="企业税号", alias="taxpayerNo")
    address: Optional[str] = Field(None, description="公司地址")
    industry: Optional[str] = Field(None, description="行业")
    nszg: Optional[str] = Field(None, description="纳税人类型")
    regist_capi: Optional[str] = Field(None, description="注册资本", alias="registCapi")
    actual_capi: Optional[str] = Field(None, description="实收资本", alias="actualCapi")
    start_date: Optional[str] = Field(None, description="成立日期", alias="startDate")
    check_date: Optional[str] = Field(None, description="核准日期", alias="checkDate")
    ent_status: Optional[str] = Field(None, description="经营状况", alias="entStatus")
    scope: Optional[str] = Field(None, description="经营范围")

    class Config:
        populate_by_name = True


class InvoiceReportData(BaseModel):
    """发票穿透报告数据"""

    # 企业基本信息
    invoice_firm_info_all_map: Optional[Dict[str, Any]] = Field(None, alias="invoiceFirmInfoAllMap")
    invoice_firm_infos: Optional[List] = Field(None, alias="invoiceFirmInfos")
    invoice_risk_items: Optional[List] = Field(None, alias="invoiceRiskItems")

    # 发票分析
    invoice_enterprise_all_map: Optional[Dict[str, Any]] = Field(None, alias="invoiceEnterpriseAllMap")
    invoice_enterprise_net_to_compares: Optional[List] = Field(None, alias="invoiceEnterpriseNetToCompares")

    # 财务风险评估
    invoice_financial_analysis_all_map: Optional[Dict[str, Any]] = Field(None, alias="invoiceFinancialAnalysisAllMap")
    invoice_financial_analysis_markets: Optional[List] = Field(None, alias="invoiceFinancialAnalysisMarkets")

    # 税务风险评估
    invoice_tax_risk_assessment_all_map: Optional[Dict[str, Any]] = Field(None, alias="invoiceTaxRiskAssessmentAllMap")
    invoice_tax_risk_assessment_paid_lists: Optional[List] = Field(None, alias="invoiceTaxRiskAssessmentPaidLists")

    # 财税票综合风险评估
    invoice_integrated_risk_assessment_all_map: Optional[Dict[str, Any]] = Field(None, alias="invoiceIntegratedRiskAssessmentAllMap")

    class Config:
        populate_by_name = True


class InvoiceReportResponse(BaseModel):
    """获取报告数据响应"""

    code: str = Field(..., description="处理结果：0-成功，1-失败")
    message: str = Field(..., description="返回信息描述")
    data: Optional[Any] = Field(None, description="报告数据或报告URL")

    class Config:
        populate_by_name = True
