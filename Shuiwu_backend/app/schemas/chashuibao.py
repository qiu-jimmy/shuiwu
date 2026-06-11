"""
查税宝经营风险报告相关的 Schema 定义
"""
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator, model_validator


# ============ 请求 Schemas ============


class QuarterSection(BaseModel):
    """年度-季度选择项"""
    year: str = Field(..., description="年度，如 2025")
    quarter: str = Field(..., description="季度（1、2、3、4）")


class ChashuibaoAuthorizationRequest(BaseModel):
    """获取授权链接请求"""

    third_party_id: Optional[str] = Field(None, description="令牌（由后端自动填充）", alias="thirdPartyId")
    sign: Optional[str] = Field(None, description="签名（由后端自动生成）")
    taxpayer_id: str = Field(..., description="纳税人识别号（加密）", alias="taxpayerId")
    company_name: str = Field(..., description="企业名称（加密）", alias="companyName")
    report_type: str = Field(default="2", description="报告类型 2：经营风险报告", alias="reportType")
    cburl: str = Field(..., description="授权完成回调页面", alias="cburl")
    quarter_section: Optional[List[QuarterSection]] = Field(None, description="年度季度多选，如 [{year:'2025',quarter:'1'},{year:'2025',quarter:'2'}]", alias="quarterSection")
    report_logo: Optional[str] = Field(None, description="封面logo(网络地址url)", alias="reportLogo")
    watermark: Optional[str] = Field(None, description="水印(网络地址url)")
    cover_url: Optional[str] = Field(None, description="封面(网络地址url)", alias="coverUrl")
    is_anonymity: Optional[int] = Field(None, description="是否匿名（0-否，1-是）", alias="isAnonymity")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "taxpayerId": "encrypted_taxpayer_id",
                "companyName": "encrypted_company_name",
                "reportType": "2",
                "cburl": "https://example.com/callback",
                "quarterSection": [
                    {"year": "2025", "quarter": "1"},
                    {"year": "2025", "quarter": "2"}
                ]
            }
        }


class ChashuibaoUploadReportRequest(BaseModel):
    """手动上传报表请求"""

    # 文件标识
    zzs_file_bs: str = Field(..., description="增值税文件单一整体标识(1单文件0多文件)", alias="zzsFileBs")
    sds_file_bs: str = Field(..., description="所得税文件单一整体标识", alias="sdsFileBs")
    cb_file_bs: str = Field(..., description="财报文件单一整体标识", alias="cbFileBs")

    # 增值税文件 URL
    zzs: Optional[str] = Field(None, description="增值税文件URL（完整，单文件）")
    zzs_zb: Optional[str] = Field(None, description="增值税文件URL-主表(多文件）", alias="zzsZb")
    zzs_fb1: Optional[str] = Field(None, description="增值税文件URL-附一", alias="zzsFb1")
    zzs_fb2: Optional[str] = Field(None, description="增值税文件URL-附二", alias="zzsFb2")
    zzs_fb3: Optional[str] = Field(None, description="增值税文件URL-附三", alias="zzsFb3")
    zzs_fb4: Optional[str] = Field(None, description="增值税文件URL-附四", alias="zzsFb4")
    zzs_jmmx: Optional[str] = Field(None, description="增值税文件URL-减免明细", alias="zzsJmmx")

    # 所得税文件 URL
    sds: Optional[str] = Field(None, description="所得税文件URL（完整，单文件）")
    sds_zb: Optional[str] = Field(None, description="所得税文件URL-主表", alias="sdsZb")
    sds_fb1: Optional[str] = Field(None, description="所得税文件URL-附一", alias="sdsFb1")
    sds_fb2: Optional[str] = Field(None, description="所得税文件URL-附二", alias="sdsFb2")
    sds_fb3: Optional[str] = Field(None, description="所得税文件URL-附三", alias="sdsFb3")

    # 财务报表文件 URL
    cb: Optional[str] = Field(None, description="财务报表文件URL（完整，单文件）")
    cb_zcfz: Optional[str] = Field(None, description="财报文件URL-资产负债", alias="cbZcfz")
    cb_lr: Optional[str] = Field(None, description="财报文件URL-利润", alias="cbLr")
    cb_xjll: Optional[str] = Field(None, description="财报文件URL-现金流量", alias="cbXjll")

    # 基本信息
    firm_name: str = Field(..., description="企业名称", alias="firmName")
    year: str = Field(..., description="年（2019）")
    quarter: str = Field(..., description="季度（1、2、3、4）")
    phone: str = Field(..., description="用户手机号")
    taxpayer_no: str = Field(..., description="纳税人识别号", alias="taxpayerNo")
    report_no: str = Field(..., description="报告编号（唯一，长度：32）", alias="reportNo")
    accounting_criterion_id: str = Field(..., description="会计准则编码", alias="accountingCriterionId")
    taxpayer_type: str = Field(..., description="纳税人类型编码", alias="taxpayerType")
    taxpayer_name: str = Field(..., description="企业名称", alias="taxpayerName")
    third_party_id: str = Field(..., description="第三方 id", alias="thirdPartyId")
    sign: str = Field(..., description="签名")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "zzsFileBs": "1",
                "sdsFileBs": "1",
                "cbFileBs": "1",
                "zzs": "https://example.com/zzs.pdf",
                "sds": "https://example.com/sds.pdf",
                "cb": "https://example.com/cb.pdf",
                "firmName": "企业名称",
                "year": "2024",
                "quarter": "1",
                "phone": "13800138000",
                "taxpayerNo": "91330100MA2XXX00XX",
                "reportNo": "unique_report_no_32_chars",
                "accountingCriterionId": "101",
                "taxpayerType": "Y",
                "taxpayerName": "企业名称",
                "thirdPartyId": "your_token",
                "sign": "signature"
            }
        }


class ChashuibaoGetReportRequest(BaseModel):
    """获取指标报告数据请求"""

    report_no: str = Field(..., description="报告编号", alias="reportNo")
    third_party_id: str = Field(..., description="第三方 id", alias="thirdPartyId")
    sign: str = Field(..., description="签名")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "reportNo": "unique_report_no_32_chars",
                "thirdPartyId": "your_token",
                "sign": "signature"
            }
        }


# ============ 响应 Schemas ============

class ChashuibaoAuthorizationResponse(BaseModel):
    """获取授权链接响应"""

    order_no: str = Field(..., description="订单号（唯一标识）", alias="orderNo")
    initial_url: str = Field(..., description="授权链接（H5链接）", alias="initialUrl")

    class Config:
        populate_by_name = True


class ChashuibaoReportNotifyData(BaseModel):
    """报告生成完成通知数据"""

    order_no: Optional[str] = Field(None, description="订单号", alias="orderNo")
    state: str = Field(..., description="成功状态：0-失败，1-成功")
    report_type: str = Field(..., description="报告类型：2-经营报告", alias="reportType")

    class Config:
        populate_by_name = True


# ============ 报告数据响应 Schemas ============

