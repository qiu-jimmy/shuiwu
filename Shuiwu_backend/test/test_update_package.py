# -*- coding: utf-8 -*-
"""
测试会员套餐更新接口
"""
import httpx
import asyncio
import sys
import io

# 设置stdout编码为utf-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


async def test_update_package():
    """测试更新套餐接口"""
    base_url = "http://127.0.0.1:8000"

    print("=" * 60)
    print("会员套餐更新接口测试")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. 登录获取管理员token
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

        token = data["data"]["access_token"]
        print(f"[OK] 登录成功")

        # 2. 查询现有套餐列表
        print("\n[步骤2] 查询套餐列表...")
        response = await client.get(
            f"{base_url}/api/member/packages",
            headers={"Authorization": f"Bearer {token}"}
        )

        if response.status_code != 200:
            print(f"[ERROR] 查询失败: {response.text}")
            return

        data = response.json()
        if data.get("code") != 1:
            print(f"[ERROR] 查询失败: {data.get('message')}")
            return

        packages = data.get("data", {}).get("packages", [])
        print(f"[OK] 找到 {len(packages)} 个套餐")

        if not packages:
            print("[WARN] 没有套餐可更新")
            return

        # 选择第一个套餐进行更新测试
        test_package = packages[0]
        package_id = test_package.get("package_id")
        print(f"\n测试套餐: {test_package.get('name')} (ID: {package_id})")
        print(f"  当前价格: {test_package.get('price')}")
        print(f"  当前类型: {test_package.get('package_type')}")
        print(f"  当前有效期: {test_package.get('duration_days')} 天")

        # 3. 测试更新套餐（只更新部分字段）
        print("\n[步骤3] 更新套餐（部分字段）...")
        update_data = {
            "price": 99.99,
            "original_price": 199.99,
            "duration_days": 90
        }

        print(f"  更新数据: {update_data}")

        response = await client.put(
            f"{base_url}/api/member/packages/{package_id}",
            headers={"Authorization": f"Bearer {token}"},
            json=update_data
        )

        print(f"\n  状态码: {response.status_code}")
        data = response.json()
        print(f"  响应码: {data.get('code')}")
        print(f"  消息: {data.get('message')}")

        if data.get("code") == 1:
            updated_package = data.get("data", {})
            print(f"\n[OK] 更新成功!")
            print(f"  新价格: {updated_package.get('price')}")
            print(f"  新原价: {updated_package.get('original_price')}")
            print(f"  新有效期: {updated_package.get('duration_days')} 天")
        else:
            # 检查是否有错误详情
            if data.get("data") and isinstance(data.get("data"), dict):
                errors = data["data"].get("errors", [])
                if errors:
                    print("\n[ERROR] 验证错误:")
                    for error in errors:
                        print(f"  - {error}")
            return

        # 4. 验证更新结果
        print("\n[步骤4] 验证更新结果...")
        await asyncio.sleep(1)

        response = await client.get(
            f"{base_url}/api/member/packages/{package_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 1:
                package = data.get("data", {})
                print(f"[OK] 验证成功!")
                print(f"  价格: {package.get('price')}")
                print(f"  原价: {package.get('original_price')}")
                print(f"  有效期: {package.get('duration_days')} 天")

    print("\n" + "=" * 60)
    print("[完成] 测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_update_package())
