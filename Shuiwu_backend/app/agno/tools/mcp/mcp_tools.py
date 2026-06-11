"""
使用 agno 官方 MCP 工具的封装
包含创建和管理 MCPTools 实例的方法
"""
from typing import Any, Dict

from agno.tools.mcp import MCPTools, StreamableHTTPClientParams


def create_mcp_tools_from_config(config: Dict[str, Any]) -> MCPTools:
    """
    从配置创建 MCPTools 实例（使用 agno 官方方法）
    
    使用 Agno 内置的 MCPTools 类，支持三种传输协议：
    - stdio: 本地进程通信
    - sse: 服务器发送事件（已弃用，自动转换为 streamable-http）
    - streamable-http: HTTP流传输（推荐）
    
    Args:
        config: MCP服务配置字典，包含：
            - transport: 传输方式 ("stdio" 或 "streamable-http")
            - command: stdio传输时的命令
            - url: streamable-http传输时的URL
            - env: 环境变量字典
            - timeout_seconds: 超时时间（秒）
            - aliyun_api_key: 阿里云服务的API Key（可选）
            - include_tools: 包含的工具列表（可选）
            - exclude_tools: 排除的工具列表（可选）
    
    Returns:
        MCPTools 实例
    """
    transport = config.get("transport", "stdio")
    default_timeout = 120  # 默认超时时间（从 60 增加到 120 秒，避免超时）
    aliyun_timeout = 180  # 阿里云服务超时时间（Agno 建议 180 秒以上）
    
    if transport == "stdio":
        return MCPTools(
            command=config["command"],
            env=config.get("env", {}),
            include_tools=config.get("include_tools"),
            exclude_tools=config.get("exclude_tools"),
            timeout_seconds=config.get("timeout_seconds", default_timeout)
        )
    elif transport == "streamable-http":
        url = config.get("url", "")
        
        # 阿里云服务的特殊处理
        if "dashscope.aliyuncs.com" in url:
            # 从前端输入的配置中获取阿里云认证信息
            aliyun_api_key = config.get("aliyun_api_key")
            # 如果没有在config中，尝试从env中获取
            if not aliyun_api_key and config.get("env"):
                env_auth = config.get("env", {}).get("Authorization", "")
                if env_auth.startswith("Bearer "):
                    aliyun_api_key = env_auth.replace("Bearer ", "")
                elif config.get("env", {}).get("DASHSCOPE_API_KEY"):
                    aliyun_api_key = config.get("env", {}).get("DASHSCOPE_API_KEY")

            if not aliyun_api_key:
                raise ValueError(
                    "阿里云MCP缺少必需的认证信息。请提供 aliyun_api_key（API Key）"
                )

            # 阿里云服务需要更长的超时时间（Agno 建议 180 秒以上）
            timeout_seconds = max(config.get("timeout_seconds", aliyun_timeout), 180)

            print(f"完整URL: {url}")
            print(f"超时时间: {timeout_seconds}秒")

            # 使用 StreamableHTTPClientParams 传递认证头和超时时间
            # 注意：必须设置 timeout，否则默认30秒会导致超时
            print("使用 StreamableHTTPClientParams 传递认证头和超时")
            from datetime import timedelta
            server_params = StreamableHTTPClientParams(
                url=url,
                headers={
                    "Authorization": f"Bearer {aliyun_api_key}",
                    "Content-Type": "application/json"
                },
                timeout=timedelta(seconds=timeout_seconds)  # ✅ 设置超时，覆盖默认的30秒
            )
            return MCPTools(
                transport="streamable-http",
                server_params=server_params,
                timeout_seconds=timeout_seconds,
                include_tools=config.get("include_tools"),
                exclude_tools=config.get("exclude_tools"),
            )
        
        # 其他HTTP服务的标准处理
        return MCPTools(
            transport="streamable-http",
            url=url,
            env=config.get("env", {}),
            include_tools=config.get("include_tools"),
            exclude_tools=config.get("exclude_tools"),
            timeout_seconds=config.get("timeout_seconds", default_timeout)
        )
    
    raise ValueError(f"不支持的传输方式: {transport}")

