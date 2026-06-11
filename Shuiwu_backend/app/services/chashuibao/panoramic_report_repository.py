"""
全景报告 - 数据访问层
"""
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import text
from app.infra.db import get_sync_engine
from app.infra.logging_config import get_logger

logger = get_logger("app.services.chashuibao.panoramic_report_repository")


class PanoramicReportRepository:
    """全景报告数据访问层"""

    def __init__(self, db_schema: str = "business"):
        self.db_schema = db_schema

    def create_report(self, report_data: Dict[str, Any]) -> Optional[int]:
        """创建全景报告记录"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                # 构建动态SQL，只插入提供的字段
                columns = []
                values = []

                for key, value in report_data.items():
                    if value is not None:
                        columns.append(key)
                        values.append(f":{key}")

                # 如果 report_data 包含 JSON 字段，需要转换
                params = {}
                for key, value in report_data.items():
                    if value is not None:
                        if key == "report_data" and isinstance(value, (dict, list)):
                            params[key] = json.dumps(value, ensure_ascii=False)
                        else:
                            params[key] = value

                logger.info(f"准备插入全景报告记录: columns={columns}, params keys={list(params.keys())}, user_id type={type(params.get('user_id'))}")

                sql = f"""
                    INSERT INTO {self.db_schema}.panoramic_reports
                    ({', '.join(columns)})
                    VALUES ({', '.join(values)})
                    RETURNING id
                """

                result = conn.execute(text(sql), params)
                row = result.fetchone()
                conn.commit()

                report_id = row[0] if row else None
                logger.info(f"创建全景报告记录成功: id={report_id}, user_id={report_data.get('user_id')}")
                return report_id
        except Exception as e:
            logger.error(f"创建全景报告记录失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return None

    def get_report_by_id(self, report_id: int) -> Optional[Dict[str, Any]]:
        """根据主键ID获取报告记录"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                row = conn.execute(text(f"""
                    SELECT * FROM {self.db_schema}.panoramic_reports WHERE id = :report_id
                """), {"report_id": report_id}).fetchone()

                if row:
                    report = dict(row._mapping)
                    # 解析 JSONB 字段
                    if report.get("report_data"):
                        report["report_data"] = dict(report["report_data"])
                    return report
                return None
        except Exception as e:
            logger.error(f"获取报告记录失败: {e}")
            return None

    def get_report_by_chashuibao_id(self, chashuibao_report_id: int) -> Optional[Dict[str, Any]]:
        """根据查税宝报告ID获取报告记录"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                row = conn.execute(text(f"""
                    SELECT * FROM {self.db_schema}.panoramic_reports
                    WHERE report_id = :chashuibao_report_id
                    ORDER BY created_at DESC
                    LIMIT 1
                """), {"chashuibao_report_id": chashuibao_report_id}).fetchone()

                if row:
                    report = dict(row._mapping)
                    # 解析 JSONB 字段
                    if report.get("report_data"):
                        report["report_data"] = dict(report["report_data"])
                    return report
                return None
        except Exception as e:
            logger.error(f"根据查税宝报告ID获取报告记录失败: {e}")
            return None

    def get_latest_report_by_user_and_taxpayer(
        self, user_id: str, taxpayer_no: str
    ) -> Optional[Dict[str, Any]]:
        """获取用户对指定企业的最新报告记录"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                row = conn.execute(text(f"""
                    SELECT * FROM {self.db_schema}.panoramic_reports
                    WHERE user_id = :user_id AND taxpayer_no = :taxpayer_no
                    ORDER BY created_at DESC
                    LIMIT 1
                """), {"user_id": user_id, "taxpayer_no": taxpayer_no}).fetchone()

                if row:
                    report = dict(row._mapping)
                    # 解析 JSONB 字段
                    if report.get("report_data"):
                        report["report_data"] = dict(report["report_data"])
                    return report
                return None
        except Exception as e:
            logger.error(f"获取用户最新报告记录失败: {e}")
            return None

    def update_report_status(
        self,
        id: int,
        status: str,
        report_id: Optional[int] = None,
        report_url: Optional[str] = None,
        report_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        callback_state: Optional[str] = None,
        taxpayer_no: Optional[str] = None,
    ) -> bool:
        """更新报告状态"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                update_fields = []
                params = {"id": id}

                if status:
                    update_fields.append("status = :status")
                    params["status"] = status

                if report_id is not None:
                    update_fields.append("report_id = :report_id")
                    params["report_id"] = report_id

                if report_url:
                    update_fields.append("report_url = :report_url")
                    params["report_url"] = report_url

                if report_data:
                    update_fields.append("report_data = :report_data")
                    params["report_data"] = json.dumps(report_data, ensure_ascii=False)

                if error_message:
                    update_fields.append("error_message = :error_message")
                    params["error_message"] = error_message

                if callback_state:
                    update_fields.append("callback_state = :callback_state")
                    params["callback_state"] = callback_state
                    update_fields.append("callback_received_at = :callback_received_at")
                    params["callback_received_at"] = datetime.now()

                if taxpayer_no is not None:
                    update_fields.append("taxpayer_no = :taxpayer_no")
                    params["taxpayer_no"] = taxpayer_no

                if status == "success" or status == "failed":
                    update_fields.append("completed_at = :completed_at")
                    params["completed_at"] = datetime.now()

                update_fields.append("updated_at = :updated_at")
                params["updated_at"] = datetime.now()

                sql = f"""
                    UPDATE {self.db_schema}.panoramic_reports
                    SET {', '.join(update_fields)}
                    WHERE id = :id
                """
                conn.execute(text(sql), params)
                conn.commit()

                logger.info(f"更新报告状态成功: id={id}, status={status}")
                return True
        except Exception as e:
            logger.error(f"更新报告状态失败: {e}")
            return False

    def list_reports_by_user(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        taxpayer_no: Optional[str] = None,
    ) -> Dict[str, Any]:
        """获取用户的报告列表"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                # 构建查询条件
                conditions = ["user_id = :user_id"]
                params = {
                    "user_id": user_id,
                    "limit": page_size,
                    "offset": (page - 1) * page_size
                }

                if status:
                    conditions.append("status = :status")
                    params["status"] = status

                if taxpayer_no:
                    conditions.append("taxpayer_no = :taxpayer_no")
                    params["taxpayer_no"] = taxpayer_no

                where_clause = f"WHERE {' AND '.join(conditions)}"

                # 查询总数
                count_sql = f"""
                    SELECT COUNT(*) FROM {self.db_schema}.panoramic_reports
                    {where_clause}
                """
                total = conn.execute(text(count_sql), params).scalar()

                # 查询列表
                list_sql = f"""
                    SELECT id, user_id, taxpayer_no, taxpayer_name, report_id,
                           report_url, status, error_message,
                           report_logo, watermark, cover_url, is_anonymity,
                           created_at, updated_at, completed_at, callback_received_at, callback_state
                    FROM {self.db_schema}.panoramic_reports
                    {where_clause}
                    ORDER BY created_at DESC
                    LIMIT :limit OFFSET :offset
                """
                rows = conn.execute(text(list_sql), params).fetchall()

                return {
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "reports": [dict(row._mapping) for row in rows]
                }
        except Exception as e:
            logger.error(f"获取用户报告列表失败: {e}")
            return {"total": 0, "page": page, "page_size": page_size, "reports": []}

    def delete_report(self, id: int) -> bool:
        """删除报告记录"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                conn.execute(text(f"""
                    DELETE FROM {self.db_schema}.panoramic_reports WHERE id = :id
                """), {"id": id})
                conn.commit()
                logger.info(f"删除报告记录成功: id={id}")
                return True
        except Exception as e:
            logger.error(f"删除报告记录失败: {e}")
            return False

    def mark_expired_reports_as_failed(
        self,
        timeout_minutes: int = 10
    ) -> Dict[str, Any]:
        """将超过指定时间的 pending 状态报告标记为失败

        Args:
            timeout_minutes: 超时时间（分钟），默认10分钟

        Returns:
            更新结果，包含更新的记录数量
        """
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                # 查找超时的 pending 状态报告
                sql = f"""
                    UPDATE {self.db_schema}.panoramic_reports
                    SET status = 'failed',
                        error_message = :error_message,
                        completed_at = :completed_at,
                        updated_at = :updated_at
                    WHERE status = 'pending'
                      AND created_at < :timeout_threshold
                    RETURNING id, user_id, taxpayer_no, created_at
                """

                timeout_threshold = datetime.now() - timedelta(minutes=timeout_minutes)
                params = {
                    "error_message": f"报告生成超时（超过{timeout_minutes}分钟未完成）",
                    "completed_at": datetime.now(),
                    "updated_at": datetime.now(),
                    "timeout_threshold": timeout_threshold
                }

                result = conn.execute(text(sql), params)
                updated_rows = result.fetchall()
                conn.commit()

                updated_count = len(updated_rows)

                if updated_count > 0:
                    logger.info(f"标记超时报告为失败: 更新数量={updated_count}")
                    # 记录被更新的报告ID
                    report_ids = [row[0] for row in updated_rows]
                    logger.debug(f"超时报告ID列表: {report_ids}")
                else:
                    logger.info("没有超时的报告需要处理")

                return {
                    "success": True,
                    "updated_count": updated_count,
                    "message": f"成功标记 {updated_count} 条超时报告为失败"
                }
        except Exception as e:
            logger.error(f"标记超时报告为失败时出错: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return {
                "success": False,
                "error": str(e)
            }


# 全局实例
panoramic_report_repository = PanoramicReportRepository()
