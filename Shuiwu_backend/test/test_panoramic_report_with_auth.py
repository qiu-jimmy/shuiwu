"""
查税宝全景报告 API 端到端测试（带认证）

测试全景报告生成、数据获取等功能
"""
import httpx
import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# API 配置
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")
API_PREFIX = "/api/chashuibao"
AUTH_API_PREFIX = "/api/auth"

# 测试配置
TEST_USER = os.getenv("TEST_USER", "test@example.com")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "test123456")
TAXPAYER_NO = "91330382556157804A"  # 示例纳税人识别号
TAXPAYER_NAME = "乐清市琪源电气科技有限公司"  # 示例企业名称


async def login_and_get_token():
    """登录并获取认证 token"""
    print("\n" + "=" * 60)
    print("登录获取认证 Token")
    print("=" * 60)

    url = f"{BASE_URL}{AUTH_API_PREFIX}/login"
    headers = {"Content-Type": "application/json"}
    payload = {
        "username": TEST_USER,
        "password": TEST_PASSWORD
    }

    print(f"请求 URL: {url}")
    print(f"用户名: {TEST_USER}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)

        print(f"响应状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 1:
                token = data.get("data", {}).get("access_token")
                print(f"✅ 登录成功，获取到 token: {token[:20]}...")
                return token
            else:
                print(f"❌ 登录失败: {data.get('message')}")
                return None
        else:
            print(f"❌ HTTP 请求失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return None

    except Exception as e:
        print(f"❌ 登录异常: {e}")
        return None


async def register_and_login():
    """先注册用户，然后登录获取 token"""
    print("\n" + "=" * 60)
    print("注册新用户")
    print("=" * 60)

    # 生成随机手机号
    import random
    from datetime import datetime
    timestamp = str(int(datetime.now().timestamp()))[-6:]
    phone = f"1888888{timestamp}"
    password = "Test123456"

    # 注册
    print(f"尝试注册用户: {phone}")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            reg_response = await client.post(
                f"{BASE_URL}{AUTH_API_PREFIX}/register",
                json={
                    "phone": phone,
                    "password": password,
                    "sms_code": "123456",
                }
            )

        print(f"注册响应状态码: {reg_response.status_code}")

        if reg_response.status_code == 200:
            data = reg_response.json()
            if data.get("code") == 1:
                print(f"✅ 注册成功")
            else:
                print(f"⚠️  注册响应: {data.get('message')}")
    except Exception as e:
        print(f"⚠️  注册请求异常: {e}")

    # 登录
    print(f"尝试登录: {phone}")
    return await login_with_credentials(phone, password)


async def login_with_credentials(username, password):
    """使用指定凭据登录"""
    url = f"{BASE_URL}{AUTH_API_PREFIX}/login"
    headers = {"Content-Type": "application/json"}
    payload = {
        "username": username,
        "password": password
    }

    print(f"请求 URL: {url}")
    print(f"用户名: {username}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)

        print(f"响应状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 1:
                token = data.get("data", {}).get("access_token")
                print(f"✅ 登录成功，获取到 token: {token[:20] if token else 'None'}...")
                return token
            else:
                print(f"⚠️  登录失败: {data.get('message')}")
        else:
            print(f"⚠️  HTTP 请求失败: {response.status_code}")

        return None
    except Exception as e:
        print(f"❌ 登录异常: {e}")
        return None


async def test_generate_panoramic_report(token: str):
    """测试生成全景报告"""
    print("\n" + "=" * 60)
    print("测试 1: 生成全景报告")
    print("=" * 60)

    url = f"{BASE_URL}{API_PREFIX}/panoramic/generate"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    payload = {
        "taxpayerNo": TAXPAYER_NO,
        "taxpayerName": TAXPAYER_NAME,
        "reportLogo": "https://example.com/logo.png",
        "watermark": "https://example.com/watermark.png",
        "isAnonymity": 0
    }

    print(f"请求 URL: {url}")
    print(f"请求参数: {payload}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)

        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.text[:500]}...")  # 只显示前500字符

        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 1:
                result = data.get("data", {})
                report_record_id = result.get("id")
                report_id = result.get("report_id")
                print(f"✅ 生成全景报告请求成功，数据库记录ID: {report_record_id}，查税宝报告ID: {report_id}")
                return report_record_id
            else:
                print(f"❌ 生成全景报告失败: {data.get('message')}")
                return None
        else:
            print(f"❌ HTTP 请求失败: {response.status_code}")
            return None

    except Exception as e:
        print(f"❌ 请求异常: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_poll_report_status(report_record_id: int, token: str, max_attempts: int = 20):
    """测试轮询报告状态"""
    print("\n" + "=" * 60)
    print("测试 3: 轮询报告状态")
    print("=" * 60)

    if not report_record_id:
        print("⚠️  跳过测试：没有有效的 report_record_id")
        return

    url = f"{BASE_URL}{API_PREFIX}/panoramic/status/{report_record_id}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    print(f"开始轮询报告状态，记录ID: {report_record_id}")
    print(f"最大尝试次数: {max_attempts}，间隔 3 秒")

    for attempt in range(1, max_attempts + 1):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 1:
                    status_data = data.get("data", {})
                    status = status_data.get("status")
                    print(f"  轮询 {attempt}/{max_attempts}: 状态={status}, 报告URL={status_data.get('report_url')}")

                    if status == "success":
                        print(f"✅ 报告生成成功!")
                        print(f"   - 报告URL: {status_data.get('report_url')}")
                        print(f"   - 完成时间: {status_data.get('completed_at')}")
                        return status_data
                    elif status == "failed":
                        print(f"❌ 报告生成失败: {status_data.get('error_message')}")
                        return status_data
                    elif status == "pending":
                        # 继续轮询
                        pass
                else:
                    print(f"⚠️  获取状态失败: {data.get('message')}")
                    break
            else:
                print(f"⚠️  HTTP 请求失败: {response.status_code}")
                break

        except Exception as e:
            print(f"⚠️  轮询请求异常: {e}")

        # 等待 3 秒后重试
        if attempt < max_attempts:
            await asyncio.sleep(3)

    print("⚠️  轮询超时，报告可能仍在生成中")
    return None


async def test_get_panoramic_report_data(report_id: int, token: str):
    """测试获取全景报告数据"""
    print("\n" + "=" * 60)
    print("测试 2: 获取全景报告数据")
    print("=" * 60)

    if not report_id:
        print("⚠️  跳过测试：没有有效的 reportId")
        return

    url = f"{BASE_URL}{API_PREFIX}/panoramic/data"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    params = {
        "report_id": report_id
    }

    print(f"请求 URL: {url}")
    print(f"请求参数: report_id={report_id}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params, headers=headers)

        print(f"响应状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 1:
                report_data = data.get("data", {})
                print(f"✅ 获取全景报告数据成功")
                print(f"   - 综合评价: {report_data.get('evaluateSynthetical', 'N/A')}")
                print(f"   - 企业名称: {report_data.get('registerName', 'N/A')}")
                print(f"   - 法定代表人: {report_data.get('registerLegalPerson', 'N/A')}")
                print(f"   - 注册资本: {report_data.get('registerCapital', 'N/A')}")
                print(f"   - 股东数量: {len(report_data.get('shareholderList', []))}")
                print(f"   - 人员数量: {len(report_data.get('personnelList', []))}")
                print(f"   - 变更记录: {len(report_data.get('changeList', []))}")
                return report_data
            else:
                print(f"❌ 获取全景报告数据失败: {data.get('message')}")
                return None
        else:
            print(f"❌ HTTP 请求失败: {response.status_code}")
            return None

    except Exception as e:
        print(f"❌ 请求异常: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_panoramic_report_notify():
    """测试全景报告回调接口（无需认证）"""
    print("\n" + "=" * 60)
    print("测试 3: 全景报告回调接口（无需认证）")
    print("=" * 60)

    url = f"{BASE_URL}{API_PREFIX}/panoramic/notify"
    headers = {
        "Content-Type": "application/json",
    }

    payload = {
        "reportId": "123456",
        "state": "1",
        "reportType": "3",
        "url": "https://example.com/report.pdf"
    }

    print(f"请求 URL: {url}")
    print(f"请求参数: {payload}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)

        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.text}")

        if response.status_code == 200:
            data = response.json()
            if data.get("code") == "0":
                print(f"✅ 回调接口处理成功")
            else:
                print(f"❌ 回调接口处理失败: {data.get('message')}")
        else:
            print(f"❌ HTTP 请求失败: {response.status_code}")

    except Exception as e:
        print(f"❌ 请求异常: {e}")


async def test_get_config(token: str):
    """测试获取查税宝配置"""
    print("\n" + "=" * 60)
    print("测试 4: 获取查税宝配置")
    print("=" * 60)

    url = f"{BASE_URL}{API_PREFIX}/config"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    print(f"请求 URL: {url}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)

        print(f"响应状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 1:
                config = data.get("data", {})
                print(f"✅ 获取配置成功")
                print(f"   - Base URL: {config.get('baseUrl', 'N/A')}")
                print(f"   - Third Party ID: {config.get('thirdPartyId', 'N/A')[:20]}...")
            else:
                print(f"❌ 获取配置失败: {data.get('message')}")
        else:
            print(f"❌ HTTP 请求失败: {response.status_code}")

    except Exception as e:
        print(f"❌ 请求异常: {e}")


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("查税宝全景报告 API 测试（带认证）")
    print("=" * 60)
    print(f"测试服务器: {BASE_URL}")

    # 检查环境变量
    required_env_vars = [
        "CHASHUIBAO_BASE_URL",
        "CHASHUIBAO_THIRD_PARTY_ID",
        "CHASHUIBAO_PRIVATE_KEY"
    ]

    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        print(f"\n⚠️  警告: 缺少环境变量: {', '.join(missing_vars)}")
        print("请确保在 .env 文件中配置了所有必需的环境变量")

    # 获取认证 token
    token = None

    # 尝试使用环境变量中的用户登录
    if os.getenv("TEST_USER") and os.getenv("TEST_PASSWORD"):
        print("\n尝试使用环境变量中的用户登录...")
        token = await login_with_credentials(
            os.getenv("TEST_USER"),
            os.getenv("TEST_PASSWORD")
        )

    # 如果失败，注册新用户
    if not token:
        print("\n尝试注册新用户并登录...")
        token = await register_and_login()

    if not token:
        print("\n❌ 无法获取认证 token，跳过需要认证的测试")
        print("仅测试无需认证的接口...")
        await test_panoramic_report_notify()
        return

    # 运行测试
    try:
        # 测试 1: 生成全景报告
        report_record_id = await test_generate_panoramic_report(token)

        # 测试 2: 轮询报告状态（如果有 report_record_id）
        if report_record_id:
            await test_poll_report_status(report_record_id, token, max_attempts=10)

        # 测试 3: 回调接口（无需认证）
        await test_panoramic_report_notify()

        # 测试 4: 获取配置
        await test_get_config(token)

    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    # 修复 Windows 控制台输出编码问题
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    asyncio.run(main())
