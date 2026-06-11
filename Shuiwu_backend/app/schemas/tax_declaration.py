"""
智能报税系统相关的 Pydantic Schema
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# 用户端 - 报税表单提交
# ============================================================================

class CreateTaxDeclarationRequest(BaseModel):
    """创建报税申报请求"""
    # 纳税人基本信息
    taxpayer_name: str = Field(..., description="纳税人姓名", min_length=1, max_length=100)
    taxpayer_id_card: Optional[str] = Field(None, description="身份证号")
    taxpayer_phone: str = Field(..., description="联系电话", min_length=1, max_length=20)
    taxpayer_type: str = Field(default="individual", description="纳税人类型: individual-个人, enterprise-企业")

    # 税种信息
    tax_type: str = Field(..., description="税种: vat-增值税, pit-个人所得税, cit-企业所得税")
    tax_period: str = Field(..., description="税期，如: 2024Q1, 2024-01")

    # 收入信息 (JSON格式，根据不同税种结构不同)
    income_info: Dict[str, Any] = Field(..., description="收入信息")

    # 扣除信息 (可选)
    deduction_info: Optional[Dict[str, Any]] = Field(None, description="扣除信息")

    # 用户备注
    user_remarks: Optional[str] = Field(None, description="用户备注", max_length=1000)

    class Config:
        json_schema_extra = {
            "example": {
                "taxpayer_name": "张三",
                "taxpayer_id_card": "110101199001011234",
                "taxpayer_phone": "13800138000",
                "taxpayer_type": "individual",
                "tax_type": "pit",
                "tax_period": "2024Q1",
                "income_info": {
                    "salary": 50000,        # 工资薪金
                    "bonus": 10000,         # 奖金
                    "investment_income": 5000  # 投资收益
                },
                "deduction_info": {
                    "special_deduction": 3000,   # 专项扣除
                    "additional_deduction": 2000  # 附加扣除
                },
                "user_remarks": "请帮我核算一下季度个税"
            }
        }


# ============================================================================
# 通用响应模型
# ============================================================================

class TaxDeclarationResponse(BaseModel):
    """报税申报响应"""
    id: int
    declaration_no: str
    user_id: str
    taxpayer_name: str
    taxpayer_phone: str
    taxpayer_type: str
    tax_type: str
    tax_period: str
    total_income: Optional[float] = None
    total_deduction: Optional[float] = None
    taxable_income: Optional[float] = None
    tax_amount: Optional[float] = None
    tax_refund: Optional[float] = None
    status: str
    created_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TaxDeclarationDetailResponse(TaxDeclarationResponse):
    """报税申报详情（包含完整信息）"""
    taxpayer_id_card: Optional[str] = None
    income_info: Optional[Dict[str, Any]] = None
    deduction_info: Optional[Dict[str, Any]] = None
    process_result: Optional[str] = None
    declaration_serial_no: Optional[str] = None
    declaration_date: Optional[datetime] = None
    declaration_proof_url: Optional[str] = None
    processed_by: Optional[str] = None
    process_notes: Optional[str] = None
    user_remarks: Optional[str] = None
    updated_at: Optional[datetime] = None


# ============================================================================
# 列表查询参数
# ============================================================================

class TaxDeclarationListQuery(BaseModel):
    """报税申报列表查询参数"""
    status: Optional[str] = Field(None, description="状态筛选")
    tax_type: Optional[str] = Field(None, description="税种筛选")
    tax_period: Optional[str] = Field(None, description="税期筛选")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")


# ============================================================================
# 管理员 - 处理报税
# ============================================================================

class ProcessTaxDeclarationRequest(BaseModel):
    """处理报税请求"""
    # 计算结果
    total_income: Optional[float] = Field(None, description="收入总额")
    total_deduction: Optional[float] = Field(None, description="扣除总额")
    taxable_income: Optional[float] = Field(None, description="应纳税所得额")
    tax_amount: Optional[float] = Field(None, description="应纳税额")
    tax_paid: Optional[float] = Field(None, description="已缴税额")
    tax_refund: Optional[float] = Field(None, description="应退税额")

    # 申报信息
    declaration_serial_no: Optional[str] = Field(None, description="税务局申报流水号")
    declaration_date: Optional[datetime] = Field(None, description="申报日期")
    declaration_proof_url: Optional[str] = Field(None, description="申报凭证URL")

    # 处理结果
    status: str = Field(..., description="处理后状态: processing-处理中, completed-已完成, rejected-已拒绝")
    process_result: Optional[str] = Field(None, description="处理结果说明")
    process_notes: Optional[str] = Field(None, description="处理备注", max_length=1000)

    class Config:
        json_schema_extra = {
            "example": {
                "total_income": 60000.00,
                "total_deduction": 5000.00,
                "taxable_income": 55000.00,
                "tax_amount": 2500.00,
                "tax_paid": 0,
                "tax_refund": 0,
                "declaration_serial_no": "WS2026012000001",
                "declaration_date": "2026-01-20T15:00:00",
                "declaration_proof_url": "https://oss.example.com/proofs/xxx.pdf",
                "status": "completed",
                "process_result": "申报成功，应纳税额2500元",
                "process_notes": "已通过电子税务局完成申报"
            }
        }


# ============================================================================
# 统计信息
# ============================================================================

class TaxDeclarationStatsResponse(BaseModel):
    """报税统计信息"""
    total_count: int = Field(..., description="总申报数")
    pending_count: int = Field(..., description="待处理数")
    processing_count: int = Field(..., description="处理中数")
    completed_count: int = Field(..., description="已完成数")
    rejected_count: int = Field(..., description="已拒绝数")
    total_tax_amount: Optional[float] = Field(None, description="总应纳税额")


# ============================================================================
# 更新请求
# ============================================================================

class UpdateTaxDeclarationRequest(BaseModel):
    """更新报税申报（用户编辑自己的草稿）"""
    taxpayer_name: Optional[str] = Field(None, min_length=1, max_length=100)
    taxpayer_phone: Optional[str] = Field(None, min_length=1, max_length=20)
    income_info: Optional[Dict[str, Any]] = None
    deduction_info: Optional[Dict[str, Any]] = None
    user_remarks: Optional[str] = Field(None, max_length=1000)


# ============================================================================
# 状态枚举
# ============================================================================

class TaxDeclarationStatus:
    """报税状态常量"""
    PENDING = "pending"       # 待处理
    PROCESSING = "processing" # 处理中
    COMPLETED = "completed"   # 已完成
    REJECTED = "rejected"     # 已拒绝


class TaxTypeEnum:
    """税种常量"""
    VAT = "vat"   # 增值税
    PIT = "pit"   # 个人所得税
    CIT = "cit"   # 企业所得税
    IIT = "iit"   # 个人所得税（综合所得）
