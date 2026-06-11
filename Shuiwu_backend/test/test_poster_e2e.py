"""
分销海报生成测试

测试范围：
1. 生成带小程序码的分销海报
2. 验证海报base64数据
3. 保存海报图片到本地
"""
import httpx
import base64
import sys
import os
from datetime import datetime

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


class PosterE2ETest:
    """分销海报生成测试"""

    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.client = httpx.Client(timeout=30.0)

    def __del__(self):
        if hasattr(self, 'client'):
            self.client.close()

    def print_step(self, step_name: str, result: bool, message: str):
        """打印测试步骤结果"""
        status = f"{Colors.GREEN}PASS{Colors.RESET}" if result else f"{Colors.RED}FAIL{Colors.RESET}"
        print(f"{status} {step_name}: {message}")

    def print_section(self, title: str):
        """打印测试章节"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}  {title}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}\n")

    def test_generate_poster(self, token: str, page: str = None) -> bool:
        """测试生成分销海报"""
        print(f"{Colors.YELLOW}测试生成分销海报...{Colors.RESET}")

        try:
            # 构建请求URL
            url = f"{self.base_url}/api/distribution/mini-qrcode"
            if page:
                url += f"?page={page}"

            # 发送请求
            response = self.client.get(
                url,
                headers={"Authorization": f"Bearer {token}"}
            )

            data = response.json()

            if data.get("code") != 1:
                self.print_step("生成海报", False, data.get("message", "未知错误"))
                return False

            # 获取base64数据
            poster_base64 = data.get("data", {}).get("base64")
            distributor_code = data.get("data", {}).get("distributor_code")

            if not poster_base64:
                self.print_step("生成海报", False, "未返回base64数据")
                return False

            self.print_step("生成海报", True, f"推广码: {distributor_code}, 数据大小: {len(poster_base64)} 字符")

            # 保存海报到本地
            self._save_poster(poster_base64, distributor_code)

            return True

        except Exception as e:
            self.print_step("生成海报", False, f"异常: {str(e)}")
            return False

    def _save_poster(self, base64_data: str, distributor_code: str):
        """保存海报图片到本地"""
        try:
            # 创建输出目录
            output_dir = "test_output"
            os.makedirs(output_dir, exist_ok=True)

            # 解码base64数据
            image_data = base64.b64decode(base64_data)

            # 生成文件名（带时间戳）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"poster_{distributor_code}_{timestamp}.png"
            filepath = os.path.join(output_dir, filename)

            # 保存图片
            with open(filepath, "wb") as f:
                f.write(image_data)

            file_size_kb = len(image_data) / 1024
            print(f"{Colors.GREEN}海报已保存到: {filepath} ({file_size_kb:.1f} KB){Colors.RESET}")

        except Exception as e:
            print(f"{Colors.RED}保存海报失败: {str(e)}{Colors.RESET}")


def main():
    """主测试函数"""
    print(f"{Colors.BOLD}{Colors.YELLOW}分销海报生成测试{Colors.RESET}\n")

    tester = PosterE2ETest()
    test_token = None

    # 测试用的token（需要替换为实际有效的token）
    # 可以先通过 /api/auth/register 或 /api/auth/login 获取
    env_token = os.getenv("TEST_TOKEN", "")

    if env_token:
        test_token = env_token
        print(f"{Colors.GREEN}使用环境变量中的token{Colors.RESET}\n")
    else:
        print(f"{Colors.YELLOW}未提供token，尝试注册新用户...{Colors.RESET}\n")

        # 步骤1: 注册新用户
        print(f"{Colors.YELLOW}步骤1: 注册测试用户{Colors.RESET}")
        import random
        test_phone = f"186{random.randint(10000000, 99999999)}"

        try:
            response = tester.client.post(
                f"{tester.base_url}/api/auth/register",
                json={
                    "phone": test_phone,
                    "password": "test123456",
                    "nickname": "测试分销商",
                    "sms_code": "123456"
                }
            )
            data = response.json()
            if data.get("code") == 1:
                test_token = data.get("data", {}).get("access_token")
                print(f"{Colors.GREEN}注册成功！手机号: {test_phone}{Colors.RESET}\n")
            else:
                print(f"{Colors.RED}注册失败: {data.get('message')}{Colors.RESET}\n")
                return
        except Exception as e:
            print(f"{Colors.RED}注册异常: {str(e)}{Colors.RESET}\n")
            return

        # 步骤2: 成为分销商
        print(f"{Colors.YELLOW}步骤2: 申请成为分销商{Colors.RESET}")
        try:
            response = tester.client.post(
                f"{tester.base_url}/api/distribution/become-distributor",
                headers={"Authorization": f"Bearer {test_token}"}
            )
            data = response.json()
            if data.get("code") == 1:
                distributor_code = data.get("data", {}).get("distributor_code")
                print(f"{Colors.GREEN}成为分销商成功！推广码: {distributor_code}{Colors.RESET}\n")
            else:
                print(f"{Colors.YELLOW}成为分销商失败或已是分销商: {data.get('message')}{Colors.RESET}\n")
        except Exception as e:
            print(f"{Colors.YELLOW}成为分销商异常（可能已是分销商）: {str(e)}{Colors.RESET}\n")

    # 测试章节
    tester.print_section("测试1: 生成分销海报（默认页面）")
    result1 = tester.test_generate_poster(test_token)

    tester.print_section("测试2: 生成分销海报（指定页面）")
    result2 = tester.test_generate_poster(test_token, page="pages/index/index")

    # 总结
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}测试总结{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")

    all_passed = result1 and result2
    if all_passed:
        print(f"{Colors.GREEN}所有测试通过！{Colors.RESET}")
    else:
        print(f"{Colors.RED}部分测试失败，请查看上方详情{Colors.RESET}")


if __name__ == "__main__":
    main()
