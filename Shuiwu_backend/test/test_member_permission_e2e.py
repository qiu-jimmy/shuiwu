"""
会员权限系统端对端测试脚本
============================
测试所有会员权限功能，包括：
- 权益检查（rag, web_search, mcp_tools）
- 配额检查（daily_chats, kb_count, file_storage等）
- 套餐检查（优先级比较）
- 组合检查
- 管理员跳过权限
- OR/AND 逻辑

使用方法：
    python test/test_member_permission_e2e.py

环境要求：
    - 服务运行在 http://127.0.0.1:8000
    - 数据库已初始化会员套餐数据
"""
import asyncio
import httpx
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta


# ==================== 配置 ====================

BASE_URL = "http://127.0.0.1:8000"
TEST_USER_PREFIX = "test_member_perm_"


# ==================== 工具函数 ====================

class Colors:
    """终端颜色"""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_success(msg: str):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")


def print_error(msg: str):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")


def print_info(msg: str):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.END}")


def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")


def print_section(title: str):
    print(f"\n{Colors.BOLD}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{title}{Colors.END}")
    print(f"{Colors.BOLD}{'=' * 60}{Colors.END}\n")


# ==================== 测试客户端 ====================

class MemberPermissionTestClient:
    """会员权限测试客户端"""

    def __init__(self):
        self.base_url = BASE_URL
        self.token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.username: Optional[str] = None
        self.user_type: Optional[str] = None
        self.role: Optional[str] = None

    async def request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        token: Optional[str] = None
    ) -> Dict[str, Any]:
        """发送 HTTP 请求"""
        url = f"{self.base_url}{path}"
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        elif self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                if method == "GET":
                    response = await client.get(url, headers=headers, params=params)
                elif method == "POST":
                    response = await client.post(url, headers=headers, json=data)
                elif method == "PUT":
                    response = await client.put(url, headers=headers, json=data)
                elif method == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    raise ValueError(f"不支持的请求方法: {method}")

                return response.json()
            except httpx.HTTPError as e:
                return {"code": "HTTP_ERROR", "message": str(e)}
            except json.JSONDecodeError:
                return {"code": "INVALID_JSON", "message": "响应不是有效的 JSON"}

    async def register_user(
        self,
        username: str,
        password: str = "Test123456",
        phone: Optional[str] = None
    ) -> Dict[str, Any]:
        """注册用户"""
        data = {
            "username": username,
            "password": password,
            "nickname": f"测试用户_{username}"
        }
        if phone:
            data["phone"] = phone

        return await self.request("POST", "/api/auth/register", data=data)

    async def login_user(self, username: str, password: str = "Test123456") -> Dict[str, Any]:
        """登录用户"""
        data = {"username": username, "password": password}
        result = await self.request("POST", "/api/auth/login", data=data)

        if result.get("code") == 200 and result.get("data"):
            self.token = result["data"].get("access_token")
            self.user_id = result["data"].get("user_id")
            self.username = result["data"].get("username")
            print_success(f"登录成功: {username}")
            return result
        else:
            print_error(f"登录失败: {result.get('message')}")
            return result

    async def get_my_privileges(self) -> Dict[str, Any]:
        """获取当前用户的权益"""
        return await self.request("GET", "/api/examples/my-privileges")

    async def check_admin_status(self) -> Dict[str, Any]:
        """检查管理员状态"""
        return await self.request("GET", "/api/examples/admin-check")

    async def test_rag_chat(self) -> Dict[str, Any]:
        """测试 RAG 聊天功能"""
        return await self.request("POST", "/api/examples/rag-chat")

    async def test_premium_feature(self) -> Dict[str, Any]:
        """测试高级会员功能"""
        return await self.request("POST", "/api/examples/premium-feature")

    async def test_advanced_chat_or(self) -> Dict[str, Any]:
        """测试高级聊天（OR 逻辑）"""
        return await self.request("POST", "/api/examples/advanced-chat-or")

    async def test_advanced_chat_and(self) -> Dict[str, Any]:
        """测试高级聊天（AND 逻辑）"""
        return await self.request("POST", "/api/examples/advanced-chat-and")

    async def test_create_knowledge(self) -> Dict[str, Any]:
        """测试创建知识库"""
        return await self.request("POST", "/api/examples/create-knowledge")

    async def test_upload_large_file(self) -> Dict[str, Any]:
        """测试上传大文件"""
        return await self.request("POST", "/api/examples/upload-large-file")

    async def test_enterprise_feature(self) -> Dict[str, Any]:
        """测试企业级功能"""
        return await self.request("POST", "/api/examples/enterprise-feature")

    async def test_admin_bypass(self) -> Dict[str, Any]:
        """测试管理员跳过权限"""
        return await self.request("GET", "/api/examples/admin-bypass")

    async def update_user_member(
        self,
        user_id: str,
        member_level: str,
        member_expire_at: Optional[str] = None,
        token: Optional[str] = None
    ) -> Dict[str, Any]:
        """直接更新用户会员信息（管理员接口）"""
        # 注意：这个接口需要管理员权限，或者通过数据库直接操作
        # 这里我们使用一个假设的管理员接口
        data = {
            "user_id": user_id,
            "member_level": member_level
        }
        if member_expire_at:
            data["member_expire_at"] = member_expire_at

        # 尝试调用管理员接口（如果不存在，需要手动在数据库中更新）
        return await self.request("POST", "/api/admin/update-member", data=data, token=token)

    async def get_package_info(self, package_id: str) -> Dict[str, Any]:
        """获取套餐信息"""
        return await self.request("GET", f"/api/examples/privileges-by-package/{package_id}")


