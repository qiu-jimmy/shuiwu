"""
认证端到端测试脚本

测试认证相关的完整流程：
1. 用户注册
2. 用户登录
3. 获取当前用户信息
4. 验证Token
5. 修改密码
6. 重置密码
7. 用户登出

运行方式：
    python test/test_auth_e2e.py
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


class APIClient:
    """API 客户端"""

    def __init__(self, base_url: str = BASE_URL, timeout: int = TEST_TIMEOUT):
        self.base_url = base_url
        self.timeout = timeout
        self.access_token: Optional[str] = None
        self.client = httpx.Client(timeout=timeout)

    def set_token(self, token: str):
        """设置访问令牌"""
        self.access_token = token

    def get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def request(
        self,
        method: str,
        path: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        use_token: bool = True,
    ) -> Dict:
        """发送请求"""
        url = f"{self.base_url}{path}"
        headers = self.get_headers() if use_token else {"Content-Type": "application/json"}
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

    def get(self, path: str, params: Optional[Dict] = None) -> Dict:
        """GET 请求"""
        return self.request("GET", path, params=params)

    def post(self, path: str, data: Optional[Dict] = None, use_token: bool = False) -> Dict:
        """POST 请求"""
        if data is None:
            data = {}
        return self.request("POST", path, data=data, use_token=use_token)

    def close(self):
        """关闭客户端"""
        self.client.close()


# ============================================================================
# 测试用例
# ============================================================================

class AuthE2ETest:
    """认证端到端测试"""

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

    def test_register(self) -> bool:
        """测试用户注册"""
        print_step("2. 用户注册")

        try:
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
                "user_type": user_info.get("user_type")
            })
            return True
        except Exception as e:
            print_error(f"注册异常: {e}")
            return False

    def test_login_with_wrong_password(self) -> bool:
        """测试使用错误密码登录"""
        print_step("3. 使用错误密码登录（预期失败）")

        try:
            result = self.client.post("/api/auth/login", {
                "username": self.test_phone,
                "password": "wrong_password"
            }, use_token=False)

            # 预期登录失败
            if result.get("code") == 1:
                print_error("错误密码登录成功（不应该）")
                return False

            print_success("错误密码登录被正确拒绝")
            print_result("错误信息", result.get("message"))
            return True
        except Exception as e:
            print_error(f"测试异常: {e}")
            return False

    def test_login_with_correct_password(self) -> bool:
        """测试使用正确密码登录"""
        print_step("4. 使用正确密码登录")

        try:
            result = self.client.post("/api/auth/login", {
                "username": self.test_phone,
                "password": self.test_password
            }, use_token=False)

            if result.get("code") != 1:
                print_error(f"登录失败: {result}")
                return False

            data = result.get("data", {})
            access_token = data.get("access_token")
            user_info = data.get("user_info", {})

            if not access_token:
                print_error("登录成功但未返回token")
                return False

            # 更新token
            self.client.set_token(access_token)
            self.test_data["access_token"] = access_token

            print_success("用户登录成功")
            print_result("Token信息", {
                "token_type": data.get("token_type"),
                "expires_in": data.get("expires_in")
            })
            return True
        except Exception as e:
            print_error(f"登录异常: {e}")
            return False

    def test_get_current_user(self) -> bool:
        """测试获取当前用户信息"""
        print_step("5. 获取当前用户信息")

        try:
            result = self.client.get("/api/auth/me")

            if result.get("code") != 1:
                print_error(f"获取用户信息失败: {result}")
                return False

            user_info = result.get("data", {})
            print_success("获取用户信息成功")
            print_result("用户信息", user_info)
            return True
        except Exception as e:
            print_error(f"获取用户信息异常: {e}")
            return False

    def test_verify_token(self) -> bool:
        """测试验证Token"""
        print_step("6. 验证Token有效性")

        try:
            result = self.client.get("/api/auth/verify-token")

            if result.get("code") != 1:
                print_error(f"Token验证失败: {result}")
                return False

            data = result.get("data", {})
            user_id = data.get("user_id")

            print_success("Token验证成功")
            print_result("用户ID", user_id)
            return True
        except Exception as e:
            print_error(f"Token验证异常: {e}")
            return False

    def test_access_without_token(self) -> bool:
        """测试无Token访问受保护接口"""
        print_step("7. 无Token访问受保护接口（预期失败）")

        try:
            # 临时清空token
            old_token = self.client.access_token
            self.client.access_token = None

            result = self.client.get("/api/auth/me")

            # 恢复token
            self.client.access_token = old_token

            # 预期失败
            if result.get("code") == 1:
                print_error("无Token访问成功（不应该）")
                return False

            print_success("无Token访问被正确拒绝")
            print_result("错误信息", result.get("message"))
            return True
        except Exception as e:
            print_error(f"测试异常: {e}")
            return False

    def test_access_with_invalid_token(self) -> bool:
        """测试使用无效Token访问"""
        print_step("8. 使用无效Token访问（预期失败）")

        try:
            # 临时设置为无效token
            old_token = self.client.access_token
            self.client.access_token = "invalid_token_12345"

            result = self.client.get("/api/auth/me")

            # 恢复token
            self.client.access_token = old_token

            # 预期失败
            if result.get("code") == 1:
                print_error("无效Token访问成功（不应该）")
                return False

            print_success("无效Token访问被正确拒绝")
            print_result("错误信息", result.get("message"))
            return True
        except Exception as e:
            print_error(f"测试异常: {e}")
            return False

    def test_change_password(self) -> bool:
        """测试修改密码"""
        print_step("9. 修改密码")

        new_password = generate_random_password()

        try:
            result = self.client.post("/api/auth/change-password", {
                "old_password": self.test_password,
                "new_password": new_password
            }, use_token=True)

            if result.get("code") != 1:
                print_error(f"修改密码失败: {result}")
                return False

            # 更新测试密码
            self.test_password = new_password

            print_success("密码修改成功")

            # 验证新密码可以登录
            print_info("验证新密码登录...")
            login_result = self.client.post("/api/auth/login", {
                "username": self.test_phone,
                "password": new_password
            }, use_token=False)

            if login_result.get("code") == 1:
                print_success("新密码登录验证成功")
                # 更新token
                data = login_result.get("data", {})
                self.client.set_token(data.get("access_token"))
                return True
            else:
                print_error("新密码登录验证失败")
                return False
        except Exception as e:
            print_error(f"修改密码异常: {e}")
            return False

    def test_reset_password(self) -> bool:
        """测试重置密码"""
        print_step("10. 重置密码")

        reset_password = generate_random_password()

        try:
            result = self.client.post("/api/auth/reset-password", {
                "phone": self.test_phone,
                "sms_code": "123456",  # 测试环境可能跳过验证
                "new_password": reset_password
            }, use_token=False)

            if result.get("code") != 1:
                print_error(f"重置密码失败: {result}")
                return False

            # 更新测试密码
            self.test_password = reset_password

            print_success("密码重置成功")

            # 验证新密码可以登录
            print_info("验证重置后的密码登录...")
            login_result = self.client.post("/api/auth/login", {
                "username": self.test_phone,
                "password": reset_password
            }, use_token=False)

            if login_result.get("code") == 1:
                print_success("重置密码登录验证成功")
                # 更新token
                data = login_result.get("data", {})
                self.client.set_token(data.get("access_token"))
                return True
            else:
                print_error("重置密码登录验证失败")
                return False
        except Exception as e:
            print_error(f"重置密码异常: {e}")
            return False

    def test_logout(self) -> bool:
        """测试用户登出"""
        print_step("11. 用户登出")

        try:
            result = self.client.post("/api/auth/logout", use_token=True)

            if result.get("code") != 1:
                print_error(f"登出失败: {result}")
                return False

            print_success("登出成功")
            print_info("注意：JWT无状态认证，登出主要在前端删除token")
            return True
        except Exception as e:
            print_error(f"登出异常: {e}")
            return False

    def test_register_duplicate_phone(self) -> bool:
        """测试重复手机号注册"""
        print_step("12. 重复手机号注册（预期失败）")

        try:
            result = self.client.post("/api/auth/register", {
                "phone": self.test_phone,
                "password": generate_random_password(),
                "nickname": "重复用户",
                "sms_code": "123456"
            }, use_token=False)

            # 预期失败
            if result.get("code") == 1:
                print_error("重复手机号注册成功（不应该）")
                return False

            print_success("重复手机号注册被正确拒绝")
            print_result("错误信息", result.get("message"))
            return True
        except Exception as e:
            print_error(f"测试异常: {e}")
            return False

    def test_login_with_user_id(self) -> bool:
        """测试使用用户ID登录"""
        print_step("13. 使用用户ID登录")

        user_id = self.test_data.get("user_id")
        if not user_id:
            print_info("跳过：没有可用的用户ID")
            return True

        try:
            result = self.client.post("/api/auth/login", {
                "username": user_id,
                "password": self.test_password
            }, use_token=False)

            if result.get("code") != 1:
                print_error(f"用户ID登录失败: {result}")
                return False

            print_success("用户ID登录成功")
            return True
        except Exception as e:
            print_error(f"用户ID登录异常: {e}")
            return False

    def run(self) -> bool:
        """运行所有测试"""
        print(f"\n{Colors.BOLD}{'='*60}")
        print(f"{Colors.BOLD}认证端到端测试")
        print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")

        tests = [
            ("前置准备", self.setup),
            ("用户注册", self.test_register),
            ("错误密码登录（预期失败）", self.test_login_with_wrong_password),
            ("正确密码登录", self.test_login_with_correct_password),
            ("获取当前用户信息", self.test_get_current_user),
            ("验证Token", self.test_verify_token),
            ("无Token访问（预期失败）", self.test_access_without_token),
            ("无效Token访问（预期失败）", self.test_access_with_invalid_token),
            ("修改密码", self.test_change_password),
            ("重置密码", self.test_reset_password),
            ("用户登出", self.test_logout),
            ("重复手机号注册（预期失败）", self.test_register_duplicate_phone),
            ("用户ID登录", self.test_login_with_user_id),
        ]

        passed = 0
        failed = 0
        results = []

        for name, test_func in tests:
            try:
                if test_func():
                    passed += 1
                    results.append((name, True))
                else:
                    failed += 1
                    results.append((name, False))
            except Exception as e:
                failed += 1
                results.append((name, False))
                print_error(f"测试异常: {e}")

        # 清理
        self.client.close()

        # 打印总结
        print_step("测试总结")
        for name, success in results:
            status = f"{Colors.GREEN}通过{Colors.END}" if success else f"{Colors.RED}失败{Colors.END}"
            print(f"  {name}: {status}")

        print(f"\n{Colors.BOLD}总计: {passed} 通过, {failed} 失败{Colors.END}\n")

        # 打印测试账号信息
        if self.test_data.get("user_id"):
            print(f"{Colors.BLUE}测试账号信息:{Colors.END}")
            print(f"  手机号: {self.test_phone}")
            print(f"  密码: {self.test_password}")
            print(f"  用户ID: {self.test_data.get('user_id')}\n")

        return failed == 0


# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数"""
    test = AuthE2ETest()
    success = test.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
