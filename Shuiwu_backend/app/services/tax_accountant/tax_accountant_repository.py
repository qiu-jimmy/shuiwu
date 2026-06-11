"""
税务师入驻管理 - 数据访问层
"""
import uuid
import json
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, date
from sqlalchemy import text
from app.infra.db import get_sync_engine


def normalize_date_string(date_input: Optional[Union[str, date]]) -> Optional[str]:
    """将日期标准化为 PostgreSQL DATE 类型接受的格式

    支持格式:
    - datetime.date 对象: 转换为 YYYY-MM-DD 字符串
    - YYYY-MM-DD 字符串: 直接返回
    - YYYY-MM 字符串: 转换为 YYYY-MM-01 (月初)
    - None: 返回 None
    """
    if not date_input:
        return None

    # 如果是 datetime.date 对象，直接转换为字符串
    if isinstance(date_input, date):
        return date_input.isoformat()

    # 如果是字符串
    date_str = date_input.strip() if isinstance(date_input, str) else str(date_input)

    # 如果已经是完整日期格式 (YYYY-MM-DD)
    if len(date_str) == 10 and date_str[4] == '-' and date_str[7] == '-':
        return date_str

    # 如果是年月格式 (YYYY-MM)，转换为月初 (YYYY-MM-01)
    if len(date_str) == 7 and date_str[4] == '-':
        return f"{date_str}-01"

    # 尝试其他格式转换
    return date_str


def format_pg_array(items: List[str]) -> str:
    """将 Python 列表转换为 PostgreSQL 数组字面量"""
    if not items:
        return "{}"
    # 转义每个元素中的引号和反斜杠
    escaped_items = []
    for item in items:
        if item is None:
            escaped_items.append("NULL")
        else:
            # 转义特殊字符
            item_str = str(item)
            item_str = item_str.replace("\\", "\\\\")
            item_str = item_str.replace('"', '\\"')
            escaped_items.append(f'"{item_str}"')
    return "{" + ",".join(escaped_items) + "}"


