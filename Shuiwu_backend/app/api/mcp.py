"""
MCP 路由
只包含接口端点定义
"""
from fastapi import APIRouter

from app.schemas.mcp import (
    MCPServiceListResponse,
    MCPServiceInfo,
    MCPToolsResponse,
    MCPToolInfo,
    TestMCPServiceResponse,
    MCPTestRequest,
    MCPTestResponse,
    MCPServiceStatusResponse,
)
from app.services.mcp.mcp_service import mcp_service_manager, mcp_test_service
from app.utils.response import response

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


@router.get("/services", response_model=MCPServiceListResponse)
async def list_mcp_services():
    """获取所有MCP服务列表"""
    try:
        services_dict = mcp_service_manager.list_services()

        services_info = {}
        for service_id, info in services_dict.items():
            services_info[service_id] = MCPServiceInfo(
                service_id=service_id,
                config=info["config"],
                tools=info["tools"],
                status=info["status"]
            )

        return MCPServiceListResponse(services=services_info)
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        print(f"获取MCP服务列表失败: {error_detail}")
        return response.fail(message=f"获取服务列表失败: {str(e)}")


@router.get("/services/{service_id}", response_model=MCPServiceInfo)
async def get_mcp_service(service_id: str):
    """获取特定MCP服务详情"""
    config = mcp_service_manager.get_service_config(service_id)
    if not config:
        return response.fail(message="服务不存在")

    service = mcp_service_manager.get_service(service_id)
    tools = []
    if service:
        if hasattr(service, 'tools') and service.tools:
            tools = list(service.tools.keys())
        elif hasattr(service, 'functions') and service.functions:
            tools = list(service.functions.keys())

    return MCPServiceInfo(
        service_id=service_id,
        config=config or {},
        tools=tools,
        status="connected" if service else "created"
    )


@router.get("/services/{service_id}/status", response_model=MCPServiceStatusResponse)
async def get_service_status(service_id: str):
    """获取MCP服务状态（基于配置和缓存信息，不进行实时连接）"""
    try:
        config = mcp_service_manager.get_service_config(service_id)
        if not config:
            return MCPServiceStatusResponse(
                service_id=service_id,
                status="error",
                is_reachable=False,
                error="服务不存在"
            )

        # 检查内存中是否有缓存的实例
        service = mcp_service_manager.get_service(service_id)
        if service and hasattr(service, 'initialized') and service.initialized:
            return MCPServiceStatusResponse(
                service_id=service_id,
                status="connected",
                is_reachable=True,
                error=None
            )

        # 服务配置存在但未初始化，返回created状态
        return MCPServiceStatusResponse(
            service_id=service_id,
            status="created",
            is_reachable=True,  # 配置有效，假设可达
            error=None
        )
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        print(f"获取MCP服务状态失败: {error_detail}")
        return MCPServiceStatusResponse(
            service_id=service_id,
            status="error",
            is_reachable=False,
            error=str(e)
        )


@router.get("/services/{service_id}/tools")
async def get_service_tools(service_id: str):
    """获取MCP服务的可用工具（基于配置或缓存）"""
    try:
        config = mcp_service_manager.get_service_config(service_id)
        if not config:
            return response.fail(message=f"服务 {service_id} 不存在")

        # 首先检查是否有已初始化的服务（包含实际工具）
        service = mcp_service_manager.get_service(service_id)
        if service and hasattr(service, 'initialized') and service.initialized:
            # 使用实际连接的工具信息
            tools_info_dict = mcp_service_manager.get_service_tools_info(service_id)
        else:
            # 返回基于配置的预期工具信息
            transport = config.get("transport", "stdio")
            tools_info_dict = {}

            if transport == "streamable-http":
                url = config.get("url", "")
                if "dashscope.aliyuncs.com" in url:
                    # 阿里云企业风险查询服务
                    tools_info_dict = {
                        "searchEnterpriseRiskInfo": {
                            "name": "searchEnterpriseRiskInfo",
                            "description": "查询企业风险信息",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "companyName": {
                                        "type": "string",
                                        "description": "企业名称"
                                    }
                                },
                                "required": ["companyName"]
                            }
                        },
                        "searchEnterpriseBasicInfo": {
                            "name": "searchEnterpriseBasicInfo",
                            "description": "查询企业基本信息",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "companyName": {
                                        "type": "string",
                                        "description": "企业名称"
                                    }
                                },
                                "required": ["companyName"]
                            }
                        }
                    }
                else:
                    # 其他HTTP服务
                    tools_info_dict = {
                        "http_tool": {
                            "name": "http_tool",
                            "description": "HTTP服务工具",
                            "parameters": {}
                        }
                    }
            elif transport == "stdio":
                # stdio传输的工具
                tools_info_dict = {
                    "stdio_tool": {
                        "name": "stdio_tool",
                        "description": "本地进程工具",
                        "parameters": {}
                    }
                }

        return response.success(data={"tools": tools_info_dict})
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        print(f"获取MCP工具列表失败: {error_detail}")
        return response.fail(message=f"获取工具列表失败: {str(e)}")


