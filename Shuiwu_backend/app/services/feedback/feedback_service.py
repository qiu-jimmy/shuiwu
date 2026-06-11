"""
问题反馈系统服务层
"""
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy import text


def _get_engine():
    """延迟导入 get_sync_engine"""
    from app.infra.db import get_sync_engine
    return get_sync_engine()


class FeedbackService:
    """问题反馈业务逻辑"""

    # ==================== 用户端接口 ====================

    def submit_feedback(
        self,
        user_id: str,
        feedback_type: str,
        feedback_content: str,
        feedback_images: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """提交问题反馈"""
        try:
            engine = _get_engine()
            with engine.connect() as conn:
                # 生成反馈ID
                feedback_id = f"FB{uuid.uuid4().hex[:14].upper()}"

                # 插入反馈记录
                conn.execute(
                    text("""
                        INSERT INTO business.user_feedback
                        (feedback_id, user_id, feedback_type, feedback_content, feedback_images, status, priority)
                        VALUES (:fid, :uid, :ftype, :fcontent, :fimages, 'pending', 'normal')
                    """),
                    {
                        "fid": feedback_id,
                        "uid": user_id,
                        "ftype": feedback_type,
                        "fcontent": feedback_content,
                        "fimages": feedback_images if feedback_images else None
                    }
                )

                conn.commit()

                return {
                    "success": True,
                    "message": "反馈提交成功，我们会尽快处理",
                    "feedback_id": feedback_id
                }

        except Exception as e:
            return {"success": False, "error": f"提交反馈失败: {str(e)}"}

    def get_my_feedbacks(
        self,
        user_id: str,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """获取我的反馈列表"""
        try:
            engine = _get_engine()
            with engine.connect() as conn:
                # 构建查询条件
                conditions = ["f.user_id = :user_id"]
                params = {"user_id": user_id}

                if status:
                    conditions.append("f.status = :status")
                    params["status"] = status

                where_clause = f"WHERE {' AND '.join(conditions)}"

                # 查询总数
                count_result = conn.execute(
                    text(f"SELECT COUNT(*) FROM business.user_feedback f {where_clause}"),
                    params
                ).fetchone()
                total = count_result[0] if count_result else 0

                # 查询记录（JOIN 用户表获取昵称和手机号）
                offset = (page - 1) * page_size
                result = conn.execute(
                    text(f"""
                        SELECT
                            f.feedback_id,
                            f.user_id,
                            f.feedback_type,
                            f.feedback_content,
                            f.feedback_images,
                            f.admin_reply,
                            f.admin_id,
                            f.replied_at,
                            f.status,
                            f.priority,
                            f.created_at,
                            f.updated_at,
                            u.nickname as user_nickname,
                            u.phone as user_phone,
                            a.nickname as admin_nickname
                        FROM business.user_feedback f
                        LEFT JOIN business.users u ON f.user_id = u.user_id
                        LEFT JOIN business.users a ON f.admin_id = a.user_id
                        {where_clause}
                        ORDER BY f.created_at DESC
                        LIMIT :page_size OFFSET :offset
                    """),
                    {**params, "page_size": page_size, "offset": offset}
                )

                feedbacks = []
                for row in result:
                    feedbacks.append({
                        "feedback_id": row[0],
                        "user_id": row[1],
                        "feedback_type": row[2],
                        "feedback_content": row[3],
                        "feedback_images": row[4] if row[4] else [],
                        "admin_reply": row[5],
                        "admin_id": row[6],
                        "replied_at": row[7].isoformat() if row[7] else None,
                        "status": row[8],
                        "priority": row[9],
                        "created_at": row[10].isoformat() if row[10] else None,
                        "updated_at": row[11].isoformat() if row[11] else None,
                        "user_nickname": row[12],
                        "user_phone": row[13],
                        "admin_nickname": row[14]
                    })

                return {
                    "success": True,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "feedbacks": feedbacks
                }

        except Exception as e:
            return {"success": False, "error": f"获取反馈列表失败: {str(e)}"}

    def get_feedback_detail(self, feedback_id: str, user_id: str) -> Dict[str, Any]:
        """获取反馈详情"""
        try:
            engine = _get_engine()
            with engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT
                            f.feedback_id,
                            f.user_id,
                            f.feedback_type,
                            f.feedback_content,
                            f.feedback_images,
                            f.admin_reply,
                            f.admin_id,
                            f.replied_at,
                            f.status,
                            f.priority,
                            f.created_at,
                            f.updated_at,
                            u.nickname as user_nickname,
                            u.phone as user_phone
                        FROM business.user_feedback f
                        LEFT JOIN business.users u ON f.user_id = u.user_id
                        WHERE f.feedback_id = :fid AND f.user_id = :user_id
                    """),
                    {"fid": feedback_id, "user_id": user_id}
                ).fetchone()

                if not result:
                    return {"success": False, "error": "反馈不存在或无权访问"}

                return {
                    "success": True,
                    "feedback": {
                        "feedback_id": result[0],
                        "user_id": result[1],
                        "feedback_type": result[2],
                        "feedback_content": result[3],
                        "feedback_images": result[4] if result[4] else [],
                        "admin_reply": result[5],
                        "admin_id": result[6],
                        "replied_at": result[7].isoformat() if result[7] else None,
                        "status": result[8],
                        "priority": result[9],
                        "created_at": result[10].isoformat() if result[10] else None,
                        "updated_at": result[11].isoformat() if result[11] else None,
                        "user_nickname": result[12],
                        "user_phone": result[13]
                    }
                }

        except Exception as e:
            return {"success": False, "error": f"获取反馈详情失败: {str(e)}"}

    # ==================== 管理员端接口 ====================

    def list_all_feedbacks(
        self,
        status: Optional[str] = None,
        feedback_type: Optional[str] = None,
        priority: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """获取所有反馈列表（管理员）"""
        try:
            engine = _get_engine()
            with engine.connect() as conn:
                # 构建查询条件
                conditions = []
                params = {}

                if status:
                    conditions.append("f.status = :status")
                    params["status"] = status

                if feedback_type:
                    conditions.append("f.feedback_type = :feedback_type")
                    params["feedback_type"] = feedback_type

                if priority:
                    conditions.append("f.priority = :priority")
                    params["priority"] = priority

                where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

                # 查询总数
                count_result = conn.execute(
                    text(f"SELECT COUNT(*) FROM business.user_feedback f {where_clause}"),
                    params
                ).fetchone()
                total = count_result[0] if count_result else 0

                # 查询记录
                offset = (page - 1) * page_size
                result = conn.execute(
                    text(f"""
                        SELECT
                            f.feedback_id,
                            f.user_id,
                            f.feedback_type,
                            f.feedback_content,
                            f.feedback_images,
                            f.admin_reply,
                            f.admin_id,
                            f.replied_at,
                            f.status,
                            f.priority,
                            f.created_at,
                            f.updated_at,
                            u.nickname as user_nickname,
                            u.phone as user_phone,
                            a.nickname as admin_nickname
                        FROM business.user_feedback f
                        LEFT JOIN business.users u ON f.user_id = u.user_id
                        LEFT JOIN business.users a ON f.admin_id = a.user_id
                        {where_clause}
                        ORDER BY
                            CASE f.priority
                                WHEN 'urgent' THEN 1
                                WHEN 'high' THEN 2
                                WHEN 'normal' THEN 3
                                WHEN 'low' THEN 4
                                ELSE 5
                            END,
                            f.created_at DESC
                        LIMIT :page_size OFFSET :offset
                    """),
                    {**params, "page_size": page_size, "offset": offset}
                )

                feedbacks = []
                for row in result:
                    feedbacks.append({
                        "feedback_id": row[0],
                        "user_id": row[1],
                        "feedback_type": row[2],
                        "feedback_content": row[3],
                        "feedback_images": row[4] if row[4] else [],
                        "admin_reply": row[5],
                        "admin_id": row[6],
                        "replied_at": row[7].isoformat() if row[7] else None,
                        "status": row[8],
                        "priority": row[9],
                        "created_at": row[10].isoformat() if row[10] else None,
                        "updated_at": row[11].isoformat() if row[11] else None,
                        "user_nickname": row[12],
                        "user_phone": row[13],
                        "admin_nickname": row[14]
                    })

                return {
                    "success": True,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "feedbacks": feedbacks
                }

        except Exception as e:
            return {"success": False, "error": f"获取反馈列表失败: {str(e)}"}

    def update_feedback_status(
        self,
        feedback_id: str,
        status: str,
        priority: Optional[str] = None
    ) -> Dict[str, Any]:
        """更新反馈状态（管理员）"""
        try:
            engine = _get_engine()
            with engine.connect() as conn:
                # 验证状态值
                valid_statuses = ['pending', 'processing', 'resolved', 'closed']
                if status not in valid_statuses:
                    return {"success": False, "error": f"无效的状态值，必须是: {', '.join(valid_statuses)}"}

                # 构建更新语句
                update_fields = ["status = :status", "updated_at = CURRENT_TIMESTAMP"]
                params = {"status": status, "fid": feedback_id}

                if priority:
                    valid_priorities = ['low', 'normal', 'high', 'urgent']
                    if priority not in valid_priorities:
                        return {"success": False, "error": f"无效的优先级，必须是: {', '.join(valid_priorities)}"}
                    update_fields.append("priority = :priority")
                    params["priority"] = priority

                # 执行更新
                result = conn.execute(
                    text(f"""
                        UPDATE business.user_feedback
                        SET {', '.join(update_fields)}
                        WHERE feedback_id = :fid
                    """),
                    params
                )

                if result.rowcount == 0:
                    return {"success": False, "error": "反馈不存在"}

                conn.commit()

                return {
                    "success": True,
                    "message": f"状态已更新为 {status}"
                }

        except Exception as e:
            return {"success": False, "error": f"更新状态失败: {str(e)}"}

    def reply_feedback(
        self,
        feedback_id: str,
        admin_id: str,
        admin_reply: str
    ) -> Dict[str, Any]:
        """管理员回复反馈"""
        try:
            engine = _get_engine()
            with engine.connect() as conn:
                # 检查反馈是否存在
                feedback = conn.execute(
                    text("SELECT user_id, status FROM business.user_feedback WHERE feedback_id = :fid"),
                    {"fid": feedback_id}
                ).fetchone()

                if not feedback:
                    return {"success": False, "error": "反馈不存在"}

                # 更新回复
                conn.execute(
                    text("""
                        UPDATE business.user_feedback
                        SET admin_reply = :reply,
                            admin_id = :admin_id,
                            replied_at = CURRENT_TIMESTAMP,
                            status = 'processing',
                            updated_at = CURRENT_TIMESTAMP
                        WHERE feedback_id = :fid
                    """),
                    {
                        "fid": feedback_id,
                        "reply": admin_reply,
                        "admin_id": admin_id
                    }
                )

                conn.commit()

                return {
                    "success": True,
                    "message": "回复成功"
                }

        except Exception as e:
            return {"success": False, "error": f"回复失败: {str(e)}"}

    def get_feedback_stats(self) -> Dict[str, Any]:
        """获取反馈统计信息（管理员）"""
        try:
            engine = _get_engine()
            with engine.connect() as conn:
                # 统计各状态数量
                result = conn.execute(
                    text("""
                        SELECT
                            COUNT(*) FILTER (WHERE status = 'pending') as pending_count,
                            COUNT(*) FILTER (WHERE status = 'processing') as processing_count,
                            COUNT(*) FILTER (WHERE status = 'resolved') as resolved_count,
                            COUNT(*) FILTER (WHERE status = 'closed') as closed_count,
                            COUNT(*) FILTER (WHERE priority = 'urgent') as urgent_count
                        FROM business.user_feedback
                    """)
                ).fetchone()

                return {
                    "success": True,
                    "stats": {
                        "pending_count": result[0] if result[0] else 0,
                        "processing_count": result[1] if result[1] else 0,
                        "resolved_count": result[2] if result[2] else 0,
                        "closed_count": result[3] if result[3] else 0,
                        "urgent_count": result[4] if result[4] else 0
                    }
                }

        except Exception as e:
            return {"success": False, "error": f"获取统计信息失败: {str(e)}"}


# 创建全局实例
feedback_service = FeedbackService()
