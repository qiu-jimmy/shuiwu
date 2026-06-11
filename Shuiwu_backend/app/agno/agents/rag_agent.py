"""
RAG Chat Agent - RAG对话 Agent
专门用于RAG对话，启用知识库但不启用搜索工具
"""
from typing import Optional

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from app.services.models.model_cache import model_cache


def create_rag_agent(
    model_id: str = "qwen-plus",
    session_id: str = None,
    user_id: str = "default",
    knowledge_base: Optional[str] = None,
    send_media_to_model: bool = True,
    temperature: float = 0.7,
    db=None,
) -> Agent:
    """
    创建RAG对话 Agent（启用知识库，不启用搜索工具）

    Args:
        model_id: 模型ID
        session_id: 会话ID
        user_id: 用户ID
        knowledge_base: 知识库名称
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

    # 知识库配置
    knowledge = None
    if knowledge_base:
        try:
            from app.services.knowledge.knowledge_service import knowledge_service
            knowledge = knowledge_service.get_or_load_knowledge(
                user_id=user_id,
                kb_name=knowledge_base,
            )
        except Exception as e:
            print(f"加载知识库失败: {e}")

    # RAG对话不启用搜索工具
    tools = []

    # 创建 Agent
    agent = Agent(
        model=model,
        knowledge=knowledge,  # 启用知识库
        tools=tools,  # 不启用搜索工具
        db=db,
        session_id=session_id,
        add_history_to_context=True,
        num_history_runs=10,
        search_knowledge=True,  # 搜索知识库
        add_knowledge_to_context=True,  # 添加知识库内容到上下文
        markdown=True,
        send_media_to_model=send_media_to_model,
        store_media=True,
        instructions=None,
    )

    return agent

