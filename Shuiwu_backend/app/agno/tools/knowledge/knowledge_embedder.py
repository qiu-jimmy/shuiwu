"""知识库嵌入器工具

封装与 Agno 框架相关的嵌入器操作，包括：
- 创建 OpenAI 嵌入器（Embedder）
"""
import os
from typing import Optional, Dict, Any

from agno.knowledge.embedder.openai import OpenAIEmbedder


def create_embedder(
    embedder_model: str = "text-embedding-3-small",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    dimensions: Optional[int] = None,
) -> OpenAIEmbedder:
    """创建 OpenAI 嵌入器

    Args:
        embedder_model: 嵌入模型ID，默认 "text-embedding-3-small"
        api_key: OpenAI API Key，如果为 None 则从环境变量获取
        base_url: OpenAI Base URL，如果为 None 则从环境变量获取
        dimensions: 嵌入维度，如果为 None 则从环境变量获取，默认 1536

    Returns:
        OpenAIEmbedder 实例
    """
    # 验证并设置默认模型名称（防止空字符串）
    if not embedder_model or not embedder_model.strip():
        embedder_model = "text-embedding-3-small"

    # 优先使用环境变量；如果未配置，则回退到与 Back 项目一致的第三方平台配置
    if api_key is None:
        api_key = os.getenv("OPENAI_API_KEY")
    if base_url is None:
        base_url = os.getenv("OPENAI_BASE_URL")
    if dimensions is None:
        dimensions = int(os.getenv("EMBEDDER_DIMENSIONS", "1536"))
    # 回退默认值，保证在未配置环境变量时功能可用（与 Back 项目保持一致）
    if not api_key:
        api_key = "sk-rjXxGkEiyx1whoVR75C20cFbF5D24a93Bf80E7CbA36b4c77"
    if not base_url:
        base_url = "https://api.gpt.ge/v1"

    # 通过 client_params 设置超时时间（单位：秒）
    client_params: Dict[str, Any] = {
        "timeout": 120.0,  # 增加超时时间到 120 秒
    }

    return OpenAIEmbedder(
        id=embedder_model,
        dimensions=dimensions,
        api_key=api_key,
        base_url=base_url,
        client_params=client_params,
    )

