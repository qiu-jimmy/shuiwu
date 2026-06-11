from collections.abc import Callable
from typing import Any

from tax_agent.schemas import AgentContext
from tax_agent.tools.rag import make_rag_tool
from tax_agent.tools.search import make_web_search_tool
from tax_agent.tools.time import make_time_tool


class ToolRegistry:
    def build_tools(self, context: AgentContext) -> list[Callable[..., Any]]:
        tools: list[Callable[..., Any]] = [make_time_tool()]
        if context.enable_rag or context.route in {"rag", "full-feature", "supervisor"}:
            tools.append(make_rag_tool(context))
        if context.enable_search or context.route in {"full-feature", "supervisor"}:
            tools.append(make_web_search_tool(context))
        return tools
