"""
会员权限测试数据初始化脚本
============================
创建测试所需的套餐数据和测试用户

使用方法：
    python test/init_member_permission_test_data.py
"""
import asyncio
import os
import psycopg2
from datetime import datetime, timedelta
from psycopg2.extras import RealDictCursor


# ==================== 配置 ====================

DB_CONFIG = {
    "host": os.getenv("PG_HOST", "localhost"),
    "port": int(os.getenv("PG_PORT", 5432)),
    "database": os.getenv("PG_DATABASE", "Agno"),
    "user": os.getenv("PG_USER", "postgres"),
    "password": os.getenv("PG_PASSWORD", "root")
}

TEST_USER_PREFIX = "test_member_perm_"


# ==================== 数据库操作 ====================

def get_connection():
    """获取数据库连接"""
    return psycopg2.connect(**DB_CONFIG)


def init_member_packages():
    """初始化会员套餐数据"""
    print("初始化会员套餐数据...")

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # 清理旧数据（可选）
    # cursor.execute("DELETE FROM business.member_packages WHERE package_id LIKE 'test_%'")

    # 插入测试套餐
    packages = [
        {
            "package_id": "free",
            "name": "免费版",
            "description": "基础功能体验",
            "package_type": "lifetime",
            "price": 0,
            "duration_days": None,
            "max_daily_chats": 20,
            "max_kb_count": 2,
            "max_kb_documents": 20,
            "max_file_storage_mb": 100,
            "max_file_count": 50,
            "enable_rag": True,
            "enable_web_search": False,
            "enable_mcp_tools": False,
            "sort_order": 0,
            "status": "active",
            "custom_config": {
                "priority": 0,
                "level": "free"
            },
            "benefits": [
                {"title": "每日20次对话", "desc": "每天可以免费使用20次AI对话"},
                {"title": "2个知识库", "desc": "支持创建2个个人知识库"},
                {"title": "基础RAG功能", "desc": "知识库检索增强生成"}
            ]
        },
        {
            "package_id": "vip_month",
            "name": "VIP 月卡",
            "description": "月度会员，解锁更多功能",
            "package_type": "month",
            "price": 29.9,
            "original_price": 39.9,
            "duration_days": 30,
            "max_daily_chats": -1,  # 无限制
            "max_kb_count": 10,
            "max_kb_documents": 500,
            "max_file_storage_mb": 2048,
            "max_file_count": 200,
            "enable_rag": True,
            "enable_web_search": True,
            "enable_mcp_tools": False,
            "sort_order": 1,
            "status": "active",
            "custom_config": {
                "priority": 1,
                "level": "basic"
            },
            "benefits": [
                {"title": "无限对话", "desc": "每日无限制AI对话次数"},
                {"title": "10个知识库", "desc": "支持创建10个知识库"},
                {"title": "网络搜索", "desc": "支持实时网络搜索功能"},
                {"title": "2GB存储", "desc": "云端文件存储空间"}
            ]
        },
        {
            "package_id": "premium_year",
            "name": "VIP 年卡",
            "description": "年度会员，最佳性价比",
            "package_type": "year",
            "price": 299.9,
            "original_price": 399.9,
            "duration_days": 365,
            "max_daily_chats": -1,
            "max_kb_count": 50,
            "max_kb_documents": 5000,
            "max_file_storage_mb": 10240,
            "max_file_count": 500,
            "enable_rag": True,
            "enable_web_search": True,
            "enable_mcp_tools": True,
            "sort_order": 2,
            "status": "active",
            "custom_config": {
                "priority": 2,
                "level": "premium"
            },
            "benefits": [
                {"title": "无限对话", "desc": "每日无限制AI对话次数"},
                {"title": "50个知识库", "desc": "支持创建50个知识库"},
                {"title": "全功能解锁", "desc": "RAG、网络搜索、MCP工具全开"},
                {"title": "10GB存储", "desc": "超大云端文件存储空间"}
            ]
        },
        {
            "package_id": "enterprise_year",
            "name": "企业年卡",
            "description": "企业级会员，最高权限",
            "package_type": "year",
            "price": 999.9,
            "original_price": 1299.9,
            "duration_days": 365,
            "max_daily_chats": -1,
            "max_kb_count": 100,
            "max_kb_documents": 10000,
            "max_file_storage_mb": 51200,
            "max_file_count": 1000,
            "enable_rag": True,
            "enable_web_search": True,
            "enable_mcp_tools": True,
            "sort_order": 3,
            "status": "active",
            "custom_config": {
                "priority": 3,
                "level": "enterprise"
            },
            "benefits": [
                {"title": "无限对话", "desc": "每日无限制AI对话次数"},
                {"title": "100个知识库", "desc": "支持创建100个知识库"},
                {"title": "全功能解锁", "desc": "RAG、网络搜索、MCP工具全开"},
                {"title": "50GB存储", "desc": "超大云端文件存储空间"},
                {"title": "专属客服", "desc": "优先客服支持"}
            ]
        }
    ]

    for pkg in packages:
        # 检查是否已存在
        cursor.execute(
            "SELECT package_id FROM business.member_packages WHERE package_id = %s",
            (pkg["package_id"],)
        )
        if cursor.fetchone():
            print(f"  套餐 {pkg['package_id']} 已存在，跳过创建")
            continue

        # 插入套餐
        cursor.execute("""
            INSERT INTO business.member_packages (
                package_id, name, description, package_type, price, original_price,
                duration_days, max_daily_chats, max_kb_count, max_kb_documents,
                max_file_storage_mb, max_file_count, enable_rag, enable_web_search,
                enable_mcp_tools, sort_order, status, custom_config, benefits
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb
            )
        """, (
            pkg["package_id"], pkg["name"], pkg["description"], pkg["package_type"],
            pkg["price"], pkg["original_price"], pkg["duration_days"],
            pkg["max_daily_chats"], pkg["max_kb_count"], pkg["max_kb_documents"],
            pkg["max_file_storage_mb"], pkg["max_file_count"],
            pkg["enable_rag"], pkg["enable_web_search"], pkg["enable_mcp_tools"],
            pkg["sort_order"], pkg["status"],
            psycopg2.extras.Json(pkg["custom_config"]),
            psycopg2.extras.Json(pkg["benefits"])
        ))
        print(f"  ✓ 创建套餐: {pkg['package_id']} - {pkg['name']}")

    conn.commit()
    cursor.close()
    conn.close()

    print("套餐数据初始化完成!\n")


