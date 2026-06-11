from typing import Any, Literal

from pydantic import BaseModel, Field


class Attachment(BaseModel):
    filename: str
    file_base64: str
    mime_type: str | None = None


class ChatRequest(BaseModel):
    user_id: str
    session_id: str
    message: str = ""
    model_id: str = "qwen-flash"
    temperature: float | None = None
    enable_rag: bool = False
    enable_search: bool = False
    knowledge_base: str | None = None
    images: list[Attachment] = Field(default_factory=list)
    files: list[Attachment] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContractReviewRequest(BaseModel):
    user_id: str
    message: str | None = "请审查这份合同，指出其中的风险条款"
    model_id: str = "qwen-plus"
    temperature: float | None = 0.6
    files: list[Attachment] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionCreateRequest(BaseModel):
    user_id: str
    name: str | None = "新建会话"


class AgentEvent(BaseModel):
    type: Literal["content", "completed", "error", "references", "tool_event"]
    content: str | None = None
    message: str | None = None
    data: Any = None


class AgentContext(BaseModel):
    user_id: str
    session_id: str | None = None
    route: str
    model_id: str
    temperature: float
    enable_rag: bool = False
    enable_search: bool = False
    knowledge_base: str | None = None
    request_id: str | None = None
    privileges: set[str] = Field(default_factory=set)
    quotas: dict[str, int] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
