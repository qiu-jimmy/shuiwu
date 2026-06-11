"""
简单的 DashScope 千问模型对话测试 - 简化版
使用 agno 框架和阿里云 DashScope API
"""
import sys
import io

# 修复 Windows 控制台编码问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from agno.agent import Agent
from agno.models.dashscope import DashScope


# 创建 Agent 实例
agent = Agent(
    model=DashScope(
        id="qwen3-max",
        api_key="sk-c9b8659683a541bfaa8580448ca67766",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    ),
    markdown=True,
    stream=True,
    instructions="You are a helpful assistant."
)

# 测试对话
question = "你是谁？"
print(f"问题: {question}")

# 流式输出 - 使用 print_response 更简单
agent.print_response(question, stream=True)
