"""
Chat 相关的 Pydantic 模型
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class CreateSessionRequest(BaseModel):
    """创建会话请求"""
    user_id: str
    name: Optional[str] = None


class ChatMessageRequest(BaseModel):
    """普通对话请求（支持多模态）"""
    model_config = ConfigDict(protected_namespaces=())

    session_id: str
    user_id: str
    message: str
    model_id: str = "qwen-flash"
    enable_rag: bool = False
    knowledge_base: Optional[str] = None
    images: Optional[List[Dict[str, str]]] = None  # [{"filename": "...", "file_base64": "..."}]
    files: Optional[List[Dict[str, str]]] = None   # [{"filename": "...", "file_base64": "..."}]


class ContractReviewRequest(BaseModel):
    """合同审查请求（无会话模式）"""
    model_config = ConfigDict(protected_namespaces=())

    user_id: str
    message: Optional[str] = None  # 审查要求（可选）
    model_id: str = "qwen-plus"
    temperature: Optional[float] = 0.6  # 温度参数
    images: Optional[List[Dict[str, str]]] = None  # 支持上传合同图片
    files: List[Dict[str, str]]  # 合同文件列表（必需）


class ChatWithSearchRequest(BaseModel):
    """在线搜索对话请求（支持多模态）"""
    model_config = ConfigDict(protected_namespaces=())

    session_id: str
    user_id: str
    message: str
    model_id: str = "qwen-plus"
    enable_rag: bool = False
    knowledge_base: Optional[str] = None
    images: Optional[List[Dict[str, str]]] = None
    files: Optional[List[Dict[str, str]]] = None


class FullFeatureChatRequest(BaseModel):
    """全功能对话请求（支持多模态 + 联网搜索 + RAG）"""
    model_config = ConfigDict(protected_namespaces=())

    session_id: str
    user_id: str
    message: str
    model_id: str = "qwen-plus"
    enable_rag: bool = False  # 是否启用智能知识库检索（Agent 自主决策是否使用）
    enable_search: bool = False  # 是否启用联网搜索（Agent 自主决策是否使用）
    knowledge_base: Optional[str] = None  # 已弃用：Agent 会自动检索所有相关知识库，无需手动指定
    images: Optional[List[Dict[str, str]]] = None
    files: Optional[List[Dict[str, str]]] = None


class RagQueryRequest(ChatMessageRequest):
    """RAG 查询请求（支持多模态）"""
    pass


class FileUploadRequest(BaseModel):
    """文件上传请求"""
    session_id: str
    file_base64: str
    filename: str


class UpdateSessionRequest(BaseModel):
    """更新会话请求"""
    session_id: str
    user_id: str
    name: str


class DeleteSessionRequest(BaseModel):
    """删除会话请求"""
    session_id: str
    user_id: str


class DeleteAllSessionsRequest(BaseModel):
    """删除用户所有会话请求"""
    user_id: str


class SessionResponse(BaseModel):
    """会话响应"""
    status: str
    session_id: str
    name: str
    created_at: str


class SessionListItem(BaseModel):
    """会话列表项"""
    id: str
    name: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class MessageItem(BaseModel):
    """消息项"""
    id: str
    role: str
    content: str
    timestamp: str
    rag_files: Optional[List[Dict[str, Any]]] = None  # 改为字典列表，包含 file_name, kb_name, source, relevance
    search_results: Optional[List[Dict[str, str]]] = None
    quote_content: Optional[str] = None
    is_reasoning: Optional[bool] = False  # 标记是否为推理过程（Supervisor 决策）
    thinking: Optional[str] = None  # ✅ Supervisor 的思维链推理过程（添加到 content 消息中）


class KnowledgeBaseItem(BaseModel):
    """知识库项"""
    kb_name: str
    description: str
    user_id: str
    document_count: int