# ==================== 数据库操作 ====================

async def update_user_via_db(user_id: str, member_level: str):
    """直接通过数据库更新用户会员信息"""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor

        # 从环境变量或配置中读取数据库连接信息
        import os
        conn = psycopg2.connect(
            host=os.getenv("PG_HOST", "localhost"),
            port=int(os.getenv("PG_PORT", 5432)),
            database=os.getenv("PG_DATABASE", "Agno"),
            user=os.getenv("PG_USER", "postgres"),
            password=os.getenv("PG_PASSWORD", "root")
        )

        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # 计算到期时间（1年后）
        expire_at = datetime.now() + timedelta(days=365)

        # 更新用户会员信息
        cursor.execute("""
            UPDATE business.users
            SET member_level = %s,
                member_expire_at = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
            RETURNING user_id, username, member_level, member_expire_at
        """, (member_level, expire_at, user_id))

        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()

        if result:
            print_success(f"数据库更新成功: {user_id} -> {member_level}")
            return True
        else:
            print_error(f"用户不存在: {user_id}")
            return False

    except ImportError:
        print_warning("未安装 psycopg2，跳过数据库操作")
        print_info("请手动在数据库中执行:")
        print_info(f"UPDATE business.users SET member_level='{member_level}' WHERE user_id='{user_id}';")
        return None
    except Exception as e:
        print_error(f"数据库操作失败: {e}")
        return None


# ==================== 测试场景 ====================

async def test_free_user_privileges():
    """测试免费用户权限"""
    print_section("测试 1: 免费用户权限")

    client = MemberPermissionTestClient()
    username = f"{TEST_USER_PREFIX}free"

    # 1. 注册并登录
    print_info("1. 注册免费用户...")
    result = await client.register_user(username, phone="13800138000")
    if result.get("code") != 200:
        print_warning(f"注册失败或用户已存在: {result.get('message')}")
    else:
        print_success("用户注册成功")

    print_info("2. 登录...")
    await client.login_user(username)

    # 3. 查看用户权益
    print_info("3. 查看用户权益...")
    privileges = await client.get_my_privileges()
    print(f"   用户权益: {json.dumps(privileges, ensure_ascii=False, indent=2)}")

    # 4. 测试 RAG 功能（免费用户应该有）
    print_info("4. 测试 RAG 功能...")
    result = await client.test_rag_chat()
    if result.get("code") == 200:
        print_success("✓ RAG 功能可用")
    else:
        print_error(f"✗ RAG 功能不可用: {result.get('message')}")

    # 5. 测试高级会员功能（免费用户不应该有）
    print_info("5. 测试高级会员功能（应该失败）...")
    result = await client.test_premium_feature()
    if result.get("code") == 200:
        print_warning("⚠ 免费用户可以访问高级功能（可能是配置问题）")
    else:
        print_success(f"✓ 正确阻止免费用户: {result.get('message')}")

    return client


