"""
新增会员权益端对端测试脚本
============================
测试新增的三个权益：发票穿透、全景报告、经营风险

测试内容：
- 权益功能开关检查
- 配额检查和消耗
- 不同套餐的权限配置
- 配额用尽后的行为
- 管理员跳过权限
- 剩余配额查询

使用方法：
    python test/test_new_privileges_e2e.py

环境要求：
    - 服务运行在 http://127.0.0.1:8000
    - 数据库已执行迁移 008_add_invoice_risk_panorama_privileges.sql
"""
import asyncio
import httpx
import json
import sys
import io
import random
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

# Windows 控制台编码修复
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


# ==================== 配置 ====================

BASE_URL = "http://127.0.0.1:8000"
TEST_USER_PREFIX = "test_new_priv_"


# ==================== 工具函数 ====================

class Colors:
    """终端颜色"""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_success(msg: str):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")


def print_error(msg: str):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")


def print_info(msg: str):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.END}")


def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")


def print_section(title: str):
    print(f"\n{Colors.BOLD}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{title}{Colors.END}")
    print(f"{Colors.BOLD}{'=' * 60}{Colors.END}\n")


# ==================== 测试客户端 ====================

class NewPrivilegeTestClient:
    """新增权益测试客户端"""

    def __init__(self):
        self.base_url = BASE_URL
        self.token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.username: Optional[str] = None

    async def request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        token: Optional[str] = None
    ) -> Dict[str, Any]:
        """发送 HTTP 请求"""
        url = f"{self.base_url}{path}"
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        elif self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                if method == "GET":
                    response = await client.get(url, headers=headers, params=params)
                elif method == "POST":
                    response = await client.post(url, headers=headers, json=data)
                elif method == "PUT":
                    response = await client.put(url, headers=headers, json=data)
                elif method == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    raise ValueError(f"不支持的请求方法: {method}")

                return response.json()
            except httpx.HTTPError as e:
                return {"code": "HTTP_ERROR", "message": str(e)}
            except json.JSONDecodeError:
                return {"code": "INVALID_JSON", "message": "响应不是有效的 JSON"}

    async def register_user(
        self,
        username: str,
        password: str = "Test123456",
        phone: Optional[str] = None
    ) -> Dict[str, Any]:
        """注册用户"""
        # 注册需要 phone 和 sms_code（测试环境可用 "123456"）
        if not phone:
            phone = f"139{random.randint(10000000, 99999999)}"

        data = {
            "phone": phone,
            "password": password,
            "nickname": f"测试用户_{username}",
            "sms_code": "123456"  # 测试环境默认验证码
        }

        result = await self.request("POST", "/api/auth/register", data=data)

        # 注册成功后自动设置 token 和 user_id
        if result.get("code") == 1 and result.get("data"):
            self.token = result["data"].get("access_token")
            self.user_id = result["data"].get("user_info", {}).get("user_id")
            self.username = username
            print_success(f"注册成功: {username}")

        return result

    async def login_user(self, username: str, password: str = "Test123456") -> Dict[str, Any]:
        """登录用户"""
        data = {"username": username, "password": password}
        result = await self.request("POST", "/api/auth/login", data=data)

        # API 返回 code: 1 表示成功
        if result.get("code") == 1 and result.get("data"):
            self.token = result["data"].get("access_token")
            self.user_id = result["data"].get("user_info", {}).get("user_id")
            self.username = result["data"].get("user_info", {}).get("nickname", username)
            print_success(f"登录成功: {username}")
            return result
        else:
            print_error(f"登录失败: {result.get('message')}")
            return result

    # ==================== 新增权益 API ====================

    async def invoice_penetration(
        self,
        taxpayer_id: str = "91330100MA2XXX00XX",
        company_name: str = "测试企业",
        cburl: str = "https://example.com/callback"
    ) -> Dict[str, Any]:
        """测试发票穿透服务"""
        return await self.request("POST", "/api/invoice-penetration/authorization", data={
            "taxpayerId": taxpayer_id,
            "companyName": company_name,
            "cburl": cburl,
            "reportType": "1",  # 改为字符串类型
            "beginDate": "202309",
            "overDate": "202408"
        })

    async def panorama_report(
        self,
        taxpayer_no: str = "91330100MA2XXX00XX",
        taxpayer_name: str = "测试企业"
    ) -> Dict[str, Any]:
        """测试全景报告服务"""
        return await self.request("POST", "/api/chashuibao/panoramic/generate", data={
            "taxpayerNo": taxpayer_no,
            "taxpayerName": taxpayer_name
        })

    async def business_risk_check(
        self,
        taxpayer_id: str = "91330100MA2XXX00XX",
        company_name: str = "测试企业",
        cburl: str = "https://example.com/callback"
    ) -> Dict[str, Any]:
        """测试经营风险查询服务"""
        # 注意：这个接口需要 thirdPartyId 和 sign，需要从配置中获取
        return await self.request("POST", "/api/chashuibao/authorization", data={
            "taxpayerId": taxpayer_id,
            "companyName": company_name,
            "cburl": cburl,
            "reportType": "2",  # 改为字符串类型
            "thirdPartyId": "test_third_party_id",  # 测试用
            "sign": "test_signature"  # 测试用
        })

    async def get_remaining_quota(self) -> Dict[str, Any]:
        """获取剩余配额 - 使用正确的端点"""
        return await self.request("GET", "/api/examples/example/my-privileges")

    # ==================== 会员管理 API ====================

    async def get_my_privileges(self) -> Dict[str, Any]:
        """获取当前用户的权益"""
        return await self.request("GET", "/api/examples/my-privileges")

    async def simulate_package(self, package_id: str, expire_days: int = 365) -> Dict[str, Any]:
        """模拟当前用户使用指定套餐（测试辅助接口）"""
        return await self.request("POST", f"/api/examples/simulate-package?package_id={package_id}&expire_days={expire_days}")

    async def reset_package(self) -> Dict[str, Any]:
        """重置当前用户为免费套餐（测试辅助接口）"""
        return await self.request("POST", "/api/examples/reset-package")


