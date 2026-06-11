"""
发票穿透报告接口测试脚本

功能：
1. 测试获取配置信息
2. 测试获取授权链接
3. 测试获取报告数据
4. 测试回调接口

运行方式：
    python test/test_invoice_penetration.py
"""
import asyncio
import httpx
import os
import sys
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 配置
BASE_URL = os.getenv('API_BASE_URL', 'http://127.0.0.1:8000')
TEST_USER = {
    'phone': '15555555555',
    'password': '12345678'
}

# 测试数据
TEST_TAXPAYER_ID = '91330382556157804A'
TEST_COMPANY_NAME = '乐清市琪源电气科技有限公司'
TEST_CBURL = 'https://example.com/callback'

# 全局变量存储测试结果
test_results = {
    'passed': 0,
    'failed': 0,
    'skipped': 0
}


def print_section(title: str):
    """打印分隔线"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_test(name: str, status: str, message: str = ""):
    """打印测试结果"""
    status_icon = {
        'PASS': '✓',
        'FAIL': '✗',
        'SKIP': '⊘'
    }.get(status, '?')

    print(f"\n[{status_icon}] {name}")
    if message:
        print(f"    {message}")

    test_results[status.lower()] = test_results.get(status.lower(), 0) + 1


async def login() -> str:
    """登录获取 token"""
    print_section("步骤 0: 用户登录")

    async with httpx.AsyncClient(timeout=10.0) as client:
        # 尝试登录（使用 username 字段）
        response = await client.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "username": TEST_USER['phone'],  # 登录接口使用 username 字段
                "password": TEST_USER['password']
            }
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 1:
                token = data["data"]["access_token"]
                print_test("用户登录", "PASS", f"获取 token 成功")
                return token

        # 登录失败，尝试注册
        print("登录失败，尝试注册新用户...")

        # 生成唯一手机号
        timestamp = str(int(datetime.now().timestamp()))[-6:]
        TEST_USER['phone'] = f"1888888{timestamp}"

        # 注册
        reg_response = await client.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "phone": TEST_USER['phone'],
                "password": TEST_USER['password'],
                "sms_code": "123456",
            }
        )

        # 登录
        login_response = await client.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "username": TEST_USER['phone'],  # 登录接口使用 username 字段
                "password": TEST_USER['password']
            }
        )

        if login_response.status_code == 200:
            data = login_response.json()
            if data.get("code") == 1:
                token = data["data"]["access_token"]
                print_test("用户注册+登录", "PASS", f"获取 token 成功")
                return token

        print_test("用户认证", "FAIL", "无法获取 token")
        return None


async def test_get_config(token: str):
    """测试获取配置信息"""
    print_section("测试 1: 获取配置信息")

    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/invoice-penetration/config",
            headers=headers
        )

        print(f"请求: GET /api/invoice-penetration/config")
        print(f"状态码: {response.status_code}")

        result = response.json()
        print(f"响应: {result}")

        if result.get("code") == 1:
            data = result.get('data', {})
            print_test("获取配置", "PASS", f"BaseURL: {data.get('baseUrl')}")
            return True
        else:
            print_test("获取配置", "FAIL", result.get('message'))
            return False


async def test_get_authorization_url(token: str):
    """测试获取授权链接"""
    print_section("测试 2: 获取授权链接")

    headers = {"Authorization": f"Bearer {token}"}

    # 构建请求参数（使用驼峰命名）
    request_data = {
        "taxpayerId": TEST_TAXPAYER_ID,
        "companyName": TEST_COMPANY_NAME,
        "cburl": TEST_CBURL,
        "reportType": "1",
        "beginDate": "202309",
        "overDate": "202408"
    }

    print(f"请求参数:")
    print(f"  taxpayerId: {request_data['taxpayerId']}")
    print(f"  companyName: {request_data['companyName']}")
    print(f"  cburl: {request_data['cburl']}")
    print(f"  reportType: {request_data['reportType']}")
    print(f"  beginDate: {request_data['beginDate']}")
    print(f"  overDate: {request_data['overDate']}")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/invoice-penetration/authorization",
            headers=headers,
            json=request_data
        )

        print(f"\n请求: POST /api/invoice-penetration/authorization")
        print(f"状态码: {response.status_code}")

        result = response.json()
        print(f"响应 code: {result.get('code')}")
        print(f"响应 message: {result.get('message')}")

        if result.get("code") == 1:
            data = result.get('data', {})
            order_no = data.get("orderNo")
            initial_url = data.get("initialUrl")

            print(f"\n返回数据:")
            print(f"  orderNo: {order_no}")
            print(f"  initialUrl: {initial_url[:80]}..." if initial_url else "  initialUrl: 无")

            print_test("获取授权链接", "PASS", f"订单号: {order_no}")
            return order_no
        else:
            error_msg = result.get('message', '未知错误')
            print_test("获取授权链接", "FAIL", error_msg)

            # 说明可能的原因
            if '非法参数' in error_msg:
                print(f"\n[提示] '非法参数' 可能是因为:")
                print(f"  1. 纳税人识别号在测试环境中无效")
                print(f"  2. 需要向查税宝获取有效的测试数据")
            return None


async def test_get_report_data(token: str, order_no: str):
    """测试获取报告数据"""
    print_section("测试 3: 获取报告数据")

    if not order_no:
        print_test("获取报告数据", "SKIP", "没有可用的订单号")
        return

    headers = {"Authorization": f"Bearer {token}"}

    # 构建请求参数（使用驼峰命名）
    params = {
        "taxpayerId": TEST_TAXPAYER_ID,
        "companyName": TEST_COMPANY_NAME,
        "orderNo": order_no,
        "dataType": 1
    }

    print(f"请求参数:")
    print(f"  taxpayerId: {params['taxpayerId']}")
    print(f"  companyName: {params['companyName']}")
    print(f"  orderNo: {params['orderNo']}")
    print(f"  dataType: {params['dataType']}")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/invoice-penetration/report_data",
            headers=headers,
            params=params
        )

        print(f"\n请求: GET /api/invoice-penetration/report_data")
        print(f"状态码: {response.status_code}")

        result = response.json()
        print(f"响应 code: {result.get('code')}")
        print(f"响应 message: {result.get('message')}")

        if result.get("code") == 1:
            print_test("获取报告数据", "PASS", "成功获取报告数据")
            return True
        else:
            error_msg = result.get('message', '未知错误')
            print_test("获取报告数据", "FAIL", error_msg)

            # 说明可能的原因
            if '暂无该条记录' in error_msg:
                print(f"\n[提示] 这是预期行为:")
                print(f"  1. 需要用户先完成税局账号授权")
                print(f"  2. 等待查税宝生成报告")
                print(f"  3. 报告生成完成后才能获取数据")
            return False


async def test_notify_callback():
    """测试回调接口"""
    print_section("测试 4: 回调接口")

    notify_data = {
        "orderNo": f"test_{int(datetime.now().timestamp())}",
        "state": "1",
        "reportType": "1"
    }

    print(f"回调数据:")
    print(f"  orderNo: {notify_data['orderNo']}")
    print(f"  state: {notify_data['state']}")
    print(f"  reportType: {notify_data['reportType']}")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/invoice-penetration/notify/callback",
            json=notify_data
        )

        print(f"\n请求: POST /api/invoice-penetration/notify/callback")
        print(f"状态码: {response.status_code}")

        result = response.json()
        print(f"响应: {result}")

        # 检查是否需要认证
        if result.get("code") == "NO_TOKEN":
            print_test("回调接口", "FAIL", "接口需要认证 token（查税宝回调应该豁免）")
            return False
        elif result.get("code") == "0":
            print_test("回调接口", "PASS", "回调接口正常")
            return True
        else:
            print_test("回调接口", "FAIL", result.get('message'))
            return False


async def main():
    """主测试函数"""
    print("\n" + "🔹" * 30)
    print("  发票穿透报告接口测试")
    print("🔹" * 30)

    # 步骤 0: 登录
    token = await login()
    if not token:
        print("\n❌ 无法获取认证 token，测试终止")
        return

    # 测试 1: 获取配置
    await test_get_config(token)

    # 测试 2: 获取授权链接
    order_no = await test_get_authorization_url(token)

    # 测试 3: 获取报告数据
    await test_get_report_data(token, order_no)

    # 测试 4: 回调接口
    await test_notify_callback()

    # 打印测试总结
    print_section("测试总结")
    print(f"  通过: {test_results.get('passed', 0)}")
    print(f"  失败: {test_results.get('failed', 0)}")
    print(f"  跳过: {test_results.get('skipped', 0)}")

    total = sum(test_results.values())
    passed = test_results.get('passed', 0)
    print(f"\n  总计: {total} 测试，成功率: {passed/total*100:.1f}%" if total > 0 else "")

    print("\n" + "🔹" * 30)

    # 说明
    print("\n📝 说明:")
    print("  1. 本测试使用明文参数，后端会自动处理签名")
    print("  2. 测试数据纳税人识别号可能在查税宝测试环境中无效")
    print("  3. 如遇到 '非法参数' 错误，请联系查税宝获取有效测试数据")
    print("  4. 完整流程需要: 获取授权链接 → 用户授权 → 等待报告生成 → 获取数据")


if __name__ == "__main__":
    asyncio.run(main())
