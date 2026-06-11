"""
Agent 工厂类 (Factory)
=================================
负责根据当前的 AgentContext（如路由标识、所需能力和模型参数）实例化对应的大模型或 LangChain Agent。
这里会依据路由装载相应的系统提示词（System Prompt），同时控制是否挂载外部工具。
"""

from typing import Any

from tax_agent.agents.prompts import BASE_TAX_SYSTEM_PROMPT, FULL_FEATURE_EXTRA_PROMPT, NORMAL_TAX_PROMPT
from tax_agent.config import get_settings
from tax_agent.schemas import AgentContext
from tax_agent.tools.registry import ToolRegistry


class MockAgent:
    """
    开发测试用的 Mock Agent。
    如果在本地未配置真实的 LLM API Key 或未开启 enable_real_llm，则会返回此对象作为占位符。
    """

    def __init__(self, context: AgentContext, tools: list[Any]) -> None:
        self.context = context
        self.tools = tools

    async def ainvoke(self, message: str) -> str:
        """模拟调用，回显当前的配置和启用的能力以供调试。"""
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
    """
    核心的大模型与 Agent 实例化工厂。
    它不仅创建 LangChain 大模型连接，还会结合工具注册表（ToolRegistry）返回完整的执行链（Runnable）。
    """
    def __init__(self, tool_registry: ToolRegistry | None = None) -> None:
        self.settings = get_settings()
        self.tool_registry = tool_registry or ToolRegistry()

    def create(self, context: AgentContext):
        """
        根据执行上下文（AgentContext）创建对应的执行体（Tool-calling Agent 或基础 LCEL Chain）。
        
        :param context: 本次聊天的上下文配置，包括路由名称、是否开启 RAG/搜索、模型参数等。
        :return: 可以调用 `.ainvoke()` 进行流式或异步推理的对象。
        """
        # 从工具注册表中获取针对当前路由的工具集
        tools = self.tool_registry.build_tools(context)
        
        # 当配置中未开启真实模型调用时，直接返回打桩对象
        if not self.settings.enable_real_llm:
            return MockAgent(context=context, tools=tools)

        from langchain.agents import create_agent
        from langchain_openai import ChatOpenAI

        # 初始化兼容 OpenAI 接口的大模型客户端
        model = ChatOpenAI(
            model=context.model_id or self.settings.llm_model,
            api_key=self.settings.llm_api_key,
            base_url=self.settings.llm_base_url or None,
            temperature=context.temperature,
        )
        
        # 默认使用通用的基础系统提示词
        prompt = BASE_TAX_SYSTEM_PROMPT
        
        # 如果是高级功能（全文或智能调度、纯检索），追加增强提示词
        if context.route in {"full-feature", "supervisor", "rag"}:
            prompt = f"{prompt}\n\n{FULL_FEATURE_EXTRA_PROMPT}"
        # 如果是轻量级基础聊天（Normal Agent），追加严控边界的普通提示词
        elif context.route == "chat":
            prompt = f"{prompt}\n\n{NORMAL_TAX_PROMPT}"
        
        # 对于不需要外部工具的 Agent（如 Normal Agent），我们不能使用 create_tool_calling_agent
        # 直接利用 LangChain Expression Language (LCEL) 组装一个带历史记忆的 prompt-model chain
        if not tools:
            from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
            
            prompt_template = ChatPromptTemplate.from_messages([
                ("system", prompt),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("user", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad", optional=True),
            ])
            # 返回一个基本的 Runnable 链，具备 ainvoke 能力
            return prompt_template | model
        else:
            # 当存在工具时，生成具备 Function/Tool Calling 能力的标准 Agent
            return create_agent(model=model, tools=tools, system_prompt=prompt)
