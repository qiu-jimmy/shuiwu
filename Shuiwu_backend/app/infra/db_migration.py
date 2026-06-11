"""
数据库迁移脚本
用于初始化和升级业务数据库Schema
"""
import os
import sys
import time
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from sqlalchemy import text
from app.infra.db import get_sync_engine


class DatabaseMigration:
    """数据库迁移管理类"""

    def __init__(self, db_schema: str = "business"):
        self.db_schema = db_schema
        self.migration_table = f"{db_schema}._schema_migrations"

    def ensure_migration_table(self):
        """确保迁移记录表存在"""
        engine = get_sync_engine()
        with engine.connect() as conn:
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {self.db_schema}"))
            conn.commit()

            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {self.migration_table} (
                    id SERIAL PRIMARY KEY,
                    version VARCHAR(50) UNIQUE NOT NULL,
                    description TEXT,
                    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            print(f"✓ 迁移记录表已创建: {self.migration_table}")

    def get_executed_migrations(self) -> list:
        """获取已执行的迁移版本"""
        engine = get_sync_engine()
        with engine.connect() as conn:
            try:
                result = conn.execute(text(
                    f"SELECT version FROM {self.migration_table} ORDER BY executed_at"
                ))
                return [row[0] for row in result]
            except:
                return []

    def execute_migration(self, version: str, description: str, sql_content: str):
        """执行单个迁移"""
        engine = get_sync_engine()
        with engine.connect() as conn:
            try:
                # 开始事务
                conn.execute(text("BEGIN"))

                # 分割并执行SQL语句
                statements = self._split_sql_statements(sql_content)
                executed_count = 0

                for statement in statements:
                    if statement.strip():
                        try:
                            conn.execute(text(statement))
                            executed_count += 1
                        except Exception as e:
                            error_msg = str(e).lower()
                            # 忽略已存在的对象
                            if "already exists" not in error_msg and "duplicate" not in error_msg:
                                print(f"  ✗ 执行失败: {e}")
                                print(f"  SQL: {statement[:100]}...")
                                raise

                # 记录迁移
                conn.execute(text(f"""
                    INSERT INTO {self.migration_table} (version, description)
                    VALUES (:version, :description)
                """), {"version": version, "description": description})

                # 提交事务
                conn.execute(text("COMMIT"))
                conn.commit()

                print(f"✓ 迁移 {version} 执行成功，共执行 {executed_count} 条SQL语句")
                return True

            except Exception as e:
                # 回滚事务
                conn.execute(text("ROLLBACK"))
                conn.commit()
                print(f"✗ 迁移 {version} 执行失败: {e}")
                return False

    def _split_sql_statements(self, sql_content: str) -> list:
        """分割SQL语句"""
        statements = []
        current_statement = []

        for line in sql_content.split("\n"):
            # 跳过注释行
            if line.strip().startswith("--"):
                continue

            # 跳过空行
            if not line.strip():
                continue

            current_statement.append(line)

            # 检查是否是语句结束
            if line.strip().endswith(";"):
                statement = "\n".join(current_statement)
                statements.append(statement)
                current_statement = []

        # 处理最后一个没有分号的语句
        if current_statement:
            statements.append("\n".join(current_statement))

        return statements

    def run_migrations(self, sql_file_path: str):
        """运行所有迁移"""
        print("=" * 60)
        print("开始数据库迁移")
        print("=" * 60)

        start_time = time.time()

        # 1. 确保迁移表存在
        self.ensure_migration_table()

        # 2. 获取已执行的迁移
        executed = self.get_executed_migrations()
        print(f"\n已执行的迁移: {len(executed)} 个")
        if executed:
            for v in executed:
                print(f"  - {v}")

        # 3. 读取SQL文件
        if not os.path.exists(sql_file_path):
            print(f"\n✗ SQL文件不存在: {sql_file_path}")
            return False

        with open(sql_file_path, "r", encoding="utf-8") as f:
            sql_content = f.read()

        # 4. 执行迁移（使用文件名作为版本）
        filename = os.path.basename(sql_file_path)
        version = filename.replace(".sql", "")
        description = f"初始化业务数据库Schema"

        if version in executed:
            print(f"\n⊘ 迁移 {version} 已执行，跳过")
            return True

        print(f"\n执行迁移: {version}")
        print(f"描述: {description}")

        success = self.execute_migration(version, description, sql_content)

        # 5. 显示结果
        elapsed = time.time() - start_time
        print("\n" + "=" * 60)
        if success:
            print(f"✓ 数据库迁移完成！耗时: {elapsed:.2f}秒")
        else:
            print(f"✗ 数据库迁移失败！耗时: {elapsed:.2f}秒")
        print("=" * 60)

        return success

    def rollback_migration(self, version: str):
        """回滚迁移（删除迁移记录，需要手动清理数据库对象）"""
        engine = get_sync_engine()
        with engine.connect() as conn:
            result = conn.execute(text(f"""
                DELETE FROM {self.migration_table}
                WHERE version = :version
                RETURNING description
            """), {"version": version})

            if result.rowcount > 0:
                conn.commit()
                row = result.fetchone()
                print(f"✓ 迁移 {version} 已从记录中删除")
                print(f"  描述: {row[0]}")
                print(f"  注意: 请手动清理相关的数据库对象")
                return True
            else:
                print(f"✗ 未找到迁移 {version}")
                return False

    def status(self):
        """显示迁移状态"""
        print("=" * 60)
        print("数据库迁移状态")
        print("=" * 60)

        executed = self.get_executed_migrations()
        print(f"\n已执行的迁移: {len(executed)} 个")

        if executed:
            engine = get_sync_engine()
            with engine.connect() as conn:
                result = conn.execute(text(f"""
                    SELECT version, description, executed_at
                    FROM {self.migration_table}
                    ORDER BY executed_at DESC
                """))

                for row in result:
                    print(f"\n  版本: {row[0]}")
                    print(f"  描述: {row[1]}")
                    print(f"  执行时间: {row[2]}")
        else:
            print("  （无）")

        print("\n" + "=" * 60)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="数据库迁移工具")
    parser.add_argument("action", choices=["migrate", "rollback", "status"],
                       help="操作: migrate=执行迁移, rollback=回滚迁移, status=查看状态")
    parser.add_argument("--version", help="迁移版本（用于rollback）")
    parser.add_argument("--sql-file", help="SQL文件路径（用于migrate）")

    args = parser.parse_args()

    migration = DatabaseMigration()

    if args.action == "migrate":
        sql_file = args.sql_file or os.path.join(
            os.path.dirname(__file__), "sql", "business_schema.sql"
        )
        migration.run_migrations(sql_file)

    elif args.action == "rollback":
        if not args.version:
            print("✗ 回滚操作需要指定 --version 参数")
            sys.exit(1)
        migration.rollback_migration(args.version)

    elif args.action == "status":
        migration.status()


if __name__ == "__main__":
    main()
