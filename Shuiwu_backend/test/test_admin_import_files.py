# -*- coding: utf-8 -*-
"""
测试管理员导入文件到知识库接口
"""
import httpx
import asyncio
import sys
import io

# 设置stdout编码为utf-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


async def test_admin_import_files():
    """测试管理员导入文件功能"""
    base_url = "http://127.0.0.1:8000"

    print("=" * 60)
    print("管理员导入文件到知识库接口测试")
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
        print("\n[步骤2] 查询文件系统中的文件...")
        response = await client.get(
            f"{base_url}/api/files/list",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        if response.status_code != 200:
            print(f"[ERROR] 查询文件失败: {response.text}")
            return

        data = response.json()
        if data.get("code") != 1:
            print(f"[ERROR] 查询文件失败: {data.get('message')}")
            return

        files = data.get("data", {}).get("files", [])
        print(f"[OK] 找到 {len(files)} 个文件")

        if not files:
            print("[WARN] 文件系统中没有文件，请先上传文件")
            return

        # 显示文件列表
        print("\n文件列表:")
        for i, f in enumerate(files[:5]):
            print(f"  {i+1}. {f.get('file_name')} (ID: {f.get('file_id')}, 所有者: {f.get('user_id')})")

        # 3. 直接使用测试数据
        print("\n[步骤3] 准备测试数据...")
        # 使用文件列表中第一个用户的知识库
        test_file_owner = files[0].get('user_id')
        print(f"[OK] 使用用户的知识库进行测试")
        print(f"  知识库用户: {test_file_owner}")

        # 4. 测试管理员导入其他用户的文件
        print("\n[步骤4] 测试管理员导入功能...")

        # 选择一个不属于知识库拥有者的文件
        test_file = None
        for f in files:
            if f.get('user_id') != test_file_owner:
                test_file = f
                break

        if not test_file:
            print("[WARN] 没有找到其他用户的文件，使用第一个文件测试")
            test_file = files[0]
            test_kb_name = "test_kb_" + test_file_owner[:8]
        else:
            # 创建一个临时知识库名称
            test_kb_name = "test_kb_admin_import"

        file_id = test_file.get('file_id')
        file_name = test_file.get('file_name')
        file_owner = test_file.get('user_id')

        print(f"\n导入信息:")
        print(f"  目标知识库: {test_kb_name} (所有者: {test_file_owner})")
        print(f"  文件: {file_name} (ID: {file_id}, 所有者: {file_owner})")
        print(f"  是否跨用户导入: {'是' if file_owner != test_file_owner else '否'}")

        import_data = {
            "kb_name": test_kb_name,
            "user_id": test_file_owner,
            "file_ids": [file_id]
        }

        response = await client.post(
            f"{base_url}/api/knowledge-base/import-files",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=import_data
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
                if r.get("filename"):
                    print(f"  文件名: {r.get('filename')}")

        # 5. 验证导入结果
        if data.get("code") == 1:
            print("\n[步骤5] 验证导入结果...")
            await asyncio.sleep(2)

            response = await client.post(
                f"{base_url}/api/knowledge-base/search",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={
                    "user_id": test_file_owner,
                    "kb_name": test_kb_name,
                    "query": " ",
                    "top_k": 100
                }
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 1:
                    results = data.get("data", {}).get("results", [])
                    print(f"[OK] 知识库中现在有 {len(results)} 个文档分块")

    print("\n" + "=" * 60)
    print("[完成] 测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_admin_import_files())
