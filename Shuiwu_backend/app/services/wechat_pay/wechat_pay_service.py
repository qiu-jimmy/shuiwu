"""
微信支付服务层 - 业务逻辑
"""
import os
import uuid
import json
from typing import Dict, Any, Optional
from datetime import datetime
# 使用官方 SDK 客户端
from app.infra.wechat_pay_sdk_client import wechat_pay_sdk_client
from app.services.wechat_pay.signature import WechatPaySignature
from app.services.member.member_repository import member_repository
from app.services.user.user_repository import user_repository
from app.services.points.point_service import point_service
from app.infra.logging_config import get_logger, get_payment_logger

# 配置日志
logger = get_logger(__name__)
payment_logger = get_payment_logger()


class WechatPayService:
    """微信支付业务逻辑层"""

    def __init__(self):
        """初始化服务"""
        self.client = wechat_pay_sdk_client
        self.member_repo = member_repository
        self.user_repo = user_repository
        self.point_service = point_service

    async def create_jsapi_order(
        self,
        order_id: str,
        openid: str
    ) -> Dict[str, Any]:
        """
        创建JSAPI支付订单

        Args:
            order_id: 内部订单ID
            openid: 微信用户OpenID

        Returns:
            包含小程序支付参数的响应
        """
        try:
            # 获取订单信息
            order = self.member_repo.get_order_by_id(order_id)
            if not order:
                return {"success": False, "error": "订单不存在"}

            # 检查订单状态
            if order.get("payment_status") == "paid":
                return {"success": False, "error": "订单已支付"}

            # 获取套餐信息
            package_id = order.get("package_id")
            package = self.member_repo.get_package_by_id(package_id)
            if not package:
                return {"success": False, "error": "套餐不存在"}

            # 金额转换为分
            total_amount = int(order.get("amount", 0) * 100)

            # 调用微信支付JSAPI下单
            # 官方 SDK 会自动处理 JSON 序列化和签名
            response = await self.client.jsapi_order(
                description=package.get("name", "会员套餐"),
                out_trade_no=order_id,
                total_amount=total_amount,
                openid=openid,
                attach=json.dumps({"order_id": order_id}, ensure_ascii=False)
            )

            # 检查响应
            if "prepay_id" not in response:
                return {"success": False, "error": f"微信支付下单失败: {response}"}

            prepay_id = response["prepay_id"]

            # 更新订单的prepay_id
            self.member_repo.update_order(
                order_id=order_id,
                prepay_id=prepay_id
            )

            # 构建小程序支付参数
            pay_params = self.client.build_mini_program_pay_params(prepay_id)

            return {
                "success": True,
                "prepay_id": prepay_id,
                "pay_params": pay_params
            }

        except Exception as e:
            return {"success": False, "error": f"创建支付订单失败: {str(e)}"}

    async def handle_payment_notify(
        self,
        timestamp: str,
        nonce: str,
        body: str,
        signature: str
    ) -> Dict[str, Any]:
        """
        处理微信支付回调通知（带幂等性保护）

        Args:
            timestamp: 时间戳
            nonce: 随机字符串
            body: 回调body
            signature: 签名

        Returns:
            处理结果
        """
        transaction_id = None
        out_trade_no = None
        order_id = None

        try:
            # 记录接收到的回调基本信息
            payment_logger.info(f"=== 支付回调开始 ===")
            payment_logger.info(f"Timestamp: {timestamp}")
            payment_logger.info(f"Nonce: {nonce}")
            payment_logger.info(f"Signature: {signature[:50]}..." if len(signature) > 50 else f"Signature: {signature}")
            payment_logger.info(f"Body length: {len(body)}")

            # 获取平台公钥路径
            public_key_path = os.getenv("WECHAT_PAY_PUBLIC_KEY_PATH")
            payment_logger.info(f"公钥路径: {public_key_path}")

            # 检查公钥文件是否存在
            if not public_key_path or not os.path.exists(public_key_path):
                payment_logger.error(f"公钥文件不存在: {public_key_path}")
                return {"success": False, "error": "公钥文件不存在"}

            # 构建验签消息（用于调试）
            message_to_verify = f"{timestamp}\n{nonce}\n{body}\n"
            payment_logger.debug(f"验签消息: {repr(message_to_verify[:200])}...")

            # 验证签名
            is_valid = WechatPaySignature.verify_wechat_pay_notify(
                timestamp=timestamp,
                nonce=nonce,
                body=body,
                signature=signature,
                public_key_path=public_key_path
            )

            if not is_valid:
                payment_logger.error("验签失败 - 可能原因：")
                payment_logger.error("  1. 公钥文件不正确或已过期")
                payment_logger.error("  2. 微信证书序列号已变更")
                payment_logger.error("  3. 回调数据被篡改")
                payment_logger.error("  4. 时间戳/nonce/body 获取错误")
                return {"success": False, "error": "签名验证失败"}

            payment_logger.info("验签成功")

            # 解析回调数据
            notify_data = json.loads(body)
            resource = notify_data.get("resource", {})

            # 解密加密数据
            decrypted_data = WechatPaySignature.decrypt_callback_resource(
                ciphertext=resource.get("ciphertext"),
                associated_data=resource.get("associated_data"),
                nonce=resource.get("nonce"),
                api_v3_key=os.getenv("WECHAT_PAY_API_V3_KEY")
            )

            # 解析解密后的数据
            order_data = json.loads(decrypted_data)
            payment_logger.info(f"解密后的订单数据: {json.dumps(order_data, ensure_ascii=False)}")

            # 获取订单信息
            out_trade_no = order_data.get("out_trade_no")
            transaction_id = order_data.get("transaction_id")
            trade_state = order_data.get("trade_state")

            payment_logger.info(f"交易号: {transaction_id}, 订单号: {out_trade_no}, 交易状态: {trade_state}")

            if trade_state != "SUCCESS":
                payment_logger.warning(f"支付状态不是SUCCESS: {trade_state}")
                return {"success": False, "error": f"支付未成功: {trade_state}"}

            # ===== 幂等性检查：检查交易是否已处理 =====
            if self.member_repo.is_transaction_processed(transaction_id):
                payment_logger.info(f"交易 {transaction_id} 已处理过，跳过")
                return {"success": True, "message": "订单已处理", "duplicate": True}

            # ===== 使用行锁获取订单 =====
            order = self.member_repo.get_order_for_update(out_trade_no)
            if not order:
                payment_logger.error(f"订单不存在: {out_trade_no}")
                return {"success": False, "error": "订单不存在"}

            order_id = order.get("order_id")
            payment_logger.info(f"获取到订单: {order_id}, 当前支付状态: {order.get('payment_status')}")

            # ===== 二次检查：订单是否已支付 =====
            if order.get("payment_status") == "paid":
                payment_logger.info(f"订单 {order_id} 已支付，记录回调后跳过")

                # 记录这次回调（标记为重复）
                self.member_repo.try_insert_payment_notify_record(
                    transaction_id=transaction_id,
                    order_id=order_id,
                    out_trade_no=out_trade_no,
                    trade_state=trade_state,
                    notify_data=decrypted_data
                )

                return {"success": True, "message": "订单已处理", "duplicate": True}

            # ===== 尝试插入支付回调记录（幂等性保护） =====
            insert_result = self.member_repo.try_insert_payment_notify_record(
                transaction_id=transaction_id,
                order_id=order_id,
                out_trade_no=out_trade_no,
                trade_state=trade_state,
                notify_data=decrypted_data
            )

            if insert_result.get("is_duplicate"):
                payment_logger.info(f"交易 {transaction_id} 在插入记录时发现重复")
                return {"success": True, "message": "订单已处理", "duplicate": True}

            # ===== 使用条件更新订单状态（乐观锁） =====
            update_success = self.member_repo.update_order_with_condition(
                order_id=order_id,
                expected_payment_status=order.get("payment_status"),
                new_payment_status="paid",
                payment_time=datetime.now(),
                transaction_id=transaction_id
            )

            if not update_success:
                payment_logger.error(f"更新订单状态失败，可能已被其他进程处理: {order_id}")
                # 更新记录为失败
                self.member_repo.update_payment_notify_record(
                    transaction_id=transaction_id,
                    process_result="failed",
                    error_message="更新订单状态失败"
                )
                return {"success": False, "error": "更新订单状态失败"}

            payment_logger.info(f"订单 {order_id} 支付状态更新成功")

            # 更新用户会员信息
            user_id = order.get("user_id")
            package_id = order.get("package_id")
            new_expire_at = order.get("new_expire_at")

            package = self.member_repo.get_package_by_id(package_id)
            user_update_data = {
                "member_level": package_id,
                "member_expire_at": new_expire_at
            }

            self.user_repo.update_user(user_id, user_update_data)
            payment_logger.info(f"用户 {user_id} 会员信息更新成功，到期时间: {new_expire_at}")

            # 增加积分奖励（按订单金额计算）
            payment_logger.info(f"开始为订单 {order_id} 增加积分")
            points_result = self.point_service.process_order_points(order_id)
            if points_result.get("success"):
                points_earned = points_result.get("points_earned", 0)
                payment_logger.info(f"订单 {order_id} 积分增加成功: {points_earned}分")
            else:
                payment_logger.error(f"订单 {order_id} 积分增加失败: {points_result.get('error', 'Unknown error')}")

            # 触发分销佣金计算
            await self._process_distribution_commission(order)

            payment_logger.info(f"=== 支付回调处理成功 ===")

            return {
                "success": True,
                "message": "支付成功",
                "order_id": out_trade_no
            }

        except Exception as e:
            payment_logger.error(f"=== 支付回调处理异常 ===")
            payment_logger.error(f"异常信息: {str(e)}", exc_info=True)

            # 记录失败到支付回调表
            if transaction_id:
                self.member_repo.update_payment_notify_record(
                    transaction_id=transaction_id,
                    process_result="failed",
                    error_message=str(e)
                )

            return {"success": False, "error": f"处理支付回调失败: {str(e)}"}

    async def query_payment_status(
        self,
        order_id: str
    ) -> Dict[str, Any]:
        """
        查询支付状态（带幂等性保护）

        Args:
            order_id: 订单ID

        Returns:
            支付状态
        """
        try:
            payment_logger.info(f"查询订单支付状态: {order_id}")

            # 调用微信支付查询接口
            result = await self.client.query_order(order_id)

            trade_state = result.get("trade_state")
            transaction_id = result.get("transaction_id")

            payment_logger.info(f"订单 {order_id} 微信返回状态: {trade_state}, 交易号: {transaction_id}")

            # 如果支付成功，更新本地订单状态（带幂等性保护）
            if trade_state == "SUCCESS":
                # 使用行锁获取订单
                order = self.member_repo.get_order_for_update(order_id)

                if order and order.get("payment_status") != "paid":
                    payment_logger.info(f"订单 {order_id} 未支付，开始更新支付状态")

                    # 检查交易是否已处理
                    if transaction_id and self.member_repo.is_transaction_processed(transaction_id):
                        payment_logger.info(f"交易 {transaction_id} 已处理，跳过")
                    else:
                        # 使用条件更新订单状态
                        update_success = self.member_repo.update_order_with_condition(
                            order_id=order_id,
                            expected_payment_status=order.get("payment_status"),
                            new_payment_status="paid",
                            payment_time=datetime.now(),
                            transaction_id=transaction_id
                        )

                        if update_success:
                            # 更新用户会员信息
                            user_id = order.get("user_id")
                            package_id = order.get("package_id")
                            new_expire_at = order.get("new_expire_at")

                            package = self.member_repo.get_package_by_id(package_id)
                            user_update_data = {
                                "member_level": package_id,
                                "member_expire_at": new_expire_at
                            }

                            self.user_repo.update_user(user_id, user_update_data)
                            payment_logger.info(f"用户 {user_id} 会员信息更新成功，到期时间: {new_expire_at}")

                            # 增加积分奖励（按订单金额计算）
                            payment_logger.info(f"开始为订单 {order_id} 增加积分")
                            points_result = self.point_service.process_order_points(order_id)
                            if points_result.get("success"):
                                points_earned = points_result.get("points_earned", 0)
                                payment_logger.info(f"订单 {order_id} 积分增加成功: {points_earned}分")
                            else:
                                payment_logger.error(f"订单 {order_id} 积分增加失败: {points_result.get('error', 'Unknown error')}")

                            # 补偿触发分销佣金计算（防止回调异常时遗漏）
                            await self._process_distribution_commission(order)

                            # 记录支付回调
                            if transaction_id:
                                self.member_repo.try_insert_payment_notify_record(
                                    transaction_id=transaction_id,
                                    order_id=order_id,
                                    out_trade_no=order_id,
                                    trade_state=trade_state
                                )

                            payment_logger.info(f"订单 {order_id} 支付状态更新成功")
                        else:
                            payment_logger.warning(f"订单 {order_id} 支付状态更新失败，可能已被其他进程处理")

            return {
                "success": True,
                "trade_state": trade_state,
                "transaction_id": transaction_id
            }

        except Exception as e:
            payment_logger.error(f"查询支付状态异常: {order_id}, {str(e)}")
            return {"success": False, "error": f"查询支付状态失败: {str(e)}"}

    async def close_order(
        self,
        order_id: str
    ) -> Dict[str, Any]:
        """
        关闭订单

        Args:
            order_id: 订单ID

        Returns:
            关闭结果
        """
        try:
            await self.client.close_order(order_id)

            # 更新本地订单状态
            self.member_repo.update_order(order_id=order_id, status="cancelled")

            return {"success": True, "message": "订单已关闭"}

        except Exception as e:
            return {"success": False, "error": f"关闭订单失败: {str(e)}"}

    async def create_refund(
        self,
        order_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        申请退款

        Args:
            order_id: 订单ID
            reason: 退款原因

        Returns:
            退款结果
        """
        try:
            # 获取订单信息
            order = self.member_repo.get_order_by_id(order_id)
            if not order:
                return {"success": False, "error": "订单不存在"}

            if order.get("payment_status") != "paid":
                return {"success": False, "error": "订单未支付，无法退款"}

            # 生成退款单号
            refund_id = f"RF{uuid.uuid4().hex[:16].upper()}"

            # 金额转换为分
            total_amount = int(order.get("amount", 0) * 100)
            refund_amount = total_amount

            # 调用微信支付退款接口
            result = await self.client.create_refund(
                out_trade_no=order_id,
                out_refund_no=refund_id,
                total_amount=total_amount,
                refund_amount=refund_amount,
                reason=reason
            )

            return {
                "success": True,
                "refund_id": refund_id,
                "status": result.get("status", "PROCESSING")
            }

        except Exception as e:
            return {"success": False, "error": f"申请退款失败: {str(e)}"}

    async def _process_distribution_commission(
        self,
        order: Dict[str, Any]
    ) -> None:
        """
        处理分销佣金（支付成功后）

        Args:
            order: 订单信息
        """
        try:
            from app.infra.db import get_sync_engine
            from sqlalchemy import text

            user_id = order.get("user_id")
            order_id = order.get("order_id")

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
                                order_amount = float(order.get("amount", 0))
                                commission_amount = order_amount * commission_rate / 100

                                if commission_amount > 0:
                                    # 获取结算天数
                                    settlement_days_result = conn.execute(
                                        text("SELECT config_value FROM business.system_configs WHERE config_key = 'distribution_settlement_days'")
                                    ).fetchone()

                                    settlement_days = int(settlement_days_result[0]) if settlement_days_result else 7

                                    # 创建分销记录
                                    record_id = f"DR{uuid.uuid4().hex[:14].upper()}"
                                    available_time = datetime.now() + __import__('datetime').timedelta(days=settlement_days)

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

        except Exception as e:
            # 分销处理失败不影响主流程
            print(f"处理分销佣金失败: {str(e)}")


# 全局实例
wechat_pay_service = WechatPayService()
