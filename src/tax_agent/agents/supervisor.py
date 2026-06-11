"""
智能路由拦截器 (Supervisor)
=================================
由于引入完整的 LangGraph 会增加过高的复杂度和开销，目前的调度器采用了轻量的“基于规则/关键字”拦截器。
负责拦截来自 /api/chat/supervisor 的请求，判定其真实意图，然后改写执行路由。
"""

from enum import StrEnum
from pydantic import BaseModel


class RouteDecision(StrEnum):
    """
    预定义的路由去向枚举值。对应不同复杂度和能力的子 Agent。
    """
    NORMAL = "chat"
    FULL_FEATURE = "full-feature"
    RAG = "rag"
    CONTRACT = "contract-chat"
    SEARCH = "search"


class SupervisorDecision(BaseModel):
    """路由决策的返回值数据模型，包含了最终的去向及附加配置。"""
    route: RouteDecision
    enable_rag: bool = False
    enable_search: bool = False
    reason: str = ""


class RuleBasedSupervisor:
    """
    基于启发式规则（如关键字）的临时智能调度器。
    在未来的演进版本中可替换为 LangGraph 的语义分类或 Router Agent。
    """

    def decide(self, message: str, has_files: bool = False) -> SupervisorDecision:
        """
        根据用户输入和附加状态（如是否有附件）得出最优的 Agent 路由。
        
        :param message: 用户发送的文本消息
        :param has_files: 本次请求是否携带了文件附件
        :return: SupervisorDecision 对象，指导 ChatService 接下来使用哪个路由上下文进行响应
        """
        text = message.lower()
        
        # 1. 如果提到了合同审查，或者带有文件且提及风险/审查，直接路由至合同 Agent
        if "合同" in text or has_files and any(k in text for k in ["审查", "风险条款", "乙方"]):
            return SupervisorDecision(route=RouteDecision.CONTRACT, reason="contract keywords")
            
        # 2. 如果包含强时效性或需要精准口径的税务词汇，触发升级到全功能 Agent（挂载 RAG 与搜索）
        if any(k in text for k in ["最新", "现在", "今年", "当前", "生效", "文号", "公告", "税率", "几个点", "扣除标准", "起征点", "免征额", "限额", "杭州", "江西", "税局"]):
            return SupervisorDecision(
                route=RouteDecision.FULL_FEATURE,
                enable_rag=True,
                enable_search=True,
                reason="time-sensitive or exact-standard tax query",
            )
            
        # 3. 如果提到“知识库”、“文件”、“附件”等政策查询词眼，直接路由给 RAG 优先搜索
        if any(k in text for k in ["政策", "法规", "条款", "依据", "案例", "知识库", "文件", "附件", "资料"]):
            return SupervisorDecision(route=RouteDecision.RAG, enable_rag=True, reason="knowledge query")
            
        # 4. 保底返回：基础问答 Agent（Normal Tax Agent）
        return SupervisorDecision(route=RouteDecision.NORMAL, reason="normal chat")
