"""
MCP 服务
处理MCP服务管理的业务逻辑（使用repository进行数据库操作）
"""
import asyncio
from typing import Any, Dict, Optional

from agno.tools.mcp import MCPTools

from app.services.mcp.mcp_repository import mcp_repository
from app.agno.tools.mcp.mcp_tools import create_mcp_tools_from_config
from app.agno.tools.mcp.mcp_agent import test_mcp_with_agent
from app.agno.tools.mcp.mcp_client import create_mcp_postgres_db


class MCPServiceManager:
    """MCP服务管理器"""

    def __init__(self):
        # 内存中缓存的服务实例（用于运行时）
        self.services: Dict[str, MCPTools] = {}

    def _ensure_database_initialized(self):
        """确保数据库已初始化（委托给repository）"""
        mcp_repository.ensure_database_initialized()

    def get_service(self, service_id: str) -> Optional[MCPTools]:
        """获取MCP服务实例（从内存缓存）"""
        return self.services.get(service_id)

    def get_service_config(self, service_id: str) -> Optional[Dict[str, Any]]:
        """从数据库获取MCP服务配置"""
        return mcp_repository.get_service_config(service_id)

    def list_services(self) -> Dict[str, Dict[str, Any]]:
        """列出所有服务及其配置"""
        services_dict = mcp_repository.list_all_services()

        # 为每个服务添加工具信息和状态
        for service_id, info in services_dict.items():
            service = self.services.get(service_id)
            tools = []
            if service:
                if hasattr(service, 'tools') and service.tools:
                    tools = list(service.tools.keys())
                elif hasattr(service, 'functions') and service.functions:
                    tools = list(service.functions.keys())

            info["tools"] = tools
            # 如果服务已缓存，状态可能是connected，否则是created
            info["status"] = "created"

        return services_dict

    def get_service_tools_info(self, service_id: str) -> Dict[str, Dict[str, Any]]:
        """获取MCP服务的工具详细信息"""
        if not self.get_service_config(service_id):
            raise ValueError(f"服务 {service_id} 不存在")

        service = self.get_service(service_id)
        if not service:
            return {}

        tools_info = {}
        # 检查 tools 属性（新版本agno）
        if hasattr(service, 'tools') and service.tools:
            for tool_name, tool_func in service.tools.items():
                tools_info[tool_name] = {
                    "name": tool_name,
                    "description": getattr(tool_func, '__doc__', '') or getattr(tool_func, 'description', ''),
                    "parameters": getattr(tool_func, 'parameters', {})
                }
        # 检查 functions 属性（旧版本agno）
        elif hasattr(service, 'functions') and service.functions:
            for tool_name, tool_func in service.functions.items():
                tools_info[tool_name] = {
                    "name": tool_name,
                    "description": getattr(tool_func, 'description', ''),
                    "parameters": getattr(tool_func, 'parameters', {})
                }

        return tools_info

    async def check_service_status(self, service_id: str) -> Dict[str, Any]:
        """检查MCP服务状态"""
        import time
        start = time.time()
        print(f"[check_service_status] 开始检查服务状态: {service_id}")

        config = self.get_service_config(service_id)
        if not config:
            return {
                "service_id": service_id,
                "status": "error",
                "is_reachable": False,
                "error": "服务不存在"
            }

        service = self.get_service(service_id)
        if not service:
            print(f"[check_service_status] 创建新的MCP服务实例")
            # 使用agno方法创建服务实例
            service = create_mcp_tools_from_config(config)
            self.services[service_id] = service
            print(f"[check_service_status] 服务实例创建完成，耗时: {time.time() - start:.2f}秒")

        if not hasattr(service, 'initialized') or not service.initialized:
            try:
                print(f"[check_service_status] 开始连接MCP服务")
                connect_start = time.time()
                # 不使用 asyncio.wait_for，让 MCP 服务使用自己的超时设置
                await service.connect()
                print(f"[check_service_status] connect() 完成，耗时: {time.time() - connect_start:.2f}秒")

                build_start = time.time()
                await service.build_tools()
                print(f"[check_service_status] build_tools() 完成，耗时: {time.time() - build_start:.2f}秒")
            except Exception as e:
                print(f"[check_service_status] 连接失败: {e}，耗时: {time.time() - start:.2f}秒")
                import traceback
                traceback.print_exc()
                return {
                    "service_id": service_id,
                    "status": "disconnected",
                    "is_reachable": False,
                    "error": str(e)
                }

        try:
            is_alive_start = time.time()
            is_alive = await asyncio.wait_for(service.is_alive(), timeout=10.0)
            print(f"[check_service_status] is_alive() 完成，耗时: {time.time() - is_alive_start:.2f}秒")
            print(f"[check_service_status] 总耗时: {time.time() - start:.2f}秒")
            return {
                "service_id": service_id,
                "status": "connected" if is_alive else "disconnected",
                "is_reachable": is_alive,
                "error": None
            }
        except asyncio.TimeoutError:
            print(f"[check_service_status] is_alive() 超时")
            return {
                "service_id": service_id,
                "status": "disconnected",
                "is_reachable": False,
                "error": None
            }
        except Exception as e:
            print(f"[check_service_status] is_alive() 失败: {e}")
            return {
                "service_id": service_id,
                "status": "disconnected",
                "is_reachable": False,
                "error": None
            }

    async def test_service(self, service_id: str) -> Dict[str, Any]:
        """测试MCP服务连接"""
        config = self.get_service_config(service_id)
        if not config:
            raise ValueError(f"服务 {service_id} 不存在")

        try:
            service = self.get_service(service_id)
            if not service:
                # 使用agno方法创建服务实例
                service = create_mcp_tools_from_config(config)
                self.services[service_id] = service

            await service.connect()
            await service.build_tools()

            # 获取工具列表
            tools = []
            if hasattr(service, 'tools') and service.tools:
                tools = list(service.tools.keys())
            elif hasattr(service, 'functions') and service.functions:
                tools = list(service.functions.keys())

            return {
                "status": "connected",
                "tools_count": len(tools),
                "tools": tools[:10] if tools else []
            }
        except Exception as e:
            return {
                "status": "error",
                "tools_count": 0,
                "tools": [],
                "error": str(e)
            }

    async def cleanup_all_services(self):
        """清理所有服务连接"""
        for service_id in list(self.services.keys()):
            try:
                service = self.services.get(service_id)
                if service and hasattr(service, 'close'):
                    await asyncio.wait_for(service.close(), timeout=2.0)
            except Exception:
                pass
            finally:
                if service_id in self.services:
                    del self.services[service_id]


