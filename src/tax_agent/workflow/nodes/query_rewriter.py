"""
查询重写器 (Query Rewriter Node)
=================================
将用户的自然语言口语化提问转换为专业、结构化的税务搜索词。
只在意图分类为 EXACT_TAX_QUERY 或需要查库时调用。
目的在于极大提升 RAG (PgVector) 和公网搜索引擎的召回率（Recall）。
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from tax_agent.config import get_settings
from tax_agent.workflow.state import TaxAgentState


# ==========================================
# 1. 查询重写数据模型 (Structured Output)
# ==========================================
class RewrittenQuery(BaseModel):
    """强制要求大模型吐出提取好的检索词字符串。"""
    search_query: str = Field(
        description="优化后用于向量检索和搜索引擎的查询语句，提取核心关键词，去除冗余语气词，补全隐含的税务实体。多个词之间用空格隔开。"
    )


# ==========================================
# 2. 查询重写器 Prompt
# ==========================================
REWRITER_SYSTEM_PROMPT = """你是一个专业的财税搜索词优化专家。
用户的原始提问通常非常口语化且缺乏专业术语。你的任务是将用户的提问改写为极具结构化、利于向量数据库（PgVector）或搜索引擎检索的查询词。

【改写规则】：
1. 提取核心实体：提炼出税种（如增值税、个税）、纳税人身份（如小规模纳税人、高新技术企业）、政策名称、年份等。
2. 去除冗余词汇：删除“请问”、“帮我看看”、“是什么”等无实际检索意义的词。
3. 补全专业术语：如用户问“退税”，根据语境补全为“期末留抵退税”或“个人所得税汇算清缴退税”；用户问“几个点”，补全为“适用税率”或“征收率”。
4. 保持紧凑：直接以空格分隔核心关键词。

示例 1：
用户提问：公司没赚钱还要不要报税？
改写结果：企业 无收入 零申报 纳税申报义务

示例 2：
用户提问：今年小规模几个点？
改写结果：2026年 小规模纳税人 增值税 征收率 免征额

注意：不要解释，也不要回答问题，仅仅输出优化后的搜索词。
"""


def rewrite_query_node(state: TaxAgentState) -> dict:
    """
    LangGraph 节点函数：查询重写器 (Query Rewriter)
    
    提取最近一条用户消息，生成精准的 search_query，更新到全局 State 中。
    """
    messages = state.get("messages", [])
    if not messages:
        return {"search_query": ""}
        
    last_user_message = messages[-1].content
    
    settings = get_settings()
    
    # 使用极低温度保证实体抽取的稳定性
    llm = ChatOpenAI(
        model=settings.llm_model, 
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url or None,
        temperature=0.1
    )
    
    # 绑定结构化输出对象
    structured_llm = llm.with_structured_output(RewrittenQuery)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", REWRITER_SYSTEM_PROMPT),
        ("human", "用户提问：{input}")
    ])
    
    rewriter_chain = prompt | structured_llm
    
    try:
        # 执行重写提取
        result: RewrittenQuery = rewriter_chain.invoke({"input": last_user_message})
        print(f"[Query Rewriter] 原始提问: '{last_user_message}' => 改写查询词: '{result.search_query}'")
        return {"search_query": result.search_query}
    except Exception as e:
        # 降级：若大模型抽取异常，直接使用原始用户提问作为查询词，避免阻断流程
        print(f"[Query Rewriter] Error rewriting query: {e}")
        return {"search_query": last_user_message}