class ChashuibaoFirmInfo(BaseModel):
    """企业概况"""

    paragraph: Optional[str] = Field(None, description="概况")
    taxpayer_name: Optional[str] = Field(None, description="企业名称", alias="taxpayerName")
    taxpayer_no: Optional[str] = Field(None, description="企业税号", alias="taxpayerNo")
    industry: Optional[str] = Field(None, description="行业")
    nszg: Optional[str] = Field(None, description="纳税人类型")
    regist_capi: Optional[str] = Field(None, description="注册资本", alias="registCapi")
    actual_capi: Optional[str] = Field(None, description="实收资本", alias="actualCapi")
    start_date: Optional[str] = Field(None, description="成立日期", alias="startDate")
    check_date: Optional[str] = Field(None, description="核准日期", alias="checkDate")
    address: Optional[str] = Field(None, description="公司地址")
    ent_status: Optional[str] = Field(None, description="经营状况", alias="entStatus")
    scope: Optional[str] = Field(None, description="经营范围")

    class Config:
        populate_by_name = True


class ChashuibaoRiskItem(BaseModel):
    """风险项"""

    xh: Optional[str] = Field(None, description="序号")
    jgmc: Optional[str] = Field(None, description="结构名称")
    zbmc: Optional[str] = Field(None, description="指标名称")
    fxts: Optional[str] = Field(None, description="风险提示")
    zbdy: Optional[str] = Field(None, description="指标定义")
    fxyd: Optional[str] = Field(None, description="风险应对")
    sfczfx: Optional[str] = Field(None, description="是否存在风险（N：否 Y：是）")
    fxz: Optional[str] = Field(None, description="分析值")
    hyckz: Optional[str] = Field(None, description="行业参考值")

    class Config:
        populate_by_name = True


class ChashuibaoTaxInfo(BaseModel):
    """税费信息"""

    bqje: Optional[str] = Field(None, description="本期数据")
    sqje: Optional[str] = Field(None, description="上期数据")
    mc: Optional[str] = Field(None, description="名称")

    class Config:
        populate_by_name = True


class ChashuibaoTaxAnalysis(BaseModel):
    """税（费）种核算风险事项分析"""

    xh: Optional[str] = Field(None, description="序号（1：增值税 2：企业所得税 3：附加税费）")
    fxts: Optional[str] = Field(None, description="风险提示")
    zbdy: Optional[str] = Field(None, description="指标定义")
    zbmc: Optional[str] = Field(None, description="指标名称")
    fxyd: Optional[str] = Field(None, description="风险应对")
    sfczfx: Optional[str] = Field(None, description="是否存在风险")

    class Config:
        populate_by_name = True


class ChashuibaoFinancialAnalysis(BaseModel):
    """财务状况分析"""

    xh: Optional[str] = Field(None, description="序号")
    jgmc: Optional[str] = Field(None, description="机构名称")
    jgfl: Optional[str] = Field(None, description="机构分类")
    fxts: Optional[str] = Field(None, description="风险提示")
    zbdy: Optional[str] = Field(None, description="指标定义")
    zbmc: Optional[str] = Field(None, description="指标名称")
    fxydfa: Optional[str] = Field(None, description="风险应对")
    sfczfx: Optional[str] = Field(None, description="是否存在风险")
    fxz: Optional[str] = Field(None, description="分析值")
    hyckz: Optional[str] = Field(None, description="行业参考值")

    class Config:
        populate_by_name = True


class ChashuibaoProfitItem(BaseModel):
    """利润表项目"""

    zbmc: Optional[str] = Field(None, description="指标名称")
    bqje: Optional[str] = Field(None, description="本期金额")
    bqbdl: Optional[str] = Field(None, description="本期变动率")
    bqzb: Optional[str] = Field(None, description="本期占总收入比重")
    sqje: Optional[str] = Field(None, description="上期金额")
    sqbdl: Optional[str] = Field(None, description="上期变动率")
    sqzb: Optional[str] = Field(None, description="上期占总收入比重")

    class Config:
        populate_by_name = True


class ChashuibaoCashFlowItem(BaseModel):
    """现金流量表项目"""

    zbmc: Optional[str] = Field(None, description="指标名称")
    bqje: Optional[str] = Field(None, description="金额")
    bqbdl: Optional[str] = Field(None, description="变动率")

    class Config:
        populate_by_name = True


class ChashuibaoBalanceSheetItem(BaseModel):
    """资产负债表项目"""

    zbmc: Optional[str] = Field(None, description="指标名称")
    bqje: Optional[str] = Field(None, description="本期金额")
    bqbdl: Optional[str] = Field(None, description="本期变动率")
    bqzb: Optional[str] = Field(None, description="本期占总资产比重")
    sqje: Optional[str] = Field(None, description="上期金额")
    sqbdl: Optional[str] = Field(None, description="上期变动率")
    sqzb: Optional[str] = Field(None, description="上期占总资产比重")

    class Config:
        populate_by_name = True


class ChashuibaoReportData(BaseModel):
    """经营风险报告数据"""

    # 企业概况
    firm_info: Optional[ChashuibaoFirmInfo] = Field(None, alias="firmInfo")

    # 风险列表
    fx_list: Optional[List[ChashuibaoRiskItem]] = Field(None, alias="fxList")

    # 申报纳税信息
    tax_info: Optional[Dict[str, Any]] = Field(None, description="申报纳税信息")
    zzssffdgc: Optional[List[ChashuibaoTaxInfo]] = Field(None, description="增值税税费负担构成")
    qysdssffdgc: Optional[List[ChashuibaoTaxInfo]] = Field(None, description="企业所得税税费负担构成")

    # 税（费）种核算风险事项分析
    szhsfxsxfx: Optional[List[ChashuibaoTaxAnalysis]] = Field(None, description="税（费）种核算风险事项分析")

    # 涉税财务核算风险事项分析
    sscwhsfxsxfx: Optional[List[ChashuibaoTaxAnalysis]] = Field(None, description="涉税财务核算风险事项分析")

    # 主要税（费）种税费负担率
    zysfzsffdl: Optional[List[ChashuibaoTaxInfo]] = Field(None, description="主要税（费）种税费负担率")

    # 财务基本信息
    financial_info: Optional[str] = Field(None, description="财务基本信息")

    # 财务状况分析
    cwzkfx: Optional[List[ChashuibaoFinancialAnalysis]] = Field(None, description="财务状况分析")

    # 利润表分析
    lrbfx: Optional[List[ChashuibaoProfitItem]] = Field(None, description="利润表分析")

    # 现金流量表分析
    xjll: Optional[List[ChashuibaoCashFlowItem]] = Field(None, description="现金流量表分析")

    # 资产负债表分析
    zcfzbfx: Optional[List[ChashuibaoBalanceSheetItem]] = Field(None, description="资产负债表分析")

    # 报告URL
    report_url: Optional[str] = Field(None, description="指标分析报告url", alias="reportUrl")
    financial_report: Optional[str] = Field(None, description="财务报表url", alias="financialReport")
    behavioural_guidance: Optional[str] = Field(None, description="行为辅导报告数据", alias="behaviouralGuidance")
    risk_num: Optional[str] = Field(None, description="风险数", alias="riskNum")
    zzs: Optional[str] = Field(None, description="增值税")
    sds: Optional[str] = Field(None, description="所得税")

    class Config:
        populate_by_name = True


class ChashuibaoReportResponse(BaseModel):
    """获取指标报告数据响应"""

    code: str = Field(..., description="处理结果：0-成功，1-失败")
    message: str = Field(..., description="返回信息描述")
    data: Optional[ChashuibaoReportData] = Field(None, description="报告数据")

    class Config:
        populate_by_name = True


# ============ 全景报告 Schemas ============

