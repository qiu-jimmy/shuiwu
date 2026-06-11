"""
问题反馈系统端到端测试
"""
import httpx


# ==================== 配置 ====================
BASE_URL = "http://127.0.0.1:8000"

# 测试账号配置
TEST_USER = {
    "phone": "13800138000",
    "password": "123456"
}

TEST_ADMIN = {
    "phone": "15555555555",
    "password": "123456"
}


# ==================== 认证相关 ====================

def login(phone: str, password: str) -> dict:
    """登录获取用户信息和token"""
    print(f"\n>>> 登录: {phone}")

    url = f"{BASE_URL}/api/auth/login"

    payload = {
        "username": phone,  # 使用手机号作为用户名
        "password": password
    }

    response = httpx.post(url, json=payload)

    print(f"状态码: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        if data.get("code") == 1:
            user_info = data["data"]["user_info"]
            access_token = data["data"]["access_token"]
            print(f"✓ 登录成功: {user_info.get('nickname')} ({user_info.get('user_id')})")
            return {
                "user_id": user_info.get("user_id"),
                "access_token": access_token,
                "user_info": user_info
            }
        else:
            print(f"✗ 登录失败: {data.get('message')}")
            return None
    else:
        print(f"✗ 登录失败: HTTP {response.status_code}")
        return None


def setup_test_accounts():
    """设置测试账号"""
    print("\n" + "=" * 80)
    print("设置测试账号")
    print("=" * 80)

    # 登录管理员账号
    admin = login(TEST_ADMIN["phone"], TEST_ADMIN["password"])
    if not admin:
        print("\n❌ 管理员登录失败，请检查账号密码是否正确")
        print(f"   手机号: {TEST_ADMIN['phone']}")
        print(f"   密码: {TEST_ADMIN['password']}")
        return None, None

    # 登录普通用户账号
    user = login(TEST_USER["phone"], TEST_USER["password"])
    if not user:
        print(f"\n⚠️  普通用户登录失败，将使用管理员账号代替")
        user = admin

    print(f"\n✓ 测试账号准备完成")
    print(f"  管理员 ID: {admin['user_id']}")
    print(f"  用户 ID: {user['user_id']}")

    return admin, user


# ==================== 辅助函数 ====================

def check_response(response_data: dict) -> tuple:
    """检查响应是否成功，返回 (success, data)"""
    if response_data.get("code") == 1:
        return True, response_data.get("data", {})
    else:
        return False, None


def get_auth_headers(access_token: str) -> dict:
    """获取带认证的请求头"""
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }


# ==================== 用户端测试 ====================

def test_submit_feedback(access_token: str):
    """测试提交问题反馈"""
    print("\n>>> 测试提交问题反馈")

    url = f"{BASE_URL}/api/feedback/submit"

    payload = {
        "feedback_type": "bug",  # 问题类型
        "feedback_content": "测试反馈：发现登录页面在移动端显示异常，请尽快修复。",
        "feedback_images": None  # 可选
    }

    headers = get_auth_headers(access_token)

    response = httpx.post(url, json=payload, headers=headers)

    print(f"状态码: {response.status_code}")

    assert response.status_code == 200
    data = response.json()

    success, result_data = check_response(data)
    assert success, f"提交失败: {data.get('message')}"
    assert "feedback_id" in result_data, f"响应中缺少 feedback_id: {result_data}"

    print(f"✓ 反馈提交成功，ID: {result_data['feedback_id']}")
    return result_data["feedback_id"]


def test_get_my_feedbacks(access_token: str):
    """测试获取我的反馈列表"""
    print("\n>>> 测试获取我的反馈列表")

    url = f"{BASE_URL}/api/feedback/my?page=1&page_size=10"

    headers = get_auth_headers(access_token)

    response = httpx.get(url, headers=headers)

    print(f"状态码: {response.status_code}")

    assert response.status_code == 200
    data = response.json()

    success, result_data = check_response(data)
    assert success, f"获取失败: {data.get('message')}"

    print(f"✓ 反馈数量: {result_data.get('total', 0)}")


def test_get_feedback_detail(feedback_id: str, access_token: str):
    """测试获取反馈详情"""
    print("\n>>> 测试获取反馈详情")

    url = f"{BASE_URL}/api/feedback/{feedback_id}"

    headers = get_auth_headers(access_token)

    response = httpx.get(url, headers=headers)

    print(f"状态码: {response.status_code}")

    assert response.status_code == 200
    data = response.json()

    success, result_data = check_response(data)
    assert success, f"获取失败: {data.get('message')}"

    feedback = result_data.get("feedback", {})
    print(f"✓ 反馈类型: {feedback.get('feedback_type')}")
    print(f"  状态: {feedback.get('status')}")


