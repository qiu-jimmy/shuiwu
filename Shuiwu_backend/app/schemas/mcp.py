"""
MCP 相关的 Pydantic 模型
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class MCPServiceInfo(BaseModel):
    """MCP服务信息"""
    service_id: str
    config: Dict[str, Any]
    tools: List[str]
    status: str


class MCPServiceListResponse(BaseModel):
    """MCP服务列表响应"""
    services: Dict[str, MCPServiceInfo]


class MCPToolInfo(BaseModel):
    """MCP工具信息"""
    name: str
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class MCPToolsResponse(BaseModel):
    """MCP工具列表响应"""
    tools: Dict[str, MCPToolInfo]


class TestMCPServiceResponse(BaseModel):
    """测试MCP服务响应"""
    status: str
    tools_count: int
    tools: List[str]
    error: Optional[str] = None


class MCPTestRequest(BaseModel):
    """MCP测试请求"""
    model_config = ConfigDict(protected_namespaces=())
    
    service_id: str
    message: str
    model_id: str = "qwen-plus"
    # OpenAI API配置（前端输入）
    openai_api_key: Optional[str] = Field(None, description="OpenAI API Key")
    openai_base_url: Optional[str] = Field(None, description="OpenAI Base URL")


class MCPTestResponse(BaseModel):
    """MCP测试响应"""
    status: str
    content: Optional[str] = None
    error: Optional[str] = None


class MCPServiceStatusResponse(BaseModel):
    """MCP服务状态检查响应"""
    service_id: str
    status: str  # "connected" | "disconnected" | "error"
    is_reachable: bool
    error: Optional[str] = None
