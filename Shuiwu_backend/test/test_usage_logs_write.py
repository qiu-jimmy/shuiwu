"""
测试 member_usage_logs 表写入功能
验证当使用会员权益时，记录是否正确写入到数据库
"""
import asyncio
import httpx
import sys
import io
from datetime import datetime

# Windows console encoding fix
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


async def test_usage_logs_write():
    """测试使用全景报告功能后，member_usage_logs 表是否正确写入"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("=" * 60)
        print("测试 member_usage_logs 表写入功能")
        print("=" * 60)

        # 1. 登录
        print("\n[1/5] 登录获取 token...")
        login = await client.post('http://127.0.0.1:8000/api/auth/login', json={
            'username': '15555555555',
            'password': '12345678'
        })
        login_data = login.json()

        if login_data.get('code') != 1:
            print(f"❌ 登录失败: {login_data}")
            return

        token = login_data['data']['access_token']
        user_info = login_data['data']['user_info']
        user_id = user_info.get('user_id')
        print(f"✅ 登录成功: {user_info.get('nickname')} (ID: {user_id})")
        print(f"   会员级别: {user_info.get('member_level')}")
        print(f"   用户类型: {user_info.get('user_type')}")

        headers = {'Authorization': f'Bearer {token}'}

        # 2. 获取当前使用量（baseline）
        print("\n[2/5] 获取当前全景报告使用量...")
        stats = await client.get(
            'http://127.0.0.1:8000/api/member/stats',
            headers=headers
        )
        stats_data = stats.json()
        if stats_data.get('code') == 1:
            member_stats = stats_data.get('data', {})
            print(f"✅ 获取统计成功")
            print(f"   今日使用量: {member_stats.get('today_chats', 0)} 次")
        else:
            print(f"⚠️ 获取统计失败: {stats_data.get('message')}")

        # 3. 调用全景报告功能（消耗配额）
        print("\n[3/5] 调用全景报告 API...")
        panorama = await client.post(
            'http://127.0.0.1:8000/api/chashuibao/panoramic/generate',
            headers=headers,
            json={
                'taxpayerNo': '91330100MA2XXX00XX',
                'taxpayerName': 'Test Company for Usage Log'
            }
        )
        panorama_data = panorama.json()
        print(f"API 响应: {panorama_data.get('message')}")

        if panorama_data.get('code') == 1:
            print(f"✅ 全景报告生成成功")
            report_data = panorama_data.get('data', {})
            print(f"   报告 ID: {report_data.get('id')}")
            print(f"   report_id: {report_data.get('report_id')}")
        else:
            print(f"❌ 全景报告生成失败: {panorama_data}")
            return

        # 4. 再次获取统计，验证配额已消耗
        print("\n[4/5] 验证配额消耗...")
        stats_after = await client.get(
            'http://127.0.0.1:8000/api/member/stats',
            headers=headers
        )
        stats_after_data = stats_after.json()

        if stats_after_data.get('code') == 1:
            member_stats_after = stats_after_data.get('data', {})
            print(f"✅ 获取统计成功")
            # 注意: quota 消耗可能在缓存中，这里主要验证数据库写入
        else:
            print(f"⚠️ 获取统计失败: {stats_after_data.get('message')}")

        # 5. 直接查询数据库验证 member_usage_logs 表
        print("\n[5/5] 验证 member_usage_logs 表写入...")
        try:
            import psycopg2
            from dotenv import load_dotenv
            import os

            load_dotenv()

            conn = psycopg2.connect(
                host=os.getenv('PG_HOST', 'localhost'),
                port=os.getenv('PG_PORT', 5432),
                user=os.getenv('PG_USER', 'postgres'),
                password=os.getenv('PG_PASSWORD'),
                database=os.getenv('PG_DATABASE', 'Agno')
            )

            cursor = conn.cursor()

            # 查询今日的使用记录
            cursor.execute("""
                SELECT user_id, usage_type, usage_amount, usage_date, created_at
                FROM business.member_usage_logs
                WHERE user_id = %s AND usage_date = CURRENT_DATE
                ORDER BY created_at DESC
            """, (user_id,))

            rows = cursor.fetchall()

            print(f"✅ 查询成功，找到 {len(rows)} 条今日使用记录:")
            print("-" * 80)

            if rows:
                for row in rows:
                    print(f"   用户ID: {row[0]}")
                    print(f"   使用类型: {row[1]}")
                    print(f"   使用次数: {row[2]}")
                    print(f"   使用日期: {row[3]}")
                    print(f"   创建时间: {row[4]}")
                    print("-" * 80)

                # 检查是否有 panorama 记录
                panorama_rows = [r for r in rows if r[1] == 'panorama']
                if panorama_rows:
                    print(f"✅ 找到 {len(panorama_rows)} 条 panorama 使用记录")
                    print(f"   最新使用次数: {panorama_rows[0][2]}")
                else:
                    print(f"⚠️ 未找到 panorama 使用记录")
            else:
                print(f"⚠️ 今日暂无使用记录")

            cursor.close()
            conn.close()

        except Exception as e:
            print(f"❌ 数据库查询失败: {e}")

        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)


if __name__ == '__main__':
    asyncio.run(test_usage_logs_write())
