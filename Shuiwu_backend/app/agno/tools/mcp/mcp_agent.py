"""
使用 agno Agent 测试 MCP 服务的功能
"""
import asyncio
from typing import Any, Dict, Optional

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.db.postgres import PostgresDb

from app.agno.tools.mcp.mcp_tools import create_mcp_tools_from_config
from agno.tools.mcp import MCPTools


async def test_mcp_with_agent(
    mcp_service: MCPTools,
    message: str,
    model_id: str = "qwen-plus",
    openai_api_key: Optional[str] = None,
    openai_base_url: Optional[str] = None,
    db: Optional[PostgresDb] = None
) -> Dict[str, Any]:
    """
    使用 Agno Agent 测试 MCP 服务功能
    
    Args:
        mcp_service: 已连接的 MCPTools 实例
        message: 测试消息
        model_id: 模型ID
        openai_api_key: OpenAI API Key
        openai_base_url: OpenAI Base URL
        db: PostgresDb 实例（用于Agent会话存储）
    
    Returns:
        测试结果字典，包含 status, content, error
    """
    try:
        # 确保MCP服务已连接并构建工具
        if not hasattr(mcp_service, 'initialized') or not mcp_service.initialized:
            await mcp_service.connect()
            await mcp_service.build_tools()
        
        # 创建 Agent
        model = OpenAIChat(
            id=model_id,
            api_key=openai_api_key or "sk-rjXxGkEiyx1whoVR75C20cFbF5D24a93Bf80E7CbA36b4c77",
            base_url=openai_base_url or "https://api.gpt.ge/v1",
            temperature=0.7,
        )
        
        agent = Agent(
            name="MCP测试Agent",
            model=model,
            tools=[mcp_service],
            db=db,
            instructions=[
                "你是一个测试agent，专门用于验证MCP服务的功能。",
                "请使用可用的MCP工具来完成用户的任务。",
                "在使用工具时，请详细说明你正在使用哪个工具以及为什么使用它。",
            ],
            markdown=True
        )
        
        # 运行agent，添加超时控制（5分钟）
        try:
            result = await asyncio.wait_for(
                agent.arun(message),
                timeout=300.0
            )
            return {
                "status": "success",
                "content": result.content if hasattr(result, 'content') else str(result),
                "error": None
            }
        except asyncio.TimeoutError:
            return {
                "status": "error",
                "content": None,
                "error": "Agent运行超时（超过5分钟），请简化任务或检查MCP服务"
            }
        except asyncio.CancelledError:
            return {
                "status": "error",
                "content": None,
                "error": "Agent运行被取消，可能是超时或连接问题"
            }
    except asyncio.CancelledError:
        return {
            "status": "error",
            "content": None,
            "error": "请求被取消，可能是超时或服务器关闭连接"
        }
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        print(f"MCP Agent测试失败: {error_detail}")
        return {
            "status": "error",
            "content": None,
            "error": str(e)
        }

