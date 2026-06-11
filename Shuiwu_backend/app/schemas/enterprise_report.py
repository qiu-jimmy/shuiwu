"""
企业体检报告相关的 Schema 定义
"""
from typing import Optional
from pydantic import BaseModel, Field


class EnterpriseReportGenerateRequest(BaseModel):
    """企业体检报告生成请求"""

    company_name: str = Field(
        ...,
        description="企业名称",
        min_length=2,
        max_length=200,
    )
    credit_code: Optional[str] = Field(
        None,
        description="统一社会信用代码（可选，用于精确匹配）",
        min_length=18,
        max_length=18,
    )

    class Config:
        json_schema_extra = {
            "example": {
                "company_name": "杭州烛龙智元科技有限公司",
                "credit_code": "91330100MA2XXX00XX",
            }
        }


class EnterpriseReportResponse(BaseModel):
    """企业体检报告生成响应"""

    report_number: str = Field(..., description="报告编号")
    file_url: str = Field(..., description="文件访问URL")
    file_name: str = Field(..., description="文件名")
    file_size: Optional[int] = Field(None, description="文件大小（字节）")
    project_name: str = Field(..., description="企业/项目名称")
    generated_at: str = Field(..., description="生成时间")

    class Config:
        json_schema_extra = {
            "example": {
                "report_number": "QT20250121001",
                "file_url": "/api/enterprise_report/download/QT20250121001",
                "file_name": "005_QT20250121001.docx",
                "file_size": 245600,
                "project_name": "005",
                "generated_at": "2025-01-21 14:30:00",
            }
        }


class EnterpriseReportStatusResponse(BaseModel):
    """企业体检报告生成状态响应"""

    is_generating: bool = Field(..., description="是否正在生成")
    queue_length: int = Field(..., description="队列长度")

    class Config:
        json_schema_extra = {
            "example": {
                "is_generating": False,
                "queue_length": 0,
            }
        }
