"""税务知识文档 Service 层（简化版）"""
from typing import Any, Dict, List, Optional

from app.schemas.tax_knowledge import (
    CreateTaxKnowledgeRequest,
    UpdateTaxKnowledgeRequest,
)
from app.services.tax_knowledge.tax_knowledge_repository import tax_knowledge_repository


class TaxKnowledgeService:
    """税务知识文档业务逻辑层"""

    def __init__(self):
        self.repository = tax_knowledge_repository

    def create_document(
        self,
        request: CreateTaxKnowledgeRequest,
        created_by: Optional[str] = None,
    ) -> Optional[str]:
        """创建税务知识文档

        Returns:
            doc_id: 创建成功返回文档ID，失败返回None
        """
        # 构建前端格式的 JSON 内容
        json_content = {
            "docType": request.docType,
            "lawId": request.lawId,
            "lawName": request.lawName,
            "lawStatus": request.lawStatus,
            "promulgationAnnouncement": request.promulgationAnnouncement.dict() if request.promulgationAnnouncement else None,
            "approvalInfo": request.approvalInfo,
            "timeInfo": request.timeInfo.dict() if request.timeInfo else None,
            "chapters": [ch.dict() for ch in request.chapters],
            "lawSource": request.lawSource,
            "remark": request.remark,
        }

        return self.repository.create_document(
            doc_type=request.docType,
            law_id=request.lawId,
            law_name=request.lawName,
            json_content=json_content,
            raw_content=request.rawContent,
            created_by=created_by,
        )

    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """获取文档详情"""
        return self.repository.get_document_by_id(doc_id)

    def get_document_by_law_id(self, law_id: str) -> Optional[Dict[str, Any]]:
        """根据法规ID获取文档详情"""
        return self.repository.get_document_by_law_id(law_id)

    def list_documents(
        self,
        doc_type: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """查询文档列表"""
        return self.repository.list_documents(
            doc_type=doc_type,
            keyword=keyword,
            page=page,
            page_size=page_size,
        )

    def update_document(
        self,
        doc_id: str,
        request: UpdateTaxKnowledgeRequest,
    ) -> bool:
        """更新文档"""
        # 构建前端格式的 JSON 内容
        json_content = None
        if any([
            request.docType is not None,
            request.lawId is not None,
            request.lawName is not None,
            request.lawStatus is not None,
            request.promulgationAnnouncement is not None,
            request.approvalInfo is not None,
            request.timeInfo is not None,
            request.chapters is not None,
            request.lawSource is not None,
            request.remark is not None,
        ]):
            # 获取现有文档
            existing = self.repository.get_document_by_id(doc_id)
            if not existing:
                return False

            # 合并更新
            existing_json = existing.get("jsonContent") or {}
            json_content = {
                "docType": request.docType if request.docType is not None else existing_json.get("docType"),
                "lawId": request.lawId if request.lawId is not None else existing_json.get("lawId"),
                "lawName": request.lawName if request.lawName is not None else existing_json.get("lawName"),
                "lawStatus": request.lawStatus if request.lawStatus is not None else existing_json.get("lawStatus"),
                "promulgationAnnouncement": request.promulgationAnnouncement.dict() if request.promulgationAnnouncement else existing_json.get("promulgationAnnouncement"),
                "approvalInfo": request.approvalInfo if request.approvalInfo is not None else existing_json.get("approvalInfo"),
                "timeInfo": request.timeInfo.dict() if request.timeInfo else existing_json.get("timeInfo"),
                "chapters": [ch.dict() for ch in request.chapters] if request.chapters is not None else existing_json.get("chapters", []),
                "lawSource": request.lawSource if request.lawSource is not None else existing_json.get("lawSource"),
                "remark": request.remark if request.remark is not None else existing_json.get("remark"),
            }

        return self.repository.update_document(
            doc_id=doc_id,
            doc_type=request.docType,
            law_id=request.lawId,
            law_name=request.lawName,
            json_content=json_content,
            raw_content=request.rawContent,
        )

    def delete_document(self, doc_id: str, hard_delete: bool = False) -> bool:
        """删除文档

        Args:
            doc_id: 文档ID
            hard_delete: 是否硬删除
        """
        return self.repository.delete_document(doc_id, hard_delete=hard_delete)

    def get_frontend_list(
        self,
        doc_type: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """获取前端格式文档列表（仅返回基本字段）"""
        result = self.list_documents(
            doc_type=doc_type,
            keyword=keyword,
            page=page,
            page_size=page_size,
        )

        # 转换为前端格式（基本字段 + remark）
        tax_knowledge = []
        for item in result["items"]:
            tax_knowledge.append({
                "docId": item.get("docId"),
                "docType": item.get("docType"),
                "lawId": item.get("lawId"),
                "lawName": item.get("lawName"),
                "remark": item.get("remark"),
            })

        return {
            "items": tax_knowledge,
            "total": result["total"],
            "page": result["page"],
            "page_size": result["page_size"],
        }

    def get_frontend_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """获取前端格式文档详情（直接返回 json_content）"""
        doc = self.repository.get_document_by_id(doc_id)
        if doc and doc.get("jsonContent"):
            return doc["jsonContent"]
        return None


# 全局实例
tax_knowledge_service = TaxKnowledgeService()
