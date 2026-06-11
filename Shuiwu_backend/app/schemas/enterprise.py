"""
企业认证相关的 Pydantic 模型
"""
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime


# ==================== 企业认证 ====================

class EnterpriseCertificationCreate(BaseModel):
    """创建企业认证申请"""
    user_id: str
    # 企业信息
    enterprise_name: str
    credit_code: str  # 统一社会信用代码
    legal_person_name: Optional[str] = None
    legal_person_phone: Optional[str] = None
    legal_person_id_card: Optional[str] = None
    # 企业地址
    province: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    address: Optional[str] = None
    # 证件资料
    business_license_url: Optional[str] = None
    id_card_front_url: Optional[str] = None
    id_card_back_url: Optional[str] = None
    other_files: Optional[dict] = None
    remark: Optional[str] = None


class EnterpriseCertificationUpdate(BaseModel):
    """更新企业认证申请"""
    enterprise_name: Optional[str] = None
    legal_person_name: Optional[str] = None
    legal_person_phone: Optional[str] = None
    business_license_url: Optional[str] = None
    id_card_front_url: Optional[str] = None
    id_card_back_url: Optional[str] = None
    other_files: Optional[dict] = None
    remark: Optional[str] = None


class EnterpriseCertificationResponse(BaseModel):
    """企业认证响应"""
    certification_id: str
    user_id: str
    enterprise_name: str
    credit_code: str
    legal_person_name: Optional[str] = None
    legal_person_phone: Optional[str] = None
    legal_person_id_card: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    address: Optional[str] = None
    business_license_url: Optional[str] = None
    id_card_front_url: Optional[str] = None
    id_card_back_url: Optional[str] = None
    other_files: Optional[dict] = None
    status: str
    reject_reason: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    cert_expire_at: Optional[datetime] = None
    remark: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class EnterpriseCertificationListResponse(BaseModel):
    """企业认证列表响应"""
    total: int
    page: int
    page_size: int
    certifications: List[EnterpriseCertificationResponse]


# ==================== 企业认证审核 ====================

class EnterpriseAuditRequest(BaseModel):
    """企业认证审核请求"""
    certification_id: str
    action: str  # approve, reject
    reject_reason: Optional[str] = None
    cert_expire_days: Optional[int] = 365  # 认证有效期，默认365天


class EnterpriseAuditResponse(BaseModel):
    """企业认证审核响应"""
    certification_id: str
    status: str
    reject_reason: Optional[str] = None
    cert_expire_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None


class EnterpriseAuditLogResponse(BaseModel):
    """企业认证审核日志响应"""
    id: int
    certification_id: str
    operator_id: Optional[str] = None
    action: str
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    remark: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ==================== 企业成员 ====================

class EnterpriseMemberCreate(BaseModel):
    """添加企业成员"""
    enterprise_id: str
    user_id: str
    member_role: str = "member"  # admin, member


class EnterpriseMemberResponse(BaseModel):
    """企业成员响应"""
    id: int
    enterprise_id: str
    user_id: str
    member_role: str
    status: str
    joined_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class EnterpriseMemberListResponse(BaseModel):
    """企业成员列表响应"""
    total: int
    members: List[EnterpriseMemberResponse]


# ==================== 企业认证查询 ====================

class EnterpriseCertificationQueryParams(BaseModel):
    """企业认证查询参数"""
    user_id: Optional[str] = None
    status: Optional[str] = None
    enterprise_name: Optional[str] = None
    credit_code: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    page: int = 1
    page_size: int = 20
