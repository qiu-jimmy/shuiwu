"""
税务师入驻模块 - 端到端测试脚本

测试税务师入驻的完整流程：
1. 用户注册并登录
2. 提交税务师入驻申请
3. 查看申请状态
4. 管理员审核申请（通过）
5. 验证税务师状态更新
6. 管理员审核申请（拒绝）
7. 获取税务师列表
8. 获取税务师统计
9. 更新税务师信息
10. 验证 /auth/me 返回 is_tax_accountant 字段

运行方式：
    python test/test_tax_accountant_e2e.py
"""
import json
import random
import string
import sys
import time
from typing import Any, Dict, Optional

import httpx

# ============================================================================
# 配置
# ============================================================================

BASE_URL = "http://127.0.0.1:8000"
TEST_TIMEOUT = 30  # 请求超时时间（秒）

# 测试用的管理员账号（需要提前在数据库中创建）
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


# ============================================================================
# 工具类
# ============================================================================

class Colors:
    """终端颜色"""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_success(message: str):
    """打印成功消息"""
    print(f"{Colors.GREEN}{Colors.BOLD}✓ {message}{Colors.END}")


def print_error(message: str):
    """打印错误消息"""
    print(f"{Colors.RED}{Colors.BOLD}✗ {message}{Colors.END}")


def print_info(message: str):
    """打印信息消息"""
    print(f"{Colors.BLUE}{Colors.BOLD}→ {message}{Colors.END}")


def print_step(message: str):
    """打印步骤消息"""
    print(f"\n{Colors.YELLOW}{Colors.BOLD}═══ {message} ═══{Colors.END}")


def print_result(message: str, data: Any = None):
    """打印结果"""
    if data is not None:
        print(f"  {message}: {json.dumps(data, ensure_ascii=False, indent=2)}")
    else:
        print(f"  {message}")


def generate_random_phone() -> str:
    """生成随机手机号（测试用）"""
    return f"1{random.randint(3, 9)}{random.randint(0, 9)}{random.randint(0, 9)}{random.randint(10000000, 99999999)}"


def generate_random_password(length: int = 8) -> str:
    """生成随机密码"""
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_random_id_card() -> str:
    """生成随机身份证号（测试用）"""
    return f"{''.join(random.choices(string.digits, k=17))}{random.choice('0123456789X')}"


class APIClient:
    """API 客户端"""

    def __init__(self, base_url: str = BASE_URL, timeout: int = TEST_TIMEOUT):
        self.base_url = base_url
        self.timeout = timeout
        self.access_token: Optional[str] = None
        self.admin_token: Optional[str] = None
        self.client = httpx.Client(timeout=timeout)

    def set_token(self, token: str, is_admin: bool = False):
        """设置访问令牌"""
        if is_admin:
            self.admin_token = token
        else:
            self.access_token = token

    def get_headers(self, is_admin: bool = False) -> Dict[str, str]:
        """获取请求头"""
        headers = {"Content-Type": "application/json"}
        token = self.admin_token if is_admin else self.access_token
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def request(
        self,
        method: str,
        path: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        use_token: bool = True,
        is_admin: bool = False,
    ) -> Dict:
        """发送请求"""
        url = f"{self.base_url}{path}"
        headers = self.get_headers(is_admin) if use_token else {"Content-Type": "application/json"}
        try:
            response = self.client.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=headers,
            )
            return response.json()
        except httpx.TimeoutException:
            raise Exception(f"请求超时: {method} {url}")
        except Exception as e:
            raise Exception(f"请求失败: {e}")

    def get(self, path: str, params: Optional[Dict] = None, is_admin: bool = False) -> Dict:
        """GET 请求"""
        return self.request("GET", path, params=params, is_admin=is_admin)

    def post(self, path: str, data: Optional[Dict] = None, use_token: bool = True, is_admin: bool = False) -> Dict:
        """POST 请求"""
        if data is None:
            data = {}
        return self.request("POST", path, data=data, use_token=use_token, is_admin=is_admin)

    def put(self, path: str, data: Optional[Dict] = None, is_admin: bool = False) -> Dict:
        """PUT 请求"""
        if data is None:
            data = {}
        return self.request("PUT", path, data=data, is_admin=is_admin)

    def delete(self, path: str, is_admin: bool = False) -> Dict:
        """DELETE 请求"""
        return self.request("DELETE", path, is_admin=is_admin)

    def close(self):
        """关闭客户端"""
        self.client.close()


# ============================================================================
# 测试用例
# ============================================================================