class TaxAccountantRepository:
    """税务师数据访问层"""

    def __init__(self, db_schema: str = "business"):
        self.db_schema = db_schema

    # ==================== 税务师申请 ====================

    def create_application(self, application_data: Dict[str, Any]) -> Optional[str]:
        """创建税务师入驻申请"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                data = application_data.copy()

                # 处理JSONB类型字段 - 转换为 JSON 字符串
                if "work_experiences" in data and isinstance(data["work_experiences"], list):
                    data["work_experiences"] = json.dumps(data["work_experiences"], ensure_ascii=False)

                # 构建SQL - 使用命名参数
                columns = []
                param_names = []
                params = {}

                for idx, (key, value) in enumerate(data.items()):
                    if value is not None:
                        columns.append(key)
                        param_name = f"param_{idx}"
                        param_names.append(f":{param_name}")
                        # 数组类型转换为 PostgreSQL 数组字面量
                        if key in ["certificate_images", "specialty_area"] and isinstance(value, list):
                            params[param_name] = format_pg_array(value)
                        elif key in ["birth_date", "certificate_date"]:
                            # 日期字段需要标准化格式 (YYYY-MM -> YYYY-MM-01)
                            params[param_name] = normalize_date_string(value)
                        else:
                            params[param_name] = value

                # 使用字符串格式化构建 SQL（这里我们是安全的，因为列名是已知的）
                sql = "INSERT INTO " + self.db_schema + ".tax_accountant_applications (" + ', '.join(columns) + ") VALUES (" + ', '.join(param_names) + ") RETURNING application_id"

                result = conn.execute(text(sql), params)
                row = result.fetchone()
                conn.commit()
                return row[0] if row else None
        except Exception as e:
            print(f"创建税务师申请失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_application_by_id(self, application_id: str) -> Optional[Dict[str, Any]]:
        """根据申请ID获取申请"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                row = conn.execute(text(f"""
                    SELECT * FROM {self.db_schema}.tax_accountant_applications
                    WHERE application_id = :application_id
                """), {"application_id": application_id}).fetchone()

                if row:
                    result = dict(row._mapping)
                    # 解析JSONB字段
                    if result.get("work_experiences"):
                        try:
                            result["work_experiences"] = json.loads(result["work_experiences"])
                        except:
                            pass
                    return result
                return None
        except Exception as e:
            print(f"获取申请失败: {e}")
            return None

    def get_application_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """根据用户ID获取最新申请"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                row = conn.execute(text(f"""
                    SELECT * FROM {self.db_schema}.tax_accountant_applications
                    WHERE user_id = :user_id
                    ORDER BY created_at DESC
                    LIMIT 1
                """), {"user_id": user_id}).fetchone()

                if row:
                    result = dict(row._mapping)
                    # 解析JSONB字段
                    if result.get("work_experiences"):
                        try:
                            result["work_experiences"] = json.loads(result["work_experiences"])
                        except:
                            pass
                    return result
                return None
        except Exception as e:
            print(f"根据用户ID获取申请失败: {e}")
            return None

    def update_application_status(
        self,
        application_id: str,
        status: str,
        reviewed_by: str,
        reject_reason: Optional[str] = None
    ) -> bool:
        """更新申请状态"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                params = {
                    "status": status,
                    "reviewed_by": reviewed_by,
                    "reviewed_at": datetime.now(),
                    "application_id": application_id
                }

                if reject_reason:
                    params["reject_reason"] = reject_reason
                    update_fields = ["status = :status", "reviewed_by = :reviewed_by", "reviewed_at = :reviewed_at", "reject_reason = :reject_reason"]
                else:
                    update_fields = ["status = :status", "reviewed_by = :reviewed_by", "reviewed_at = :reviewed_at", "reject_reason = NULL"]

                sql = "UPDATE " + self.db_schema + ".tax_accountant_applications SET " + ', '.join(update_fields) + " WHERE application_id = :application_id"
                conn.execute(text(sql), params)
                conn.commit()
                return True
        except Exception as e:
            print(f"更新申请状态失败: {e}")
            return False

    def list_applications(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        keyword: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取申请列表"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                conditions = []
                params = {}

                if status:
                    conditions.append("status = :status")
                    params["status"] = status
                if keyword:
                    conditions.append("(real_name ILIKE :keyword1 OR phone ILIKE :keyword2 OR certificate_number ILIKE :keyword3)")
                    keyword_pattern = f"%{keyword}%"
                    params["keyword1"] = keyword_pattern
                    params["keyword2"] = keyword_pattern
                    params["keyword3"] = keyword_pattern

                where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

                # 查询总数
                count_sql = "SELECT COUNT(*) FROM " + self.db_schema + ".tax_accountant_applications " + where_clause
                total = conn.execute(text(count_sql), params if params else {}).scalar()

                # 查询列表
                params["limit"] = page_size
                params["offset"] = (page - 1) * page_size
                list_sql = "SELECT * FROM " + self.db_schema + ".tax_accountant_applications " + where_clause + " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
                rows = conn.execute(text(list_sql), params).fetchall()

                # 解析JSONB字段
                applications = []
                for row in rows:
                    app_dict = dict(row._mapping)
                    if app_dict.get("work_experiences"):
                        try:
                            app_dict["work_experiences"] = json.loads(app_dict["work_experiences"])
                        except:
                            pass
                    applications.append(app_dict)

                return {
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "applications": applications
                }
        except Exception as e:
            print(f"获取申请列表失败: {e}")
            return {"total": 0, "page": page, "page_size": page_size, "applications": []}

    def get_application_stats(self) -> Dict[str, int]:
        """获取申请统计"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                # 总申请数
                total = conn.execute(text(f"""
                    SELECT COUNT(*) FROM {self.db_schema}.tax_accountant_applications
                """)).scalar()

                # 待审核数
                pending = conn.execute(text(f"""
                    SELECT COUNT(*) FROM {self.db_schema}.tax_accountant_applications
                    WHERE status = 'pending'
                """)).scalar()

                # 已通过数
                approved = conn.execute(text(f"""
                    SELECT COUNT(*) FROM {self.db_schema}.tax_accountant_applications
                    WHERE status = 'approved'
                """)).scalar()

                # 已拒绝数
                rejected = conn.execute(text(f"""
                    SELECT COUNT(*) FROM {self.db_schema}.tax_accountant_applications
                    WHERE status = 'rejected'
                """)).scalar()

                return {
                    "total_applications": total,
                    "pending_count": pending,
                    "approved_count": approved,
                    "rejected_count": rejected
                }
        except Exception as e:
            print(f"获取申请统计失败: {e}")
            return {
                "total_applications": 0,
                "pending_count": 0,
                "approved_count": 0,
                "rejected_count": 0
            }

    # ==================== 税务师信息 ====================

    def create_accountant(self, accountant_data: Dict[str, Any]) -> Optional[str]:
        """创建税务师记录"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                data = accountant_data.copy()

                # 处理JSONB类型字段 - 转换为 JSON 字符串
                if "work_experiences" in data and isinstance(data["work_experiences"], list):
                    data["work_experiences"] = json.dumps(data["work_experiences"], ensure_ascii=False)

                # 构建SQL - 使用命名参数
                columns = []
                param_names = []
                params = {}

                for idx, (key, value) in enumerate(data.items()):
                    if value is not None:
                        columns.append(key)
                        param_name = f"param_{idx}"
                        param_names.append(f":{param_name}")
                        # 数组类型转换为 PostgreSQL 数组字面量
                        if key == "specialty_area" and isinstance(value, list):
                            params[param_name] = format_pg_array(value)
                        elif key in ["birth_date", "certificate_date"]:
                            # 日期字段需要标准化格式 (YYYY-MM -> YYYY-MM-01)
                            params[param_name] = normalize_date_string(value)
                        else:
                            params[param_name] = value

                # 使用字符串格式化构建 SQL
                sql = "INSERT INTO " + self.db_schema + ".tax_accountants (" + ', '.join(columns) + ") VALUES (" + ', '.join(param_names) + ") RETURNING accountant_id"

                result = conn.execute(text(sql), params)
                row = result.fetchone()
                conn.commit()
                return row[0] if row else None
        except Exception as e:
            print(f"创建税务师记录失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_accountant_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """根据用户ID获取税务师"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                row = conn.execute(text(f"""
                    SELECT ta.*, u.nickname, u.avatar_url
                    FROM {self.db_schema}.tax_accountants ta
                    LEFT JOIN {self.db_schema}.users u ON ta.user_id = u.user_id
                    WHERE ta.user_id = :user_id
                """), {"user_id": user_id}).fetchone()

                if row:
                    result = dict(row._mapping)
                    # 解析JSONB字段
                    if result.get("work_experiences"):
                        try:
                            result["work_experiences"] = json.loads(result["work_experiences"])
                        except:
                            pass
                    return result
                return None
        except Exception as e:
            print(f"根据用户ID获取税务师失败: {e}")
            return None

    def get_accountant_by_id(self, accountant_id: str) -> Optional[Dict[str, Any]]:
        """根据税务师ID获取税务师"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                row = conn.execute(text(f"""
                    SELECT ta.*, u.nickname, u.avatar_url
                    FROM {self.db_schema}.tax_accountants ta
                    LEFT JOIN {self.db_schema}.users u ON ta.user_id = u.user_id
                    WHERE ta.accountant_id = :accountant_id
                """), {"accountant_id": accountant_id}).fetchone()

                if row:
                    result = dict(row._mapping)
                    # 解析JSONB字段
                    if result.get("work_experiences"):
                        try:
                            result["work_experiences"] = json.loads(result["work_experiences"])
                        except:
                            pass
                    return result
                return None
        except Exception as e:
            print(f"获取税务师失败: {e}")
            return None

    def list_accountants(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        keyword: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取税务师列表"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                conditions = []
                params = {}

                if status:
                    conditions.append("ta.status = :status")
                    params["status"] = status
                if keyword:
                    conditions.append("(ta.real_name ILIKE :keyword1 OR ta.phone ILIKE :keyword2)")
                    keyword_pattern = f"%{keyword}%"
                    params["keyword1"] = keyword_pattern
                    params["keyword2"] = keyword_pattern

                where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

                # 查询总数
                count_sql = "SELECT COUNT(*) FROM " + self.db_schema + ".tax_accountants ta " + where_clause
                total = conn.execute(text(count_sql), params if params else {}).scalar()

                # 查询列表
                params["limit"] = page_size
                params["offset"] = (page - 1) * page_size
                list_sql = "SELECT ta.*, u.nickname, u.avatar_url FROM " + self.db_schema + ".tax_accountants ta LEFT JOIN " + self.db_schema + ".users u ON ta.user_id = u.user_id " + where_clause + " ORDER BY ta.created_at DESC LIMIT :limit OFFSET :offset"
                rows = conn.execute(text(list_sql), params).fetchall()

                # 解析JSONB字段
                accountants = []
                for row in rows:
                    acc_dict = dict(row._mapping)
                    if acc_dict.get("work_experiences"):
                        try:
                            acc_dict["work_experiences"] = json.loads(acc_dict["work_experiences"])
                        except:
                            pass
                    accountants.append(acc_dict)

                return {
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "accountants": accountants
                }
        except Exception as e:
            print(f"获取税务师列表失败: {e}")
            return {"total": 0, "page": page, "page_size": page_size, "accountants": []}

    def update_accountant(self, accountant_id: str, update_data: Dict[str, Any]) -> bool:
        """更新税务师信息"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                update_fields = []
                params = {"accountant_id": accountant_id}

                for key, value in update_data.items():
                    if value is not None:
                        param_name = f"param_{key}"
                        if key == "specialty_area" and isinstance(value, list):
                            # 数组类型转换为 PostgreSQL 数组字面量，不需要类型转换（PostgreSQL会从格式推断）
                            update_fields.append(key + " = :" + param_name)
                            params[param_name] = format_pg_array(value)
                        elif key == "work_experiences" and isinstance(value, list):
                            # JSONB类型使用 CAST
                            update_fields.append(key + " = CAST(:" + param_name + " AS jsonb)")
                            params[param_name] = json.dumps(value, ensure_ascii=False)
                        else:
                            update_fields.append(key + " = :" + param_name)
                            params[param_name] = value

                if update_fields:
                    params["updated_at"] = datetime.now()
                    update_fields.append("updated_at = :updated_at")

                    sql = "UPDATE " + self.db_schema + ".tax_accountants SET " + ', '.join(update_fields) + " WHERE accountant_id = :accountant_id"
                    conn.execute(text(sql), params)
                    conn.commit()
                    return True
            return False
        except Exception as e:
            print(f"更新税务师信息失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def update_accountant_status(self, accountant_id: str, status: str) -> bool:
        """更新税务师状态"""
        return self.update_accountant(accountant_id, {"status": status})

    def increment_service_count(self, accountant_id: str) -> bool:
        """增加服务次数"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                conn.execute(text(f"""
                    UPDATE {self.db_schema}.tax_accountants
                    SET service_count = service_count + 1
                    WHERE accountant_id = :accountant_id
                """), {"accountant_id": accountant_id})
                conn.commit()
                return True
        except Exception as e:
            print(f"增加服务次数失败: {e}")
            return False

    def get_active_accountants_count(self) -> int:
        """获取活跃税务师数量"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                count = conn.execute(text(f"""
                    SELECT COUNT(*) FROM {self.db_schema}.tax_accountants
                    WHERE status = 'active'
                """)).scalar()
                return count
        except Exception as e:
            print(f"获取活跃税务师数量失败: {e}")
            return 0


# 全局实例
tax_accountant_repository = TaxAccountantRepository()
