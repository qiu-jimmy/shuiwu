from typing import Any

from tax_agent.agents.prompts import BASE_TAX_SYSTEM_PROMPT, FULL_FEATURE_EXTRA_PROMPT
from tax_agent.config import get_settings
from tax_agent.schemas import AgentContext
from tax_agent.tools.registry import ToolRegistry


class MockAgent:
    """Development fallback used before real model credentials are wired."""

    def __init__(self, context: AgentContext, tools: list[Any]) -> None:
        self.context = context
        self.tools = tools

    async def ainvoke(self, message: str) -> str:
        enabled = []
        if self.context.enable_rag:
            enabled.append("RAG")
        if self.context.enable_search:
            enabled.append("联网搜索")
        if self.tools:
            enabled.append(f"{len(self.tools)} 个工具")
        enabled_text = "、".join(enabled) if enabled else "基础问答"
        return (
            f"这是 LangChain Agent 新架构的脚手架响应。当前路由为 {self.context.route}，"
            f"已启用能力：{enabled_text}。用户问题：{message}"
        )


class AgentFactory:
    def __init__(self, tool_registry: ToolRegistry | None = None) -> None:
        self.settings = get_settings()
        self.tool_registry = tool_registry or ToolRegistry()

    def create(self, context: AgentContext):
        tools = self.tool_registry.build_tools(context)
        if not self.settings.enable_real_llm:
            return MockAgent(context=context, tools=tools)

        from langchain.agents import create_agent
        from langchain_openai import ChatOpenAI

        model = ChatOpenAI(
            model=context.model_id or self.settings.llm_model,
            api_key=self.settings.llm_api_key,
            base_url=self.settings.llm_base_url or None,
            temperature=context.temperature,
        )
        prompt = BASE_TAX_SYSTEM_PROMPT
        if context.route in {"full-feature", "supervisor", "rag"}:
            prompt = f"{prompt}\n\n{FULL_FEATURE_EXTRA_PROMPT}"
        return create_agent(model=model, tools=tools, system_prompt=prompt)
