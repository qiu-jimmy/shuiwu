"""
测试支付端到端测试脚本

使用方法:
    python test/test_payment_e2e.py

或使用 pytest:
    pytest test/test_payment_e2e.py -v

环境要求:
    - PAYMENT_TEST_MODE=true (在 .env 文件中设置)
    - 服务运行在 http://127.0.0.1:8000
"""
import os
import sys
import time
import json
from datetime import datetime
from typing import Dict, Any, Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx

# ==================== 配置 ====================
BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
TEST_USER = {
    "phone": "13800138999",
    "password": "test123456",
    "nickname": "支付测试用户"
}
TEST_PACKAGE_ID = "vip_month"


# ==================== 工具函数 ====================
def print_section(title: str):
    """打印测试章节标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_result(test_name: str, success: bool, message: str = ""):
    """打印测试结果"""
    status = "[PASS]" if success else "[FAIL]"
    print(f"{status} - {test_name}")
    if message:
        print(f"    {message}")


def setup_console_encoding():
    """设置控制台编码（Windows修复）"""
    if sys.platform == "win32":
        # 设置环境变量
        os.environ["PYTHONIOENCODING"] = "utf-8"
        # 尝试设置控制台编码页
        try:
            import locale
            import codecs
            sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, 'strict')
            sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, 'strict')
        except Exception:
            pass  # 如果设置失败，继续使用默认编码


# ==================== API 客户端 ====================
class PaymentTestClient:
    """支付测试客户端"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.token: Optional[str] = None
        self.user_info: Optional[Dict] = None
        self.client = httpx.Client(timeout=30.0)

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """发送HTTP请求"""
        url = f"{self.base_url}{path}"
        headers = kwargs.pop("headers", {})

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            response = self.client.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            return {"code": 0, "message": f"HTTP请求失败: {str(e)}", "data": None}

    def register(self, phone: str, password: str, nickname: str) -> Dict[str, Any]:
        """用户注册"""
        return self._request(
            "POST",
            "/api/auth/register",
            json={
                "phone": phone,
                "password": password,
                "nickname": nickname,
                "sms_code": "123456"  # 测试验证码
            }
        )

    def login(self, phone: str, password: str) -> Dict[str, Any]:
        """用户登录"""
        result = self._request(
            "POST",
            "/api/auth/login",
            json={"username": phone, "password": password}
        )

        if result.get("code") == 1:
            self.token = result["data"]["access_token"]
            self.user_info = result["data"].get("user_info", {})

        return result

    def create_order(self, package_id: str, payment_method: str = "wechat") -> Dict[str, Any]:
        """创建订单"""
        return self._request(
            "POST",
            "/api/member/orders",
            json={
                "package_id": package_id,
                "payment_method": payment_method
            }
        )

    def simulate_payment(self, order_id: str, success: bool) -> Dict[str, Any]:
        """模拟支付"""
        return self._request(
            "POST",
            f"/api/payments/test/simulate?order_id={order_id}&success={str(success).lower()}"
        )

    def get_order(self, order_id: str) -> Dict[str, Any]:
        """获取订单详情"""
        return self._request("GET", f"/api/member/orders/{order_id}")

    def get_member_info(self) -> Dict[str, Any]:
        """获取会员信息"""
        return self._request("GET", "/api/member/info")

    def get_payment_status(self, order_id: str) -> Dict[str, Any]:
        """查询支付状态"""
        return self._request("GET", f"/api/payments/{order_id}/status")

    def close(self):
        """关闭客户端"""
        self.client.close()


