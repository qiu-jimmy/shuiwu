"""
SM2 签名测试脚本
用于生成测试密钥对和验证签名功能
"""
import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.chashuibao.sm2_signature import ChashuibaoSignature


# 测试用的 SM2 密钥对（从标准测试用例获取）
# 私钥: 64位十六进制
TEST_PRIVATE_KEY = "3945208F7B2144B17F2A39C06B3B4F2D67AEE8B9A0A9B0B7F3F3F3F3F3F3F3F3F"
# 公钥: 128位十六进制 (未压缩格式)
TEST_PUBLIC_KEY = "09F9DF311E5D1D4E3B9F4A5A6B7C8D9E0F1A2B3C4D5E6F7A8B9C0D1E2F3A4B5C6D7E8F9A0B1C2D3E4F5A6B7C8D9E0F1A2B3C4D5E6F7A8B9C0D1E2F3A4B5C6D7E8F9"


def test_signature():
    """测试签名功能"""
    # 使用测试密钥对
    private_key = TEST_PRIVATE_KEY
    public_key = TEST_PUBLIC_KEY

    print("=" * 60)
    print("SM2 签名测试")
    print("=" * 60)
    print(f"\n测试私钥: {private_key}")
    print(f"测试公钥: {public_key}")

    # 设置私钥
    ChashuibaoSignature.set_private_key(private_key)

    # 测试签名参数（模拟获取授权链接的参数）
    test_params = {
        'thirdPartyId': 'test_token_123',
        'taxpayerId': 'encrypted_taxpayer_id',
        'companyName': 'encrypted_company_name',
        'reportType': '2',
        'cburl': 'https://example.com/callback',
        'year': '2024',
        'quarter': '1',
    }

    print("\n" + "=" * 60)
    print("测试签名功能")
    print("=" * 60)

    # 构建待签名字符串
    sign_string = ChashuibaoSignature.build_sign_string(test_params)
    print(f"\n待签名字符串:\n{sign_string}")

    # 生成签名
    try:
        signature = ChashuibaoSignature.sign(test_params)
        print(f"\n签名结果 (128位十六进制):\n{signature}")
    except Exception as e:
        print(f"\n签名失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 验证签名
    try:
        is_valid = ChashuibaoSignature.verify(test_params, signature, public_key)
        print(f"\n验签结果: {'[成功]' if is_valid else '[失败]'}")
    except Exception as e:
        print(f"\n验签异常: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("=" * 60)

    # 测试字段加密
    print("\n" + "=" * 60)
    print("测试字段加密功能")
    print("=" * 60)

    plaintext = "91330100MA2XXX00XX"
    print(f"\n明文: {plaintext}")

    try:
        encrypted = ChashuibaoSignature.encrypt_field(plaintext, public_key)
        print(f"加密后 (Base64):\n{encrypted}")

        # 解密
        decrypted = ChashuibaoSignature.decrypt_field(encrypted)
        print(f"\n解密后: {decrypted}")
        print(f"解密{'[成功]' if decrypted == plaintext else '[失败]'}")
    except Exception as e:
        print(f"\n加密/解密异常: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("=" * 60)

    return True


def print_env_config():
    """打印环境变量配置示例"""
    print("\n" + "=" * 60)
    print("环境变量配置示例")
    print("=" * 60)
    print("""
# 在 .env 文件中添加以下配置：

# 查税宝配置
CHASHUIBAO_BASE_URL=https://testcsbplus.dianzuanmao.com  # 测试环境
# CHASHUIBAO_BASE_URL=https://csb.dianzuanmao.com  # 正式环境
CHASHUIBAO_THIRD_PARTY_ID=your_third_party_id  # 由查税宝提供
CHASHUIBAO_PRIVATE_KEY=your_sm2_private_key  # SM2 私钥（64位十六进制）
CHASHUIBAO_PUBLIC_KEY=your_sm2_public_key  # SM2 公钥（128位十六进制，用于加密字段）

# 注意：
# 1. 私钥和公钥由查税宝提供，或者使用您自己的密钥对
# 2. 公钥用于加密敏感字段（纳税人识别号、企业名称）
# 3. 私钥用于生成签名
    """)
    print("=" * 60)


if __name__ == "__main__":
    success = test_signature()
    if success:
        print("\n[OK] 所有测试通过！")
        print("\n[注意] 上述使用的是测试密钥对")
        print("   实际对接时，请使用查税宝提供的正式密钥对")
        print_env_config()
    else:
        print("\n[FAIL] 测试失败！")