class TaxAccountantE2ETest:
    """税务师入驻端到端测试"""

    def __init__(self):
        self.client = APIClient()
        self.test_data: Dict[str, Any] = {}
        # 生成测试用的手机号和密码
        self.test_phone = generate_random_phone()
        self.test_password = generate_random_password()

    def setup(self) -> bool:
        """测试前置准备"""
        print_step("1. 测试前置准备")

        # 健康检查
        try:
            result = self.client.get("/health")
            if result.get("code") != 1:
                print_error("服务健康检查失败")
                return False
            print_success("服务健康检查通过")
        except Exception as e:
            print_error(f"无法连接到服务: {e}")
            print_info("请确保服务正在运行: python main.py")
            return False

        print_info(f"测试手机号: {self.test_phone}")
        print_info(f"测试密码: {self.test_password}")

        return True

    def test_user_register_and_login(self) -> bool:
        """测试用户注册和登录"""
        print_step("2. 用户注册并登录")

        try:
            # 注册用户
            result = self.client.post("/api/auth/register", {
                "phone": self.test_phone,
                "password": self.test_password,
                "nickname": f"测试用户{self.test_phone[-4:]}",
                "sms_code": "123456"  # 测试环境可能跳过验证
            }, use_token=False)

            if result.get("code") != 1:
                print_error(f"注册失败: {result}")
                return False

            data = result.get("data", {})
            access_token = data.get("access_token")
            user_info = data.get("user_info", {})

            if not access_token:
                print_error("注册成功但未返回token")
                return False

            # 保存token和用户信息
            self.client.set_token(access_token)
            self.test_data.update({
                "access_token": access_token,
                "user_id": user_info.get("user_id"),
                "nickname": user_info.get("nickname")
            })

            print_success("用户注册成功")
            print_result("用户信息", {
                "user_id": user_info.get("user_id"),
                "nickname": user_info.get("nickname"),
                "phone": user_info.get("phone"),
                "is_tax_accountant": user_info.get("is_tax_accountant", False)
            })

            # 验证 is_tax_accountant 字段存在且为 False
            if "is_tax_accountant" not in user_info:
                print_error("用户信息中缺少 is_tax_accountant 字段")
                return False

            if user_info.get("is_tax_accountant") != False:
                print_error(f"新用户的 is_tax_accountant 应该为 False，实际是: {user_info.get('is_tax_accountant')}")
                return False

            print_success("验证 is_tax_accountant 字段正确（False）")
            return True
        except Exception as e:
            print_error(f"注册异常: {e}")
            return False

    def test_admin_login(self) -> bool:
        """测试管理员登录"""
        print_step("3. 管理员登录")

        try:
            result = self.client.post("/api/admin/login", {
                "username": ADMIN_USERNAME,
                "password": ADMIN_PASSWORD
            }, use_token=False, is_admin=True)

            if result.get("code") != 1:
                print_error(f"管理员登录失败: {result}")
                print_info("请确保管理员账号存在，可以通过数据库创建")
                return False

            data = result.get("data", {})
            admin_token = data.get("access_token")
            admin_info = data.get("admin_info", {})

            if not admin_token:
                print_error("登录成功但未返回token")
                return False

            # 保存管理员token
            self.client.set_token(admin_token, is_admin=True)
            self.test_data.update({
                "admin_token": admin_token,
                "admin_id": admin_info.get("admin_id") or admin_info.get("user_id")
            })

            print_success("管理员登录成功")
            print_result("管理员信息", {
                "admin_id": admin_info.get("admin_id") or admin_info.get("user_id"),
                "nickname": admin_info.get("nickname"),
                "role": admin_info.get("role")
            })
            return True
        except Exception as e:
            print_error(f"管理员登录异常: {e}")
            return False

    def test_submit_tax_accountant_application(self) -> bool:
        """测试提交税务师入驻申请"""
        print_step("4. 提交税务师入驻申请")

        try:
            # 使用前端表单字段名（camelCase）
            application_data = {
                "name": "张三",
                "birthDate": "1985-06-15",
                "idCard": generate_random_id_card(),
                "address": "北京市朝阳区某某街道",
                "phone": self.test_phone,
                "certificateNo": f"TA{random.randint(20200000, 20999999)}",
                "certificateDate": "2015-06",
                "certificateImages": [
                    "https://example.com/cert1.jpg",
                    "https://example.com/cert2.jpg"
                ],
                "signatureImage": "https://example.com/signature.jpg",
                "experiences": [
                    {
                        "start_date": "2015-01",
                        "end_date": "2020-12",
                        "company": "某税务师事务所",
                        "position": "税务师",
                        "work_content": "负责企业所得税筹划和税务咨询"
                    },
                    {
                        "start_date": "2021-01",
                        "end_date": None,
                        "company": "某会计师事务所",
                        "position": "高级税务顾问",
                        "work_content": "负责企业税务风险防控"
                    }
                ],
                "expertise": "企业所得税",
                "settledIndex": 1,
                "additionalInfo": "本人具有10年税务从业经验，精通各类税务业务"
            }

            # 需要传递 token (use_token=True)
            result = self.client.post("/api/tax_accountant/apply", application_data, use_token=True)

            if result.get("code") != 1:
                print_error(f"提交申请失败: {result}")
                return False

            data = result.get("data", {})
            application_id = data.get("application_id")

            if not application_id:
                print_error("申请提交成功但未返回application_id")
                return False

            self.test_data["application_id"] = application_id

            print_success("税务师申请提交成功")
            print_result("申请ID", application_id)
            return True
        except Exception as e:
            print_error(f"提交申请异常: {e}")
            return False

    def test_get_my_application_status(self) -> bool:
        """测试查看申请状态"""
        print_step("5. 查看我的申请状态")

        try:
            result = self.client.get("/api/tax_accountant/my-application")

            if result.get("code") != 1:
                print_error(f"获取申请状态失败: {result}")
                return False

            data = result.get("data", {})

            print_success("获取申请状态成功")
            print_result("申请状态", {
                "has_applied": data.get("has_applied"),
                "application_id": data.get("application_id"),
                "status": data.get("status"),
                "reject_reason": data.get("reject_reason"),
                "created_at": data.get("created_at")
            })

            # 验证状态
            if not data.get("has_applied"):
                print_error("has_applied 应该为 True")
                return False

            if data.get("status") != "pending":
                print_error(f"状态应该是 pending，实际是 {data.get('status')}")
                return False

            return True
        except Exception as e:
            print_error(f"获取申请状态异常: {e}")
            return False

    def test_admin_get_application_list(self) -> bool:
        """测试管理员获取申请列表"""
        print_step("6. 管理员获取申请列表")

        try:
            result = self.client.get("/api/admin/tax-accountant/applications", is_admin=True)

            if result.get("code") != 1:
                print_error(f"获取申请列表失败: {result}")
                return False

            data = result.get("data", {})
            applications = data.get("applications", [])

            print_success("管理员获取申请列表成功")
            print_result("申请列表", {
                "total": data.get("total"),
                "page": data.get("page"),
                "page_size": data.get("page_size"),
                "applications_count": len(applications)
            })

            if applications:
                first_app = applications[0]
                print_result("第一个申请", {
                    "application_id": first_app.get("application_id"),
                    "real_name": first_app.get("real_name"),
                    "phone": first_app.get("phone"),
                    "status": first_app.get("status")
                })

            return True
        except Exception as e:
            print_error(f"获取申请列表异常: {e}")
            return False

    def test_admin_get_application_detail(self) -> bool:
        """测试管理员获取申请详情"""
        print_step("7. 管理员获取申请详情")

        try:
            application_id = self.test_data.get("application_id")
            if not application_id:
                print_error("缺少 application_id")
                return False

            result = self.client.get(f"/api/admin/tax-accountant/applications/{application_id}", is_admin=True)

            if result.get("code") != 1:
                print_error(f"获取申请详情失败: {result}")
                return False

            data = result.get("data", {})

            print_success("管理员获取申请详情成功")
            print_result("申请详情", {
                "application_id": data.get("application_id"),
                "real_name": data.get("real_name"),
                "id_card": data.get("id_card"),
                "phone": data.get("phone"),
                "certificate_number": data.get("certificate_number"),
                "work_experience": data.get("work_experience"),
                "specialty_area": data.get("specialty_area"),
                "status": data.get("status")
            })

            return True
        except Exception as e:
            print_error(f"获取申请详情异常: {e}")
            return False

    def test_admin_approve_application(self) -> bool:
        """测试管理员审核通过申请"""
        print_step("8. 管理员审核通过申请")

        try:
            application_id = self.test_data.get("application_id")
            if not application_id:
                print_error("缺少 application_id")
                return False

            result = self.client.post("/api/admin/tax-accountant/review", {
                "application_id": application_id,
                "action": "approve"
            }, is_admin=True)

            if result.get("code") != 1:
                print_error(f"审核失败: {result}")
                return False

            data = result.get("data", {})
            accountant_id = data.get("accountant_id")

            self.test_data["accountant_id"] = accountant_id

            print_success("管理员审核通过成功")
            print_result("税务师ID", accountant_id)
            return True
        except Exception as e:
            print_error(f"审核异常: {e}")
            return False

    def test_verify_tax_accountant_status(self) -> bool:
        """验证税务师状态已更新"""
        print_step("9. 验证税务师状态已更新")

        try:
            # 获取用户信息验证 is_tax_accountant
            result = self.client.get("/api/auth/me")

            if result.get("code") != 1:
                print_error(f"获取用户信息失败: {result}")
                return False

            user_info = result.get("data", {})

            print_success("获取用户信息成功")
            print_result("用户税务师状态", {
                "user_id": user_info.get("user_id"),
                "is_tax_accountant": user_info.get("is_tax_accountant")
            })

            # 验证 is_tax_accountant 为 True
            if not user_info.get("is_tax_accountant"):
                print_error("审核通过后 is_tax_accountant 应该为 True")
                return False

            print_success("验证 is_tax_accountant 字段正确（True）")

            # 获取税务师信息
            result = self.client.get("/api/tax_accountant/my-info")

            if result.get("code") != 1:
                print_error(f"获取税务师信息失败: {result}")
                return False

            accountant_info = result.get("data", {})

            print_success("获取税务师信息成功")
            print_result("税务师信息", {
                "accountant_id": accountant_info.get("accountant_id"),
                "real_name": accountant_info.get("real_name"),
                "certificate_number": accountant_info.get("certificate_number"),
                "specialty_area": accountant_info.get("specialty_area"),
                "status": accountant_info.get("status")
            })

            return True
        except Exception as e:
            print_error(f"验证状态异常: {e}")
            return False

    def test_get_tax_accountant_list(self) -> bool:
        """测试获取税务师列表"""
        print_step("10. 获取税务师列表")

        try:
            # 用户端获取列表
            result = self.client.get("/api/tax_accountant/list")

            if result.get("code") != 1:
                print_error(f"获取税务师列表失败: {result}")
                return False

            data = result.get("data", {})
            accountants = data.get("accountants", [])

            print_success("获取税务师列表成功")
            print_result("列表信息", {
                "total": data.get("total"),
                "page": data.get("page"),
                "page_size": data.get("page_size"),
                "accountants_count": len(accountants)
            })

            if accountants:
                first_accountant = accountants[0]
                print_result("第一个税务师", {
                    "accountant_id": first_accountant.get("accountant_id"),
                    "real_name": first_accountant.get("real_name"),
                    "specialty_area": first_accountant.get("specialty_area"),
                    "service_count": first_accountant.get("service_count"),
                    "rating": first_accountant.get("rating")
                })

            return True
        except Exception as e:
            print_error(f"获取税务师列表异常: {e}")
            return False

    def test_admin_get_accountant_list(self) -> bool:
        """测试管理员获取税务师列表"""
        print_step("11. 管理员获取税务师列表")

        try:
            result = self.client.get("/api/admin/tax-accountant/list", is_admin=True)

            if result.get("code") != 1:
                print_error(f"管理员获取税务师列表失败: {result}")
                return False

            data = result.get("data", {})

            print_success("管理员获取税务师列表成功")
            print_result("列表信息", {
                "total": data.get("total"),
                "page": data.get("page"),
                "page_size": data.get("page_size")
            })

            return True
        except Exception as e:
            print_error(f"管理员获取税务师列表异常: {e}")
            return False

    def test_admin_update_accountant(self) -> bool:
        """测试管理员更新税务师信息"""
        print_step("12. 管理员更新税务师信息")

        try:
            accountant_id = self.test_data.get("accountant_id")
            if not accountant_id:
                print_error("缺少 accountant_id")
                return False

            result = self.client.put(f"/api/admin/tax-accountant/{accountant_id}", {
                "specialty_area": ["企业所得税", "税务筹划", "增值税"],
                "introduction": "更新后的简介：15年税务从业经验，精通各类税务业务"
            }, is_admin=True)

            if result.get("code") != 1:
                print_error(f"更新税务师信息失败: {result}")
                return False

            print_success("管理员更新税务师信息成功")
            return True
        except Exception as e:
            print_error(f"更新税务师信息异常: {e}")
            return False

    def test_admin_get_statistics(self) -> bool:
        """测试获取税务师统计数据"""
        print_step("13. 获取税务师统计")

        try:
            result = self.client.get("/api/admin/tax-accountant/stats", is_admin=True)

            if result.get("code") != 1:
                print_error(f"获取统计数据失败: {result}")
                return False

            data = result.get("data", {})

            print_success("获取税务师统计成功")
            print_result("统计数据", {
                "total_applications": data.get("total_applications"),
                "pending_count": data.get("pending_count"),
                "approved_count": data.get("approved_count"),
                "rejected_count": data.get("rejected_count"),
                "active_accountants": data.get("active_accountants")
            })

            return True
        except Exception as e:
            print_error(f"获取统计数据异常: {e}")
            return False

    def test_submit_second_application_should_fail(self) -> bool:
        """测试已通过的税务师不能再次申请"""
        print_step("14. 测试已通过的税务师不能再次申请")

        try:
            # 使用前端表单字段名（camelCase）
            result = self.client.post("/api/tax_accountant/apply", {
                "name": "李四",
                "idCard": generate_random_id_card(),
                "phone": self.test_phone,
                "certificateNo": f"TA{random.randint(20200000, 20999999)}",
                "certificateImages": ["https://example.com/cert.jpg"],
                "expertise": "个人所得税"
            }, use_token=True)  # 需要传递 token

            if result.get("code") == 1:
                print_error("已通过的税务师不应该能再次申请")
                return False

            print_success("已通过的税务师无法再次申请（符合预期）")
            print_result("错误信息", result.get("message"))
            return True
        except Exception as e:
            print_error(f"测试异常: {e}")
            return False

    def test_get_tax_accountant_detail(self) -> bool:
        """测试获取税务师详情"""
        print_step("15. 获取税务师详情")

        try:
            accountant_id = self.test_data.get("accountant_id")
            if not accountant_id:
                print_error("缺少 accountant_id")
                return False

            result = self.client.get(f"/api/tax_accountant/{accountant_id}")

            if result.get("code") != 1:
                print_error(f"获取税务师详情失败: {result}")
                return False

            data = result.get("data", {})

            print_success("获取税务师详情成功")
            print_result("税务师详情", {
                "accountant_id": data.get("accountant_id"),
                "real_name": data.get("real_name"),
                "certificate_number": data.get("certificate_number"),
                "specialty_area": data.get("specialty_area"),
                "introduction": data.get("introduction"),
                "service_count": data.get("service_count"),
                "rating": data.get("rating"),
                "status": data.get("status")
            })

            return True
        except Exception as e:
            print_error(f"获取税务师详情异常: {e}")
            return False

    def run_all_tests(self) -> bool:
        """运行所有测试"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}")
        print("税务师入驻模块 - 端到端测试")
        print(f"{'='*60}{Colors.END}\n")

        all_passed = True

        # 测试列表
        tests = [
            ("前置准备", self.setup),
            ("用户注册并登录", self.test_user_register_and_login),
            ("管理员登录", self.test_admin_login),
            ("提交税务师入驻申请", self.test_submit_tax_accountant_application),
            ("查看我的申请状态", self.test_get_my_application_status),
            ("管理员获取申请列表", self.test_admin_get_application_list),
            ("管理员获取申请详情", self.test_admin_get_application_detail),
            ("管理员审核通过申请", self.test_admin_approve_application),
            ("验证税务师状态已更新", self.test_verify_tax_accountant_status),
            ("获取税务师列表", self.test_get_tax_accountant_list),
            ("管理员获取税务师列表", self.test_admin_get_accountant_list),
            ("管理员更新税务师信息", self.test_admin_update_accountant),
            ("获取税务师统计", self.test_admin_get_statistics),
            ("测试已通过的税务师不能再次申请", self.test_submit_second_application_should_fail),
            ("获取税务师详情", self.test_get_tax_accountant_detail),
        ]

        passed = 0
        failed = 0

        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
                else:
                    failed += 1
                    all_passed = False
            except Exception as e:
                print_error(f"{test_name} 测试异常: {e}")
                failed += 1
                all_passed = False

        # 测试结果汇总
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}")
        print("测试结果汇总")
        print(f"{'='*60}{Colors.END}")

        print(f"  总计: {passed + failed} 个测试")
        print(f"  {Colors.GREEN}通过: {passed} 个{Colors.END}")
        print(f"  {Colors.RED}失败: {failed} 个{Colors.END}")

        if all_passed:
            print(f"\n{Colors.GREEN}{Colors.BOLD}✓ 所有测试通过！{Colors.END}\n")
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}✗ 部分测试失败{Colors.END}\n")

        return all_passed


# ============================================================================
# 主程序
# ============================================================================

def main():
    """主程序"""
    # Windows 控制台编码修复
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    test = TaxAccountantE2ETest()
    try:
        success = test.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print_error("\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print_error(f"\n测试异常: {e}")
        sys.exit(1)
    finally:
        test.client.close()


if __name__ == "__main__":
    main()
