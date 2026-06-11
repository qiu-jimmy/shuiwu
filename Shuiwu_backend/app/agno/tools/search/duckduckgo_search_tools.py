"""
DuckDuckGo 搜索工具
单独封装，便于复用和维护。
"""
from typing import Any, List


def create_duckduckgo_tools() -> List[Any]:
    """
    创建 DuckDuckGo 相关工具列表。

    Returns:
        List[Any]: DuckDuckGo 工具列表（可能为空）。
    """
    tools: List[Any] = []

    try:
        from agno.tools.duckduckgo import DuckDuckGoTools

        # DuckDuckGo搜索：适合英文内容，使用 yandex 后端可能更稳定
        duckduckgo_tools = DuckDuckGoTools(
            backend="yandex",  # 国内可能更稳定
            enable_news=True,
        )
        tools.append(duckduckgo_tools)
        print("DuckDuckGo搜索工具已启用")
    except ImportError:
        print("DuckDuckGo工具未安装，跳过")
    except Exception as e:
        print(f"初始化DuckDuckGo工具失败: {e}")

    return tools


