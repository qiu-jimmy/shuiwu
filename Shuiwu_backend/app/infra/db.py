"""
数据库连接配置和工具函数
统一管理所有数据库连接
"""
import os
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine
from agno.db.postgres import PostgresDb

# 默认连接信息，可通过环境变量覆盖
DB_HOST = os.getenv("PG_HOST", "localhost")
DB_PORT = os.getenv("PG_PORT", "5432")
DB_USER = os.getenv("PG_USER", "postgres")
DB_PASSWORD = os.getenv("PG_PASSWORD", "")
DB_NAME = os.getenv("PG_DATABASE", "Agno")

# 异步数据库URL（用于异步操作）
DATABASE_URL_ASYNC = (
    f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# 同步数据库URL（用于同步操作，如会话管理）
# 使用 psycopg2 而不是 psycopg3，因为 psycopg3 对 SQLAlchemy 命名参数支持有问题
DATABASE_URL_SYNC = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# 异步引擎（用于异步操作）
async_engine = create_async_engine(
    DATABASE_URL_ASYNC,
    echo=False,
    future=True,
    pool_size=5,            # 每个worker保持5个连接 (多进程环境下需考虑总连接数 = worker数 * (pool_size + max_overflow))
    max_overflow=10,        # 高峰期额外10个连接
    pool_pre_ping=True,     # 连接前检查连接是否有效，防止MySQL/PG gone away报错
    pool_recycle=3600,      # 1小时后回收连接，防止数据库端主动断开长时间不活跃的连接
    connect_args={
        "connect_timeout": 10,  # 连接超时10秒
        "command_timeout": 30,  # 命令超时30秒
    }
)
AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)

# 同步引擎（用于会话管理等同步操作）
sync_engine = create_engine(
    DATABASE_URL_SYNC,
    echo=False,
    pool_size=5,            # 每个worker保持5个连接
    max_overflow=10,        # 高峰期额外10个连接
    pool_pre_ping=True,     # 连接前检查连接是否有效
    pool_recycle=3600,      # 1小时后回收连接
    connect_args={
        "connect_timeout": 10,  # 连接超时10秒
    }
)
SyncSessionLocal = sessionmaker(bind=sync_engine, autocommit=False, autoflush=False)

Base = declarative_base()


def get_db_url() -> str:
    """获取同步数据库URL"""
    return DATABASE_URL_SYNC


def get_async_db_url() -> str:
    """获取异步数据库URL"""
    return DATABASE_URL_ASYNC


def get_sync_engine():
    """获取同步数据库引擎"""
    return sync_engine


def get_async_engine():
    """获取异步数据库引擎"""
    return async_engine


def create_postgres_db(session_table: str = "agent_sessions") -> PostgresDb:
    """
    创建 Agno PostgresDb 实例（同步版本）

    Args:
        session_table: 会话表名

    Returns:
        PostgresDb 实例
    """
    db = PostgresDb(
        db_url=get_db_url(),
        session_table=session_table,
    )
    # 确保表已创建
    try:
        db._create_all_tables()
    except Exception as e:
        print(f"创建表时出错（可能已存在）: {e}")
    return db


# 异步 PostgresDb 缓存
_async_postgres_db_cache = {}


def create_async_postgres_db(session_table: str = "agent_sessions"):
    """
    创建 Agno AsyncPostgresDb 实例（异步版本，推荐使用）

    Args:
        session_table: 会话表名

    Returns:
        AsyncPostgresDb 实例
    """
    from agno.db.postgres import AsyncPostgresDb

    # 使用缓存，避免重复创建和检查表
    if session_table not in _async_postgres_db_cache:
        db = AsyncPostgresDb(
            db_url=get_async_db_url(),  # ✅ 使用异步URL（asyncpg而不是psycopg）
            session_table=session_table,
        )
        _async_postgres_db_cache[session_table] = db

    return _async_postgres_db_cache[session_table]



async def get_db():
    """获取异步数据库会话（FastAPI依赖注入）"""
    async with AsyncSessionLocal() as session:
        yield session


def get_sync_db():
    """获取同步数据库会话（FastAPI依赖注入）"""
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()

