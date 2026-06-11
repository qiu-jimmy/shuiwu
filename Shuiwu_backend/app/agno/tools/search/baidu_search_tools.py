"""
百度搜索工具
单独封装，便于复用和维护。
"""
from typing import Any, Optional


def create_baidu_search_tool() -> Optional[Any]:
    """
    创建百度搜索工具。

    Returns:
        单个百度搜索 tool 对象；如果依赖缺失则返回 None。
    """
    try:
        from agno.tools import tool
        from baidusearch.baidusearch import search as baidu_search_func

        @tool()
        def baidu_search(query: str) -> str:
            """使用百度搜索引擎查询信息，特别适合中文内容和国内信息。"""
            try:
                # 调用百度搜索，返回结果列表
                results = baidu_search_func(query, num_results=5)

                if not results:
                    return "未找到相关搜索结果"

                # 格式化搜索结果，提取标题、摘要和链接
                formatted_results = []
                for i, result in enumerate(results, 1):
                    if isinstance(result, dict):
                        title = result.get("title", "无标题")
                        url = result.get("url", result.get("link", ""))
                        abstract = result.get(
                            "abstract",
                            result.get("snippet", result.get("des", "")),
                        )

                        # 清理摘要文本，移除过多的换行和空白
                        if abstract:
                            abstract = " ".join(abstract.split()[:50])  # 限制摘要长度
                            if len(abstract) > 200:
                                abstract = abstract[:200] + "..."

                        result_text = f"{i}. {title}"
                        if abstract:
                            result_text += f"\n   摘要: {abstract}"
                        if url:
                            result_text += f"\n   链接: {url}"

                        formatted_results.append(result_text)
                    elif isinstance(result, str):
                        formatted_results.append(f"{i}. {result}")
                    else:
                        formatted_results.append(f"{i}. {str(result)}")

                return "\n\n".join(formatted_results)
            except Exception as e:
                import traceback

                error_detail = f"{str(e)}\n{traceback.format_exc()}"
                print(f"百度搜索错误: {error_detail}")
                return f"百度搜索失败: {str(e)}"

        print("百度搜索工具已启用")
        return baidu_search
    except ImportError:
        print("baidusearch包未安装，跳过百度搜索")
    except Exception as e:
        print(f"初始化百度搜索工具失败: {e}")

    return None


