"""税务知识文档 Repository 层（简化版）"""
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.infra.db import get_sync_engine


class TaxKnowledgeRepository:
    """税务知识文档数据访问层"""

    def __init__(self, db_schema: str = "business"):
        self.db_schema = db_schema
        self.engine = get_sync_engine()

    def create_document(
        self,
        doc_type: str,
        law_id: str,
        law_name: str,
        json_content: Dict[str, Any],
        raw_content: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> Optional[str]:
        """创建税务知识文档

        Returns:
            doc_id: 文档ID
        """
        doc_id = f"tkd_{uuid.uuid4().hex[:12]}"

        try:
            with self.engine.connect() as conn:
                sql = text(f"""
                    INSERT INTO {self.db_schema}.tax_knowledge_documents
                    (doc_id, doc_type, law_id, law_name, raw_content, json_content, created_by)
                    VALUES
                    (:doc_id, :doc_type, :law_id, :law_name, :raw_content, :json_content::jsonb, :created_by)
                    RETURNING doc_id
                """)
                result = conn.execute(
                    sql,
                    {
                        "doc_id": doc_id,
                        "doc_type": doc_type,
                        "law_id": law_id,
                        "law_name": law_name,
                        "raw_content": raw_content,
                        "json_content": json.dumps(json_content, ensure_ascii=False),
                        "created_by": created_by,
                    }
                )
                conn.commit()
                return result.scalar()
        except SQLAlchemyError as e:
            print(f"创建文档失败: {e}")
            return None

    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """根据文档ID获取文档"""
        try:
            with self.engine.connect() as conn:
                sql = text(f"""
                    SELECT
                        id, doc_id, doc_type, law_id, law_name, raw_content, json_content,
                        created_by, created_at, updated_at, status
                    FROM {self.db_schema}.tax_knowledge_documents
                    WHERE doc_id = :doc_id AND status != 'deleted'
                """)
                result = conn.execute(sql, {"doc_id": doc_id}).fetchone()
                if result:
                    return self._row_to_dict(result)
                return None
        except SQLAlchemyError as e:
            print(f"获取文档失败: {e}")
            return None

    def get_document_by_law_id(self, law_id: str) -> Optional[Dict[str, Any]]:
        """根据法规ID获取文档"""
        try:
            with self.engine.connect() as conn:
                sql = text(f"""
                    SELECT
                        id, doc_id, doc_type, law_id, law_name, raw_content, json_content,
                        created_by, created_at, updated_at, status
                    FROM {self.db_schema}.tax_knowledge_documents
                    WHERE law_id = :law_id AND status != 'deleted'
                """)
                result = conn.execute(sql, {"law_id": law_id}).fetchone()
                if result:
                    return self._row_to_dict(result)
                return None
        except SQLAlchemyError as e:
            print(f"获取文档失败: {e}")
            return None

    def list_documents(
        self,
        doc_type: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """查询文档列表（仅返回基本字段，不包含完整jsonContent）"""
        try:
            with self.engine.connect() as conn:
                # 构建查询条件
                conditions = ["status != 'deleted'"]
                params = {}

                if doc_type:
                    conditions.append("doc_type = :doc_type")
                    params["doc_type"] = doc_type
                if keyword:
                    conditions.append("(law_name ILIKE :keyword OR law_id ILIKE :keyword)")
                    params["keyword"] = f"%{keyword}%"

                where_clause = " AND ".join(conditions)

                # 查询总数
                count_sql = text(f"""
                    SELECT COUNT(*) as total
                    FROM {self.db_schema}.tax_knowledge_documents
                    WHERE {where_clause}
                """)
                total = conn.execute(count_sql, params).scalar()

                # 查询数据（返回基本字段 + remark 列）
                offset = (page - 1) * page_size
                data_sql = text(f"""
                    SELECT
                        id, doc_id, doc_type, law_id, law_name, remark,
                        created_by, created_at, updated_at
                    FROM {self.db_schema}.tax_knowledge_documents
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                    LIMIT :page_size OFFSET :offset
                """)
                params["page_size"] = page_size
                params["offset"] = offset

                rows = conn.execute(data_sql, params).fetchall()
                items = [self._row_to_dict_summary(row) for row in rows]

                return {
                    "items": items,
                    "total": total or 0,
                    "page": page,
                    "page_size": page_size,
                }
        except SQLAlchemyError as e:
            print(f"查询文档列表失败: {e}")
            return {"items": [], "total": 0, "page": page, "page_size": page_size}

    def update_document(
        self,
        doc_id: str,
        doc_type: Optional[str] = None,
        law_id: Optional[str] = None,
        law_name: Optional[str] = None,
        json_content: Optional[Dict[str, Any]] = None,
        raw_content: Optional[str] = None,
    ) -> bool:
        """更新文档"""
        try:
            with self.engine.connect() as conn:
                updates = []
                params = {"doc_id": doc_id}

                if doc_type is not None:
                    updates.append("doc_type = :doc_type")
                    params["doc_type"] = doc_type
                if law_id is not None:
                    updates.append("law_id = :law_id")
                    params["law_id"] = law_id
                if law_name is not None:
                    updates.append("law_name = :law_name")
                    params["law_name"] = law_name
                if raw_content is not None:
                    updates.append("raw_content = :raw_content")
                    params["raw_content"] = raw_content
                if json_content is not None:
                    updates.append("json_content = :json_content::jsonb")
                    params["json_content"] = json.dumps(json_content, ensure_ascii=False)

                if not updates:
                    return True

                sql = text(f"""
                    UPDATE {self.db_schema}.tax_knowledge_documents
                    SET {', '.join(updates)}
                    WHERE doc_id = :doc_id AND status != 'deleted'
                """)
                conn.execute(sql, params)
                conn.commit()
                return True
        except SQLAlchemyError as e:
            print(f"更新文档失败: {e}")
            return False

    def delete_document(self, doc_id: str, hard_delete: bool = False) -> bool:
        """删除文档

        Args:
            doc_id: 文档ID
            hard_delete: 是否硬删除（物理删除），默认软删除
        """
        try:
            with self.engine.connect() as conn:
                if hard_delete:
                    # 硬删除：物理删除记录
                    sql = text(f"""
                        DELETE FROM {self.db_schema}.tax_knowledge_documents
                        WHERE doc_id = :doc_id
                    """)
                else:
                    # 软删除：标记为 deleted
                    sql = text(f"""
                        UPDATE {self.db_schema}.tax_knowledge_documents
                        SET status = 'deleted'
                        WHERE doc_id = :doc_id
                    """)
                conn.execute(sql, {"doc_id": doc_id})
                conn.commit()
                return True
        except SQLAlchemyError as e:
            print(f"删除文档失败: {e}")
            return False

    def _row_to_dict(self, row) -> Dict[str, Any]:
        """将数据库行转换为字典（完整信息）"""
        return {
            "id": row.id,
            "docId": row.doc_id,
            "docType": row.doc_type,
            "lawId": row.law_id,
            "lawName": row.law_name,
            "rawContent": row.raw_content,
            "jsonContent": row.json_content,
            "createdBy": row.created_by,
            "createdAt": row.created_at,
            "updatedAt": row.updated_at,
        }

    def _row_to_dict_summary(self, row) -> Dict[str, Any]:
        """将数据库行转换为字典（摘要信息，不含jsonContent和rawContent）"""
        return {
            "id": row.id,
            "docId": row.doc_id,
            "docType": row.doc_type,
            "lawId": row.law_id,
            "lawName": row.law_name,
            "remark": row.remark,  # remark 独立列，通过触发器与 json_content 同步
            "createdBy": row.created_by,
            "createdAt": row.created_at,
            "updatedAt": row.updated_at,
        }


# 全局实例
tax_knowledge_repository = TaxKnowledgeRepository()
