from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from tax_agent.config import get_settings
from tax_agent.workflow.state import TaxAgentState

# ==========================================
# 1. 意图分类数据模型 (Structured Output)
# ==========================================
class IntentClassification(BaseModel):
    """
    强制大模型按照此结构输出分类结果，杜绝随意的纯文本回复。
    """
    intent: Literal["GREETING", "BASIC_TAX_CONCEPT", "EXACT_TAX_QUERY", "CONTRACT_REVIEW"] = Field(
        description="""
        识别用户的意图并分类：
        - GREETING: 日常寒暄、打招呼、无意义的闲聊（例如："你好"、"在吗"、"你是谁"）。
        - BASIC_TAX_CONCEPT: 基础税务概念解释、宽泛的流程咨询、没有任何具体数字或年份要求的求助（例如："什么是增值税"、"个体户怎么报税"、"一般纳税人什么意思"）。
        - EXACT_TAX_QUERY: 需要极高准确性的查库请求，包括：询问最新税率、具体文号、生效日期、扣除标准具体金额，或者明确要求基于给定文档/知识库作答（例如："今年小规模免征额是多少"、"2026年个税专项扣除标准"、"根据财税2024第11号公告..."）。
        - CONTRACT_REVIEW: 明确要求对合同、协议、条款进行风险审查或修改建议（例如："帮我看看这份合同"、"审查这个条款"）。
        """
    )
    reasoning: str = Field(description="你做出这个分类决定的原因分析（一步步思考）。")

# ==========================================
# 2. 意图分类器 Prompt
# ==========================================
ROUTER_SYSTEM_PROMPT = """你是一个财税专家系统的前置意图分类网关。
你的任务是极度严谨地分析用户的最后一条发言，并将其归类为指定的 4 种意图之一。

分类边界与防误判指南：
1. 【闲聊与测试】：如果用户的提问完全不涉及财务、税务、法务、合同等业务内容，仅仅是打招呼、询问你是谁、询问你的能力、或者发无意义的测试内容（如"测试一下"、"你会聊天吗"、"随便说点什么"、"天气不错"），请务必坚决返回 GREETING。不要过度联想。
2. 【合同审查优先】：只要用户提问中包含“合同”、“协议”、“条款”（如违约金、劳务协议）等字眼，且要求判断其风险、合法性或要求审查，即使带有“高不高”、“是否合法”等字眼，也必须优先归类为 CONTRACT_REVIEW。
3. 【基础 vs 精确查询】：
   - 只有涉及通用概念、普通流程（"什么是..."、"怎么去操作"）时才归为 BASIC_TAX_CONCEPT。
   - 一旦涉及具体数据、金额、税率百分比、年份（如"2026年"）、具体政策文号、或者明确指出根据某文件作答（如"现在几个点"、"免征额是多少"），必须归为 EXACT_TAX_QUERY。

你的输出将被系统直接捕获执行路由，所以你必须按要求生成结构化的 JSON。
"""

def analyze_intent_node(state: TaxAgentState) -> dict:
    """
    LangGraph 节点函数：意图分类器 (Intent Router)
    
    提取状态中的最后一条用户消息，交由大模型进行结构化意图识别。
    返回一个包含 `intent` 字段的字典，以便 LangGraph 更新全局 State。
    """
    # 提取最后一条用户消息（假设一定会有消息）
    messages = state.get("messages", [])
    if not messages:
        return {"intent": "GREETING"}
        
    last_user_message = messages[-1].content
    
    settings = get_settings()
    
    # 实例化一个低延迟/低成本的模型来进行路由判断
    # 实际生产中可以是一个微调过的小模型（如 Qwen-7B）以加快速度
    llm = ChatOpenAI(
        model=settings.llm_model, 
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url or None,
        temperature=0.0 # 路由需要绝对确定性，温度设为0
    )
    
    # 将大模型绑定 Pydantic 模型，强制约束其输出格式
    structured_llm = llm.with_structured_output(IntentClassification)
    
    # 组装 Prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", ROUTER_SYSTEM_PROMPT),
        ("human", "{input}")
    ])
    
    # 构建执行链：Prompt -> 带有结构化约束的 LLM
    router_chain = prompt | structured_llm
    
    try:
        # 执行分类
        result: IntentClassification = router_chain.invoke({"input": last_user_message})
        
        # 将解析到的意图返回，LangGraph 会自动合入 State 中
        return {"intent": result.intent}
        
    except Exception as e:
        # 降级容错机制：如果大模型解析失败（极少情况），为了安全起见，默认降级到严格查库管线
        # 或者在日志中告警
        print(f"[Intent Router] Error parsing intent: {e}")
        return {"intent": "EXACT_TAX_QUERY"}
