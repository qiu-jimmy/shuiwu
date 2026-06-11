"""
税务师入驻服务
处理税务师申请、审核、管理等业务逻辑
"""
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from app.services.tax_accountant.tax_accountant_repository import tax_accountant_repository
from app.services.user.user_repository import user_repository


class TaxAccountantService:
    """税务师入驻服务类"""

    def __init__(self):
        pass

    # ==================== 用户端功能 ====================

    def submit_application(
        self,
        user_id: str,
        application_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        提交税务师入驻申请

        Args:
            user_id: 用户ID
            application_data: 申请数据（前端表单结构）

        Returns:
            包含申请ID的字典
        """
        # 检查用户是否存在
        user = user_repository.get_user_by_id(user_id)
        if not user:
            return {"success": False, "message": "用户不存在"}

        # 检查是否已有待审核或已通过的申请
        existing_application = tax_accountant_repository.get_application_by_user_id(user_id)
        if existing_application:
            if existing_application["status"] == "pending":
                return {"success": False, "message": "您已有待审核的申请，请等待审核结果"}
            if existing_application["status"] == "approved":
                return {"success": False, "message": "您已是认证税务师，无需重复申请"}

        # 检查是否已经是税务师
        existing_accountant = tax_accountant_repository.get_accountant_by_user_id(user_id)
        if existing_accountant:
            return {"success": False, "message": "您已是认证税务师"}

        # 创建申请
        application_id = str(uuid.uuid4())

        # 合并固定字段和表单数据
        create_data = {
            "application_id": application_id,
            "user_id": user_id,
            "status": "pending"
        }
        create_data.update(application_data)

        result = tax_accountant_repository.create_application(create_data)

        if result:
            return {
                "success": True,
                "message": "申请提交成功，请等待审核",
                "application_id": application_id
            }
        else:
            return {"success": False, "message": "申请提交失败，请稍后重试"}

    def get_my_application_status(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户的申请状态

        Args:
            user_id: 用户ID

        Returns:
            包含申请状态的字典
        """
        application = tax_accountant_repository.get_application_by_user_id(user_id)

        if not application:
            return {
                "has_applied": False,
                "application_id": None,
                "status": None,
                "reject_reason": None,
                "created_at": None
            }

        return {
            "has_applied": True,
            "application_id": application["application_id"],
            "status": application["status"],
            "reject_reason": application.get("reject_reason"),
            "created_at": application.get("created_at")
        }

    def get_my_accountant_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取用户的税务师信息

        Args:
            user_id: 用户ID

        Returns:
            税务师信息字典，如果不是税务师则返回None
        """
        return tax_accountant_repository.get_accountant_by_user_id(user_id)

    def is_tax_accountant(self, user_id: str) -> bool:
        """
        判断用户是否是税务师

        Args:
            user_id: 用户ID

        Returns:
            是否是认证税务师
        """
        accountant = tax_accountant_repository.get_accountant_by_user_id(user_id)
        return accountant is not None and accountant.get("status") == "active"

    # ==================== 管理端功能 ====================

    def review_application(
        self,
        application_id: str,
        action: str,
        reviewed_by: str,
        reject_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        审核税务师申请

        Args:
            application_id: 申请ID
            action: 审核操作 (approve-通过, reject-拒绝)
            reviewed_by: 审核人ID
            reject_reason: 拒绝原因（拒绝时必填）

        Returns:
            操作结果字典
        """
        # 获取申请信息
        application = tax_accountant_repository.get_application_by_id(application_id)
        if not application:
            return {"success": False, "message": "申请不存在"}

        if application["status"] != "pending":
            return {"success": False, "message": "该申请已被处理"}

        # 验证拒绝原因
        if action == "reject" and not reject_reason:
            return {"success": False, "message": "拒绝时必须填写拒绝原因"}

        # 更新申请状态
        new_status = "approved" if action == "approve" else "rejected"
        update_success = tax_accountant_repository.update_application_status(
            application_id, new_status, reviewed_by, reject_reason
        )

        if not update_success:
            return {"success": False, "message": "审核失败，请稍后重试"}

        # 如果通过审核，创建税务师记录
        if action == "approve":
            accountant_id = str(uuid.uuid4())

            # 从申请中提取数据创建税务师记录
            accountant_data = {
                "accountant_id": accountant_id,
                "user_id": application["user_id"],
                "application_id": application_id,
                "real_name": application["real_name"],
                "birth_date": application.get("birth_date"),
                "id_card": application["id_card"],
                "address": application.get("address"),
                "phone": application["phone"],
                "certificate_number": application["certificate_number"],
                "certificate_date": application.get("certificate_date"),
                "signature_image": application.get("signature_image"),
                "work_experiences": application.get("work_experiences"),
                "specialty_area": application["specialty_area"],
                "introduction": application.get("introduction"),
                "additional_info": application.get("additional_info"),
                "status": "active"
            }

            result = tax_accountant_repository.create_accountant(accountant_data)

            if not result:
                return {"success": False, "message": "创建税务师记录失败"}

            # 更新用户的 is_tax_accountant 标志
            user_repository.update_user(application["user_id"], {"is_tax_accountant": True})

            return {
                "success": True,
                "message": "审核通过，税务师已入驻",
                "accountant_id": accountant_id
            }
        else:
            return {
                "success": True,
                "message": "已拒绝该申请"
            }

    def get_application_list(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        keyword: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取申请列表

        Args:
            page: 页码
            page_size: 每页数量
            status: 状态筛选
            keyword: 关键词搜索

        Returns:
            申请列表字典
        """
        return tax_accountant_repository.list_applications(page, page_size, status, keyword)

    def get_application_detail(self, application_id: str) -> Optional[Dict[str, Any]]:
        """
        获取申请详情

        Args:
            application_id: 申请ID

        Returns:
            申请详情字典
        """
        application = tax_accountant_repository.get_application_by_id(application_id)
        if not application:
            return None

        # 获取用户信息
        user = user_repository.get_user_by_id(application["user_id"])
        if user:
            application["user_nickname"] = user.get("nickname")
            application["user_avatar"] = user.get("avatar_url")

        return application

    def get_accountant_list(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        keyword: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取税务师列表

        Args:
            page: 页码
            page_size: 每页数量
            status: 状态筛选
            keyword: 关键词搜索

        Returns:
            税务师列表字典
        """
        return tax_accountant_repository.list_accountants(page, page_size, status, keyword)

    def get_accountant_detail(self, accountant_id: str) -> Optional[Dict[str, Any]]:
        """
        获取税务师详情

        Args:
            accountant_id: 税务师ID

        Returns:
            税务师详情字典
        """
        return tax_accountant_repository.get_accountant_by_id(accountant_id)

    def update_accountant(
        self,
        accountant_id: str,
        status: Optional[str] = None,
        specialty_area: Optional[list] = None,
        introduction: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        更新税务师信息

        Args:
            accountant_id: 税务师ID
            status: 状态
            specialty_area: 专长领域
            introduction: 个人简介

        Returns:
            操作结果字典
        """
        update_data = {}
        if status is not None:
            update_data["status"] = status
        if specialty_area is not None:
            update_data["specialty_area"] = specialty_area
        if introduction is not None:
            update_data["introduction"] = introduction

        if not update_data:
            return {"success": False, "message": "没有需要更新的内容"}

        success = tax_accountant_repository.update_accountant(accountant_id, update_data)

        if success:
            return {"success": True, "message": "更新成功"}
        else:
            return {"success": False, "message": "更新失败"}

    def delete_accountant(self, accountant_id: str) -> Dict[str, Any]:
        """
        删除税务师（暂停服务）

        Args:
            accountant_id: 税务师ID

        Returns:
            操作结果字典
        """
        # 使用update来暂停服务而不是物理删除
        success = tax_accountant_repository.update_accountant_status(accountant_id, "suspended")

        if success:
            return {"success": True, "message": "税务师已暂停服务"}
        else:
            return {"success": False, "message": "操作失败"}

    def get_statistics(self) -> Dict[str, int]:
        """
        获取统计数据

        Returns:
            统计数据字典
        """
        app_stats = tax_accountant_repository.get_application_stats()
        active_count = tax_accountant_repository.get_active_accountants_count()

        return {
            "total_applications": app_stats["total_applications"],
            "pending_count": app_stats["pending_count"],
            "approved_count": app_stats["approved_count"],
            "rejected_count": app_stats["rejected_count"],
            "active_accountants": active_count
        }


# 全局实例
tax_accountant_service = TaxAccountantService()
