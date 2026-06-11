"""
文件管理端到端测试脚本

测试文件管理相关的完整流程：
1. 配置OSS
2. 文件上传
3. 文件列表查询
4. 文件信息获取
5. 文件更新
6. 文件下载
7. 文件删除
8. 批量操作
9. 文件统计

运行方式：
    python test/test_files_e2e.py
"""
import io
import json
import os
import random
import string
import sys
import time
from typing import Any, Dict, List, Optional
from pathlib import Path

import httpx
from dotenv import load_dotenv

# 加载 .env 文件
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


# ============================================================================
# 配置
# ============================================================================

BASE_URL = "http://127.0.0.1:8000"
TEST_TIMEOUT = 60  # 请求超时时间（秒）


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
    print(f"{Colors.GREEN}{Colors.BOLD}[OK] {message}{Colors.END}")


def print_error(message: str):
    """打印错误消息"""
    print(f"{Colors.RED}{Colors.BOLD}[FAIL] {message}{Colors.END}")


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


def generate_random_string(length: int = 8) -> str:
    """生成随机字符串"""
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_test_file_content(filename: str) -> tuple[bytes, str]:
    """生成测试文件内容"""
    # 根据文件扩展名生成不同的测试内容
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'txt'

    if ext == 'pdf':
        # PDF文件头 + 更大的内容（约2MB）
        content = b"%PDF-1.4\n" + b"Test PDF Content\n" * 50000
    elif ext == 'txt':
        # 生成更大的文本文件（约5MB）
        content = (f"Test file content: {filename}\nGenerated at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n" +
                   "X" * 5000 + "\n").encode('utf-8') * 100
    elif ext in ['jpg', 'jpeg']:
        # JPEG文件头 + 更大的内容（约1MB）
        content = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"X" * 1000000
    elif ext == 'png':
        # PNG文件头 + 更大的内容（约1MB）
        content = b"\x89PNG\r\n\x1a\n" + b"X" * 1000000
    else:
        content = (f"Test file: {filename}\n" + "X" * 10000 + "\n").encode('utf-8') * 100

    return content, ext


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
        headers = {}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def request(
        self,
        method: str,
        path: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        files: Optional[Dict] = None,
        use_token: bool = True,
    ) -> Dict:
        """发送请求"""
        url = f"{self.base_url}{path}"
        headers = self.get_headers() if use_token else {}

        try:
            if files:
                # 文件上传
                response = self.client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    files=files,
                    data=data
                )
            else:
                # 普通请求
                response = self.client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                    params=params
                )

            return response.json()
        except httpx.TimeoutException:
            raise Exception(f"请求超时: {method} {url}")
        except Exception as e:
            raise Exception(f"请求失败: {e}")

    def get(self, path: str, params: Optional[Dict] = None) -> Dict:
        """GET 请求"""
        return self.request("GET", path, params=params)

    def post(self, path: str, data: Optional[Dict] = None, files: Optional[Dict] = None, use_token: bool = True) -> Dict:
        """POST 请求"""
        return self.request("POST", path, data=data, files=files, use_token=use_token)

    def put(self, path: str, data: Optional[Dict] = None) -> Dict:
        """PUT 请求"""
        return self.request("PUT", path, data=data)

    def delete(self, path: str, params: Optional[Dict] = None, data: Optional[Dict] = None) -> Dict:
        """DELETE 请求"""
        return self.request("DELETE", path, params=params, data=data)

    def close(self):
        """关闭客户端"""
        self.client.close()


# ============================================================================
# 测试用例
# ============================================================================

