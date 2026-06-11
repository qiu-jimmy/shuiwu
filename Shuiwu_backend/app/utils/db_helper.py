"""
数据库连接辅助工具
提供简化的数据库连接方式
"""
from sqlalchemy import text
from app.infra.db import get_sync_engine


def execute_query(sql: str, params: dict = None) -> list:
    """执行查询并返回结果列表"""
    engine = get_sync_engine()
    with engine.connect() as conn:
        if params:
            result = conn.execute(text(sql), params)
        else:
            result = conn.execute(text(sql))
        return result.fetchall()


def execute_query_one(sql: str, params: dict = None):
    """执行查询并返回单条结果"""
    engine = get_sync_engine()
    with engine.connect() as conn:
        if params:
            result = conn.execute(text(sql), params)
        else:
            result = conn.execute(text(sql))
        return result.fetchone()


def execute_update(sql: str, params: dict = None) -> bool:
    """执行更新/插入/删除操作"""
    engine = get_sync_engine()
    with engine.connect() as conn:
        if params:
            conn.execute(text(sql), params)
        else:
            conn.execute(text(sql))
        conn.commit()
        return True
