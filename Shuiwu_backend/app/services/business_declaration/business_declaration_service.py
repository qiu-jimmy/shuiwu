"""
个体户工商申报服务层。

职责：
  - create_declaration：将申报表单写入 business.business_declarations 表
  - get_declaration：按 ID（及可选 user_id）查询申报详情
  - list_declarations：分页查询申报列表，支持 user_id/status/declaration_type 筛选
  - process_declaration：管理员更新申报状态及审核信息
  - get_stats：汇总各状态与类型的申报数量，含新增的 license_application_count
"""
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy import text
from app.infra.db import get_sync_engine


class BusinessDeclarationService:
    """工商申报服务"""

    def __init__(self):
        self.engine = get_sync_engine()

    def create_declaration(
        self,
        user_id: str,
        business_name: str,
        operator_name: str,
        operator_phone: str,
        declaration_type: str,
        business_license_no: Optional[str] = None,
        business_address: Optional[str] = None,
        business_type: Optional[str] = None,
        business_scope: Optional[str] = None,
        operator_id_card: Optional[str] = None,
        declaration_info: Optional[Dict[str, Any]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        user_remarks: Optional[str] = None,
    ) -> Dict[str, Any]:
        """创建工商申报

        Args:
            user_id: 用户ID
            business_name: 个体户名称
            operator_name: 经营者姓名
            operator_phone: 联系电话
            declaration_type: 申报类型
            business_license_no: 营业执照号
            business_address: 经营地址
            business_type: 经营类型
            business_scope: 经营范围
            operator_id_card: 身份证号
            declaration_info: 申报详细信息
            attachments: 附件信息
            user_remarks: 用户备注

        Returns:
            创建结果
        """
        # 生成申报单号
        declaration_no = self._generate_declaration_no()

        try:
            # 使用 psycopg2 的 Json 适配器处理 JSONB
            import psycopg2
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

            sql = """
                INSERT INTO business.business_declarations (
                    declaration_no, user_id, business_name, business_license_no,
                    business_address, business_type, business_scope,
                    operator_name, operator_id_card, operator_phone,
                    declaration_type, declaration_info, attachments, user_remarks
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING id, declaration_no, created_at
            """

            cursor.execute(sql, (
                declaration_no, user_id, business_name, business_license_no,
                business_address, business_type, business_scope,
                operator_name, operator_id_card, operator_phone,
                declaration_type,
                Json(declaration_info) if declaration_info else None,
                Json(attachments) if attachments else None,
                user_remarks
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
        """获取工商申报详情

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
                        id, declaration_no, user_id,
                        business_name, business_license_no, business_address,
                        business_type, business_scope,
                        operator_name, operator_id_card, operator_phone,
                        declaration_type, declaration_info, attachments,
                        status, approval_no, approval_date, approval_proof_url,
                        process_result, process_notes,
                        processed_by, processed_at,
                        user_remarks, created_at, updated_at
                    FROM business.business_declarations
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
        declaration_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """获取工商申报列表

        Args:
            user_id: 用户ID（用户端必传，管理员可不传）
            status: 状态筛选
            declaration_type: 申报类型筛选
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

                if declaration_type:
                    where_conditions.append("declaration_type = :declaration_type")
                    params["declaration_type"] = declaration_type

                where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

                # 查询总数
                count_sql = text(f"""
                    SELECT COUNT(*)
                    FROM business.business_declarations
                    WHERE {where_clause}
                """)
                total_result = conn.execute(count_sql, params)
                total = total_result.scalar()

                # 分页查询
                offset = (page - 1) * page_size
                list_sql = text(f"""
                    SELECT
                        id, declaration_no, user_id,
                        business_name, operator_name, operator_phone,
                        declaration_type, status,
                        created_at, processed_at
                    FROM business.business_declarations
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
        status: str,
        approval_no: Optional[str] = None,
        approval_date: Optional[str] = None,
        approval_proof_url: Optional[str] = None,
        process_result: Optional[str] = None,
        process_notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """管理员处理工商申报

        Args:
            declaration_id: 申报ID
            processed_by: 处理人ID
            status: 处理状态
            approval_no: 受理号
            approval_date: 受理日期
            approval_proof_url: 批准凭证URL
            process_result: 处理结果说明
            process_notes: 处理备注

        Returns:
            处理结果
        """
        try:
            # 使用 psycopg2 来处理日期类型
            import psycopg2
            from dotenv import load_dotenv
            import os
            load_dotenv()

            conn = psycopg2.connect(
                host=os.getenv('PG_HOST', 'localhost'),
                port=os.getenv('PG_PORT', 5432),
                user=os.getenv('PG_USER', 'postgres'),
                password=os.getenv('PG_PASSWORD', 'root'),
                database=os.getenv('PG_DATABASE', 'Agno')
            )
            cursor = conn.cursor()

            # 处理日期
            approval_date_value = None
            if approval_date:
                try:
                    approval_date_value = datetime.fromisoformat(approval_date.replace('Z', '+00:00')).date()
                except:
                    approval_date_value = None

            sql = """
                UPDATE business.business_declarations
                SET
                    status = %s,
                    approval_no = %s,
                    approval_date = %s,
                    approval_proof_url = %s,
                    process_result = %s,
                    process_notes = %s,
                    processed_by = %s,
                    processed_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING id, declaration_no, status
            """

            cursor.execute(sql, (
                status,
                approval_no,
                approval_date_value,
                approval_proof_url,
                process_result,
                process_notes,
                processed_by,
                declaration_id
            ))

            row = cursor.fetchone()
            conn.commit()
            cursor.close()
            conn.close()

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
        """获取工商申报统计信息

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
                        COUNT(*) FILTER (WHERE status = 'need_supplement') as need_supplement_count,
                        COUNT(*) FILTER (WHERE declaration_type = 'annual_report') as annual_report_count,
                        COUNT(*) FILTER (WHERE declaration_type = 'change_registration') as change_registration_count,
                        COUNT(*) FILTER (WHERE declaration_type = 'deregistration') as deregistration_count,
                        COUNT(*) FILTER (WHERE declaration_type = 'license_application') as license_application_count
                    FROM business.business_declarations
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
                        "need_supplement_count": row[5] or 0,
                        "annual_report_count": row[6] or 0,
                        "change_registration_count": row[7] or 0,
                        "deregistration_count": row[8] or 0,
                        # 新增：工商执照申请类型统计
                        "license_application_count": row[9] or 0,
                    }
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _generate_declaration_no(self) -> str:
        """生成申报单号

        格式: BD + YYYYMMDD + 6位序号
        示例: BD2026012000001
        """
        today = datetime.now().strftime("%Y%m%d")

        # 查询今日最大序号
        with self.engine.connect() as conn:
            sql = text("""
                SELECT COUNT(*) as count
                FROM business.business_declarations
                WHERE DATE(created_at) = CURRENT_DATE
            """)
            result = conn.execute(sql)
            count = result.scalar() or 0

        sequence = str(count + 1).zfill(6)
        return f"BD{today}{sequence}"

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
                "business_name": row[3],
                "operator_name": row[4],
                "operator_phone": row[5],
                "declaration_type": row[6],
                "status": row[7],
                "created_at": row[8].isoformat() if row[8] else None,
                "processed_at": row[9].isoformat() if row[9] else None
            }

        # 完整模式
        return {
            "id": row[0],
            "declaration_no": row[1],
            "user_id": row[2],
            "business_name": row[3],
            "business_license_no": row[4],
            "business_address": row[5],
            "business_type": row[6],
            "business_scope": row[7],
            "operator_name": row[8],
            "operator_id_card": row[9],
            "operator_phone": row[10],
            "declaration_type": row[11],
            "declaration_info": row[12],
            "attachments": row[13],
            "status": row[14],
            "approval_no": row[15],
            "approval_date": row[16].isoformat() if row[16] else None,
            "approval_proof_url": row[17],
            "process_result": row[18],
            "process_notes": row[19],
            "processed_by": row[20],
            "processed_at": row[21].isoformat() if row[21] else None,
            "user_remarks": row[22],
            "created_at": row[23].isoformat() if row[23] else None,
            "updated_at": row[24].isoformat() if row[24] else None
        }


# 全局服务实例
business_declaration_service = BusinessDeclarationService()
