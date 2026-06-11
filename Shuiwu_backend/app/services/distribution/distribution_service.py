"""
分销推广业务逻辑层
"""
import os
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from io import BytesIO
from sqlalchemy import text


def _get_engine():
    """延迟导入 get_sync_engine，避免模块级别导入"""
    from app.infra.db import get_sync_engine
    return get_sync_engine()


class DistributionService:
    """分销推广业务逻辑"""

    # ==================== 分销商管理 ====================

    def become_distributor(self, user_id: str) -> Dict[str, Any]:
        """成为分销商"""
        try:
            engine = _get_engine()
            with engine.connect() as conn:
                # 检查是否已经是分销商
                result = conn.execute(
                    text("SELECT user_id FROM business.distributors WHERE user_id = :user_id"),
                    {"user_id": user_id}
                ).fetchone()

                if result:
                    return {"success": False, "error": "您已经是分销商"}

                # 生成推广码
                import string
                import random
                while True:
                    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                    check = conn.execute(
                        text("SELECT user_id FROM business.distributors WHERE distributor_code = :code"),
                        {"code": code}
                    ).fetchone()
                    if not check:
                        break

                # 创建分销商
                conn.execute(
                    text("""
                        INSERT INTO business.distributors (user_id, distributor_code, parent_id, distributor_level, status)
                        VALUES (:user_id, :code, NULL, 1, 'active')
                    """),
                    {"user_id": user_id, "code": code}
                )
                conn.commit()

                distributor = conn.execute(
                    text("SELECT * FROM business.distributors WHERE user_id = :user_id"),
                    {"user_id": user_id}
                ).fetchone()

                return {"success": True, "distributor": {"user_id": distributor[0], "distributor_code": distributor[1]}}

        except Exception as e:
            return {"success": False, "error": f"成为分销商异常: {str(e)}"}

    def get_my_distributor_code(self, user_id: str) -> Dict[str, Any]:
        """获取我的推广码"""
        try:
            engine = _get_engine()
            with engine.connect() as conn:
                # 查询分销商的推广码
                result = conn.execute(
                    text("SELECT distributor_code FROM business.distributors WHERE user_id = :user_id"),
                    {"user_id": user_id}
                ).fetchone()

                if not result:
                    return {"success": False, "error": "您还不是分销商"}

                code = result[0]

                # 查询用户的邀请人信息
                inviter_info = conn.execute(
                    text("""
                        SELECT u.inviter_id, inviter.nickname, inviter.avatar_url,
                               d.distributor_code as inviter_code
                        FROM business.users u
                        LEFT JOIN business.users inviter ON u.inviter_id = inviter.user_id
                        LEFT JOIN business.distributors d ON inviter.user_id = d.user_id
                        WHERE u.user_id = :user_id
                    """),
                    {"user_id": user_id}
                ).fetchone()

                inviter_data = None
                if inviter_info and inviter_info[0]:
                    inviter_data = {
                        "inviter_id": inviter_info[0],
                        "inviter_nickname": inviter_info[1],
                        "inviter_avatar": inviter_info[2],
                        "inviter_code": inviter_info[3]
                    }

                return {
                    "success": True,
                    "distributor_code": code,
                    "share_link": f"{os.getenv('FRONTEND_URL', 'https://yourdomain.com')}/register?ref={code}",
                    "share_text": f"邀请您使用我们的服务，输入邀请码：{code}",
                    "inviter": inviter_data  # 新增：邀请人信息
                }

        except Exception as e:
            return {"success": False, "error": f"获取推广码异常: {str(e)}"}

    async def generate_mini_qrcode(self, user_id: str, page: Optional[str] = None, img: int = 1) -> Dict[str, Any]:
        """
        生成带小程序二维码的分销海报

        Args:
            user_id: 用户ID
            page: 小程序页面路径（可选，如 pages/index/index）
            img: 海报模板编号（1-4，默认1）

        Returns:
            包含拼接后的海报图片的响应（base64格式）
        """
        try:
            from PIL import Image
            from app.services.wechat_pay.wechat_mini_client import wechat_mini_client

            engine = _get_engine()
            with engine.connect() as conn:
                # 查询分销商的推广码
                result = conn.execute(
                    text("SELECT distributor_code FROM business.distributors WHERE user_id = :user_id"),
                    {"user_id": user_id}
                ).fetchone()

                if not result:
                    return {"success": False, "error": "您还不是分销商"}

                distributor_code = result[0]

            print(f"[分销海报] 生成海报，用户: {user_id}, 推广码: {distributor_code}, 页面: {page or '默认主页'}, 模板: {img}")

            # 1. 获取海报模板路径（模板在项目根目录的 templates 文件夹）
            # 根据 img 参数选择模板：poster1.png, poster2.png, poster3.png, poster4.png
            img = max(1, min(4, img))  # 限制在 1-4 范围内
            template_filename = f"poster{img}.png"
            template_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                "templates",
                template_filename
            )

            if not os.path.exists(template_path):
                return {"success": False, "error": f"海报模板不存在: {template_path}"}

            # 2. 加载海报模板
            poster = Image.open(template_path).convert("RGBA")
            poster_width, poster_height = poster.size

            # 3. 调用微信API生成小程序码
            qrcode_bytes = await wechat_mini_client.get_unlimited_qrcode(
                scene=distributor_code,
                page=page,
                check_path=False,
                env_version="release",
                width=430  # 获取高清二维码
            )

            # 4. 打开二维码图片并调整大小
            qrcode_img = Image.open(BytesIO(qrcode_bytes)).convert("RGBA")
            qrcode_size = 190  # 二维码大小（缩小）
            qrcode_resized = qrcode_img.resize((qrcode_size, qrcode_size), Image.Resampling.LANCZOS)

            # 5. 计算二维码位置（右下角，距离右边和底部各40px）
            # 模板2、3、4需要向左移动20px，向上移动20px
            if img == 1:
                qrcode_x = poster_width - qrcode_size - 18
                qrcode_y = poster_height - qrcode_size - 15
            else:  # img == 2, 3, 4
                qrcode_x = poster_width - qrcode_size - 18 - 25  # 向左20px
                qrcode_y = poster_height - qrcode_size - 15 - 25  # 向上20px

            # 6. 将二维码粘贴到海报上
            poster.paste(qrcode_resized, (qrcode_x, qrcode_y), qrcode_resized)

            # 7. 转换为RGB并保存为字节流
            poster_rgb = Image.new("RGB", poster.size, (255, 255, 255))
            poster_rgb.paste(poster, mask=poster.split()[-1])  # 使用alpha通道作为mask

            output_buffer = BytesIO()
            poster_rgb.save(output_buffer, format="PNG", quality=95)
            poster_bytes = output_buffer.getvalue()

            print(f"[分销海报] 生成成功，推广码: {distributor_code}, 图片大小: {len(poster_bytes)} bytes")

            return {
                "success": True,
                "qrcode": poster_bytes,  # 返回拼接后的海报
                "distributor_code": distributor_code
            }

        except Exception as e:
            print(f"[分销海报] 生成失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": f"生成海报异常: {str(e)}"}

    def validate_distributor_code(self, code: str) -> Dict[str, Any]:
        """验证推广码有效性"""
        try:
            engine = _get_engine()
            with engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT user_id FROM business.distributors
                        WHERE distributor_code = :code AND status = 'active'
                    """),
                    {"code": code}
                ).fetchone()

                if not result:
                    return {"valid": False, "error": "推广码无效"}
                return {"valid": True, "promoter_id": result[0]}

        except Exception as e:
            return {"valid": False, "error": f"验证推广码异常: {str(e)}"}

    def get_distributor_stats(self, user_id: str) -> Dict[str, Any]:
        """获取分销商统计信息"""
        try:
            engine = _get_engine()
            with engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT * FROM business.distributors WHERE user_id = :user_id
                    """),
                    {"user_id": user_id}
                ).fetchone()

                if not result:
                    return {"success": False, "error": "分销商不存在"}

                return {
                    "success": True,
                    "stats": {
                        "total_children_count": result[5],
                        "total_order_count": result[6],
                        "total_commission": float(result[7]),
                        "available_commission": float(result[8]),
                        "frozen_commission": float(result[9]),
                        "total_withdrawn": float(result[10])
                    }
                }

        except Exception as e:
            return {"success": False, "error": f"获取统计信息异常: {str(e)}"}

    # ==================== 其他方法（实现真实查询）====================

    def list_my_records(self, promoter_id: str, status: Optional[str] = None, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """获取我的分销记录"""
        try:
            engine = _get_engine()
            with engine.connect() as conn:
                # 构建查询条件
                conditions = ["promoter_id = :promoter_id"]
                params = {"promoter_id": promoter_id}

                if status:
                    conditions.append("commission_status = :status")
                    params["status"] = status

                where_clause = f"WHERE {' AND '.join(conditions)}"

                # 查询总数
                count_result = conn.execute(
                    text(f"SELECT COUNT(*) FROM business.distribution_records {where_clause}"),
                    params
                ).fetchone()
                total = count_result[0] if count_result else 0

                # 查询记录
                offset = (page - 1) * page_size
                records_query = text(f"""
                    SELECT
                        record_id,
                        promoter_id,
                        new_user_id,
                        order_id,
                        commission_amount,
                        commission_status,
                        commission_type,
                        commission_rate,
                        order_amount,
                        available_time,
                        settled_time,
                        expire_time,
                        created_at
                    FROM business.distribution_records
                    {where_clause}
                    ORDER BY created_at DESC
                    LIMIT :page_size OFFSET :offset
                """)

                params["page_size"] = page_size
                params["offset"] = offset

                result = conn.execute(records_query, params)

                records = []
                for row in result:
                    # 获取新用户昵称（如果有的话）
                    new_user_nickname = None
                    if row[2]:  # new_user_id
                        user_info = conn.execute(
                            text("SELECT nickname FROM business.users WHERE user_id = :uid"),
                            {"uid": row[2]}
                        ).fetchone()
                        new_user_nickname = user_info[0] if user_info else None

                    records.append({
                        "record_id": row[0],
                        "promoter_id": row[1],
                        "new_user_id": row[2],
                        "new_user_nickname": new_user_nickname,
                        "order_id": row[3],
                        "commission_amount": float(row[4]) if row[4] else 0,
                        "commission_status": row[5],
                        "commission_type": row[6],
                        "commission_rate": float(row[7]) if row[7] else 0,
                        "order_amount": float(row[8]) if row[8] else 0,
                        "available_time": row[9].isoformat() if row[9] else None,
                        "settled_time": row[10].isoformat() if row[10] else None,
                        "expire_time": row[11].isoformat() if row[11] else None,
                        "created_at": row[12].isoformat() if row[12] else None
                    })

                return {
                    "success": True,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "records": records
                }

        except Exception as e:
            return {"success": False, "error": f"获取分销记录失败: {str(e)}"}

    def create_withdrawal_request(self, user_id: str, amount: float, withdrawal_method: str, account_name: str, account_number: str, bank_name: Optional[str] = None, bank_branch: Optional[str] = None) -> Dict[str, Any]:
        """创建提现申请"""
        try:
            engine = _get_engine()
            with engine.connect() as conn:
                # 1. 检查是否是分销商
                distributor = conn.execute(
                    text("""
                        SELECT user_id, status, available_commission
                        FROM business.distributors
                        WHERE user_id = :user_id
                    """),
                    {"user_id": user_id}
                ).fetchone()

                if not distributor:
                    return {"success": False, "error": "您还不是分销商"}

                if distributor[1] != 'active':
                    return {"success": False, "error": "您的分销商账户已被冻结，无法提现"}

                # 2. 检查提现金额
                available_commission = float(distributor[2])

                # 获取最低提现门槛配置
                min_withdrawal = 50.0  # 默认50元
                try:
                    min_config = conn.execute(
                        text("SELECT config_value FROM business.system_configs WHERE config_key = 'distribution_min_withdrawal'")
                    ).fetchone()
                    if min_config:
                        min_withdrawal = float(min_config[0])
                except:
                    pass

                if amount < min_withdrawal:
                    return {"success": False, "error": f"提现金额不能低于 {min_withdrawal} 元"}

                if amount > available_commission:
                    return {"success": False, "error": f"可提现余额不足，当前可提现 {available_commission:.2f} 元"}

                # 3. 创建提现申请
                withdrawal_id = str(uuid.uuid4())

                conn.execute(
                    text("""
                        INSERT INTO business.withdrawal_requests
                        (withdrawal_id, user_id, amount, withdrawal_method,
                         account_name, account_number, bank_name, bank_branch, status)
                        VALUES (:wid, :user_id, :amount, :method,
                                :account_name, :account_number, :bank_name, :bank_branch, 'pending')
                    """),
                    {
                        "wid": withdrawal_id,
                        "user_id": user_id,
                        "amount": amount,
                        "method": withdrawal_method,
                        "account_name": account_name,
                        "account_number": account_number,
                        "bank_name": bank_name,
                        "bank_branch": bank_branch
                    }
                )

                # 4. 冻结对应金额（从可提现转为冻结）
                conn.execute(
                    text("""
                        UPDATE business.distributors
                        SET available_commission = available_commission - :amount,
                            frozen_commission = frozen_commission + :amount,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = :user_id
                    """),
                    {"amount": amount, "user_id": user_id}
                )

                conn.commit()

                return {
                    "success": True,
                    "message": "提现申请已提交，等待审核",
                    "withdrawal_id": withdrawal_id
                }

        except Exception as e:
            return {"success": False, "error": f"创建提现申请失败: {str(e)}"}

    def list_my_withdrawals(self, user_id: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """获取我的提现记录"""
        try:
            engine = _get_engine()
            with engine.connect() as conn:
                # 查询总数
                count_result = conn.execute(
                    text("SELECT COUNT(*) FROM business.withdrawal_requests WHERE user_id = :user_id"),
                    {"user_id": user_id}
                ).fetchone()
                total = count_result[0] if count_result else 0

                # 查询记录
                offset = (page - 1) * page_size
                result = conn.execute(
                    text("""
                        SELECT
                            withdrawal_id,
                            user_id,
                            amount,
                            withdrawal_method,
                            account_name,
                            account_number,
                            bank_name,
                            status,
                            reject_reason,
                            created_at,
                            processed_at
                        FROM business.withdrawal_requests
                        WHERE user_id = :user_id
                        ORDER BY created_at DESC
                        LIMIT :page_size OFFSET :offset
                    """),
                    {"user_id": user_id, "page_size": page_size, "offset": offset}
                )

                withdrawals = []
                for row in result:
                    # 脱敏处理账户号码
                    account_number = row[5]
                    if account_number and len(account_number) > 6:
                        account_number = account_number[:3] + "****" + account_number[-3:]

                    withdrawals.append({
                        "withdrawal_id": row[0],
                        "user_id": row[1],
                        "amount": float(row[2]) if row[2] else 0,
                        "withdrawal_method": row[3],
                        "account_name": row[4],
                        "account_number": account_number,
                        "bank_name": row[6],
                        "status": row[7],
                        "reject_reason": row[8],
                        "created_at": row[9].isoformat() if row[9] else None,
                        "processed_at": row[10].isoformat() if row[10] else None
                    })

                return {
                    "success": True,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "withdrawals": withdrawals
                }

        except Exception as e:
            return {"success": False, "error": f"获取提现记录失败: {str(e)}"}

    def process_order_commission(self, order_id: str, new_user_id: str, order_amount: float) -> Dict[str, Any]:
        """处理订单佣金，创建分销记录"""
        try:
            engine = _get_engine()
            with engine.connect() as conn:
                # 1. 检查配置
                config = conn.execute(
                    text("SELECT config_value FROM business.system_configs WHERE config_key = 'distribution_enabled'")
                ).fetchone()

                if not config or config[0].lower() != "true":
                    return {"success": True, "message": "分销系统未开启，跳过佣金计算"}

                # 2. 获取用户邀请人
                inviter = conn.execute(
                    text("SELECT inviter_id FROM business.users WHERE user_id = :user_id"),
                    {"user_id": new_user_id}
                ).fetchone()

                if not inviter or not inviter[0]:
                    return {"success": True, "message": "用户无邀请人，跳过佣金计算"}

                promoter_id = inviter[0]

                # 3. 检查邀请人是否是分销商
                distributor = conn.execute(
                    text("SELECT user_id FROM business.distributors WHERE user_id = :promoter_id AND status = 'active'"),
                    {"promoter_id": promoter_id}
                ).fetchone()

                if not distributor:
                    return {"success": True, "message": "邀请人不是分销商，跳过佣金计算"}

                # 4. 检查是否已处理过该订单
                existing = conn.execute(
                    text("SELECT record_id FROM business.distribution_records WHERE order_id = :order_id"),
                    {"order_id": order_id}
                ).fetchone()

                if existing:
                    return {"success": True, "message": "订单佣金已处理，跳过"}

                # 5. 计算佣金
                commission_rate = 10.0  # 默认10%
                try:
                    rate_config = conn.execute(
                        text("SELECT config_value FROM business.system_configs WHERE config_key = 'distribution_commission_rate'")
                    ).fetchone()
                    if rate_config:
                        commission_rate = float(rate_config[0])
                except:
                    pass

                commission_amount = order_amount * commission_rate / 100

                # 6. 获取结算天数配置
                settle_days = 7  # 默认7天后可提现
                try:
                    days_config = conn.execute(
                        text("SELECT config_value FROM business.system_configs WHERE config_key = 'distribution_settle_days'")
                    ).fetchone()
                    if days_config:
                        settle_days = int(days_config[0])
                except:
                    pass

                available_time = datetime.now() + timedelta(days=settle_days)
                expire_time = datetime.now() + timedelta(days=90)  # 90天过期

                # 7. 创建分销记录
                record_id = str(uuid.uuid4())

                conn.execute(
                    text("""
                        INSERT INTO business.distribution_records
                        (record_id, promoter_id, new_user_id, order_id,
                         commission_amount, commission_status, commission_type,
                         commission_rate, order_amount, available_time, expire_time)
                        VALUES (:rid, :promoter_id, :new_user_id, :order_id,
                                :amount, 'pending', 'direct', :rate, :order_amount,
                                :available_time, :expire_time)
                    """),
                    {
                        "rid": record_id,
                        "promoter_id": promoter_id,
                        "new_user_id": new_user_id,
                        "order_id": order_id,
                        "amount": commission_amount,
                        "rate": commission_rate / 100,  # 转为小数
                        "order_amount": order_amount,
                        "available_time": available_time,
                        "expire_time": expire_time
                    }
                )

                # 8. 更新分销商统计
                conn.execute(
                    text("""
                        UPDATE business.distributors
                        SET total_order_count = total_order_count + 1,
                            total_commission = total_commission + :amount,
                            frozen_commission = frozen_commission + :amount,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = :promoter_id
                    """),
                    {"amount": commission_amount, "promoter_id": promoter_id}
                )

                conn.commit()

                return {
                    "success": True,
                    "message": f"佣金创建成功，金额 {commission_amount:.2f} 元",
                    "commission_amount": commission_amount,
                    "record_id": record_id
                }

        except Exception as e:
            return {"success": False, "error": f"处理佣金异常: {str(e)}"}

    def list_distributors(self, status: Optional[str] = None, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """获取分销商列表（管理员）"""
        try:
            engine = _get_engine()
            with engine.connect() as conn:
                # 构建查询条件
                conditions = []
                params = {}

                if status:
                    conditions.append("d.status = :status")
                    params["status"] = status

                where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

                # 查询总数
                count_result = conn.execute(
                    text(f"SELECT COUNT(*) FROM business.distributors d {where_clause}"),
                    params
                ).fetchone()
                total = count_result[0] if count_result else 0

                # 查询记录
                offset = (page - 1) * page_size
                result = conn.execute(
                    text(f"""
                        SELECT
                            d.user_id,
                            d.distributor_code,
                            d.parent_id,
                            d.distributor_level,
                            d.status,
                            d.total_children_count,
                            d.total_order_count,
                            d.total_commission,
                            d.available_commission,
                            d.frozen_commission,
                            d.total_withdrawn,
                            d.created_at,
                            u.nickname,
                            u.phone
                        FROM business.distributors d
                        LEFT JOIN business.users u ON d.user_id = u.user_id
                        {where_clause}
                        ORDER BY d.created_at DESC
                        LIMIT :page_size OFFSET :offset
                    """),
                    {**params, "page_size": page_size, "offset": offset}
                )

                distributors = []
                for row in result:
                    distributors.append({
                        "user_id": row[0],
                        "distributor_code": row[1],
                        "parent_id": row[2],
                        "distributor_level": row[3],
                        "status": row[4],
                        "total_children_count": row[5],
                        "total_order_count": row[6],
                        "total_commission": float(row[7]) if row[7] else 0,
                        "available_commission": float(row[8]) if row[8] else 0,
                        "frozen_commission": float(row[9]) if row[9] else 0,
                        "total_withdrawn": float(row[10]) if row[10] else 0,
                        "created_at": row[11].isoformat() if row[11] else None,
                        "nickname": row[12],
                        "phone": row[13]
                    })

                return {
                    "success": True,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "distributors": distributors
                }

        except Exception as e:
            return {"success": False, "error": f"获取分销商列表失败: {str(e)}"}

    def get_distributor_detail(self, user_id: str) -> Dict[str, Any]:
        """获取分销商详情（管理员）"""
        try:
            engine = _get_engine()
            with engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT
                            d.user_id,
                            d.distributor_code,
                            d.parent_id,
                            d.distributor_level,
                            d.status,
                            d.total_children_count,
                            d.total_order_count,
                            d.total_commission,
                            d.available_commission,
                            d.frozen_commission,
                            d.total_withdrawn,
                            d.created_at,
                            u.nickname,
                            u.phone,
                            p.nickname as parent_nickname,
                            p_distributor.distributor_code as parent_code
                        FROM business.distributors d
                        LEFT JOIN business.users u ON d.user_id = u.user_id
                        LEFT JOIN business.distributors p_distributor ON d.parent_id = p_distributor.user_id
                        LEFT JOIN business.users p ON p_distributor.user_id = p.user_id
                        WHERE d.user_id = :user_id
                    """),
                    {"user_id": user_id}
                ).fetchone()

                if not result:
                    return {"success": False, "error": "分销商不存在"}

                return {
                    "success": True,
                    "distributor": {
                        "user_id": result[0],
                        "distributor_code": result[1],
                        "parent_id": result[2],
                        "distributor_level": result[3],
                        "status": result[4],
                        "total_children_count": result[5],
                        "total_order_count": result[6],
                        "total_commission": float(result[7]) if result[7] else 0,
                        "available_commission": float(result[8]) if result[8] else 0,
                        "frozen_commission": float(result[9]) if result[9] else 0,
                        "total_withdrawn": float(result[10]) if result[10] else 0,
                        "created_at": result[11].isoformat() if result[11] else None,
                        "nickname": result[12],
                        "phone": result[13],
                        "parent_info": {
                            "nickname": result[14],
                            "distributor_code": result[15]
                        } if result[14] else None
                    }
                }

        except Exception as e:
            return {"success": False, "error": f"获取分销商详情失败: {str(e)}"}

    def update_distributor_status(self, user_id: str, status: str, admin_id: str) -> Dict[str, Any]:
        """更新分销商状态（管理员）"""
        try:
            # 验证状态值
            valid_statuses = ['active', 'frozen', 'inactive']
            if status not in valid_statuses:
                return {"success": False, "error": f"无效的状态值，必须是: {', '.join(valid_statuses)}"}

            engine = _get_engine()
            with engine.connect() as conn:
                # 检查分销商是否存在
                distributor = conn.execute(
                    text("SELECT user_id, status FROM business.distributors WHERE user_id = :user_id"),
                    {"user_id": user_id}
                ).fetchone()

                if not distributor:
                    return {"success": False, "error": "分销商不存在"}

                old_status = distributor[1]

                # 更新状态
                conn.execute(
                    text("""
                        UPDATE business.distributors
                        SET status = :status, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = :user_id
                    """),
                    {"status": status, "user_id": user_id}
                )
                conn.commit()

                return {
                    "success": True,
                    "message": f"分销商状态已从 {old_status} 更新为 {status}"
                }

        except Exception as e:
            return {"success": False, "error": f"更新分销商状态失败: {str(e)}"}

    def list_withdrawals(self, status: Optional[str] = None, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """获取提现申请列表（管理员）"""
        try:
            engine = _get_engine()
            with engine.connect() as conn:
                # 构建查询条件
                conditions = []
                params = {}

                if status:
                    conditions.append("wr.status = :status")
                    params["status"] = status

                where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

                # 查询总数
                count_result = conn.execute(
                    text(f"SELECT COUNT(*) FROM business.withdrawal_requests wr {where_clause}"),
                    params
                ).fetchone()
                total = count_result[0] if count_result else 0

                # 查询记录
                offset = (page - 1) * page_size
                result = conn.execute(
                    text(f"""
                        SELECT
                            wr.withdrawal_id,
                            wr.user_id,
                            wr.amount,
                            wr.withdrawal_method,
                            wr.account_name,
                            wr.account_number,
                            wr.bank_name,
                            wr.bank_branch,
                            wr.status,
                            wr.reject_reason,
                            wr.processed_by,
                            wr.processed_at,
                            wr.transaction_id,
                            wr.created_at,
                            u.nickname,
                            u.phone
                        FROM business.withdrawal_requests wr
                        LEFT JOIN business.users u ON wr.user_id = u.user_id
                        {where_clause}
                        ORDER BY wr.created_at DESC
                        LIMIT :page_size OFFSET :offset
                    """),
                    {**params, "page_size": page_size, "offset": offset}
                )

                withdrawals = []
                for row in result:
                    # 脱敏处理账户号码
                    account_number = row[5]
                    if account_number and len(account_number) > 6:
                        account_number = account_number[:3] + "****" + account_number[-3:]

                    withdrawals.append({
                        "withdrawal_id": row[0],
                        "user_id": row[1],
                        "amount": float(row[2]) if row[2] else 0,
                        "withdrawal_method": row[3],
                        "account_name": row[4],
                        "account_number": account_number,
                        "bank_name": row[6],
                        "bank_branch": row[7],
                        "status": row[8],
                        "reject_reason": row[9],
                        "processed_by": row[10],
                        "processed_at": row[11].isoformat() if row[11] else None,
                        "transaction_id": row[12],
                        "created_at": row[13].isoformat() if row[13] else None,
                        "user_nickname": row[14],
                        "user_phone": row[15]
                    })

                return {
                    "success": True,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "withdrawals": withdrawals
                }

        except Exception as e:
            return {"success": False, "error": f"获取提现列表失败: {str(e)}"}

    def get_withdrawal_detail(self, withdrawal_id: str) -> Dict[str, Any]:
        """获取提现申请详情（管理员）"""
        try:
            engine = _get_engine()
            with engine.connect() as conn:
                # 查询提现申请详情
                result = conn.execute(
                    text("""
                        SELECT
                            wr.withdrawal_id,
                            wr.user_id,
                            u.nickname as user_nickname,
                            u.phone as user_phone,
                            wr.amount,
                            wr.withdrawal_method,
                            wr.account_name,
                            wr.account_number,
                            wr.bank_name,
                            wr.bank_branch,
                            wr.status,
                            wr.reject_reason,
                            wr.processed_by,
                            wr.processed_at,
                            wr.transaction_id,
                            wr.created_at,
                            COALESCE(d.total_commission, 0) as total_commission,
                            COALESCE(d.available_commission, 0) as available_balance,
                            COALESCE(d.frozen_commission, 0) as frozen_amount,
                            COALESCE(d.total_withdrawn, 0) as withdrawn_amount
                        FROM business.withdrawal_requests wr
                        LEFT JOIN business.users u ON wr.user_id = u.user_id
                        LEFT JOIN business.distributors d ON wr.user_id = d.user_id
                        WHERE wr.withdrawal_id = :wid
                    """),
                    {"wid": withdrawal_id}
                ).fetchone()

                if not result:
                    return {"success": False, "error": "提现申请不存在"}

                return {
                    "success": True,
                    "withdrawal": {
                        "id": result[0],
                        "distributor_id": result[1],
                        "distributor_name": result[2],
                        "distributor_phone": result[3],
                        "amount": float(result[4]),
                        "account_type": result[5],
                        "account_holder": result[6],
                        "account_number": result[7],
                        "bank_name": result[8],
                        "bank_branch": result[9],
                        "status": result[10],
                        "reject_reason": result[11],
                        "processed_by": result[12],
                        "processed_at": result[13].isoformat() if result[13] else None,
                        "transaction_id": result[14],
                        "created_at": result[15].isoformat() if result[15] else None,
                        "total_commission": float(result[16]),
                        "available_balance": float(result[17]),
                        "frozen_amount": float(result[18]),
                        "withdrawn_amount": float(result[19])
                    }
                }

        except Exception as e:
            return {"success": False, "error": f"获取提现详情失败: {str(e)}"}

    def approve_withdrawal(self, withdrawal_id: str, processed_by: str, transaction_id: Optional[str] = None) -> Dict[str, Any]:
        """审核通过提现申请（管理员）"""
        try:
            engine = _get_engine()
            with engine.connect() as conn:
                # 1. 查询提现申请
                withdrawal = conn.execute(
                    text("""
                        SELECT withdrawal_id, user_id, amount, status
                        FROM business.withdrawal_requests
                        WHERE withdrawal_id = :wid
                    """),
                    {"wid": withdrawal_id}
                ).fetchone()

                if not withdrawal:
                    return {"success": False, "error": "提现申请不存在"}

                if withdrawal[3] != 'pending':
                    return {"success": False, "error": "该提现申请已处理"}

                user_id = withdrawal[1]
                amount = withdrawal[2]

                # 2. 检查冻结余额是否足够（防止数据不一致导致负数）
                distributor = conn.execute(
                    text("""
                        SELECT frozen_commission FROM business.distributors
                        WHERE user_id = :user_id
                    """),
                    {"user_id": user_id}
                ).fetchone()

                if not distributor:
                    return {"success": False, "error": "分销商不存在"}

                current_frozen = float(distributor[0]) if distributor[0] else 0
                if current_frozen < amount:
                    return {
                        "success": False,
                        "error": f"冻结余额不足，当前冻结金额 {current_frozen:.2f} 元，需要扣减 {amount:.2f} 元"
                    }

                # 3. 更新提现申请状态
                conn.execute(
                    text("""
                        UPDATE business.withdrawal_requests
                        SET status = 'completed',
                            processed_by = :processed_by,
                            processed_at = CURRENT_TIMESTAMP,
                            transaction_id = :transaction_id,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE withdrawal_id = :wid
                    """),
                    {
                        "wid": withdrawal_id,
                        "processed_by": processed_by,
                        "transaction_id": transaction_id
                    }
                )

                # 4. 更新分销商账户：从冻结转为已提现（带余额校验）
                result = conn.execute(
                    text("""
                        UPDATE business.distributors
                        SET frozen_commission = frozen_commission - :amount,
                            total_withdrawn = total_withdrawn + :amount,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = :user_id
                          AND frozen_commission >= :amount
                    """),
                    {"amount": amount, "user_id": user_id}
                )

                if result.rowcount == 0:
                    conn.rollback()
                    return {"success": False, "error": "更新失败：冻结余额不足或数据已被修改"}

                conn.commit()

                return {
                    "success": True,
                    "message": "提现已完成"
                }

        except Exception as e:
            return {"success": False, "error": f"审核通过失败: {str(e)}"}

    def reject_withdrawal(self, withdrawal_id: str, processed_by: str, reject_reason: str) -> Dict[str, Any]:
        """拒绝提现申请（管理员）"""
        try:
            engine = _get_engine()
            with engine.connect() as conn:
                # 1. 查询提现申请
                withdrawal = conn.execute(
                    text("""
                        SELECT withdrawal_id, user_id, amount, status
                        FROM business.withdrawal_requests
                        WHERE withdrawal_id = :wid
                    """),
                    {"wid": withdrawal_id}
                ).fetchone()

                if not withdrawal:
                    return {"success": False, "error": "提现申请不存在"}

                if withdrawal[3] != 'pending':
                    return {"success": False, "error": "该提现申请已处理"}

                user_id = withdrawal[1]
                amount = withdrawal[2]

                # 2. 检查冻结余额是否足够（防止数据不一致导致负数）
                distributor = conn.execute(
                    text("""
                        SELECT frozen_commission FROM business.distributors
                        WHERE user_id = :user_id
                    """),
                    {"user_id": user_id}
                ).fetchone()

                if not distributor:
                    return {"success": False, "error": "分销商不存在"}

                current_frozen = float(distributor[0]) if distributor[0] else 0
                if current_frozen < amount:
                    return {
                        "success": False,
                        "error": f"冻结余额不足，当前冻结金额 {current_frozen:.2f} 元，需要退回 {amount:.2f} 元。请联系管理员检查数据一致性"
                    }

                # 3. 更新提现申请状态
                conn.execute(
                    text("""
                        UPDATE business.withdrawal_requests
                        SET status = 'rejected',
                            reject_reason = :reason,
                            processed_by = :processed_by,
                            processed_at = CURRENT_TIMESTAMP,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE withdrawal_id = :wid
                    """),
                    {
                        "wid": withdrawal_id,
                        "reason": reject_reason,
                        "processed_by": processed_by
                    }
                )

                # 4. 退回冻结金额到可提现（带余额校验）
                result = conn.execute(
                    text("""
                        UPDATE business.distributors
                        SET frozen_commission = frozen_commission - :amount,
                            available_commission = available_commission + :amount,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = :user_id
                          AND frozen_commission >= :amount
                    """),
                    {"amount": amount, "user_id": user_id}
                )

                if result.rowcount == 0:
                    conn.rollback()
                    return {"success": False, "error": "更新失败：冻结余额不足或数据已被修改"}

                conn.commit()

                return {
                    "success": True,
                    "message": "提现已拒绝，金额已退回"
                }

        except Exception as e:
            return {"success": False, "error": f"拒绝失败: {str(e)}"}


    def list_all_distributors(
        self,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """获取所有分销商列表（管理员视角）- list_distributors 的别名
        与 list_distributors 功能相同，保持 API 命名一致性
        """
        return self.list_distributors(status=status, page=page, page_size=page_size)


    def settle_pending_commissions(self) -> Dict[str, Any]:
        """结算待处理佣金（定时任务）"""
        try:
            engine = _get_engine()
            with engine.connect() as conn:
                # 1. 查询所有可结算的佣金记录
                # 条件：状态为 pending，且已过可提现时间
                now = datetime.now()

                pending_records = conn.execute(
                    text("""
                        SELECT record_id, promoter_id, commission_amount
                        FROM business.distribution_records
                        WHERE commission_status = 'pending'
                          AND available_time IS NOT NULL
                          AND available_time <= :now
                    """),
                    {"now": now}
                ).fetchall()

                if not pending_records:
                    return {
                        "success": True,
                        "message": "没有需要结算的佣金",
                        "updated_count": 0
                    }

                updated_count = 0
                affected_promoters = set()

                for record in pending_records:
                    record_id = record[0]
                    promoter_id = record[1]
                    amount = float(record[2])

                    # 2. 先检查分销商的冻结余额是否足够（防止数据不一致）
                    distributor = conn.execute(
                        text("""
                            SELECT frozen_commission FROM business.distributors
                            WHERE user_id = :promoter_id
                        """),
                        {"promoter_id": promoter_id}
                    ).fetchone()

                    if not distributor:
                        print(f"[警告] 佣金结算失败：分销商不存在 {promoter_id}")
                        continue

                    current_frozen = float(distributor[0]) if distributor[0] else 0
                    if current_frozen < amount:
                        print(f"[警告] 佣金结算失败：分销商 {promoter_id} 冻结余额不足 (当前: {current_frozen:.2f}, 需要: {amount:.2f})")
                        continue

                    # 3. 更新佣金记录状态
                    conn.execute(
                        text("""
                            UPDATE business.distribution_records
                            SET commission_status = 'available',
                                settled_time = CURRENT_TIMESTAMP
                            WHERE record_id = :rid
                        """),
                        {"rid": record_id}
                    )

                    # 4. 更新分销商账户：从冻结转为可提现（带余额校验）
                    result = conn.execute(
                        text("""
                            UPDATE business.distributors
                            SET frozen_commission = frozen_commission - :amount,
                                available_commission = available_commission + :amount,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE user_id = :promoter_id
                              AND frozen_commission >= :amount
                        """),
                        {"amount": amount, "promoter_id": promoter_id}
                    )

                    if result.rowcount == 0:
                        print(f"[警告] 佣金结算失败：分销商 {promoter_id} 更新失败，余额不足或数据已被修改")
                        conn.rollback()
                        continue

                    affected_promoters.add(promoter_id)
                    updated_count += 1

                conn.commit()

                return {
                    "success": True,
                    "message": f"成功结算 {updated_count} 条佣金记录",
                    "updated_count": updated_count
                }

        except Exception as e:
            return {"success": False, "error": f"结算佣金失败: {str(e)}", "updated_count": 0}

    def upgrade_distributor_levels(self) -> Dict[str, Any]:
        """
        升级分销商等级（独立定时任务）

        扫描所有分销商的业绩，根据累计订单数和累计佣金自动升级等级

        等级规则：
        - Lv.1: 新分销商默认
        - Lv.2: 累计订单 ≥ 10 或 累计佣金 ≥ 500元
        - Lv.3: 累计订单 ≥ 50 或 累计佣金 ≥ 2000元
        - Lv.4: 累计订单 ≥ 200 或 累计佣金 ≥ 10000元
        - Lv.5: 累计订单 ≥ 500 或 累计佣金 ≥ 50000元

        Returns:
            包含升级数量的字典
        """
        try:
            engine = _get_engine()
            with engine.connect() as conn:
                # 获取所有分销商
                distributors = conn.execute(
                    text("""
                        SELECT user_id, distributor_level, total_order_count, total_commission
                        FROM business.distributors
                        WHERE status = 'active'
                    """)
                ).fetchall()

                upgraded_count = 0
                upgrade_details = []

                for dist in distributors:
                    user_id = dist[0]
                    current_level = dist[1]
                    total_orders = dist[2]
                    total_commission = float(dist[3]) if dist[3] else 0

                    # 计算应该达到的等级
                    new_level = self._calculate_level(total_orders, total_commission)

                    # 如果等级提升，更新
                    if new_level > current_level:
                        conn.execute(
                            text("""
                                UPDATE business.distributors
                                SET distributor_level = :new_level,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE user_id = :user_id
                            """),
                            {"new_level": new_level, "user_id": user_id}
                        )
                        upgraded_count += 1
                        upgrade_details.append({
                            "user_id": user_id,
                            "old_level": current_level,
                            "new_level": new_level,
                            "total_orders": total_orders,
                            "total_commission": total_commission
                        })
                        print(f"[等级升级] {user_id}: Lv.{current_level} → Lv.{new_level} (订单:{total_orders}, 佣金:{total_commission})")

                conn.commit()

                return {
                    "success": True,
                    "upgraded_count": upgraded_count,
                    "upgrade_details": upgrade_details,
                    "message": f"成功升级 {upgraded_count} 个分销商等级"
                }

        except Exception as e:
            return {"success": False, "error": f"升级等级失败: {str(e)}", "upgraded_count": 0}

    def _calculate_level(self, total_orders: int, total_commission: float) -> int:
        """
        根据业绩计算等级

        Args:
            total_orders: 累计订单数
            total_commission: 累计佣金

        Returns:
            应达到的等级（1-5）
        """
        # 满足任一条件即可升级到对应等级（订单数 OR 佣金金额）
        if total_orders >= 500 or total_commission >= 50000:
            return 5
        elif total_orders >= 200 or total_commission >= 10000:
            return 4
        elif total_orders >= 50 or total_commission >= 2000:
            return 3
        elif total_orders >= 10 or total_commission >= 500:
            return 2
        else:
            return 1


# 创建全局实例
distribution_service = DistributionService()
