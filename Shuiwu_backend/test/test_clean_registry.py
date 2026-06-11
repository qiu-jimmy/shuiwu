# -*- coding: utf-8 -*-
"""
测试管理员删除文档接口 - 清理 registry 记录
"""
import httpx
import asyncio
import sys
import io

# 设置stdout编码为utf-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


async def test_clean_registry_records():
    """测试清理 registry 记录功能"""
    base_url = "http://127.0.0.1:8000"

    print("=" * 60)
    print("测试清理 registry 记录功能")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. 管理员登录
        print("\n[步骤1] 管理员登录...")
        response = await client.post(
            f"{base_url}/api/auth/login",
            json={"username": "admin", "password": "admin123"}
        )

        if response.status_code != 200:
            print(f"[ERROR] 登录失败: {response.text}")
            return

        data = response.json()
        if data.get("code") != 1:
            print(f"[ERROR] 登录失败: {data.get('message')}")
            return

        admin_token = data["data"]["access_token"]
        print(f"[OK] 管理员登录成功")

        # 2. 查询文件系统中的文件
        print("\n[步骤2] 查询文件列表...")
        response = await client.get(
            f"{base_url}/api/files/list",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        if response.status_code != 200:
            print(f"[ERROR] 查询文件失败: {response.text}")
            return

        data = response.json()
        files = data.get("data", {}).get("files", [])
        print(f"[OK] 找到 {len(files)} 个文件")

        if not files:
            print("[WARN] 文件系统中没有文件")
            return

        # 选择一个文件进行测试
        test_file = files[0]
        file_id = test_file.get('file_id')
        filename = test_file.get('file_name')
        file_owner = test_file.get('user_id')

        print(f"\n测试文件: {filename}")
        print(f"  file_id: {file_id}")
        print(f"  所有者: {file_owner}")

        # 3. 先尝试删除一个在知识库中不存在的文件
        print("\n[步骤3] 测试删除不存在的文件...")
        response = await client.post(
            f"{base_url}/api/knowledge-base/admin/remove-documents",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "kb_name": "系统ycc",
                "user_id": file_owner,
                "filenames": ["不存在的文件名_12345.txt"]
            }
        )

        print(f"\n状态码: {response.status_code}")
        data = response.json()
        print(f"响应码: {data.get('code')}")
        print(f"消息: {data.get('message')}")

        if data.get("data"):
            results = data["data"].get("results", [])
            for r in results:
                status_icon = "[OK]" if r.get("status") == "success" else "[FAIL]"
                print(f"\n{status_icon} 结果:")
                print(f"  状态: {r.get('status')}")
                print(f"  消息: {r.get('message')}")
                if "cleaned_count" in r:
                    print(f"  清理记录数: {r.get('cleaned_count')}")

        # 4. 测试按 filename 删除并清理 registry
        print("\n[步骤4] 测试按 filename 删除并清理 registry...")
        response = await client.post(
            f"{base_url}/api/knowledge-base/admin/remove-documents",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "kb_name": "系统ycc",
                "user_id": file_owner,
                "filenames": [filename]
            }
        )

        print(f"\n状态码: {response.status_code}")
        data = response.json()
        print(f"响应码: {data.get('code')}")
        print(f"消息: {data.get('message')}")

        if data.get("data"):
            results = data["data"].get("results", [])
            for r in results:
                status_icon = "[OK]" if r.get("status") == "success" else "[FAIL]"
                print(f"\n{status_icon} 结果:")
                print(f"  状态: {r.get('status')}")
                print(f"  消息: {r.get('message')}")
                if r.get("cleaned_count"):
                    print(f"  清理记录数: {r.get('cleaned_count')}")
                if r.get("deleted_count"):
                    print(f"  删除记录数: {r.get('deleted_count')}")

        # 5. 再次执行相同的删除操作，应该返回"已清理 registry 记录"
        print("\n[步骤5] 再次删除同一文件（测试清理 registry）...")
        await asyncio.sleep(1)

        response = await client.post(
            f"{base_url}/api/knowledge-base/admin/remove-documents",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "kb_name": "系统ycc",
                "user_id": file_owner,
                "filenames": [filename]
            }
        )

        print(f"\n状态码: {response.status_code}")
        data = response.json()
        print(f"响应码: {data.get('code')}")
        print(f"消息: {data.get('message')}")

        if data.get("data"):
            results = data["data"].get("results", [])
            for r in results:
                status_icon = "[OK]" if r.get("status") == "success" else "[FAIL]"
                print(f"\n{status_icon} 结果:")
                print(f"  状态: {r.get('status')}")
                print(f"  消息: {r.get('message')}")
                if "已清理 registry" in r.get('message', ''):
                    print(f"  ✓ 成功：文件不存在时清理了 registry 记录")

    print("\n" + "=" * 60)
    print("[完成] 测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_clean_registry_records())