def init_test_users():
    """创建测试用户"""
    print("创建测试用户...")

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    test_users = [
        {
            "username": f"{TEST_USER_PREFIX}free",
            "phone": "13800138000",
            "password": "Test123456",
            "member_level": "free",
            "member_expire_at": datetime.now() + timedelta(days=365)
        },
        {
            "username": f"{TEST_USER_PREFIX}vip_month",
            "phone": "13800138001",
            "password": "Test123456",
            "member_level": "vip_month",
            "member_expire_at": datetime.now() + timedelta(days=30)
        },
        {
            "username": f"{TEST_USER_PREFIX}premium_year",
            "phone": "13800138002",
            "password": "Test123456",
            "member_level": "premium_year",
            "member_expire_at": datetime.now() + timedelta(days=365)
        },
        {
            "username": f"{TEST_USER_PREFIX}admin",
            "phone": "13800138003",
            "password": "Test123456",
            "member_level": "free",  # 管理员不需要会员
            "member_expire_at": None,
            "user_type": "admin",
            "role": "admin"
        }
    ]

    for user in test_users:
        # 检查是否已存在
        cursor.execute(
            "SELECT user_id FROM business.users WHERE username = %s",
            (user["username"],)
        )
        existing = cursor.fetchone()

        if existing:
            # 更新现有用户
            cursor.execute("""
                UPDATE business.users
                SET member_level = %s,
                    member_expire_at = %s,
                    user_type = COALESCE(%s, user_type),
                    role = COALESCE(%s, role),
                    updated_at = CURRENT_TIMESTAMP
                WHERE username = %s
            """, (
                user["member_level"], user["member_expire_at"],
                user.get("user_type"), user.get("role"),
                user["username"]
            ))
            print(f"  ✓ 更新用户: {user['username']} ({user['member_level']})")
        else:
            # 创建新用户（需要生成 user_id 和密码哈希）
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            password_hash = pwd_context.hash(user["password"])
            user_id = f"user_{user['username']}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

            cursor.execute("""
                INSERT INTO business.users (
                    user_id, username, nickname, phone, password_hash,
                    member_level, member_expire_at, user_type, role, status
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, 'normal'
                )
            """, (
                user_id, user["username"], f"测试用户_{user['username']}",
                user["phone"], password_hash, user["member_level"],
                user["member_expire_at"], user.get("user_type"),
                user.get("role")
            ))
            print(f"  ✓ 创建用户: {user['username']} ({user['member_level']})")
            print(f"    密码: {user['password']}")

    conn.commit()
    cursor.close()
    conn.close()

    print("测试用户创建完成!\n")


