"""
使用 agno PostgresDb 创建 MCP 专用的数据库实例
"""
from agno.db.postgres import PostgresDb

from app.infra.db import get_db_url


def create_mcp_postgres_db(schema: str = "mcp", session_table: str = "mcp_test_session") -> PostgresDb:
    """
    创建 MCP 专用的 PostgresDb 实例（使用 agno 官方方法）
    
    使用 mcp schema 下的指定表
    PostgresDb 使用 db_schema 参数来指定 schema，session_table 只需要表名
    
    Args:
        schema: 数据库schema名称
        session_table: 会话表名（只需要表名，不需要schema前缀）
    
    Returns:
        PostgresDb 实例
    """
    db_url = get_db_url()
    db = PostgresDb(
        db_url=db_url,
        db_schema=schema,  # 明确指定schema为 mcp
        session_table=session_table,  # 只需要表名，不需要schema前缀
    )
    # 表会在首次使用时自动创建，不需要手动调用
    return db

