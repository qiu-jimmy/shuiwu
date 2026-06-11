"""知识库数据访问层

负责所有与数据库相关的操作，包括：
- 查询知识库表列表
- 检查知识库表是否存在
- 删除知识库表
- 查询知识库文档信息
- 知识库注册表管理（与类型关联）
"""
import sqlalchemy
from typing import Any, Dict, List, Optional
from sqlalchemy import text

from app.infra.db import get_sync_engine


class KnowledgeRepository:
    """知识库数据访问层"""

    def __init__(self, db_schema: str = "knowledge"):
        self.db_schema = db_schema
        self.engine = get_sync_engine()
        self.registry_table = f"{db_schema}.knowledge_base_registry"
    
    def list_knowledge_base_tables(self, user_id: Optional[str] = None) -> List[str]:
        """列出所有知识库表名
        
        Args:
            user_id: 用户ID，如果提供则只返回该用户的知识库表
            
        Returns:
            知识库表名列表（不包含 schema 前缀）
        """
        try:
            inspector = sqlalchemy.inspect(self.engine)
            all_tables = inspector.get_table_names(schema=self.db_schema)
            
            # 过滤出知识库表（以 kb_ 开头）
            kb_tables = [t for t in all_tables if t.startswith("kb_")]
            
            if user_id:
                # 进一步过滤出该用户的知识库表
                kb_tables = [t for t in kb_tables if t.startswith(f"kb_{user_id}_")]
            
            return kb_tables
        except Exception as e:
            print(f"列出知识库表失败: {e}")
            return []
    
    def check_knowledge_base_exists(self, table_name: str) -> bool:
        """检查知识库表是否存在

        Args:
            table_name: 表名（不包含 schema 前缀）

        Returns:
            表是否存在
        """
        try:
            inspector = sqlalchemy.inspect(self.engine)
            tables = inspector.get_table_names(schema=self.db_schema)
            return table_name in tables
        except Exception as e:
            print(f"检查知识库表是否存在失败: {e}")
            return False

    def check_document_exists(self, table_name: str, filename: str) -> bool:
        """检查文档是否已在知识库中

        Args:
            table_name: 表名（不包含 schema 前缀）
            filename: 文件名

        Returns:
            文档是否存在
        """
        try:
            if not self.check_knowledge_base_exists(table_name):
                return False

            with self.engine.connect() as conn:
                # 检查 filename 是否存在（在 meta_data, filters 或 name 字段中）
                check_sql = text(
                    f"""
                    SELECT EXISTS(
                        SELECT 1
                        FROM "{self.db_schema}"."{table_name}"
                        WHERE
                            COALESCE(
                                (meta_data->>'filename')::text,
                                (filters->>'filename')::text,
                                name
                            ) = :filename
                        LIMIT 1
                    )
                    """
                )
                result = conn.execute(check_sql, {"filename": filename})
                return result.scalar() or False
        except Exception as e:
            print(f"检查文档是否存在失败: {e}")
            return False

    def check_document_in_registry(self, table_name: str, filename: str) -> bool:
        """检查文档是否已在 knowledge_base_registry 的 document_ids 中

        Args:
            table_name: 表名（不包含 schema 前缀）
            filename: 文件名

        Returns:
            文档是否在 document_ids 中
        """
        try:
            with self.engine.connect() as conn:
                # 检查 document_ids 数组中是否存在该文件名
                check_sql = text(
                    f"""
                    SELECT EXISTS(
                        SELECT 1
                        FROM {self.registry_table}
                        WHERE table_name = :table_name
                        AND EXISTS (
                            SELECT 1
                            FROM jsonb_array_elements(document_ids) AS doc
                            WHERE doc->>'filename' = :filename
                        )
                        LIMIT 1
                    )
                    """
                )
                result = conn.execute(check_sql, {"table_name": table_name, "filename": filename})
                return result.scalar() or False
        except Exception as e:
            print(f"检查 document_ids 是否存在失败: {e}")
            return False
    
    def delete_knowledge_base_table(self, table_name: str) -> bool:
        """删除知识库表
        
        Args:
            table_name: 表名（不包含 schema 前缀）
            
        Returns:
            是否删除成功
        """
        try:
            with self.engine.connect() as conn:
                sql = text(f'DROP TABLE IF EXISTS {self.db_schema}."{table_name}"')
                conn.execute(sql)
                conn.commit()
            return True
        except Exception as e:
            print(f"删除知识库表失败: {e}")
            return False
    
    def get_knowledge_base_info(self, table_name: str) -> Optional[Dict[str, Any]]:
        """获取知识库信息

        Args:
            table_name: 表名（不包含 schema 前缀）

        Returns:
            知识库信息字典，包含文档数量等
        """
        try:
            if not self.check_knowledge_base_exists(table_name):
                return None

            # 优先从 knowledge_base_registry 查询真实的 kb_name 和 user_id
            registry_info = self.get_knowledge_base_registry(table_name)
            if registry_info:
                kb_name = registry_info.get("kb_name", table_name)
                user_id = registry_info.get("user_id", "unknown")
                description = registry_info.get("description", "")
                is_system = registry_info.get("is_system", False)  # ✅ 提取 is_system 字段
            else:
                # 兜底：从表名解析（仅用于未注册到 registry 的旧表）
                parts = table_name.split("_", 2)
                if len(parts) >= 3:
                    user_id = parts[1]
                    kb_name = parts[2]
                else:
                    user_id = "unknown"
                    kb_name = table_name
                description = ""
                is_system = False  # 未注册的知识库默认不是系统知识库

            # 统计"文档数量"，而不是分块数量：
            # 对齐 Back 项目的实现：按去重后的 filename 数量统计
            document_count = 0
            with self.engine.connect() as conn:
                try:
                    # 优先从 meta_data / filters / name 中提取 filename 并去重计数
                    count_sql = text(
                        f"""
                        SELECT COUNT(DISTINCT
                            COALESCE(
                                (meta_data->>'filename')::text,
                                (filters->>'filename')::text,
                                name
                            )
                        ) AS doc_count
                        FROM "{self.db_schema}"."{table_name}"
                        """
                    )
                    result = conn.execute(count_sql)
                    document_count = result.scalar() or 0
                except Exception as e:
                    print(f"统计表 {table_name} 文档数失败: {e}")
                    # 兜底：简单 COUNT(*)，避免整个接口失败
                    try:
                        fallback_sql = text(
                            f'SELECT COUNT(*) AS doc_count FROM "{self.db_schema}"."{table_name}"'
                        )
                        result = conn.execute(fallback_sql)
                        document_count = result.scalar() or 0
                    except Exception as inner_e:
                        print(f"文档数兜底统计失败: {inner_e}")
                        document_count = 0

                return {
                    "kb_name": kb_name,
                    "user_id": user_id,
                    "table_name": table_name,
                    "document_count": document_count,
                    "description": description,
                    "is_system": is_system,  # ✅ 添加 is_system 字段
                }
        except Exception as e:
            print(f"获取知识库信息失败: {e}")
            return None
    
    def list_knowledge_bases(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出所有知识库信息
        
        Args:
            user_id: 用户ID，如果提供则只返回该用户的知识库
            
        Returns:
            知识库信息列表
        """
        kb_list = []
        try:
            tables = self.list_knowledge_base_tables(user_id)
            for table_name in tables:
                kb_info = self.get_knowledge_base_info(table_name)
                if kb_info:
                    kb_list.append(kb_info)
        except Exception as e:
            print(f"列出知识库失败: {e}")
        
        return kb_list

    # ========================================================================
    # 知识库注册表管理（与类型关联）
    # ========================================================================

    def register_knowledge_base(
        self,
        table_name: str,
        kb_name: str,
        user_id: str,
        type_id: Optional[str] = None,
        description: Optional[str] = None,
        chunking_rule: str = "fixed_size",
        chunk_size: int = 5000,
        chunk_overlap: int = 200,
        embedder_model: str = "text-embedding-3-small",
        is_system: bool = False
    ) -> bool:
        """注册知识库到注册表

        Args:
            table_name: 知识库表名
            kb_name: 知识库名称
            user_id: 用户ID
            type_id: 知识库类型ID（可选）
            description: 知识库描述
            chunking_rule: 分块规则
            chunk_size: 分块大小
            chunk_overlap: 分块重叠
            embedder_model: 嵌入模型
            is_system: 是否为系统知识库

        Returns:
            是否注册成功
        """
        try:
            with self.engine.connect() as conn:
                sql = text(f"""
                    INSERT INTO {self.registry_table}
                    (table_name, kb_name, user_id, type_id, description, chunking_rule, chunk_size, chunk_overlap, embedder_model, is_system)
                    VALUES (:table_name, :kb_name, :user_id, :type_id, :description, :chunking_rule, :chunk_size, :chunk_overlap, :embedder_model, :is_system)
                    ON CONFLICT (table_name) DO UPDATE SET
                        kb_name = EXCLUDED.kb_name,
                        type_id = EXCLUDED.type_id,
                        description = EXCLUDED.description,
                        chunking_rule = EXCLUDED.chunking_rule,
                        chunk_size = EXCLUDED.chunk_size,
                        chunk_overlap = EXCLUDED.chunk_overlap,
                        embedder_model = EXCLUDED.embedder_model,
                        is_system = EXCLUDED.is_system,
                        updated_at = CURRENT_TIMESTAMP,
                        status = 'active',
                        deleted_at = NULL
                """)
                conn.execute(sql, {
                    "table_name": table_name,
                    "kb_name": kb_name,
                    "user_id": user_id,
                    "type_id": type_id,
                    "description": description,
                    "chunking_rule": chunking_rule,
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap,
                    "embedder_model": embedder_model,
                    "is_system": is_system
                })
                conn.commit()
                return True
        except Exception as e:
            print(f"注册知识库失败: {e}")
            raise  # 抛出异常，让上层知道注册失败

    def unregister_knowledge_base(self, table_name: str, soft_delete: bool = True) -> bool:
        """从注册表中删除知识库

        Args:
            table_name: 知识库表名
            soft_delete: 是否软删除（默认True）

        Returns:
            是否删除成功
        """
        try:
            with self.engine.connect() as conn:
                if soft_delete:
                    sql = text(f"""
                        UPDATE {self.registry_table}
                        SET status = 'deleted', deleted_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                        WHERE table_name = :table_name
                    """)
                else:
                    sql = text(f"DELETE FROM {self.registry_table} WHERE table_name = :table_name")
                conn.execute(sql, {"table_name": table_name})
                conn.commit()
                return True
        except Exception as e:
            print(f"从注册表删除知识库失败: {e}")
            return False

    def get_knowledge_base_registry(self, table_name: str) -> Optional[Dict[str, Any]]:
        """获取知识库注册信息

        Args:
            table_name: 知识库表名

        Returns:
            注册信息字典
        """
        try:
            with self.engine.connect() as conn:
                sql = text(f"""
                    SELECT id, table_name, kb_name, user_id, type_id, description,
                           chunking_rule, chunk_size, chunk_overlap, embedder_model,
                           status, created_at, updated_at, deleted_at, is_system
                    FROM {self.registry_table}
                    WHERE table_name = :table_name
                    AND (deleted_at IS NULL OR status != 'deleted')
                """)
                result = conn.execute(sql, {"table_name": table_name})
                row = result.fetchone()

                if row:
                    return {
                        "id": row[0],
                        "table_name": row[1],
                        "kb_name": row[2],
                        "user_id": row[3],
                        "type_id": row[4],
                        "description": row[5],
                        "chunking_rule": row[6],
                        "chunk_size": row[7],
                        "chunk_overlap": row[8],
                        "embedder_model": row[9],
                        "status": row[10],
                        "created_at": row[11].isoformat() if row[11] else None,
                        "updated_at": row[12].isoformat() if row[12] else None,
                        "deleted_at": row[13].isoformat() if row[13] else None,
                        "is_system": row[14] if len(row) > 14 else False
                    }
        except Exception as e:
            print(f"获取知识库注册信息失败: {e}")
            return None

    def get_knowledge_base_by_kb_name(self, kb_name: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """通过知识库名称查询知识库信息（不限制是否为系统知识库）

        Args:
            kb_name: 知识库名称
            user_id: 用户ID（可选，如果提供则只查询该用户的知识库）

        Returns:
            知识库注册信息字典，如果不存在则返回 None
        """
        try:
            with self.engine.connect() as conn:
                sql_parts = [
                    f"""SELECT id, table_name, kb_name, user_id, type_id, description,
                           chunking_rule, chunk_size, chunk_overlap, embedder_model,
                           status, created_at, updated_at, deleted_at, is_system
                    FROM {self.registry_table}
                    WHERE kb_name = :kb_name"""
                ]

                # 如果指定了 user_id，添加用户过滤
                if user_id:
                    sql_parts.append("AND user_id = :user_id")

                # 只查询未删除的
                sql_parts.append("AND (deleted_at IS NULL OR status != 'deleted')")

                sql = text(" ".join(sql_parts))
                params = {"kb_name": kb_name}
                if user_id:
                    params["user_id"] = user_id

                result = conn.execute(sql, params)
                row = result.fetchone()

                if row:
                    return {
                        "id": row[0],
                        "table_name": row[1],
                        "kb_name": row[2],
                        "user_id": row[3],
                        "type_id": row[4],
                        "description": row[5],
                        "chunking_rule": row[6],
                        "chunk_size": row[7],
                        "chunk_overlap": row[8],
                        "embedder_model": row[9],
                        "status": row[10],
                        "created_at": row[11].isoformat() if row[11] else None,
                        "updated_at": row[12].isoformat() if row[12] else None,
                        "deleted_at": row[13].isoformat() if row[13] else None,
                        "is_system": row[14] if len(row) > 14 else False
                    }
        except Exception as e:
            print(f"查询知识库失败: {e}")
            return None

    def get_system_knowledge_by_name(self, kb_name: str) -> Optional[Dict[str, Any]]:
        """通过知识库名称查询系统知识库

        Args:
            kb_name: 知识库名称

        Returns:
            系统知识库注册信息字典，如果不存在或不是系统知识库则返回 None
        """
        try:
            with self.engine.connect() as conn:
                sql = text(f"""
                    SELECT id, table_name, kb_name, user_id, type_id, description,
                           chunking_rule, chunk_size, chunk_overlap, embedder_model,
                           status, created_at, updated_at, deleted_at, is_system
                    FROM {self.registry_table}
                    WHERE kb_name = :kb_name
                    AND is_system = TRUE
                    AND (deleted_at IS NULL OR status != 'deleted')
                """)
                result = conn.execute(sql, {"kb_name": kb_name})
                row = result.fetchone()

                if row:
                    return {
                        "id": row[0],
                        "table_name": row[1],
                        "kb_name": row[2],
                        "user_id": row[3],
                        "type_id": row[4],
                        "description": row[5],
                        "chunking_rule": row[6],
                        "chunk_size": row[7],
                        "chunk_overlap": row[8],
                        "embedder_model": row[9],
                        "status": row[10],
                        "created_at": row[11].isoformat() if row[11] else None,
                        "updated_at": row[12].isoformat() if row[12] else None,
                        "deleted_at": row[13].isoformat() if row[13] else None,
                        "is_system": row[14] if len(row) > 14 else False
                    }
        except Exception as e:
            print(f"查询系统知识库失败: {e}")
            return None

    def list_knowledge_bases_unified(
        self,
        user_id: Optional[str] = None,
        kb_name: Optional[str] = None,
        type_id: Optional[str] = None,
        is_system: Optional[bool] = None,
        status: str = "active"
    ) -> List[Dict[str, Any]]:
        """统一的知识库列表查询方法

        查询逻辑：
        1. is_system=true: 仅查询系统知识库
        2. is_system=false: 仅查询当前用户的个人知识库
        3. is_system=None (不传): 查询系统知识库 + 当前用户的个人知识库

        Args:
            user_id: 用户ID（从 token 中获取）
            kb_name: 知识库名称（可选，用于精确筛选）
            type_id: 知识库类型ID（可选）
            is_system: 是否仅查询系统知识库（true/false/null）
            status: 状态筛选（默认 active）

        Returns:
            知识库注册信息列表
        """
        try:
            with self.engine.connect() as conn:
                conditions = [
                    "(deleted_at IS NULL OR status != 'deleted')",
                    "status = :status"
                ]
                params = {"status": status}

                # 权限控制逻辑
                if is_system is True:
                    # 仅查询系统知识库
                    conditions.append("is_system = TRUE")
                elif is_system is False:
                    # 仅查询个人知识库
                    if user_id is None:
                        # 管理员视角：查询所有用户的个人知识库（不过滤 user_id）
                        conditions.append("is_system = FALSE")
                    else:
                        # 普通用户视角：仅查询当前用户的个人知识库
                        conditions.append("is_system = FALSE")
                        conditions.append("user_id = :user_id")
                        params["user_id"] = user_id
                else:
                    # is_system 为 None:
                    # - 如果是管理员查询（user_id=None），查询所有知识库（系统+所有用户的个人知识库）
                    # - 如果是普通用户查询，查询系统知识库 + 当前用户的个人知识库
                    if user_id is None:
                        # 管理员视角：查询所有知识库（不过滤 user_id）
                        conditions.append("(is_system = TRUE OR is_system = FALSE)")
                    else:
                        # 普通用户视角：查询系统知识库 + 当前用户的个人知识库
                        conditions.append("(is_system = TRUE OR (is_system = FALSE AND user_id = :user_id))")
                        params["user_id"] = user_id

                # 可选：按知识库名称筛选
                if kb_name:
                    conditions.append("kb_name = :kb_name")
                    params["kb_name"] = kb_name

                # 可选：按类型筛选
                if type_id:
                    conditions.append("type_id = :type_id")
                    params["type_id"] = type_id

                where_clause = f"WHERE {' AND '.join(conditions)}"

                sql = text(f"""
                    SELECT id, table_name, kb_name, user_id, type_id, description,
                           chunking_rule, chunk_size, chunk_overlap, embedder_model,
                           status, created_at, updated_at, is_system, document_ids
                    FROM {self.registry_table}
                    {where_clause}
                    ORDER BY is_system DESC, created_at DESC
                """)
                result = conn.execute(sql, params)

                kb_list = []
                for row in result:
                    # 直接使用 document_ids 的长度作为文档数量
                    doc_count = 0
                    if row[14]:  # document_ids 字段
                        try:
                            # document_ids 是 jsonb 类型，使用 jsonb_array_length 获取长度
                            doc_count = len(row[14]) if isinstance(row[14], list) else 0
                        except Exception:
                            doc_count = 0

                    kb_list.append({
                        "id": row[0],
                        "table_name": row[1],
                        "kb_name": row[2],
                        "user_id": row[3],
                        "type_id": row[4],
                        "description": row[5],
                        "chunking_rule": row[6],
                        "chunk_size": row[7],
                        "chunk_overlap": row[8],
                        "embedder_model": row[9],
                        "status": row[10],
                        "created_at": row[11].isoformat() if row[11] else None,
                        "updated_at": row[12].isoformat() if row[12] else None,
                        "is_system": row[13],
                        "document_count": doc_count
                    })

                return kb_list
        except Exception as e:
            print(f"根据类型列出知识库失败: {e}")
            return []

    def update_knowledge_base_type(self, table_name: str, type_id: str) -> bool:
        """更新知识库的类型

        Args:
            table_name: 知识库表名
            type_id: 新的类型ID

        Returns:
            是否更新成功
        """
        try:
            with self.engine.connect() as conn:
                sql = text(f"""
                    UPDATE {self.registry_table}
                    SET type_id = :type_id, updated_at = CURRENT_TIMESTAMP
                    WHERE table_name = :table_name
                """)
                conn.execute(sql, {"table_name": table_name, "type_id": type_id})
                conn.commit()
                return True
        except Exception as e:
            print(f"更新知识库类型失败: {e}")
            return False

    def count_user_knowledge_bases(self, user_id: str) -> int:
        """统计用户的知识库数量

        Args:
            user_id: 用户ID

        Returns:
            用户的有效知识库数量
        """
        try:
            with self.engine.connect() as conn:
                sql = text(f"""
                    SELECT COUNT(*) as count
                    FROM {self.registry_table}
                    WHERE user_id = :user_id
                      AND status = 'active'
                      AND deleted_at IS NULL
                """)
                result = conn.execute(sql, {"user_id": user_id}).fetchone()
                return result[0] if result else 0
        except Exception as e:
            print(f"统计用户知识库数量失败: {e}")
            return 0



    def list_all_knowledge_bases(
        self,
        keyword: Optional[str] = None,
        is_system: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """管理员视角：获取所有知识库列表（分页）

        Args:
            keyword: 搜索关键词（知识库名称）
            is_system: 是否仅查询系统知识库
            page: 页码
            page_size: 每页数量

        Returns:
            包含 total, page, page_size, knowledge_bases 的字典
        """
        try:
            kb_list = self.list_knowledge_bases_unified(
                user_id=None,  # 管理员查看所有
                kb_name=keyword,
                is_system=is_system,
                status='active'
            )

            # 简单分页
            total = len(kb_list)
            start = (page - 1) * page_size
            end = start + page_size
            paginated_list = kb_list[start:end]

            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "knowledge_bases": paginated_list
            }
        except Exception as e:
            print(f"管理员获取知识库列表失败: {e}")
            return {
                "total": 0,
                "page": page,
                "page_size": page_size,
                "knowledge_bases": []
            }



# 全局实例

    def list_all_knowledge_bases(
        self,
        keyword: Optional[str] = None,
        is_system: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """管理员视角：获取所有知识库列表（分页）

        Args:
            keyword: 搜索关键词（知识库名称）
            is_system: 是否仅查询系统知识库
            page: 页码
            page_size: 每页数量

        Returns:
            包含 total, page, page_size, knowledge_bases 的字典
        """
        try:
            kb_list = self.list_knowledge_bases_unified(
                user_id=None,  # 管理员查看所有
                kb_name=keyword,
                is_system=is_system,
                status='active'
            )

            # 简单分页
            total = len(kb_list)
            start = (page - 1) * page_size
            end = start + page_size
            paginated_list = kb_list[start:end]

            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "knowledge_bases": paginated_list
            }
        except Exception as e:
            print(f"管理员获取知识库列表失败: {e}")
            return {
                "total": 0,
                "page": page,
                "page_size": page_size,
                "knowledge_bases": []
            }





knowledge_repository = KnowledgeRepository()
