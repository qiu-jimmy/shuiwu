from tax_agent.schemas import AgentContext
from tax_agent.tools.decorators import compatible_tool


def make_web_search_tool(context: AgentContext):
    @compatible_tool
    def web_search(query: str) -> str:
        """Search latest tax policy information from external search providers."""
        return (
            f"Mock web search result for user {context.user_id}: {query}. "
            "真实搜索工具将在 P1/P2 接入百度、官方税务网站或第三方搜索服务。"
        )

    return web_search
