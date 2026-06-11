"""知识库类型数据访问层"""
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from app.infra.db import get_sync_engine


class KnowledgeTypeRepository:
    """知识库类型数据访问层"""

    def __init__(self, db_schema: str = "knowledge"):
        self.db_schema = db_schema
        self.engine = get_sync_engine()

    def create_knowledge_type(self, type_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """创建知识库类型"""
        try:
            type_id = type_data.get("type_id") or f"type_{uuid.uuid4().hex[:8]}"

            with self.engine.connect() as conn:
                sql = text(f"""
                    INSERT INTO {self.db_schema}.knowledge_types
                    (type_id, type_name, type_code, description, icon, sort_order, is_system, status)
                    VALUES (:type_id, :type_name, :type_code, :description, :icon, :sort_order, :is_system, :status)
                    RETURNING type_id, type_name, type_code, description, icon, sort_order, is_system, status,
                              created_at, updated_at
                """)
                result = conn.execute(sql, {
                    "type_id": type_id,
                    "type_name": type_data["type_name"],
                    "type_code": type_data["type_code"],
                    "description": type_data.get("description"),
                    "icon": type_data.get("icon"),
                    "sort_order": type_data.get("sort_order", 0),
                    "is_system": type_data.get("is_system", False),
                    "status": type_data.get("status", "active")
                })
                conn.commit()

                row = result.fetchone()
                if row:
                    return {
                        "type_id": row[0],
                        "type_name": row[1],
                        "type_code": row[2],
                        "description": row[3],
                        "icon": row[4],
                        "sort_order": row[5],
                        "is_system": row[6],
                        "status": row[7],
                        "created_at": row[8].isoformat() if row[8] else None,
                        "updated_at": row[9].isoformat() if row[9] else None
                    }
        except Exception as e:
            print(f"创建知识库类型失败: {e}")
            return None

    def get_knowledge_type_by_id(self, type_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取知识库类型"""
        try:
            with self.engine.connect() as conn:
                sql = text(f"""
                    SELECT type_id, type_name, type_code, description, icon, sort_order, is_system, status,
                           created_at, updated_at
                    FROM {self.db_schema}.knowledge_types
                    WHERE type_id = :type_id
                """)
                result = conn.execute(sql, {"type_id": type_id})
                row = result.fetchone()

                if row:
                    return {
                        "type_id": row[0],
                        "type_name": row[1],
                        "type_code": row[2],
                        "description": row[3],
                        "icon": row[4],
                        "sort_order": row[5],
                        "is_system": row[6],
                        "status": row[7],
                        "created_at": row[8].isoformat() if row[8] else None,
                        "updated_at": row[9].isoformat() if row[9] else None
                    }
        except Exception as e:
            print(f"获取知识库类型失败: {e}")
            return None

    def get_knowledge_type_by_code(self, type_code: str) -> Optional[Dict[str, Any]]:
        """根据代码获取知识库类型"""
        try:
            with self.engine.connect() as conn:
                sql = text(f"""
                    SELECT type_id, type_name, type_code, description, icon, sort_order, is_system, status,
                           created_at, updated_at
                    FROM {self.db_schema}.knowledge_types
                    WHERE type_code = :type_code
                """)
                result = conn.execute(sql, {"type_code": type_code})
                row = result.fetchone()

                if row:
                    return {
                        "type_id": row[0],
                        "type_name": row[1],
                        "type_code": row[2],
                        "description": row[3],
                        "icon": row[4],
                        "sort_order": row[5],
                        "is_system": row[6],
                        "status": row[7],
                        "created_at": row[8].isoformat() if row[8] else None,
                        "updated_at": row[9].isoformat() if row[9] else None
                    }
        except Exception as e:
            print(f"获取知识库类型失败: {e}")
            return None

    def list_knowledge_types(
        self,
        status: Optional[str] = None,
        is_system: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """获取知识库类型列表"""
        try:
            with self.engine.connect() as conn:
                conditions = []
                params = {}

                if status:
                    conditions.append("status = :status")
                    params["status"] = status

                if is_system is not None:
                    conditions.append("is_system = :is_system")
                    params["is_system"] = is_system

                where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

                sql = text(f"""
                    SELECT type_id, type_name, type_code, description, icon, sort_order, is_system, status,
                           created_at, updated_at
                    FROM {self.db_schema}.knowledge_types
                    {where_clause}
                    ORDER BY sort_order ASC, created_at ASC
                """)
                result = conn.execute(sql, params)

                types = []
                for row in result:
                    types.append({
                        "type_id": row[0],
                        "type_name": row[1],
                        "type_code": row[2],
                        "description": row[3],
                        "icon": row[4],
                        "sort_order": row[5],
                        "is_system": row[6],
                        "status": row[7],
                        "created_at": row[8].isoformat() if row[8] else None,
                        "updated_at": row[9].isoformat() if row[9] else None
                    })

                return types
        except Exception as e:
            print(f"获取知识库类型列表失败: {e}")
            return []

    def update_knowledge_type(self, type_id: str, update_data: Dict[str, Any]) -> bool:
        """更新知识库类型"""
        try:
            # 构建更新字段
            update_fields = []
            params = {"type_id": type_id}

            for key in ["type_name", "description", "icon", "sort_order", "status"]:
                if key in update_data:
                    update_fields.append(f"{key} = :{key}")
                    params[key] = update_data[key]

            if not update_fields:
                return False

            with self.engine.connect() as conn:
                sql = text(f"""
                    UPDATE {self.db_schema}.knowledge_types
                    SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                    WHERE type_id = :type_id
                """)
                conn.execute(sql, params)
                conn.commit()
                return True
        except Exception as e:
            print(f"更新知识库类型失败: {e}")
            return False

    def delete_knowledge_type(self, type_id: str, allow_system: bool = False) -> bool:
        """删除知识库类型"""
        try:
            with self.engine.connect() as conn:
                # 先检查是否是系统类型
                check_sql = text(f"""
                    SELECT is_system FROM {self.db_schema}.knowledge_types
                    WHERE type_id = :type_id
                """)
                result = conn.execute(check_sql, {"type_id": type_id})
                row = result.fetchone()

                if not row:
                    return False

                # 如果不允许删除系统类型
                if not allow_system and row[0]:  # is_system = True
                    return False

                # 删除类型（管理员可删除系统类型）
                if allow_system:
                    delete_sql = text(f"""
                        DELETE FROM {self.db_schema}.knowledge_types
                        WHERE type_id = :type_id
                    """)
                else:
                    delete_sql = text(f"""
                        DELETE FROM {self.db_schema}.knowledge_types
                        WHERE type_id = :type_id AND is_system = false
                    """)
                conn.execute(delete_sql, {"type_id": type_id})
                conn.commit()
                return True
        except Exception as e:
            print(f"删除知识库类型失败: {e}")
            return False

    def search_knowledge_content(
        self,
        keyword: str,
        user_id: Optional[str] = None,
        type_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """搜索知识库内容

        Args:
            keyword: 搜索关键词
            user_id: 用户ID（可选，如果提供则只搜索该用户的知识库）
            type_id: 知识库类型ID（可选，用于筛选）
            limit: 返回结果数量
            offset: 偏移量

        Returns:
            搜索结果列表
        """
        try:
            with self.engine.connect() as conn:
                # 如果指定了类型，从注册表获取对应的知识库表
                if type_id:
                    registry_sql = text(f"""
                        SELECT table_name
                        FROM {self.db_schema}.knowledge_base_registry
                        WHERE type_id = :type_id
                        AND status = 'active'
                        AND (deleted_at IS NULL OR status != 'deleted')
                    """)
                    params = {"type_id": type_id}
                    if user_id:
                        registry_sql = text(f"""
                            SELECT table_name
                            FROM {self.db_schema}.knowledge_base_registry
                            WHERE type_id = :type_id
                            AND user_id = :user_id
                            AND status = 'active'
                            AND (deleted_at IS NULL OR status != 'deleted')
                        """)
                        params["user_id"] = user_id

                    result = conn.execute(registry_sql, params)
                    tables = [row[0] for row in result]
                else:
                    # 否则从 information_schema 获取知识库表
                    tables = []
                    table_conditions = ["table_name LIKE 'kb_%'"]

                    if user_id:
                        table_conditions.append("table_name LIKE :user_pattern")

                    # 构建查询知识库表的SQL
                    tables_sql = text(f"""
                        SELECT table_name
                        FROM information_schema.tables
                        WHERE table_schema = :schema
                        AND {' AND '.join(table_conditions)}
                        ORDER BY table_name
                    """)

                    params = {"schema": self.db_schema}
                    if user_id:
                        params["user_pattern"] = f"kb_{user_id}_%"

                    result = conn.execute(tables_sql, params)
                    tables = [row[0] for row in result]

                if not tables:
                    return []

                # 在每个知识库表中搜索关键词
                search_results = []

                for table in tables:
                    try:
                        # 使用 PostgreSQL 全文搜索
                        search_sql = text(f"""
                            SELECT
                                id,
                                name,
                                meta_data->>'filename' as filename,
                                meta_data->>'doc_id' as doc_id,
                                CASE
                                    WHEN LENGTH(data) > 200 THEN SUBSTRING(data FROM 0 FOR 200) || '...'
                                    ELSE data
                                END as content_preview,
                                ts_rank(to_tsvector('chinese', coalesce(data, '')), plainto_tsquery('chinese', :keyword)) as rank
                            FROM \"{self.db_schema}\".\"{table}\"
                            WHERE to_tsvector('chinese', coalesce(data, '')) @@ plainto_tsquery('chinese', :keyword)
                               OR data ILIKE :pattern
                               OR name ILIKE :pattern
                               OR coalesce(meta_data->>'filename', '') ILIKE :pattern
                            ORDER BY rank DESC, id DESC
                            LIMIT :limit_per_table
                        """)

                        result = conn.execute(search_sql, {
                            "keyword": keyword,
                            "pattern": f"%{keyword}%",
                            "limit_per_table": 5
                        })

                        for row in result:
                            # 从表名解析用户ID和知识库名称
                            # 表名格式: kb_{user_id}_{kb_name}
                            parts = table.split("_", 2)
                            if len(parts) >= 3:
                                kb_user_id = parts[1]
                                kb_name = parts[2]
                            else:
                                kb_user_id = "unknown"
                                kb_name = table

                            search_results.append({
                                "id": row[0],
                                "name": row[1],
                                "filename": row[2],
                                "doc_id": row[3],
                                "content_preview": row[4],
                                "rank": float(row[5]) if row[5] else 0,
                                "table_name": table,
                                "user_id": kb_user_id,
                                "kb_name": kb_name
                            })
                    except Exception as e:
                        print(f"搜索表 {table} 失败: {e}")
                        continue

                # 按相关度排序并限制结果数量
                search_results.sort(key=lambda x: x["rank"], reverse=True)

                return search_results[offset:offset + limit]

        except Exception as e:
            print(f"搜索知识库内容失败: {e}")
            return []

    def search_knowledge_bases(
        self,
        keyword: str,
        user_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """搜索知识库（按知识库名称搜索）

        Args:
            keyword: 搜索关键词
            user_id: 用户ID（可选）
            limit: 返回结果数量
            offset: 偏移量

        Returns:
            搜索结果
        """
        try:
            with self.engine.connect() as conn:
                conditions = ["table_name LIKE 'kb_%'"]
                params = {"schema": self.db_schema, "pattern": f"%{keyword}%"}

                if user_id:
                    conditions.append("table_name LIKE :user_pattern")
                    params["user_pattern"] = f"kb_{user_id}_%"

                where_clause = f"AND {' AND '.join(conditions)}"

                # 统计总数
                count_sql = text(f"""
                    SELECT COUNT(*)
                    FROM information_schema.tables
                    WHERE table_schema = :schema
                    {where_clause}
                """)
                total_result = conn.execute(count_sql, params)
                total = total_result.scalar() or 0

                # 查询知识库列表
                list_sql = text(f"""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = :schema
                    {where_clause}
                    ORDER BY table_name
                    LIMIT :limit OFFSET :offset
                """)
                params["limit"] = limit
                params["offset"] = offset

                result = conn.execute(list_sql, params)

                kb_list = []
                for row in result:
                    table_name = row[0]
                    # 从表名解析用户ID和知识库名称
                    parts = table_name.split("_", 2)
                    if len(parts) >= 3:
                        kb_user_id = parts[1]
                        kb_name = parts[2]
                    else:
                        kb_user_id = "unknown"
                        kb_name = table_name

                    # 统计文档数量
                    doc_count_sql = text(f'''
                        SELECT COUNT(DISTINCT
                            COALESCE(
                                (meta_data->>'filename')::text,
                                (filters->>'filename')::text,
                                name
                            )
                        ) FROM "{self.db_schema}"."{table_name}"
                    ''')
                    doc_result = conn.execute(doc_count_sql)
                    doc_count = doc_result.scalar() or 0

                    kb_list.append({
                        "table_name": table_name,
                        "user_id": kb_user_id,
                        "kb_name": kb_name,
                        "document_count": doc_count
                    })

                return {
                    "total": total,
                    "items": kb_list,
                    "limit": limit,
                    "offset": offset
                }

        except Exception as e:
            print(f"搜索知识库失败: {e}")
            return {"total": 0, "items": []}


# 全局实例
knowledge_type_repository = KnowledgeTypeRepository()
