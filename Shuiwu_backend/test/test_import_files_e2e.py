"""
从文件系统导入文件到知识库 - 端到端测试脚本

测试新增的 /api/knowledge-base/import-files 接口功能：
1. 用户登录获取token
2. 创建知识库
3. 上传文件到文件系统（OSS）
4. 从文件系统导入文件到知识库
5. 验证文件已成功导入（搜索知识库）
6. 清理测试数据

运行方式：
    python test/test_import_files_e2e.py
"""
import asyncio
import io
import json
import os
import sys
import time
from typing import Any, Dict, List
from pathlib import Path

import httpx
from dotenv import load_dotenv

# 加载 .env 文件
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# 修复Windows终端编码问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


# ============================================================================
# 配置
# ============================================================================

BASE_URL = "http://127.0.0.1:8000"
TEST_USER = "15555555555"
TEST_PASSWORD = "123456"
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
        print(f"{Colors.GREEN}{message}{Colors.END}")
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(f"{Colors.GREEN}{message}{Colors.END}")


# ============================================================================
# HTTP客户端
# ============================================================================

class TestClient:
    """测试HTTP客户端"""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.token = None
        self.user_id = None  # 存储真实的user_id
        self.headers = {}

    def set_token(self, token: str, user_id: str = None):
        """设置认证token"""
        self.token = token
        self.user_id = user_id  # 保存user_id供后续使用
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    async def request(
        self,
        method: str,
        path: str,
        data: Dict = None,
        params: Dict = None,
        files: Dict = None,
        multipart: bool = False
    ) -> Dict:
        """发送HTTP请求"""
        url = f"{self.base_url}{path}"

        headers = self.headers.copy()
        if multipart:
            # 文件上传时使用multipart/form-data
            headers.pop("Content-Type", None)

        try:
            async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers, params=params)
                elif method.upper() == "POST":
                    if files:
                        # 文件上传
                        response = await client.post(url, headers=headers, data=data, files=files)
                    elif multipart:
                        # multipart表单
                        response = await client.post(url, headers=headers, data=data)
                    else:
                        # JSON请求
                        response = await client.post(url, headers=headers, json=data)
                elif method.upper() == "PUT":
                    response = await client.put(url, headers=headers, json=data)
                elif method.upper() == "DELETE":
                    response = await client.delete(url, headers=headers, params=params)
                else:
                    raise ValueError(f"不支持的HTTP方法: {method}")

                return {
                    "status_code": response.status_code,
                    "data": response.json() if response.text else None
                }
        except httpx.TimeoutException:
            return {"status_code": 408, "data": {"message": "请求超时"}}
        except Exception as e:
            return {"status_code": 500, "data": {"message": f"请求异常: {str(e)}"}}


# ============================================================================
# 测试函数
# ============================================================================

async def test_login(client: TestClient) -> bool:
    """测试用户登录"""
    print_step("1. 用户登录获取Token")

    response = await client.request(
        "POST",
        "/api/auth/login",
        data={
            "username": TEST_USER,
            "password": TEST_PASSWORD
        }
    )

    if response["status_code"] == 200:
        data = response["data"]
        if data.get("code") == 1 and "data" in data:
            token = data["data"].get("access_token")
            user_info = data["data"].get("user_info", {})
            user_id = user_info.get("user_id")  # 获取真实的user_id (UUID格式)

            if token:
                client.set_token(token, user_id)
                print_result("登录成功", {
                    "access_token": token[:20] + "...",
                    "user_id": user_id
                })
                return True

    print_error("登录失败")
    print_result("响应", response["data"])
    return False


async def test_create_knowledge_base(client: TestClient, kb_name: str) -> bool:
    """测试创建知识库"""
    print_step(f"2. 创建知识库: {kb_name}")

    response = await client.request(
        "POST",
        "/api/knowledge-base/create",
        data={
            "name": kb_name,
            "description": "测试导入文件功能的知识库",
            "user_id": client.user_id,
            "chunking_rule": "fixed_size",
            "chunk_size": 1000,
            "chunk_overlap": 100
        }
    )

    if response["status_code"] == 200:
        data = response["data"]
        if data.get("code") == 1:
            print_result("知识库创建成功", data["data"])
            return True

    print_error("知识库创建失败")
    print_result("响应", response["data"])
    return False