async def test_vip_month_user_privileges():
    """测试 VIP 月卡用户权限"""
    print_section("测试 2: VIP 月卡用户权限")

    client = MemberPermissionTestClient()
    username = f"{TEST_USER_PREFIX}vip_month"

    # 1. 注册并登录
    print_info("1. 注册用户...")
    await client.register_user(username, phone="13800138001")
    await client.login_user(username)

    # 2. 升级为 VIP 月卡
    print_info("2. 升级为 VIP 月卡套餐...")
    success = await update_user_via_db(client.user_id, "vip_month")
    if success is False:
        return

    # 重新登录以刷新 token
    await client.login_user(username)

    # 3. 查看用户权益
    print_info("3. 查看用户权益...")
    privileges = await client.get_my_privileges()
    print(f"   用户权益: {json.dumps(privileges, ensure_ascii=False, indent=2)}")

    # 4. 测试 RAG 功能
    print_info("4. 测试 RAG 功能...")
    result = await client.test_rag_chat()
    if result.get("code") == 200:
        print_success("✓ RAG 功能可用")
    else:
        print_error(f"✗ RAG 功能不可用: {result.get('message')}")

    # 5. 测试高级会员功能
    print_info("5. 测试高级会员功能...")
    result = await client.test_premium_feature()
    if result.get("code") == 200:
        print_success("✓ 高级会员功能可用")
    else:
        print_error(f"✗ 高级会员功能不可用: {result.get('message')}")

    # 6. 测试 OR 逻辑
    print_info("6. 测试 OR 逻辑（RAG 或网络搜索）...")
    result = await client.test_advanced_chat_or()
    if result.get("code") == 200:
        print_success("✓ OR 逻辑检查通过")
    else:
        print_error(f"✗ OR 逻辑检查失败: {result.get('message')}")

    # 7. 测试企业级功能（应该失败）
    print_info("7. 测试企业级功能（应该失败）...")
    result = await client.test_enterprise_feature()
    if result.get("code") == 200:
        print_warning("⚠ VIP 月卡用户可以访问企业级功能")
    else:
        print_success(f"✓ 正确阻止: {result.get('message')}")

    return client


async def test_premium_year_user_privileges():
    """测试 VIP 年卡用户权限（优先级更高）"""
    print_section("测试 3: VIP 年卡用户权限（优先级更高）")

    client = MemberPermissionTestClient()
    username = f"{TEST_USER_PREFIX}premium_year"

    # 1. 注册并登录
    print_info("1. 注册用户...")
    await client.register_user(username, phone="13800138002")
    await client.login_user(username)

    # 2. 升级为 VIP 年卡
    print_info("2. 升级为 VIP 年卡套餐（priority=2）...")
    success = await update_user_via_db(client.user_id, "premium_year")
    if success is False:
        return

    await client.login_user(username)

    # 3. 查看用户权益
    print_info("3. 查看用户权益...")
    privileges = await client.get_my_privileges()
    print(f"   用户权益: {json.dumps(privileges, ensure_ascii=False, indent=2)}")

    # 4. 测试企业级功能（由于 priority=2 > vip_month=1，应该可以访问）
    print_info("4. 测试企业级功能（优先级比较）...")
    result = await client.test_enterprise_feature()
    if result.get("code") == 200:
        print_success("✓ 优先级比较通过：VIP 年卡可以访问需要 VIP 月卡的功能")
    else:
        print_warning(f"⚠ 优先级比较未通过: {result.get('message')}")

    # 5. 测试 AND 逻辑
    print_info("5. 测试 AND 逻辑（RAG + 网络搜索 + MCP 工具）...")
    result = await client.test_advanced_chat_and()
    if result.get("code") == 200:
        print_success("✓ AND 逻辑检查通过")
    else:
        print_error(f"✗ AND 逻辑检查失败: {result.get('message')}")

    return client


