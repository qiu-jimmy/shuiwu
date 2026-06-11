# -*- coding: utf-8 -*-
"""
测试小程序码生成功能
"""
import httpx
import json
import time
import base64

# 配置
BASE_URL = "http://127.0.0.1:8000"


def print_section(title):
    """打印分隔线"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_mini_qrcode():
    """测试小程序码生成流程"""

    # 第一步：注册并登录
    print_section("步骤1：注册新用户")

    timestamp = int(time.time())
    test_user = {
        "phone": f"188{timestamp % 100000000:08d}",
        "nickname": "测试分销商",
        "password": "Test123456",
        "sms_code": "123456"  # 测试环境验证码（已跳过验证）
        # referral_code 不填写，使用默认值 None
    }

    print(f"注册用户: {test_user['phone']}")

    response = httpx.post(f"{BASE_URL}/api/auth/register", json=test_user)
    print(f"注册响应: {response.status_code}")

    if response.status_code != 200:
        print(f"注册失败: {response.text}")
        return

    register_data = response.json()
    if register_data.get("code") != 1:
        print(f"注册失败: {register_data}")
        return

    print("[OK] 注册成功")

    # 第二步：登录获取token
    print_section("步骤2：登录获取Token")

    login_data = {
        "username": test_user["phone"],  # username 可以是手机号
        "password": test_user["password"]
    }

    response = httpx.post(f"{BASE_URL}/api/auth/login", json=login_data)
    print(f"登录响应: {response.status_code}")

    if response.status_code != 200:
        print(f"登录失败: {response.text}")
        return

    login_result = response.json()
    if login_result.get("code") != 1:
        print(f"登录失败: {login_result}")
        return

    access_token = login_result["data"]["access_token"]
    print(f"[OK] 登录成功，获取到 Token")

    # 第三步：成为分销商
    print_section("步骤3：申请成为分销商")

    headers = {"Authorization": f"Bearer {access_token}"}

    response = httpx.post(f"{BASE_URL}/api/distribution/become-distributor", headers=headers)
    print(f"成为分销商响应: {response.status_code}")

    if response.status_code != 200:
        print(f"成为分销商失败: {response.text}")
        return

    become_result = response.json()
    if become_result.get("code") != 1:
        print(f"成为分销商失败: {become_result}")
        return

    distributor_code = become_result["data"]["distributor_code"]
    print(f"[OK] 成为分销商成功")
    print(f"  推广码: {distributor_code}")

    # 第四步：获取推广码信息
    print_section("步骤4：获取推广码信息")

    response = httpx.get(f"{BASE_URL}/api/distribution/my-code", headers=headers)
    print(f"获取推广码响应: {response.status_code}")

    if response.status_code == 200:
        code_result = response.json()
        if code_result.get("code") == 1:
            print("[OK] 获取推广码成功")
            print(f"  推广码: {code_result['data']['distributor_code']}")
            print(f"  分享链接: {code_result['data']['share_link']}")
            print(f"  分享文案: {code_result['data']['share_text']}")

    # 第五步：测试所有模板
    print_section("步骤5：测试所有海报模板")

    for img in [1, 2, 3, 4]:
        print(f"\n--- 测试模板 {img} ---")

        response = httpx.post(
            f"{BASE_URL}/api/distribution/mini-qrcode",
            headers=headers,
            json={"img": img}
        )

        print(f"响应状态: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            if result.get("code") == 1:
                data = result.get("data", {})
                base64_str = data.get("base64")
                qrcode_data = base64.b64decode(base64_str)

                # 保存小程序码
                filename = f"test_qrcode_{distributor_code}_img{img}.png"
                with open(filename, "wb") as f:
                    f.write(qrcode_data)
                print(f"[OK] 模板{img}生成成功，已保存为: {filename}")
                print(f"  图片大小: {len(qrcode_data)} bytes")
            else:
                print(f"[FAIL] 模板{img}生成失败: {result}")
        else:
            print(f"[FAIL] 模板{img}生成失败: {response.text}")

    # 第六步：测试带page参数
    print_section("步骤6：测试指定页面")

    response = httpx.post(
        f"{BASE_URL}/api/distribution/mini-qrcode",
        headers=headers,
        json={"img": 1, "page": "pages/index/index"}
    )

    print(f"响应状态: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        if result.get("code") == 1:
            data = result.get("data", {})
            base64_str = data.get("base64")
            qrcode_data = base64.b64decode(base64_str)

            filename = f"test_qrcode_{distributor_code}_with_page.png"
            with open(filename, "wb") as f:
                f.write(qrcode_data)
            print(f"[OK] 带页面参数生成成功，已保存为: {filename}")
            print(f"  图片大小: {len(qrcode_data)} bytes")
        else:
            print(f"[FAIL] 生成失败: {result}")
    else:
        print(f"[FAIL] 生成失败: {response.text}")

    # 测试场景解析说明
    print_section("小程序码使用说明")
    print(f"""
小程序码已生成，scene 参数包含推广码: {distributor_code}

小程序端使用方法：
1. 用户扫描小程序码进入小程序
2. 在 app.js 或页面 onLoad 中解析 scene 参数：
3. 用户注册时，自动填入邀请码：
```javascript
// 注册时读取邀请码
const inviteCode = wx.getStorageSync('inviteCode') || '';
this.setData({{ inviteCode }});
```
    """)

    print_section("测试完成")
    print(f"推广码: {distributor_code}")
    print(f"手机号: {test_user['phone']}")
    print(f"密码: {test_user['password']}")
    print("=" * 60)


if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║           微信小程序码生成功能测试                        ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    try:
        test_mini_qrcode()
    except KeyboardInterrupt:
        print("\n\n测试中断")
    except Exception as e:
        print(f"\n\n测试异常: {e}")
        import traceback
        traceback.print_exc()