def show_test_credentials():
    """显示测试账号凭证"""
    print("\n" + "=" * 60)
    print("测试账号凭证")
    print("=" * 60)
    print("\n所有测试用户的密码都是: Test123456\n")

    print("用户列表:")
    print("  1. 免费用户")
    print("     用户名: test_member_perm_free")
    print("     套餐: free")
    print("     权益: RAG 功能，每日 20 次对话")
    print("")
    print("  2. VIP 月卡用户")
    print("     用户名: test_member_perm_vip_month")
    print("     套餐: vip_month (priority=1)")
    print("     权益: RAG + 网络搜索，无限对话")
    print("")
    print("  3. VIP 年卡用户")
    print("     用户名: test_member_perm_premium_year")
    print("     套餐: premium_year (priority=2)")
    print("     权益: RAG + 网络搜索 + MCP 工具")
    print("")
    print("  4. 管理员")
    print("     用户名: test_member_perm_admin")
    print("     权限: 跳过所有会员权限检查")
    print("")
    print("=" * 60 + "\n")


def cleanup_test_data():
    """清理测试数据"""
    print("清理测试数据...")
    print("警告: 此操作将删除所有测试用户和相关数据!")

    confirm = input("确认清理? (yes/no): ")
    if confirm.lower() != "yes":
        print("取消清理")
        return

    conn = get_connection()
    cursor = conn.cursor()

    # 删除测试用户
    cursor.execute(f"""
        DELETE FROM business.users
        WHERE username LIKE '{TEST_USER_PREFIX}%'
    """)
    deleted_count = cursor.rowcount
    conn.commit()

    cursor.close()
    conn.close()

    print(f"✓ 已删除 {deleted_count} 个测试用户")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("会员权限测试数据初始化")
    print("=" * 60 + "\n")

    try:
        # 1. 初始化套餐
        init_member_packages()

        # 2. 创建测试用户
        init_test_users()

        # 3. 显示凭证
        show_test_credentials()

        print("✓ 测试数据初始化完成!")
        print("\n接下来可以运行:")
        print("  python test/test_member_permission_e2e.py")

    except Exception as e:
        print(f"\n✗ 初始化失败: {e}")
        import traceback
        traceback.print_exc()

    else:
        # 询问是否清理
        print("\n其他操作:")
        print("  1. 查看测试账号凭证")
        print("  2. 清理测试数据")
        print("  0. 退出")

        choice = input("\n请选择 (0-2): ")

        if choice == "1":
            show_test_credentials()
        elif choice == "2":
            cleanup_test_data()


if __name__ == "__main__":
    main()
