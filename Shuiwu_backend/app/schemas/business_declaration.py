"""
个体户工商申报 Pydantic 请求/响应模型与枚举常量。

该文件定义：
  - CreateBusinessDeclarationRequest：用户提交申报的请求体，兼容旧类型字段
    与新版执照申请（license_application）专属字段
  - BusinessDeclarationDetailResponse：申报详情响应结构
  - BusinessDeclarationListQuery / ListResponse / StatsResponse：列表与统计
  - ProcessBusinessDeclarationRequest：管理员处理申报请求体
  - DeclarationType / DeclarationStatus：申报类型与状态枚举常量
  - PoliticalStatus / EducationLevel：执照申请专属枚举常量
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# 用户端请求/响应模型
# ============================================================================

class CreateBusinessDeclarationRequest(BaseModel):
    """
    创建工商申报请求体。

    兼容两类申报：
    - 旧类型（annual_report / change_registration / deregistration /
      tax_registration / invoice_application）：使用 business_name、
      operator_name、operator_phone 等旧字段；
    - 新类型（license_application）：使用 license_store_name、
      applicant_name、applicant_phone 等新字段，旧字段可不传。

    后端在 API 层根据 declaration_type 做分支校验与字段映射，
    旧字段兜底设为 Optional 以避免新旧前端互相干扰。
    """

    # ---- 申报类型（所有类型必填）----
    declaration_type: str = Field(..., description="申报类型")

    # ---- 旧类型公用字段 ----
    business_name: Optional[str] = Field(None, description="个体户名称（旧类型使用）")
    business_license_no: Optional[str] = Field(None, description="营业执照号")
    business_address: Optional[str] = Field(None, description="经营地址")
    business_type: Optional[str] = Field(None, description="经营类型")
    business_scope: Optional[str] = Field(None, description="经营范围")
    operator_name: Optional[str] = Field(None, description="经营者姓名（旧类型使用）")
    operator_id_card: Optional[str] = Field(None, description="身份证号（旧类型使用）")
    operator_phone: Optional[str] = Field(None, description="联系电话（旧类型使用）")
    declaration_info: Optional[Dict[str, Any]] = Field(None, description="申报详细信息（旧类型使用）")
    attachments: Optional[List[Dict[str, Any]]] = Field(None, description="附件（旧类型使用）")

    # ---- 执照申请（license_application）专属字段 ----
    license_store_name: Optional[str] = Field(None, description="主营业执照字号")
    license_store_name_list: Optional[List[str]] = Field(None, description="备用字号列表，可为空数组")
    id_card_number: Optional[str] = Field(None, description="18位身份证号")
    id_card_valid_type: Optional[str] = Field(None, description="证件有效期类型：range（有期限）/ long_term（长期）")
    id_card_valid_start: Optional[str] = Field(None, description="证件有效期开始（YYYY-MM-DD），id_card_valid_type=range 时必填")
    id_card_valid_end: Optional[str] = Field(None, description="证件有效期结束（YYYY-MM-DD），id_card_valid_type=range 时必填")
    id_card_front_url: Optional[str] = Field(None, description="身份证人像面 OSS URL")
    id_card_back_url: Optional[str] = Field(None, description="身份证国徽面 OSS URL")
    applicant_name: Optional[str] = Field(None, description="申请人姓名（执照申请使用）")
    applicant_phone: Optional[str] = Field(None, description="申请人手机号（执照申请使用）")
    political_status: Optional[str] = Field(None, description="政治面貌：masses/league_member/party_member/other")
    education_level: Optional[str] = Field(None, description="学历：high_school/junior_college/bachelor/postgraduate")
    email: Optional[str] = Field(None, description="邮箱（选填，非空时校验格式）")
    extra_attachments: Optional[List[Dict[str, Any]]] = Field(None, description="补充材料 [{file_url, name}]（执照申请使用）")
    agree_protocol: Optional[bool] = Field(None, description="已同意协议，执照申请时前端固定传 true")

    # ---- 通用选填 ----
    user_remarks: Optional[str] = Field(None, description="用户备注")


class BusinessDeclarationDetailResponse(BaseModel):
    """工商申报详情响应"""
    id: int
    declaration_no: str
    user_id: str

    business_name: str
    business_license_no: Optional[str]
    business_address: Optional[str]
    business_type: Optional[str]
    business_scope: Optional[str]

    operator_name: str
    operator_id_card: Optional[str]
    operator_phone: str

    declaration_type: str
    declaration_info: Optional[Dict[str, Any]]
    attachments: Optional[List[Dict[str, Any]]]

    status: str
    approval_no: Optional[str]
    approval_date: Optional[str]
    approval_proof_url: Optional[str]
    process_result: Optional[str]
    process_notes: Optional[str]

    processed_by: Optional[str]
    processed_at: Optional[str]

    user_remarks: Optional[str]
    created_at: str
    updated_at: str


class BusinessDeclarationListQuery(BaseModel):
    """工商申报列表查询参数"""
    status: Optional[str] = None
    declaration_type: Optional[str] = None
    page: int = 1
    page_size: int = 20


class BusinessDeclarationListResponse(BaseModel):
    """工商申报列表响应"""
    total: int
    page: int
    page_size: int
    declarations: List[Dict[str, Any]]


class BusinessDeclarationStatsResponse(BaseModel):
    """工商申报统计响应"""
    stats: Dict[str, Any]


# ============================================================================
# 管理员模型
# ============================================================================

class ProcessBusinessDeclarationRequest(BaseModel):
    """管理员处理工商申报请求"""
    status: str = Field(..., description="处理状态")
    approval_no: Optional[str] = Field(None, description="受理号")
    approval_date: Optional[str] = Field(None, description="受理日期")
    approval_proof_url: Optional[str] = Field(None, description="批准凭证URL")
    process_result: Optional[str] = Field(None, description="处理结果说明")
    process_notes: Optional[str] = Field(None, description="处理备注")


# ============================================================================
# 申报类型枚举
# ============================================================================

class DeclarationType:
    """申报类型常量"""
    ANNUAL_REPORT = "annual_report"              # 年报
    CHANGE_REGISTRATION = "change_registration"  # 变更登记
    DEREGISTRATION = "deregistration"            # 注销登记
    TAX_REGISTRATION = "tax_registration"        # 税务登记
    INVOICE_APPLICATION = "invoice_application"  # 发票申请
    LICENSE_APPLICATION = "license_application"  # 工商执照申请（新增）

    @classmethod
    def all(cls) -> list:
        return [
            cls.ANNUAL_REPORT,
            cls.CHANGE_REGISTRATION,
            cls.DEREGISTRATION,
            cls.TAX_REGISTRATION,
            cls.INVOICE_APPLICATION,
            cls.LICENSE_APPLICATION,
        ]

    @classmethod
    def get_name(cls, type_code: str) -> str:
        names = {
            cls.ANNUAL_REPORT: "年报",
            cls.CHANGE_REGISTRATION: "变更登记",
            cls.DEREGISTRATION: "注销登记",
            cls.TAX_REGISTRATION: "税务登记",
            cls.INVOICE_APPLICATION: "发票申请",
            cls.LICENSE_APPLICATION: "工商执照申请",
        }
        return names.get(type_code, type_code)


class DeclarationStatus:
    """申报状态常量"""
    PENDING = "pending"                  # 待处理
    PROCESSING = "processing"            # 处理中
    COMPLETED = "completed"              # 已完成
    REJECTED = "rejected"                # 已拒绝
    NEED_SUPPLEMENT = "need_supplement"  # 需要补充材料

    @classmethod
    def all(cls) -> list:
        return [
            cls.PENDING,
            cls.PROCESSING,
            cls.COMPLETED,
            cls.REJECTED,
            cls.NEED_SUPPLEMENT,
        ]

    @classmethod
    def get_name(cls, status: str) -> str:
        names = {
            cls.PENDING: "待处理",
            cls.PROCESSING: "处理中",
            cls.COMPLETED: "已完成",
            cls.REJECTED: "已拒绝",
            cls.NEED_SUPPLEMENT: "需要补充材料",
        }
        return names.get(status, status)


# ============================================================================
# 执照申请专属枚举（用于文档/校验参考）
# ============================================================================

class PoliticalStatus:
    """政治面貌枚举"""
    MASSES = "masses"              # 群众
    LEAGUE_MEMBER = "league_member"  # 共青团员
    PARTY_MEMBER = "party_member"  # 中共党员
    OTHER = "other"                # 其他

    @classmethod
    def all(cls) -> list:
        return [cls.MASSES, cls.LEAGUE_MEMBER, cls.PARTY_MEMBER, cls.OTHER]


class EducationLevel:
    """学历枚举"""
    HIGH_SCHOOL = "high_school"        # 高中及以下
    JUNIOR_COLLEGE = "junior_college"  # 大专
    BACHELOR = "bachelor"              # 本科
    POSTGRADUATE = "postgraduate"      # 研究生及以上

    @classmethod
    def all(cls) -> list:
        return [cls.HIGH_SCHOOL, cls.JUNIOR_COLLEGE, cls.BACHELOR, cls.POSTGRADUATE]
