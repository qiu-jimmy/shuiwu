"""
智能报税系统端对端测试
测试完整的业务流程和性能
"""
import httpx
import asyncio
import time
import json
from typing import Dict, Any, Optional
from datetime import datetime


class TaxDeclarationE2ETest:
    """智能报税端对端测试"""

    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.client = httpx.Client(timeout=30.0)
        self.user_token: Optional[str] = None
        self.admin_token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.declaration_id: Optional[int] = None
        self.declaration_no: Optional[str] = None

        # 测试结果
        self.results = {
            "success": [],
            "failed": [],
            "performance": {}
        }

    def log(self, message: str, level: str = "INFO"):
        """输出日志"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] [{level}] {message}")

    def measure_time(self, func, name: str):
        """测量函数执行时间"""
        start = time.perf_counter()
        try:
            result = func()
            end = time.perf_counter()
            elapsed = (end - start) * 1000  # 转换为毫秒
            self.results["performance"][name] = {
                "elapsed_ms": round(elapsed, 2),
                "success": True
            }
            self.log(f"{name} 耗时: {elapsed:.2f}ms", "PERF")
            return result
        except Exception as e:
            end = time.perf_counter()
            elapsed = (end - start) * 1000
            self.results["performance"][name] = {
                "elapsed_ms": round(elapsed, 2),
                "success": False,
                "error": str(e)
            }
            self.log(f"{name} 失败: {str(e)}", "ERROR")
            raise

    def register_user(self, phone: str, password: str) -> bool:
        """注册测试用户"""
        try:
            response = self.client.post(
                f"{self.base_url}/api/auth/register",
                json={
                    "phone": phone,
                    "password": password,
                    "nickname": f"测试用户_{phone}",
                    "sms_code": "123456"  # 测试验证码
                }
            )
            data = response.json()
            if data.get("code") == 1:
                self.log(f"用户注册成功: {phone}")
                return True
            # 如果用户已存在，也算成功
            if "已存在" in data.get("message", "") or "已被注册" in data.get("message", ""):
                self.log(f"用户已存在: {phone}")
                return True
            self.log(f"注册失败: {data.get('message')}", "WARN")
            return False
        except Exception as e:
            self.log(f"注册异常: {str(e)}", "ERROR")
            return False

    def login_user(self, phone: str, password: str, is_admin: bool = False) -> bool:
        """用户登录"""
        try:
            response = self.client.post(
                f"{self.base_url}/api/auth/login",
                json={"username": phone, "password": password}  # 使用 username 而不是 phone
            )
            data = response.json()

            if data.get("code") == 1:
                token = data["data"]["access_token"]
                if is_admin:
                    self.admin_token = token
                    self.log("管理员登录成功")
                else:
                    self.user_token = token
                    self.user_id = data["data"].get("user_id")
                    self.log(f"用户登录成功: {self.user_id}")
                return True
            else:
                self.log(f"登录失败: {data.get('message')}", "ERROR")
                return False
        except Exception as e:
            self.log(f"登录异常: {str(e)}", "ERROR")
            return False

    def test_1_submit_declaration(self) -> bool:
        """测试1: 提交报税申报"""
        self.log("=== 测试1: 提交报税申报 ===")

        def _submit():
            response = self.client.post(
                f"{self.base_url}/api/tax-declaration/submit",
                headers={"Authorization": f"Bearer {self.user_token}"},
                json={
                    "taxpayer_name": "张三",
                    "taxpayer_id_card": "110101199001011234",
                    "taxpayer_phone": "13800138000",
                    "taxpayer_type": "individual",
                    "tax_type": "pit",
                    "tax_period": "2024Q1",
                    "income_info": {
                        "salary": 60000,
                        "bonus": 10000,
                        "labor_income": 5000
                    },
                    "deduction_info": {
                        "special_deduction": 5000,
                        "additional_deduction": {
                            "children_education": 12000,
                            "housing_loan": 12000
                        }
                    },
                    "user_remarks": "请帮我核算季度个税"
                }
            )
            return response

        response = self.measure_time(_submit, "提交报税申报")
        data = response.json()

        if data.get("code") == 1:
            self.declaration_id = data["data"]["id"]
            self.declaration_no = data["data"]["declaration_no"]
            self.log(f"申报提交成功: {self.declaration_no}")
            self.results["success"].append("提交报税申报")
            return True
        else:
            self.log(f"申报提交失败: {data.get('message')}", "ERROR")
            self.results["failed"].append("提交报税申报")
            return False

    def test_2_list_my_declarations(self) -> bool:
        """测试2: 获取我的申报列表"""
        self.log("=== 测试2: 获取我的申报列表 ===")

        def _list():
            response = self.client.get(
                f"{self.base_url}/api/tax-declaration/list",
                headers={"Authorization": f"Bearer {self.user_token}"}
            )
            return response

        response = self.measure_time(_list, "获取申报列表")
        data = response.json()

        if data.get("code") == 1:
            total = data["data"]["total"]
            self.log(f"获取列表成功，共 {total} 条记录")
            self.results["success"].append("获取申报列表")
            return True
        else:
            self.log(f"获取列表失败: {data.get('message')}", "ERROR")
            self.results["failed"].append("获取申报列表")
            return False

    def test_3_get_declaration_detail(self) -> bool:
        """测试3: 获取申报详情"""
        self.log("=== 测试3: 获取申报详情 ===")

        def _detail():
            response = self.client.get(
                f"{self.base_url}/api/tax-declaration/{self.declaration_id}",
                headers={"Authorization": f"Bearer {self.user_token}"}
            )
            return response

        response = self.measure_time(_detail, "获取申报详情")
        data = response.json()

        if data.get("code") == 1:
            declaration = data["data"]
            self.log(f"获取详情成功: {declaration.get('declaration_no')}")
            self.log(f"  纳税人: {declaration.get('taxpayer_name')}")
            self.log(f"  税种: {declaration.get('tax_type')}")
            self.log(f"  税期: {declaration.get('tax_period')}")
            self.log(f"  收入: {declaration.get('income_info')}")
            self.results["success"].append("获取申报详情")
            return True
        else:
            self.log(f"获取详情失败: {data.get('message')}", "ERROR")
            self.results["failed"].append("获取申报详情")
            return False

    def test_4_get_my_stats(self) -> bool:
        """测试4: 获取我的统计信息"""
        self.log("=== 测试4: 获取我的统计信息 ===")

        def _stats():
            response = self.client.get(
                f"{self.base_url}/api/tax-declaration/stats/my",
                headers={"Authorization": f"Bearer {self.user_token}"}
            )
            return response

        response = self.measure_time(_stats, "获取统计信息")
        data = response.json()

        if data.get("code") == 1:
            stats = data["data"]
            self.log(f"统计信息:")
            self.log(f"  总申报数: {stats.get('total_count')}")
            self.log(f"  待处理: {stats.get('pending_count')}")
            self.log(f"  已完成: {stats.get('completed_count')}")
            self.results["success"].append("获取统计信息")
            return True
        else:
            self.log(f"获取统计失败: {data.get('message')}", "ERROR")
            self.results["failed"].append("获取统计信息")
            return False

    def test_5_admin_list_all(self) -> bool:
        """测试5: 管理员获取所有申报"""
        self.log("=== 测试5: 管理员获取所有申报 ===")

        def _list():
            response = self.client.get(
                f"{self.base_url}/api/tax-declaration/admin/list",
                headers={"Authorization": f"Bearer {self.admin_token}"}
            )
            return response

        response = self.measure_time(_list, "管理员获取所有申报")
        data = response.json()

        if data.get("code") == 1:
            total = data["data"]["total"]
            self.log(f"管理员获取列表成功，共 {total} 条记录")
            self.results["success"].append("管理员获取所有申报")
            return True
        else:
            self.log(f"管理员获取列表失败: {data.get('message')}", "ERROR")
            self.results["failed"].append("管理员获取所有申报")
            return False

    def test_6_admin_process_declaration(self) -> bool:
        """测试6: 管理员处理申报（自动计算）"""
        self.log("=== 测试6: 管理员处理申报（自动计算） ===")

        def _process():
            response = self.client.post(
                f"{self.base_url}/api/tax-declaration/admin/{self.declaration_id}/process",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                json={
                    # 不填写计算结果，测试自动计算
                    "status": "completed",
                    "declaration_serial_no": "WS2026012000001",
                    "declaration_date": datetime.now().isoformat(),
                    "process_result": "申报成功，税额已自动计算",
                    "process_notes": "系统自动计算税额并完成申报"
                }
            )
            return response

        response = self.measure_time(_process, "管理员处理申报")
        data = response.json()

        if data.get("code") == 1:
            self.log(f"处理成功: {data.get('message')}")
            self.results["success"].append("管理员处理申报")
            return True
        else:
            self.log(f"处理失败: {data.get('message')}", "ERROR")
            self.results["failed"].append("管理员处理申报")
            return False

    def test_7_verify_calculation(self) -> bool:
        """测试7: 验证自动计算结果"""
        self.log("=== 测试7: 验证自动计算结果 ===")

        def _verify():
            response = self.client.get(
                f"{self.base_url}/api/tax-declaration/{self.declaration_id}",
                headers={"Authorization": f"Bearer {self.user_token}"}
            )
            return response

        response = self.measure_time(_verify, "验证计算结果")
        data = response.json()

        if data.get("code") == 1:
            declaration = data["data"]
            self.log(f"自动计算结果:")
            self.log(f"  收入总额: {declaration.get('total_income')} 元")
            self.log(f"  扣除总额: {declaration.get('total_deduction')} 元")
            self.log(f"  应纳税所得额: {declaration.get('taxable_income')} 元")
            self.log(f"  应纳税额: {declaration.get('tax_amount')} 元")
            self.log(f"  状态: {declaration.get('status')}")
            self.results["success"].append("验证计算结果")
            return True
        else:
            self.log(f"验证失败: {data.get('message')}", "ERROR")
            self.results["failed"].append("验证计算结果")
            return False

    def test_8_export_declaration(self) -> bool:
        """测试8: 导出申报表"""
        self.log("=== 测试8: 导出申报表 ===")

        def _export():
            response = self.client.get(
                f"{self.base_url}/api/tax-declaration/{self.declaration_id}/export",
                headers={"Authorization": f"Bearer {self.user_token}"},
                params={"format": "xlsx"}
            )
            return response

        response = self.measure_time(_export, "导出申报表")

        if response.status_code == 200:
            file_size = len(response.content)
            self.log(f"导出成功，文件大小: {file_size} 字节")
            self.results["success"].append("导出申报表")
            return True
        else:
            self.log(f"导出失败: {response.status_code}", "ERROR")
            self.results["failed"].append("导出申报表")
            return False

    def test_9_admin_global_stats(self) -> bool:
        """测试9: 管理员获取全局统计"""
        self.log("=== 测试9: 管理员获取全局统计 ===")

        def _stats():
            response = self.client.get(
                f"{self.base_url}/api/tax-declaration/admin/stats",
                headers={"Authorization": f"Bearer {self.admin_token}"}
            )
            return response

        response = self.measure_time(_stats, "管理员获取全局统计")
        data = response.json()

        if data.get("code") == 1:
            stats = data["data"]
            self.log(f"全局统计:")
            self.log(f"  总申报数: {stats.get('total_count')}")
            self.log(f"  总应纳税额: {stats.get('total_tax_amount')} 元")
            self.results["success"].append("管理员获取全局统计")
            return True
        else:
            self.log(f"获取统计失败: {data.get('message')}", "ERROR")
            self.results["failed"].append("管理员获取全局统计")
            return False

    def test_10_concurrent_requests(self) -> bool:
        """测试10: 并发请求测试"""
        self.log("=== 测试10: 并发请求测试 ===")

        async def _concurrent_test():
            async with httpx.AsyncClient(timeout=30.0) as client:
                tasks = []
                for i in range(10):
                    task = client.get(
                        f"{self.base_url}/api/tax-declaration/list",
                        headers={"Authorization": f"Bearer {self.user_token}"}
                    )
                    tasks.append(task)

                start = time.perf_counter()
                responses = await asyncio.gather(*tasks)
                end = time.perf_counter()

                elapsed = (end - start) * 1000
                avg_time = elapsed / len(responses)

                self.log(f"并发 {len(responses)} 个请求:")
                self.log(f"  总耗时: {elapsed:.2f}ms")
                self.log(f"  平均耗时: {avg_time:.2f}ms")
                self.log(f"  QPS: {len(responses) / (elapsed / 1000):.2f}")

                self.results["performance"]["并发请求"] = {
                    "elapsed_ms": round(elapsed, 2),
                    "avg_ms": round(avg_time, 2),
                    "qps": round(len(responses) / (elapsed / 1000), 2),
                    "success": True
                }

                return all(r.status_code == 200 for r in responses)

        try:
            result = asyncio.run(_concurrent_test())
            if result:
                self.results["success"].append("并发请求测试")
            else:
                self.results["failed"].append("并发请求测试")
            return result
        except Exception as e:
            self.log(f"并发测试失败: {str(e)}", "ERROR")
            self.results["failed"].append("并发请求测试")
            return False

    def print_summary(self):
        """打印测试总结"""
        print("\n" + "="*60)
        print("测试总结")
        print("="*60)

        total_tests = len(self.results['success']) + len(self.results['failed'])
        print(f"\n成功测试 ({len(self.results['success'])}/{total_tests}):")
        for test in self.results["success"]:
            print(f"  [OK] {test}")

        if self.results["failed"]:
            print(f"\n失败测试 ({len(self.results['failed'])}):")
            for test in self.results["failed"]:
                print(f"  [FAIL] {test}")

        print(f"\n性能测试结果:")
        print(f"{'接口':<25} {'耗时(ms)':<15} {'状态'}")
        print("-" * 60)
        for name, perf in self.results["performance"].items():
            status = "[OK]" if perf["success"] else "[FAIL]"
            elapsed = perf.get("elapsed_ms", 0)
            print(f"{name:<25} {elapsed:<15} {status}")

        # 计算平均响应时间
        success_times = [
            p["elapsed_ms"] for p in self.results["performance"].values()
            if p["success"] and "elapsed_ms" in p
        ]
        if success_times:
            avg = sum(success_times) / len(success_times)
            max_time = max(success_times)
            min_time = min(success_times)
            print(f"\n统计信息:")
            print(f"  平均响应时间: {avg:.2f}ms")
            print(f"  最大响应时间: {max_time:.2f}ms")
            print(f"  最小响应时间: {min_time:.2f}ms")

        print("="*60 + "\n")

    def run_all_tests(self):
        """运行所有测试"""
        self.log("开始智能报税系统端对端测试", "INFO")

        # 准备测试账号
        test_user_phone = "13800138999"
        test_admin_phone = "13800139999"
        test_password = "Test123456"

        # 注册用户
        self.register_user(test_user_phone, test_password)
        self.register_user(test_admin_phone, test_password)

        # 登录
        if not self.login_user(test_user_phone, test_password):
            self.log("用户登录失败，测试终止", "ERROR")
            return

        # 尝试登录管理员（如果失败则使用普通用户）
        if not self.login_user(test_admin_phone, test_password, is_admin=True):
            self.log("管理员登录失败，使用普通用户进行管理员测试", "WARN")
            self.admin_token = self.user_token

        # 运行测试
        tests = [
            self.test_1_submit_declaration,
            self.test_2_list_my_declarations,
            self.test_3_get_declaration_detail,
            self.test_4_get_my_stats,
            self.test_5_admin_list_all,
            self.test_6_admin_process_declaration,
            self.test_7_verify_calculation,
            self.test_8_export_declaration,
            self.test_9_admin_global_stats,
            self.test_10_concurrent_requests,
        ]

        for test in tests:
            try:
                test()
                time.sleep(0.1)  # 避免请求过快
            except Exception as e:
                self.log(f"测试异常: {str(e)}", "ERROR")

        # 打印总结
        self.print_summary()

        self.client.close()


def main():
    """主函数"""
    import sys

    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"

    print("="*60)
    print("智能报税系统 - 端对端测试")
    print(f"测试服务器: {base_url}")
    print("="*60 + "\n")

    tester = TaxDeclarationE2ETest(base_url)
    tester.run_all_tests()


if __name__ == "__main__":
    main()
