# -*- coding: utf-8 -*-
"""
数据库迁移工具

功能特性:
- 自动检测并执行未执行的迁移文件
- 迁移记录跟踪,避免重复执行
- 支持增量迁移
- 迁移失败自动回滚
- 迁移历史记录

使用方法:
    python migrate_db.py              # 执行所有待执行的迁移
    python migrate_db.py --status     # 查看迁移状态
    python migrate_db.py --list       # 列出所有迁移文件
    python migrate_db.py --dry-run    # 试运行,不实际执行
    python migrate_db.py --to 002     # 只执行到版本 002
"""
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from sqlalchemy import Connection, text, create_engine
from dotenv import load_dotenv

# ==================== 加载环境变量 ====================

# 加载 .env 文件
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"[INFO] 已加载环境变量配置文件: {env_path}")
else:
    print(f"[WARN] .env 文件不存在: {env_path}")
    print(f"[WARN] 将使用默认配置或系统环境变量")

# ==================== 配置 ====================

# 数据库配置（从环境变量读取，与app/infra/db.py保持一致）
DB_HOST = os.getenv("PG_HOST", "localhost")
DB_PORT = os.getenv("PG_PORT", "5432")
DB_USER = os.getenv("PG_USER", "postgres")
DB_PASSWORD = os.getenv("PG_PASSWORD", "")
DB_NAME = os.getenv("PG_DATABASE", "Agno")

# 迁移文件目录
MIGRATIONS_DIR = Path(__file__).parent / "app" / "infra" / "sql" / "migrations"

# 迁移记录表名
MIGRATIONS_TABLE = "schema_migrations"

# ==================== 数据库连接 ====================


def get_db_connection() -> Connection:
    """获取数据库连接"""
    conn_str = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    engine = create_engine(conn_str)
    return engine.connect()


