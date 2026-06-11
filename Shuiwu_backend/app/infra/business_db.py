"""
业务数据库初始化和连接管理
"""
import os
from app.infra.db import get_sync_engine


class BusinessDatabase:
    """业务数据库管理类"""

    def __init__(self, db_schema: str = "business"):
        self.db_schema = db_schema
        self._initialized = False

    def initialize(self):
        """初始化业务数据库"""
        if self._initialized:
            return

        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                # 先检查 schema 是否已存在(快速检查)
                # 转义 schema_name 中的单引号
                safe_schema = self.db_schema.replace("'", "''")

                # 使用原始 DBAPI 连接执行 SQL
                raw_conn = conn.connection
                cursor = raw_conn.cursor()
                cursor.execute(
                    """
                        SELECT schema_name
                        FROM information_schema.schemata
                        WHERE schema_name = %s
                    """,
                    (safe_schema,)
                )
                result = cursor.fetchone()

                if result:
                    # Schema 已存在,跳过初始化
                    print(f"业务数据库 Schema '{self.db_schema}' 已存在,跳过初始化")
                    self._initialized = True
                    return

                print(f"业务数据库 Schema '{self.db_schema}' 不存在,开始初始化...")

                # 读取SQL文件并执行
                sql_file_path = os.path.join(
                    os.path.dirname(__file__),
                    "sql",
                    "business_schema.sql"
                )

                if os.path.exists(sql_file_path):
                    with open(sql_file_path, "r", encoding="utf-8") as f:
                        sql_content = f.read()

                    # 分割SQL语句并执行
                    statements = self._split_sql_statements(sql_content)
                    print(f"开始执行 {len(statements)} 条 SQL 语句...")

                    executed = 0
                    for statement in statements:
                        if statement.strip():
                            try:
                                conn.execute(text(statement))
                                conn.commit()
                                executed += 1
                            except Exception as e:
                                # 忽略已存在的对象错误
                                if "already exists" not in str(e):
                                    print(f"执行SQL时出错: {e}")
                                    print(f"SQL语句: {statement[:100]}...")

                    print(f"成功执行 {executed}/{len(statements)} 条 SQL 语句")

                self._initialized = True
                print("业务数据库初始化完成")

        except Exception as e:
            print(f"初始化业务数据库时出错: {e}")
            import traceback
            traceback.print_exc()

    def _split_sql_statements(self, sql_content: str) -> list:
        """分割SQL语句"""
        statements = []
        current_statement = []
        in_comment = False

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

    def is_initialized(self) -> bool:
        """检查数据库是否已初始化"""
        return self._initialized


# 全局实例
business_db = BusinessDatabase()


def init_business_database():
    """初始化业务数据库（供应用启动时调用）"""
    business_db.initialize()