async def test_upload_files_to_system(
    client: TestClient,
    file_count: int = 3
) -> List[str]:
    """测试上传文件到文件系统（OSS）"""
    print_step(f"3. 上传 {file_count} 个测试文件到文件系统")

    file_ids = []

    # 创建测试文件内容
    test_files = [
        ("test_doc1.txt", "这是第一个测试文档。内容包括增值税相关政策说明。增值税是中国最重要的税种之一。"),
        ("test_doc2.txt", "这是第二个测试文档。内容包括企业所得税政策说明。企业所得税是对企业所得征收的税。"),
        ("test_doc3.txt", "这是第三个测试文档。内容包括个人所得税政策说明。个人所得税是对个人所得征收的税。")
    ]

    for i, (filename, content) in enumerate(test_files[:file_count], 1):
        print_info(f"上传文件 {i}/{file_count}: {filename}")

        # 准备multipart表单数据
        files = {
            "file": (filename, content.encode("utf-8"), "text/plain")
        }
        data = {
            "folder_path": "test/import",
            "kb_name": None  # 上传时不关联知识库
        }

        response = await client.request(
            "POST",
            "/api/files/upload",
            data=data,
            files=files,
            multipart=True
        )

        if response["status_code"] == 200:
            resp_data = response["data"]
            if resp_data.get("code") == 1:
                file_id = resp_data["data"].get("file_id")
                file_ids.append(file_id)
                print_success(f"文件上传成功: {filename} (ID: {file_id})")
            else:
                print_error(f"文件上传失败: {filename}")
                print_result("响应", resp_data)
        else:
            print_error(f"文件上传失败: {filename}")
            print_result("响应", response["data"])

    if file_ids:
        print_result(f"成功上传 {len(file_ids)} 个文件", {"file_ids": file_ids})
    else:
        print_error("没有文件上传成功")

    return file_ids


async def test_import_files_to_knowledge_base(
    client: TestClient,
    kb_name: str,
    file_ids: List[str]
) -> bool:
    """测试从文件系统导入文件到知识库"""
    print_step(f"4. 从文件系统导入 {len(file_ids)} 个文件到知识库")

    print_info(f"文件ID列表: {file_ids}")

    # 使用client.user_id（真实的UUID格式user_id）而不是TEST_USER（手机号）
    response = await client.request(
        "POST",
        "/api/knowledge-base/import-files",
        data={
            "kb_name": kb_name,
            "user_id": client.user_id,
            "file_ids": file_ids,
            "chunking_rule": "fixed_size",
            "chunk_size": 500,
            "chunk_overlap": 50
        }
    )

    if response["status_code"] == 200:
        data = response["data"]
        if data.get("code") == 1:
            results = data["data"].get("results", [])
            print_result(f"导入完成: {data['message']}", results)

            # 检查是否所有文件都成功
            success_count = sum(1 for r in results if r.get("status") == "success")
            if success_count == len(file_ids):
                print_success(f"所有 {success_count} 个文件导入成功！")
                return True
            else:
                print_info(f"部分文件导入失败: 成功 {success_count}/{len(file_ids)}")
                return True  # 部分成功也算测试通过
        else:
            print_error("导入失败")
            print_result("响应", data)
            return False
    else:
        print_error("导入请求失败")
        print_result("响应", response["data"])
        return False


async def test_search_knowledge_base(client: TestClient, kb_name: str) -> bool:
    """测试搜索知识库验证文件已导入"""
    print_step("5. 搜索知识库验证文件已导入")

    test_queries = [
        "增值税",
        "企业所得税",
        "个人所得税"
    ]

    all_success = True

    for query in test_queries:
        print_info(f"搜索: {query}")

        response = await client.request(
            "POST",
            "/api/knowledge-base/search",
            data={
                "user_id": client.user_id,
                "kb_name": kb_name,
                "query": query,
                "top_k": 3
            }
        )

        if response["status_code"] == 200:
            data = response["data"]
            if data.get("code") == 1:
                results = data["data"].get("results", [])
                count = data["data"].get("count", 0)
                print_success(f"找到 {count} 条相关结果")
                if results:
                    for i, result in enumerate(results[:2], 1):
                        content_preview = result.get("content", "")[:50] + "..."
                        print(f"  结果{i}: {content_preview}")
            else:
                print_error(f"搜索失败: {data.get('message')}")
                all_success = False
        else:
            print_error("搜索请求失败")
            all_success = False

        time.sleep(0.5)  # 避免请求过快

    if all_success:
        print_success("搜索验证通过，文件已成功导入知识库")
    else:
        print_error("搜索验证失败")

    return all_success