class FilesE2ETest:
    """文件管理端到端测试"""

    def __init__(self):
        self.client = APIClient()
        self.test_data: Dict[str, Any] = {}
        self.uploaded_file_ids: List[str] = []

        # 生成测试文件名
        self.test_filenames = [
            f"test_document_{generate_random_string()}.txt",
            f"test_pdf_{generate_random_string()}.pdf",
            f"test_image_{generate_random_string()}.jpg"
        ]

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

        # 登录获取token
        print_info("尝试登录测试用户...")
        try:
            # 这里需要根据实际的认证信息调整
            # 如果没有测试用户，可能需要先注册
            login_result = self.client.post("/api/auth/login", {
                "username": "test_user",
                "password": "test_password"
            }, use_token=False)

            if login_result.get("code") == 1:
                data = login_result.get("data", {})
                access_token = data.get("access_token")
                if access_token:
                    self.client.set_token(access_token)
                    self.test_data["user_id"] = data.get("user_info", {}).get("user_id")
                    print_success("用户登录成功")
                    return True

            # 如果登录失败，尝试注册测试用户
            print_info("登录失败，尝试注册测试用户...")
            register_result = self.client.post("/api/auth/register", {
                "phone": f"1{random.randint(3, 9)}{random.randint(0, 9)}{random.randint(0, 9)}{random.randint(10000000, 99999999)}",
                "password": "test123456",
                "nickname": "文件测试用户",
                "sms_code": "123456"
            }, use_token=False)

            if register_result.get("code") == 1:
                data = register_result.get("data", {})
                access_token = data.get("access_token")
                if access_token:
                    self.client.set_token(access_token)
                    self.test_data["user_id"] = data.get("user_info", {}).get("user_id")
                    print_success("测试用户注册并登录成功")
                    return True

            print_error("认证失败，无法继续测试")
            return False

        except Exception as e:
            print_error(f"认证过程异常: {e}")
            return False

    def test_configure_oss(self) -> bool:
        """测试配置OSS"""
        print_step("2. 配置阿里云OSS")

        # 检查是否已有配置
        try:
            config_result = self.client.get("/api/files/config/oss")
            if config_result.get("data", {}).get("configured"):
                print_info("OSS已配置，跳过配置步骤")
                print_result("当前配置", config_result.get("data"))
                self.test_data["oss_configured"] = True
                return True
        except Exception as e:
            print_info(f"检查OSS配置失败（可能未配置）: {e}")

        print_info("尝试从环境变量读取OSS配置...")

        # 从环境变量读取OSS配置
        access_key_id = os.getenv("OSS_ACCESS_KEY_ID")
        access_key_secret = os.getenv("OSS_ACCESS_KEY_SECRET")
        region = os.getenv("OSS_REGION", "cn-hangzhou")
        bucket = os.getenv("OSS_BUCKET")

        # 打印环境变量读取状态（不显示敏感信息）
        print_info(f"OSS_ACCESS_KEY_ID: {'已设置' if access_key_id else '未设置'}")
        print_info(f"OSS_ACCESS_KEY_SECRET: {'已设置' if access_key_secret else '未设置'}")
        print_info(f"OSS_REGION: {region}")
        print_info(f"OSS_BUCKET: {'已设置' if bucket else '未设置'}")

        if not all([access_key_id, access_key_secret, bucket]):
            print_info("未检测到完整的OSS环境变量，跳过OSS相关测试")
            print_info("如需测试OSS功能，请设置以下环境变量：")
            print_info("  export OSS_ACCESS_KEY_ID='your_key'")
            print_info("  export OSS_ACCESS_KEY_SECRET='your_secret'")
            print_info("  export OSS_BUCKET='your_bucket'")
            print_info("  export OSS_REGION='cn-hangzhou'  # 可选，默认cn-hangzhou")
            self.test_data["oss_configured"] = False
            return True

        try:
            print_info("正在配置OSS...")
            result = self.client.post("/api/files/config/oss", {
                "access_key_id": access_key_id,
                "access_key_secret": access_key_secret,
                "region": region,
                "bucket": bucket
            })

            if result.get("code") != 1:
                print_error(f"OSS配置失败: {result}")
                self.test_data["oss_configured"] = False
                return False

            self.test_data["oss_configured"] = True
            print_success("OSS配置成功")
            print_result("配置信息", {
                "bucket": result.get("data", {}).get("bucket"),
                "region": result.get("data", {}).get("region")
            })
            return True

        except Exception as e:
            print_error(f"OSS配置异常: {e}")
            self.test_data["oss_configured"] = False
            return False

    def test_upload_file(self) -> bool:
        """测试文件上传"""
        print_step("3. 文件上传")

        if not self.test_data.get("oss_configured"):
            print_info("OSS未配置，跳过文件上传测试")
            return True

        try:
            # 上传第一个测试文件
            filename = self.test_filenames[0]
            content, file_ext = generate_test_file_content(filename)

            files = {
                "file": (filename, io.BytesIO(content), "text/plain")
            }

            data = {
                "folder_path": "test_folder",
                "kb_name": "test_kb"
            }

            result = self.client.post("/api/files/upload", data=data, files=files)

            if result.get("code") != 1:
                print_error(f"文件上传失败: {result}")
                return False

            file_data = result.get("data", {})
            self.uploaded_file_ids.append(file_data.get("file_id"))
            self.test_data["uploaded_file"] = file_data

            print_success(f"文件 '{filename}' 上传成功")
            print_result("文件信息", {
                "file_id": file_data.get("file_id"),
                "file_name": file_data.get("file_name"),
                "file_size": file_data.get("file_size"),
                "file_type": file_data.get("file_type"),
                "category": file_data.get("category")
            })
            return True

        except Exception as e:
            print_error(f"文件上传异常: {e}")
            return False

    def test_upload_multiple_files(self) -> bool:
        """测试批量上传文件"""
        print_step("4. 批量上传文件")

        if not self.test_data.get("oss_configured"):
            print_info("OSS未配置，跳过批量上传测试")
            return True

        try:
            for filename in self.test_filenames[1:]:
                content, file_ext = generate_test_file_content(filename)

                files = {
                    "file": (filename, io.BytesIO(content))
                }

                result = self.client.post("/api/files/upload", files=files)

                if result.get("code") == 1:
                    file_data = result.get("data", {})
                    self.uploaded_file_ids.append(file_data.get("file_id"))
                    print_success(f"文件 '{filename}' 上传成功")

            print_info(f"共上传 {len(self.uploaded_file_ids)} 个文件")
            return True

        except Exception as e:
            print_error(f"批量上传异常: {e}")
            return False

    def test_list_files(self) -> bool:
        """测试查询文件列表"""
        print_step("5. 查询文件列表")

        try:
            result = self.client.get("/api/files/list", params={
                "page": 1,
                "page_size": 20
            })

            if result.get("code") != 1:
                print_error(f"查询文件列表失败: {result}")
                return False

            data = result.get("data", {})
            files = data.get("files", [])
            total = data.get("total", 0)

            print_success(f"查询成功，共 {total} 个文件")
            for file in files[:3]:  # 只显示前3个
                print_result("文件", {
                    "file_id": file.get("file_id"),
                    "file_name": file.get("file_name"),
                    "file_size": file.get("file_size"),
                    "category": file.get("category")
                })

            return True

        except Exception as e:
            print_error(f"查询文件列表异常: {e}")
            return False

    def test_get_file_info(self) -> bool:
        """测试获取文件信息"""
        print_step("6. 获取文件详情")

        if not self.uploaded_file_ids:
            print_info("没有已上传的文件，跳过此测试")
            return True

        try:
            file_id = self.uploaded_file_ids[0]
            result = self.client.get(f"/api/files/{file_id}")

            if result.get("code") != 1:
                print_error(f"获取文件信息失败: {result}")
                return False

            file_data = result.get("data", {})
            print_success("获取文件信息成功")
            print_result("文件详情", {
                "file_id": file_data.get("file_id"),
                "file_name": file_data.get("file_name"),
                "file_type": file_data.get("file_type"),
                "file_size": file_data.get("file_size"),
                "file_url": file_data.get("file_url"),
                "download_count": file_data.get("download_count")
            })
            return True

        except Exception as e:
            print_error(f"获取文件信息异常: {e}")
            return False

    def test_get_download_url(self) -> bool:
        """测试获取下载链接"""
        print_step("7. 获取文件下载链接")

        if not self.uploaded_file_ids:
            print_info("没有已上传的文件，跳过此测试")
            return True

        try:
            file_id = self.uploaded_file_ids[0]
            result = self.client.get(f"/api/files/{file_id}/download")

            if result.get("code") != 1:
                print_error(f"获取下载链接失败: {result}")
                return False

            download_url = result.get("data", {}).get("download_url")
            print_success("获取下载链接成功")
            print_result("下载URL", download_url[:100] + "..." if len(download_url) > 100 else download_url)
            return True

        except Exception as e:
            print_error(f"获取下载链接异常: {e}")
            return False

    def test_update_file(self) -> bool:
        """测试更新文件信息"""
        print_step("8. 更新文件信息")

        if not self.uploaded_file_ids:
            print_info("没有已上传的文件，跳过此测试")
            return True

        try:
            file_id = self.uploaded_file_ids[0]
            new_filename = f"updated_{self.test_filenames[0]}"

            result = self.client.put(f"/api/files/{file_id}", data={
                "file_name": new_filename,
                "folder_path": "updated_folder"
            })

            if result.get("code") != 1:
                print_error(f"更新文件信息失败: {result}")
                return False

            print_success("文件信息更新成功")
            print_result("更新内容", {
                "file_id": file_id,
                "new_name": new_filename,
                "new_folder": "updated_folder"
            })
            return True

        except Exception as e:
            print_error(f"更新文件信息异常: {e}")
            return False

    def test_batch_update_files(self) -> bool:
        """测试批量更新文件"""
        print_step("9. 批量更新文件")

        if len(self.uploaded_file_ids) < 2:
            print_info("文件数量不足，跳过批量更新测试")
            return True

        try:
            result = self.client.put("/api/files/batch", data={
                "file_ids": self.uploaded_file_ids[:2],
                "folder_path": "batch_updated_folder"
            })

            if result.get("code") != 1:
                print_error(f"批量更新失败: {result}")
                return False

            updated_count = result.get("data", {}).get("updated_count", 0)
            print_success(f"批量更新成功，更新了 {updated_count} 个文件")
            return True

        except Exception as e:
            print_error(f"批量更新异常: {e}")
            return False

    def test_get_file_stats(self) -> bool:
        """测试获取文件统计"""
        print_step("10. 获取文件统计信息")

        try:
            result = self.client.get("/api/files/stats/my")

            if result.get("code") != 1:
                print_error(f"获取统计信息失败: {result}")
                return False

            stats = result.get("data", {})
            print_success("获取文件统计成功")
            print_result("统计信息", {
                "total_files": stats.get("total_files"),
                "total_size_mb": stats.get("total_size_mb"),
                "today_uploads": stats.get("today_uploads"),
                "month_uploads": stats.get("month_uploads")
            })
            return True

        except Exception as e:
            print_error(f"获取统计信息异常: {e}")
            return False

    def test_list_folders(self) -> bool:
        """测试获取文件夹列表"""
        print_step("11. 获取文件夹列表")

        try:
            result = self.client.get("/api/files/folders")

            if result.get("code") != 1:
                print_error(f"获取文件夹列表失败: {result}")
                return False

            folders = result.get("data", {}).get("folders", [])
            print_success(f"获取文件夹列表成功，共 {len(folders)} 个文件夹")
            if folders:
                print_result("文件夹列表", folders[:5])  # 只显示前5个
            return True

        except Exception as e:
            print_error(f"获取文件夹列表异常: {e}")
            return False

    def test_delete_file(self) -> bool:
        """测试删除文件"""
        print_step("12. 删除文件")

        if not self.uploaded_file_ids:
            print_info("没有已上传的文件，跳过删除测试")
            return True

        try:
            file_id = self.uploaded_file_ids.pop(0)

            # 软删除
            result = self.client.delete(f"/api/files/{file_id}", params={
                "permanent": False
            })

            if result.get("code") != 1:
                print_error(f"删除文件失败: {result}")
                return False

            print_success("文件软删除成功")
            print_result("删除的文件ID", file_id)

            # 恢复到列表中用于后续清理
            self.uploaded_file_ids.insert(0, file_id)
            return True

        except Exception as e:
            print_error(f"删除文件异常: {e}")
            return False

    def test_batch_delete_files(self) -> bool:
        """测试批量删除文件"""
        print_step("13. 批量删除文件")

        if len(self.uploaded_file_ids) < 2:
            print_info("文件数量不足，跳过批量删除测试")
            return True

        try:
            # 只删除部分文件用于测试
            files_to_delete = self.uploaded_file_ids[-2:]
            remaining_ids = self.uploaded_file_ids[:-2]
            self.uploaded_file_ids = remaining_ids

            result = self.client.delete("/api/files/batch", data={
                "file_ids": files_to_delete,
                "permanent": False
            })

            if result.get("code") != 1:
                print_error(f"批量删除失败: {result}")
                return False

            deleted_count = result.get("data", {}).get("deleted_count", 0)
            print_success(f"批量删除成功，删除了 {deleted_count} 个文件")
            return True

        except Exception as e:
            print_error(f"批量删除异常: {e}")
            return False

    def cleanup(self) -> bool:
        """清理测试数据"""
        print_step("14. 清理测试数据")

        if not self.uploaded_file_ids:
            print_info("没有需要清理的文件")
            return True

        try:
            # 永久删除所有测试文件
            result = self.client.delete("/api/files/batch", data={
                "file_ids": self.uploaded_file_ids,
                "permanent": True
            })

            if result.get("code") == 1:
                deleted_count = result.get("data", {}).get("deleted_count", 0)
                print_success(f"清理成功，永久删除了 {deleted_count} 个测试文件")
            else:
                print_info("清理请求发送，但结果未知")

            return True

        except Exception as e:
            print_error(f"清理测试数据异常: {e}")
            return False

    def run(self) -> bool:
        """运行所有测试"""
        print(f"\n{Colors.BOLD}{'='*60}")
        print(f"{Colors.BOLD}文件管理端到端测试")
        print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")

        tests = [
            ("前置准备", self.setup),
            ("配置OSS", self.test_configure_oss),
            ("上传文件", self.test_upload_file),
            ("批量上传文件", self.test_upload_multiple_files),
            ("查询文件列表", self.test_list_files),
            ("获取文件详情", self.test_get_file_info),
            ("获取下载链接", self.test_get_download_url),
            ("更新文件信息", self.test_update_file),
            ("批量更新文件", self.test_batch_update_files),
            ("获取文件统计", self.test_get_file_stats),
            ("获取文件夹列表", self.test_list_folders),
            ("删除文件", self.test_delete_file),
            ("批量删除文件", self.test_batch_delete_files),
            ("清理测试数据", self.cleanup),
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

        return failed == 0


# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数"""
    test = FilesE2ETest()
    success = test.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
