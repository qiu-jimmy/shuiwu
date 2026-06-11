"""
测试绑定邀请码接口

使用方法：
1. 确保后端服务已启动（python main.py）
2. 运行此测试脚本：python test/test_bind_invite_code.py
"""
import httpx
import json


# 配置
BASE_URL = "http://127.0.0.1:8000"
ADMIN_PHONE = "15555555555"
ADMIN_PASSWORD = "123456"


def print_result(title, response):
    """打印测试结果"""
    print(f"\n{'='*60}")
    print(f"测试: {title}")
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
    print('='*60)


def test_bind_invite_code():
    """测试绑定邀请码流程"""

    # 1. 管理员登录获取token
    print("\n步骤1: 管理员登录...")
    login_response = httpx.post(
        f"{BASE_URL}/api/auth/login",
        json={
            "username": ADMIN_PHONE,
            "password": ADMIN_PASSWORD
        }
    )
    print_result("管理员登录", login_response)

    if login_response.status_code != 200 or login_response.json().get("code") != 1:
        print("登录失败，请检查账号密码")
        return

    admin_token = login_response.json()["data"]["access_token"]
    admin_user_id = login_response.json()["data"]["user_info"]["user_id"]
    print(f"管理员ID: {admin_user_id}")

    # 2. 获取管理员的分销商信息（获取推广码）
    print("\n步骤2: 获取管理员的分销商信息...")
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 先尝试申请成为分销商（如果还不是）
    apply_response = httpx.post(
        f"{BASE_URL}/api/distribution/become-distributor",
        headers=headers
    )
    print_result("申请成为分销商", apply_response)

    # 获取分销商推广码
    distributor_response = httpx.get(
        f"{BASE_URL}/api/distribution/my-code",
        headers=headers
    )
    print_result("获取分销商推广码", distributor_response)

    if distributor_response.status_code == 200 and distributor_response.json().get("code") == 1:
        distributor_data = distributor_response.json()["data"]
        invite_code = distributor_data.get("distributor_code")
        print(f"\n推广邀请码: {invite_code}")
    else:
        print("获取分销商信息失败")
        return

    # 3. 创建一个新用户（测试用）
    print("\n步骤3: 创建测试用户...")
    test_phone = "13999999999"
    test_password = "test123456"

    # 先尝试注册
    register_response = httpx.post(
        f"{BASE_URL}/api/auth/register",
        json={
            "phone": test_phone,
            "password": test_password,
            "sms_code": "123456"  # 测试环境固定验证码
        }
    )
    print_result("注册测试用户", register_response)

    # 如果已存在，直接登录
    if register_response.status_code != 200 or register_response.json().get("code") != 1:
        print("用户可能已存在，尝试登录...")
        login_response = httpx.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "username": test_phone,
                "password": test_password
            }
        )
        print_result("测试用户登录", login_response)

        if login_response.status_code != 200 or login_response.json().get("code") != 1:
            print("测试用户登录失败")
            return

        test_token = login_response.json()["data"]["access_token"]
        test_user_id = login_response.json()["data"]["user_info"]["user_id"]
    else:
        test_token = register_response.json()["data"]["access_token"]
        test_user_id = register_response.json()["data"]["user_info"]["user_id"]

    print(f"测试用户ID: {test_user_id}")

    # 4. 测试绑定邀请码
    print("\n步骤4: 测试绑定邀请码...")
    test_headers = {"Authorization": f"Bearer {test_token}"}

    bind_response = httpx.post(
        f"{BASE_URL}/api/distribution/bind-invite-code",
        headers=test_headers,
        json={"invite_code": invite_code}
    )
    print_result("绑定邀请码", bind_response)

    # 5. 验证绑定结果（获取用户信息）
    print("\n步骤5: 验证绑定结果...")
    user_info_response = httpx.get(
        f"{BASE_URL}/api/auth/me",
        headers=test_headers
    )
    print_result("获取用户信息验证绑定", user_info_response)

    # 6. 测试重复绑定（应该失败）
    print("\n步骤6: 测试重复绑定（应该失败）...")
    bind_again_response = httpx.post(
        f"{BASE_URL}/api/distribution/bind-invite-code",
        headers=test_headers,
        json={"invite_code": invite_code}
    )
    print_result("重复绑定邀请码（预期失败）", bind_again_response)

    # 7. 测试无效邀请码
    print("\n步骤7: 测试无效邀请码...")

    # 创建另一个用户
    test_phone2 = "13888888888"
    httpx.post(
        f"{BASE_URL}/api/auth/register",
        json={
            "phone": test_phone2,
            "password": test_password,
            "sms_code": "123456"
        }
    )

    login_response2 = httpx.post(
        f"{BASE_URL}/api/auth/login",
        json={
            "username": test_phone2,
            "password": test_password
        }
    )

    if login_response2.status_code == 200:
        test_token2 = login_response2.json()["data"]["access_token"]
        invalid_bind_response = httpx.post(
            f"{BASE_URL}/api/distribution/bind-invite-code",
            headers={"Authorization": f"Bearer {test_token2}"},
            json={"invite_code": "INVALID"}
        )
        print_result("绑定无效邀请码（预期失败）", invalid_bind_response)

    print("\n" + "="*60)
    print("测试完成！")
    print("="*60)


if __name__ == "__main__":
    test_bind_invite_code()
