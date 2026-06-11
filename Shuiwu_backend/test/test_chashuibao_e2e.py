"""
查税宝经营风险报告接口测试

运行前请确保：
1. 配置环境变量 CHASHUIBAO_BASE_URL、CHASHUIBAO_THIRD_PARTY_ID、CHASHUIBAO_PRIVATE_KEY
2. 服务已启动: python main.py
3. 安装依赖: pip install -r requirements.txt
"""
import asyncio
import httpx
import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

BASE_URL = "http://127.0.0.1:8000"
TEST_TOKEN = None  # 登录后获取的 token


async def login():
    """登录获取 token"""
    global TEST_TOKEN

    print("\n=== 测试登录 ===")
    async with httpx.AsyncClient() as client:
        # 使用时间戳生成唯一手机号，避免冲突
        import time
        timestamp = str(int(time.time()))[-6:]  # 取时间戳后6位
        username = f"1555555{timestamp}"  # 例如: 1555555123456
        password = "Test123456"

        print(f"使用手机号: {username}")

        # 注册新用户
        reg_response = await client.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "phone": username,
                "password": password,
                "sms_code": "123456",  # 短信验证码（服务层已注释验证，任意值即可）
            }
        )
        print(f"注册响应: status={reg_response.status_code}, {reg_response.text[:100]}")

        # 登录（使用手机号作为用户名）
        response = await client.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "username": username,  # 登录接口使用 username 字段，可以是手机号
                "password": password,
            }
        )

        print(f"登录响应: status={response.status_code}, {response.text[:200]}")

        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 1:
                TEST_TOKEN = data["data"]["access_token"]
                print(f"登录成功，token: {TEST_TOKEN[:20] if TEST_TOKEN else 'None'}...")
                return True
            else:
                print(f"登录失败: {data.get('message')}")
                return False
        else:
            print(f"登录请求失败: {response.status_code}")
            return False


async def test_get_config():
    """测试获取配置信息"""
    print("\n=== 测试获取配置信息 ===")

    headers = {"Authorization": f"Bearer {TEST_TOKEN}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/chashuibao/config",
            headers=headers
        )

        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")


async def test_get_authorization_url():
    """测试获取授权链接"""
    print("\n=== 测试获取授权链接 ===")

    headers = {"Authorization": f"Bearer {TEST_TOKEN}"}

    # 注意：taxpayerId 和 companyName 需要先使用 SM2 公钥加密
    # 这里仅作为示例，实际使用需要先加密
    request_data = {
        "thirdPartyId": "test_token",
        "sign": "test_signature",  # 实际需要使用 SM2 签名
        "taxpayerId": "encrypted_taxpayer_id",
        "companyName": "encrypted_company_name",
        "reportType": "2",
        "cburl": "https://example.com/callback",
        "year": "2024",
        "quarter": "1"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/chashuibao/authorization",
            headers=headers,
            json=request_data
        )

        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")


async def test_upload_report():
    """测试上传报表"""
    print("\n=== 测试上传报表 ===")

    headers = {"Authorization": f"Bearer {TEST_TOKEN}"}

    request_data = {
        "zzsFileBs": "0",
        "sdsFileBs": "0",
        "cbFileBs": "0",
        "zzs": "https://example.com/zzs.pdf",
        "sds": "https://example.com/sds.pdf",
        "cb": "https://example.com/cb.pdf",
        "firmName": "测试企业",
        "year": "2024",
        "quarter": "1",
        "phone": "13800138000",
        "taxpayerNo": "91330100MA2XXX00XX",
        "reportNo": "test_report_no_1234567890123456789012",
        "accountingCriterionId": "101",
        "taxpayerType": "Y",
        "taxpayerName": "测试企业",
        "thirdPartyId": "test_token",
        "sign": "test_signature"  # 实际需要使用 SM2 签名
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/chashuibao/upload_report",
            headers=headers,
            json=request_data
        )

        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")


async def test_get_report_data():
    """测试获取报告数据"""
    print("\n=== 测试获取报告数据 ===")

    headers = {"Authorization": f"Bearer {TEST_TOKEN}"}

    report_no = "test_report_no_1234567890123456789012"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/chashuibao/report_data",
            headers=headers,
            params={"report_no": report_no}
        )

        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")


async def test_notify_callback():
    """测试报告生成完成通知回调"""
    print("\n=== 测试报告生成完成通知回调 ===")

    notify_data = {
        "orderNo": "test_order_123",
        "state": "1",
        "reportType": "2"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/chashuibao/notify/callback",
            json=notify_data
        )

        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")


async def main():
    """主测试函数"""
    print("查税宝经营风险报告接口测试")

    # 先登录
    if not await login():
        print("登录失败，无法继续测试")
        return

    # 测试各接口
    await test_get_config()
    await test_get_authorization_url()
    await test_upload_report()
    await test_get_report_data()
    await test_notify_callback()

    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    asyncio.run(main())
