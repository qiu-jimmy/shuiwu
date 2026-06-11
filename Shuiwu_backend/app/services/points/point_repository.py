"""
积分数据访问层
处理积分记录的数据库操作
"""
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.infra.db import get_sync_engine
from sqlalchemy import text


class PointRepository:
    """积分数据访问类"""

    def __init__(self):
        pass

    def add_point_record(
        self,
        user_id: str,
        points: int,
        change_type: str,
        change_reason: str,
        related_order_id: Optional[str] = None,
        related_user_id: Optional[str] = None
    ) -> Optional[str]:
        """
        添加积分记录（双表操作，使用事务）

        Args:
            user_id: 用户ID
            points: 积分数量（正数）
            change_type: 变化类型
            change_reason: 变化原因
            related_order_id: 关联订单ID
            related_user_id: 关联用户ID

        Returns:
            记录ID，失败返回None
        """
        record_id = f"point_{uuid.uuid4().hex[:16]}"

        try:
            engine = get_sync_engine()
            with engine.begin() as conn:  # 使用事务
                # 1. 查询或创建用户积分记录
                user_points = conn.execute(
                    text("""
                        SELECT user_id, points_balance, total_points_earned
                        FROM business.user_points
                        WHERE user_id = :user_id
                        FOR UPDATE
                    """),
                    {"user_id": user_id}
                ).fetchone()

                if user_points:
                    # 更新现有记录
                    old_balance = user_points[1]
                    old_total_earned = user_points[2]
                    new_balance = old_balance + points
                    new_total_earned = old_total_earned + points

                    conn.execute(
                        text("""
                            UPDATE business.user_points
                            SET points_balance = :points_balance,
                                total_points_earned = :total_points_earned,
                                updated_at = :updated_at
                            WHERE user_id = :user_id
                        """),
                        {
                            "points_balance": new_balance,
                            "total_points_earned": new_total_earned,
                            "updated_at": datetime.now(),
                            "user_id": user_id
                        }
                    )
                else:
                    # 创建新记录
                    new_balance = points
                    new_total_earned = points

                    conn.execute(
                        text("""
                            INSERT INTO business.user_points (
                                user_id, points_balance, total_points_earned, updated_at
                            ) VALUES (
                                :user_id, :points_balance, :total_points_earned, :updated_at
                            )
                        """),
                        {
                            "user_id": user_id,
                            "points_balance": new_balance,
                            "total_points_earned": new_total_earned,
                            "updated_at": datetime.now()
                        }
                    )

                # 2. 插入积分变动记录（包含变动后余额）
                conn.execute(
                    text("""
                        INSERT INTO business.point_records (
                            record_id, user_id, points, change_type, change_reason,
                            related_order_id, related_user_id, balance_after, created_at
                        ) VALUES (
                            :record_id, :user_id, :points, :change_type, :change_reason,
                            :related_order_id, :related_user_id, :balance_after, :created_at
                        )
                    """),
                    {
                        "record_id": record_id,
                        "user_id": user_id,
                        "points": points,
                        "change_type": change_type,
                        "change_reason": change_reason,
                        "related_order_id": related_order_id,
                        "related_user_id": related_user_id,
                        "balance_after": new_balance,
                        "created_at": datetime.now()
                    }
                )

                return record_id

        except Exception as e:
            print(f"添加积分记录失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_user_points_balance(self, user_id: str) -> int:
        """
        获取用户积分余额（从余额表直接读取）

        Args:
            user_id: 用户ID

        Returns:
            积分余额
        """
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT COALESCE(points_balance, 0)
                        FROM business.user_points
                        WHERE user_id = :user_id
                    """),
                    {"user_id": user_id}
                ).fetchone()
                return result[0] if result else 0
        except Exception as e:
            print(f"获取用户积分余额失败: {e}")
            return 0

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
            积分记录列表及总数
        """
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                # 查询总数
                count_result = conn.execute(
                    text("""
                        SELECT COUNT(*)
                        FROM business.point_records
                        WHERE user_id = :user_id
                    """),
                    {"user_id": user_id}
                ).fetchone()
                total = count_result[0] if count_result else 0

                # 查询记录
                offset = (page - 1) * page_size
                records_result = conn.execute(
                    text("""
                        SELECT
                            record_id,
                            points,
                            change_type,
                            change_reason,
                            related_order_id,
                            related_user_id,
                            balance_after,
                            created_at
                        FROM business.point_records
                        WHERE user_id = :user_id
                        ORDER BY created_at DESC
                        LIMIT :limit OFFSET :offset
                    """),
                    {
                        "user_id": user_id,
                        "limit": page_size,
                        "offset": offset
                    }
                ).fetchall()

                records = []
                for row in records_result:
                    records.append({
                        "record_id": row[0],
                        "points": row[1],
                        "change_type": row[2],
                        "change_reason": row[3],
                        "related_order_id": row[4],
                        "related_user_id": row[5],
                        "balance_after": row[6],
                        "created_at": row[7]
                    })

                return {
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "records": records
                }
        except Exception as e:
            print(f"查询积分记录失败: {e}")
            return {
                "total": 0,
                "page": page,
                "page_size": page_size,
                "records": []
            }

    def get_point_record_with_details(self, record_id: str) -> Optional[Dict[str, Any]]:
        """
        获取积分记录详情（包含关联信息）

        Args:
            record_id: 记录ID

        Returns:
            积分记录详情
        """
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT
                            pr.record_id,
                            pr.user_id,
                            pr.points,
                            pr.change_type,
                            pr.change_reason,
                            pr.related_order_id,
                            pr.related_user_id,
                            pr.balance_after,
                            u.nickname as related_user_nickname,
                            o.actual_amount as order_amount,
                            pr.created_at
                        FROM business.point_records pr
                        LEFT JOIN business.users u ON pr.related_user_id = u.user_id
                        LEFT JOIN business.orders o ON pr.related_order_id = o.order_id
                        WHERE pr.record_id = :record_id
                    """),
                    {"record_id": record_id}
                ).fetchone()

                if result:
                    return {
                        "record_id": result[0],
                        "user_id": result[1],
                        "points": result[2],
                        "change_type": result[3],
                        "change_reason": result[4],
                        "related_order_id": result[5],
                        "related_user_id": result[6],
                        "balance_after": result[7],
                        "related_user_nickname": result[8],
                        "order_amount": float(result[9]) if result[9] else None,
                        "created_at": result[10]
                    }
                return None
        except Exception as e:
            print(f"获取积分记录详情失败: {e}")
            return None

    def get_points_statistics(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        获取积分统计数据（从余额表和流水表统计）

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            统计数据
        """
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                # 有积分的用户数（从余额表统计）
                users_result = conn.execute(
                    text("""
                        SELECT COUNT(*)
                        FROM business.user_points
                        WHERE points_balance > 0
                    """)
                ).fetchone()
                total_users_with_points = users_result[0] if users_result else 0

                # 累计发放积分（从余额表统计）
                total_result = conn.execute(
                    text("""
                        SELECT COALESCE(SUM(total_points_earned), 0)
                        FROM business.user_points
                    """)
                ).fetchone()
                total_points_issued = total_result[0] if total_result else 0

                # 按类型统计（从流水表统计）
                type_result = conn.execute(
                    text("""
                        SELECT change_type, SUM(points) as total_points
                        FROM business.point_records
                        GROUP BY change_type
                    """)
                ).fetchall()

                points_by_type = {}
                for row in type_result:
                    points_by_type[row[0]] = row[1]

                return {
                    "total_users_with_points": total_users_with_points,
                    "total_points_issued": total_points_issued,
                    "points_by_type": points_by_type
                }
        except Exception as e:
            print(f"获取积分统计失败: {e}")
            return {
                "total_users_with_points": 0,
                "total_points_issued": 0,
                "points_by_type": {}
            }

    def is_first_order(self, user_id: str) -> bool:
        """
        判断是否是用户的第一个支付订单

        Args:
            user_id: 用户ID

        Returns:
            是否是首次支付
        """
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT COUNT(*)
                        FROM business.orders
                        WHERE user_id = :user_id
                        AND payment_status = 'paid'
                    """),
                    {"user_id": user_id}
                ).fetchone()
                return result[0] == 1 if result else True
        except Exception as e:
            print(f"判断首次订单失败: {e}")
            return False


# 全局积分仓库实例
point_repository = PointRepository()
