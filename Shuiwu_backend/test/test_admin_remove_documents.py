# -*- coding: utf-8 -*-
"""
测试管理员删除知识库文档接口 - 直接测试版

使用指定的知识库进行测试：
- kb_name: 测试知识库2
- user_id: user_b39bf3ddb9c14413
- table_name: kb_user_b39bf3ddb9c14413_测试知识库2
"""
import httpx
import asyncio
import sys
import io

# 设置stdout编码为utf-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


class AdminRemoveDocumentsTester:
    """管理员删除文档测试器"""

    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.admin_token = None
        # 指定的测试数据
        self.test_kb_name = "测试知识库2"
        self.test_user_id = "user_b39bf3ddb9c14413"
        self.test_table_name = "kb_user_b39bf3ddb9c14413_测试知识库2"

    async def setup(self):
        """测试前置准备：登录获取token"""
        print("=" * 60)
        print("[前置准备] 登录获取token")
        print("=" * 60)

        async with httpx.AsyncClient(timeout=30.0) as client:
            # 管理员登录
            admin_credentials = [
                {"username": "admin", "password": "admin123"},
                {"username": "admin", "password": "123456"},
                {"username": "super_admin", "password": "admin123"},
            ]

            for cred in admin_credentials:
                try:
                    response = await client.post(
                        f"{self.base_url}/api/auth/login",
                        json=cred
                    )
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("code") == 1:
                            self.admin_token = data["data"]["access_token"]
                            print(f"[OK] 管理员登录成功: {cred['username']}")
                            print(f"     Token: {self.admin_token[:50]}...")
                            break
                except Exception as e:
                    continue

            if not self.admin_token:
                print("[ERROR] 管理员登录失败")
                return False

            # 验证用户权限
            print("\n[验证] 检查用户权限...")
            try:
                # 调用一个需要管理员权限的接口来验证
                test_response = await client.get(
                    f"{self.base_url}/api/knowledge-base/list",
                    headers={"Authorization": f"Bearer {self.admin_token}"}
                )

                # 尝试解析token获取用户信息
                import base64
                import json

                # JWT token 解码 (只解码 payload 部分)
                parts = self.admin_token.split('.')
                if len(parts) >= 2:
                    payload = parts[1]
                    # 添加填充
                    payload += '=' * (4 - len(payload) % 4)
                    decoded = base64.b64decode(payload)
                    user_info = json.loads(decoded)
                    print(f"  Token中的用户ID: {user_info.get('sub', 'N/A')}")

            except Exception as e:
                print(f"  [WARN] 无法解析token: {e}")

        return True

    async def test_list_documents(self):
        """测试：列出知识库中的文档"""
        print("\n" + "=" * 60)
        print("[步骤1] 查询知识库中的文档")
        print("=" * 60)
        print(f"kb_name: {self.test_kb_name}")
        print(f"user_id: {self.test_user_id}")
        print(f"table_name: {self.test_table_name}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            # 通过 search 接口获取文档列表（搜索空字符串获取所有）
            print("\n[查询] 文档列表（通过搜索接口）...")
            search_response = await client.post(
                f"{self.base_url}/api/knowledge-base/search",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                json={
                    "user_id": self.test_user_id,
                    "kb_name": self.test_kb_name,
                    "query": " ",  # 空格搜索
                    "top_k": 100
                }
            )

            if search_response.status_code == 200:
                search_data = search_response.json()
                print(f"响应码: {search_data.get('code')}")
                print(f"消息: {search_data.get('message')}")

                if search_data.get("code") == 1:
                    results = search_data.get("data", {}).get("results", [])
                    print(f"找到 {len(results)} 个搜索结果")

                    if len(results) == 0:
                        print("\n[WARN] 知识库中没有文档，请先上传文档")
                        return {}

                    # 按文件名分组统计
                    file_stats = {}
                    for r in results:
                        meta = r.get("meta_data", {})
                        filename = meta.get("filename") or r.get("name", "未知")
                        file_id = meta.get("file_id", "")

                        if filename not in file_stats:
                            file_stats[filename] = {"file_id": file_id, "count": 0}
                        file_stats[filename]["count"] += 1

                    print(f"\n文件列表（按文件名分组）:")
                    for i, (filename, info) in enumerate(file_stats.items(), 1):
                        print(f"  {i}. {filename}")
                        print(f"     file_id: {info['file_id']}")
                        print(f"     分块数: {info['count']}")

                    return file_stats
                else:
                    print(f"[ERROR] 搜索失败: {search_data.get('message')}")
            else:
                print(f"查询失败: {search_response.text}")

            return {}

    async def test_remove_by_filename(self, file_stats):
        """测试：按filename删除文档"""
        print("\n" + "=" * 60)
        print("[步骤2] 按filename删除文档")
        print("=" * 60)

        if not file_stats:
            print("[WARN] 没有可删除的文件")
            return

        # 获取第一个文件
        first_filename = list(file_stats.keys())[0]
        first_file_id = file_stats[first_filename]["file_id"]

        print(f"准备删除:")
        print(f"  filename: {first_filename}")
        print(f"  file_id: {first_file_id if first_file_id else '(空)'}")
        print(f"  分块数: {file_stats[first_filename]['count']}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/knowledge-base/admin/remove-documents",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                json={
                    "kb_name": self.test_kb_name,
                    "user_id": self.test_user_id,
                    "filenames": [first_filename],
                    "delete_from_file_system": False
                }
            )

            print(f"\n删除结果:")
            print(f"  状态码: {response.status_code}")
            data = response.json()
            print(f"  响应码: {data.get('code')}")
            print(f"  消息: {data.get('message')}")

            if data.get("data"):
                results = data["data"].get("results", [])
                for r in results:
                    status_icon = "[OK]" if r.get("status") == "success" else "[FAIL]"
                    print(f"  {status_icon} {r.get('message')}")

            # 验证删除
            print(f"\n[验证] 重新查询文档列表...")
            await asyncio.sleep(1)

            # 通过搜索接口验证
            verify_response = await client.post(
                f"{self.base_url}/api/knowledge-base/search",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                json={
                    "user_id": self.test_user_id,
                    "kb_name": self.test_kb_name,
                    "query": " ",
                    "top_k": 100
                }
            )

            if verify_response.status_code == 200:
                verify_data = verify_response.json()
                if verify_data.get("code") == 1:
                    results = verify_data.get("data", {}).get("results", [])
                    remaining_count = len(results)
                    print(f"  剩余文档分块数: {remaining_count}")

                    # 检查被删除的文件是否还存在
                    remaining_files = set()
                    for r in results:
                        meta = r.get("meta_data", {})
                        filename = meta.get("filename") or r.get("name", "")
                        remaining_files.add(filename)

                    if first_filename not in remaining_files:
                        print(f"  [OK] 文件 '{first_filename}' 已成功删除")
                    else:
                        print(f"  [WARN] 文件 '{first_filename}' 仍然存在")

    async def test_remove_by_file_id(self, file_stats):
        """测试：按file_id删除文档"""
        print("\n" + "=" * 60)
        print("[步骤3] 按file_id删除文档")
        print("=" * 60)

        # 找一个有 file_id 的文件
        target_file = None
        for filename, info in file_stats.items():
            if info["file_id"]:
                target_file = (filename, info["file_id"], info["count"])
                break

        if not target_file:
            print("[WARN] 没有找到有 file_id 的文件，跳过此测试")
            print("提示: 这通常是因为文档是通过 base64 上传的，没有关联 file_id")
            return

        filename, file_id, count = target_file
        print(f"准备删除:")
        print(f"  filename: {filename}")
        print(f"  file_id: {file_id}")
        print(f"  分块数: {count}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/knowledge-base/admin/remove-documents",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                json={
                    "kb_name": self.test_kb_name,
                    "user_id": self.test_user_id,
                    "file_ids": [file_id],
                    "delete_from_file_system": False
                }
            )

            print(f"\n删除结果:")
            print(f"  状态码: {response.status_code}")
            data = response.json()
            print(f"  响应码: {data.get('code')}")
            print(f"  消息: {data.get('message')}")

            if data.get("data"):
                results = data["data"].get("results", [])
                for r in results:
                    status_icon = "[OK]" if r.get("status") == "success" else "[FAIL]"
                    print(f"  {status_icon} {r.get('message')}")

    async def test_error_cases(self):
        """测试：错误场景"""
        print("\n" + "=" * 60)
        print("[步骤4] 测试错误场景")
        print("=" * 60)

        async with httpx.AsyncClient(timeout=30.0) as client:

            # 测试1: 不提供file_ids和filenames
            print("\n[测试1] 不提供file_ids和filenames")
            response = await client.post(
                f"{self.base_url}/api/knowledge-base/admin/remove-documents",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                json={
                    "kb_name": self.test_kb_name,
                    "user_id": self.test_user_id,
                }
            )
            data = response.json()
            print(f"  状态码: {response.status_code}")
            print(f"  结果: {data.get('message')}")

            # 测试2: 同时提供file_ids和filenames
            print("\n[测试2] 同时提供file_ids和filenames")
            response = await client.post(
                f"{self.base_url}/api/knowledge-base/admin/remove-documents",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                json={
                    "kb_name": self.test_kb_name,
                    "user_id": self.test_user_id,
                    "file_ids": ["test_id"],
                    "filenames": ["test.txt"]
                }
            )
            data = response.json()
            print(f"  状态码: {response.status_code}")
            print(f"  结果: {data.get('message')}")

            # 测试3: file_id不存在
            print("\n[测试3] file_id不存在")
            response = await client.post(
                f"{self.base_url}/api/knowledge-base/admin/remove-documents",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                json={
                    "kb_name": self.test_kb_name,
                    "user_id": self.test_user_id,
                    "file_ids": ["nonexistent_file_id_12345"],
                    "delete_from_file_system": False
                }
            )
            data = response.json()
            print(f"  状态码: {response.status_code}")
            print(f"  结果: {data.get('message')}")

            if data.get("data"):
                results = data["data"].get("results", [])
                for r in results:
                    print(f"    - {r.get('message')}")

    async def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "=" * 60)
        print("管理员删除知识库文档接口测试")
        print(f"测试知识库: {self.test_kb_name}")
        print(f"测试用户: {self.test_user_id}")
        print("=" * 60)

        # 前置准备
        if not await self.setup():
            print("\n[ERROR] 前置准备失败，测试终止")
            return

        # 步骤1: 查询文档列表
        file_stats = await self.test_list_documents()

        if file_stats:
            # 步骤2: 按filename删除
            await self.test_remove_by_filename(file_stats)

            # 步骤3: 按file_id删除
            await self.test_remove_by_file_id(file_stats)
        else:
            print("\n[WARN] 没有找到文档，跳过删除测试")

        # 步骤4: 错误场景测试
        await self.test_error_cases()

        print("\n" + "=" * 60)
        print("[完成] 所有测试场景执行完毕")
        print("=" * 60)


async def main():
    """主函数"""
    tester = AdminRemoveDocumentsTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