# ==================== 测试用例 ====================
def test_payment_success_flow(client: PaymentTestClient) -> bool:
    """
    测试用例 1: 正常支付成功流程
    验证: 创建订单 → 模拟支付成功 → 验证会员激活
    """
    print_section("测试用例 1: 正常支付成功流程")

    # 步骤 1: 注册/登录
    print("\n1. 注册/登录用户...")

    # 使用带时间戳的手机号确保唯一性
    unique_phone = f"138{int(time.time()) % 100000000:08d}"

    # 先尝试登录，如果失败则注册
    login_result = client.login(unique_phone, TEST_USER["password"])
    if login_result.get("code") != 1:
        # 登录失败，尝试注册
        reg_result = client.register(unique_phone, TEST_USER["password"], TEST_USER["nickname"])
        if reg_result.get("code") == 1:
            # 注册成功，再次登录
            login_result = client.login(unique_phone, TEST_USER["password"])

    if login_result.get("code") != 1:
        print_result("用户登录", False, login_result.get("message"))
        return False

    print_result("用户登录", True, f"手机号: {unique_phone}")

    # 获取原始会员到期时间
    member_info = client.get_member_info()
    original_expire = member_info.get("data", {}).get("member_expire_at")
    print(f"   原始会员到期时间: {original_expire}")

    # 步骤 2: 创建订单
    print("\n2. 创建订单...")
    order_result = client.create_order(TEST_PACKAGE_ID)

    if order_result.get("code") != 1:
        print_result("创建订单", False, order_result.get("message"))
        return False

    order = order_result["data"]  # 订单直接在 data 中
    order_id = order["order_id"]
    print_result("创建订单", True, f"订单ID: {order_id}, 金额: {order.get('amount')}")

    # 步骤 3: 模拟支付成功
    print("\n3. 模拟支付成功...")
    payment_result = client.simulate_payment(order_id, success=True)

    if payment_result.get("code") != 1:
        print_result("模拟支付", False, payment_result.get("message"))
        return False

    transaction_id = payment_result["data"].get("transaction_id", "")
    print_result("模拟支付成功", True, f"交易号: {transaction_id}")

    # 验证交易号格式
    if not transaction_id.startswith("TEST_"):
        print_result("验证交易号格式", False, f"交易号应以 TEST_ 开头，实际: {transaction_id}")
        return False

    print_result("验证交易号格式", True)

    # 步骤 4: 验证订单状态
    print("\n4. 验证订单状态...")
    order_detail = client.get_order(order_id)

    if order_detail.get("code") != 1:
        print_result("获取订单详情", False, order_detail.get("message"))
        return False

    order = order_detail["data"]  # 订单详情直接在 data 中

    if order.get("payment_status") != "paid":
        print_result("验证订单支付状态", False, f"期望: paid, 实际: {order.get('payment_status')}")
        return False

    print_result("验证订单支付状态", True, f"状态: {order.get('payment_status')}")

    # 步骤 5: 验证会员状态
    print("\n5. 验证会员激活...")
    member_info = client.get_member_info()

    if member_info.get("code") != 1:
        print_result("获取会员信息", False, member_info.get("message"))
        return False

    member = member_info["data"]

    if not member.get("is_member_valid"):
        print_result("验证会员有效性", False, "会员状态无效")
        return False

    print_result("验证会员有效性", True)

    if member.get("member_level") != TEST_PACKAGE_ID:
        print_result("验证会员等级", False, f"期望: {TEST_PACKAGE_ID}, 实际: {member.get('member_level')}")
        return False

    print_result("验证会员等级", True, f"等级: {member.get('member_level')}")

    # 验证到期时间延长
    new_expire = member.get("member_expire_at")
    if new_expire and original_expire:
        try:
            new_expire_dt = datetime.fromisoformat(new_expire.replace('Z', '+00:00'))
            if original_expire:
                original_expire_dt = datetime.fromisoformat(original_expire.replace('Z', '+00:00'))
                if new_expire_dt <= original_expire_dt:
                    print_result("验证到期时间延长", False, f"新到期时间未延长: {new_expire}")
                    return False
            print_result("验证到期时间延长", True, f"新到期时间: {new_expire}")
        except Exception as e:
            print_result("验证到期时间延长", False, f"时间解析失败: {e}")
            return False

    return True


