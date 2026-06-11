"""
会员订阅功能端到端测试
测试会员套餐查询、订单创建、会员权益等功能
"""
import httpx
import json
import sys
from typing import Dict, Any, Optional

# 修复Windows控制台编码问题
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


class MemberE2ETest:
    """会员功能端到端测试"""

    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.client = httpx.Client(timeout=30.0)
        self.token = None
        self.user_id = None

    def print_result(self, title: str, success: bool, data: Any = None):
        """打印测试结果"""
        status = "[PASS]" if success else "[FAIL]"
        print(f"\n{status} - {title}")
        if data:
            print(f"响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")

    def test_register_and_login(self):
        """测试用户登录"""
        print("\n" + "="*60)
        print("测试1: 用户登录")
        print("="*60)

        # 尝试登录已有用户
        # 注意: 这里假设已经有一个测试用户存在
        # 如果需要创建新用户,需要通过管理后台或直接操作数据库

        # 使用默认测试用户
        login_data = {
            "username": "13800138000",  # 假设已存在的用户
            "password": "password123"
        }

        try:
            response = self.client.post(
                f"{self.base_url}/api/auth/login",
                json=login_data
            )
            result = response.json()

            if result.get("code") == 1:
                self.token = result.get("data", {}).get("access_token")
                self.user_id = result.get("data", {}).get("user_info", {}).get("user_id")
                self.print_result("用户登录", True, {"user_id": self.user_id})
            else:
                self.print_result("用户登录", False, result.get("message"))
                print("提示: 请确保数据库中存在测试用户 (13800138000 / password123)")
        except Exception as e:
            self.print_result("用户登录", False, str(e))
            print(f"登录异常: {e}")

        return self.token is not None

    def test_get_packages(self):
        """测试获取套餐列表"""
        print("\n" + "="*60)
        print("测试2: 获取会员套餐列表")
        print("="*60)

        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        response = self.client.get(
            f"{self.base_url}/api/member/packages",
            headers=headers
        )
        result = response.json()

        success = result.get("code") == 1
        self.print_result("获取套餐列表", success, result.get("data") if success else result.get("message"))

        return success

    def test_get_member_info(self):
        """测试获取会员信息"""
        print("\n" + "="*60)
        print("测试3: 获取用户会员信息")
        print("="*60)

        if not self.token:
            print("跳过: 未获取到token")
            return False

        headers = {"Authorization": f"Bearer {self.token}"}

        response = self.client.get(
            f"{self.base_url}/api/member/info",
            headers=headers
        )
        result = response.json()

        success = result.get("code") == 1
        self.print_result("获取会员信息", success, result.get("data") if success else result.get("message"))

        return success

    def test_create_order(self):
        """测试创建订单"""
        print("\n" + "="*60)
        print("测试4: 创建购买套餐订单")
        print("="*60)

        if not self.token:
            print("跳过: 未获取到token")
            return False

        headers = {"Authorization": f"Bearer {self.token}"}

        # 购买VIP月卡
        order_data = {
            "user_id": self.user_id,
            "package_id": "vip_month",
            "order_type": "subscription",
            "payment_method": "wechat"
        }

        response = self.client.post(
            f"{self.base_url}/api/member/orders",
            json=order_data,
            headers=headers
        )
        result = response.json()

        success = result.get("code") == 1
        self.print_result("创建订单", success, result.get("data") if success else result.get("message"))

        if success:
            order_id = result.get("data", {}).get("order_id")
            print(f"订单ID: {order_id}")
            return order_id
        return None

    def test_get_order(self, order_id: str):
        """测试获取订单详情"""
        print("\n" + "="*60)
        print("测试5: 获取订单详情")
        print("="*60)

        if not self.token or not order_id:
            print("跳过: 缺少必要参数")
            return False

        headers = {"Authorization": f"Bearer {self.token}"}

        response = self.client.get(
            f"{self.base_url}/api/member/orders/{order_id}",
            headers=headers
        )
        result = response.json()

        success = result.get("code") == 1
        self.print_result("获取订单详情", success, result.get("data") if success else result.get("message"))

        return success

    def test_complete_payment(self, order_id: str):
        """测试完成支付"""
        print("\n" + "="*60)
        print("测试6: 完成支付")
        print("="*60)

        if not self.token or not order_id:
            print("跳过: 缺少必要参数")
            return False

        headers = {"Authorization": f"Bearer {self.token}"}

        # 模拟支付
        payment_data = {
            "transaction_id": f"TXN{order_id[-10:]}"
        }

        response = self.client.post(
            f"{self.base_url}/api/member/orders/{order_id}/payment",
            params=payment_data,
            headers=headers
        )
        result = response.json()

        success = result.get("code") == 1
        self.print_result("完成支付", success, result.get("data") if success else result.get("message"))

        return success

    def test_list_orders(self):
        """测试获取订单列表"""
        print("\n" + "="*60)
        print("测试7: 获取用户订单列表")
        print("="*60)

        if not self.token:
            print("跳过: 未获取到token")
            return False

        headers = {"Authorization": f"Bearer {self.token}"}

        response = self.client.get(
            f"{self.base_url}/api/member/orders",
            headers=headers
        )
        result = response.json()

        success = result.get("code") == 1
        self.print_result("获取订单列表", success, result.get("data") if success else result.get("message"))

        return success

    def test_get_member_stats(self):
        """测试获取会员统计"""
        print("\n" + "="*60)
        print("测试8: 获取会员使用统计")
        print("="*60)

        if not self.token:
            print("跳过: 未获取到token")
            return False

        headers = {"Authorization": f"Bearer {self.token}"}

        response = self.client.get(
            f"{self.base_url}/api/member/stats",
            headers=headers
        )
        result = response.json()

        success = result.get("code") == 1
        self.print_result("获取会员统计", success, result.get("data") if success else result.get("message"))

        return success

    def test_check_privilege(self):
        """测试检查会员权益"""
        print("\n" + "="*60)
        print("测试9: 检查会员权益")
        print("="*60)

        if not self.token:
            print("跳过: 未获取到token")
            return False

        headers = {"Authorization": f"Bearer {self.token}"}

        # 检查RAG功能权益
        response = self.client.get(
            f"{self.base_url}/api/member/privileges/check",
            params={"privilege_type": "rag"},
            headers=headers
        )
        result = response.json()

        success = result.get("code") == 1
        self.print_result("检查RAG权益", success, result.get("data") if success else result.get("message"))

        return success

    def test_get_benefits(self):
        """测试获取会员权益列表"""
        print("\n" + "="*60)
        print("测试10: 获取所有会员权益")
        print("="*60)

        response = self.client.get(f"{self.base_url}/api/member/benefits")
        result = response.json()

        success = result.get("code") == 1
        self.print_result("获取会员权益列表", success, result.get("data") if success else result.get("message"))

        return success

    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "="*60)
        print("会员订阅功能端到端测试")
        print("="*60)

        results = []

        # 测试1: 登录
        results.append(("用户登录", self.test_register_and_login()))

        # 测试2: 获取套餐列表
        results.append(("获取套餐列表", self.test_get_packages()))

        # 测试3: 获取会员信息
        results.append(("获取会员信息", self.test_get_member_info()))

        # 测试4: 创建订单
        order_id = self.test_create_order()
        results.append(("创建订单", order_id is not None))

        # 测试5: 获取订单详情
        if order_id:
            results.append(("获取订单详情", self.test_get_order(order_id)))

            # 测试6: 完成支付
            results.append(("完成支付", self.test_complete_payment(order_id)))

        # 测试7: 获取订单列表
        results.append(("获取订单列表", self.test_list_orders()))

        # 测试8: 获取会员统计
        results.append(("获取会员统计", self.test_get_member_stats()))

        # 测试9: 检查会员权益
        results.append(("检查会员权益", self.test_check_privilege()))

        # 测试10: 获取权益列表
        results.append(("获取权益列表", self.test_get_benefits()))

        # 输出测试汇总
        print("\n" + "="*60)
        print("测试汇总")
        print("="*60)

        passed = sum(1 for _, success in results if success)
        total = len(results)

        for name, success in results:
            status = "[PASS]" if success else "[FAIL]"
            print(f"{status} - {name}")

        print(f"\n总计: {passed}/{total} 通过")

        return passed == total


if __name__ == "__main__":
    tester = MemberE2ETest()
    success = tester.run_all_tests()
    exit(0 if success else 1)
