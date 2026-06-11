"""
微信支付集成测试脚本
验证核心逻辑和组件是否正常工作
"""
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置UTF-8编码输出（Windows兼容）
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 设置测试环境变量
os.environ["WECHAT_PAY_APPID"] = "wx1234567890abcdef"
os.environ["WECHAT_PAY_MCHID"] = "1234567890"
os.environ["WECHAT_PAY_API_V3_KEY"] = "test_api_v3_key_32bytes1234567890AB"
os.environ["WECHAT_PAY_CERT_SERIAL_NO"] = "TEST123456"
os.environ["WECHAT_PAY_PRIVATE_KEY_PATH"] = "./test_key.pem"
os.environ["WECHAT_PAY_PUBLIC_KEY_PATH"] = "./test_pubkey.pem"
os.environ["WECHAT_PAY_NOTIFY_URL"] = "https://test.com/api/payments/notify"

# 添加数据库配置（避免导入错误）
os.environ["PG_HOST"] = "localhost"
os.environ["PG_PORT"] = "5432"
os.environ["PG_USER"] = "test"
os.environ["PG_PASSWORD"] = "test"
os.environ["PG_DATABASE"] = "test"


def test_signature_utils():
    """测试签名工具类"""
    print("\n=== 测试签名工具 ===")
    try:
        from app.services.wechat_pay.signature import WechatPaySignature

        # 测试1: 构建签名消息
        message = WechatPaySignature.build_signature_message(
            http_method="POST",
            url="/v3/pay/transactions/jsapi",
            timestamp="1642234567",
            nonce_str="5K8264ILTKCH16CQ2502SI8ZNMTM67VS",
            body='{"test": "data"}'
        )
        print(f"✓ 构建签名消息成功")
        print(f"  消息格式: {message[:50]}...")

        # 测试2: 构建参数签名字符串
        params = {"key1": "value1", "key2": "value2"}
        param_str = WechatPaySignature.build_param_signature(params)
        print(f"✓ 构建参数签名字符串成功")
        print(f"  参数字符串: {param_str}")

        # 测试3: HMAC-SHA256签名
        hmac_sig = WechatPaySignature.hmac_sha256_sign("test_message", "test_key")
        print(f"✓ HMAC-SHA256签名成功")
        print(f"  签名: {hmac_sig}")

        return True
    except Exception as e:
        print(f"✗ 签名工具测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_client_initialization():
    """测试客户端初始化"""
    print("\n=== 测试客户端初始化 ===")
    try:
        from app.infra.wechat_pay_client import WechatPayClient

        # 创建客户端实例（不初始化配置）
        client = WechatPayClient()
        print(f"✓ 客户端实例创建成功")
        print(f"  基础URL: {client.base_url}")
        print(f"  延迟初始化: {not client._initialized}")

        # 测试配置检查（会抛出异常，因为文件不存在）
        try:
            client._ensure_initialized()
        except ValueError as e:
            if "配置不完整" in str(e) or "私钥文件" in str(e):
                print(f"✓ 配置验证逻辑正常")
                print(f"  预期异常: {e}")
            else:
                raise

        return True
    except Exception as e:
        print(f"✗ 客户端初始化测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_schema_models():
    """测试数据模型"""
    print("\n=== 测试数据模型 ===")
    try:
        from app.schemas.payment import (
            CreatePaymentRequest,
            PaymentNotifyRequest,
            QueryPaymentRequest,
            CreateRefundRequest,
            CreatePaymentResponse
        )

        # 测试创建支付请求
        request = CreatePaymentRequest(
            order_id="TEST123456",
            openid="o1234567890abcdef"
        )
        print(f"✓ 创建支付请求模型成功")
        print(f"  order_id: {request.order_id}")
        print(f"  openid: {request.openid}")

        # 测试支付响应模型
        response = CreatePaymentResponse(
            prepay_id="wx1234567890",
            pay_params={"appId": "wx123", "timeStamp": "123456"}
        )
        print(f"✓ 创建支付响应模型成功")
        print(f"  prepay_id: {response.prepay_id}")

        return True
    except Exception as e:
        print(f"✗ 数据模型测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_payment_service_structure():
    """测试支付服务结构"""
    print("\n=== 测试支付服务结构 ===")
    try:
        from app.services.wechat_pay.wechat_pay_service import WechatPayService

        # 检查服务类的方法
        service_methods = [
            'create_jsapi_order',
            'handle_payment_notify',
            'query_payment_status',
            'close_order',
            'create_refund'
        ]

        for method in service_methods:
            if hasattr(WechatPayService, method):
                print(f"✓ 服务方法存在: {method}")
            else:
                print(f"✗ 服务方法缺失: {method}")
                return False

        return True
    except Exception as e:
        print(f"✗ 支付服务结构测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_routes():
    """测试API路由结构"""
    print("\n=== 测试API路由结构 ===")
    try:
        from app.api.payment import router

        # 检查路由
        routes = [
            "/api/payments/jsapi",
            "/api/payments/notify",
            "/api/payments/{order_id}/status",
            "/api/payments/orders/{order_id}/close",
            "/api/payments/refunds"
        ]

        route_paths = [route.path for route in router.routes]

        for route in routes:
            if route in route_paths:
                print(f"✓ 路由存在: {route}")
            else:
                print(f"✗ 路由缺失: {route}")
                print(f"  现有路由: {route_paths}")
                return False

        return True
    except Exception as e:
        print(f"✗ API路由结构测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_repository():
    """测试配置管理"""
    print("\n=== 测试配置管理 ===")
    try:
        from app.services.wechat_pay.wechat_pay_repository import WechatPayConfig

        config = WechatPayConfig()
        print(f"✓ 配置实例创建成功")
        print(f"  未初始化状态: {not config.is_loaded()}")

        # 测试加载配置
        import asyncio
        asyncio.run(config.load_config())

        print(f"✓ 配置加载成功")
        print(f"  已加载状态: {config.is_loaded()}")

        # 读取配置值
        appid = config.get("appid")
        print(f"✓ 配置读取成功")
        print(f"  appid: {appid}")

        return True
    except Exception as e:
        print(f"✗ 配置管理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("微信支付集成验证测试")
    print("=" * 60)

    results = []

    # 运行各项测试
    results.append(("签名工具", test_signature_utils()))
    results.append(("客户端初始化", test_client_initialization()))
    results.append(("数据模型", test_schema_models()))
    results.append(("支付服务结构", test_payment_service_structure()))
    results.append(("API路由结构", test_api_routes()))
    results.append(("配置管理", test_config_repository()))

    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    passed = 0
    failed = 0

    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{name:20s}: {status}")
        if result:
            passed += 1
        else:
            failed += 1

    print("-" * 60)
    print(f"总计: {passed} 通过, {failed} 失败")

    if failed == 0:
        print("\n✓ 所有测试通过！微信支付集成逻辑正常。")
        return 0
    else:
        print(f"\n✗ 有 {failed} 项测试失败，请检查相关模块。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