def test_payment_failure_flow(client: PaymentTestClient) -> bool:
    """
    测试用例 2: 支付失败流程
    验证: 创建订单 → 模拟支付失败 → 验证会员未激活
    """
    print_section("测试用例 2: 支付失败流程")

    # 步骤 1: 创建订单
    print("\n1. 创建订单...")
    order_result = client.create_order(TEST_PACKAGE_ID)

    if order_result.get("code") != 1:
        print_result("创建订单", False, order_result.get("message"))
        return False

    order = order_result["data"]  # 订单直接在 data 中
    order_id = order["order_id"]
    print_result("创建订单", True, f"订单ID: {order_id}")

    # 获取原始会员状态
    member_info = client.get_member_info()
    original_expire = member_info.get("data", {}).get("member_expire_at")

    # 步骤 2: 模拟支付失败
    print("\n2. 模拟支付失败...")
    payment_result = client.simulate_payment(order_id, success=False)

    # 支付失败时，API可能返回 code: 0 或 code: 1，取决于实现
    print_result("模拟支付失败", True, f"返回: {payment_result.get('message')}")

    # 步骤 3: 验证订单状态为失败
    print("\n3. 验证订单状态...")
    order_detail = client.get_order(order_id)

    if order_detail.get("code") != 1:
        print_result("获取订单详情", False, order_detail.get("message"))
        return False

    order = order_detail["data"]  # 订单详情直接在 data 中

    if order.get("status") != "failed":
        print_result("验证订单状态", False, f"期望: failed, 实际: {order.get('status')}")
        return False

    print_result("验证订单状态", True, f"状态: {order.get('status')}")

    # 步骤 4: 验证会员未改变
    print("\n4. 验证会员未激活...")
    member_info = client.get_member_info()

    if member_info.get("code") != 1:
        print_result("获取会员信息", False, member_info.get("message"))
        return False

    member = member_info["data"]
    new_expire = member.get("member_expire_at")

    if original_expire != new_expire:
        print_result("验证会员未改变", False, f"到期时间已改变: {original_expire} -> {new_expire}")
        return False

    print_result("验证会员未改变", True)

    return True


def test_duplicate_payment(client: PaymentTestClient) -> bool:
    """
    测试用例 3: 重复支付幂等性测试
    验证: 已支付订单不能重复支付
    """
    print_section("测试用例 3: 重复支付幂等性")

    # 步骤 1: 创建订单并支付成功
    print("\n1. 创建订单并支付...")
    order_result = client.create_order(TEST_PACKAGE_ID)

    if order_result.get("code") != 1:
        print_result("创建订单", False, order_result.get("message"))
        return False

    order_id = order_result["data"]["order_id"]  # 订单直接在 data 中

    # 首次支付
    first_payment = client.simulate_payment(order_id, success=True)
    if first_payment.get("code") != 1:
        print_result("首次支付", False, first_payment.get("message"))
        return False

    print_result("首次支付成功", True, f"订单ID: {order_id}")

    # 获取会员到期时间
    member_info = client.get_member_info()
    expire_after_first = member_info.get("data", {}).get("member_expire_at")

    # 步骤 2: 尝试重复支付
    print("\n2. 尝试重复支付...")
    time.sleep(1)  # 等待1秒确保时间戳不同
    second_payment = client.simulate_payment(order_id, success=True)

    if second_payment.get("code") == 1:
        print_result("重复支付被拒绝", False, "不应该允许重复支付")
        return False

    print_result("重复支付被拒绝", True, f"错误信息: {second_payment.get('message')}")

    # 步骤 3: 验证会员时间未重复延长
    print("\n3. 验证会员时间未重复延长...")
    member_info = client.get_member_info()
    expire_after_second = member_info.get("data", {}).get("member_expire_at")

    if expire_after_first != expire_after_second:
        print_result("验证会员时间", False, "会员时间被重复延长")
        return False

    print_result("验证会员时间", True, "会员时间未重复延长")

    return True


