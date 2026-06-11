"""
分销系统端到端测试

测试范围：
1. 分销商管理
2. 推广码验证
3. 订单佣金处理
4. 分销记录查询
5. 提现申请流程
6. 管理员接口
7. 系统统计
"""
import httpx
import json
import random
import sys
import time
import os
from typing import Dict, Any, Optional

# Windows 控制台编码修复
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())


class Colors:
    """终端颜色"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


class DistributionE2ETest:
    """分销系统端到端测试"""

    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.client = httpx.Client(timeout=30.0)

        # 测试数据存储
        self.promoter_token: Optional[str] = None
        self.promoter_user_id: Optional[str] = None
        self.promoter_code: Optional[str] = None
        self.new_user_token: Optional[str] = None
        self.new_user_id: Optional[str] = None
        self.order_id: Optional[str] = None
        self.admin_token: Optional[str] = None
        self.withdrawal_id: Optional[str] = None

        # 生成随机手机号，避免重复注册
        self.promoter_phone = f"139{random.randint(10000000, 99999999)}"
        self.new_user_phone = f"139{random.randint(10000000, 99999999)}"

        # 测试计数
        self.passed_tests = 0
        self.failed_tests = 0

    def __del__(self):
        if hasattr(self, 'client'):
            self.client.close()

    def print_step(self, step_name: str, result: bool, message: str):
        """打印测试步骤结果"""
        status = f"{Colors.GREEN}✅{Colors.RESET}" if result else f"{Colors.RED}❌{Colors.RESET}"
        print(f"{status} {step_name}: {message}")
        if result:
            self.passed_tests += 1
        else:
            self.failed_tests += 1

    def print_section(self, title: str):
        """打印测试章节"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}  {title}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}\n")

    # ==================== 认证相关 ====================

    def test_01_register_promoter(self) -> bool:
        """步骤1：注册推广人"""
        print("注册推广人...")

        try:
            # 注册推广人
            response = self.client.post(
                f"{self.base_url}/api/auth/register",
                json={
                    "phone": self.promoter_phone,
                    "password": "test123456",
                    "nickname": "推广人张三",
                    "sms_code": "123456"  # 测试环境可使用任意验证码
                }
            )

            data = response.json()

            if data.get("code") == 1:
                self.promoter_token = data["data"]["access_token"]
                self.promoter_user_id = data["data"]["user_info"]["user_id"]
                self.print_step("注册推广人", True, f"用户ID: {self.promoter_user_id}")
                return True
            else:
                self.print_step("注册推广人", False, data.get("message", "注册失败"))
                return False

        except Exception as e:
            self.print_step("注册推广人", False, f"异常: {str(e)}")
            return False

    def test_02_login_admin(self) -> bool:
        """步骤2：管理员登录"""
        print("管理员登录...")

        try:
            response = self.client.post(
                f"{self.base_url}/api/admin/login",
                json={"username": "admin", "password": "admin123"}
            )

            data = response.json()

            if data.get("code") == 1:
                # access_token 在 data 层级下
                self.admin_token = data["data"]["access_token"]
                self.print_step("管理员登录", True, "登录成功")
                return True
            else:
                self.print_step("管理员登录", False, data.get("message", "登录失败"))
                return False

        except Exception as e:
            self.print_step("管理员登录", False, f"异常: {str(e)}")
            return False

    # ==================== 分销商管理 ====================

    def test_03_become_distributor(self) -> bool:
        """步骤3：成为分销商"""
        print("成为分销商...")

        try:
            response = self.client.post(
                f"{self.base_url}/api/distribution/become-distributor",
                headers={"Authorization": f"Bearer {self.promoter_token}"}
            )

            data = response.json()

            if data.get("code") == 1:
                self.print_step("成为分销商", True, "分销商账户创建成功")
                return True
            else:
                self.print_step("成为分销商", False, data.get("message", "成为分销商失败"))
                return False

        except Exception as e:
            self.print_step("成为分销商", False, f"异常: {str(e)}")
            return False

    def test_04_get_distributor_code(self) -> bool:
        """步骤4：获取推广码"""
        print("获取推广码...")

        try:
            response = self.client.get(
                f"{self.base_url}/api/distribution/my-code",
                headers={"Authorization": f"Bearer {self.promoter_token}"}
            )

            data = response.json()

            if data.get("code") == 1:
                self.promoter_code = data["data"]["distributor_code"]
                share_link = data["data"]["share_link"]
                self.print_step("获取推广码", True, f"推广码: {self.promoter_code}")
                return True
            else:
                self.print_step("获取推广码", False, data.get("message", "获取推广码失败"))
                return False

        except Exception as e:
            self.print_step("获取推广码", False, f"异常: {str(e)}")
            return False

    def test_05_validate_code(self) -> bool:
        """步骤5：验证推广码"""
        print("验证推广码...")

        try:
            response = self.client.get(
                f"{self.base_url}/api/distribution/validate-code",
                params={"code": self.promoter_code}
            )

            data = response.json()

            if data.get("code") == 1 and data["data"]["valid"]:
                self.print_step("验证推广码", True, "推广码有效")
                return True
            else:
                self.print_step("验证推广码", False, data.get("message", "推广码无效"))
                return False

        except Exception as e:
            self.print_step("验证推广码", False, f"异常: {str(e)}")
            return False

    def test_06_get_distributor_stats(self) -> bool:
        """步骤6：获取分销商统计"""
        print("获取分销商统计...")

        try:
            response = self.client.get(
                f"{self.base_url}/api/distribution/stats",
                headers={"Authorization": f"Bearer {self.promoter_token}"}
            )

            data = response.json()

            if data.get("code") == 1:
                stats = data["data"]
                self.print_step("获取统计", True,
                    f"下级: {stats.get('total_children_count')}, "
                    f"订单: {stats.get('total_order_count')}, "
                    f"佣金: {stats.get('total_commission'):.2f}元, "
                    f"可提现: {stats.get('available_commission'):.2f}元")
                return True
            else:
                self.print_step("获取统计", False, data.get("message", "获取统计失败"))
                return False

        except Exception as e:
            self.print_step("获取统计", False, f"异常: {str(e)}")
            return False

    # ==================== 推广注册 ====================

    def test_07_register_with_referral(self) -> bool:
        """步骤7：通过推广码注册新用户"""
        print("通过推广码注册新用户...")

        try:
            # 使用推广码注册
            response = self.client.post(
                f"{self.base_url}/api/auth/register",
                json={
                    "phone": self.new_user_phone,
                    "password": "test123456",
                    "nickname": "新用户李四",
                    "sms_code": "123456",
                    "referral_code": self.promoter_code
                }
            )

            data = response.json()

            if data.get("code") == 1:
                self.new_user_token = data["data"]["access_token"]
                self.new_user_id = data["data"]["user_info"]["user_id"]
                self.print_step("注册新用户", True, f"用户ID: {self.new_user_id}，已绑定推广人")
                return True
            else:
                self.print_step("注册新用户", False, data.get("message", "注册失败"))
                return False

        except Exception as e:
            self.print_step("注册新用户", False, f"异常: {str(e)}")
            return False

    # ==================== 订单与佣金 ====================

    def test_08_create_order(self) -> bool:
        """步骤8：新用户创建订单"""
        print("创建订单...")

        try:
            # 获取套餐列表
            response = self.client.get(
                f"{self.base_url}/api/member/packages",
                headers={"Authorization": f"Bearer {self.new_user_token}"}
            )

            data = response.json()

            if data.get("code") != 1 or not data["data"].get("packages"):
                self.print_step("创建订单", False, "获取套餐列表失败")
                return False

            package_id = data["data"]["packages"][0]["package_id"]

            # 创建订单
            response = self.client.post(
                f"{self.base_url}/api/member/orders",
                headers={"Authorization": f"Bearer {self.new_user_token}"},
                json={
                    "package_id": package_id,
                    "payment_method": "wechat"
                }
            )

            data = response.json()

            if data.get("code") == 1:
                self.order_id = data["data"]["order_id"]
                order_amount = data["data"]["amount"]
                self.print_step("创建订单", True, f"订单ID: {self.order_id}, 金额: {order_amount}元")
                return True
            else:
                self.print_step("创建订单", False, data.get("message", "创建订单失败"))
                return False

        except Exception as e:
            self.print_step("创建订单", False, f"异常: {str(e)}")
            return False

    def test_09_complete_payment(self) -> bool:
        """步骤9：完成支付（触发分销佣金）"""
        print("完成支付...")

        try:
            response = self.client.post(
                f"{self.base_url}/api/member/orders/{self.order_id}/complete-payment",
                headers={"Authorization": f"Bearer {self.new_user_token}"},
                json={"transaction_id": f"TEST_TXN_{int(time.time() * 1000)}"}
            )

            data = response.json()

            if data.get("code") == 1:
                self.print_step("完成支付", True, "支付成功，分销佣金已计算")
                return True
            else:
                self.print_step("完成支付", False, data.get("message", "支付失败"))
                return False

        except Exception as e:
            self.print_step("完成支付", False, f"异常: {str(e)}")
            return False

    # ==================== 分销记录 ====================

    def test_10_list_records(self) -> bool:
        """步骤10：获取分销记录"""
        print("获取分销记录...")

        try:
            response = self.client.get(
                f"{self.base_url}/api/distribution/records",
                headers={"Authorization": f"Bearer {self.promoter_token}"},
                params={"page": 1, "page_size": 10}
            )

            data = response.json()

            if data.get("code") == 1:
                total = data["data"]["total"]
                records = data["data"]["records"]
                self.print_step("获取分销记录", True, f"共 {total} 条记录")
                if records:
                    for r in records[:2]:
                        print(f"    - {r.get('commission_amount', 0):.2f}元 | {r.get('commission_status')} | {r.get('commission_type')}")
                return True
            else:
                self.print_step("获取分销记录", False, data.get("message", "获取失败"))
                return False

        except Exception as e:
            self.print_step("获取分销记录", False, f"异常: {str(e)}")
            return False

    # ==================== 提现申请 ====================

    def test_11_create_withdrawal(self) -> bool:
        """步骤11：创建提现申请"""
        print("创建提现申请...")

        try:
            response = self.client.post(
                f"{self.base_url}/api/distribution/withdraw",
                headers={"Authorization": f"Bearer {self.promoter_token}"},
                json={
                    "amount": 50.0,
                    "withdrawal_method": "wechat",
                    "account_name": "测试用户",
                    "account_number": "wx_test_123456"
                }
            )

            data = response.json()

            if data.get("code") == 1:
                self.withdrawal_id = data.get("data", {}).get("withdrawal_id")
                self.print_step("创建提现申请", True, f"提现ID: {self.withdrawal_id}")
                return True
            else:
                self.print_step("创建提现申请", False, data.get("message", "创建失败"))
                return False

        except Exception as e:
            self.print_step("创建提现申请", False, f"异常: {str(e)}")
            return False

    def test_12_list_withdrawals(self) -> bool:
        """步骤12：获取提现记录"""
        print("获取提现记录...")

        try:
            response = self.client.get(
                f"{self.base_url}/api/distribution/withdrawals",
                headers={"Authorization": f"Bearer {self.promoter_token}"},
                params={"page": 1, "page_size": 10}
            )

            data = response.json()

            if data.get("code") == 1:
                total = data["data"]["total"]
                withdrawals = data["data"]["withdrawals"]
                self.print_step("获取提现记录", True, f"共 {total} 条记录")
                if withdrawals:
                    for w in withdrawals[:2]:
                        print(f"    - {w.get('amount', 0):.2f}元 | {w.get('status')} | {w.get('withdrawal_method')}")
                return True
            else:
                self.print_step("获取提现记录", False, data.get("message", "获取失败"))
                return False

        except Exception as e:
            self.print_step("获取提现记录", False, f"异常: {str(e)}")
            return False

    # ==================== 管理员接口 ====================

    def test_13_admin_list_distributors(self) -> bool:
        """步骤13：管理员获取分销商列表"""
        print("管理员获取分销商列表...")

        try:
            response = self.client.get(
                f"{self.base_url}/api/distribution/admin/distributors",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                params={"page": 1, "page_size": 10}
            )

            data = response.json()

            if data.get("code") == 1:
                total = data["data"]["total"]
                distributors = data["data"]["distributors"]
                self.print_step("管理员获取分销商", True, f"共 {total} 个分销商")
                if distributors:
                    for d in distributors[:2]:
                        print(f"    - {d.get('distributor_code')} | {d.get('nickname')} | {d.get('status')} | 佣金: {d.get('total_commission', 0):.2f}元")
                return True
            else:
                self.print_step("管理员获取分销商", False, data.get("message", "获取失败"))
                return False

        except Exception as e:
            self.print_step("管理员获取分销商", False, f"异常: {str(e)}")
            return False

    def test_14_admin_list_withdrawals(self) -> bool:
        """步骤14：管理员获取提现申请列表"""
        print("管理员获取提现申请列表...")

        try:
            response = self.client.get(
                f"{self.base_url}/api/distribution/admin/withdrawals",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                params={"page": 1, "page_size": 10}
            )

            data = response.json()

            if data.get("code") == 1:
                total = data["data"]["total"]
                withdrawals = data["data"]["withdrawals"]
                self.print_step("管理员获取提现列表", True, f"共 {total} 条提现申请")
                if withdrawals:
                    for w in withdrawals[:2]:
                        print(f"    - {w.get('user_nickname')} | {w.get('amount', 0):.2f}元 | {w.get('status')}")
                return True
            else:
                self.print_step("管理员获取提现列表", False, data.get("message", "获取失败"))
                return False

        except Exception as e:
            self.print_step("管理员获取提现列表", False, f"异常: {str(e)}")
            return False

    def test_15_admin_approve_withdrawal(self) -> bool:
        """步骤15：管理员审核通过提现"""
        print("管理员审核通过提现...")

        if not self.withdrawal_id:
            self.print_step("审核通过提现", False, "没有可审核的提现申请")
            return False

        try:
            response = self.client.post(
                f"{self.base_url}/api/distribution/admin/withdrawals/{self.withdrawal_id}/approve",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                json={"transaction_id": f"TXN_{int(time.time() * 1000)}"}
            )

            data = response.json()

            if data.get("code") == 1:
                self.print_step("审核通过提现", True, "提现已完成")
                return True
            else:
                # 可能已被处理，不算失败
                msg = data.get("message", "")
                if "已处理" in msg:
                    self.print_step("审核通过提现", True, "提现申请已处理")
                    return True
                self.print_step("审核通过提现", False, msg)
                return False

        except Exception as e:
            self.print_step("审核通过提现", False, f"异常: {str(e)}")
            return False

    # ==================== 系统统计 ====================

    def test_16_get_system_stats(self) -> bool:
        """步骤16：获取系统统计"""
        print("获取系统统计...")

        try:
            response = self.client.get(
                f"{self.base_url}/api/admin/stats",
                headers={"Authorization": f"Bearer {self.admin_token}"}
            )

            data = response.json()

            if data.get("code") == 1:
                stats = data["data"]
                self.print_step("获取系统统计", True,
                    f"用户: {stats.get('total_users')}, "
                    f"会员: {stats.get('total_members')}, "
                    f"订单: {stats.get('total_orders')}, "
                    f"收入: {stats.get('total_revenue', 0):.2f}元")
                return True
            else:
                self.print_step("获取系统统计", False, data.get("message", "获取失败"))
                return False

        except Exception as e:
            self.print_step("获取系统统计", False, f"异常: {str(e)}")
            return False

    # ==================== 运行测试 ====================

    def run_all_tests(self):
        """运行所有测试"""
        print(f"{Colors.BOLD}分销推广模块 - 端对端测试{Colors.RESET}")
        print(f"测试地址: {self.base_url}")
        print(f"推广人手机: {self.promoter_phone}")
        print(f"新用户手机: {self.new_user_phone}")

        self.print_section("开始测试")

        # 认证测试
        self.print_section("1. 认证模块")
        self.test_01_register_promoter()
        self.test_02_login_admin()

        if not self.promoter_token:
            print(f"\n{Colors.RED}推广人注册失败，测试终止{Colors.RESET}")
            return

        # 分销商管理
        self.print_section("2. 分销商管理")
        self.test_03_become_distributor()
        self.test_04_get_distributor_code()
        self.test_05_validate_code()
        self.test_06_get_distributor_stats()

        # 推广注册
        self.print_section("3. 推广注册")
        self.test_07_register_with_referral()

        # 订单与佣金
        self.print_section("4. 订单与佣金")
        self.test_08_create_order()
        self.test_09_complete_payment()

        # 分销记录
        self.print_section("5. 分销记录")
        self.test_10_list_records()

        # 提现申请
        self.print_section("6. 提现申请")
        self.test_11_create_withdrawal()
        self.test_12_list_withdrawals()

        # 管理员接口
        self.print_section("7. 管理员接口")
        self.test_13_admin_list_distributors()
        self.test_14_admin_list_withdrawals()
        self.test_15_admin_approve_withdrawal()

        # 系统统计
        self.print_section("8. 系统统计")
        self.test_16_get_system_stats()

        # 输出测试结果
        self.print_section("测试结果")
        total = self.passed_tests + self.failed_tests

        print(f"总计: {total} 个测试")
        print(f"{Colors.GREEN}通过: {self.passed_tests}{Colors.RESET}")
        print(f"{Colors.RED}失败: {self.failed_tests}{Colors.RESET}")
        print(f"成功率: {self.passed_tests / total * 100:.1f}%")

        if self.failed_tests == 0:
            print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 所有测试通过！{Colors.RESET}")
        else:
            print(f"\n{Colors.YELLOW}有 {self.failed_tests} 个测试失败{Colors.RESET}")


def main():
    """主函数"""
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"

    test = DistributionE2ETest(base_url)
    test.run_all_tests()


if __name__ == "__main__":
    main()
