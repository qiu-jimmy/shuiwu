"""
文件管理数据访问层（Repository）
处理所有与文件数据库相关的操作
"""
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from app.infra.db import get_sync_engine


class FilesRepository:
    """文件管理数据访问层

    注意：数据库表结构通过迁移系统管理，执行迁移前请运行：
    python migrate_db.py
    """

    def __init__(self, db_schema: str = "business"):
        self.db_schema = db_schema

    def ensure_database_initialized(self):
        """确保数据库已初始化（通过迁移系统管理）

        此方法已废弃，表结构现在通过迁移文件管理。
        请确保已执行数据库迁移：python migrate_db.py
        """
        # 不再需要动态初始化，数据库结构由迁移系统管理
        pass

    def create_file(self, file_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """创建文件记录"""
        self.ensure_database_initialized()

        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                # 生成file_id（如果未提供）
                file_id = file_data.get('file_id') or str(uuid.uuid4())

                conn.execute(text(f"""
                    INSERT INTO {self.db_schema}.files
                    (file_id, user_id, file_name, file_type, file_size, file_path, file_url,
                     mime_type, category, folder_path, kb_name, status)
                    VALUES (:file_id, :user_id, :file_name, :file_type, :file_size,
                            :file_path, :file_url, :mime_type, :category, :folder_path,
                            :kb_name, :status)
                    RETURNING *
                """), {
                    "file_id": file_id,
                    "user_id": file_data['user_id'],
                    "file_name": file_data['file_name'],
                    "file_type": file_data['file_type'],
                    "file_size": file_data['file_size'],
                    "file_path": file_data['file_path'],
                    "file_url": file_data['file_url'],
                    "mime_type": file_data.get('mime_type'),
                    "category": file_data.get('category', 'document'),
                    "folder_path": file_data.get('folder_path'),
                    "kb_name": file_data.get('kb_name'),
                    "status": file_data.get('status', 'active')
                })

                conn.commit()

                # 返回创建的文件信息
                row = conn.execute(
                    text(f"SELECT * FROM {self.db_schema}.files WHERE file_id = :file_id"),
                    {"file_id": file_id}
                ).fetchone()

                if row:
                    return self._row_to_dict(row)
                return None

        except Exception as e:
            print(f"创建文件记录失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_file_by_id(self, file_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取文件信息"""
        self.ensure_database_initialized()

        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                row = conn.execute(
                    text(f"""
                        SELECT * FROM {self.db_schema}.files
                        WHERE file_id = :file_id AND is_deleted = FALSE
                    """),
                    {"file_id": file_id}
                ).fetchone()

                if row:
                    return self._row_to_dict(row)
                return None

        except Exception as e:
            print(f"获取文件信息失败: {e}")
            return None

    def list_files(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """查询文件列表（支持分页和过滤）"""
        self.ensure_database_initialized()

        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                # 构建查询条件
                conditions = ["is_deleted = FALSE"]
                params = {}

                if filters.get('user_id'):
                    conditions.append("user_id = :user_id")
                    params['user_id'] = filters['user_id']

                if filters.get('file_type'):
                    conditions.append("file_type = :file_type")
                    params['file_type'] = filters['file_type']

                if filters.get('category'):
                    conditions.append("category = :category")
                    params['category'] = filters['category']

                if filters.get('folder_path'):
                    conditions.append("folder_path = :folder_path")
                    params['folder_path'] = filters['folder_path']

                if filters.get('kb_name'):
                    conditions.append("kb_name = :kb_name")
                    params['kb_name'] = filters['kb_name']

                if filters.get('status'):
                    conditions.append("status = :status")
                    params['status'] = filters['status']

                if filters.get('keyword'):
                    conditions.append("file_name LIKE :keyword")
                    params['keyword'] = f"%{filters['keyword']}%"

                if filters.get('start_date'):
                    conditions.append("created_at >= :start_date")
                    params['start_date'] = filters['start_date']

                if filters.get('end_date'):
                    conditions.append("created_at <= :end_date")
                    params['end_date'] = filters['end_date']

                where_clause = " AND ".join(conditions)

                # 查询总数
                count_sql = f"""
                    SELECT COUNT(*) FROM {self.db_schema}.files
                    WHERE {where_clause}
                """
                total = conn.execute(text(count_sql), params).scalar()

                # 分页查询
                page = filters.get('page', 1)
                page_size = filters.get('page_size', 20)
                offset = (page - 1) * page_size

                list_sql = f"""
                    SELECT * FROM {self.db_schema}.files
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                    LIMIT :page_size OFFSET :offset
                """
                params['page_size'] = page_size
                params['offset'] = offset

                rows = conn.execute(text(list_sql), params).fetchall()

                files = [self._row_to_dict(row) for row in rows]

                return {
                    'total': total,
                    'page': page,
                    'page_size': page_size,
                    'files': files
                }

        except Exception as e:
            print(f"查询文件列表失败: {e}")
            return {'total': 0, 'page': 1, 'page_size': 20, 'files': []}

    def update_file(self, file_id: str, update_data: Dict[str, Any]) -> bool:
        """更新文件信息"""
        self.ensure_database_initialized()

        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                # 构建更新字段
                update_fields = []
                params = {"file_id": file_id}

                for key, value in update_data.items():
                    if key in ['file_name', 'folder_path', 'kb_name', 'category', 'status']:
                        update_fields.append(f"{key} = :{key}")
                        params[key] = value

                if not update_fields:
                    return False

                update_fields.append("updated_at = CURRENT_TIMESTAMP")

                sql = f"""
                    UPDATE {self.db_schema}.files
                    SET {', '.join(update_fields)}
                    WHERE file_id = :file_id AND is_deleted = FALSE
                """

                result = conn.execute(text(sql), params)
                conn.commit()

                return result.rowcount > 0

        except Exception as e:
            print(f"更新文件信息失败: {e}")
            return False

    def delete_file(self, file_id: str, permanent: bool = False) -> bool:
        """删除文件（软删除或永久删除）"""
        self.ensure_database_initialized()

        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                if permanent:
                    # 永久删除
                    sql = f"DELETE FROM {self.db_schema}.files WHERE file_id = :file_id"
                else:
                    # 软删除
                    sql = f"""
                        UPDATE {self.db_schema}.files
                        SET is_deleted = TRUE, status = 'deleted', updated_at = CURRENT_TIMESTAMP
                        WHERE file_id = :file_id
                    """

                result = conn.execute(text(sql), {"file_id": file_id})
                conn.commit()

                return result.rowcount > 0

        except Exception as e:
            print(f"删除文件失败: {e}")
            return False

    def batch_delete_files(self, file_ids: List[str], permanent: bool = False) -> int:
        """批量删除文件"""
        self.ensure_database_initialized()

        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                if permanent:
                    # 永久删除
                    sql = f"DELETE FROM {self.db_schema}.files WHERE file_id = ANY(:file_ids)"
                else:
                    # 软删除
                    sql = f"""
                        UPDATE {self.db_schema}.files
                        SET is_deleted = TRUE, status = 'deleted', updated_at = CURRENT_TIMESTAMP
                        WHERE file_id = ANY(:file_ids)
                    """

                result = conn.execute(text(sql), {"file_ids": file_ids})
                conn.commit()

                return result.rowcount

        except Exception as e:
            print(f"批量删除文件失败: {e}")
            return 0

    def check_file_exists_by_name(self, user_id: str, filename: str) -> bool:
        """根据用户ID和文件名检查文件是否已存在

        Args:
            user_id: 用户ID
            filename: 文件名

        Returns:
            文件是否存在
        """
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                sql = text(f"""
                    SELECT EXISTS(
                        SELECT 1
                        FROM {self.db_schema}.files
                        WHERE user_id = :user_id
                        AND file_name = :filename
                        AND is_deleted = FALSE
                        LIMIT 1
                    )
                """)
                result = conn.execute(sql, {"user_id": user_id, "filename": filename})
                return result.scalar() or False
        except Exception as e:
            print(f"检查文件是否存在失败: {e}")
            return False

    def increment_download_count(self, file_id: str) -> bool:
        """增加文件下载次数"""
        self.ensure_database_initialized()

        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                sql = f"""
                    UPDATE {self.db_schema}.files
                    SET download_count = download_count + 1
                    WHERE file_id = :file_id
                """

                result = conn.execute(text(sql), {"file_id": file_id})
                conn.commit()

                return result.rowcount > 0

        except Exception as e:
            print(f"更新下载次数失败: {e}")
            return False

    def get_files_by_ids(
        self,
        file_ids: List[str],
        user_id: Optional[str] = None,
        is_admin: bool = False
    ) -> Dict[str, Any]:
        """批量获取文件信息（返回 file_id -> file_url 的映射）

        使用临时表 + JOIN 优化，支持任意数量的 file_ids，避免 PostgreSQL ROW 表达式限制（1664 entries）。

        Args:
            file_ids: 文件ID列表
            user_id: 当前用户ID（用于权限检查）
            is_admin: 是否为管理员（管理员可以查看所有文件）

        Returns:
            文件ID到文件信息的映射 {file_id: {file_url, file_name, ...}}
        """
        try:
            if not file_ids:
                print(f"[get_files_by_ids] file_ids 为空")
                return {}

            print(f"[get_files_by_ids] 输入: file_ids 数量={len(file_ids)}, 前3个={file_ids[:3]}, user_id={user_id}, is_admin={is_admin}")

            result = {}
            engine = get_sync_engine()

            with engine.connect() as conn:
                # 获取OSS配置用于动态生成URL
                oss_config = self._get_oss_config(conn)

                # 使用临时表方案，支持任意数量的 ID
                # 先删除已存在的临时表（如果有的话），再创建新的
                conn.execute(text("DROP TABLE IF EXISTS temp_query_file_ids"))
                conn.execute(text("""
                    CREATE TEMP TABLE temp_query_file_ids (
                        file_id VARCHAR(64) PRIMARY KEY
                    )
                """))

                # 分批插入 ID 到临时表（每批 1000 个，避免单次 SQL 过长）
                insert_batch_size = 1000
                for i in range(0, len(file_ids), insert_batch_size):
                    batch_ids = file_ids[i:i + insert_batch_size]
                    # 使用 VALUES 批量插入
                    values_sql = ','.join([f"('{fid}')" for fid in batch_ids])
                    conn.execute(text(f"INSERT INTO temp_query_file_ids (file_id) VALUES {values_sql} ON CONFLICT DO NOTHING"))

                # 使用 JOIN 查询（一次查询完成）
                if is_admin:
                    sql = text(f"""
                        SELECT f.file_id, f.file_url, f.file_name, f.user_id, f.file_path
                        FROM {self.db_schema}.files f
                        INNER JOIN temp_query_file_ids t ON f.file_id = t.file_id
                        WHERE f.is_deleted = FALSE
                    """)
                    print(f"[get_files_by_ids] 管理员查询(临时表JOIN): file_ids 数量={len(file_ids)}")
                else:
                    sql = text(f"""
                        SELECT f.file_id, f.file_url, f.file_name, f.user_id, f.file_path
                        FROM {self.db_schema}.files f
                        INNER JOIN temp_query_file_ids t ON f.file_id = t.file_id
                        WHERE f.user_id = :user_id AND f.is_deleted = FALSE
                    """)
                    print(f"[get_files_by_ids] 普通用户查询(临时表JOIN): file_ids 数量={len(file_ids)}, user_id={user_id}")

                if is_admin:
                    rows = conn.execute(sql).fetchall()
                else:
                    rows = conn.execute(sql, {"user_id": user_id}).fetchall()

                print(f"[get_files_by_ids] 查询结果: 返回 {len(rows)} 行")

                # 处理查询结果
                for row in rows:
                    file_id = row[0]
                    file_url = row[1]
                    file_name = row[2]
                    row_user_id = row[3]
                    file_path = row[4] if len(row) > 4 else None

                    # 如果 file_url 为空，尝试根据 file_path 动态生成
                    if not file_url and file_path and oss_config:
                        file_url = self._generate_oss_url(file_path, oss_config)
                        if len(result) < 3:
                            print(f"[get_files_by_ids] 动态生成URL: file_id={file_id}, file_path={file_path} -> {file_url}")

                    result[file_id] = {"file_url": file_url, "file_name": file_name, "user_id": row_user_id}
                    if len(result) <= 3:
                        print(f"[get_files_by_ids] [{len(result)}] file_id={file_id}, file_url={'[有值]' if file_url else '[空]'}, file_name={file_name}")

                # 清理临时表（可选，会话结束时会自动删除）
                conn.execute(text("DROP TABLE IF EXISTS temp_query_file_ids"))

                print(f"[get_files_by_ids] 返回结果: 包含 {len(result)} 个文件, keys 前3个: {list(result.keys())[:3]}")
                return result

        except Exception as e:
            print(f"批量获取文件信息失败: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def get_file_stats(self, user_id: str, is_admin: bool = False) -> Dict[str, Any]:
        """获取文件统计信息（管理员可查看全局统计）"""
        self.ensure_database_initialized()

        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                # 构建用户过滤条件
                user_filter = "" if is_admin else "AND user_id = :user_id"

                # 总文件数和总大小
                stats_row = conn.execute(text(f"""
                    SELECT
                        COUNT(*) as total_files,
                        COALESCE(SUM(file_size), 0) as total_size,
                        COUNT(CASE WHEN DATE(created_at) = CURRENT_DATE THEN 1 END) as today_uploads,
                        COUNT(CASE WHEN DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE) THEN 1 END) as month_uploads
                    FROM {self.db_schema}.files
                    WHERE is_deleted = FALSE {user_filter}
                """), {"user_id": user_id} if not is_admin else {}).fetchone()

                # 将结果转换为字典
                stats = self._row_to_dict(stats_row) if stats_row else {
                    'total_files': 0, 'total_size': 0, 'today_uploads': 0, 'month_uploads': 0
                }

                # 按文件类型统计
                type_stats_rows = conn.execute(text(f"""
                    SELECT
                        file_type,
                        COUNT(*) as count,
                        COALESCE(SUM(file_size), 0) as size
                    FROM {self.db_schema}.files
                    WHERE is_deleted = FALSE {user_filter}
                    GROUP BY file_type
                    ORDER BY count DESC
                """), {"user_id": user_id} if not is_admin else {}).fetchall()

                # 按分类统计
                category_stats_rows = conn.execute(text(f"""
                    SELECT
                        category,
                        COUNT(*) as count,
                        COALESCE(SUM(file_size), 0) as size
                    FROM {self.db_schema}.files
                    WHERE is_deleted = FALSE {user_filter}
                    GROUP BY category
                    ORDER BY count DESC
                """), {"user_id": user_id} if not is_admin else {}).fetchall()

                # 转换统计结果
                file_type_stats = []
                for row in type_stats_rows:
                    row_dict = self._row_to_dict(row) if not isinstance(row, dict) else row
                    file_type_stats.append({
                        'file_type': row_dict.get('file_type', ''),
                        'count': row_dict.get('count', 0),
                        'size_mb': round(row_dict.get('size', 0) / (1024 * 1024), 2)
                    })

                category_stats = []
                for row in category_stats_rows:
                    row_dict = self._row_to_dict(row) if not isinstance(row, dict) else row
                    category_stats.append({
                        'category': row_dict.get('category', ''),
                        'count': row_dict.get('count', 0),
                        'size_mb': round(row_dict.get('size', 0) / (1024 * 1024), 2)
                    })

                total_size = stats.get('total_size', 0)
                total_size_mb = round(total_size / (1024 * 1024), 2)

                return {
                    'total_files': stats.get('total_files', 0),
                    'total_size': total_size,
                    'total_size_mb': total_size_mb,
                    'today_uploads': stats.get('today_uploads', 0),
                    'month_uploads': stats.get('month_uploads', 0),
                    'file_type_stats': file_type_stats,
                    'category_stats': category_stats
                }

        except Exception as e:
            print(f"获取文件统计信息失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'total_files': 0,
                'total_size': 0,
                'total_size_mb': 0,
                'today_uploads': 0,
                'month_uploads': 0,
                'file_type_stats': [],
                'category_stats': []
            }

    def _row_to_dict(self, row) -> Dict[str, Any]:
        """将数据库行转换为字典，兼容 psycopg v3 Row 对象"""
        if row is None:
            return {}

        # 如果已经是字典，直接返回
        if isinstance(row, dict):
            return row

        row_dict = {}

        # psycopg v3 和 SQLAlchemy Row 对象转换
        try:
            # 方法1：使用 _fields 或 _mapping 属性（SQLAlchemy 和 psycopg3）
            if hasattr(row, '_mapping'):
                # SQLAlchemy 2.0+ 使用 _mapping
                for key, value in row._mapping.items():
                    if hasattr(value, 'isoformat'):
                        value = value.isoformat()
                    row_dict[key] = value
            elif hasattr(row, '_fields'):
                # namedtuple 对象
                for key in row._fields:
                    value = getattr(row, key)
                    if hasattr(value, 'isoformat'):
                        value = value.isoformat()
                    row_dict[key] = value
            # 方法2：尝试通过 _attributes 获取列名（psycopg3）
            elif hasattr(row, '_attributes'):
                for i, attr in enumerate(row._attributes):
                    value = row[i]
                    if hasattr(value, 'isoformat'):
                        value = value.isoformat()
                    row_dict[attr] = value
            # 方法3：使用 dict() 构造函数
            else:
                try:
                    row_dict = dict(row)
                    # 转换 datetime 对象
                    for key, value in row_dict.items():
                        if hasattr(value, 'isoformat'):
                            row_dict[key] = value.isoformat()
                except Exception:
                    # 最后的回退方案：通过索引访问，使用已知字段名
                    field_names = [
                        'file_id', 'user_id', 'file_name', 'file_type', 'file_size',
                        'file_path', 'file_url', 'mime_type', 'category', 'folder_path',
                        'kb_name', 'status', 'is_deleted', 'download_count', 'created_at', 'updated_at',
                        'total_files', 'total_size', 'today_uploads', 'month_uploads', 'count', 'size',
                        'share_id', 'share_code', 'share_type', 'password', 'expire_time',
                        'max_access_count', 'access_count'
                    ]
                    for i, field in enumerate(field_names):
                        if i < len(row):
                            value = row[i]
                            if hasattr(value, 'isoformat'):
                                value = value.isoformat()
                            row_dict[field] = value

        except Exception as e:
            print(f"[ERROR] Exception in _row_to_dict: {e}")
            import traceback
            traceback.print_exc()
            return {}

        return row_dict

    def _get_oss_config(self, conn) -> Optional[Dict[str, str]]:
        """获取OSS配置（从数据库）"""
        try:
            import json
            row = conn.execute(text("""
                SELECT config FROM system.configs
                WHERE config_key = 'oss_settings'
            """)).fetchone()

            if not row:
                return None

            config_value = row[0]
            if isinstance(config_value, str):
                return json.loads(config_value)
            elif isinstance(config_value, dict):
                return config_value
            return None
        except Exception as e:
            print(f"[get_files_by_ids] 获取OSS配置失败: {e}")
            return None

    def _generate_oss_url(self, file_path: str, oss_config: Dict[str, str]) -> Optional[str]:
        """根据 file_path 和 OSS 配置生成下载URL"""
        try:
            bucket = oss_config.get('bucket')
            region = oss_config.get('region', 'cn-hangzhou')
            endpoint = oss_config.get('endpoint', '')

            if endpoint and endpoint.strip():
                # 使用自定义endpoint（去除协议前缀）
                endpoint_clean = endpoint.replace('https://', '').replace('http://', '').strip()
                return f"https://{bucket}.{endpoint_clean}/{file_path}"
            else:
                # 使用标准endpoint格式：bucket.oss-region.aliyuncs.com
                return f"https://{bucket}.oss-{region}.aliyuncs.com/{file_path}"
        except Exception as e:
            print(f"[get_files_by_ids] 生成OSS URL失败: {e}")
            return None


# 全局Repository实例
files_repository = FilesRepository()
