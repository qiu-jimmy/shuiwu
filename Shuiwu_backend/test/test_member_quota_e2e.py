"""
Member Quota System End-to-End Test
Tests quota checking, recording, refresh, etc.
"""
import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx

# Disable proxy for httpx
import os
os.environ['NO_PROXY'] = '127.0.0.1,localhost'
if 'HTTP_PROXY' in os.environ:
    del os.environ['HTTP_PROXY']
if 'HTTPS_PROXY' in os.environ:
    del os.environ['HTTPS_PROXY']


# Test configuration
BASE_URL = "http://127.0.0.1:8000"


class MemberQuotaTester:
    """Member Quota Tester"""

    def __init__(self):
        self.base_url = BASE_URL
        self.token = None
        self.user_id = None
        self.test_user_prefix = f"test_quota_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    async def print_section(self, title: str):
        """Print test section"""
        print("\n" + "=" * 60)
        print("  " + title)
        print("=" * 60)

    async def print_result(self, success: bool, message: str):
        """Print test result"""
        status = "[PASS]" if success else "[FAIL]"
        print(f"{status} {message}")

    async def register_and_login(self) -> bool:
        """Register and login test user"""
        await self.print_section("1. Register and Login")

        try:
            # Register test user
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                # Generate a random phone number for testing
                import random
                import time
                test_phone = f"13{int(time.time() * 1000) % 90000000 + 10000000}"

                register_data = {
                    "phone": test_phone,
                    "password": "test123456",
                    "nickname": f"{self.test_user_prefix}_user",
                    "sms_code": "123456"  # Default test SMS code
                }

                response = await client.post(
                    f"{self.base_url}/api/auth/register",
                    json=register_data
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 1:
                        await self.print_result(True, f"Register user: {register_data['phone']}")
                    else:
                        # If user already exists, that's ok - try to login instead
                        if "已被注册" in data.get("message", ""):
                            await self.print_result(True, f"User already exists: {register_data['phone']}, proceeding to login")
                        else:
                            await self.print_result(False, f"Register failed: {data.get('message', 'Unknown error')}")
                            return False
                else:
                    await self.print_result(False, f"Register failed with status: {response.status_code}")
                    return False

            # Login to get token
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                login_data = {
                    "username": register_data["phone"],
                    "password": register_data["password"]
                }

                response = await client.post(
                    f"{self.base_url}/api/auth/login",
                    json=login_data
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 1:
                        self.token = data["data"]["access_token"]
                        self.user_id = data["data"]["user_info"]["user_id"]
                        await self.print_result(True, f"Login success, user_id: {self.user_id}")
                        return True
                    else:
                        await self.print_result(False, f"Login failed: {data.get('message', 'Unknown error')}")
                        return False

                await self.print_result(False, f"Login failed with status: {response.status_code}")
                return False

        except Exception as e:
            await self.print_result(False, f"Register/Login error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    async def get_member_stats(self) -> dict:
        """Get member stats"""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                response = await client.get(
                    f"{self.base_url}/api/member/stats",
                    params={"user_id": self.user_id},
                    headers={"Authorization": f"Bearer {self.token}"}
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 1:
                        return data.get("data", {})

                return {}
        except Exception as e:
            print(f"Get member stats failed: {e}")
            return {}

    async def test_daily_chats_quota(self):
        """Test daily chats quota"""
        await self.print_section("2. Test Daily Chats Quota")

        try:
            # Get initial quota
            stats = await self.get_member_stats()
            max_chats = stats.get("max_daily_chats", -1)
            today_chats = stats.get("today_chats", 0)

            print(f"Current quota: {today_chats}/{max_chats}")

            # Try to call chat endpoint
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                chat_data = {
                    "user_id": self.user_id,
                    "message": "Test message",
                    "model_id": "qwen-plus",
                    "session_id": f"test_session_{datetime.now().timestamp()}"
                }

                response = await client.post(
                    f"{self.base_url}/api/chat/chat",
                    json=chat_data,
                    headers={"Authorization": f"Bearer {self.token}"}
                )

                # Check response
                if response.status_code == 200:
                    await self.print_result(True, "Chat request success (quota check passed)")
                else:
                    data = response.json()
                    if "QUOTA_EXCEEDED" in str(data.get("code", "")):
                        await self.print_result(True, "Quota check works: daily limit reached")
                    else:
                        await self.print_result(False, f"Request failed: {data}")

                # Check if quota was recorded
                await asyncio.sleep(0.5)
                new_stats = await self.get_member_stats()
                new_chats = new_stats.get("today_chats", 0)

                print(f"After use: {new_chats}/{max_chats} (+{new_chats - today_chats})")

                if new_chats > today_chats:
                    await self.print_result(True, "Quota recorded correctly")
                else:
                    await self.print_result(False, "Quota NOT recorded (BUG!)")

        except Exception as e:
            await self.print_result(False, f"Test chat quota failed: {str(e)}")

    async def test_knowledge_base_quota(self):
        """Test knowledge base quota"""
        await self.print_section("3. Test Knowledge Base Quota")

        try:
            stats = await self.get_member_stats()
            max_kb = stats.get("max_kb_count", 5)
            kb_count = stats.get("kb_count", 0)

            print(f"KB quota: {kb_count}/{max_kb}")

            # Try to create knowledge base
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                kb_data = {
                    "user_id": self.user_id,
                    "name": f"test_kb_{datetime.now().timestamp()}",
                    "description": "Test KB",
                    "chunking_rule": "fixed_size",
                    "chunk_size": 5000,
                    "chunk_overlap": 200
                }

                response = await client.post(
                    f"{self.base_url}/api/knowledge-base/create",
                    json=kb_data,
                    headers={"Authorization": f"Bearer {self.token}"}
                )

                data = response.json()

                if response.status_code == 200 and data.get("code") == 1:
                    await self.print_result(True, "Create KB success")

                    # Check if quota was recorded
                    new_stats = await self.get_member_stats()
                    new_kb_count = new_stats.get("kb_count", 0)

                    print(f"After use: {new_kb_count}/{max_kb} (+{new_kb_count - kb_count})")

                    if new_kb_count > kb_count:
                        await self.print_result(True, "KB quota recorded")
                    else:
                        await self.print_result(False, "KB quota NOT recorded (BUG!)")
                elif "QUOTA_EXCEEDED" in str(data.get("code", "")):
                    await self.print_result(True, "KB quota limit works")
                else:
                    await self.print_result(False, f"Create KB failed: {data}")

        except Exception as e:
            await self.print_result(False, f"Test KB quota failed: {str(e)}")

    async def test_privilege_check(self):
        """Test privilege check"""
        await self.print_section("4. Test Privilege Check")

        try:
            stats = await self.get_member_stats()
            has_rag = stats.get("enable_rag", False)
            has_web_search = stats.get("enable_web_search", False)

            print(f"RAG privilege: {has_rag}")
            print(f"Web search privilege: {has_web_search}")

            # Test RAG endpoint (needs RAG privilege)
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                # First create a KB
                kb_data = {
                    "user_id": self.user_id,
                    "name": f"test_rag_kb_{datetime.now().timestamp()}",
                    "description": "Test RAG",
                    "chunking_rule": "fixed_size",
                    "chunk_size": 5000,
                    "chunk_overlap": 200
                }

                await client.post(
                    f"{self.base_url}/api/knowledge-base/create",
                    json=kb_data,
                    headers={"Authorization": f"Bearer {self.token}"}
                )

                # Test RAG search
                rag_data = {
                    "user_id": self.user_id,
                    "kb_name": kb_data["name"],
                    "query": "Test query",
                    "top_k": 5
                }

                response = await client.post(
                    f"{self.base_url}/api/knowledge-base/search",
                    json=rag_data,
                    headers={"Authorization": f"Bearer {self.token}"}
                )

                data = response.json()

                if "PRIVILEGE_REQUIRED" in str(data.get("code", "")):
                    await self.print_result(True, "RAG privilege check works")
                elif response.status_code == 200:
                    if has_rag:
                        await self.print_result(True, "RAG privilege passed")
                    else:
                        await self.print_result(False, "RAG privilege check NOT working (BUG!)")
                else:
                    await self.print_result(False, f"RAG test failed: {data}")

        except Exception as e:
            await self.print_result(False, f"Test privilege failed: {str(e)}")

    async def test_unlimited_quota(self):
        """Test unlimited quota (-1)"""
        await self.print_section("5. Test Unlimited Quota (-1)")

        try:
            stats = await self.get_member_stats()
            max_chats = stats.get("max_daily_chats", 0)

            if max_chats == -1:
                await self.print_result(True, f"User has unlimited quota (max_daily_chats = -1)")

                # Test multiple requests to ensure no limit
                for i in range(3):
                    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                        chat_data = {
                            "user_id": self.user_id,
                            "message": f"Unlimited test message {i+1}",
                            "model_id": "qwen-plus",
                            "session_id": f"test_unlimited_{datetime.now().timestamp()}_{i}"
                        }

                        response = await client.post(
                            f"{self.base_url}/api/chat/chat",
                            json=chat_data,
                            headers={"Authorization": f"Bearer {self.token}"}
                        )

                        if response.status_code == 200:
                            await self.print_result(True, f"Request {i+1} success")
                        else:
                            await self.print_result(False, f"Request {i+1} blocked")
                            break

                    await asyncio.sleep(0.3)
            else:
                await self.print_result(True, f"User has limited quota ({max_chats}/day)")

        except Exception as e:
            await self.print_result(False, f"Test unlimited quota failed: {str(e)}")

    async def test_quota_exceeded(self):
        """Test quota exceeded"""
        await self.print_section("6. Test Quota Exceeded")

        try:
            stats = await self.get_member_stats()
            max_chats = stats.get("max_daily_chats", 0)

            if max_chats <= 0 or max_chats == -1:
                await self.print_result(True, "Skip: User has no quota limit")
                return

            today_chats = stats.get("today_chats", 0)
            remaining = max_chats - today_chats

            print(f"Remaining quota: {remaining}/{max_chats}")

            if remaining > 10:
                await self.print_result(True, f"Skip: Too many remaining ({remaining})")
                await self.print_result(True, "Tip: Manually use up quota to test exceeded limit")
                return

            # Try multiple requests until exceeded
            exceeded_count = 0
            for i in range(remaining + 3):
                async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                    chat_data = {
                        "user_id": self.user_id,
                        "message": f"Exceed test message {i+1}",
                        "model_id": "qwen-plus",
                        "session_id": f"test_exceed_{datetime.now().timestamp()}_{i}"
                    }

                    response = await client.post(
                        f"{self.base_url}/api/chat/chat",
                        json=chat_data,
                        headers={"Authorization": f"Bearer {self.token}"}
                    )

                    if response.status_code == 200:
                        print(f"Request {i+1} success")
                    else:
                        data = response.json()
                        if "QUOTA_EXCEEDED" in str(data.get("code", "")):
                            exceeded_count += 1
                            await self.print_result(True, f"Request {i+1} blocked by quota")
                        else:
                            print(f"Request {i+1} failed: {data}")

                if exceeded_count > 0:
                    await self.print_result(True, f"Quota exceeded check works, blocked {exceeded_count} requests")

        except Exception as e:
            await self.print_result(False, f"Test quota exceeded failed: {str(e)}")

    async def run_all_tests(self):
        """Run all tests"""
        print("\n" + "=" * 60)
        print("  Member Quota System Test")
        print("=" * 60)

        # 1. Register and login
        if not await self.register_and_login():
            print("\n[FAIL] Test failed: Cannot register/login")
            return

        # Wait for database update
        await asyncio.sleep(1)

        # 2. Test daily chats quota
        await self.test_daily_chats_quota()
        await asyncio.sleep(0.5)

        # 3. Test knowledge base quota
        await self.test_knowledge_base_quota()
        await asyncio.sleep(0.5)

        # 4. Test privilege check
        await self.test_privilege_check()
        await asyncio.sleep(0.5)

        # 5. Test unlimited quota
        await self.test_unlimited_quota()
        await asyncio.sleep(0.5)

        # 6. Test quota exceeded
        await self.test_quota_exceeded()

        # Summary
        await self.print_section("Test Complete")
        print("\nTips:")
        print("- Quota refreshes daily at midnight (uses CURRENT_DATE)")
        print("- max_quota = -1 means unlimited usage")
        print("- Admins bypass all quota checks")
        print("- Check member_usage_logs table for usage records")


async def main():
    """Main function"""
    tester = MemberQuotaTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
