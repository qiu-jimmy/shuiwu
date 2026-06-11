"""
通知服务
支持多种通知渠道：邮件、短信、系统内通知等
"""
from typing import Optional, Dict, Any
from datetime import datetime


class NotificationService:
    """通知服务"""

    def __init__(self):
        # TODO: 配置邮件、短信等服务的API密钥
        self.email_enabled = False
        self.sms_enabled = False

    def send_tax_declaration_notification(
        self,
        user_id: str,
        user_email: Optional[str] = None,
        user_phone: Optional[str] = None,
        notification_type: str = "status_change",
        declaration_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        发送报税申报通知

        Args:
            user_id: 用户ID
            user_email: 用户邮箱（可选）
            user_phone: 用户手机号（可选）
            notification_type: 通知类型
                - submit_success: 提交成功
                - status_change: 状态变更
                - processing: 开始处理
                - completed: 处理完成
                - rejected: 审核拒绝
            declaration_data: 申报数据

        Returns:
            发送结果
        """
        templates = {
            "submit_success": {
                "title": "报税申报提交成功",
                "content": "您的报税申报已成功提交，申报单号：{declaration_no}，我们将在1-2个工作日内处理。"
            },
            "status_change": {
                "title": "报税申报状态变更",
                "content": "您的申报单 {declaration_no} 状态已更新。"
            },
            "processing": {
                "title": "报税申报开始处理",
                "content": "您的申报单 {declaration_no} 正在处理中，请耐心等待。"
            },
            "completed": {
                "title": "报税申报处理完成",
                "content": "您的申报单 {declaration_no} 已处理完成。应纳税额：{tax_amount} 元。{refund_info}"
            },
            "rejected": {
                "title": "报税申报审核未通过",
                "content": "您的申报单 {declaration_no} 审核未通过。原因：{reason}。请修改后重新提交。"
            }
        }

        template = templates.get(notification_type, templates["status_change"])

        # 构建通知内容
        content = template["content"]
        if declaration_data:
            # 填充模板变量
            content = content.format(
                declaration_no=declaration_data.get("declaration_no", ""),
                tax_amount=declaration_data.get("tax_amount", "0"),
                refund_info=self._get_refund_info(declaration_data),
                reason=declaration_data.get("process_result", "资料不完整")
            )

        # 发送系统内通知（记录到数据库）
        self._save_system_notification(
            user_id=user_id,
            title=template["title"],
            content=content,
            notification_type=notification_type,
            declaration_data=declaration_data
        )

        # TODO: 发送邮件通知
        if self.email_enabled and user_email:
            self._send_email(user_email, template["title"], content)

        # TODO: 发送短信通知
        if self.sms_enabled and user_phone:
            self._send_sms(user_phone, content)

        return {
            "success": True,
            "message": "通知发送成功"
        }

    def _save_system_notification(
        self,
        user_id: str,
        title: str,
        content: str,
        notification_type: str,
        declaration_data: Optional[Dict[str, Any]] = None
    ):
        """保存系统内通知到数据库"""
        from app.infra.db import get_sync_engine
        from sqlalchemy import text
        import json

        try:
            # 使用 psycopg2 的 Json 适配器
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
                INSERT INTO business.notifications (
                    user_id, title, content, notification_type,
                    related_data, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, CURRENT_TIMESTAMP
                )
            """

            cursor.execute(sql, (
                user_id,
                title,
                content,
                notification_type,
                Json(declaration_data) if declaration_data else None
            ))

            conn.commit()
            cursor.close()
            conn.close()

        except Exception as e:
            # 如果通知表不存在，静默失败（不影响主流程）
            print(f"保存通知失败（非关键错误）: {e}")

    def _send_email(self, email: str, title: str, content: str):
        """发送邮件通知"""
        # TODO: 集成邮件服务（如阿里云邮件、SendGrid等）
        pass

    def _send_sms(self, phone: str, content: str):
        """发送短信通知"""
        # TODO: 集成短信服务（如阿里云短信、腾讯云短信等）
        pass

    def _get_refund_info(self, declaration_data: Dict[str, Any]) -> str:
        """获取退税信息"""
        tax_refund = declaration_data.get("tax_refund", 0)
        if tax_refund and float(tax_refund) > 0:
            return f"应退税额：{tax_refund} 元。"
        return ""


# 全局通知服务实例
notification_service = NotificationService()