@router.post("/services/{service_id}/test", response_model=TestMCPServiceResponse)
async def test_mcp_service(service_id: str):
    """测试MCP服务连接（返回配置信息，不进行实时连接）"""
    try:
        config = mcp_service_manager.get_service_config(service_id)
        if not config:
            raise ValueError(f"服务 {service_id} 不存在")

        service = mcp_service_manager.get_service(service_id)
        if not service:
            # 创建MCPTools实例但不连接
            from app.agno.tools.mcp.mcp_tools import create_mcp_tools_from_config
            service = create_mcp_tools_from_config(config)
            mcp_service_manager.services[service_id] = service

        # 获取预期的工具信息（基于配置）
        transport = config.get("transport", "stdio")
        tools_preview = []

        if transport == "streamable-http":
            url = config.get("url", "")
            if "dashscope.aliyuncs.com" in url:
                # 阿里云企业风险查询服务
                tools_preview = [
                    "searchEnterpriseRiskInfo",
                    "searchEnterpriseBasicInfo"
                ]
            else:
                tools_preview = ["HTTP服务工具"]

        return TestMCPServiceResponse(
            status="created",  # 配置已创建
            tools_count=len(tools_preview),
            tools=tools_preview[:10],  # 返回前10个工具
            error=None
        )
    except ValueError as e:
        return response.fail(message=str(e))
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        print(f"测试MCP服务失败: {error_detail}")
        return TestMCPServiceResponse(
            status="error",
            tools_count=0,
            tools=[],
            error=str(e)
        )


@router.post("/services/{service_id}/connect")
async def connect_service(service_id: str):
    """
    实际连接MCP服务（仅在需要时调用）
    注意：此端点会在FastAPI请求上下文中执行MCP连接，可能会超时
    建议使用 /test 端点验证配置，然后在Agent使用时自动连接
    """
    try:
        config = mcp_service_manager.get_service_config(service_id)
        if not config:
            return response.fail(message="服务不存在")

        result = await mcp_service_manager.test_service(service_id)
        return TestMCPServiceResponse(**result)
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        print(f"连接MCP服务失败: {error_detail}")
        return TestMCPServiceResponse(
            status="error",
            tools_count=0,
            tools=[],
            error=f"连接超时或失败: {str(e)}"[:200]  # 限制错误信息长度
        )


@router.post("/test", response_model=MCPTestResponse)
async def test_mcp_with_agent(request: MCPTestRequest):
    """使用Agent测试MCP服务功能"""
    import asyncio
    try:
        result = await mcp_test_service.test_mcp_with_agent(
            service_id=request.service_id,
            message=request.message,
            model_id=request.model_id,
            openai_api_key=request.openai_api_key,
            openai_base_url=request.openai_base_url
        )
        return MCPTestResponse(**result)
    except asyncio.CancelledError:
        # 如果请求被取消,返回错误响应
        return MCPTestResponse(
            status="error",
            content=None,
            error="请求被取消,可能是超时或连接问题"
        )
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        print(f"MCP Agent测试失败: {error_detail}")
        return MCPTestResponse(
            status="error",
            content=None,
            error=str(e)
        )
