"""
会员订阅模块 - 数据访问层
"""
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import text
from app.infra.db import get_sync_engine


def _serialize_json_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """序列化 JSON 字段"""
    result = data.copy()
    if "custom_config" in result and isinstance(result["custom_config"], (dict, list)):
        result["custom_config"] = json.dumps(result["custom_config"], ensure_ascii=False)
    if "benefits" in result and isinstance(result["benefits"], (dict, list)):
        result["benefits"] = json.dumps(result["benefits"], ensure_ascii=False)
    return result


def _deserialize_json_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """反序列化 JSON 字段"""
    if "custom_config" in data and isinstance(data["custom_config"], str):
        try:
            data["custom_config"] = json.loads(data["custom_config"])
        except (json.JSONDecodeError, ValueError):
            data["custom_config"] = {}
    if "benefits" in data and isinstance(data["benefits"], str):
        try:
            data["benefits"] = json.loads(data["benefits"])
        except (json.JSONDecodeError, ValueError):
            data["benefits"] = []
    return data


class MemberRepository:
    """会员数据访问层"""

    def __init__(self, db_schema: str = "business"):
        self.db_schema = db_schema

    # ==================== 会员套餐管理 ====================

    def create_package(self, package_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """创建会员套餐"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                # 序列化 JSON 字段
                serialized_data = _serialize_json_fields(package_data)

                columns = []
                values = []

                for key, value in serialized_data.items():
                    if value is not None:
                        columns.append(key)
                        values.append(f":{key}")

                sql = f"""
                    INSERT INTO {self.db_schema}.member_packages
                    ({', '.join(columns)})
                    VALUES ({', '.join(values)})
                    RETURNING *
                """

                result = conn.execute(text(sql), serialized_data)
                conn.commit()
                row = result.fetchone()
                return _deserialize_json_fields(dict(row._mapping)) if row else None
        except Exception as e:
            print(f"创建会员套餐失败: {e}")
            return None

    def get_package_by_id(self, package_id: str) -> Optional[Dict[str, Any]]:
        """根据套餐ID获取套餐"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                row = conn.execute(text(f"""
                    SELECT * FROM {self.db_schema}.member_packages
                    WHERE package_id = :package_id
                """), {"package_id": package_id}).fetchone()

                return _deserialize_json_fields(dict(row._mapping)) if row else None
        except Exception as e:
            print(f"获取套餐失败: {e}")
            return None

    def list_packages(
        self,
        status: Optional[str] = None,
        package_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取套餐列表"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                conditions = []
                params = {}

                if status:
                    conditions.append("status = :status")
                    params["status"] = status
                if package_type:
                    conditions.append("package_type = :package_type")
                    params["package_type"] = package_type

                where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

                rows = conn.execute(text(f"""
                    SELECT * FROM {self.db_schema}.member_packages
                    {where_clause}
                    ORDER BY sort_order ASC, price ASC
                """), params).fetchall()

                return [_deserialize_json_fields(dict(row._mapping)) for row in rows]
        except Exception as e:
            print(f"获取套餐列表失败: {e}")
            return []

    def update_package(self, package_id: str, update_data: Dict[str, Any]) -> bool:
        """更新套餐"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                # 序列化 JSON 字段
                serialized_data = _serialize_json_fields(update_data)

                update_fields = []
                params = {"package_id": package_id}

                for key, value in serialized_data.items():
                    if value is not None:
                        update_fields.append(f"{key} = :{key}")
                        params[key] = value

                if update_fields:
                    params["updated_at"] = datetime.now()
                    update_fields.append("updated_at = :updated_at")

                    sql = f"""
                        UPDATE {self.db_schema}.member_packages
                        SET {', '.join(update_fields)}
                        WHERE package_id = :package_id
                    """
                    conn.execute(text(sql), params)
                    conn.commit()
                    return True
            return False
        except Exception as e:
            print(f"更新套餐失败: {e}")
            return False

    def delete_package(self, package_id: str) -> bool:
        """删除套餐（软删除，设置状态为inactive）"""
        return self.update_package(package_id, {"status": "inactive"})

    # ==================== 订单管理 ====================

    def create_order(self, order_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """创建订单"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                sql = f"""
                    INSERT INTO {self.db_schema}.orders
                    (order_id, user_id, package_id, order_type, amount, actual_amount,
                     payment_method, payment_status, package_name, duration_days,
                     original_expire_at, new_expire_at, status)
                    VALUES
                    (:order_id, :user_id, :package_id, :order_type, :amount, :actual_amount,
                     :payment_method, :payment_status, :package_name, :duration_days,
                     :original_expire_at, :new_expire_at, :status)
                    RETURNING *
                """

                result = conn.execute(text(sql), order_data)
                conn.commit()
                row = result.fetchone()
                return dict(row._mapping) if row else None
        except Exception as e:
            print(f"创建订单失败: {e}")
            return None

    def get_order_by_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        """根据订单ID获取订单"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                row = conn.execute(text(f"""
                    SELECT * FROM {self.db_schema}.orders
                    WHERE order_id = :order_id
                """), {"order_id": order_id}).fetchone()

                return dict(row._mapping) if row else None
        except Exception as e:
            print(f"获取订单失败: {e}")
            return None

    def list_orders(
        self,
        user_id: Optional[str] = None,
        payment_status: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """获取订单列表"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                conditions = []
                params = {"limit": page_size, "offset": (page - 1) * page_size}

                if user_id:
                    conditions.append("user_id = :user_id")
                    params["user_id"] = user_id
                if payment_status:
                    conditions.append("payment_status = :payment_status")
                    params["payment_status"] = payment_status
                if status:
                    conditions.append("status = :status")
                    params["status"] = status
                if start_date:
                    conditions.append("created_at >= :start_date")
                    params["start_date"] = start_date
                if end_date:
                    conditions.append("created_at <= :end_date")
                    params["end_date"] = end_date

                where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

                # 查询总数
                count_sql = f"""
                    SELECT COUNT(*) FROM {self.db_schema}.orders
                    {where_clause}
                """
                total = conn.execute(text(count_sql), params).scalar()

                # 查询列表
                list_sql = f"""
                    SELECT * FROM {self.db_schema}.orders
                    {where_clause}
                    ORDER BY created_at DESC
                    LIMIT :limit OFFSET :offset
                """
                rows = conn.execute(text(list_sql), params).fetchall()

                return {
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "orders": [dict(row._mapping) for row in rows]
                }
        except Exception as e:
            print(f"获取订单列表失败: {e}")
            return {"total": 0, "page": page, "page_size": page_size, "orders": []}

    def update_order(
        self,
        order_id: str,
        payment_status: Optional[str] = None,
        payment_time: Optional[datetime] = None,
        transaction_id: Optional[str] = None,
        status: Optional[str] = None,
        prepay_id: Optional[str] = None
    ) -> bool:
        """更新订单"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                update_fields = []
                params = {"order_id": order_id}

                if payment_status is not None:
                    update_fields.append("payment_status = :payment_status")
                    params["payment_status"] = payment_status
                if payment_time:
                    update_fields.append("payment_time = :payment_time")
                    params["payment_time"] = payment_time
                if transaction_id:
                    update_fields.append("transaction_id = :transaction_id")
                    params["transaction_id"] = transaction_id
                if status:
                    update_fields.append("status = :status")
                    params["status"] = status
                if prepay_id:
                    update_fields.append("prepay_id = :prepay_id")
                    params["prepay_id"] = prepay_id

                if update_fields:
                    params["updated_at"] = datetime.now()
                    update_fields.append("updated_at = :updated_at")

                    sql = f"""
                        UPDATE {self.db_schema}.orders
                        SET {', '.join(update_fields)}
                        WHERE order_id = :order_id
                    """
                    conn.execute(text(sql), params)
                    conn.commit()
                    return True
            return False
        except Exception as e:
            print(f"更新订单失败: {e}")
            return False

    def get_order_for_update(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        获取订单并加锁（FOR UPDATE）
        用于支付回调处理中的并发控制

        Args:
            order_id: 订单ID

        Returns:
            订单信息（如果存在）
        """
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                row = conn.execute(text(f"""
                    SELECT * FROM {self.db_schema}.orders
                    WHERE order_id = :order_id
                    FOR UPDATE
                """), {"order_id": order_id}).fetchone()

                return dict(row._mapping) if row else None
        except Exception as e:
            print(f"获取订单加锁失败: {e}")
            return None

    def is_transaction_processed(self, transaction_id: str) -> bool:
        """
        检查交易是否已处理（幂等性检查）

        Args:
            transaction_id: 微信支付交易号

        Returns:
            True 表示已处理，False 表示未处理
        """
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                result = conn.execute(text(f"""
                    SELECT COUNT(*) as count
                    FROM {self.db_schema}.payment_notify_records
                    WHERE transaction_id = :transaction_id
                """), {"transaction_id": transaction_id}).fetchone()

                return result[0] > 0 if result else False
        except Exception as e:
            # 如果表不存在，认为未处理
            if "payment_notify_records" in str(e):
                return False
            print(f"检查交易处理状态失败: {e}")
            return False

    def try_insert_payment_notify_record(
        self,
        transaction_id: str,
        order_id: str,
        out_trade_no: str,
        trade_state: str,
        notify_data: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        尝试插入支付回调记录（幂等性保护）

        使用 INSERT ... ON CONFLICT DO NOTHING 实现原子性检查
        如果 transaction_id 已存在，则返回 is_duplicate=True

        Args:
            transaction_id: 微信支付交易号
            order_id: 内部订单ID
            out_trade_no: 商户订单号
            trade_state: 交易状态
            notify_data: 回调数据（JSON字符串）

        Returns:
            {
                "success": bool,
                "is_duplicate": bool,
                "error": str
            }
        """
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                # 尝试插入记录，如果 transaction_id 重复则忽略
                conn.execute(text(f"""
                    INSERT INTO {self.db_schema}.payment_notify_records
                    (transaction_id, order_id, out_trade_no, trade_state, notify_data, process_result)
                    VALUES (:transaction_id, :order_id, :out_trade_no, :trade_state, :notify_data, 'success')
                    ON CONFLICT (transaction_id) DO NOTHING
                """), {
                    "transaction_id": transaction_id,
                    "order_id": order_id,
                    "out_trade_no": out_trade_no,
                    "trade_state": trade_state,
                    "notify_data": notify_data
                })
                conn.commit()

                # 检查是否是重复记录
                existing = conn.execute(text(f"""
                    SELECT process_result FROM {self.db_schema}.payment_notify_records
                    WHERE transaction_id = :transaction_id
                """), {"transaction_id": transaction_id}).fetchone()

                if existing and existing[0] == 'success':
                    return {
                        "success": True,
                        "is_duplicate": False,
                        "error": None
                    }
                else:
                    return {
                        "success": True,
                        "is_duplicate": True,
                        "error": None
                    }

        except Exception as e:
            # 如果表不存在，先创建表
            if "payment_notify_records" in str(e):
                try:
                    # 表不存在，返回认为未处理
                    return {
                        "success": True,
                        "is_duplicate": False,
                        "error": None
                    }
                except Exception:
                    pass
            print(f"插入支付回调记录失败: {e}")
            return {
                "success": False,
                "is_duplicate": False,
                "error": str(e)
            }

    def update_order_with_condition(
        self,
        order_id: str,
        expected_payment_status: str,
        new_payment_status: str,
        payment_time: Optional[datetime] = None,
        transaction_id: Optional[str] = None
    ) -> bool:
        """
        带条件更新订单状态（乐观锁）

        只有当订单当前状态等于 expected_payment_status 时才更新
        用于防止并发重复处理

        Args:
            order_id: 订单ID
            expected_payment_status: 期望的当前支付状态
            new_payment_status: 新的支付状态
            payment_time: 支付时间
            transaction_id: 交易号

        Returns:
            True 表示更新成功，False 表示状态不匹配或更新失败
        """
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                params = {
                    "order_id": order_id,
                    "expected_payment_status": expected_payment_status,
                    "new_payment_status": new_payment_status,
                    "updated_at": datetime.now()
                }

                update_fields = [
                    "payment_status = :new_payment_status",
                    "updated_at = :updated_at"
                ]

                if payment_time:
                    params["payment_time"] = payment_time
                    update_fields.append("payment_time = :payment_time")

                if transaction_id:
                    params["transaction_id"] = transaction_id
                    update_fields.append("transaction_id = :transaction_id")

                sql = f"""
                    UPDATE {self.db_schema}.orders
                    SET {', '.join(update_fields)}
                    WHERE order_id = :order_id
                    AND payment_status = :expected_payment_status
                """

                result = conn.execute(text(sql), params)
                conn.commit()

                # 检查是否真的更新了记录
                return result.rowcount > 0

        except Exception as e:
            print(f"带条件更新订单失败: {e}")
            return False

    def update_payment_notify_record(
        self,
        transaction_id: str,
        process_result: str,
        error_message: Optional[str] = None
    ) -> bool:
        """
        更新支付回调记录的处理结果

        Args:
            transaction_id: 交易号
            process_result: 处理结果 (success, failed, duplicate)
            error_message: 错误信息

        Returns:
            是否更新成功
        """
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                params = {
                    "transaction_id": transaction_id,
                    "process_result": process_result,
                    "error_message": error_message
                }

                conn.execute(text(f"""
                    UPDATE {self.db_schema}.payment_notify_records
                    SET process_result = :process_result,
                        error_message = :error_message
                    WHERE transaction_id = :transaction_id
                """), params)
                conn.commit()
                return True

        except Exception as e:
            # 表不存在时忽略
            if "payment_notify_records" not in str(e):
                print(f"更新支付回调记录失败: {e}")
            return False

    # ==================== 会员权益使用记录 ====================

    def record_usage(
        self,
        user_id: str,
        usage_type: str,
        usage_amount: int = 1
    ) -> bool:
        """记录会员权益使用"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                conn.execute(text(f"""
                    INSERT INTO {self.db_schema}.member_usage_logs
                    (user_id, usage_type, usage_amount, usage_date)
                    VALUES (:user_id, :usage_type, :usage_amount, CURRENT_DATE)
                    ON CONFLICT (user_id, usage_type, usage_date)
                    DO UPDATE SET
                        usage_amount = member_usage_logs.usage_amount + :usage_amount,
                        created_at = CURRENT_TIMESTAMP
                """), {
                    "user_id": user_id,
                    "usage_type": usage_type,
                    "usage_amount": usage_amount
                })
                conn.commit()

            # 清除缓存，确保下次读取到最新的使用量
            try:
                from app.middleware.member_permission import clear_member_cache
                clear_member_cache(user_id)
            except Exception:
                # 清除缓存失败不影响记录使用量
                pass

            return True
        except Exception as e:
            print(f"记录会员权益使用失败: {e}")
            return False

    def get_usage_today(
        self,
        user_id: str,
        usage_type: str
    ) -> int:
        """获取今日使用量"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                result = conn.execute(text(f"""
                    SELECT COALESCE(usage_amount, 0) as amount
                    FROM {self.db_schema}.member_usage_logs
                    WHERE user_id = :user_id
                      AND usage_type = :usage_type
                      AND usage_date = CURRENT_DATE
                """), {"user_id": user_id, "usage_type": usage_type}).fetchone()

                return result[0] if result else 0
        except Exception as e:
            print(f"获取今日使用量失败: {e}")
            return 0

    def get_today_usage(
        self,
        user_id: str,
        usage_types: list = None
    ) -> Dict[str, int]:
        """
        批量获取今日使用量

        参数：
            user_id: 用户ID
            usage_types: 需要查询的使用类型列表，默认查询所有类型

        返回：
            dict: {usage_type: usage_amount}
        """
        if usage_types is None:
            # 默认查询所有新权益类型
            usage_types = [
                "invoice_penetration", "panorama", "business_risk",
                # 合同审查相关
                "contract_review_count", "contract_screening_pages", "multi_page_contract_pages",
                # 权益记录（用于权限检查）
                "contract_screening", "contract_review",
            ]

        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                placeholders = ", ".join([f":type_{i}" for i in range(len(usage_types))])
                params = {f"type_{i}": t for i, t in enumerate(usage_types)}
                params["user_id"] = user_id

                result = conn.execute(text(f"""
                    SELECT usage_type, COALESCE(usage_amount, 0) as amount
                    FROM {self.db_schema}.member_usage_logs
                    WHERE user_id = :user_id
                      AND usage_type IN ({placeholders})
                      AND usage_date = CURRENT_DATE
                """), params).fetchall()

                # 构建返回结果
                usage_dict = {t: 0 for t in usage_types}
                for row in result:
                    usage_dict[row[0]] = row[1]

                return usage_dict
        except Exception as e:
            print(f"批量获取今日使用量失败: {e}")
            return {t: 0 for t in usage_types}

    def get_usage_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户使用统计"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                # 获取今日对话次数
                today_chats = self.get_usage_today(user_id, "daily_chats")

                # 从知识库服务获取知识库数量
                try:
                    from app.services.knowledge.knowledge_repository import knowledge_repository
                    kb_count = knowledge_repository.count_user_knowledge_bases(user_id)
                except Exception:
                    kb_count = 0

                # 获取文件存储使用量
                try:
                    storage_result = conn.execute(text(f"""
                        SELECT COALESCE(SUM(file_size), 0) as total_size
                        FROM {self.db_schema}.user_files
                        WHERE user_id = :user_id AND status = 'active'
                    """), {"user_id": user_id}).fetchone()
                    used_storage_bytes = storage_result[0] if storage_result else 0
                    used_storage_mb = round(used_storage_bytes / (1024 * 1024), 2)
                except Exception:
                    used_storage_mb = 0

                # 获取文件数量
                try:
                    file_count_result = conn.execute(text(f"""
                        SELECT COUNT(*) as count
                        FROM {self.db_schema}.user_files
                        WHERE user_id = :user_id AND status = 'active'
                    """), {"user_id": user_id}).fetchone()
                    file_count = file_count_result[0] if file_count_result else 0
                except Exception:
                    file_count = 0

                return {
                    "today_chats": today_chats,
                    "kb_count": kb_count,
                    "used_storage_mb": used_storage_mb,
                    "file_count": file_count
                }
        except Exception as e:
            print(f"获取使用统计失败: {e}")
            return {
                "today_chats": 0,
                "kb_count": 0,
                "used_storage_mb": 0,
                "file_count": 0
            }

    # ==================== 会员信息查询 ====================

    def get_user_member_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户会员信息（包含套餐详情）"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                row = conn.execute(text(f"""
                    SELECT
                        u.user_id,
                        u.member_level,
                        u.member_expire_at,
                        u.status,
                        p.package_id,
                        p.name as package_name,
                        p.description,
                        p.max_daily_chats,
                        p.max_kb_count,
                        p.max_kb_documents,
                        p.max_file_storage_mb,
                        p.max_file_count,
                        p.enable_rag,
                        p.enable_web_search,
                        p.enable_mcp_tools,
                        p.custom_config,
                        p.benefits
                    FROM {self.db_schema}.users u
                    LEFT JOIN {self.db_schema}.member_packages p
                        ON u.member_level = p.package_id
                    WHERE u.user_id = :user_id
                """), {"user_id": user_id}).fetchone()

                return _deserialize_json_fields(dict(row._mapping)) if row else None
        except Exception as e:
            print(f"获取用户会员信息失败: {e}")
            return None

    def is_member_valid(self, user_id: str) -> bool:
        """检查会员是否有效"""
        try:
            member_info = self.get_user_member_info(user_id)
            if not member_info:
                return False

            # 检查会员等级
            if member_info.get("member_level") == "free":
                return False

            # 检查到期时间
            expire_at = member_info.get("member_expire_at")
            if expire_at and expire_at < datetime.now():
                return False

            return True
        except Exception as e:
            print(f"检查会员有效性失败: {e}")
            return False

    def cancel_timeout_orders(self, timeout_minutes: int = 30) -> Dict[str, Any]:
        """
        取消超时的待支付订单

        Args:
            timeout_minutes: 超时时间（分钟），默认30分钟

        Returns:
            包含 success, updated_count, message 的字典
        """
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                # 计算超时时间点
                timeout_time = datetime.now() - timedelta(minutes=timeout_minutes)

                # 查询待更新的订单数量
                count_result = conn.execute(text(f"""
                    SELECT COUNT(*) as count
                    FROM {self.db_schema}.orders
                    WHERE payment_status = 'pending'
                    AND status = 'active'
                    AND created_at < :timeout_time
                """), {"timeout_time": timeout_time}).fetchone()

                count = count_result[0] if count_result else 0

                if count > 0:
                    # 更新超时订单状态
                    conn.execute(text(f"""
                        UPDATE {self.db_schema}.orders
                        SET
                            status = 'cancelled',
                            updated_at = :updated_at
                        WHERE payment_status = 'pending'
                        AND status = 'active'
                        AND created_at < :timeout_time
                    """), {
                        "timeout_time": timeout_time,
                        "updated_at": datetime.now()
                    })
                    conn.commit()

                return {
                    "success": True,
                    "updated_count": count,
                    "message": f"已取消 {count} 个超时订单"
                }
        except Exception as e:
            print(f"取消超时订单失败: {e}")
            return {
                "success": False,
                "updated_count": 0,
                "error": str(e)
            }


# 全局实例
member_repository = MemberRepository()
