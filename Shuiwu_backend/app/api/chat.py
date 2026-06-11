"""
Chat 路由 - 只包含接口端点定义
高内聚:集中处理所有 Chat 相关的 HTTP 请求
低耦合:业务逻辑委托给 Service 层,Agent 执行委托给 Runner 层
"""
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.schemas.chat import (
    CreateSessionRequest,
    ChatMessageRequest,
    ContractReviewRequest,
    ChatWithSearchRequest,
    FullFeatureChatRequest,
    RagQueryRequest,
    UpdateSessionRequest,
    DeleteSessionRequest,
    DeleteAllSessionsRequest,
)
from app.services.chat.chat_service import chat_service
from app.utils.response import response
from app.middleware.member_permission import (
    require_member_privilege,
    require_member_quota,
    require_member_features,
    require_any_member_privilege,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/sessions")
async def create_session_endpoint(request: CreateSessionRequest):
    """创建新会话"""
    try:
        result = await chat_service.create_session(request.user_id, request.name)
        return response.success(data=result, message="创建会话成功")
    except Exception as e:
        return response.fail(message=str(e))


@router.put("/sessions")
async def update_session_endpoint(request: UpdateSessionRequest):
    """更新会话名称"""
    try:
        result = await chat_service.update_session_name(request.session_id, request.user_id, request.name)
        return response.success(data=result, message="更新会话名称成功")
    except Exception as e:
        if "不存在" in str(e) or "无权限" in str(e):
            return response.fail(message=str(e))
        return response.fail(message=str(e))


@router.delete("/sessions")
async def delete_session_endpoint(request: DeleteSessionRequest):
    """删除单个会话"""
    try:
        result = await chat_service.delete_session(request.session_id, request.user_id)
        return response.success(data=result, message="删除会话成功")
    except Exception as e:
        if "不存在" in str(e) or "无权限" in str(e):
            return response.fail(message=str(e))
        return response.fail(message=str(e))


@router.delete("/sessions/all")
async def delete_all_sessions_endpoint(request: DeleteAllSessionsRequest):
    """删除用户的所有会话"""
    try:
        result = await chat_service.delete_all_sessions(request.user_id)
        return response.success(data=result, message=result.get("message", f"成功删除 {result.get('deleted_count', 0)} 个会话"))
    except Exception as e:
        return response.fail(message=str(e))


@router.get("/sessions")
async def list_sessions_endpoint(user_id: str):
    """获取指定用户的所有会话"""
    try:
        result = await chat_service.list_sessions(user_id)
        return response.success(data=result, message="获取会话列表成功")
    except Exception as e:
        return response.fail(message=str(e))


@router.get("/sessions/{session_id}/messages")
async def get_session_messages_endpoint(session_id: str, user_id: str):
    """获取会话消息历史（Supervisor-Agent Workflow，role 映射：Supervisor→content, 专家→assistant）"""
    try:
        result = await chat_service.get_session_messages(session_id, user_id)
        return response.success(data=result, message="获取消息历史成功")
    except Exception as e:
        if "不存在" in str(e) or "无权" in str(e):
            return response.fail(message=str(e))
        return response.fail(message=str(e))


@router.get("/sessions/{session_id}/messages/simple")
async def get_session_messages_simple_endpoint(session_id: str, user_id: str):
    """获取会话消息历史（简化版本，用于普通对话）"""
    try:
        result = await chat_service.get_session_messages_simple(session_id, user_id)
        return response.success(data=result, message="获取消息历史成功")
    except Exception as e:
        if "不存在" in str(e) or "无权" in str(e):
            return response.fail(message=str(e))
        return response.fail(message=str(e))


@router.post("/chat")
@require_member_quota("daily_chats", consume=1)
async def chat_message(request: Request, chat_request: ChatMessageRequest):
    """普通对话接口(支持多模态) - 需要每日聊天配额"""
    try:
        response_generator = await chat_service.handle_chat_stream(
            request=chat_request,
            enable_search=False,
            chat_type="normal",
        )
        return StreamingResponse(
            response_generator,
            media_type="text/event-stream; charset=utf-8",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
    except Exception as e:
        return response.fail(message=str(e))


@router.post("/contract-chat")
@require_any_member_privilege(["contract_screening", "contract_review"])
@require_member_quota("contract_review_count", consume=1)
async def contract_chat(request: Request, contract_request: ContractReviewRequest):
    """
    合同审查接口（无会话模式）- 需要合同审查或合同筛查权限

    功能：
    - 上传合同文件并进行漏洞检测
    - 从乙方视角审查合同，识别对乙方不利的条款
    - 不保存会话历史，每次调用都是独立的合同审查
    - 不需要 session_id 参数

    权限说明：
    - contract_screening: 合同筛查权限（基础版，3页内）
    - contract_review: 合同审查权限（完整版，支持多页合同）

    用法：
    - 在 files 参数中上传合同文件（必需）
    - 在 message 参数中说明审查要求（可选，默认为"请审查这份合同，指出其中的风险条款"）

    请求体示例：
    {
      "user_id": "user_123",
      "message": "请帮我审查这份合同，指出其中的风险条款",
      "model_id": "qwen-plus",
      "temperature": 0.6  // 可选
      "files": [
        {
          "filename": "合同.docx",
          "file_base64": "..."
        }
      ]
    }
    """
    try:
        response_generator = await chat_service.handle_contract_review(
            request=contract_request,
        )
        return StreamingResponse(
            response_generator,
            media_type="text/event-stream; charset=utf-8",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
    except Exception as e:
        return response.fail(message=str(e))


@router.post("/chat-with-search")
@require_member_privilege("web_search")
@require_member_quota("daily_chats", consume=1)
async def chat_with_search(request: Request, search_request: ChatWithSearchRequest):
    """在线搜索对话接口(启用搜索) - 需要联网搜索权限和每日聊天配额"""
    try:
        response_generator = await chat_service.handle_chat_stream(
            request=search_request,
            enable_search=True,
            chat_type="search",
        )
        return StreamingResponse(
            response_generator,
            media_type="text/event-stream; charset=utf-8",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
    except Exception as e:
        return response.fail(message=str(e))


@router.post("/rag")
@require_member_privilege("rag")
@require_member_quota("daily_chats", consume=1)
async def rag_query(request: Request, rag_request: RagQueryRequest):
    """RAG查询接口 - 需要RAG权限和每日聊天配额"""
    if not rag_request.enable_rag or not rag_request.knowledge_base:
        return response.fail(message="RAG查询需要启用RAG并指定知识库")

    try:
        response_generator = await chat_service.handle_chat_stream(
            request=rag_request,
            enable_search=False,
            chat_type="rag",
        )
        return StreamingResponse(
            response_generator,
            media_type="text/event-stream; charset=utf-8",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
    except Exception as e:
        return response.fail(message=str(e))


@router.post("/full-feature")
@require_any_member_privilege(["rag", "web_search"])
@require_member_quota("daily_chats", consume=1)
async def full_feature_chat(request: Request, full_request: FullFeatureChatRequest):
    """
    全功能对话接口（支持多模态 + 联网搜索 + 智能RAG） - 需要RAG或联网搜索权限（至少其一）

    特性：
    - 支持文本、图片、文件上传
    - 联网搜索（百度 + DuckDuckGo）：由 request.enable_search 参数控制
    - 智能知识库检索：Agent 自动判断是否检索知识库，无需手动指定知识库名称
    - AI 智能判断何时调用搜索、何时检索知识库

    权限说明：
    - 用户只需拥有 rag 或 web_search 其中一个权限即可使用
    - Agent 会根据问题类型和参数自主决定使用哪些工具

    知识库检索说明：
    - enable_rag=True 时，Agent 可使用「搜索所有知识库」工具
    - 该工具自动检索系统知识库和用户个人知识库
    - 无需传递 knowledge_base 参数（已弃用）

    参数说明：
    - enable_search: 是否启用联网搜索（默认 False，由前端/用户控制）
    - enable_rag: 是否启用智能知识库检索（默认 true）
    """
    try:
        response_generator = await chat_service.handle_chat_stream(
            request=full_request,
            enable_search=full_request.enable_search,  # ✅ 使用请求中的值，而非硬编码
            chat_type="full",  # 全功能类型
        )
        return StreamingResponse(
            response_generator,
            media_type="text/event-stream; charset=utf-8",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
    except Exception as e:
        return response.fail(message=str(e))


@router.get("/knowledge-bases")
async def get_knowledge_bases_endpoint(user_id: str):
    """获取用户的知识库列表"""
    try:
        result = chat_service.get_knowledge_bases(user_id)
        return response.success(data=result, message="获取知识库列表成功")
    except Exception as e:
        return response.fail(message=str(e))


@router.post("/supervisor")
@require_any_member_privilege(["rag", "web_search"])
@require_member_quota("daily_chats", consume=1)
async def supervisor_chat(request: Request, supervisor_request: FullFeatureChatRequest):
    """
    Supervisor-Agent 对话接口（领导-专家模式） - 需要RAG或联网搜索权限（至少其一）

    特性：
    - Supervisor Agent（领导）分析用户输入
    - 自动判断是否与税务相关
    - 智能决策是否启用工具、RAG、联网搜索
    - 派发给专业 Agent 处理
    - 支持文本、图片、文件上传

    权限说明：
    - 用户只需拥有 rag 或 web_search 其中一个权限即可使用
    - Agent 会根据问题类型和参数自主决定使用哪些工具

    与 full-feature 接口的区别：
    - full-feature: Workflow 内部 Router 自动路由
    - supervisor: Supervisor Agent 智能分析决策后路由
    """
    try:
        response_generator = await chat_service.handle_supervisor_chat_stream(
            request=supervisor_request,
        )
        return StreamingResponse(
            response_generator,
            media_type="text/event-stream; charset=utf-8",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
    except Exception as e:
        return response.fail(message=str(e))



