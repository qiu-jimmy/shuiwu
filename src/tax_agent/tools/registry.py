"""
工具挂载注册表 (Tool Registry)
=================================
大模型的“手臂”。根据特定的聊天上下文配置（如是否启用检索、什么特定的路由模式），
按需提取并组装出提供给 LangChain Tool Calling 环境调用的外部工具集合。
"""

from collections.abc import Callable
from typing import Any

from tax_agent.schemas import AgentContext
from tax_agent.tools.rag import make_rag_tool
from tax_agent.tools.search import make_web_search_tool
from tax_agent.tools.time import make_time_tool


class ToolRegistry:
    """
    负责生产和聚合系统工具链的工厂类。
    """
    def build_tools(self, context: AgentContext) -> list[Callable[..., Any]]:
        """
        构建匹配本次对话所需的具体工具函数列表。
        
        :param context: 携带路由模式（如 Normal、RAG 等）及权限配置的核心上下文。
        :return: LangChain 兼容的可执行 Tool 函数列表。
        """
        tools: list[Callable[..., Any]] = []
        
        # 1. 常规普通聊天（Normal Tax Agent），强制禁止挂载基础的时间感知工具。
        #    通过切断其时效能力，避免它利用时间参数强制推算/瞎编当下的政策环境。
        if context.route != "chat":
            tools.append(make_time_tool())
            
        # 2. 如果开启了知识库强关联的提问，或者路由到了需要严谨作证的高级路由模式，
        #    则挂载私有向量库（PgVector）文档检索回调。
        if context.enable_rag or context.route in {"rag", "full-feature", "supervisor"}:
            tools.append(make_rag_tool(context))
            
        # 3. 如果显式开启搜索或者要求处理高时效口径的高级路由模式，
        #    则挂载公网检索（Baidu / DuckDuckGo）辅助爬虫查询工具。
        if context.enable_search or context.route in {"full-feature", "supervisor"}:
            tools.append(make_web_search_tool(context))
            
        return tools
