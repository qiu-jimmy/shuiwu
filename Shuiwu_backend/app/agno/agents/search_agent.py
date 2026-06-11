"""
Search Chat Agent - 搜索对话 Agent
专门用于在线搜索对话，启用搜索工具但不启用RAG
"""
from typing import Optional

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from app.agno.tools.search.baidu_search_tools import create_baidu_search_tool
from app.agno.tools.search.duckduckgo_search_tools import create_duckduckgo_tools
from app.services.models.model_cache import model_cache


def create_search_agent(
    model_id: str = "qwen-plus",
    session_id: str = None,
    user_id: str = "default",
    send_media_to_model: bool = True,
    temperature: float = 0.7,
    db=None,
) -> Agent:
    """
    创建搜索对话 Agent（启用搜索工具，不启用RAG）

    Args:
        model_id: 模型ID
        session_id: 会话ID
        user_id: 用户ID
        send_media_to_model: 是否将媒体发送给模型
        temperature: 温度参数
        db: Agno PostgresDb 实例

    Returns:
        配置好的 Agent 实例
    """
    # 从缓存获取模型配置
    model_config = model_cache.get_model_config(model_id)

    if not model_config:
        raise ValueError(f"模型配置不存在: {model_id}")

    # 提取配置参数
    api_key = model_config.get("model_api_key")
    base_url = model_config.get("model_url")

    if not api_key:
        raise ValueError(f"模型 {model_id} 缺少 API Key 配置")

    # 创建模型实例
    model = OpenAIChat(
        id=model_id,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
    )

    # 工具配置 - 启用搜索工具（直接使用两个工具工厂）
    tools = []

    # 百度搜索
    baidu_tool = create_baidu_search_tool()
    if baidu_tool is not None:
        tools.append(baidu_tool)

    # DuckDuckGo 搜索
    duckduckgo_list = create_duckduckgo_tools()
    if duckduckgo_list:
        tools.extend(duckduckgo_list)

    # 创建 Agent
    instructions = []
    if tools:
        instructions = [
            "使用百度搜索中文内容和国内信息",
            "使用DuckDuckGo搜索英文内容和国际信息",
            "根据查询语言和内容类型选择合适的搜索引擎",
            "如果某个搜索引擎没有结果，尝试使用另一个搜索引擎",
            "重要：搜索后要总结搜索结果中的信息，用自然语言回答用户问题",
            "不要直接复制搜索结果中的链接或markdown格式",
            "不要在回复中包含类似'点击查看'、'[链接]'等引导用户点击的内容",
            "直接给出用户需要的信息答案，而不是提供参考链接"
        ]

    agent = Agent(
        model=model,
        knowledge=None,  # 不启用知识库
        tools=tools,  # 启用搜索工具
        db=db,
        session_id=session_id,
        add_history_to_context=True,
        num_history_runs=10,
        search_knowledge=False,  # 不搜索知识库
        add_knowledge_to_context=False,  # 不添加知识库内容到上下文
        markdown=False,  # 关闭 Markdown，避免自动转换链接格式
        send_media_to_model=send_media_to_model,
        store_media=True,
        instructions=instructions if instructions else None,
    )

    return agent