class ChashuibaoGeneratePanoramicRequest(BaseModel):
    """生成全景报告请求（客户端请求，签名由后端生成）"""

    taxpayer_no: Optional[str] = Field(None, description="纳税识别号", alias="taxpayerNo")
    taxpayer_name: Optional[str] = Field(None, description="公司名称", alias="taxpayerName")
    # 以下字段由后端自动生成，客户端无需提供
    third_party_id: Optional[str] = Field(None, description="第三方 id（后端自动生成）", alias="thirdPartyId")
    sign: Optional[str] = Field(None, description="签名（后端自动生成）")
    report_logo: Optional[str] = Field(None, description="封面logo(网络地址url)", alias="reportLogo")
    watermark: Optional[str] = Field(None, description="水印(网络地址url)")
    cover_url: Optional[str] = Field(None, description="封面(网络地址url)", alias="coverUrl")
    is_anonymity: Optional[int] = Field(None, description="是否匿名（0-否，1-是）", alias="isAnonymity")

    @model_validator(mode='after')
    def validate_at_least_one(self):
        """验证纳税人识别号和企业名称至少填一个"""
        if not self.taxpayer_no and not self.taxpayer_name:
            raise ValueError('纳税人识别号和企业名称至少需要填写一个')
        return self

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "taxpayerNo": "91330100MA2XXX00XX",
                "taxpayerName": "企业名称",
                "reportLogo": "https://example.com/logo.png",
                "watermark": "https://example.com/watermark.png",
                "coverUrl": "https://example.com/cover.png",
                "isAnonymity": 0
            }
        }


class ChashuibaoGeneratePanoramicResponse(BaseModel):
    """生成全景报告响应"""

    code: str = Field(..., description="0成功 1失败")
    message: str = Field(..., description="报文信息")
    data: Optional["ChashuibaoGeneratePanoramicData"] = Field(None, description="报告Id")

    class Config:
        populate_by_name = True


class ChashuibaoGeneratePanoramicData(BaseModel):
    """生成全景报告数据"""

    report_id: int = Field(..., description="报告Id", alias="reportId")

    class Config:
        populate_by_name = True


class ChashuibaoPanoramicNotifyData(BaseModel):
    """全景报告生成完成通知数据（查税宝主动调用）"""

    report_id: Union[str, int] = Field(..., description="报告id", alias="reportId")
    state: Union[str, int] = Field(..., description="成功状态，0——失败，1——成功")
    report_type: Union[str, int] = Field(..., description="报告类型  3；全景报告", alias="reportType")
    url: Optional[str] = Field(None, description="报告url")

    @field_validator('report_id', 'state', 'report_type', mode='before')
    @classmethod
    def convert_to_str(cls, v):
        """将输入值转换为字符串"""
        return str(v) if v is not None else None

    class Config:
        populate_by_name = True


class ChashuibaoGetPanoramicRequest(BaseModel):
    """获取全景报告数据请求"""

    report_id: int = Field(..., description="报告id", alias="reportId")
    third_party_id: str = Field(..., description="第三方 id", alias="thirdPartyId")
    sign: str = Field(..., description="签名(详见签名规则)")

    class Config:
        populate_by_name = True


class ChashuibaoGetPanoramicResponse(BaseModel):
    """获取全景报告数据响应"""

    code: str = Field(..., description="0成功 1失败")
    message: str = Field(..., description="报文信息")
    data: Optional["ChashuibaoPanoramicData"] = Field(None, description="全景报告数据")

    class Config:
        populate_by_name = True


# ============ 全景报告详细数据 Schemas ============

class ChashuibaoGeneItem(BaseModel):
    """企业基因"""
    gene: Optional[str] = Field(None, description="基因名称")


class ChashuibaoAddress(BaseModel):
    """地理位置"""
    province_name: Optional[str] = Field(None, description="省份名称", alias="provinceName")
    city_name: Optional[str] = Field(None, description="市名称", alias="cityName")
    area_name: Optional[str] = Field(None, description="区名称", alias="areaName")
    towns_name: Optional[str] = Field(None, description="乡镇名称", alias="townsName")
    street_name: Optional[str] = Field(None, description="街道名称", alias="streetName")
    district: Optional[str] = Field(None, description="商圈")
    physsical_address: Optional[str] = Field(None, description="实际地址", alias="physsicalAddress")
    loc_address: Optional[str] = Field(None, description="坐标地址", alias="locAddress")
    standard_address: Optional[str] = Field(None, description="标准地址", alias="standardAddress")
    address_level: Optional[str] = Field(None, description="地址级别", alias="addressLevel")
    street_direction: Optional[str] = Field(None, description="街道方向", alias="streetDirection")
    street_distance: Optional[str] = Field(None, description="街道距离", alias="streetDistance")


class ChashuibaoShareholder(BaseModel):
    """股东信息"""
    shareholder_name: Optional[str] = Field(None, description="股东名称", alias="shareholderName")
    shareholder_type: Optional[str] = Field(None, description="股东类型", alias="shareholderType")
    contribution_amount: Optional[str] = Field(None, description="认缴出资额(万元)", alias="contributionAmount")
    contribution_ratio: Optional[str] = Field(None, description="出资比例", alias="contributionRatio")
    contribution_time: Optional[str] = Field(None, description="出资日期", alias="contributionTime")
    enter_time: Optional[str] = Field(None, description="进入时间", alias="enterTime")
    exit_time: Optional[str] = Field(None, description="退出时间", alias="exitTime")
    hold_time: Optional[str] = Field(None, description="持股时长", alias="holdTime")
    status: Optional[int] = Field(None, description="股东状态 0-现有股东 1-退出股东")


class ChashuibaoPersonnel(BaseModel):
    """人员信息"""
    type: Optional[int] = Field(None, description="类型 0-董事会成员 1-监事会成员 2-其他人员")
    name: Optional[str] = Field(None, description="名称")
    position: Optional[str] = Field(None, description="职务")
    enter_time: Optional[str] = Field(None, description="进入时间", alias="enterTime")
    exit_time: Optional[str] = Field(None, description="退出时间", alias="exitTime")
    hold_time: Optional[str] = Field(None, description="任职时长", alias="holdTime")
    status: Optional[int] = Field(None, description="状态 0-在职 1-退出")


class ChashuibaoChange(BaseModel):
    """变更信息"""
    change_item: Optional[str] = Field(None, description="变更事项", alias="changeItem")
    old_content: Optional[str] = Field(None, description="变更前内容", alias="oldContent")
    new_content: Optional[str] = Field(None, description="变更后内容", alias="newContent")
    change_time: Optional[str] = Field(None, description="变更日期", alias="changeTime")


class ChashuibaoPledgeEquity(BaseModel):
    """股权出质"""
    register_num: Optional[str] = Field(None, description="登记编号", alias="registerNum")
    pledgor: Optional[str] = Field(None, description="出质人")
    certificate_num: Optional[str] = Field(None, description="证件号", alias="certificateNum")
    pledge_amount: Optional[str] = Field(None, description="出质股权数额", alias="pledgeAmount")
    pledgee: Optional[str] = Field(None, description="质权人")
    license_num: Optional[str] = Field(None, description="证照号", alias="licenseNum")
    register_pledging_time: Optional[str] = Field(None, description="质权出质设立登记日期", alias="registerPledgingTime")
    status: Optional[str] = Field(None, description="状态")
    public_time: Optional[str] = Field(None, description="公示日期", alias="publicTime")