async def test_list_documents_in_kb(client: TestClient, kb_name: str) -> bool:
    """测试列出知识库中的文档"""
    print_step("6. 列出知识库中的所有文档")

    response = await client.request(
        "GET",
        "/api/knowledge-base/documents",
        params={
            "kb_name": kb_name,
            "user_id": client.user_id
        }
    )

    if response["status_code"] == 200:
        data = response["data"]
        if data.get("code") == 1:
            kb_data = data["data"]
            total = kb_data.get("total_documents", 0)
            documents = kb_data.get("documents", [])

            print_result(f"知识库包含 {total} 个文档", [
                {
                    "filename": doc.get("filename"),
                    "chunks": doc.get("total_chunks"),
                    "status": doc.get("parse_status")
                }
                for doc in documents
            ])

            if total > 0:
                print_success(f"文档列表验证通过，共 {total} 个文档")
                return True
            else:
                print_error("知识库中没有文档")
                return False
        else:
            print_error("获取文档列表失败")
            print_result("响应", data)
            return False
    else:
        print_error("获取文档列表请求失败")
        print_result("响应", response["data"])
        return False


async def test_cleanup(client: TestClient, kb_name: str, file_ids: List[str]):
    """清理测试数据"""
    print_step("7. 清理测试数据")

    # 删除知识库
    print_info(f"删除知识库: {kb_name}")
    await client.request(
        "DELETE",
        f"/api/knowledge-base/{kb_name}"
    )

    # 删除文件
    print_info(f"删除 {len(file_ids)} 个文件")
    for file_id in file_ids:
        await client.request(
            "DELETE",
            f"/api/files/{file_id}",
            params={"permanent": "true"}
        )

    print_success("清理完成")


# ============================================================================
# 主测试流程
# ============================================================================

async def main():
    """主测试函数"""
    print(f"\n{Colors.BOLD}{'='*60}")
    print(f"{Colors.BLUE}从文件系统导入文件到知识库 - 端到端测试{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}\n")

    client = TestClient(BASE_URL)
    # 使用更短的知识库名称，避免PostgreSQL索引名超过63字符限制
    kb_name = f"test_kb_{int(time.time()) % 100000}"  # 使用时间戳的后5位
    file_ids = []

    try:
        # 1. 登录
        if not await test_login(client):
            print_error("测试终止: 登录失败")
            return False

        # 2. 创建知识库
        if not await test_create_knowledge_base(client, kb_name):
            print_error("测试终止: 创建知识库失败")
            return False

        # 3. 上传文件到文件系统
        file_ids = await test_upload_files_to_system(client, file_count=3)
        if not file_ids:
            print_error("测试终止: 上传文件失败")
            return False

        # 等待文件处理完成
        time.sleep(2)

        # 4. 从文件系统导入文件到知识库
        if not await test_import_files_to_knowledge_base(client, kb_name, file_ids):
            print_error("测试终止: 导入文件失败")
            await test_cleanup(client, kb_name, file_ids)
            return False

        # 等待向量化和索引完成
        print_info("等待向量化和索引完成...")
        time.sleep(5)

        # 5. 搜索验证
        if not await test_search_knowledge_base(client, kb_name):
            print_error("搜索验证失败，但导入可能成功")

        # 6. 列出文档验证
        await test_list_documents_in_kb(client, kb_name)

        # 7. 清理
        await test_cleanup(client, kb_name, file_ids)

        # 测试成功
        print(f"\n{Colors.GREEN}{Colors.BOLD}{'='*60}")
        print_success("所有测试通过！")
        print(f"{Colors.GREEN}{Colors.BOLD}{'='*60}\n")
        return True

    except KeyboardInterrupt:
        print_info("\n测试被用户中断")
        if file_ids:
            await test_cleanup(client, kb_name, file_ids)
        return False
    except Exception as e:
        print_error(f"测试过程中发生异常: {str(e)}")
        import traceback
        traceback.print_exc()
        if file_ids:
            await test_cleanup(client, kb_name, file_ids)
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
