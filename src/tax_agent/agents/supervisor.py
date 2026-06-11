from enum import StrEnum

from pydantic import BaseModel


class RouteDecision(StrEnum):
    NORMAL = "chat"
    FULL_FEATURE = "full-feature"
    RAG = "rag"
    CONTRACT = "contract-chat"
    SEARCH = "search"


class SupervisorDecision(BaseModel):
    route: RouteDecision
    enable_rag: bool = False
    enable_search: bool = False
    reason: str = ""


class RuleBasedSupervisor:
    """Temporary supervisor. Replace with LangGraph in the orchestration phase."""

    def decide(self, message: str, has_files: bool = False) -> SupervisorDecision:
        text = message.lower()
        if "合同" in text or has_files and any(k in text for k in ["审查", "风险条款", "乙方"]):
            return SupervisorDecision(route=RouteDecision.CONTRACT, reason="contract keywords")
        if any(k in text for k in ["最新", "现在", "今年", "当前", "生效", "文号", "公告"]):
            return SupervisorDecision(
                route=RouteDecision.FULL_FEATURE,
                enable_rag=True,
                enable_search=True,
                reason="time-sensitive tax query",
            )
        if any(k in text for k in ["政策", "法规", "条款", "依据", "案例", "知识库"]):
            return SupervisorDecision(route=RouteDecision.RAG, enable_rag=True, reason="knowledge query")
        return SupervisorDecision(route=RouteDecision.NORMAL, reason="normal chat")
