import uuid
from collections.abc import AsyncIterator

from tax_agent.agents.factory import AgentFactory
from tax_agent.agents.supervisor import RuleBasedSupervisor
from tax_agent.schemas import AgentContext, ChatRequest, ContractReviewRequest
from tax_agent.services.permission_gateway import PermissionGateway
from tax_agent.services.session_store import InMemorySessionStore


class ChatService:
    def __init__(
        self,
        session_store: InMemorySessionStore,
        agent_factory: AgentFactory | None = None,
        permission_gateway: PermissionGateway | None = None,
    ) -> None:
        self.session_store = session_store
        self.agent_factory = agent_factory or AgentFactory()
        self.permission_gateway = permission_gateway or PermissionGateway()
        self.supervisor = RuleBasedSupervisor()

    async def stream_chat(self, request: ChatRequest, route: str) -> AsyncIterator[dict]:
        request_id = str(uuid.uuid4())
        try:
            final_route = route
            enable_rag = request.enable_rag
            enable_search = request.enable_search
            if route == "supervisor":
                decision = self.supervisor.decide(request.message, has_files=bool(request.files))
                final_route = decision.route.value
                enable_rag = enable_rag or decision.enable_rag
                enable_search = enable_search or decision.enable_search

            privileges = await self.permission_gateway.get_privileges(request.user_id)
            context = AgentContext(
                user_id=request.user_id,
                session_id=request.session_id,
                route=final_route,
                model_id=request.model_id,
                temperature=request.temperature if request.temperature is not None else 0.3,
                enable_rag=enable_rag,
                enable_search=enable_search,
                knowledge_base=request.knowledge_base,
                request_id=request_id,
                privileges=privileges,
                metadata=request.metadata,
            )
            await self.permission_gateway.assert_allowed(context)
            agent = self.agent_factory.create(context)
            answer = await agent.ainvoke(request.message)
            await self.session_store.append_message(request.user_id, request.session_id, "user", request.message)
            await self.session_store.append_message(request.user_id, request.session_id, "assistant", answer)
            for chunk in self._chunk_text(answer):
                yield {"type": "content", "content": chunk}
            yield {"type": "completed", "data": {"request_id": request_id, "route": final_route}}
        except Exception as exc:
            yield {"type": "error", "message": str(exc), "data": {"request_id": request_id}}

    async def stream_contract_review(self, request: ContractReviewRequest) -> AsyncIterator[dict]:
        chat_request = ChatRequest(
            user_id=request.user_id,
            session_id=request.metadata.get("session_id", f"contract-{uuid.uuid4()}"),
            message=request.message or "请审查这份合同，指出其中的风险条款",
            model_id=request.model_id,
            temperature=request.temperature,
            files=request.files,
            metadata=request.metadata,
        )
        async for event in self.stream_chat(chat_request, route="contract-chat"):
            yield event

    @staticmethod
    def _chunk_text(text: str, size: int = 80) -> list[str]:
        return [text[i : i + size] for i in range(0, len(text), size)] or [""]