# 全局MCP服务管理器实例
mcp_service_manager = MCPServiceManager()


class MCPTestService:
    """MCP测试服务"""

    def __init__(self):
        self.db_schema = "mcp"
        # 初始化数据库schema
        mcp_repository.init_schema_only()
        # 使用agno方法创建PostgresDb实例
        self.db = create_mcp_postgres_db(schema=self.db_schema)

    async def test_mcp_with_agent(
        self,
        service_id: str,
        message: str,
        model_id: str = "qwen-plus",
        openai_api_key: Optional[str] = None,
        openai_base_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """使用Agent测试MCP服务功能（调用agno方法）"""
        import time
        start = time.time()
        print(f"[test_mcp_with_agent] 开始测试MCP服务: {service_id}")

        try:
            # 获取服务配置
            config = mcp_service_manager.get_service_config(service_id)
            if not config:
                raise ValueError(f"MCP服务 {service_id} 不存在")

            print(f"[test_mcp_with_agent] 配置获取完成，耗时: {time.time() - start:.2f}秒")

            # 获取或创建MCP服务实例
            mcp_service = mcp_service_manager.get_service(service_id)
            if not mcp_service:
                print(f"[test_mcp_with_agent] 创建新的MCP服务实例")
                create_start = time.time()
                # 使用agno方法创建服务实例
                mcp_service = create_mcp_tools_from_config(config)
                mcp_service_manager.services[service_id] = mcp_service
                print(f"[test_mcp_with_agent] MCP服务实例创建完成，耗时: {time.time() - create_start:.2f}秒")

            print(f"[test_mcp_with_agent] 准备调用agno test_mcp_with_agent，总耗时: {time.time() - start:.2f}秒")

            # 使用agno方法测试MCP服务
            result = await test_mcp_with_agent(
                mcp_service=mcp_service,
                message=message,
                model_id=model_id,
                openai_api_key=openai_api_key,
                openai_base_url=openai_base_url,
                db=self.db
            )

            print(f"[test_mcp_with_agent] 测试完成，总耗时: {time.time() - start:.2f}秒")
            return result
        except Exception as e:
            import traceback
            error_detail = f"{str(e)}\n{traceback.format_exc()}"
            print(f"MCP测试失败，总耗时: {time.time() - start:.2f}秒")
            print(f"错误详情:\n{error_detail}")
            return {
                "status": "error",
                "content": None,
                "error": str(e)
            }


# 全局MCP测试服务实例
mcp_test_service = MCPTestService()