class ChashuibaoChattelMortgage(BaseModel):
    """动产抵押"""
    register_num: Optional[str] = Field(None, description="登记编号", alias="registerNum")
    register_time: Optional[str] = Field(None, description="登记日期", alias="registerTime")
    register_authority: Optional[str] = Field(None, description="登记机关", alias="registerAuthority")
    secured_amount: Optional[str] = Field(None, description="被担保债权数额（万元）", alias="securedAmount")
    stauts: Optional[str] = Field(None, description="状态")
    public_time: Optional[str] = Field(None, description="公示日期", alias="publicTime")


class ChashuibaoLiquidation(BaseModel):
    """清算信息"""
    liquidation_principal: Optional[str] = Field(None, description="清算组负责人", alias="liquidationPrincipal")
    liquidation_member: Optional[str] = Field(None, description="清算组成员", alias="liquidationMember")


class ChashuibaoExamine(BaseModel):
    """抽查检查"""
    examine_authority: Optional[str] = Field(None, description="检查实施机关", alias="examineAuthority")
    examine_type: Optional[str] = Field(None, description="检查类型", alias="examineType")
    examine_time: Optional[str] = Field(None, description="检查日期", alias="examineTime")
    examine_result: Optional[str] = Field(None, description="检查结果", alias="examineResult")


class ChashuibaoJudicialAid(BaseModel):
    """司法协助"""
    person_name: Optional[str] = Field(None, description="检查实施机关", alias="personName")
    equity_amount: Optional[str] = Field(None, description="股权数额", alias="equityAmount")
    executive_court: Optional[str] = Field(None, description="执行法院", alias="executiveCourt")
    executive_num: Optional[str] = Field(None, description="执行通知书文号", alias="executiveNum")
    status: Optional[str] = Field(None, description="状态")


class ChashuibaoPenalty(BaseModel):
    """行政处罚"""
    penalty_num: Optional[str] = Field(None, description="检查实施机关", alias="penaltyNum")
    penalty_type: Optional[str] = Field(None, description="违法行为类型", alias="penaltyType")
    penalty_content: Optional[str] = Field(None, description="行政处罚内容", alias="penaltyContent")
    penalty_time: Optional[str] = Field(None, description="做出行政处罚决定日期", alias="penaltyTime")


class ChashuibaoAbnormalOperation(BaseModel):
    """经营异常"""
    enrol_time: Optional[str] = Field(None, description="检查实施机关", alias="enrolTime")
    enrol_cause: Optional[str] = Field(None, description="违法行为类型", alias="enrolCause")
    enrol_authority: Optional[str] = Field(None, description="列入作出决定机关", alias="enrolAuthority")
    shift_time: Optional[str] = Field(None, description="移出日期", alias="shiftTime")
    shift_cause: Optional[str] = Field(None, description="移出经营异常名录原因", alias="shiftCause")
    shift_authority: Optional[str] = Field(None, description="移出作出决定机关", alias="shiftAuthority")
    enter_public: Optional[str] = Field(None, description="是否当前公示", alias="enterPublic")


class ChashuibaoIllegalBreach(BaseModel):
    """严重违法失信"""
    type: Optional[str] = Field(None, description="检查实施机关")
    enrol_time: Optional[str] = Field(None, description="列入日期", alias="enrolTime")
    enrol_cause: Optional[str] = Field(None, description="列入严重违法失信企业名单原因", alias="enrolCause")
    enrol_authority: Optional[str] = Field(None, description="作出决定机关（列入）", alias="enrolAuthority")
    shift_time: Optional[str] = Field(None, description="移出日期", alias="shiftTime")
    shift_cause: Optional[str] = Field(None, description="移出严重违法失信企业名单原因", alias="shiftCause")
    shift_authority: Optional[str] = Field(None, description="作出决定机关(移出)", alias="shiftAuthority")


class ChashuibaoInvest(BaseModel):
    """企业对外投资"""
    firm_name: Optional[str] = Field(None, description="被投企业名称", alias="firmName")
    registered_capital: Optional[str] = Field(None, description="注册资本(万元)", alias="registeredCapital")
    contribution_capital: Optional[str] = Field(None, description="出资金额（万元）", alias="contributionCapital")
    contribution_ratio: Optional[str] = Field(None, description="出资比例", alias="contributionRatio")
    status: Optional[str] = Field(None, description="登记状态")
    establish_time: Optional[str] = Field(None, description="成立日期", alias="establishTime")


class ChashuibaoInvestExit(BaseModel):
    """历史退出对外投资"""
    firm_name: Optional[str] = Field(None, description="被投企业名称", alias="firmName")
    enter_time: Optional[str] = Field(None, description="进入时间", alias="enterTime")
    exit_time: Optional[str] = Field(None, description="退出时间", alias="exitTime")
    hold_time: Optional[str] = Field(None, description="持股时长", alias="holdTime")


class ChashuibaoBranch(BaseModel):
    """分支机构"""
    branch_name: Optional[str] = Field(None, description="被投企业名称", alias="branchName")
    province_name: Optional[str] = Field(None, description="所属省份", alias="provinceName")
    status: Optional[str] = Field(None, description="登记状态")
    establish_time: Optional[str] = Field(None, description="成立日期", alias="establishTime")


class ChashuibaoPersonnelInvest(BaseModel):
    """法人代表对外投资"""
    type: Optional[int] = Field(None, description="人员类型 0-法人 1-其他（高管）")
    name: Optional[str] = Field(None, description="姓名")
    role: Optional[str] = Field(None, description="角色")
    firm_name: Optional[str] = Field(None, description="被投企业名称", alias="firmName")
    registered_capital: Optional[str] = Field(None, description="注册资本(万元)", alias="registeredCapital")
    contribution_amount: Optional[str] = Field(None, description="出资金额(万元)", alias="contributionAmount")
    contribution_ratio: Optional[str] = Field(None, description="出资比例", alias="contributionRatio")
    status: Optional[str] = Field(None, description="登记状态")
    establish_time: Optional[str] = Field(None, description="成立日期", alias="establishTime")


class ChashuibaoPersonnelOffice(BaseModel):
    """法人代表外部任职"""
    type: Optional[int] = Field(None, description="人员类型 0-法人 1-其他（高管）")
    name: Optional[str] = Field(None, description="姓名")
    role: Optional[str] = Field(None, description="角色")
    firm_name: Optional[str] = Field(None, description="任职企业名称", alias="firmName")
    position: Optional[str] = Field(None, description="职务")
    is_legal: Optional[str] = Field(None, description="是否法定代表人", alias="isLegal")
    status: Optional[str] = Field(None, description="登记状态")
    establish_time: Optional[str] = Field(None, description="成立日期", alias="establishTime")


class ChashuibaoListedCompanyInfo(BaseModel):
    """上市公司基本信息"""
    firm_name: Optional[str] = Field(None, description="企业名称", alias="firmName")
    firm_english_name: Optional[str] = Field(None, description="英文名称", alias="firmEnglishName")
    stock_code: Optional[str] = Field(None, description="股票代码", alias="stockCode")
    stock_name: Optional[str] = Field(None, description="股票名称", alias="stockName")
    market_time: Optional[str] = Field(None, description="上市时间", alias="marketTime")