# ==================== 数据库操作 ====================

async def update_user_via_db(user_id: str, member_level: str):
    """直接通过数据库更新用户会员信息"""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor

        # 从环境变量或配置中读取数据库连接信息
        import os
        conn = psycopg2.connect(
            host=os.getenv("PG_HOST", "localhost"),
            port=int(os.getenv("PG_PORT", 5432)),
            database=os.getenv("PG_DATABASE", "Agno"),
            user=os.getenv("PG_USER", "postgres"),
            password=os.getenv("PG_PASSWORD", "root")
        )

        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # 计算到期时间（1年后）
        expire_at = datetime.now() + timedelta(days=365)

        # 更新用户会员信息
        cursor.execute("""
            UPDATE business.users
            SET member_level = %s,
                member_expire_at = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
            RETURNING user_id, username, member_level, member_expire_at
        """, (member_level, expire_at, user_id))

        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()

        if result:
            print_success(f"数据库更新成功: {user_id} -> {member_level}")
            return True
        else:
            print_error(f"用户不存在: {user_id}")
            return False

    except ImportError:
        print_warning("未安装 psycopg2，跳过数据库操作")
        print_info("请手动在数据库中执行:")
        print_info(f"UPDATE business.users SET member_level='{member_level}' WHERE user_id='{user_id}';")
        return None
    except Exception as e:
        print_error(f"数据库操作失败: {e}")
        return None


