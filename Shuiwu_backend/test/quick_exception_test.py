"""
快速测试异常输出 - 在服务器运行时使用
"""
import requests

BASE_URL = "http://127.0.0.1:8000"

def test_exception(endpoint: str, description: str):
    """测试异常端点"""
    print(f"\n{'='*60}")
    print(f"测试: {description}")
    print(f"端点: {endpoint}")
    print(f"{'='*60}")

    try:
        response = requests.get(f"{BASE_URL}{endpoint}")
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
    except Exception as e:
        print(f"请求失败: {e}")

    print(f"请检查服务器控制台的异常输出！")
    print(f"{'='*60}\n")


def main():
    print("\n" + "*" * 60)
    print("快速异常测试")
    print("*" * 60)
    print("请确保服务器正在运行: python main.py")
    print("*" * 60)

    # 测试列表
    tests = [
        ("/api/test/error/not-found", "404异常"),
        ("/api/test/error/validation", "参数验证异常"),
        ("/api/test/error/database", "数据库异常"),
        ("/api/test/error/ai-service", "AI服务异常"),
        ("/api/test/error/http", "HTTP异常"),
        ("/api/test/error/unexpected", "未捕获异常（除零错误）"),
        ("/api/test/error/key-error", "KeyError"),
    ]

    print("\n可用测试:")
    for i, (endpoint, desc) in enumerate(tests, 1):
        print(f"{i}. {desc} - {endpoint}")

    print("\n输入数字选择测试，或输入'all'测试所有异常")
    choice = input("> ").strip()

    if choice.lower() == 'all':
        for endpoint, desc in tests:
            test_exception(endpoint, desc)
            input("按Enter继续...")
    elif choice.isdigit() and 1 <= int(choice) <= len(tests):
        endpoint, desc = tests[int(choice) - 1]
        test_exception(endpoint, desc)
    else:
        print("无效选择")

    print("\n" + "*" * 60)
    print("测试完成！")
    print("如果控制台没有看到异常输出，请查看:")
    print("1. 服务器控制台 (运行 python main.py 的终端)")
    print("2. 日志文件: tail -f logs/exception.log")
    print("*" * 60 + "\n")


if __name__ == "__main__":
    main()
