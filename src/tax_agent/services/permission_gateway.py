from tax_agent.schemas import AgentContext


class PermissionGateway:
    """Bridge to legacy membership and quota system.

    Current scaffold allows everything. P2 should call the legacy backend or query
    the old business schema to enforce privileges and consume quotas.
    """

    async def get_privileges(self, user_id: str) -> set[str]:
        return {
            "daily_chats",
            "rag",
            "web_search",
            "mcp_tools",
            "contract_review",
            "contract_screening",
        }

    async def assert_allowed(self, context: AgentContext) -> None:
        if context.enable_rag and "rag" not in context.privileges:
            raise PermissionError("MEMBER_REQUIRED: 当前套餐不支持知识库检索")
        if context.enable_search and "web_search" not in context.privileges:
            raise PermissionError("PRIVILEGE_REQUIRED: 当前套餐不支持联网搜索")
        if context.route == "contract-chat" and not (
            {"contract_review", "contract_screening"} & context.privileges
        ):
            raise PermissionError("PRIVILEGE_REQUIRED: 当前套餐不支持合同审查")