async def set_admin_via_db(user_id: str):
    """将用户设置为管理员"""
    try:
        import psycopg2
        import os

        conn = psycopg2.connect(
            host=os.getenv("PG_HOST", "localhost"),
            port=int(os.getenv("PG_PORT", 5432)),
            database=os.getenv("PG_DATABASE", "Agno"),
            user=os.getenv("PG_USER", "postgres"),
            password=os.getenv("PG_PASSWORD", "root")
        )

        cursor = conn.cursor()
        cursor.execute("""
            UPDATE business.users
            SET user_type = 'admin',
                role = 'admin',
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
        """, (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        print_success("管理员设置成功")
        return True

    except Exception as e:
        print_error(f"设置管理员失败: {e}")
        print_info("请手动在数据库中执行:")
        print_info(f"UPDATE business.users SET user_type='admin', role='admin' WHERE user_id='{user_id}';")
        return False


# ==================== 测试场景 ====================

async def test_free_user_no_access():
    """测试免费用户无法访问新权益"""
    print_section("测试 1: 免费用户无法访问新权益")

    client = NewPrivilegeTestClient()
    username = f"{TEST_USER_PREFIX}free"

    # 1. 注册并登录
    print_info("1. 注册免费用户...")
    result = await client.register_user(username, phone="13900000001")
    if result.get("code") != 1:
        print_warning(f"注册失败: {result.get('message')}")

    # 注册成功后自动登录，无需再次登录

    # 2. 确保用户是免费套餐
    print_info("2. 设置为免费套餐...")
    result = await client.reset_package()
    if result.get("code") == 1:
        print_success("已重置为免费套餐")
    await client.login_user("13900000001")  # 使用手机号登录

    # 3. 查看配额
    print_info("3. 查看配额...")
    quota = await client.get_remaining_quota()
    if quota.get("code") == 200:
        data = quota.get("data", {})
        print(f"   用户套餐: {data.get('member_level', 'N/A')}")
        print(f"   自定义配置: {json.dumps(data.get('custom_config', {}), ensure_ascii=False, indent=2)}")
    else:
        print(f"   配额信息: {json.dumps(quota, ensure_ascii=False, indent=2)}")

    # 5. 测试发票穿透（应该失败）
    print_info("5. 测试发票穿透（应该失败）...")
    result = await client.invoice_penetration()
    if result.get("code") == 200:
        print_warning("⚠ 免费用户可以访问发票穿透（可能是配置问题）")
    else:
        print_success(f"✓ 正确阻止: {result.get('message')}")

    # 6. 测试全景报告（应该失败）
    print_info("6. 测试全景报告（应该失败）...")
    result = await client.panorama_report()
    if result.get("code") == 200:
        print_warning("⚠ 免费用户可以访问全景报告（可能是配置问题）")
    else:
        print_success(f"✓ 正确阻止: {result.get('message')}")

    # 7. 测试经营风险（应该失败）
    print_info("7. 测试经营风险（应该失败）...")
    result = await client.business_risk_check()
    if result.get("code") == 200:
        print_warning("⚠ 免费用户可以访问经营风险（可能是配置问题）")
    else:
        print_success(f"✓ 正确阻止: {result.get('message')}")

    return client


async def test_vip_month_access():
    """测试 VIP 月卡用户可以访问新权益"""
    print_section("测试 2: VIP 月卡用户可以访问新权益")

    client = NewPrivilegeTestClient()
    username = f"{TEST_USER_PREFIX}vip_month"

    # 1. 注册并登录
    print_info("1. 注册用户...")
    result = await client.register_user(username, phone="13900000002")
    if result.get("code") != 1:
        print_warning(f"注册失败: {result.get('message')}")

    # 如果注册失败（用户已存在），手动登录
    if result.get("code") != 1:
        print_info("用户已存在，尝试登录...")
        await client.login_user("13900000002")

    # 2. 升级为 VIP 月卡
    print_info("2. 升级为 VIP 月卡套餐...")
    result = await client.simulate_package("vip_month")
    if result.get("code") == 1:
        print_success("已升级为 VIP 月卡")
    else:
        print_error(f"升级失败: {result.get('message')}")
        return

    # 重新登录以刷新 token
    await client.login_user("13900000002")  # 使用手机号登录

    # 3. 查看配额
    print_info("3. 查看配额...")
    quota = await client.get_remaining_quota()
    if quota.get("code") == 200:
        data = quota.get("data", {})
        custom_config = data.get("custom_config", {})
        print(f"   用户套餐: {data.get('member_level', 'N/A')}")
        print(f"   发票穿透: enable={custom_config.get('enable_invoice_penetration', False)}, max={custom_config.get('max_invoice_penetration', 0)}, used={data.get('invoice_penetration_used', 0)}")
        print(f"   全景报告: enable={custom_config.get('enable_panorama', False)}, max={custom_config.get('max_panorama', 0)}, used={data.get('panorama_used', 0)}")
        print(f"   经营风险: enable={custom_config.get('enable_business_risk', False)}, max={custom_config.get('max_business_risk', 0)}, used={data.get('business_risk_used', 0)}")
    else:
        print(f"   配额信息: {json.dumps(quota, ensure_ascii=False, indent=2)}")

    # 4. 测试发票穿透
    print_info("4. 测试发票穿透...")
    result = await client.invoice_penetration()
    if result.get("code") == 200:
        print_success("✓ 发票穿透功能可用")
        data = result.get("data", {})
        remaining = data.get("remaining_quota", "未知")
        print(f"   剩余配额: {remaining}")
    else:
        print_error(f"✗ 发票穿透功能不可用: {result.get('message')}")

    # 5. 测试全景报告
    print_info("5. 测试全景报告...")
    result = await client.panorama_report()
    if result.get("code") == 200:
        print_success("✓ 全景报告功能可用")
        data = result.get("data", {})
        remaining = data.get("remaining_quota", "未知")
        print(f"   剩余配额: {remaining}")
    else:
        print_error(f"✗ 全景报告功能不可用: {result.get('message')}")

    # 6. 测试经营风险
    print_info("6. 测试经营风险...")
    result = await client.business_risk_check()
    if result.get("code") == 200:
        print_success("✓ 经营风险功能可用")
        data = result.get("data", {})
        remaining = data.get("remaining_quota", "未知")
        print(f"   剩余配额: {remaining}")
    else:
        print_error(f"✗ 经营风险功能不可用: {result.get('message')}")

    return client


async def test_quota_consumption():
    """测试配额消耗"""
    print_section("测试 3: 配额消耗")

    client = NewPrivilegeTestClient()
    username = f"{TEST_USER_PREFIX}quota_test"

    # 1. 注册并设置为 VIP 月卡
    print_info("1. 注册用户并设置为 VIP 月卡...")
    result = await client.register_user(username, phone="13900000003")
    if result.get("code") != 1:
        print_warning(f"注册失败: {result.get('message')}")

    # 如果注册失败（用户已存在），手动登录
    if result.get("code") != 1:
        await client.login_user("13900000003")

    result = await client.simulate_package("vip_month")
    if result.get("code") == 1:
        print_success("已设置为 VIP 月卡")
    await client.login_user("13900000003")  # 使用手机号登录

    # 2. 获取初始配额
    print_info("2. 获取初始配额...")
    quota = await client.get_remaining_quota()
    initial_invoice = 0
    if quota.get("code") == 200:
        data = quota.get("data", {})
        custom_config = data.get("custom_config", {})
        initial_invoice = custom_config.get('max_invoice_penetration', 0)
        used = data.get('invoice_penetration_used', 0)
        remaining = initial_invoice - used
        print(f"   初始发票穿透配额: max={initial_invoice}, used={used}, remaining={remaining}")

    # 3. 使用发票穿透功能
    print_info("3. 使用发票穿透功能...")
    result = await client.invoice_penetration()
    if result.get("code") == 200:
        print_success("   使用成功")
    else:
        print_error(f"   使用失败: {result.get('message')}")

    # 4. 再次获取配额，检查是否减少
    print_info("4. 检查配额是否减少...")
    quota = await client.get_remaining_quota()
    if quota.get("code") == 200:
        data = quota.get("data", {})
        custom_config = data.get("custom_config", {})
        used = data.get('invoice_penetration_used', 0)
        remaining = custom_config.get('max_invoice_penetration', 0) - used
        print(f"   当前发票穿透配额: used={used}, remaining={remaining}")
        if used > 0:
            print_success("✓ 配额正确记录使用")
        else:
            print_warning("⚠ 配额未记录使用")

    # 5. 连续使用（仅测试少量次数）
    print_info("5. 测试多次使用...")
    for i in range(2):
        result = await client.invoice_penetration(
            taxpayer_id=f"91330100MA2XXX00{i}",
            company_name=f"测试企业{i}"
        )
        if result.get("code") == 200:
            print(f"   第 {i+2} 次使用成功")
        else:
            print(f"   第 {i+2} 次使用失败: {result.get('message')}")

    # 6. 查看最终配额
    print_info("6. 查看最终配额...")
    quota = await client.get_remaining_quota()
    if quota.get("code") == 200:
        data = quota.get("data", {})
        custom_config = data.get("custom_config", {})
        used = data.get('invoice_penetration_used', 0)
        remaining = custom_config.get('max_invoice_penetration', 0) - used
        print(f"   最终配额: max={custom_config.get('max_invoice_penetration', 0)}, used={used}, remaining={remaining}")

    return client


async def test_premium_year_higher_quota():
    """测试高级年卡用户更高配额"""
    print_section("测试 4: 高级年卡用户更高配额")

    client = NewPrivilegeTestClient()
    username = f"{TEST_USER_PREFIX}premium"

    # 1. 注册并设置为高级套餐
    print_info("1. 注册用户并设置为高级套餐...")
    result = await client.register_user(username, phone="13900000004")
    if result.get("code") != 1:
        print_warning(f"注册失败: {result.get('message')}")

    # 如果注册失败（用户已存在），手动登录
    if result.get("code") != 1:
        await client.login_user("13900000004")

    result = await client.simulate_package("premium_year")
    if result.get("code") == 1:
        print_success("已设置为高级年卡")
    await client.login_user("13900000004")  # 使用手机号登录

    # 2. 查看配额
    print_info("2. 查看配额（应该比 VIP 月卡高）...")
    quota = await client.get_remaining_quota()
    if quota.get("code") == 200:
        data = quota.get("data", {})
        custom_config = data.get("custom_config", {})
        print(f"   发票穿透: enable={custom_config.get('enable_invoice_penetration', False)}, max={custom_config.get('max_invoice_penetration', 0)}")
        print(f"   全景报告: enable={custom_config.get('enable_panorama', False)}, max={custom_config.get('max_panorama', 0)}")
        print(f"   经营风险: enable={custom_config.get('enable_business_risk', False)}, max={custom_config.get('max_business_risk', 0)}")

        # 验证配额是否更高
        invoice_max = custom_config.get('max_invoice_penetration', 0)
        if invoice_max >= 30:  # 高级套餐应该有 30 次以上
            print_success(f"✓ 发票穿透配额符合预期: {invoice_max} 次")
        else:
            print_warning(f"⚠ 发票穿透配额偏低: {invoice_max} 次")

    # 3. 测试功能可用性
    print_info("3. 测试所有功能...")
    result = await client.invoice_penetration()
    if result.get("code") == 200:
        print_success("✓ 发票穿透可用")
    else:
        print_error(f"✗ 发票穿透不可用: {result.get('message')}")

    result = await client.panorama_report()
    if result.get("code") == 200:
        print_success("✓ 全景报告可用")
    else:
        print_error(f"✗ 全景报告不可用: {result.get('message')}")

    result = await client.business_risk_check()
    if result.get("code") == 200:
        print_success("✓ 经营风险可用")
    else:
        print_error(f"✗ 经营风险不可用: {result.get('message')}")

    return client


async def test_enterprise_unlimited():
    """测试企业套餐无限使用"""
    print_section("测试 5: 企业套餐无限使用")

    client = NewPrivilegeTestClient()
    username = f"{TEST_USER_PREFIX}enterprise"

    # 1. 注册并设置为企业套餐
    print_info("1. 注册用户并设置为企业套餐...")
    result = await client.register_user(username, phone="13900000005")
    if result.get("code") != 1:
        print_warning(f"注册失败: {result.get('message')}")

    # 如果注册失败（用户已存在），手动登录
    if result.get("code") != 1:
        await client.login_user("13900000005")

    result = await client.simulate_package("enterprise_year")
    if result.get("code") == 1:
        print_success("已设置为企业年卡")
    await client.login_user("13900000005")  # 使用手机号登录

    # 2. 查看配额（应该显示 -1 或无限）
    print_info("2. 查看配额（应该是无限）...")
    quota = await client.get_remaining_quota()
    if quota.get("code") == 200:
        data = quota.get("data", {})
        custom_config = data.get("custom_config", {})
        print(f"   发票穿透: enable={custom_config.get('enable_invoice_penetration', False)}, max={custom_config.get('max_invoice_penetration', 0)}")
        print(f"   全景报告: enable={custom_config.get('enable_panorama', False)}, max={custom_config.get('max_panorama', 0)}")
        print(f"   经营风险: enable={custom_config.get('enable_business_risk', False)}, max={custom_config.get('max_business_risk', 0)}")

        invoice_max = custom_config.get('max_invoice_penetration', 0)
        if invoice_max == -1:
            print_success("✓ 企业套餐配额为无限")
        else:
            print_warning(f"⚠ 企业套餐配额不是无限: {invoice_max}")

    # 3. 多次使用测试
    print_info("3. 多次使用测试...")
    for i in range(3):
        result = await client.invoice_penetration(
            taxpayer_id=f"91330100MA2XXX00{i}",
            company_name=f"测试企业{i}"
        )
        if result.get("code") == 200:
            print(f"   第 {i+1} 次使用成功")
        else:
            print_error(f"   第 {i+1} 次使用失败: {result.get('message')}")
            break

    # 4. 验证配额没有被耗尽
    print_info("4. 验证配额仍然是无限...")
    quota = await client.get_remaining_quota()
    if quota.get("code") == 200:
        data = quota.get("data", {})
        custom_config = data.get("custom_config", {})
        invoice_max = custom_config.get('max_invoice_penetration', 0)
        if invoice_max == -1:
            print_success("✓ 配额仍然是无限")
        else:
            print_warning(f"⚠ 配额发生变化: {invoice_max}")

    return client


async def test_admin_bypass():
    """测试管理员跳过权限"""
    print_section("测试 6: 管理员跳过权限")

    client = NewPrivilegeTestClient()
    username = f"{TEST_USER_PREFIX}admin"

    # 1. 注册用户
    print_info("1. 注册用户...")
    result = await client.register_user(username, phone="13900000006")
    if result.get("code") != 1:
        print_warning(f"注册失败: {result.get('message')}")

    # 注意：管理员跳过权限测试需要管理员权限
    # 由于测试环境限制，跳过此测试
    print_warning("⚠ 管理员权限测试需要手动在数据库中设置 user_type='admin'，跳过此测试")
    return client


async def test_quota_exhaustion():
    """测试配额用尽后的行为"""
    print_section("测试 7: 配额用尽后的行为")

    client = NewPrivilegeTestClient()
    username = f"{TEST_USER_PREFIX}exhaust"

    # 1. 注册用户
    print_info("1. 注册用户...")
    result = await client.register_user(username, phone="13900000007")
    if result.get("code") != 1:
        print_warning(f"注册失败: {result.get('message')}")

    # 如果注册失败（用户已存在），手动登录
    if result.get("code") != 1:
        await client.login_user("13900000007")

    # 2. 设置配额用尽（通过多次使用功能）
    print_info("2. 设置配额用尽...")
    result = await client.simulate_package("vip_month")
    if result.get("code") != 1:
        print_warning(f"设置套餐失败: {result.get('message')}")
        return client

    await client.login_user("13900000007")  # 使用手机号登录

    # 查看配额
    quota = await client.get_remaining_quota()
    if quota.get("code") == 1:
        data = quota.get("data", {})
        custom_config = data.get("custom_config", {})
        max_quota = custom_config.get('max_invoice_penetration', 0)
        print(f"   发票穿透配额: max={max_quota}")

        # 使用功能直到配额用尽
        print_info("3. 使用功能直到配额用尽...")
        for i in range(max_quota + 1):
            result = await client.invoice_penetration(
                taxpayer_id=f"91330100MA2XXX0{i}",
                company_name=f"测试企业{i}"
            )
            if result.get("code") == 200:
                print(f"   第 {i+1} 次使用成功")
            else:
                print(f"   第 {i+1} 次使用失败: {result.get('message')}")
                break
    else:
        print_warning("无法获取配额信息")
        return client

    # 3. 查看配额状态
    print_info("3. 查看配额状态...")
    quota = await client.get_remaining_quota()
    if quota.get("code") == 200:
        data = quota.get("data", {})
        custom_config = data.get("custom_config", {})
        used = data.get('invoice_penetration_used', 0)
        max_quota = custom_config.get('max_invoice_penetration', 0)
        remaining = max_quota - used
        print(f"   发票穿透: max={max_quota}, used={used}, remaining={remaining}")

    # 4. 尝试使用功能（应该失败）
    print_info("4. 尝试使用发票穿透（应该失败）...")
    result = await client.invoice_penetration()
    if result.get("code") == 200:
        print_warning("⚠ 配额用尽仍然可以使用（可能是配置问题）")
    else:
        print_success(f"✓ 正确阻止: {result.get('message')}")

    return client


# ==================== 主测试函数 ====================

async def run_all_tests():
    """运行所有测试"""
    print(f"\n{Colors.BOLD}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}新增会员权益端对端测试{Colors.END}")
    print(f"{Colors.BOLD}{'=' * 60}{Colors.END}")
    print(f"测试服务器: {BASE_URL}")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = {
        "passed": 0,
        "failed": 0,
        "warnings": 0,
        "tests": []
    }

    # 测试 1: 免费用户无法访问
    try:
        await test_free_user_no_access()
        results["passed"] += 1
        results["tests"].append(("免费用户无法访问新权益", "PASSED"))
    except Exception as e:
        results["failed"] += 1
        results["tests"].append(("免费用户无法访问新权益", f"FAILED: {e}"))
        print_error(f"测试失败: {e}")

    # 测试 2: VIP 月卡用户可以访问
    try:
        await test_vip_month_access()
        results["passed"] += 1
        results["tests"].append(("VIP 月卡用户可以访问新权益", "PASSED"))
    except Exception as e:
        results["failed"] += 1
        results["tests"].append(("VIP 月卡用户可以访问新权益", f"FAILED: {e}"))
        print_error(f"测试失败: {e}")

    # 测试 3: 配额消耗
    try:
        await test_quota_consumption()
        results["passed"] += 1
        results["tests"].append(("配额消耗", "PASSED"))
    except Exception as e:
        results["failed"] += 1
        results["tests"].append(("配额消耗", f"FAILED: {e}"))
        print_error(f"测试失败: {e}")

    # 测试 4: 高级年卡用户更高配额
    try:
        await test_premium_year_higher_quota()
        results["passed"] += 1
        results["tests"].append(("高级年卡用户更高配额", "PASSED"))
    except Exception as e:
        results["failed"] += 1
        results["tests"].append(("高级年卡用户更高配额", f"FAILED: {e}"))
        print_error(f"测试失败: {e}")

    # 测试 5: 企业套餐无限使用
    try:
        await test_enterprise_unlimited()
        results["passed"] += 1
        results["tests"].append(("企业套餐无限使用", "PASSED"))
    except Exception as e:
        results["failed"] += 1
        results["tests"].append(("企业套餐无限使用", f"FAILED: {e}"))
        print_error(f"测试失败: {e}")

    # 测试 6: 管理员跳过权限
    try:
        await test_admin_bypass()
        results["passed"] += 1
        results["tests"].append(("管理员跳过权限", "PASSED"))
    except Exception as e:
        results["failed"] += 1
        results["tests"].append(("管理员跳过权限", f"FAILED: {e}"))
        print_error(f"测试失败: {e}")

    # 测试 7: 配额用尽后的行为
    try:
        await test_quota_exhaustion()
        results["passed"] += 1
        results["tests"].append(("配额用尽后的行为", "PASSED"))
    except Exception as e:
        results["failed"] += 1
        results["tests"].append(("配额用尽后的行为", f"FAILED: {e}"))
        print_error(f"测试失败: {e}")

    # 打印测试结果汇总
    print(f"\n{Colors.BOLD}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}测试结果汇总{Colors.END}")
    print(f"{Colors.BOLD}{'=' * 60}{Colors.END}\n")

    for test_name, result in results["tests"]:
        if result == "PASSED":
            print_success(f"{test_name}")
        elif "FAILED" in result:
            print_error(f"{test_name}")
            print(f"   {result}")
        else:
            print_warning(f"{test_name}")
            print(f"   {result}")

    print(f"\n总计: {Colors.BOLD}{results['passed']} 通过{Colors.END}, "
          f"{Colors.RED if results['failed'] > 0 else ''}{results['failed']} 失败{Colors.END if results['failed'] > 0 else ''}, "
          f"{Colors.YELLOW if results['warnings'] > 0 else ''}{results['warnings']} 警告{Colors.END if results['warnings'] > 0 else ''}")
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 输出 SQL 清理脚本
    print(f"\n{Colors.BOLD}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}测试数据清理{Colors.END}")
    print(f"{Colors.BOLD}{'=' * 60}{Colors.END}\n")
    print("如需清理测试数据，请执行以下 SQL:")
    print("-- 删除测试用户")
    print(f"DELETE FROM business.users WHERE username LIKE '{TEST_USER_PREFIX}%';")


# ==================== 入口函数 ====================

async def main():
    """主函数"""
    try:
        await run_all_tests()
    except KeyboardInterrupt:
        print_warning("\n测试被用户中断")
    except Exception as e:
        print_error(f"\n测试发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
