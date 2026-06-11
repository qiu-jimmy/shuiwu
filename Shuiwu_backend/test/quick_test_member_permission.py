"""
会员权限快速测试脚本
==================
简化版的测试脚本，用于快速验证基本功能

使用方法：
    python test/quick_test_member_permission.py
"""
import asyncio
import httpx
import json
from datetime import datetime


# 配置
BASE_URL = "http://127.0.0.1:8000"


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")


def print_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")


def print_info(msg):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.END}")


def print_section(title):
    print(f"\n{Colors.BOLD}{'━' * 50}{Colors.END}")
    print(f"{Colors.BOLD}{title}{Colors.END}")
    print(f"{Colors.BOLD}{'━' * 50}{Colors.END}")


async def test_login(username, password):
    """测试登录"""
    print_info(f"登录用户: {username}")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": username, "password": password}
        )
        result = response.json()

        # API 返回: {"code": 1, "message": "...", "data": {...}} 表示成功
        #        {"code": 0, "message": "...", "data": None} 表示失败
        if result.get("code") == 1 and result.get("data"):
            token = result["data"]["access_token"]
            print_success(f"登录成功")
            return token, result["data"]
        else:
            print_error(f"登录失败: {result.get('message')}")
            return None, None


async def test_privilege_with_token(token, privilege_name, endpoint):
    """使用 token 测试权限"""
    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.post(f"{BASE_URL}{endpoint}", headers=headers)

            # 先检查 HTTP 状态码
            if response.status_code != 200:
                print_error(f"{privilege_name}: HTTP {response.status_code}")
                return False

            result = response.json()

            # API 返回: {"code": 1, ...} 表示成功
            if result.get("code") == 1:
                # 检查是否为管理员跳过（安全地获取嵌套数据）
                data = result.get("data") or {}
                admin_info = data.get("admin_info") or {}
                is_admin_bypass = admin_info.get("is_admin", False)

                if is_admin_bypass:
                    print_success(f"{privilege_name}: 管理员跳过 ✓")
                else:
                    print_success(f"{privilege_name}: 有权限 ✓")
                return True
            else:
                msg = result.get("message", "未知错误")
                result_code = result.get("code", "")
                # 检查是否是权限相关的错误
                if "PRIVILEGE_REQUIRED" in str(result_code):
                    print_error(f"{privilege_name}: 无权限 ✗ ({msg})")
                elif "MEMBER_REQUIRED" in str(result_code):
                    print_error(f"{privilege_name}: 需要会员 ✗")
                elif "UPGRADE_REQUIRED" in str(result_code):
                    print_error(f"{privilege_name}: 需要升级套餐 ✗")
                else:
                    print_error(f"{privilege_name}: 失败 ✗ ({msg})")
                return False
    except Exception as e:
        print_error(f"{privilege_name}: 异常 ✗ ({e})")
        return False


async def test_get_privileges(token, user_label):
    """获取用户权益信息"""
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get(
            f"{BASE_URL}/api/examples/example/my-privileges",
            headers=headers
        )
        result = response.json()

        # API 返回: {"code": 1, ...} 表示成功
        if result.get("code") == 1:
            data = result.get("data", {})
            print_info(f"{user_label} 权益:")
            print(f"  套餐: {data.get('member_level')}")
            print(f"  RAG: {data.get('enable_rag')}")
            print(f"  网络搜索: {data.get('enable_web_search')}")
            print(f"  MCP 工具: {data.get('enable_mcp_tools')}")
            print(f"  今日对话: {data.get('today_chats')}/{data.get('max_daily_chats')}")
            print(f"  知识库: {data.get('kb_count')}/{data.get('max_kb_count')}")
        return result


async def test_admin_status(token):
    """检查管理员状态"""
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get(
            f"{BASE_URL}/api/examples/example/admin-check",
            headers=headers
        )
        result = response.json()

        # API 返回: {"code": 1, ...} 表示成功
        if result.get("code") == 1:
            data = result.get("data", {})
            is_admin = data.get("is_admin", False)
            if is_admin:
                print_success("管理员身份: 确认 ✓")
            else:
                print_info("管理员身份: 否")
        return result


async def main():
    """主测试函数"""
    print(f"\n{Colors.BOLD}{'=' * 50}{Colors.END}")
    print(f"{Colors.BOLD}会员权限快速测试{Colors.END}")
    print(f"{Colors.BOLD}{'=' * 50}{Colors.END}")
    print(f"测试服务器: {BASE_URL}")
    print(f"开始时间: {datetime.now().strftime('%H:%M:%S')}")

    # 测试账号（实际账号）
    test_accounts = [
        {
            "username": "13333333333",
            "password": "12345678",
            "label": "免费用户",
            "expected": {
                "rag": True,
                "web_search": False,
                "mcp_tools": False,
                "premium": False,
                "enterprise": False
            }
        },
        {
            "username": "15555555555",
            "password": "123456",
            "label": "管理员",
            "expected": {
                "rag": True,  # 管理员跳过
                "web_search": True,  # 管理员跳过
                "mcp_tools": True,  # 管理员跳过
                "premium": True,  # 管理员跳过
                "enterprise": True  # 管理员跳过
            }
        }
    ]

    results = {"passed": 0, "failed": 0}

    for account in test_accounts:
        print_section(f"测试: {account['label']}")

        # 1. 登录
        token, user_info = await test_login(account["username"], account["password"])
        if not token:
            results["failed"] += 1
            print_info("提示: 请确认用户名和密码正确")
            continue

        # 2. 查看权益
        await test_get_privileges(token, account["label"])

        # 3. 检查管理员状态
        if account["label"] == "管理员":
            await test_admin_status(token)

        # 4. 测试各种权限
        print_info("测试权限:")

        # RAG 功能
        has_rag = await test_privilege_with_token(token, "RAG 功能", "/api/examples/example/rag-chat")
        expected_rag = account["expected"]["rag"]
        if has_rag == expected_rag or (account["label"] == "管理员" and has_rag):
            pass  # 正确
        else:
            print_error(f"RAG 功能测试结果与预期不符")
            results["failed"] += 1

        # 高级会员功能
        has_premium = await test_privilege_with_token(token, "高级会员功能", "/api/examples/example/premium-feature")
        expected_premium = account["expected"]["premium"]

        # 企业级功能
        has_enterprise = await test_privilege_with_token(token, "企业级功能", "/api/examples/example/enterprise-feature")
        expected_enterprise = account["expected"]["enterprise"]

        results["passed"] += 1

    # 汇总
    print(f"\n{Colors.BOLD}{'━' * 50}{Colors.END}")
    print(f"{Colors.BOLD}测试汇总{Colors.END}")
    print(f"{Colors.BOLD}{'━' * 50}{Colors.END}\n")
    print(f"通过: {Colors.GREEN}{results['passed']}{Colors.END}")
    print(f"失败: {Colors.RED if results['failed'] > 0 else ''}{results['failed']}{Colors.END if results['failed'] > 0 else ''}")
    print(f"\n结束时间: {datetime.now().strftime('%H:%M:%S')}")

    if results["failed"] == 0:
        print_success("\n所有测试通过! ✓")
    else:
        print_error(f"\n有 {results['failed']} 个测试失败")
        print_info("请检查:")
        print_info("  1. 服务是否正常运行")
        print_info("  2. 测试数据是否已初始化")
        print_info("  3. 套餐配置是否正确")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n测试被中断")
    except Exception as e:
        print_error(f"\n测试出错: {e}")
