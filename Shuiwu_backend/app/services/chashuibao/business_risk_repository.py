"""
经营风险报告 - 数据访问层
"""
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy import text
from app.infra.db import get_sync_engine
from app.infra.logging_config import get_logger

logger = get_logger("app.services.chashuibao.business_risk_repository")


class BusinessRiskRepository:
    """经营风险报告数据访问层"""

    def __init__(self, db_schema: str = "business"):
        self.db_schema = db_schema
        self.table = f"{db_schema}.business_risk_reports"

    def create_report(self, user_id: str, taxpayer_no: str, company_name: str, order_no: str) -> Optional[int]:
        """创建经营风险报告记录，返回主键 id"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                row = conn.execute(text(f"""
                    INSERT INTO {self.table} (user_id, taxpayer_no, company_name, order_no, status)
                    VALUES (:user_id, :taxpayer_no, :company_name, :order_no, 'pending')
                    RETURNING id
                """), {
                    "user_id": user_id,
                    "taxpayer_no": taxpayer_no,
                    "company_name": company_name,
                    "order_no": order_no,
                }).fetchone()
                conn.commit()
                report_id = row[0] if row else None
                logger.info(f"创建经营风险报告记录成功: id={report_id}, order_no={order_no}")
                return report_id
        except Exception as e:
            logger.error(f"创建经营风险报告记录失败: {e}")
            return None

    def get_report_by_order_no(self, order_no: str) -> Optional[Dict[str, Any]]:
        """根据订单号获取报告记录"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                row = conn.execute(text(f"""
                    SELECT * FROM {self.table}
                    WHERE order_no = :order_no
                    ORDER BY created_at DESC LIMIT 1
                """), {"order_no": order_no}).fetchone()
                return dict(row._mapping) if row else None
        except Exception as e:
            logger.error(f"根据订单号获取经营风险报告记录失败: {e}")
            return None

    def update_report_status(
        self,
        order_no: str,
        status: str,
        report_url: Optional[str] = None,
        error_message: Optional[str] = None,
        callback_state: Optional[str] = None,
    ) -> bool:
        """根据 order_no 更新报告状态"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                fields = ["status = :status", "updated_at = :updated_at"]
                params: Dict[str, Any] = {
                    "order_no": order_no,
                    "status": status,
                    "updated_at": datetime.now(),
                }

                if report_url:
                    fields.append("report_url = :report_url")
                    params["report_url"] = report_url

                if error_message:
                    fields.append("error_message = :error_message")
                    params["error_message"] = error_message

                if callback_state:
                    fields.append("callback_state = :callback_state")
                    fields.append("callback_received_at = :callback_received_at")
                    params["callback_state"] = callback_state
                    params["callback_received_at"] = datetime.now()

                if status in ("success", "failed"):
                    fields.append("completed_at = :completed_at")
                    params["completed_at"] = datetime.now()

                conn.execute(text(f"""
                    UPDATE {self.table}
                    SET {', '.join(fields)}
                    WHERE order_no = :order_no
                """), params)
                conn.commit()
                logger.info(f"更新经营风险报告状态成功: order_no={order_no}, status={status}")
                return True
        except Exception as e:
            logger.error(f"更新经营风险报告状态失败: {e}")
            return False

    def list_reports_by_user(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """获取用户的经营风险报告列表"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                conditions = ["user_id = :user_id"]
                params: Dict[str, Any] = {
                    "user_id": user_id,
                    "limit": page_size,
                    "offset": (page - 1) * page_size,
                }

                if status:
                    conditions.append("status = :status")
                    params["status"] = status

                where = f"WHERE {' AND '.join(conditions)}"

                total = conn.execute(text(f"""
                    SELECT COUNT(*) FROM {self.table} {where}
                """), params).scalar()

                rows = conn.execute(text(f"""
                    SELECT id, user_id, order_no, company_name, taxpayer_no,
                           status, report_url, error_message,
                           created_at, completed_at
                    FROM {self.table}
                    {where}
                    ORDER BY created_at DESC
                    LIMIT :limit OFFSET :offset
                """), params).fetchall()

                return {
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "reports": [dict(row._mapping) for row in rows],
                }
        except Exception as e:
            logger.error(f"获取用户经营风险报告列表失败: {e}")
            return {"total": 0, "page": page, "page_size": page_size, "reports": []}


# 全局实例
business_risk_repository = BusinessRiskRepository()
