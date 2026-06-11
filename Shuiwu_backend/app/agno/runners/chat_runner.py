"""
Chat Runner - 负责执行聊天流程
高内聚：集中处理 Agent 执行的所有逻辑
低耦合：通过 Agent 工厂获取 Agent，不直接依赖 Agent 创建逻辑
"""
import json
import re
from typing import AsyncGenerator, Dict, List, Optional, Any

from agno.agent import Agent, RunEvent
from agno.media import Image


class ChatRunner:
    """聊天执行器 - 负责执行 Agent 并处理流式响应"""

    def __init__(self, agent: Agent):
        """
        初始化 Runner

        Args:
            agent: Agent 实例（由 Agent 工厂创建）
        """
        self.agent = agent

    async def run_chat(
        self,
        message: str,
        images: Optional[List[Image]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        执行聊天并返回流式响应

        Args:
            message: 用户消息
            images: 图片列表（可选）

        Yields:
            Dict[str, Any]: 流式响应事件
                - type: 事件类型 (content, completed, error)
                - content: 内容 (content 类型)
                - message: 错误消息 (error 类型)
        """
        try:
            response_stream = self.agent.arun(
                input=message,
                images=images,
                stream=True,
                stream_events=True,
            )

            async for event in response_stream:
                # 1. 模型正常内容流
                if hasattr(event, "event") and event.event == RunEvent.run_content:
                    if hasattr(event, "content") and isinstance(event.content, str):
                        yield {
                            "type": "content",
                            "content": event.content,
                        }
                    continue

                # 2. 工具调用事件（不再处理，数据自动保存到 Agno runs）
                #    工具调用结果会自动保存到 Agno 的 runs 表中
                #    前端通过 chat_service._extract_intermediate_results() 提取

                # 3. 对话完成事件
                if hasattr(event, "event") and event.event == RunEvent.run_completed:
                    # ✅ 不再单独发送 rag_result 和 search_result 事件
                    # 这些数据已经通过工具调用自动保存到 Agno 的 runs 表中
                    # 前端会从 runs 中提取这些数据（通过 chat_service._extract_intermediate_results）

                    # 仅发送完成事件
                    yield {
                        "type": "completed",
                    }

        except Exception as e:
            yield {
                "type": "error",
                "message": str(e)
            }

    @staticmethod
    def format_sse_event(event: Dict[str, Any]) -> str:
        """
        将事件格式化为 Server-Sent Events 格式

        Args:
            event: 事件字典

        Returns:
            str: SSE 格式的字符串
        """
        return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    @staticmethod
    def _parse_search_results(tool_output: str) -> List[Dict[str, str]]:
        """
        解析搜索工具输出，转换为结构化格式

        与 chat_service.py 中的解析逻辑保持一致

        Args:
            tool_output: 搜索工具返回的原始文本

        Returns:
            List[Dict[str, str]]: 结构化搜索结果列表 [{"title": "...", "url": "..."}]
        """
        search_results = []
        lines = tool_output.split("\n")
        current_title = ""
        current_url = ""

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检查是否是标题行（通常以数字开头，后面跟着点或顿号）
            if line and len(line) > 0 and line[0].isdigit():
                # 保存上一个结果（仅当标题有效时）
                if current_title and len(current_title) > 1:  # 过滤掉单字符标题
                    search_results.append({
                        "title": current_title,
                        "url": current_url
                    })

                # 提取新标题（移除数字前缀）
                # 支持格式：1. 标题 或 1、标题
                if "." in line:
                    parts = line.split(".", 1)
                    current_title = parts[1].strip() if len(parts) > 1 else line
                elif "、" in line:
                    parts = line.split("、", 1)
                    current_title = parts[1].strip() if len(parts) > 1 else line
                else:
                    # 如果没有分隔符，尝试移除开头的数字和空格
                    current_title = re.sub(r'^\d+\s*', '', line).strip()
                current_url = ""

            # 检查是否是链接行
            elif "链接:" in line or "link:" in line.lower() or "href:" in line.lower():
                url_part = line.split(":", 1)
                if len(url_part) > 1:
                    current_url = url_part[1].strip()

        # 保存最后一个结果（仅当标题有效时）
        if current_title and len(current_title) > 1:  # 过滤掉单字符标题
            search_results.append({
                "title": current_title,
                "url": current_url
            })

        # 额外过滤：移除标题过短或包含异常字符的结果
        filtered_results = []
        for result in search_results:
            title = result.get("title", "")
            # 过滤条件：标题长度>=2，且不是纯数字或纯特殊字符
            if len(title) >= 2 and not title.isspace():
                # 检查是否包含至少一个中文字符或英文字母
                has_valid_char = any(
                    '\u4e00' <= char <= '\u9fff' or  # 中文
                    'a' <= char.lower() <= 'z'  # 英文
                    for char in title
                )
                if has_valid_char:
                    filtered_results.append(result)

        return filtered_results

    @staticmethod
    def _parse_rag_files(tool_output: Any) -> List[str]:
        """
        解析 RAG 知识库搜索结果，提取文件名

        支持两种格式：
        1. 旧格式：纯 JSON 数组
        2. 新格式：文本 + ---REFERENCES--- 标记的 JSON 数据

        Args:
            tool_output: 知识库搜索工具返回的结果（可能是字符串或已解析的对象）

        Returns:
            List[str]: 文件信息字典列表（包含 filename, kb_name, kb_type, score）
        """
        rag_files = []
        seen_files = set()

        try:
            # 如果是字符串，尝试提取 ---REFERENCES--- 标记的内容
            if isinstance(tool_output, str):
                # 新格式：提取 ---REFERENCES--- 和 ---END-REFERENCES--- 之间的 JSON
                import re
                match = re.search(
                    r'---REFERENCES---\s*\n(.*?)\n---END-REFERENCES---',
                    tool_output,
                    re.DOTALL
                )
                if match:
                    refs_json = match.group(1).strip()
                    refs = json.loads(refs_json)
                else:
                    # 旧格式：直接解析 JSON
                    refs = json.loads(tool_output)
            else:
                refs = tool_output

            if isinstance(refs, list):
                for ref in refs:
                    if not isinstance(ref, dict):
                        continue

                    filename = None

                    # 新格式：直接从 filename 字段获取
                    filename = ref.get("filename")

                    # 旧格式：meta_data.filename
                    if not filename:
                        meta_data = ref.get("meta_data", {})
                        if isinstance(meta_data, dict):
                            filename = meta_data.get("filename")

                    # 旧格式：filters.filename（顶层或嵌套）
                    if not filename:
                        filters = ref.get("filters", {})
                        if isinstance(filters, dict):
                            filename = filters.get("filename")
                        elif isinstance(meta_data, dict):
                            nested_filters = meta_data.get("filters", {})
                            if isinstance(nested_filters, dict):
                                filename = nested_filters.get("filename")

                    # 旧格式：兜底取 name
                    if not filename:
                        filename = ref.get("name")

                    # 使用唯一标识（filename + kb_name）去重
                    file_key = f"{filename}_{ref.get('kb_name', '')}"
                    if filename and file_key not in seen_files:
                        rag_files.append({
                            "file_name": filename,  # 使用 file_name（与日志输出一致）
                            "kb_name": ref.get("kb_name", ""),
                            "source": ref.get("kb_type", "unknown"),
                            "relevance": ref.get("score", 0),
                        })
                        seen_files.add(file_key)

        except (json.JSONDecodeError, TypeError, AttributeError) as e:
            # 解析失败，返回空列表
            pass

        return rag_files

    @staticmethod
    def _extract_filenames_from_references(references) -> List[str]:
        """
        从 Agno 的 references 对象中提取文件名

        Args:
            references: Agno RunResponse 的 references 属性
                       通常是 MessageReferences 对象列表，包含内层的 references 字典列表

        Returns:
            List[str]: 文件名列表
        """
        filenames = []
        seen_files = set()

        try:
            # references 可能是 MessageReferences 对象列表
            if hasattr(references, '__iter__') and not isinstance(references, (str, dict)):
                for ref in references:
                    # 1. 检查 meta_data 属性
                    if hasattr(ref, 'meta_data'):
                        meta_data = ref.meta_data
                        if isinstance(meta_data, dict):
                            filename = meta_data.get('filename')
                            if filename and filename not in seen_files:
                                filenames.append(filename)
                                seen_files.add(filename)

                    # 2. 检查 data 属性
                    elif hasattr(ref, 'data'):
                        data = ref.data
                        if isinstance(data, dict):
                            filename = data.get('filename')
                            if filename and filename not in seen_files:
                                filenames.append(filename)
                                seen_files.add(filename)

                    # 3. 检查 references 属性(内层字典列表，这是实际结构!)
                    if hasattr(ref, 'references'):
                        inner_refs = ref.references
                        if isinstance(inner_refs, list):
                            for inner_ref in inner_refs:
                                if isinstance(inner_ref, dict):
                                    # 检查 meta_data.filename
                                    if 'meta_data' in inner_ref:
                                        meta_data = inner_ref['meta_data']
                                        if isinstance(meta_data, dict):
                                            filename = meta_data.get('filename')
                                            if filename and filename not in seen_files:
                                                filenames.append(filename)
                                                seen_files.add(filename)
                                    # 检查 filters.filename
                                    elif 'filters' in inner_ref:
                                        filters = inner_ref['filters']
                                        if isinstance(filters, dict):
                                            filename = filters.get('filename')
                                            if filename and filename not in seen_files:
                                                filenames.append(filename)
                                                seen_files.add(filename)
                                    # 兜底：直接检查 filename
                                    elif 'filename' in inner_ref:
                                        filename = inner_ref['filename']
                                        if filename and filename not in seen_files:
                                            filenames.append(filename)
                                            seen_files.add(filename)

            # 也可能是字典格式
            elif isinstance(references, dict):
                for key, value in references.items():
                    if isinstance(value, dict):
                        filename = value.get('filename')
                        if filename and filename not in seen_files:
                            filenames.append(filename)
                            seen_files.add(filename)

        except Exception as e:
            print(f"[ChatRunner] 提取 references 文件名时出错: {e}")

        return filenames

    @staticmethod
    def _extract_filenames_from_citations(citations) -> List[str]:
        """
        从 Agno 的 citations 对象中提取文件名

        Args:
            citations: Agno RunResponse 的 citations 属性

        Returns:
            List[str]: 文件名列表
        """
        filenames = []
        seen_files = set()

        try:
            # citations 可能是 Citation 对象
            if hasattr(citations, 'raw'):
                raw = citations.raw
                if isinstance(raw, dict):
                    # 检查 grounding_metadata
                    grounding_metadata = raw.get('grounding_metadata', {})
                    grounding_chunks = grounding_metadata.get('grounding_chunks', [])

                    for chunk in grounding_chunks:
                        if isinstance(chunk, dict):
                            retrieved_context = chunk.get('retrieved_context', {})
                            if isinstance(retrieved_context, dict):
                                filename = retrieved_context.get('filename')
                                if filename and filename not in seen_files:
                                    filenames.append(filename)
                                    seen_files.add(filename)

            # 也可能是列表格式
            elif hasattr(citations, '__iter__') and not isinstance(citations, (str, dict)):
                for citation in citations:
                    if hasattr(citation, 'meta_data'):
                        meta_data = citation.meta_data
                        if isinstance(meta_data, dict):
                            filename = meta_data.get('filename')
                            if filename and filename not in seen_files:
                                filenames.append(filename)
                                seen_files.add(filename)

        except Exception as e:
            print(f"[ChatRunner] 提取 citations 文件名时出错: {e}")

        return filenames