class ChashuibaoListedCompanyShareholder(BaseModel):
    """上市公司十大股东"""
    name: Optional[str] = Field(None, description="股东名称")
    stock_amount: Optional[str] = Field(None, description="持股数量(股)", alias="stockAmount")
    stock_ratio: Optional[str] = Field(None, description="持股比例", alias="stockRatio")
    shareholders_nature: Optional[str] = Field(None, description="股东性质", alias="shareholdersNature")


class ChashuibaoReportFinancialDetail(BaseModel):
    """报表详情"""
    sheet_type: Optional[int] = Field(None, description="表类型 0-资产负债表 1-利润表 2-现金流量表", alias="sheetType")
    titile: Optional[str] = Field(None, description="主标题")
    subtitle: Optional[str] = Field(None, description="副标题")
    target: Optional[str] = Field(None, description="指标")
    quarter1: Optional[str] = Field(None, description="第一季度")
    quarter2: Optional[str] = Field(None, description="第二季度")
    quarter3: Optional[str] = Field(None, description="第三季度")
    quarter4: Optional[str] = Field(None, description="第四季度")


class ChashuibaoReportFinancial(BaseModel):
    """财务报表"""
    type: Optional[int] = Field(None, description="报表类型 0-资产负债表 1-利润表 2-现金流量表")
    report_name: Optional[str] = Field(None, description="报表名称", alias="reportName")
    report_financial_detail_list: Optional[List["ChashuibaoReportFinancialDetail"]] = Field(None, alias="reportFinancialDetailList")


class ChashuibaoReportAnnualWebsite(BaseModel):
    """网店或网站信息"""
    name: Optional[str] = Field(None, description="网站名称")
    url: Optional[str] = Field(None, description="网址")


class ChashuibaoReportAnnualShareholderContribution(BaseModel):
    """股东及出资信息"""
    shareholder: Optional[str] = Field(None, description="股东")
    contribution_amount: Optional[str] = Field(None, description="认缴出资额(万元)", alias="contributionAmount")
    contribution_date: Optional[str] = Field(None, description="认缴出资时间", alias="contributionDate")
    contribution_type: Optional[str] = Field(None, description="认缴出资方式", alias="contributionType")
    contribution_amount_actual: Optional[str] = Field(None, description="实缴出资额(万元)", alias="contributionAmountActual")
    contribution_date_actual: Optional[str] = Field(None, description="实缴出资时间", alias="contributionDateActual")
    contribution_type_actual: Optional[str] = Field(None, description="实缴出资方式", alias="contributionTypeActual")


class ChashuibaoReportAnnualInvest(BaseModel):
    """对外投资信息"""
    firm_name: Optional[str] = Field(None, description="投资设立企业或购买股权企业名称", alias="firmName")
    unify_credit_code: Optional[str] = Field(None, description="统一社会信用代码", alias="unifyCreditCode")


class ChashuibaoReportAnnualFinancial(BaseModel):
    """企业财务状况"""
    assets_total: Optional[str] = Field(None, description="资产总额", alias="assetsTotal")
    owner_equity_total: Optional[str] = Field(None, description="所有者权益合计", alias="ownerEquityTotal")
    sales_total: Optional[str] = Field(None, description="销售总额", alias="salesTotal")
    profit_total: Optional[str] = Field(None, description="利润总额", alias="profitTotal")
    core_business_total: Optional[str] = Field(None, description="营业额收入中主营业务收入", alias="coreBusinessTotal")
    profit_retained_total: Optional[str] = Field(None, description="净利润", alias="profitRetainedTotal")
    tax_total: Optional[str] = Field(None, description="纳税总额", alias="taxTotal")
    liabilities_total: Optional[str] = Field(None, description="负债总额", alias="liabilitiesTotal")


class ChashuibaoReportAnnualGuaranty(BaseModel):
    """对外担保信息"""
    creditor: Optional[str] = Field(None, description="债权人")
    debtor: Optional[str] = Field(None, description="债务人")
    debt_principal_type: Optional[str] = Field(None, description="主债权种类", alias="debtPrincipalType")
    debt_principal_amount: Optional[str] = Field(None, description="主债权数额", alias="debtPrincipalAmount")
    debt_principal_period: Optional[str] = Field(None, description="履行债务期限", alias="debtPrincipalPeriod")
    guaranty_period: Optional[str] = Field(None, description="保证期限", alias="guarantyPeriod")
    guaranty_mode: Optional[str] = Field(None, description="保证方式", alias="guarantyMode")


class ChashuibaoReportAnnualEquityChange(BaseModel):
    """股权变更信息"""
    shareholder: Optional[str] = Field(None, description="股东")
    old_ratio: Optional[str] = Field(None, description="变更前股权比例", alias="oldRatio")
    new_ratio: Optional[str] = Field(None, description="变更后股权比例", alias="newRatio")
    change_time: Optional[str] = Field(None, description="股权变更日期", alias="changeTime")


class ChashuibaoReportAnnualSocialSecurity(BaseModel):
    """社保信息"""
    old_age: Optional[str] = Field(None, description="城镇职工基本养老保险")
    out_work: Optional[str] = Field(None, description="失业保险")
    medical: Optional[str] = Field(None, description="职工基本医疗保险")
    injury: Optional[str] = Field(None, description="工伤保险")
    birth: Optional[str] = Field(None, description="生育保险")
    old_age_base: Optional[str] = Field(None, description="单位参加城镇职工基本养老保险缴费基数", alias="oldAgeBase")
    out_work_base: Optional[str] = Field(None, description="单位参加失业保险缴费基数", alias="outWorkBase")
    medical_base: Optional[str] = Field(None, description="单位参加职工基本医疗保险缴费基数", alias="medicalBase")
    injury_base: Optional[str] = Field(None, description="单位参加工伤保险缴费基数", alias="injuryBase")
    birth_base: Optional[str] = Field(None, description="单位参加生育保险缴费基数", alias="birthBase")
    old_age_base_actual: Optional[str] = Field(None, description="参加城镇职工基本养老保险本期实际缴费基数", alias="oldAgeBaseActual")
    out_work_base_actual: Optional[str] = Field(None, description="参加失业保险本期实际缴费基数", alias="outWorkBaseActual")
    medical_base_actual: Optional[str] = Field(None, description="参加职工基本医疗保险本期实际缴费基数", alias="medicalBaseActual")
    injury_base_actual: Optional[str] = Field(None, description="参加工伤保险本期实际缴费基数", alias="injuryBaseActual")
    birth_base_actual: Optional[str] = Field(None, description="参加生育保险本期实际缴费基数", alias="birthBaseActual")
    old_age_base_arrears: Optional[str] = Field(None, description="单位参加城镇职工基本养老保险累计欠缴金额", alias="oldAgeBaseArrears")
    out_work_base_arrears: Optional[str] = Field(None, description="单位参加失业保险累计欠缴金额", alias="outWorkBaseArrears")
    medical_base_arrears: Optional[str] = Field(None, description="单位参加职工基本医疗保险累计欠缴金额", alias="medicalBaseArrears")
    injury_base_arrears: Optional[str] = Field(None, description="单位参加工伤保险累计欠缴金额", alias="injuryBaseArrears")
    birth_base_arrears: Optional[str] = Field(None, description="单位参加生育保险累计欠缴金额", alias="birthBaseArrears")


class ChashuibaoReportAnnualModifyItem(BaseModel):
    """修改信息"""
    item: Optional[str] = Field(None, description="修改事项")
    before: Optional[str] = Field(None, description="修改前")
    after: Optional[str] = Field(None, description="修改后")
    modify_time: Optional[str] = Field(None, description="修改时间", alias="modifyTime")


