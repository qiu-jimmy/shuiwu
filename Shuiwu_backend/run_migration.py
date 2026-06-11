"""
运行数据库迁移脚本
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

# 获取命令行参数
migration_file = sys.argv[1] if len(sys.argv) > 1 else "007_create_panoramic_report_system.sql"

# 读取 SQL 文件
sql_file = Path(__file__).parent / "app" / "infra" / "sql" / "migrations" / migration_file
if not sql_file.exists():
    print(f"[ERROR] Migration file not found: {sql_file}")
    sys.exit(1)

with open(sql_file, "r", encoding="utf-8") as f:
    sql_content = f.read()

# 获取数据库配置
db_host = os.getenv("PG_HOST", "localhost")
db_port = os.getenv("PG_PORT", "5432")
db_user = os.getenv("PG_USER", "postgres")
db_password = os.getenv("PG_PASSWORD")
db_database = os.getenv("PG_DATABASE", "agentdemostudio")

# 创建数据库连接
connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_database}"
engine = create_engine(connection_string)

try:
    with engine.connect() as conn:
        # 执行 SQL
        conn.execute(text(sql_content))
        conn.commit()
        print(f"[SUCCESS] Database migration completed: {migration_file}")
except Exception as e:
    print(f"[ERROR] Database migration failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
