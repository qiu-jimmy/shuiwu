from typing import Annotated, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class TaxAgentState(TypedDict):
    """
    财税系统全局状态机对象 (State)
    ===========================
    在 LangGraph 工作流中，所有节点共享并修改此状态。
    这是系统的“全局内存”，保证了流程的可观测性、可中断性和自纠错能力。
    """
    # 消息历史（使用 add_messages 使得新消息会自动追加而不是覆盖）
    messages: Annotated[list[BaseMessage], add_messages]
    
    # 意图识别结果 (GREETING, BASIC_TAX_CONCEPT, EXACT_TAX_QUERY, CONTRACT_REVIEW)
    intent: str
    
    # 提取出的需要进行底层检索的实体词或改写后的查询语句
    search_query: str
    
    # 从 PgVector 或联网检索中召回的相关文档材料
    documents: list[str] # 暂时用 str，后续接入真实 Retriever 会替换为 Document 对象
    
    # 生成器节点的草稿回答，用于等待检查器查验
    draft_answer: str
    
    # 事实性/幻觉校验结果：是否通过了依据审核
    compliance_passed: bool