class ChashuibaoReportAnnualInfo(BaseModel):
    """企业基本信息"""
    unify_credit_code: Optional[str] = Field(None, description="统一社会信用代码", alias="unifyCreditCode")
    firm_name: Optional[str] = Field(None, description="企业名称", alias="firmName")
    telephone_num: Optional[str] = Field(None, description="企业联系电话", alias="telephoneNum")
    postal_code: Optional[str] = Field(None, description="邮政编码", alias="postalCode")
    email: Optional[str] = Field(None, description="电子邮箱")
    is_transfer_equity: Optional[str] = Field(None, description="是否转让股东股权", alias="isTransferEquity")
    is_website: Optional[str] = Field(None, description="是否有网站或网店", alias="isWebsite")
    is_invest: Optional[str] = Field(None, description="是否投资或购买其他公司股权", alias="isInvest")
    status: Optional[str] = Field(None, description="登记状态")
    employee_amount: Optional[str] = Field(None, description="从业人数", alias="employeeAmount")
    postal_address: Optional[str] = Field(None, description="企业通讯地址", alias="postalAddress")
    report_annual_website_list: Optional[List[ChashuibaoReportAnnualWebsite]] = Field(None, alias="reportAnnualWebsiteList")
    report_annual_shareholder_contribution_list: Optional[List[ChashuibaoReportAnnualShareholderContribution]] = Field(None, alias="reportAnnualShareholderContributionList")
    report_annual_invest_list: Optional[List[ChashuibaoReportAnnualInvest]] = Field(None, alias="reportAnnualInvestList")
    report_annual_financial: Optional[List[ChashuibaoReportAnnualFinancial]] = Field(None, alias="reportAnnualFinancial")
    report_annual_guaranty_list: Optional[List[ChashuibaoReportAnnualGuaranty]] = Field(None, alias="reportAnnualGuarantyList")
    report_annual_equity_change_list: Optional[List[ChashuibaoReportAnnualEquityChange]] = Field(None, alias="reportAnnualEquityChangeList")
    report_annual_social_security: Optional[ChashuibaoReportAnnualSocialSecurity] = Field(None, alias="reportAnnualSocialSecurity")
    report_annual_modify_item_list: Optional[List[ChashuibaoReportAnnualModifyItem]] = Field(None, alias="reportAnnualModifyItemList")


class ChashuibaoReportAnnual(BaseModel):
    """企业年报"""
    reports_name: Optional[str] = Field(None, description="报告名称", alias="reportsName")
    report_annual_info: Optional[ChashuibaoReportAnnualInfo] = Field(None, alias="reportAnnualInfo")


class ChashuibaoItem(BaseModel):
    """企业项目"""
    item_name: Optional[str] = Field(None, description="项目名称", alias="itemName")
    item_time: Optional[str] = Field(None, description="项目时间", alias="itemTime")
    item_intro: Optional[str] = Field(None, description="项目简介", alias="itemIntro")


class ChashuibaoHonor(BaseModel):
    """企业荣誉"""
    honor_name: Optional[str] = Field(None, description="荣誉名称", alias="honorName")
    rating_organ: Optional[str] = Field(None, description="评价机构", alias="ratingOrgan")
    rating_time: Optional[str] = Field(None, description="评选时间", alias="ratingTime")


class ChashuibaoTrademarkPatent(BaseModel):
    """商标注册、专利申请"""
    register_no: Optional[str] = Field(None, description="注册号(专利类型)", alias="registerNo")
    name: Optional[str] = Field(None, description="商标名称")
    register_field: Optional[str] = Field(None, description="注册领域", alias="registerField")
    state: Optional[str] = Field(None, description="商标状态")
    apply_date: Optional[str] = Field(None, description="申请日期", alias="applyDate")
    public_date: Optional[str] = Field(None, description="公开公告日", alias="publicDate")
    type: Optional[int] = Field(None, description="类型（1：专利  2：商标）")


class ChashuibaoCopyright(BaseModel):
    """作品著作权、软件著作权"""
    name: Optional[str] = Field(None, description="企业名称")
    version: Optional[str] = Field(None, description="作品类别(软件名称)")
    complete_date: Optional[str] = Field(None, description="作品类别(版本)", alias="completeDate")
    register_date: Optional[str] = Field(None, description="创作完成日期（首次发表日期）", alias="registerDate")
    type: Optional[int] = Field(None, description="类型（1：作品著作权  2：软件著作权）")


class ChashuibaoNetworkRecruitment(BaseModel):
    """网络招聘"""
    position_name: Optional[str] = Field(None, description="职位名称", alias="positionName")
    hiring_people_num: Optional[str] = Field(None, description="招聘人数", alias="hiringPeopleNum")
    work_experience: Optional[str] = Field(None, description="工作经验", alias="workExperience")
    minimum_education_background: Optional[str] = Field(None, description="最低学历", alias="minimumEducationBackground")
    working_place: Optional[str] = Field(None, description="工作地点", alias="workingPlace")
    recruitment_date: Optional[str] = Field(None, description="招聘日期", alias="recruitmentDate")


class ChashuibaoQualification(BaseModel):
    """企业资质"""
    qualification_name: Optional[str] = Field(None, description="资质名称", alias="qualificationName")
    certificate_num: Optional[str] = Field(None, description="证书编号", alias="certificateNum")
    issue_time: Optional[str] = Field(None, description="发证时间", alias="issueTime")
    valid_time: Optional[str] = Field(None, description="有效期至", alias="validTime")
    authority_organ: Optional[str] = Field(None, description="认证机构", alias="authorityOrgan")
    authority_content: Optional[str] = Field(None, description="认证内容", alias="authorityContent")


class ChashuibaoWebShopDomainName(BaseModel):
    """网站商铺、网站域名"""
    name: Optional[str] = Field(None, description="店铺/网站名称")
    shop_location: Optional[str] = Field(None, description="店铺位置", alias="shopLocation")
    shop_url: Optional[str] = Field(None, description="店铺网址(网站域名)", alias="shopUrl")
    website_license_number: Optional[str] = Field(None, description="网站许可证号", alias="websiteLicenseNumber")
    website_manager: Optional[str] = Field(None, description="网站负责人", alias="websiteManager")
    type: Optional[str] = Field(None, description="类型（1：网站商铺  2：网站域名）")


class ChashuibaoTradeGoodsInfo(BaseModel):
    """贸易商品信息"""
    type: Optional[str] = Field(None, description="类别")
    time: Optional[str] = Field(None, description="时间")
    trading_nation: Optional[str] = Field(None, description="贸易国", alias="tradingNation")
    goods: Optional[str] = Field(None, description="商品(美元)")
    money: Optional[str] = Field(None, description="金额(美元)")


class ChashuibaoAmericaTradePartner(BaseModel):
    """美国贸易伙伴"""
    american_enterprise_name: Optional[str] = Field(None, description="美国企业名称", alias="americanEnterpriseName")
    real_buyer: Optional[str] = Field(None, description="是否真实买家", alias="realBuyer")


