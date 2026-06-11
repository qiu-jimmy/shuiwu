"""
会员订阅模块 - 业务逻辑层
"""
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy import text
from app.services.member.member_repository import member_repository
from app.services.user.user_repository import user_repository


class MemberService:
    """会员业务逻辑层"""

    def __init__(self):
        self.member_repo = member_repository
        self.user_repo = user_repository

    # ==================== 会员套餐管理 ====================

    def create_package(self, package_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建会员套餐"""
        try:
            # 检查套餐ID是否已存在
            existing = self.member_repo.get_package_by_id(package_data["package_id"])
            if existing:
                return {"success": False, "error": "套餐ID已存在"}

            # 创建套餐
            package = self.member_repo.create_package(package_data)
            if package:
                return {"success": True, "package": package}
            return {"success": False, "error": "创建套餐失败"}
        except Exception as e:
            return {"success": False, "error": f"创建套餐异常: {str(e)}"}

    def get_package(self, package_id: str) -> Dict[str, Any]:
        """获取套餐详情"""
        try:
            package = self.member_repo.get_package_by_id(package_id)
            if package:
                return {"success": True, "package": package}
            return {"success": False, "error": "套餐不存在"}
        except Exception as e:
            return {"success": False, "error": f"获取套餐异常: {str(e)}"}

    def list_packages(
        self,
        status: Optional[str] = None,
        package_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取套餐列表"""
        try:
            # 默认只返回有效的套餐
            if status is None:
                status = "active"

            packages = self.member_repo.list_packages(status=status, package_type=package_type)
            return {"success": True, "packages": packages}
        except Exception as e:
            return {"success": False, "error": f"获取套餐列表异常: {str(e)}"}

    def update_package(
        self,
        package_id: str,
        update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """更新套餐"""
        try:
            # 检查套餐是否存在
            package = self.member_repo.get_package_by_id(package_id)
            if not package:
                return {"success": False, "error": "套餐不存在"}

            # 如果没有传递 enable_rag、enable_web_search、enable_mcp_tools，默认设为 False
            if "enable_rag" not in update_data:
                update_data["enable_rag"] = False
            if "enable_web_search" not in update_data:
                update_data["enable_web_search"] = False
            if "enable_mcp_tools" not in update_data:
                update_data["enable_mcp_tools"] = False

            # max_daily_chats 为 null 时默认为 -1（表示无限制）
            if "max_daily_chats" in update_data and update_data["max_daily_chats"] is None:
                update_data["max_daily_chats"] = -1

            # 更新套餐
            success = self.member_repo.update_package(package_id, update_data)
            if success:
                # 返回更新后的套餐信息
                updated_package = self.member_repo.get_package_by_id(package_id)
                return {"success": True, "package": updated_package}
            return {"success": False, "error": "更新套餐失败"}
        except Exception as e:
            return {"success": False, "error": f"更新套餐异常: {str(e)}"}

    def delete_package(self, package_id: str) -> Dict[str, Any]:
        """删除套餐（软删除）"""
        try:
            # 检查套餐是否存在
            package = self.member_repo.get_package_by_id(package_id)
            if not package:
                return {"success": False, "error": "套餐不存在"}

            # 禁止删除免费套餐
            if package_id == "free":
                return {"success": False, "error": "免费套餐不能删除"}

            # 软删除套餐
            success = self.member_repo.delete_package(package_id)
            if success:
                return {"success": True, "message": "删除成功"}
            return {"success": False, "error": "删除套餐失败"}
        except Exception as e:
            return {"success": False, "error": f"删除套餐异常: {str(e)}"}

    # ==================== 订单管理 ====================

    def create_order(
        self,
        user_id: str,
        package_id: str,
        order_type: str = "subscription",
        payment_method: str = "wechat"
    ) -> Dict[str, Any]:
        """创建订单"""
        try:
            # 检查用户是否存在
            user = self.user_repo.get_user_by_id(user_id)
            if not user:
                return {"success": False, "error": "用户不存在"}

            # 检查套餐是否存在且有效
            package = self.member_repo.get_package_by_id(package_id)
            if not package:
                return {"success": False, "error": "套餐不存在"}
            if package.get("status") != "active":
                return {"success": False, "error": "套餐已下架"}

            # 计算会员到期时间
            member_expire_at = user.get("member_expire_at")
            duration_days = package.get("duration_days")

            original_expire_at = member_expire_at
            new_expire_at = None

            if duration_days:
                # 计算基础时间：
                # 1. 如果用户有会员且未过期，从原到期时间开始累加
                # 2. 如果用户没有会员或已过期，从当前时间开始计算
                if member_expire_at and member_expire_at > datetime.now():
                    base_time = member_expire_at  # 累加：从原到期时间开始
                else:
                    base_time = datetime.now()  # 新购/已过期：从当前时间开始

                new_expire_at = base_time + timedelta(days=duration_days)

            # 生成订单ID
            order_id = f"ORD{uuid.uuid4().hex[:16].upper()}"

            # 准备订单数据
            order_data = {
                "order_id": order_id,
                "user_id": user_id,
                "package_id": package_id,
                "order_type": order_type,
                "amount": float(package.get("price", 0)),
                "actual_amount": float(package.get("price", 0)),
                "payment_method": payment_method,
                "payment_status": "pending",
                "package_name": package.get("name"),
                "duration_days": duration_days,
                "original_expire_at": original_expire_at,
                "new_expire_at": new_expire_at,
                "status": "active"
            }

            # 创建订单
            order = self.member_repo.create_order(order_data)
            if order:
                return {"success": True, "order": order}
            return {"success": False, "error": "创建订单失败"}
        except Exception as e:
            return {"success": False, "error": f"创建订单异常: {str(e)}"}

    def get_order(self, order_id: str) -> Dict[str, Any]:
        """获取订单详情"""
        try:
            order = self.member_repo.get_order_by_id(order_id)
            if order:
                return {"success": True, "order": order}
            return {"success": False, "error": "订单不存在"}
        except Exception as e:
            return {"success": False, "error": f"获取订单异常: {str(e)}"}

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
            result = self.member_repo.list_orders(
                user_id=user_id,
                payment_status=payment_status,
                status=status,
                start_date=start_date,
                end_date=end_date,
                page=page,
                page_size=page_size
            )
            return {"success": True, **result}
        except Exception as e:
            return {"success": False, "error": f"获取订单列表异常: {str(e)}"}

    def complete_payment(
        self,
        order_id: str,
        transaction_id: str
    ) -> Dict[str, Any]:
        """完成支付，激活会员"""
        try:
            # 获取订单信息
            order = self.member_repo.get_order_by_id(order_id)
            if not order:
                return {"success": False, "error": "订单不存在"}

            # 检查订单状态
            if order.get("payment_status") == "paid":
                return {"success": False, "error": "订单已支付"}

            # 更新订单状态
            success = self.member_repo.update_order(
                order_id=order_id,
                payment_status="paid",
                payment_time=datetime.now(),
                transaction_id=transaction_id
            )

            if not success:
                return {"success": False, "error": "更新订单状态失败"}

            # 更新用户会员信息
            user_id = order.get("user_id")
            package_id = order.get("package_id")
            new_expire_at = order.get("new_expire_at")

            # 获取套餐信息，确定会员等级
            package = self.member_repo.get_package_by_id(package_id)

            # 更新用户会员状态
            user_update_data = {
                "member_level": package_id,
                "member_expire_at": new_expire_at
            }

            self.user_repo.update_user(user_id, user_update_data)

            # 触发分销佣金计算（临时简化版：直接查询数据库）
            from app.infra.db import get_sync_engine
            from sqlalchemy import text
            engine = get_sync_engine()
            with engine.connect() as conn:
                # 检查配置
                config = conn.execute(
                    text("SELECT config_value FROM business.system_configs WHERE config_key = 'distribution_enabled'")
                ).fetchone()

                if config and config[0].lower() == "true":
                    # 获取用户邀请人
                    inviter = conn.execute(
                        text("SELECT inviter_id FROM business.users WHERE user_id = :user_id"),
                        {"user_id": user_id}
                    ).fetchone()

                    if inviter and inviter[0]:
                        # 检查邀请人是否是分销商
                        distributor = conn.execute(
                            text("SELECT status FROM business.distributors WHERE user_id = :user_id"),
                            {"user_id": inviter[0]}
                        ).fetchone()

                        if distributor and distributor[0] == "active":
                            # 计算佣金
                            commission_rate_result = conn.execute(
                                text("SELECT config_value FROM business.system_configs WHERE config_key = 'distribution_commission_rate'")
                            ).fetchone()

                            if commission_rate_result:
                                commission_rate = float(commission_rate_result[0])
                                # 从订单中获取金额
                                order_amount = float(order.get("amount", 0))
                                commission_amount = order_amount * commission_rate / 100

                                if commission_amount > 0:
                                    # 获取结算天数
                                    settlement_days_result = conn.execute(
                                        text("SELECT config_value FROM business.system_configs WHERE config_key = 'distribution_settlement_days'")
                                    ).fetchone()
                                    
                                    settlement_days = int(settlement_days_result[0]) if settlement_days_result else 7
                                    
                                    # 创建分销记录
                                    from datetime import timedelta
                                    import uuid
                                    record_id = f"DR{uuid.uuid4().hex[:14].upper()}"
                                    available_time = datetime.now() + timedelta(days=settlement_days)
                                    
                                    conn.execute(
                                        text("""
                                            INSERT INTO business.distribution_records 
                                            (record_id, promoter_id, new_user_id, order_id, commission_amount,
                                             commission_status, commission_type, commission_rate, order_amount, available_time)
                                            VALUES (:record_id, :promoter_id, :new_user_id, :order_id, :commission_amount,
                                                    'pending', 'direct', :commission_rate, :order_amount, :available_time)
                                        """),
                                        {
                                            "record_id": record_id,
                                            "promoter_id": inviter[0],
                                            "new_user_id": user_id,
                                            "order_id": order_id,
                                            "commission_amount": commission_amount,
                                            "commission_rate": commission_rate,
                                            "order_amount": order_amount,
                                            "available_time": available_time
                                        }
                                    )
                                    
                                    # 更新分销商统计（付款阶段只统计订单和佣金，不再增加累计邀请人数）
                                    conn.execute(
                                        text("""
                                            UPDATE business.distributors
                                            SET total_order_count = total_order_count + 1,
                                                frozen_commission = frozen_commission + :commission_amount,
                                                updated_at = :updated_at
                                            WHERE user_id = :user_id
                                        """),
                                        {
                                            "commission_amount": commission_amount,
                                            "updated_at": datetime.now(),
                                            "user_id": inviter[0]
                                        }
                                    )
                                    
                                    conn.commit()

            # 赠送积分
            try:
                from app.services.points.point_service import point_service
                points_result = point_service.process_order_points(order_id)
                if points_result.get("success"):
                    print(f"订单 {order_id} 积分赠送成功: {points_result.get('points_earned', 0)} 积分")
                else:
                    print(f"订单 {order_id} 积分赠送失败: {points_result.get('error')}")
            except Exception as points_error:
                print(f"赠送积分异常: {points_error}")

            return {
                "success": True,
                "message": "支付成功，会员已激活",
                "new_expire_at": new_expire_at
            }
        except Exception as e:
            return {"success": False, "error": f"完成支付异常: {str(e)}"}

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """取消订单"""
        try:
            # 获取订单信息
            order = self.member_repo.get_order_by_id(order_id)
            if not order:
                return {"success": False, "error": "订单不存在"}

            # 检查订单状态
            if order.get("payment_status") == "paid":
                return {"success": False, "error": "已支付订单不能取消"}

            # 更新订单状态
            success = self.member_repo.update_order(order_id=order_id, status="cancelled")
            if success:
                return {"success": True, "message": "订单已取消"}
            return {"success": False, "error": "取消订单失败"}
        except Exception as e:
            return {"success": False, "error": f"取消订单异常: {str(e)}"}

    # ==================== 会员权益管理 ====================

    def get_member_info(self, user_id: str) -> Dict[str, Any]:
        """获取用户会员信息"""
        try:
            # 获取用户基本信息
            user = self.user_repo.get_user_by_id(user_id)
            if not user:
                return {"success": False, "error": "用户不存在"}

            # 获取会员详细信息
            member_info = self.member_repo.get_user_member_info(user_id)

            # 获取使用统计
            usage_stats = self.member_repo.get_usage_stats(user_id)

            # 检查会员是否有效
            is_valid = self.member_repo.is_member_valid(user_id)

            # 组合返回数据
            result = {
                "success": True,
                "user_id": user_id,
                "member_level": user.get("member_level"),
                "member_expire_at": user.get("member_expire_at"),
                "is_member_valid": is_valid,
                "package_info": member_info if member_info else None,
                "usage_stats": usage_stats
            }

            return result
        except Exception as e:
            return {"success": False, "error": f"获取会员信息异常: {str(e)}"}

    def get_member_stats(self, user_id: str) -> Dict[str, Any]:
        """获取会员使用统计"""
        try:
            # 获取用户会员信息
            member_info = self.member_repo.get_user_member_info(user_id)
            if not member_info:
                return {"success": False, "error": "获取会员信息失败"}

            # 获取使用统计
            usage_stats = self.member_repo.get_usage_stats(user_id)

            # 获取今日使用记录（用于新配额类型）
            today_usage = self.member_repo.get_today_usage(user_id)

            # 获取 custom_config（包含新权益配置）
            # 注意：如果数据库中 custom_config 是 NULL，get() 会返回 None 而不是 {}
            # 所以需要额外判断
            custom_config = member_info.get("custom_config") or {}

            # 组合返回数据
            result = {
                "success": True,
                "user_id": user_id,
                "member_level": member_info.get("member_level"),
                "member_expire_at": member_info.get("member_expire_at"),
                # 标准权益配置
                "max_daily_chats": member_info.get("max_daily_chats", -1),
                "max_kb_count": member_info.get("max_kb_count", 5),
                "max_kb_documents": member_info.get("max_kb_documents", 100),
                "max_file_storage_mb": member_info.get("max_file_storage_mb", 1024),
                "max_file_count": member_info.get("max_file_count", 100),
                "enable_rag": member_info.get("enable_rag", False),
                "enable_web_search": member_info.get("enable_web_search", False),
                "enable_mcp_tools": member_info.get("enable_mcp_tools", False),
                # 新增权益配置（从 custom_config 读取）
                "enable_invoice_penetration": custom_config.get("enable_invoice_penetration", False),
                "max_invoice_penetration": custom_config.get("max_invoice_penetration", 0),
                "enable_panorama": custom_config.get("enable_panorama", False),
                "max_panorama": custom_config.get("max_panorama", 0),
                "enable_business_risk": custom_config.get("enable_business_risk", False),
                "max_business_risk": custom_config.get("max_business_risk", 0),
                # 合同审查权益配置（从 custom_config 读取）
                "enable_contract_review": custom_config.get("enable_contract_review", False),
                "enable_contract_screening": custom_config.get("enable_contract_screening", False),
                "max_contract_review_count": custom_config.get("max_contract_review_count", 0),
                "contract_screening_pages": custom_config.get("contract_screening_pages", 0),
                "multi_page_contract_pages": custom_config.get("multi_page_contract_pages", 0),
                # 使用情况
                "today_chats": usage_stats.get("today_chats", 0),
                "kb_count": usage_stats.get("kb_count", 0),
                "kb_documents_count": 0,  # 需要额外统计
                "used_storage_mb": usage_stats.get("used_storage_mb", 0),
                "file_count": usage_stats.get("file_count", 0),
                # 新增权益使用情况（从今日使用记录读取）
                "invoice_penetration_used": today_usage.get("invoice_penetration", 0),
                "panorama_used": today_usage.get("panorama", 0),
                "business_risk_used": today_usage.get("business_risk", 0),
                # 合同审查使用情况（从今日使用记录读取）
                "contract_review_count_used": today_usage.get("contract_review_count", 0),
                "contract_screening_pages_used": today_usage.get("contract_screening_pages", 0),
                "multi_page_contract_pages_used": today_usage.get("multi_page_contract_pages", 0),
                # 保留 custom_config 供后续使用
                "custom_config": custom_config,
                "benefits": member_info.get("benefits", [])
            }

            return result
        except Exception as e:
            return {"success": False, "error": f"获取会员统计异常: {str(e)}"}

    def check_privilege(
        self,
        user_id: str,
        privilege_type: str
    ) -> Dict[str, Any]:
        """
        检查会员权益是否可用（支持动态权限类型）

        支持的权限类型：
        - 标准权限：rag, web_search, mcp_tools
        - 动态权限：会自动检查套餐表中 enable_{privilege_type} 字段
        - custom_config 中的权限：从 custom_config JSON 中读取配置
        - 特殊权限：daily_chats（检查每日配额）

        扩展性说明：
        1. 在数据库 member_packages 表中添加 enable_xxx 字段
        2. 或在 custom_config 中添加 {"enable_xxx": true}
        """
        try:
            # 检查会员是否有效
            is_valid = self.member_repo.is_member_valid(user_id)
            if not is_valid:
                return {
                    "success": True,
                    "has_privilege": False,
                    "reason": "会员已过期或未开通"
                }

            # 获取会员信息
            member_info = self.member_repo.get_user_member_info(user_id)
            if not member_info:
                return {
                    "success": True,
                    "has_privilege": False,
                    "reason": "获取会员信息失败"
                }

            # 根据权益类型检查
            result = {"success": True, "has_privilege": True, "reason": ""}

            # 特殊处理：每日对话次数
            if privilege_type == "daily_chats":
                max_chats = member_info.get("max_daily_chats", -1)
                if max_chats != -1:  # -1表示无限制
                    today_chats = self.member_repo.get_usage_today(user_id, "daily_chats")
                    result["has_privilege"] = today_chats < max_chats
                    result["reason"] = f"今日对话次数已达上限（{max_chats}次）" if not result["has_privilege"] else ""
                    result["used"] = today_chats
                    result["max"] = max_chats
                return result

            # 标准权限检查
            standard_privileges = {
                "rag": "enable_rag",
                "web_search": "enable_web_search",
                "mcp_tools": "enable_mcp_tools",
            }

            # 检查是否为标准权限
            if privilege_type in standard_privileges:
                field_name = standard_privileges[privilege_type]
                has_permission = member_info.get(field_name, False)

                # 友好的错误消息
                error_messages = {
                    "rag": "当前套餐不支持RAG功能",
                    "web_search": "当前套餐不支持网络搜索",
                    "mcp_tools": "当前套餐不支持MCP工具",
                }

                result["has_privilege"] = has_permission
                result["reason"] = error_messages.get(privilege_type, "权限不足") if not has_permission else ""
                return result

            # 动态权限检查：优先从 custom_config JSON 中读取，然后查找 enable_{privilege_type} 字段
            # 这允许在不修改代码的情况下添加新权限

            # 1. 先尝试从 custom_config 中读取
            # 注意：如果数据库中 custom_config 是 NULL，get() 会返回 None 而不是 {}
            # 所以需要额外判断
            custom_config = member_info.get("custom_config") or {}
            if isinstance(custom_config, dict):
                # 检查 custom_config 中的 enable_{privilege_type} 或直接用 privilege_type
                config_key = f"enable_{privilege_type}"
                if config_key in custom_config:
                    has_permission = custom_config.get(config_key, False)
                    result["has_privilege"] = has_permission
                    if not has_permission:
                        privilege_name = privilege_type.replace("_", " ").title()
                        result["reason"] = f"当前套餐不支持{privilege_name}功能"
                    return result
                # 也支持直接用 privilege_type 作为 key（不带 enable_ 前缀）
                if privilege_type in custom_config:
                    has_permission = custom_config.get(privilege_type, False)
                    result["has_privilege"] = has_permission
                    if not has_permission:
                        privilege_name = privilege_type.replace("_", " ").title()
                        result["reason"] = f"当前套餐不支持{privilege_name}功能"
                    return result

            # 2. 然后尝试查找表字段 enable_{privilege_type}
            field_name = f"enable_{privilege_type}"
            has_permission = member_info.get(field_name, False)

            result["has_privilege"] = has_permission
            if not has_permission:
                # 生成友好的错误消息
                privilege_name = privilege_type.replace("_", " ").title()
                result["reason"] = f"当前套餐不支持{privilege_name}功能"

            return result
        except Exception as e:
            return {"success": False, "error": f"检查权益异常: {str(e)}"}

    def record_usage(
        self,
        user_id: str,
        usage_type: str,
        usage_amount: int = 1
    ) -> Dict[str, Any]:
        """记录会员权益使用"""
        try:
            success = self.member_repo.record_usage(user_id, usage_type, usage_amount)
            if success:
                return {"success": True, "message": "记录成功"}
            return {"success": False, "error": "记录失败"}
        except Exception as e:
            return {"success": False, "error": f"记录使用异常: {str(e)}"}

    # ==================== 会员续费和升级 ====================

    def renew_membership(
        self,
        user_id: str,
        package_id: str,
        payment_method: str = "wechat"
    ) -> Dict[str, Any]:
        """续费会员"""
        try:
            # 检查用户是否存在
            user = self.user_repo.get_user_by_id(user_id)
            if not user:
                return {"success": False, "error": "用户不存在"}

            # 创建续费订单
            result = self.create_order(
                user_id=user_id,
                package_id=package_id,
                order_type="renewal",
                payment_method=payment_method
            )

            return result
        except Exception as e:
            return {"success": False, "error": f"续费异常: {str(e)}"}

    def upgrade_membership(
        self,
        user_id: str,
        package_id: str,
        payment_method: str = "wechat"
    ) -> Dict[str, Any]:
        """升级会员"""
        try:
            # 检查用户是否存在
            user = self.user_repo.get_user_by_id(user_id)
            if not user:
                return {"success": False, "error": "用户不存在"}

            # 获取目标套餐
            target_package = self.member_repo.get_package_by_id(package_id)
            if not target_package:
                return {"success": False, "error": "套餐不存在"}

            # 获取当前套餐
            current_package_id = user.get("member_level")
            current_package = self.member_repo.get_package_by_id(current_package_id) if current_package_id else None

            # 检查是否为升级
            if current_package:
                current_price = current_package.get("price", 0)
                target_price = target_package.get("price", 0)
                if target_price <= current_price:
                    return {"success": False, "error": "目标套餐价格必须高于当前套餐"}

            # 创建升级订单
            result = self.create_order(
                user_id=user_id,
                package_id=package_id,
                order_type="upgrade",
                payment_method=payment_method
            )

            return result
        except Exception as e:
            return {"success": False, "error": f"升级异常: {str(e)}"}

    # ==================== 会员套餐推荐 ====================

    def get_recommended_packages(self, user_id: str) -> Dict[str, Any]:
        """获取推荐的套餐"""
        try:
            # 获取用户当前会员等级
            user = self.user_repo.get_user_by_id(user_id)
            if not user:
                return {"success": False, "error": "用户不存在"}

            current_level = user.get("member_level", "free")

            # 获取所有有效套餐
            packages_result = self.list_packages(status="active")
            if not packages_result.get("success"):
                return {"success": False, "error": "获取套餐列表失败"}

            all_packages = packages_result.get("packages", [])

            # 根据当前等级推荐套餐
            recommended = []

            if current_level == "free":
                # 免费用户推荐月卡
                recommended = [p for p in all_packages if p.get("package_type") == "month"]
            elif current_level in ["vip_month", "vip_quarter"]:
                # 月卡/季卡用户推荐年卡
                recommended = [p for p in all_packages if p.get("package_type") == "year"]
            else:
                # 其他情况推荐更高级的套餐
                current_package = self.member_repo.get_package_by_id(current_level)
                if current_package:
                    current_price = current_package.get("price", 0)
                    recommended = [p for p in all_packages if p.get("price", 0) > current_price]

            return {
                "success": True,
                "current_level": current_level,
                "recommended_packages": recommended[:3]  # 最多返回3个推荐
            }
        except Exception as e:
            return {"success": False, "error": f"获取推荐套餐异常: {str(e)}"}

    def get_actual_member_expire_at(self, user_id: str) -> Optional[datetime]:
        """
        获取用户实际会员到期时间（基于已支付的订单）
        获取最新创建的已支付订单的 new_expire_at
        如果 new_expire_at 为空，则根据 duration_days 和支付时间计算
        """
        try:
            from app.infra.db import get_sync_engine
            engine = get_sync_engine()
            with engine.connect() as conn:
                # 获取最新创建的已支付订单（按 created_at DESC）
                result = conn.execute(text("""
                    SELECT new_expire_at, duration_days, payment_time, created_at
                    FROM business.orders
                    WHERE user_id = :user_id
                      AND payment_status = 'paid'
                    ORDER BY created_at DESC
                    LIMIT 1
                """), {"user_id": user_id}).fetchone()

                if not result:
                    # 没有已支付的订单
                    return None

                new_expire_at = result[0]
                duration_days = result[1]
                payment_time = result[2] or result[3]  # payment_time 或 created_at

                print(f"[DEBUG] 最新已支付订单: new_expire_at={new_expire_at}, duration_days={duration_days}, payment_time={payment_time}, created_at={result[3]}")

                # 如果 new_expire_at 有值，直接返回
                if new_expire_at:
                    return new_expire_at

                # 如果 new_expire_at 为空但有 duration_days，计算到期时间
                if duration_days is not None and duration_days > 0 and payment_time:
                    calculated_expire = payment_time + timedelta(days=duration_days)
                    print(f"[DEBUG] 计算会员到期时间: {payment_time} + {duration_days}天 = {calculated_expire}")
                    return calculated_expire
                else:
                    print(f"[DEBUG] 无法计算到期时间: duration_days={duration_days}, payment_time={payment_time}")

                return None
        except Exception as e:
            print(f"获取实际会员到期时间失败: {e}")
            import traceback
            traceback.print_exc()
            return None


# 全局实例
member_service = MemberService()
