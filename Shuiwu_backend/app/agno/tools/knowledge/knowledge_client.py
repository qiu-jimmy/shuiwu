"""知识库客户端工具

封装与 Agno 框架相关的知识库实例创建，包括：
- 创建知识库实例（Knowledge）
- 配置向量数据库（PgVector）
"""
from typing import Optional

from agno.knowledge.knowledge import Knowledge
from agno.vectordb.pgvector import PgVector, SearchType

from app.agno.tools.knowledge.knowledge_embedder import create_embedder
from app.utils.knowledge_utils import build_table_name


def create_knowledge_base_instance(
    name: str,
    description: str,
    user_id: str,
    db_url: str,
    table_name: Optional[str] = None,
    embedder_model: str = "text-embedding-3-small",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    dimensions: Optional[int] = None,
    schema: str = "knowledge",
) -> Knowledge:
    """创建知识库实例

    Args:
        name: 知识库名称
        description: 知识库描述
        user_id: 用户ID
        db_url: 数据库连接URL
        table_name: 表名（可选，不传则自动生成哈希表名）
                    对于已存在的知识库，必须传入 registry 中存储的 table_name
        embedder_model: 嵌入模型ID
        api_key: OpenAI API Key
        base_url: OpenAI Base URL
        dimensions: 嵌入维度
        schema: 数据库schema名称，默认 "knowledge"

    Returns:
        Knowledge 实例
    """
    embedder = create_embedder(
        embedder_model=embedder_model,
        api_key=api_key,
        base_url=base_url,
        dimensions=dimensions,
    )

    # 如果未传入 table_name，则使用 build_table_name 生成统一的哈希表名格式
    # 对于已存在的知识库，必须传入 registry 中存储的 table_name，避免重复生成导致不一致
    if table_name is None:
        table_name = build_table_name(user_id, name)
    
    knowledge = Knowledge(
        name=name,
        description=description,
        vector_db=PgVector(
            table_name=table_name,
            db_url=db_url,
            embedder=embedder,
            schema=schema,
            # ✅ 启用混合检索（向量 + 关键词）
            search_type=SearchType.hybrid,
            vector_score_weight=0.7,  # 向量相似度权重（0-1）
            prefix_match=True,         # 启用前缀匹配
        ),
    )

    return knowledge