class ChashuibaoCustomsRegisterInfo(BaseModel):
    """海关注册信息"""
    social_credit_code: Optional[str] = Field(None, description="统一社会信用代码", alias="socialCreditCode")
    customs_registration_code: Optional[str] = Field(None, description="海关注册编码", alias="customsRegistrationCode")
    register_time: Optional[str] = Field(None, description="注册日期", alias="registerTime")
    organization_code: Optional[str] = Field(None, description="组织机构代码", alias="organizationCode")
    chinese_name: Optional[str] = Field(None, description="企业中文名称", alias="chineseName")
    register_customs: Optional[str] = Field(None, description="注册海关", alias="registerCustoms")
    business_register_address: Optional[str] = Field(None, description="工商注册地址", alias="businessRegisterAddress")
    administrative_division: Optional[str] = Field(None, description="行政区划", alias="administrativeDivision")
    division_of_economic_zones: Optional[str] = Field(None, description="经济区划", alias="divisionOfEconomicZones")
    business_category: Optional[str] = Field(None, description="经营类别", alias="businessCategory")
    special_trade_zone: Optional[str] = Field(None, description="特殊贸易区域", alias="specialTradeZone")
    industry_type: Optional[str] = Field(None, description="行业种类", alias="industryType")
    customs_declaration_valid_time: Optional[str] = Field(None, description="报关有效期", alias="customsDeclarationValidTime")
    customs_cancellation_marks: Optional[str] = Field(None, description="海关注销标志", alias="customsCancellationMarks")
    annual_report_situation: Optional[str] = Field(None, description="年报情况", alias="annualReportSituation")
    abnormal_credit_information: Optional[str] = Field(None, description="信用信息异常情况", alias="abnormalCreditInformation")


class ChashuibaoCustomsCreditLevel(BaseModel):
    """海关信用等级"""
    identified_time: Optional[str] = Field(None, description="认定时间", alias="identifiedTime")
    identified_no: Optional[str] = Field(None, description="认证证书编号", alias="identifiedNo")
    credit_level: Optional[str] = Field(None, description="信用等级", alias="creditLevel")


class ChashuibaoCustomsPunish(BaseModel):
    """海关行政处罚信息"""
    party: Optional[str] = Field(None, description="资质名称")
    case_nature: Optional[str] = Field(None, description="案件性质", alias="caseNature")
    punish_time: Optional[str] = Field(None, description="处罚日期", alias="punishTime")
    punish_no: Optional[str] = Field(None, description="行政处罚决定书编号", alias="punishNo")


class ChashuibaoFinalCase(BaseModel):
    """法院执行、终本案件"""
    case_no: Optional[str] = Field(None, description="资质名称", alias="caseNo")
    put_on_record_time: Optional[str] = Field(None, description="立案时间", alias="putOnRecordTime")
    final_this_time: Optional[str] = Field(None, description="终本日期(撤出公示日期)", alias="finalThisTime")
    perform_object: Optional[str] = Field(None, description="执行标的(元)", alias="performObject")
    fails_to_perform_money: Optional[str] = Field(None, description="未履行金额(元)", alias="failsToPerformMoney")
    execution_of_court: Optional[str] = Field(None, description="执行法院", alias="executionOfCourt")
    type: Optional[int] = Field(None, description="类型(1:终本案件 2:法院执行)")


class ChashuibaoRefereeDocument(BaseModel):
    """裁判文书"""
    case_type: Optional[str] = Field(None, description="案件类型", alias="caseType")
    case_no: Optional[str] = Field(None, description="案号", alias="caseNo")
    case_name: Optional[str] = Field(None, description="案件名称", alias="caseName")
    party_type: Optional[str] = Field(None, description="当事人类型", alias="partyType")
    trial_time: Optional[str] = Field(None, description="审判日期", alias="trialTime")


class ChashuibaoBrokenPromise(BaseModel):
    """企业失信、高管失信"""
    executives_name: Optional[str] = Field(None, description="高管名称", alias="executivesName")
    release_time: Optional[str] = Field(None, description="发布时间", alias="releaseTime")
    legal_document: Optional[str] = Field(None, description="法律文书", alias="legalDocument")
    perform_situation: Optional[str] = Field(None, description="履行情况", alias="performSituation")
    end_time: Optional[str] = Field(None, description="完结时间", alias="endTime")
    type: Optional[str] = Field(None, description="类型 0-企业失信 1-高管失信")


class ChashuibaoAdministrativeLicense(BaseModel):
    """信用中国行政许可"""
    decision_book_no: Optional[str] = Field(None, description="行政许可决定书文号", alias="decisionBookNo")
    audit_type: Optional[str] = Field(None, description="审核类型", alias="auditType")
    content_license: Optional[str] = Field(None, description="内容许可", alias="contentLincense")
    license_valid_date: Optional[str] = Field(None, description="许可有效期", alias="licenseValidDate")
    license_end_date: Optional[str] = Field(None, description="许可截至日期", alias="licenseEndDate")
    license_organ: Optional[str] = Field(None, description="许可机关", alias="licenseOrgan")
    data_update_date: Optional[str] = Field(None, description="数据更新时间", alias="dataUpdateDate")


class ChashuibaoAdministrativePunishment(BaseModel):
    """信用中国行政处罚"""
    decision_book_no: Optional[str] = Field(None, description="决定书文号", alias="decisionBookNo")
    punishment_name: Optional[str] = Field(None, description="处罚名称", alias="punishmentName")
    punishment_category: Optional[str] = Field(None, description="处罚类别", alias="punishmentCategory")
    punishment_organ: Optional[str] = Field(None, description="处罚机关", alias="punishmentOrgan")
    punishment_date: Optional[str] = Field(None, description="处罚决定日期", alias="punishmentDate")


class ChashuibaoCreditList(BaseModel):
    """信用中国守信红名单、信用中国失信黑名单"""
    serial_no: Optional[str] = Field(None, description="序号", alias="serialNo")
    category: Optional[str] = Field(None, description="类别")
    quantity: Optional[str] = Field(None, description="数量")
    type: Optional[int] = Field(None, description="类型（1：红名单  2：黑名单）")


class ChashuibaoBidTender(BaseModel):
    """招投标"""
    project_name: Optional[str] = Field(None, description="项目名称", alias="projectName")
    procurement: Optional[str] = Field(None, description="采购人", alias="procurement")
    release_time: Optional[str] = Field(None, description="发布时间", alias="releaseTime")


class ChashuibaoGoodsInfo(BaseModel):
    """商品信息"""
    goods_bar_code: Optional[str] = Field(None, description="商品条形码", alias="goodsBarCode")
    name: Optional[str] = Field(None, description="名称")
    brand: Optional[str] = Field(None, description="商标")
    specifications: Optional[str] = Field(None, description="规格型号")
    bar_code_state: Optional[str] = Field(None, description="条形码状态", alias="barCodeState")


class ChashuibaoAppApplication(BaseModel):
    """APP应用"""
    icon: Optional[str] = Field(None, description="图标")
    name: Optional[str] = Field(None, description="名称")
    classification: Optional[str] = Field(None, description="分类")
    system: Optional[str] = Field(None, description="系统")