# ==================== 管理员端测试 ====================

def test_admin_list_feedbacks(access_token: str):
    """测试管理员获取所有反馈列表"""
    print("\n>>> 测试管理员获取所有反馈列表")

    url = f"{BASE_URL}/api/admin/feedback/list?page=1&page_size=10"

    headers = get_auth_headers(access_token)

    response = httpx.get(url, headers=headers)

    print(f"状态码: {response.status_code}")

    assert response.status_code == 200
    data = response.json()

    success, result_data = check_response(data)
    assert success, f"获取失败: {data.get('message')}"

    print(f"✓ 反馈总数: {result_data.get('total', 0)}")


def test_admin_update_status(feedback_id: str, access_token: str):
    """测试管理员更新反馈状态"""
    print("\n>>> 测试管理员更新反馈状态")

    url = f"{BASE_URL}/api/admin/feedback/{feedback_id}/status"

    payload = {
        "status": "processing",  # 更新为处理中
        "priority": "high"       # 设置为高优先级
    }

    headers = get_auth_headers(access_token)

    response = httpx.put(url, json=payload, headers=headers)

    print(f"状态码: {response.status_code}")

    assert response.status_code == 200
    data = response.json()

    success, _ = check_response(data)
    assert success, f"更新失败: {data.get('message')}"

    print(f"✓ 状态已更新")


def test_admin_reply(feedback_id: str, access_token: str):
    """测试管理员回复反馈"""
    print("\n>>> 测试管理员回复反馈")

    url = f"{BASE_URL}/api/admin/feedback/{feedback_id}/reply"

    payload = {
        "admin_reply": "您好，感谢您的反馈！我们已收到您的问题，正在加紧处理中，预计本周内完成修复。"
    }

    headers = get_auth_headers(access_token)

    response = httpx.post(url, json=payload, headers=headers)

    print(f"状态码: {response.status_code}")

    assert response.status_code == 200
    data = response.json()

    success, _ = check_response(data)
    assert success, f"回复失败: {data.get('message')}"

    print(f"✓ 回复成功")


def test_admin_get_stats(access_token: str):
    """测试管理员获取统计信息"""
    print("\n>>> 测试管理员获取统计信息")

    url = f"{BASE_URL}/api/admin/feedback/stats/overview"

    headers = get_auth_headers(access_token)

    response = httpx.get(url, headers=headers)

    print(f"状态码: {response.status_code}")

    assert response.status_code == 200
    data = response.json()

    success, result_data = check_response(data)
    assert success, f"获取失败: {data.get('message')}"

    print(f"✓ 统计信息:")
    print(f"  待处理: {result_data.get('pending_count', 0)}")
    print(f"  处理中: {result_data.get('processing_count', 0)}")
    print(f"  已解决: {result_data.get('resolved_count', 0)}")
    print(f"  已关闭: {result_data.get('closed_count', 0)}")
    print(f"  紧急: {result_data.get('urgent_count', 0)}")


# ==================== 完整测试流程 ====================

def run_all_tests():
    """运行所有测试"""
    print("=" * 80)
    print("问题反馈系统端到端测试")
    print("=" * 80)

    # 设置测试账号
    admin, user = setup_test_accounts()
    if not admin:
        print("\n❌ 无法设置测试账号，测试终止")
        return False

    try:
        # 1. 提交反馈
        feedback_id = test_submit_feedback(
            access_token=user["access_token"]
        )

        # 2. 获取我的反馈列表
        test_get_my_feedbacks(
            access_token=user["access_token"]
        )

        # 3. 获取反馈详情
        test_get_feedback_detail(
            feedback_id=feedback_id,
            access_token=user["access_token"]
        )

        # 4. 管理员获取所有反馈列表
        test_admin_list_feedbacks(
            access_token=admin["access_token"]
        )

        # 5. 管理员更新状态
        test_admin_update_status(
            feedback_id=feedback_id,
            access_token=admin["access_token"]
        )

        # 6. 管理员回复
        test_admin_reply(
            feedback_id=feedback_id,
            access_token=admin["access_token"]
        )

        # 7. 管理员获取统计信息
        test_admin_get_stats(
            access_token=admin["access_token"]
        )

        print("\n" + "=" * 80)
        print("✅ 所有测试通过！")
        print("=" * 80)
        print(f"\n使用的管理员账号:")
        print(f"  手机号: {TEST_ADMIN['phone']}")
        print(f"  管理员ID: {admin['user_id']}")

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        return False
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    import sys

    # Windows 控制台编码修复
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    success = run_all_tests()
    sys.exit(0 if success else 1)
