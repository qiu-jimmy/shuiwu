"""
聊天核心调度服务 (Chat Service)
=================================
连接 API 控制器和底层 Agent 执行链路的中枢模块。
负责统筹会话历史的读取/追加、权限校验、智能调度（Supervisor）、Agent 实例化以及流式输出封装。
"""

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
        """
        初始化核心服务，挂载所需的基础设施与核心服务模块。
        """
        self.session_store = session_store
        self.agent_factory = agent_factory or AgentFactory()
        self.permission_gateway = permission_gateway or PermissionGateway()
        # 启动基于规则的默认调度器
        self.supervisor = RuleBasedSupervisor()

    async def stream_chat(self, request: ChatRequest, route: str) -> AsyncIterator[dict]:
        """
        通用流式会话方法。完成从接受请求到 SSE 流式抛出模型内容的完整生命周期。
        
        :param request: HTTP 传入的对话请求实体
        :param route: 所期望的执行子路由（例如 chat, full-feature, supervisor 等）
        :yield: 发送给前端的各类数据块（content, completed, error 等格式字典）
        """
        request_id = str(uuid.uuid4())
        try:
            final_route = route
            enable_rag = request.enable_rag
            enable_search = request.enable_search
            
            # 1. 意图调度：如果指定了 supervisor，则通过意图判断重新计算并覆盖最终的执行路由和启用工具
            if route == "supervisor":
                decision = self.supervisor.decide(request.message, has_files=bool(request.files))
                final_route = decision.route.value
                enable_rag = enable_rag or decision.enable_rag
                enable_search = enable_search or decision.enable_search

            # 2. 权限读取：从网关处获取用户的订阅、会员和特权列表
            privileges = await self.permission_gateway.get_privileges(request.user_id)
            
            # 3. 构造当前执行的统一上下文 (Context)
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
            
            # 4. 执行严苛的调用前权限校验
            await self.permission_gateway.assert_allowed(context)
            
            # 5. 基于上下文动态生产 LangChain Agent 或者 Runnable (例如 Normal Agent)
            agent = self.agent_factory.create(context)
            
            # 6. 获取和修剪历史会话记录（默认获取最近10条作为多轮记忆）
            raw_history = await self.session_store.get_messages(request.user_id, request.session_id)
            raw_history = raw_history[-10:] if raw_history else []
            
            # 7. 根据生成的 agent 种类不同（真模型 vs 模拟器）调用对应接口
            if not hasattr(agent, "tools"):
                # 如果对象没有 tools 属性，说明它是原生的 LangChain LCEL 链
                from langchain_core.messages import HumanMessage, AIMessage
                chat_history = []
                for msg in raw_history:
                    if msg["role"] == "user":
                        chat_history.append(HumanMessage(content=msg["content"]))
                    else:
                        chat_history.append(AIMessage(content=msg["content"]))
                
                # 传入历史会话并等待模型的推理返回
                response = await agent.ainvoke({"input": request.message, "chat_history": chat_history})
                if isinstance(response, dict) and "output" in response:
                    answer = response["output"]
                else:
                    answer = response.content if hasattr(response, "content") else str(response)
            else:
                # 否则可能是 AgentExecutor 或是兜底的 MockAgent
                answer = await agent.ainvoke(request.message)
                
            # 8. 持久化记录本次的双向交流文本
            await self.session_store.append_message(request.user_id, request.session_id, "user", request.message)
            await self.session_store.append_message(request.user_id, request.session_id, "assistant", answer)
            
            # 9. 将合并后的大段模型文本按区块进行切分，模拟流式 SSE 输出体验给前端
            for chunk in self._chunk_text(answer):
                yield {"type": "content", "content": chunk}
                
            # 10. 抛出最终完成信号
            yield {"type": "completed", "data": {"request_id": request_id, "route": final_route}}
        except Exception as exc:
            yield {"type": "error", "message": str(exc), "data": {"request_id": request_id}}

    async def stream_contract_review(self, request: ContractReviewRequest) -> AsyncIterator[dict]:
        """
        专门处理合同评审请求的服务入口，将其转化为标准的 ChatRequest，然后使用合同评审特定的路邮进行分发。
        """
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
        """
        将大段文本强行切分为指定字符数的切片数组，用于在未使用原生 Stream 接口时模拟流式吐出。
        """
        return [text[i : i + size] for i in range(0, len(text), size)] or [""]