class ChashuibaoPanoramicData(BaseModel):
    """全景报告数据"""
    # 评价
    evaluate_level: Optional[int] = Field(None, description="0成功 1失败", alias="evaluateLevel")
    evaluate_synthetical: Optional[str] = Field(None, description="评价-综合评价", alias="evaluateSynthetical")
    evaluate_mark: Optional[str] = Field(None, description="评价-综合评分", alias="evaluateMark")
    evaluate_six_figure_url: Optional[str] = Field(None, description="评价-六维评价图", alias="evaluateSixFigureUrl")

    # 描述
    describe_logo: Optional[str] = Field(None, description="描述-企业标识", alias="describeLogo")
    describe_official_website: Optional[str] = Field(None, description="描述-企业官网", alias="describeOfficialWebsite")
    describe_introduce: Optional[str] = Field(None, description="描述-企业介绍", alias="describeIntroduce")

    # 登记
    register_name: Optional[str] = Field(None, description="登记-企业名称", alias="registerName")
    register_old_name: Optional[str] = Field(None, description="登记-历史名称", alias="registerOldName")
    register_legal_person: Optional[str] = Field(None, description="登记-法定代表人", alias="registerLegalPerson")
    register_english_name: Optional[str] = Field(None, description="登记-企业英文名称", alias="registerEnglishName")
    register_status: Optional[str] = Field(None, description="登记-登记状态", alias="registerStatus")
    register_unify_credit_code: Optional[str] = Field(None, description="登记-统一社会信用代码", alias="registerUnifyCreditCode")
    register_organizational_code: Optional[str] = Field(None, description="登记-组织机构代码", alias="registerOrganizationalCode")
    register_capital: Optional[str] = Field(None, description="登记-注册资本", alias="registerCapital")
    register_establish_date: Optional[str] = Field(None, description="登记-核准日期", alias="registerEstablishDate")
    register_industry: Optional[str] = Field(None, description="登记-所属行业", alias="registerIndustry")
    register_form: Optional[str] = Field(None, description="登记-企业类型", alias="registerForm")
    register_address: Optional[str] = Field(None, description="登记-住址", alias="registerAddress")
    register_institution: Optional[str] = Field(None, description="登记-登记机关", alias="registerInstitution")
    register_contact_info: Optional[str] = Field(None, description="登记-联系方式", alias="registerContactInfo")
    register_scope: Optional[str] = Field(None, description="登记-经营范围", alias="registerScope")

    # 控制
    actual_controller: Optional[str] = Field(None, description="控制-实际控制人", alias="actualController")

    # 统计
    personnel_investment_total: Optional[str] = Field(None, description="投资-企业关联人员投资", alias="personnelInvestmentTotal")
    change_total: Optional[str] = Field(None, description="变更-变更信息统计", alias="changeTotal")
    personnel_office_total: Optional[str] = Field(None, description="任职-企业关联人员任职", alias="personnelOfficeTotal")

    # 详细列表
    gene_list: Optional[List[ChashuibaoGeneItem]] = Field(None, alias="geneList")
    address: Optional[ChashuibaoAddress] = Field(None)
    shareholder_list: Optional[List[ChashuibaoShareholder]] = Field(None, alias="shareholderList")
    personnel_list: Optional[List[ChashuibaoPersonnel]] = Field(None, alias="personnelList")
    change_list: Optional[List[ChashuibaoChange]] = Field(None, alias="changeList")
    pledge_equity_list: Optional[List[ChashuibaoPledgeEquity]] = Field(None, alias="pledgeEquityList")
    chattel_mortgage_list: Optional[List[ChashuibaoChattelMortgage]] = Field(None, alias="chattelMortgageList")
    liquidation_list: Optional[List[ChashuibaoLiquidation]] = Field(None, alias="liquidationList")
    examine_list: Optional[List[ChashuibaoExamine]] = Field(None, alias="examineList")
    judicial_aid_list: Optional[List[ChashuibaoJudicialAid]] = Field(None, alias="judicialAidList")
    penalty_list: Optional[List[ChashuibaoPenalty]] = Field(None, alias="penaltyList")
    abnormal_operation_list: Optional[List[ChashuibaoAbnormalOperation]] = Field(None, alias="abnormalOperationList")
    illegal_breach_list: Optional[List[ChashuibaoIllegalBreach]] = Field(None, alias="illegalBreachList")
    invest_list: Optional[List[ChashuibaoInvest]] = Field(None, alias="investList")
    invest_exit_list: Optional[List[ChashuibaoInvestExit]] = Field(None, alias="investExitList")
    branch_list: Optional[List[ChashuibaoBranch]] = Field(None, alias="branchList")
    personnel_invest_list: Optional[List[ChashuibaoPersonnelInvest]] = Field(None, alias="personnelInvestList")
    personnel_office_list: Optional[List[ChashuibaoPersonnelOffice]] = Field(None, alias="personnelOfficeList")
    listed_company_info: Optional[ChashuibaoListedCompanyInfo] = Field(None, alias="listedCompanyInfo")
    listed_company_shareholder10_list: Optional[List[ChashuibaoListedCompanyShareholder]] = Field(None, alias="listedCompanyShareholder10List")
    report_financial_list: Optional[List[ChashuibaoReportFinancial]] = Field(None, alias="reportFinancialList")
    report_annual_list: Optional[List[ChashuibaoReportAnnual]] = Field(None, alias="reportAnnualList")
    item_list: Optional[List[ChashuibaoItem]] = Field(None, alias="itemList")
    qualification_list: Optional[List[ChashuibaoQualification]] = Field(None, alias="qualificationList")
    honor_list: Optional[List[ChashuibaoHonor]] = Field(None, alias="honorList")
    trademark_patent_list: Optional[List[ChashuibaoTrademarkPatent]] = Field(None, alias="trademarkPatentList")
    copyright_list: Optional[List[ChashuibaoCopyright]] = Field(None, alias="copyrightList")
    network_recruitment_list: Optional[List[ChashuibaoNetworkRecruitment]] = Field(None, alias="networkRecruitmentList")
    web_shop_domain_name_list: Optional[List[ChashuibaoWebShopDomainName]] = Field(None, alias="webShopDomainNameList")
    trade_goods_info_list: Optional[List[ChashuibaoTradeGoodsInfo]] = Field(None, alias="tradeGoodsInfoList")
    america_trade_partner_list: Optional[List[ChashuibaoAmericaTradePartner]] = Field(None, alias="americaTradePartnerList")
    customs_register_info: Optional[ChashuibaoCustomsRegisterInfo] = Field(None, alias="customsRegisterInfo")
    customs_credit_level_list: Optional[List[ChashuibaoCustomsCreditLevel]] = Field(None, alias="customsCreditLevelList")
    customs_punish_list: Optional[List[ChashuibaoCustomsPunish]] = Field(None, alias="customsPunishList")
    final_case_list: Optional[List[ChashuibaoFinalCase]] = Field(None, alias="finalCaseList")
    the_referee_documents_list: Optional[List[ChashuibaoRefereeDocument]] = Field(None, alias="theRefereeDocumentsList")
    broken_promises_list: Optional[List[ChashuibaoBrokenPromise]] = Field(None, alias="brokenPromisesList")
    administrative_license_list: Optional[List[ChashuibaoAdministrativeLicense]] = Field(None, alias="administrativeLicenseList")
    administrative_punishment_list: Optional[List[ChashuibaoAdministrativePunishment]] = Field(None, alias="administrativePunishmentList")
    credit_list_list: Optional[List[ChashuibaoCreditList]] = Field(None, alias="creditListList")
    bid_tender_list: Optional[List[ChashuibaoBidTender]] = Field(None, alias="bidTenderList")
    goods_info_list: Optional[List[ChashuibaoGoodsInfo]] = Field(None, alias="goodsInfoList")
    app_application_list: Optional[List[ChashuibaoAppApplication]] = Field(None, alias="appApplicationList")

    class Config:
        populate_by_name = True