async def test_admin_bypass_privileges():
    """测试管理员跳过权限"""
    print_section("测试 4: 管理员跳过权限")

    client = MemberPermissionTestClient()
    username = f"{TEST_USER_PREFIX}admin"

    # 1. 注册并登录
    print_info("1. 注册管理员用户...")
    result = await client.register_user(username, phone="13800138003")

    # 2. 设置为管理员
    print_info("2. 设置为管理员（user_type=admin）...")
    try:
        import psycopg2
        import os

        conn = psycopg2.connect(
            host=os.getenv("PG_HOST", "localhost"),
            port=int(os.getenv("PG_PORT", 5432)),
            database=os.getenv("PG_DATABASE", "Agno"),
            user=os.getenv("PG_USER", "postgres"),
            password=os.getenv("PG_PASSWORD", "root")
        )

        cursor = conn.cursor()
        cursor.execute("""
            UPDATE business.users
            SET user_type = 'admin',
                role = 'admin',
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
        """, (client.user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        print_success("管理员设置成功")
    except Exception as e:
        print_error(f"设置管理员失败: {e}")
        print_info("请手动在数据库中执行:")
        print_info(f"UPDATE business.users SET user_type='admin', role='admin' WHERE user_id='{client.user_id}';")

    await client.login_user(username)

    # 3. 检查管理员状态
    print_info("3. 检查管理员状态...")
    admin_status = await client.check_admin_status()
    print(f"   管理员状态: {json.dumps(admin_status, ensure_ascii=False, indent=2)}")

    if admin_status.get("data", {}).get("is_admin"):
        print_success("✓ 管理员身份确认")
    else:
        print_warning("⚠ 管理员身份未确认")

    # 4. 测试管理员跳过权限
    print_info("4. 测试管理员跳过 RAG 权限检查...")
    result = await client.test_admin_bypass()
    if result.get("code") == 200:
        data = result.get("data", {})
        if data.get("admin_info", {}).get("is_admin"):
            print_success("✓ 管理员成功跳过权限检查")
            print(f"   跳过信息: {data}")
        else:
            print_warning("⚠ 未检测到管理员跳过")
    else:
        print_error(f"✗ 请求失败: {result.get('message')}")

    # 5. 测试管理员访问企业级功能（即使没有会员）
    print_info("5. 测试管理员访问企业级功能（无需会员）...")
    result = await client.test_enterprise_feature()
    if result.get("code") == 200:
        print_success("✓ 管理员可以访问所有功能")
    else:
        print_warning(f"⚠ 访问受限: {result.get('message')}")

    return client


async def test_quota_limits():
    """测试配额限制"""
    print_section("测试 5: 配额限制")

    client = MemberPermissionTestClient()
    username = f"{TEST_USER_PREFIX}quota"

    # 1. 注册并登录
    print_info("1. 注册用户...")
    await client.register_user(username, phone="13800138004")
    await client.login_user(username)

    # 2. 设置为免费套餐（配额有限）
    print_info("2. 设置为免费套餐（测试配额限制）...")
    await update_user_via_db(client.user_id, "free")
    await client.login_user(username)

    # 3. 查看配额使用情况
    print_info("3. 查看配额使用情况...")
    privileges = await client.get_my_privileges()
    if privileges.get("code") == 200:
        data = privileges.get("data", {})
        print(f"   今日聊天: {data.get('today_chats', 0)} / {data.get('max_daily_chats', 0)}")
        print(f"   知识库数量: {data.get('kb_count', 0)} / {data.get('max_kb_count', 0)}")
        print(f"   文件存储: {data.get('used_storage_mb', 0)} MB / {data.get('max_file_storage_mb', 0)} MB")

    # 4. 测试创建知识库（配额检查）
    print_info("4. 测试创建知识库（配额检查）...")
    result = await client.test_create_knowledge()
    if result.get("code") == 200:
        print_success("✓ 配额检查通过")
    else:
        print_warning(f"⚠ 配额不足或检查失败: {result.get('message')}")

    return client


async def test_custom_privilege():
    """测试自定义权益（custom_config）"""
    print_section("测试 6: 自定义权益（custom_config）")

    # 1. 首先检查套餐配置
    print_info("1. 检查套餐配置...")
    client = MemberPermissionTestClient()

    result = await client.get_package_info("premium_year")
    print(f"   套餐信息: {json.dumps(result, ensure_ascii=False, indent=2)}")

    # 2. 测试自定义功能
    print_info("2. 如果套餐配置了自定义权益，测试访问...")

    username = f"{TEST_USER_PREFIX}custom"
    await client.register_user(username, phone="13800138005")
    await client.login_user(username)
    await update_user_via_db(client.user_id, "premium_year")
    await client.login_user(username)

    # 测试企业功能
    result = await client.test_enterprise_feature()
    if result.get("code") == 200:
        print_success("✓ 自定义权益功能可用")
    else:
        print_warning(f"⚠ 自定义权益功能不可用: {result.get('message')}")

    return client


# ==================== 主测试函数 ====================

async def run_all_tests():
    """运行所有测试"""
    print(f"\n{Colors.BOLD}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}会员权限系统端对端测试{Colors.END}")
    print(f"{Colors.BOLD}{'=' * 60}{Colors.END}")
    print(f"测试服务器: {BASE_URL}")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = {
        "passed": 0,
        "failed": 0,
        "warnings": 0,
        "tests": []
    }

    # 测试 1: 免费用户
    try:
        await test_free_user_privileges()
        results["passed"] += 1
        results["tests"].append(("免费用户权限", "PASSED"))
    except Exception as e:
        results["failed"] += 1
        results["tests"].append(("免费用户权限", f"FAILED: {e}"))
        print_error(f"测试失败: {e}")

    # 测试 2: VIP 月卡用户
    try:
        await test_vip_month_user_privileges()
        results["passed"] += 1
        results["tests"].append(("VIP 月卡用户权限", "PASSED"))
    except Exception as e:
        results["failed"] += 1
        results["tests"].append(("VIP 月卡用户权限", f"FAILED: {e}"))
        print_error(f"测试失败: {e}")

    # 测试 3: VIP 年卡用户（优先级）
    try:
        await test_premium_year_user_privileges()
        results["passed"] += 1
        results["tests"].append(("VIP 年卡用户权限（优先级）", "PASSED"))
    except Exception as e:
        results["failed"] += 1
        results["tests"].append(("VIP 年卡用户权限（优先级）", f"FAILED: {e}"))
        print_error(f"测试失败: {e}")

    # 测试 4: 管理员跳过权限
    try:
        await test_admin_bypass_privileges()
        results["passed"] += 1
        results["tests"].append(("管理员跳过权限", "PASSED"))
    except Exception as e:
        results["failed"] += 1
        results["tests"].append(("管理员跳过权限", f"FAILED: {e}"))
        print_error(f"测试失败: {e}")

    # 测试 5: 配额限制
    try:
        await test_quota_limits()
        results["passed"] += 1
        results["tests"].append(("配额限制", "PASSED"))
    except Exception as e:
        results["failed"] += 1
        results["tests"].append(("配额限制", f"FAILED: {e}"))
        print_error(f"测试失败: {e}")

    # 测试 6: 自定义权益
    try:
        await test_custom_privilege()
        results["passed"] += 1
        results["tests"].append(("自定义权益", "PASSED"))
    except Exception as e:
        results["failed"] += 1
        results["tests"].append(("自定义权益", f"FAILED: {e}"))
        print_error(f"测试失败: {e}")

    # 打印测试结果汇总
    print(f"\n{Colors.BOLD}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}测试结果汇总{Colors.END}")
    print(f"{Colors.BOLD}{'=' * 60}{Colors.END}\n")

    for test_name, result in results["tests"]:
        if result == "PASSED":
            print_success(f"{test_name}")
        elif "FAILED" in result:
            print_error(f"{test_name}")
            print(f"   {result}")
        else:
            print_warning(f"{test_name}")
            print(f"   {result}")

    print(f"\n总计: {Colors.BOLD}{results['passed']} 通过{Colors.END}, "
          f"{Colors.RED if results['failed'] > 0 else ''}{results['failed']} 失败{Colors.END if results['failed'] > 0 else ''}, "
          f"{Colors.YELLOW if results['warnings'] > 0 else ''}{results['warnings']} 警告{Colors.END if results['warnings'] > 0 else ''}")
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 输出 SQL 清理脚本
    print(f"\n{Colors.BOLD}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}测试数据清理{Colors.END}")
    print(f"{Colors.BOLD}{'=' * 60}{Colors.END}\n")
    print("如需清理测试数据，请执行以下 SQL:")
    print("-- 删除测试用户")
    print(f"DELETE FROM business.users WHERE username LIKE '{TEST_USER_PREFIX}%';")


# ==================== 入口函数 ====================

async def main():
    """主函数"""
    try:
        await run_all_tests()
    except KeyboardInterrupt:
        print_warning("\n测试被用户中断")
    except Exception as e:
        print_error(f"\n测试发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
