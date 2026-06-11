"""
积分业务逻辑层
处理积分相关的业务逻辑
"""
from typing import Dict, Any, Optional
from datetime import datetime
import json
import os

from app.services.points.point_repository import point_repository
from app.services.user.user_repository import user_repository


class PointService:
    """积分业务逻辑类"""

    def __init__(self):
        # JSON 配置文件路径
        self.config_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config/points_config.json")
        # 加载配置
        self.points_config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """从 JSON 文件加载配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 如果文件不存在，创建默认配置
                default_config = {
                    "payment_points_rate": 1,
                    "invitation_reward_points": 100
                }
                self._save_config(default_config)
                return default_config
        except Exception as e:
            print(f"加载积分配置失败: {e}")
            return {
                "payment_points_rate": 1,
                "invitation_reward_points": 100
            }

    def _save_config(self, config: Dict[str, Any]) -> bool:
        """保存配置到 JSON 文件"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存积分配置失败: {e}")
            return False

    def get_user_points_balance(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户积分余额

        Args:
            user_id: 用户ID

        Returns:
            积分余额信息
        """
        balance = point_repository.get_user_points_balance(user_id)
        return {
            "points_balance": balance
        }

    def add_points(
        self,
        user_id: str,
        points: int,
        change_type: str,
        change_reason: str = "",
        related_order_id: Optional[str] = None,
        related_user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        增加积分

        Args:
            user_id: 用户ID
            points: 积分数量（正数）
            change_type: 变化类型（order_payment/invitation_reward）
            change_reason: 变化原因
            related_order_id: 关联订单ID
            related_user_id: 关联用户ID

        Returns:
            操作结果
        """
        if points <= 0:
            return {
                "success": False,
                "error": "积分数量必须大于0",
                "error_code": "INVALID_POINTS"
            }

        # 验证用户是否存在
        user = user_repository.get_user_by_id(user_id)
        if not user:
            return {
                "success": False,
                "error": "用户不存在",
                "error_code": "USER_NOT_FOUND"
            }

        # 添加积分记录
        record_id = point_repository.add_point_record(
            user_id=user_id,
            points=points,
            change_type=change_type,
            change_reason=change_reason,
            related_order_id=related_order_id,
            related_user_id=related_user_id
        )

        if not record_id:
            return {
                "success": False,
                "error": "添加积分记录失败",
                "error_code": "ADD_RECORD_FAILED"
            }

        # 获取最新余额
        new_balance = point_repository.get_user_points_balance(user_id)

        return {
            "success": True,
            "record_id": record_id,
            "points": points,
            "new_balance": new_balance
        }

    def get_point_records(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        查询用户积分记录（分页）

        Args:
            user_id: 用户ID
            page: 页码
            page_size: 每页大小

        Returns:
            积分记录列表
        """
        result = point_repository.get_point_records(user_id, page, page_size)

        # 为每条记录添加额外信息
        records_with_details = []
        for record in result["records"]:
            # 如果是邀请奖励，获取被邀请人昵称
            if record["change_type"] == "invitation_reward" and record["related_user_id"]:
                invited_user = user_repository.get_user_by_id(record["related_user_id"])
                record["related_user_nickname"] = invited_user.get("nickname") if invited_user else None

            # 如果是支付积分，获取订单金额
            if record["change_type"] == "order_payment" and record["related_order_id"]:
                try:
                    from app.infra.db import get_sync_engine
                    from sqlalchemy import text
                    engine = get_sync_engine()
                    with engine.connect() as conn:
                        order_result = conn.execute(
                            text("""
                                SELECT actual_amount
                                FROM business.orders
                                WHERE order_id = :order_id
                            """),
                            {"order_id": record["related_order_id"]}
                        ).fetchone()
                        record["order_amount"] = float(order_result[0]) if order_result and order_result[0] else None
                except Exception:
                    record["order_amount"] = None

            records_with_details.append(record)

        result["records"] = records_with_details
        return result

    def is_first_order(self, user_id: str) -> bool:
        """
        判断是否是用户的第一个支付订单

        Args:
            user_id: 用户ID

        Returns:
            是否是首次支付
        """
        return point_repository.is_first_order(user_id)

    def get_points_config(self) -> Dict[str, Any]:
        """
        获取积分配置（从 JSON 文件）

        Returns:
            积分配置信息
        """
        # 重新加载配置以获取最新值
        self.points_config = self._load_config()
        return self.points_config.copy()

    def update_points_config(
        self,
        payment_points_rate: int,
        invitation_reward_points: int
    ) -> Dict[str, Any]:
        """
        更新积分配置（保存到 JSON 文件）

        Args:
            payment_points_rate: 支付积分比例
            invitation_reward_points: 邀请奖励积分

        Returns:
            更新后的配置
        """
        # 验证参数
        if payment_points_rate < 1 or payment_points_rate > 1000:
            return {
                "success": False,
                "error": "支付积分比例必须在1-1000之间",
                "error_code": "INVALID_RATE"
            }

        if invitation_reward_points < 0 or invitation_reward_points > 10000:
            return {
                "success": False,
                "error": "邀请奖励积分必须在0-10000之间",
                "error_code": "INVALID_REWARD"
            }

        # 更新配置
        self.points_config["payment_points_rate"] = payment_points_rate
        self.points_config["invitation_reward_points"] = invitation_reward_points

        # 保存到文件
        if self._save_config(self.points_config):
            return {
                "success": True,
                "config": self.points_config.copy()
            }
        else:
            return {
                "success": False,
                "error": "保存配置失败",
                "error_code": "SAVE_FAILED"
            }

    def get_points_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        获取积分统计数据

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            统计数据
        """
        return point_repository.get_points_statistics(start_date, end_date)

    def process_order_points(
        self,
        order_id: str,
        custom_points: Optional[int] = None,
        custom_reason: Optional[str] = None,
        skip_invitation_reward: bool = False
    ) -> Dict[str, Any]:
        """
        处理订单积分（支付成功后调用或管理员手动处理）

        Args:
            order_id: 订单ID
            custom_points: 自定义积分数量（不填则按订单金额自动计算）
            custom_reason: 自定义原因（不填则使用默认原因）
            skip_invitation_reward: 是否跳过邀请奖励（默认false）

        Returns:
            处理结果
        """
        try:
            # 获取订单信息
            from app.infra.db import get_sync_engine
            from sqlalchemy import text
            engine = get_sync_engine()

            with engine.connect() as conn:
                order_result = conn.execute(
                    text("""
                        SELECT order_id, user_id, actual_amount, payment_status
                        FROM business.orders
                        WHERE order_id = :order_id
                    """),
                    {"order_id": order_id}
                ).fetchone()

                if not order_result:
                    return {
                        "success": False,
                        "error": "订单不存在",
                        "error_code": "ORDER_NOT_FOUND"
                    }

                order_id, user_id, actual_amount, payment_status = order_result

                if payment_status != "paid":
                    return {
                        "success": False,
                        "error": "订单未支付",
                        "error_code": "ORDER_NOT_PAID"
                    }

            # 计算积分（使用自定义积分或按比例计算）
            if custom_points is not None:
                points = custom_points
                is_custom = True
            else:
                points = int(actual_amount * self.points_config["payment_points_rate"])
                is_custom = False

            if points <= 0:
                return {
                    "success": True,
                    "message": "订单金额不足以获得积分",
                    "points_earned": 0
                }

            # 设置积分原因
            change_reason = custom_reason if custom_reason else "订单支付获得积分"
            if is_custom and not custom_reason:
                change_reason = f"管理员手动赠送积分（订单{order_id}）"

            # 送积分给下单用户
            result1 = self.add_points(
                user_id=user_id,
                points=points,
                change_type="order_payment",
                change_reason=change_reason,
                related_order_id=order_id
            )

            if not result1.get("success"):
                return {
                    "success": False,
                    "error": "赠送积分失败",
                    "error_code": "ADD_POINTS_FAILED"
                }

            # 检查是否是首次支付，送邀请积分（除非跳过）
            result2 = {"success": True, "points": 0}
            if not skip_invitation_reward and not is_custom:
                if self.is_first_order(user_id):
                    # 获取邀请人
                    user = user_repository.get_user_by_id(user_id)
                    inviter_id = user.get("inviter_id") if user else None

                    if inviter_id:
                        result2 = self.add_points(
                            user_id=inviter_id,
                            points=self.points_config["invitation_reward_points"],
                            change_type="invitation_reward",
                            change_reason="邀请用户奖励",
                            related_user_id=user_id
                        )

            return {
                "success": True,
                "message": "积分赠送成功",
                "points_earned": points,
                "invitation_reward_earned": result2.get("points", 0) if result2.get("success") else 0,
                "is_custom": is_custom,
                "change_reason": change_reason
            }

        except Exception as e:
            print(f"处理订单积分失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "error_code": "PROCESS_FAILED"
            }


# 全局积分服务实例
point_service = PointService()
