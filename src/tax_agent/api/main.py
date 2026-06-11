"""
LangChain Agent API 入口文件
=================================
此文件负责初始化 FastAPI 应用，挂载中间件，并定义了所有与会话和聊天相关的 API 路由。
这些路由保持了与旧版 /api/chat/* 的兼容性，允许前端（如微信小程序）零修改接入。
"""

import json
import uuid
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from tax_agent.schemas import ChatRequest, ContractReviewRequest, SessionCreateRequest
from tax_agent.services.chat_service import ChatService
from tax_agent.services.session_store import InMemorySessionStore

# 内存会话存储实例（开发环境使用，后续可替换为数据库实现）
session_store = InMemorySessionStore()
# 核心对话服务，用于处理对话生成、工具挂载及权限校验
chat_service = ChatService(session_store=session_store)

app = FastAPI(
    title="智税引擎 LangChain Agent API",
    description="基于 LangChain 的新版 Agent 服务，保持对旧 API 的兼容。",
    version="0.1.0",
)

# 允许跨域请求（CORS）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def sse_response(events: AsyncIterator[dict]) -> StreamingResponse:
    """
    将异步事件流转化为 Server-Sent Events (SSE) 格式的 StreamingResponse 响应。
    
    :param events: 生成字典的异步迭代器，字典中应包含符合前端协议的响应数据。
    :return: FastAPI 的 StreamingResponse 对象。
    """
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
    """健康检查接口，用于探测服务是否正常存活。"""
    return {"code": 1, "message": "ok", "data": {"status": "ok"}}


@app.post("/api/chat/sessions")
async def create_session(request: SessionCreateRequest) -> dict:
    """
    创建新会话。
    接收用户 ID 和可选的会话名称，创建一个独立上下文。
    """
    session = await session_store.create_session(user_id=request.user_id, name=request.name or "新建会话")
    return {"code": 1, "message": "创建会话成功", "data": session}


@app.get("/api/chat/sessions")
async def list_sessions(user_id: str) -> dict:
    """
    获取指定用户的历史会话列表。
    """
    sessions = await session_store.list_sessions(user_id=user_id)
    return {"code": 1, "message": "获取会话列表成功", "data": {"sessions": sessions}}


@app.get("/api/chat/sessions/{session_id}/messages")
async def get_messages(session_id: str, user_id: str) -> dict:
    """
    获取指定会话内的所有消息历史记录（完整版）。
    """
    messages = await session_store.get_messages(user_id=user_id, session_id=session_id)
    return {"code": 1, "message": "获取消息历史成功", "data": {"messages": messages}}


@app.get("/api/chat/sessions/{session_id}/messages/simple")
async def get_messages_simple(session_id: str, user_id: str) -> dict:
    """
    获取指定会话内的简易消息历史记录。
    此处行为同上，旨在提供向后兼容。
    """
    messages = await session_store.get_messages(user_id=user_id, session_id=session_id)
    return {"code": 1, "message": "获取消息历史成功", "data": {"messages": messages}}


@app.post("/api/chat/chat")
async def chat(_: Request, body: ChatRequest) -> StreamingResponse:
    """
    基础对话接口 (Normal Tax Agent)。
    默认不挂载重型工具，仅用于基础税务常识、流程的解释。遇到精确需求时将引导升级。
    """
    return sse_response(chat_service.stream_chat(body, route="chat"))


@app.post("/api/chat/full-feature")
async def full_feature(_: Request, body: ChatRequest) -> StreamingResponse:
    """
    全功能对话接口 (Full Feature Agent)。
    允许 Agent 自主决定是否调用 RAG 知识库检索或联网搜索工具来核验时间敏感型及精准数字口径。
    """
    return sse_response(chat_service.stream_chat(body, route="full-feature"))


@app.post("/api/chat/rag")
async def rag(_: Request, body: ChatRequest) -> StreamingResponse:
    """
    基于知识库的对话接口 (RAG Agent)。
    强制开启 RAG 功能，专门用于基于上传文件或指定文档库的提问。
    """
    body.enable_rag = True
    return sse_response(chat_service.stream_chat(body, route="rag"))


@app.post("/api/chat/supervisor")
async def supervisor(_: Request, body: ChatRequest) -> StreamingResponse:
    """
    智能路由接口 (Supervisor Agent)。
    在请求转交给底层大模型前，基于规则判定用户意图（如“是否有最新政策”、“是否涉及合同风险”），
    将请求自动路由给对应的专用 Agent 进行处理。
    """
    return sse_response(chat_service.stream_chat(body, route="supervisor"))


@app.post("/api/chat/contract-chat")
async def contract_chat(_: Request, body: ContractReviewRequest) -> StreamingResponse:
    """
    合同审查对话接口。
    专注于审查合同文本的风险（包含税务及普通商业风险），对文本进行高强度的风险分析和合规性校验。
    """
    return sse_response(chat_service.stream_contract_review(body))


@app.get("/api/debug/request-id")
async def request_id() -> dict:
    """生成用于调试的唯一 Request ID 接口。"""
    return {"request_id": str(uuid.uuid4())}
