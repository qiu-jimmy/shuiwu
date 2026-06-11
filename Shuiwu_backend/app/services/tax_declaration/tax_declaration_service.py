"""
智能报税服务层
"""
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy import text
from app.infra.db import get_sync_engine


class TaxDeclarationService:
    """报税申报服务"""

    def __init__(self):
        self.engine = get_sync_engine()

    def create_declaration(
        self,
        user_id: str,
        taxpayer_name: str,
        taxpayer_phone: str,
        tax_type: str,
        tax_period: str,
        income_info: Dict[str, Any],
        taxpayer_id_card: Optional[str] = None,
        taxpayer_type: str = "individual",
        deduction_info: Optional[Dict[str, Any]] = None,
        user_remarks: Optional[str] = None,
    ) -> Dict[str, Any]:
        """创建报税申报

        Args:
            user_id: 用户ID
            taxpayer_name: 纳税人姓名
            taxpayer_phone: 联系电话
            tax_type: 税种
            tax_period: 税期
            income_info: 收入信息
            taxpayer_id_card: 身份证号
            taxpayer_type: 纳税人类型
            deduction_info: 扣除信息
            user_remarks: 用户备注

        Returns:
            创建结果
        """
        # 生成申报单号
        declaration_no = self._generate_declaration_no()

        # 自动计算税额（用户提交时就计算，方便列表展示）
        try:
            from app.services.tax_declaration.tax_calculator import tax_calculator
            calculation = tax_calculator.calculate(tax_type, income_info, deduction_info)
            total_income = calculation.get("total_income")
            total_deduction = calculation.get("total_deduction")
            taxable_income = calculation.get("taxable_income")
            tax_amount = calculation.get("tax_amount")
        except Exception as e:
            # 计算失败不影响创建，字段设为 NULL
            print(f"自动计算税额失败: {e}")
            total_income = None
            total_deduction = None
            taxable_income = None
            tax_amount = None

        try:
            # 使用原始 psycopg2 连接，并使用 Json 适配器
            import psycopg2
            from psycopg2 import sql
            from psycopg2.extras import Json
            import os
            from dotenv import load_dotenv

            load_dotenv()

            conn = psycopg2.connect(
                host=os.getenv('PG_HOST', 'localhost'),
                port=os.getenv('PG_PORT', 5432),
                user=os.getenv('PG_USER', 'postgres'),
                password=os.getenv('PG_PASSWORD', 'root'),
                database=os.getenv('PG_DATABASE', 'Agno')
            )
            cursor = conn.cursor()

            # 使用 psycopg2 的 Json 适配器处理 JSONB
            sql = """
                INSERT INTO business.tax_declarations (
                    declaration_no, user_id, taxpayer_name, taxpayer_id_card,
                    taxpayer_phone, taxpayer_type, tax_type, tax_period,
                    income_info, deduction_info, user_remarks,
                    total_income, total_deduction, taxable_income, tax_amount
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING id, declaration_no, created_at
            """

            cursor.execute(sql, (
                declaration_no, user_id, taxpayer_name, taxpayer_id_card,
                taxpayer_phone, taxpayer_type, tax_type, tax_period,
                Json(income_info) if income_info else None,
                Json(deduction_info) if deduction_info else None,
                user_remarks,
                total_income, total_deduction, taxable_income, tax_amount
            ))

            row = cursor.fetchone()
            conn.commit()
            cursor.close()
            conn.close()

            return {
                "success": True,
                "declaration": {
                    "id": row[0],
                    "declaration_no": row[1],
                    "created_at": row[2].isoformat() if row[2] else None
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_declaration(
        self,
        declaration_id: int,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取报税申报详情

        Args:
            declaration_id: 申报ID
            user_id: 用户ID（用于权限验证）

        Returns:
            申报详情
        """
        try:
            with self.engine.connect() as conn:
                # 构建查询条件
                where_clause = "id = :declaration_id"
                params = {"declaration_id": declaration_id}

                if user_id:
                    where_clause += " AND user_id = :user_id"
                    params["user_id"] = user_id

                sql = text(f"""
                    SELECT
                        id, declaration_no, user_id, taxpayer_name, taxpayer_id_card,
                        taxpayer_phone, taxpayer_type, tax_type, tax_period,
                        income_info, deduction_info,
                        total_income, total_deduction, taxable_income,
                        tax_amount, tax_paid, tax_refund,
                        status, process_result,
                        declaration_serial_no, declaration_date, declaration_proof_url,
                        processed_by, processed_at, process_notes,
                        user_remarks, created_at, updated_at
                    FROM business.tax_declarations
                    WHERE {where_clause}
                """)

                result = conn.execute(sql, params)
                row = result.fetchone()

                if not row:
                    return {
                        "success": False,
                        "error": "申报不存在或无权访问"
                    }

                return {
                    "success": True,
                    "declaration": self._row_to_dict(row)
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def list_declarations(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        tax_type: Optional[str] = None,
        tax_period: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """获取报税申报列表

        Args:
            user_id: 用户ID（用户端必传，管理员可不传）
            status: 状态筛选
            tax_type: 税种筛选
            tax_period: 税期筛选
            page: 页码
            page_size: 每页数量

        Returns:
            申报列表
        """
        try:
            with self.engine.connect() as conn:
                # 构建查询条件
                where_conditions = []
                params = {}

                if user_id:
                    where_conditions.append("user_id = :user_id")
                    params["user_id"] = user_id

                if status:
                    where_conditions.append("status = :status")
                    params["status"] = status

                if tax_type:
                    where_conditions.append("tax_type = :tax_type")
                    params["tax_type"] = tax_type

                if tax_period:
                    where_conditions.append("tax_period = :tax_period")
                    params["tax_period"] = tax_period

                where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

                # 查询总数
                count_sql = text(f"""
                    SELECT COUNT(*)
                    FROM business.tax_declarations
                    WHERE {where_clause}
                """)
                total_result = conn.execute(count_sql, params)
                total = total_result.scalar()

                # 分页查询
                offset = (page - 1) * page_size
                list_sql = text(f"""
                    SELECT
                        id, declaration_no, user_id, taxpayer_name, taxpayer_phone,
                        taxpayer_type, tax_type, tax_period,
                        total_income, tax_amount, tax_refund,
                        status, created_at, processed_at
                    FROM business.tax_declarations
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                    LIMIT :page_size OFFSET :offset
                """)

                params["page_size"] = page_size
                params["offset"] = offset

                result = conn.execute(list_sql, params)
                rows = result.fetchall()

                declarations = [self._row_to_dict(row, summary=True) for row in rows]

                return {
                    "success": True,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "declarations": declarations
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def process_declaration(
        self,
        declaration_id: int,
        processed_by: str,
        total_income: Optional[float] = None,
        total_deduction: Optional[float] = None,
        taxable_income: Optional[float] = None,
        tax_amount: Optional[float] = None,
        tax_paid: Optional[float] = None,
        tax_refund: Optional[float] = None,
        declaration_serial_no: Optional[str] = None,
        declaration_date: Optional[datetime] = None,
        declaration_proof_url: Optional[str] = None,
        status: str = "processing",
        process_result: Optional[str] = None,
        process_notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """管理员处理报税申报

        Args:
            declaration_id: 申报ID
            processed_by: 处理人ID
            其他参数见 ProcessTaxDeclarationRequest

        Returns:
            处理结果
        """
        try:
            with self.engine.connect() as conn:
                sql = text("""
                    UPDATE business.tax_declarations
                    SET
                        total_income = :total_income,
                        total_deduction = :total_deduction,
                        taxable_income = :taxable_income,
                        tax_amount = :tax_amount,
                        tax_paid = :tax_paid,
                        tax_refund = :tax_refund,
                        declaration_serial_no = :declaration_serial_no,
                        declaration_date = :declaration_date,
                        declaration_proof_url = :declaration_proof_url,
                        status = :status,
                        process_result = :process_result,
                        processed_by = :processed_by,
                        processed_at = CURRENT_TIMESTAMP,
                        process_notes = :process_notes
                    WHERE id = :declaration_id
                    RETURNING id, declaration_no, status
                """)

                result = conn.execute(sql, {
                    "declaration_id": declaration_id,
                    "total_income": total_income,
                    "total_deduction": total_deduction,
                    "taxable_income": taxable_income,
                    "tax_amount": tax_amount,
                    "tax_paid": tax_paid,
                    "tax_refund": tax_refund,
                    "declaration_serial_no": declaration_serial_no,
                    "declaration_date": declaration_date,
                    "declaration_proof_url": declaration_proof_url,
                    "status": status,
                    "process_result": process_result,
                    "processed_by": processed_by,
                    "process_notes": process_notes
                })

                row = result.fetchone()
                conn.commit()

                if not row:
                    return {
                        "success": False,
                        "error": "申报不存在"
                    }

                return {
                    "success": True,
                    "message": f"申报 {row[1]} 状态已更新为 {row[2]}",
                    "declaration_id": row[0],
                    "declaration_no": row[1],
                    "status": row[2]
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """获取报税统计信息

        Args:
            user_id: 用户ID（用户端统计自己的，管理员统计全部）

        Returns:
            统计信息
        """
        try:
            with self.engine.connect() as conn:
                where_conditions = []
                params = {}

                if user_id:
                    where_conditions.append("user_id = :user_id")
                    params["user_id"] = user_id

                where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

                sql = text(f"""
                    SELECT
                        COUNT(*) as total_count,
                        COUNT(*) FILTER (WHERE status = 'pending') as pending_count,
                        COUNT(*) FILTER (WHERE status = 'processing') as processing_count,
                        COUNT(*) FILTER (WHERE status = 'completed') as completed_count,
                        COUNT(*) FILTER (WHERE status = 'rejected') as rejected_count,
                        COALESCE(SUM(tax_amount) FILTER (WHERE status = 'completed'), 0) as total_tax_amount
                    FROM business.tax_declarations
                    WHERE {where_clause}
                """)

                result = conn.execute(sql, params)
                row = result.fetchone()

                return {
                    "success": True,
                    "stats": {
                        "total_count": row[0] or 0,
                        "pending_count": row[1] or 0,
                        "processing_count": row[2] or 0,
                        "completed_count": row[3] or 0,
                        "rejected_count": row[4] or 0,
                        "total_tax_amount": float(row[5]) if row[5] else 0
                    }
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _generate_declaration_no(self) -> str:
        """生成申报单号

        格式: TD + YYYYMMDD + 6位序号
        示例: TD2026012000001
        """
        today = datetime.now().strftime("%Y%m%d")

        # 查询今日最大序号
        with self.engine.connect() as conn:
            sql = text("""
                SELECT COUNT(*) as count
                FROM business.tax_declarations
                WHERE DATE(created_at) = CURRENT_DATE
            """)
            result = conn.execute(sql)
            count = result.scalar() or 0

        sequence = str(count + 1).zfill(6)
        return f"TD{today}{sequence}"

    def _row_to_dict(self, row, summary: bool = False) -> Dict[str, Any]:
        """将数据库行转换为字典

        Args:
            row: 数据库行
            summary: 是否为摘要模式（只返回部分字段）

        Returns:
            字典
        """
        if summary:
            return {
                "id": row[0],
                "declaration_no": row[1],
                "user_id": row[2],
                "taxpayer_name": row[3],
                "taxpayer_phone": row[4],
                "taxpayer_type": row[5],
                "tax_type": row[6],
                "tax_period": row[7],
                "total_income": float(row[8]) if row[8] else None,
                "tax_amount": float(row[9]) if row[9] else None,
                "tax_refund": float(row[10]) if row[10] else None,
                "status": row[11],
                "created_at": row[12].isoformat() if row[12] else None,
                "processed_at": row[13].isoformat() if row[13] else None
            }

        # 完整模式
        return {
            "id": row[0],
            "declaration_no": row[1],
            "user_id": row[2],
            "taxpayer_name": row[3],
            "taxpayer_id_card": row[4],
            "taxpayer_phone": row[5],
            "taxpayer_type": row[6],
            "tax_type": row[7],
            "tax_period": row[8],
            "income_info": row[9],
            "deduction_info": row[10],
            "total_income": float(row[11]) if row[11] else None,
            "total_deduction": float(row[12]) if row[12] else None,
            "taxable_income": float(row[13]) if row[13] else None,
            "tax_amount": float(row[14]) if row[14] else None,
            "tax_paid": float(row[15]) if row[15] else None,
            "tax_refund": float(row[16]) if row[16] else None,
            "status": row[17],
            "process_result": row[18],
            "declaration_serial_no": row[19],
            "declaration_date": row[20].isoformat() if row[20] else None,
            "declaration_proof_url": row[21],
            "processed_by": row[22],
            "processed_at": row[23].isoformat() if row[23] else None,
            "process_notes": row[24],
            "user_remarks": row[25],
            "created_at": row[26].isoformat() if row[26] else None,
            "updated_at": row[27].isoformat() if row[27] else None
        }


# 全局服务实例
tax_declaration_service = TaxDeclarationService()
