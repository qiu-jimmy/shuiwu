"""
权限验证与计费网关 (Permission Gateway)
=================================
连接旧版会员权限系统和次数消耗计费系统的桥梁。
在此进行套餐特权、资源消耗及安全越权阻断，保证 RAG、发票穿透等高级工具不在未授权套餐中被调用。
"""

from tax_agent.schemas import AgentContext


class PermissionGateway:
    """
    桥接 Legacy 业务后端的权限门禁网关。
    当前作为新架构脚手架默认放行全部特权。
    未来重构第二阶段 (P2) 会替换为通过 gRPC / HTTP 真实回调原有的后台校验接口。
    """

    async def get_privileges(self, user_id: str) -> set[str]:
        """
        获取用户身上所绑定的会员服务特权字典。
        
        :param user_id: 当前请求者的小程序/业务系统的用户唯一标识。
        :return: 用户所持有的所有高价值能力的英文 Key 的集合。
        """
        return {
            "daily_chats",
            "rag",
            "web_search",
            "mcp_tools",
            "contract_review",
            "contract_screening",
        }

    async def assert_allowed(self, context: AgentContext) -> None:
        """
        严格校验当前路由（如是否启用了 RAG 知识库功能、是否启用了联网搜索等）是否被用户的特权囊括。
        如果出现越权尝试，立刻抛出 PermissionError，前端捕捉后可以给出续费提示。
        
        :param context: 包含用户特权列表和其申请调用的业务动作参数的执行上下文。
        :raises PermissionError: 当缺乏前置会员权益时主动阻断对话生成。
        """
        if context.enable_rag and "rag" not in context.privileges:
            raise PermissionError("MEMBER_REQUIRED: 当前套餐不支持知识库检索")
        if context.enable_search and "web_search" not in context.privileges:
            raise PermissionError("PRIVILEGE_REQUIRED: 当前套餐不支持联网搜索")
        if context.route == "contract-chat" and not (
            {"contract_review", "contract_screening"} & context.privileges
        ):
            raise PermissionError("PRIVILEGE_REQUIRED: 当前套餐不支持合同审查")
