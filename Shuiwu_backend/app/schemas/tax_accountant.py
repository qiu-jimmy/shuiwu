"""
税务师入驻相关的 Pydantic 模型
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime, date


# ==================== 工作经历 ====================

class WorkExperienceItem(BaseModel):
    """工作经历项"""
    start_date: str = Field(..., description="开始时间", examples=["2020-01"])
    end_date: Optional[str] = Field(None, description="结束时间", examples=["2023-12"])
    company: str = Field(..., description="工作单位/执业机构名称")
    position: str = Field(..., description="职务/岗位")
    work_content: Optional[str] = Field(None, description="主要工作内容")


# ==================== 税务师申请 ====================

class TaxAccountantApplicationCreate(BaseModel):
    """创建税务师入驻申请"""
    name: str = Field(..., description="真实姓名", min_length=2, max_length=100)
    birthDate: Optional[str] = Field(None, description="出生日期", examples=["1990-01-01"])
    idCard: str = Field(..., description="身份证号", min_length=15, max_length=20)
    address: Optional[str] = Field(None, description="现住地", max_length=500)
    phone: str = Field(..., description="联系电话", min_length=11, max_length=20)
    certificateNo: str = Field(..., description="税务师职业资格证书编号", min_length=1, max_length=100)
    certificateDate: Optional[str] = Field(None, description="证书取得时间", examples=["2015-06"])
    certificateImages: List[str] = Field(..., description="证书图片URL列表", min_items=1)
    signatureImage: Optional[str] = Field(None, description="签字确认图片URL")
    experiences: Optional[List[WorkExperienceItem]] = Field(default_factory=list, description="工作经历")
    expertise: str = Field(..., description="擅长的税务业务领域",
                               examples=["企业所得税", "个人所得税", "增值税", "税务筹划"])
    settledIndex: Optional[int] = Field(None, description="是否入驻索引: 0-否, 1-是")
    additionalInfo: Optional[str] = Field(None, description="补充说明", max_length=2000)

    # 映射到后端字段名
    def to_internal_dict(self) -> Dict[str, Any]:
        """转换为后端内部使用的字典"""
        # 将expertise转换为specialty_area数组
        specialty_area_list = [self.expertise] if self.expertise else []

        # 将settledIndex转换为has_settled布尔值
        has_settled = self.settledIndex == 1 if self.settledIndex is not None else False

        # 将experiences转换为JSON
        experiences_data = None
        if self.experiences:
            experiences_data = [exp.model_dump() for exp in self.experiences]

        return {
            "real_name": self.name,
            "birth_date": self.birthDate,
            "id_card": self.idCard,
            "address": self.address,
            "phone": self.phone,
            "certificate_number": self.certificateNo,
            "certificate_date": self.certificateDate,
            "certificate_images": self.certificateImages,
            "signature_image": self.signatureImage,
            "work_experiences": experiences_data,
            "specialty_area": specialty_area_list,
            "introduction": None,
            "additional_info": self.additionalInfo,
            "has_settled": has_settled
        }


class TaxAccountantApplicationResponse(BaseModel):
    """税务师申请响应"""
    application_id: str
    user_id: str
    real_name: str
    birth_date: Optional[str] = None
    id_card: str
    address: Optional[str] = None
    phone: str
    certificate_number: str
    certificate_date: Optional[str] = None
    certificate_images: List[str]
    signature_image: Optional[str] = None
    work_experiences: Optional[List[WorkExperienceItem]] = None
    specialty_area: List[str]
    introduction: Optional[str] = None
    additional_info: Optional[str] = None
    has_settled: bool = False
    status: str  # pending, approved, rejected
    reject_reason: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TaxAccountantApplicationListResponse(BaseModel):
    """税务师申请列表响应"""
    total: int
    page: int
    page_size: int
    applications: List[TaxAccountantApplicationResponse]


class TaxAccountantApplicationStatusResponse(BaseModel):
    """税务师申请状态响应"""
    has_applied: bool  # 是否已申请
    application_id: Optional[str] = None
    status: Optional[str] = None  # pending, approved, rejected
    reject_reason: Optional[str] = None
    created_at: Optional[datetime] = None


# ==================== 税务师管理 ====================

class TaxAccountantReviewRequest(BaseModel):
    """税务师审核请求"""
    application_id: str = Field(..., description="申请ID")
    action: str = Field(..., description="审核操作: approve-通过, reject-拒绝")
    reject_reason: Optional[str] = Field(None, description="拒绝原因（拒绝时必填）")


class TaxAccountantUpdateRequest(BaseModel):
    """更新税务师信息请求"""
    accountant_id: str = Field(..., description="税务师ID")
    status: Optional[str] = Field(None, description="状态: active-正常, suspended-暂停")
    specialty_area: Optional[List[str]] = Field(None, description="专长领域")
    introduction: Optional[str] = Field(None, description="个人简介")


class TaxAccountantResponse(BaseModel):
    """税务师响应"""
    accountant_id: str
    user_id: str
    application_id: str
    real_name: str
    birth_date: Optional[str] = None
    id_card: str
    address: Optional[str] = None
    phone: str
    certificate_number: str
    certificate_date: Optional[str] = None
    specialty_area: List[str]
    introduction: Optional[str] = None
    additional_info: Optional[str] = None
    status: str  # active, suspended
    service_count: int
    rating: float
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TaxAccountantListResponse(BaseModel):
    """税务师列表响应"""
    total: int
    page: int
    page_size: int
    accountants: List[TaxAccountantResponse]


class TaxAccountantDetailResponse(BaseModel):
    """税务师详情响应（包含用户信息）"""
    accountant_id: str
    user_id: str
    application_id: str
    real_name: str
    birth_date: Optional[str] = None
    id_card: str
    address: Optional[str] = None
    phone: str
    certificate_number: str
    certificate_date: Optional[str] = None
    specialty_area: List[str]
    introduction: Optional[str] = None
    additional_info: Optional[str] = None
    status: str
    service_count: int
    rating: float
    # 用户信息
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ==================== 税务师统计 ====================

class TaxAccountantStatsResponse(BaseModel):
    """税务师统计响应"""
    total_applications: int  # 总申请数
    pending_count: int  # 待审核数
    approved_count: int  # 已通过数
    rejected_count: int  # 已拒绝数
    active_accountants: int  # 活跃税务师数
