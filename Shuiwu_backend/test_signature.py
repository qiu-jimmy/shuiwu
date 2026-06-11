"""
微信支付签名、加解密测试脚本
"""
import os
import sys
import json
import base64

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.wechat_pay.signature import WechatPaySignature


def test_public_key_encrypt():
    """测试公钥加密敏感字段"""
    print("=" * 50)
    print("测试1: 公钥加密敏感字段")
    print("=" * 50)

    public_key_path = r"D:\download\taxation\Shuiwu_backend\certs\pub_key.pem"

    # 测试数据
    test_cases = [
        ("手机号", "13800138000"),
        ("身份证号", "110101199001011234"),
        ("银行卡号", "6222021234567890"),
        ("地址", "北京市朝阳区XX路XX号"),
        ("短字符串", "test"),
    ]

    for name, plaintext in test_cases:
        try:
            print(f"\n测试: {name}")
            print(f"  明文: {plaintext}")

            # 加密
            ciphertext = WechatPaySignature.public_key_encrypt(
                plaintext=plaintext,
                public_key_path=public_key_path
            )
            print(f"  密文: {ciphertext[:50]}..." if len(ciphertext) > 50 else f"  密文: {ciphertext}")
            print(f"  长度: {len(ciphertext)} 字符")

            # 验证密文格式（Base64）
            try:
                decoded = base64.b64decode(ciphertext)
                print(f"  [OK] Base64格式有效")
            except Exception as e:
                print(f"  [FAIL] Base64格式无效: {e}")

        except Exception as e:
            print(f"  [FAIL] 加密失败: {e}")


def test_public_key_verify():
    """测试公钥验签"""
    print("\n" + "=" * 50)
    print("测试2: 公钥验签")
    print("=" * 50)

    public_key_path = r"D:\download\taxation\Shuiwu_backend\certs\pub_key.pem"
    private_key_path = r"D:\download\taxation\Shuiwu_backend\certs\apiclient_key_pkcs8.pem.bak"

    # 构造测试消息
    test_message = "Hello WeChat Pay"
    print(f"测试消息: {test_message}")

    # 使用私钥签名
    print("\n使用私钥签名...")
    try:
        signature = WechatPaySignature.private_key_sign(
            message=test_message,
            private_key_path=private_key_path
        )
        print(f"  签名: {signature[:50]}...")
        print(f"  长度: {len(signature)} 字符")
    except Exception as e:
        print(f"  [FAIL] 签名失败: {e}")
        return

    # 使用公钥验签
    print("\n使用公钥验签...")
    try:
        result = WechatPaySignature.public_key_verify(
            message=test_message,
            signature=signature,
            public_key_path=public_key_path
        )
        if result:
            print(f"  [OK] 验签成功")
        else:
            print(f"  [FAIL] 验签失败")
    except Exception as e:
        print(f"  [FAIL] 验签异常: {e}")


def test_wechat_pay_notify_verify():
    """测试微信支付回调验签"""
    print("\n" + "=" * 50)
    print("测试3: 微信支付回调验签")
    print("=" * 50)

    public_key_path = r"D:\download\taxation\Shuiwu_backend\certs\pub_key.pem"
    private_key_path = r"D:\download\taxation\Shuiwu_backend\certs\apiclient_key_pkcs8.pem.bak"

    # 模拟微信支付回调数据
    timestamp = "1770908326"
    nonce = "bAgonx48qlY4CWzEQMIgpbEX8SLRuf2s"
    body = '{"event_type":"TRANSACTION.SUCCESS","resource":{"ciphertext":"test","associated_data":"test","nonce":"test","algorithm":"AEAD_AES_256_GCM"}}'

    print(f"时间戳: {timestamp}")
    print(f"随机串: {nonce}")
    print(f"Body: {body[:50]}...")

    # 构建待签名字符串
    message = f"{timestamp}\n{nonce}\n{body}\n"
    print(f"\n待签名字符串:")
    print(f"  {repr(message[:100])}...")

    # 使用私钥签名（模拟微信支付签名）
    print("\n使用私钥模拟签名...")
    try:
        signature = WechatPaySignature.private_key_sign(
            message=message,
            private_key_path=private_key_path
        )
        print(f"  签名: {signature[:50]}...")
    except Exception as e:
        print(f"  [FAIL] 签名失败: {e}")
        return

    # 验签
    print("\n使用公钥验签...")
    try:
        result = WechatPaySignature.verify_wechat_pay_notify(
            timestamp=timestamp,
            nonce=nonce,
            body=body,
            signature=signature,
            public_key_path=public_key_path
        )
        if result:
            print(f"  [OK] 回调验签成功")
        else:
            print(f"  [FAIL] 回调验签失败")
    except Exception as e:
        print(f"  [FAIL] 回调验签异常: {e}")


def test_decrypt_callback_resource():
    """测试回调资源解密"""
    print("\n" + "=" * 50)
    print("测试4: 回调资源解密")
    print("=" * 50)

    api_v3_key = "11111111111111111111111111"  # 测试用
    ciphertext = "dGVzdA=="
    associated_data = "test"
    nonce = "test"

    print(f"密文: {ciphertext}")
    print(f"附加数据: {associated_data}")
    print(f"随机串: {nonce}")
    print(f"API V3 Key: {api_v3_key}")

    try:
        decrypted = WechatPaySignature.decrypt_callback_resource(
            ciphertext=ciphertext,
            associated_data=associated_data,
            nonce=nonce,
            api_v3_key=api_v3_key
        )
        print(f"  [OK] 解密成功: {decrypted}")
    except Exception as e:
        print(f"  解密失败（可能密文不正确）: {e}")


def test_build_signature_message():
    """测试构建签名字符串"""
    print("\n" + "=" * 50)
    print("测试5: 构建签名字符串")
    print("=" * 50)

    http_method = "POST"
    url = "/v3/pay/transactions/jsapi"
    timestamp = "1770908326"
    nonce_str = "bAgonx48qlY4CWzEQMIgpbEX8SLRuf2s"
    body = '{"test":"data"}'

    message = WechatPaySignature.build_signature_message(
        http_method=http_method,
        url=url,
        timestamp=timestamp,
        nonce_str=nonce_str,
        body=body
    )

    print(f"HTTP方法: {http_method}")
    print(f"URL: {url}")
    print(f"时间戳: {timestamp}")
    print(f"随机串: {nonce_str}")
    print(f"Body: {body}")
    print(f"\n签名字符串:")
    print(repr(message))


def main():
    """运行所有测试"""
    print("\n" + "=" * 50)
    print("微信支付签名、加解密测试")
    print("=" * 50)

    # 检查证书文件
    print("\n检查证书文件:")
    cert_files = {
        "商户私钥": r"D:\download\taxation\Shuiwu_backend\certs\apiclient_key_pkcs8.pem.bak",
        "微信支付公钥": r"D:\download\taxation\Shuiwu_backend\certs\pub_key.pem",
    }

    for name, path in cert_files.items():
        exists = os.path.exists(path)
        status = "[OK] Exists" if exists else "[FAIL] Not exists"
        print(f"  {name}: {status} - {path}")

    # 运行测试
    try:
        test_public_key_encrypt()
        test_public_key_verify()
        test_wechat_pay_notify_verify()
        test_decrypt_callback_resource()
        test_build_signature_message()
    except KeyboardInterrupt:
        print("\n\n测试中断")
    except Exception as e:
        print(f"\n\n测试异常: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)


if __name__ == "__main__":
    main()