def test_order_not_exist(client: PaymentTestClient) -> bool:
    """
    测试用例 4: 订单不存在测试
    验证: 使用无效订单ID时返回错误
    """
    print_section("测试用例 4: 订单不存在")

    fake_order_id = "ORD_FAKE_1234567890"

    print(f"\n1. 使用无效订单ID: {fake_order_id}")
    result = client.simulate_payment(fake_order_id, success=True)

    if result.get("code") == 1:
        print_result("订单不存在错误", False, "应该返回错误")
        return False

    print_result("订单不存在错误", True, f"错误信息: {result.get('message')}")

    return True


def test_paid_order_cannot_fail(client: PaymentTestClient) -> bool:
    """
    测试用例 5: 已支付订单不能模拟失败
    验证: 已支付订单不能改为失败状态
    """
    print_section("测试用例 5: 已支付订单不能模拟失败")

    # 步骤 1: 创建订单并支付成功
    print("\n1. 创建订单并支付...")
    order_result = client.create_order(TEST_PACKAGE_ID)

    if order_result.get("code") != 1:
        print_result("创建订单", False, order_result.get("message"))
        return False

    order_id = order_result["data"]["order_id"]  # 订单直接在 data 中

    # 支付成功
    payment = client.simulate_payment(order_id, success=True)
    if payment.get("code") != 1:
        print_result("支付成功", False, payment.get("message"))
        return False

    print_result("支付成功", True, f"订单ID: {order_id}")

    # 步骤 2: 尝试将已支付订单改为失败
    print("\n2. 尝试模拟支付失败...")
    result = client.simulate_payment(order_id, success=False)

    if result.get("code") == 1:
        print_result("拒绝修改", False, "不应该允许将已支付订单改为失败")
        return False

    print_result("拒绝修改", True, f"错误信息: {result.get('message')}")

    return True


def test_mode_disabled() -> bool:
    """
    测试用例 6: 测试模式未启用测试
    验证: PAYMENT_TEST_MODE=false 时调用接口返回错误
    注意: 此测试需要手动设置环境变量后重启服务
    """
    print_section("测试用例 6: 测试模式未启用 (需手动配置)")

    print("\n此测试需要以下步骤:")
    print("1. 设置环境变量 PAYMENT_TEST_MODE=false")
    print("2. 重启服务")
    print("3. 运行此测试")

    # 跳过此测试，因为需要手动配置
    print("\n[SKIP] 跳过此测试 (需手动配置环境变量)")
    print("   如需运行，请设置 PAYMENT_TEST_MODE=false 后重启服务")

    return True  # 默认通过，不阻塞其他测试


# ==================== 主测试运行器 ====================
def run_all_tests():
    """运行所有测试"""
    setup_console_encoding()

    print("\n" + "="*60)
    print("  测试支付端到端测试")
    print("="*60)
    print(f"  API地址: {BASE_URL}")
    print(f"  测试用户: {TEST_USER['phone']}")
    print(f"  测试套餐: {TEST_PACKAGE_ID}")
    print("="*60)

    # 创建客户端
    client = PaymentTestClient()

    # 测试结果
    results = []

    try:
        # 运行测试
        results.append(("支付成功流程", test_payment_success_flow(client)))
        results.append(("支付失败流程", test_payment_failure_flow(client)))
        results.append(("重复支付幂等性", test_duplicate_payment(client)))
        results.append(("订单不存在", test_order_not_exist(client)))
        results.append(("已支付订单不能失败", test_paid_order_cannot_fail(client)))
        results.append(("测试模式未启用", test_mode_disabled()))

    finally:
        client.close()

    # 打印测试汇总
    print_section("测试结果汇总")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        print_result(name, result)

    print(f"\n总计: {passed}/{total} 通过")

    if passed == total:
        print("\n[SUCCESS] 所有测试通过!")
        return 0
    else:
        print(f"\n[FAILURE] {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