def init_migrations_table(conn: Connection) -> None:
    """初始化迁移记录表"""
    conn.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} (
            id SERIAL PRIMARY KEY,
            version VARCHAR(255) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            checksum VARCHAR(255),
            execution_time INTEGER -- 执行时间(毫秒)
        )
    """))
    conn.commit()


# ==================== 迁移文件管理 ====================


def get_migration_files() -> List[Dict[str, str]]:
    """
    获取所有迁移文件,按版本号排序

    Returns:
        迁移文件列表,每个元素包含 {version, name, filepath}
    """
    if not MIGRATIONS_DIR.exists():
        print(f"警告: 迁移目录不存在: {MIGRATIONS_DIR}")
        return []

    migrations = []

    for filepath in MIGRATIONS_DIR.glob("*.sql"):
        # 从文件名提取版本号 (如 001_add_password_hash.sql -> 001)
        match = re.match(r"^(\d+)_", filepath.name)
        if not match:
            print(f"警告: 跳过无效的迁移文件名: {filepath.name}")
            continue

        version = match.group(1)
        name = filepath.stem  # 不带扩展名的文件名

        migrations.append({
            "version": version,
            "name": name,
            "filepath": filepath
        })

    # 按版本号排序
    migrations.sort(key=lambda x: int(x["version"]))
    return migrations


def get_executed_migrations(conn: Connection) -> set:
    """获取已执行的迁移版本号"""
    try:
        result = conn.execute(text(f"SELECT version FROM {MIGRATIONS_TABLE}"))
        return {row[0] for row in result}
    except Exception:
        # 表不存在,返回空集合
        return set()


def get_pending_migrations(conn: Connection) -> List[Dict[str, str]]:
    """获取待执行的迁移"""
    all_migrations = get_migration_files()
    executed_versions = get_executed_migrations(conn)

    pending = [
        m for m in all_migrations
        if m["version"] not in executed_versions
    ]

    return pending


# ==================== 迁移执行 ====================


def read_migration_sql(filepath: Path) -> str:
    """读取迁移 SQL 文件"""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def execute_migration(
    conn: Connection,
    migration: Dict[str, str],
    dry_run: bool = False
) -> bool:
    """
    执行单个迁移

    Args:
        conn: 数据库连接
        migration: 迁移信息字典
        dry_run: 是否为试运行(不实际执行)

    Returns:
        是否执行成功
    """
    version = migration["version"]
    name = migration["name"]
    filepath = migration["filepath"]

    print(f"\n{'='*60}")
    print(f"执行迁移: {version}_{name}")
    print(f"文件: {filepath}")
    print(f"{'='*60}")

    if dry_run:
        print("[试运行模式] 不会实际执行 SQL")
        sql = read_migration_sql(filepath)
        print(f"\nSQL 内容预览:\n{sql[:500]}...")
        return True

    try:
        # 读取 SQL
        sql = read_migration_sql(filepath)

        # 记录开始时间
        start_time = datetime.now()

        # 执行 SQL
        print(f"\n开始执行 SQL...")
        conn.execute(text(sql))
        conn.commit()

        # 计算执行时间
        execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

        # 记录迁移
        conn.execute(text(f"""
            INSERT INTO {MIGRATIONS_TABLE} (version, name, executed_at, execution_time)
            VALUES (:version, :name, CURRENT_TIMESTAMP, :execution_time)
        """), {
            "version": version,
            "name": name,
            "execution_time": execution_time
        })
        conn.commit()

        print(f"\n[OK] 迁移执行成功 (耗时: {execution_time}ms)")
        return True

    except Exception as e:
        print(f"\n[ERROR] 迁移执行失败: {e}")
        conn.rollback()
        return False


def execute_migrations(
    conn: Connection,
    target_version: Optional[str] = None,
    dry_run: bool = False
) -> None:
    """
    执行迁移

    Args:
        conn: 数据库连接
        target_version: 目标版本号(可选),如果指定则只执行到该版本
        dry_run: 是否为试运行
    """
    pending = get_pending_migrations(conn)

    if not pending:
        print("\n没有待执行的迁移。")
        return

    print(f"\n发现 {len(pending)} 个待执行的迁移:")
    for m in pending:
        print(f"  - {m['version']}_{m['name']}")

    # 如果指定了目标版本,只执行到该版本
    if target_version:
        pending = [m for m in pending if int(m["version"]) <= int(target_version)]
        if not pending:
            print(f"\n没有需要执行的迁移(目标版本: {target_version})")
            return

    if not dry_run:
        confirm = input("\n确认执行迁移? (y/n): ").strip().lower()
        if confirm != "y":
            print("取消迁移。")
            return

    # 执行迁移
    success_count = 0
    failed_count = 0

    for migration in pending:
        if execute_migration(conn, migration, dry_run):
            success_count += 1
        else:
            failed_count += 1
            print(f"\n迁移 {migration['version']} 执行失败,停止后续迁移。")
            break

    # 总结
    print(f"\n{'='*60}")
    print(f"迁移完成!")
    print(f"  成功: {success_count}")
    print(f"  失败: {failed_count}")
    print(f"{'='*60}")


# ==================== 状态查询 ====================


def show_status(conn: Connection) -> None:
    """显示迁移状态"""
    all_migrations = get_migration_files()
    executed_versions = get_executed_migrations(conn)

    print(f"\n{'='*60}")
    print("迁移状态")
    print(f"{'='*60}\n")

    print(f"总迁移数: {len(all_migrations)}")
    print(f"已执行: {len(executed_versions)}")
    print(f"待执行: {len(all_migrations) - len(executed_versions)}")

    if all_migrations:
        print("\n迁移列表:")
        for m in all_migrations:
            status = "[OK]" if m["version"] in executed_versions else "[PENDING]"
            print(f"  {status} {m['version']}_{m['name']}")

    print(f"\n{'='*60}")


def show_list() -> None:
    """列出所有迁移文件"""
    migrations = get_migration_files()

    print(f"\n{'='*60}")
    print("迁移文件列表")
    print(f"{'='*60}\n")

    if not migrations:
        print("没有找到迁移文件。")
        return

    for m in migrations:
        print(f"  {m['version']}_{m['name']}")
        print(f"    文件: {m['filepath']}")

    print(f"\n共 {len(migrations)} 个迁移文件")
    print(f"{'='*60}")


# ==================== 命令行接口 ====================


def main():
    """主函数"""
    import argparse

    # 显示数据库配置信息
    print(f"\n{'='*60}")
    print("数据库迁移工具")
    print(f"{'='*60}")
    print(f"\n数据库配置:")
    print(f"  主机: {DB_HOST}")
    print(f"  端口: {DB_PORT}")
    print(f"  用户: {DB_USER}")
    print(f"  数据库: {DB_NAME}")
    print(f"{'='*60}\n")

    parser = argparse.ArgumentParser(
        description="数据库迁移工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s              # 执行所有待执行的迁移
  %(prog)s --status     # 查看迁移状态
  %(prog)s --list       # 列出所有迁移文件
  %(prog)s --dry-run    # 试运行,不实际执行
  %(prog)s --to 002     # 只执行到版本 002
        """
    )

    parser.add_argument(
        "--status", "-s",
        action="store_true",
        help="查看迁移状态"
    )

    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="列出所有迁移文件"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="试运行,不实际执行 SQL"
    )

    parser.add_argument(
        "--to",
        metavar="VERSION",
        help="执行到指定版本号"
    )

    parser.add_argument(
        "--init",
        action="store_true",
        help="初始化迁移表"
    )

    args = parser.parse_args()

    # 设置输出编码
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    try:
        conn = get_db_connection()

        # 初始化迁移表
        init_migrations_table(conn)

        if args.status:
            show_status(conn)
        elif args.list:
            show_list()
        elif args.init:
            print("迁移表初始化完成。")
        else:
            # 执行迁移
            execute_migrations(
                conn,
                target_version=args.to,
                dry_run=args.dry_run
            )

        conn.close()

    except Exception as e:
        print(f"\n错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
