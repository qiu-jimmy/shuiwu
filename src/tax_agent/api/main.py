import json
import uuid
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from tax_agent.schemas import ChatRequest, ContractReviewRequest, SessionCreateRequest
from tax_agent.services.chat_service import ChatService
from tax_agent.services.session_store import InMemorySessionStore


session_store = InMemorySessionStore()
chat_service = ChatService(session_store=session_store)

app = FastAPI(
    title="智税引擎 LangChain Agent API",
    description="New LangChain-based Agent service with legacy API compatibility.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def sse_response(events: AsyncIterator[dict]) -> StreamingResponse:
    async def iterator() -> AsyncIterator[str]:
        async for event in events:
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        iterator(),
        media_type="text/event-stream; charset=utf-8",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.get("/health")
async def health_check() -> dict:
    return {"code": 1, "message": "ok", "data": {"status": "ok"}}


@app.post("/api/chat/sessions")
async def create_session(request: SessionCreateRequest) -> dict:
    session = await session_store.create_session(user_id=request.user_id, name=request.name or "新建会话")
    return {"code": 1, "message": "创建会话成功", "data": session}


@app.get("/api/chat/sessions")
async def list_sessions(user_id: str) -> dict:
    sessions = await session_store.list_sessions(user_id=user_id)
    return {"code": 1, "message": "获取会话列表成功", "data": {"sessions": sessions}}


@app.get("/api/chat/sessions/{session_id}/messages")
async def get_messages(session_id: str, user_id: str) -> dict:
    messages = await session_store.get_messages(user_id=user_id, session_id=session_id)
    return {"code": 1, "message": "获取消息历史成功", "data": {"messages": messages}}


@app.get("/api/chat/sessions/{session_id}/messages/simple")
async def get_messages_simple(session_id: str, user_id: str) -> dict:
    messages = await session_store.get_messages(user_id=user_id, session_id=session_id)
    return {"code": 1, "message": "获取消息历史成功", "data": {"messages": messages}}


@app.post("/api/chat/chat")
async def chat(_: Request, body: ChatRequest) -> StreamingResponse:
    return sse_response(chat_service.stream_chat(body, route="chat"))


@app.post("/api/chat/full-feature")
async def full_feature(_: Request, body: ChatRequest) -> StreamingResponse:
    return sse_response(chat_service.stream_chat(body, route="full-feature"))


@app.post("/api/chat/rag")
async def rag(_: Request, body: ChatRequest) -> StreamingResponse:
    body.enable_rag = True
    return sse_response(chat_service.stream_chat(body, route="rag"))


@app.post("/api/chat/supervisor")
async def supervisor(_: Request, body: ChatRequest) -> StreamingResponse:
    return sse_response(chat_service.stream_chat(body, route="supervisor"))


@app.post("/api/chat/contract-chat")
async def contract_chat(_: Request, body: ContractReviewRequest) -> StreamingResponse:
    return sse_response(chat_service.stream_contract_review(body))


@app.get("/api/debug/request-id")
async def request_id() -> dict:
    return {"request_id": str(uuid.uuid4())}
