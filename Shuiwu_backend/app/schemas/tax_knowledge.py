"""税务知识文档 Schemas（简化版）"""
from datetime import datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


# ============================================================================
# 前端格式模型（完全匹配 taxKnowledge.js 结构）
# ============================================================================

class PromulgationAnnouncement(BaseModel):
    """发布公告信息"""
    announcementNo: str = Field("", description="公告编号")
    announcementContent: str = Field("", description="公告内容")
    announcementIssuer: str = Field("", description="发布单位")
    announcementDate: str = Field("", description="发布日期")


class TimeInfo(BaseModel):
    """时间信息"""
    approvalDate: str = Field("", description="审批日期")
    promulgationDate: str = Field("", description="发布日期")
    effectiveDate: str = Field("", description="生效日期")
    activityEndDate: Optional[str] = Field(None, description="活动结束日期")
    expiryDate: Optional[str] = Field(None, description="失效日期")


class Article(BaseModel):
    """条款"""
    articleNo: str = Field(..., description="条款编号")
    articleContent: str = Field(..., description="条款内容")


class Chapter(BaseModel):
    """章节"""
    chapterName: str = Field(..., description="章节名称")
    articles: List[Article] = Field(default_factory=list, description="条款列表")


class TaxKnowledgeFrontendData(BaseModel):
    """税务知识文档前端格式（完全匹配 taxKnowledge.js）"""
    docType: str = Field(..., description="文档类型")
    lawId: str = Field(..., description="法规ID")
    lawName: str = Field(..., description="法规名称")
    lawStatus: str = Field(..., description="法规状态")
    promulgationAnnouncement: Optional[PromulgationAnnouncement] = Field(None, description="发布公告信息")
    approvalInfo: Optional[str] = Field(None, description="审批信息")
    timeInfo: Optional[TimeInfo] = Field(None, description="时间信息")
    chapters: List[Chapter] = Field(default_factory=list, description="章节列表")
    lawSource: Optional[str] = Field(None, description="法规来源")
    remark: Optional[str] = Field(None, description="备注")


# ============================================================================
# 请求模型
# ============================================================================

class CreateTaxKnowledgeRequest(BaseModel):
    """创建税务知识文档请求"""
    docType: str = Field(..., description="文档类型")
    lawId: str = Field(..., description="法规ID")
    lawName: str = Field(..., description="法规名称")
    lawStatus: str = Field("全文有效", description="法规状态")
    promulgationAnnouncement: Optional[PromulgationAnnouncement] = Field(None, description="发布公告信息")
    approvalInfo: Optional[str] = Field(None, description="审批信息")
    timeInfo: Optional[TimeInfo] = Field(None, description="时间信息")
    chapters: List[Chapter] = Field(default_factory=list, description="章节列表")
    lawSource: Optional[str] = Field(None, description="法规来源")
    remark: Optional[str] = Field(None, description="备注")
    rawContent: Optional[str] = Field(None, description="原始markdown内容")


class UpdateTaxKnowledgeRequest(BaseModel):
    """更新税务知识文档请求"""
    docType: Optional[str] = Field(None, description="文档类型")
    lawId: Optional[str] = Field(None, description="法规ID")
    lawName: Optional[str] = Field(None, description="法规名称")
    lawStatus: Optional[str] = Field(None, description="法规状态")
    promulgationAnnouncement: Optional[PromulgationAnnouncement] = Field(None, description="发布公告信息")
    approvalInfo: Optional[str] = Field(None, description="审批信息")
    timeInfo: Optional[TimeInfo] = Field(None, description="时间信息")
    chapters: Optional[List[Chapter]] = Field(None, description="章节列表")
    lawSource: Optional[str] = Field(None, description="法规来源")
    remark: Optional[str] = Field(None, description="备注")
    rawContent: Optional[str] = Field(None, description="原始markdown内容")


# ============================================================================
# 响应模型
# ============================================================================

class TaxKnowledgeResponse(BaseModel):
    """税务知识文档响应"""
    id: int = Field(..., description="主键ID")
    docId: str = Field(..., description="文档ID")
    docType: str = Field(..., description="文档类型")
    lawId: str = Field(..., description="法规ID")
    lawName: str = Field(..., description="法规名称")
    rawContent: Optional[str] = Field(None, description="原始markdown内容")
    jsonContent: Optional[Dict[str, Any]] = Field(None, description="清洗后的JSON内容")
    createdBy: Optional[str] = Field(None, description="创建人")
    createdAt: datetime = Field(..., description="创建时间")
    updatedAt: datetime = Field(..., description="更新时间")
