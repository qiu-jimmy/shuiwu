"""
Chat 服务 - 负责会话管理和业务逻辑
高内聚：集中处理会话相关的所有业务逻辑
低耦合：通过 Agent 工厂创建 Agent，不直接依赖具体实现
"""
import json
import re
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from agno.models.openai import OpenAIChat
from agno.session.agent import AgentSession

from app.infra.db import create_async_postgres_db
from app.agno.agents.normal_agent import create_normal_agent
from app.agno.agents.search_agent import create_search_agent
from app.agno.agents.rag_agent import create_rag_agent
from app.agno.agents.full_agent import create_full_agent
from app.agno.agents.contract_review_agent import create_contract_review_agent


class ChatService:
    """Chat 服务类 - 负责会话管理和业务逻辑"""

    # 类级别的缓存，所有实例共享
    _session_cache = {}  # 格式: {session_id: (user_id, timestamp)}

    def __init__(self):
        # 使用统一的数据库配置（异步版本）
        # 延迟初始化，避免在模块导入时阻塞
        self._db = None

    @property
    def db(self):
        """延迟加载 AsyncPostgresDb 实例（异步版本）"""
        if self._db is None:
            self._db = create_async_postgres_db(session_table="agent_sessions")
        return self._db

    def create_agent(
        self,
        chat_type: str = "normal",
        model_id: str = "qwen-plus",
        session_id: str = None,
        user_id: str = "default",
        knowledge_base: Optional[str] = None,
        send_media_to_model: bool = True,
        temperature: float = 0.7,
        enable_search: Optional[bool] = None,
        enable_rag: Optional[bool] = None,
    ):
        """
        创建智能体（根据chat_type调用对应的Agent工厂）

        Args:
            chat_type: 对话类型 ("normal", "search", "rag", "full", "contract_review")
            model_id: 模型ID
            session_id: 会话ID
            user_id: 用户ID
            knowledge_base: 知识库名称（仅 rag 类型支持，full 类型已弃用该参数）
            send_media_to_model: 是否将媒体发送给模型
            temperature: 温度参数
            enable_search: 是否启用搜索（仅 full 类型支持，None 表示 AI 自主决策）
            enable_rag: 是否启用智能知识库检索（仅 full 类型支持，None 表示 AI 自主决策）
        """
        if chat_type == "contract_review":
            # 合同审查：仅支持文件上传，不保存会话历史
            return create_contract_review_agent(
                model_id=model_id,
                user_id=user_id,
                send_media_to_model=send_media_to_model,
                temperature=temperature,
            )
        elif chat_type == "full":
            # 全功能对话：根据参数动态启用搜索工具和知识库
            return create_full_agent(
                model_id=model_id,
                session_id=session_id,
                user_id=user_id,
                knowledge_base=knowledge_base,
                send_media_to_model=send_media_to_model,
                temperature=temperature,
                db=self.db,
                enable_search=enable_search,
                enable_rag=enable_rag,
            )
        elif chat_type == "rag":
            # RAG对话：启用知识库，不启用搜索
            return create_rag_agent(
                model_id=model_id,
                session_id=session_id,
                user_id=user_id,
                knowledge_base=knowledge_base,
                send_media_to_model=send_media_to_model,
                temperature=temperature,
                db=self.db,
            )
        elif chat_type == "search":
            # 搜索对话：启用搜索工具，不启用知识库
            return create_search_agent(
                model_id=model_id,
                session_id=session_id,
                user_id=user_id,
                send_media_to_model=send_media_to_model,
                temperature=temperature,
                db=self.db,
            )
        else:
            # 普通对话：不启用搜索和知识库
            return create_normal_agent(
                model_id=model_id,
                session_id=session_id,
                user_id=user_id,
                send_media_to_model=send_media_to_model,
                temperature=temperature,
                db=self.db,
            )

    async def create_session(self, user_id: str, name: Optional[str] = None) -> Dict[str, Any]:
        """创建新会话（异步版本）"""
        session_id = str(uuid.uuid4())
        now = int(time.time())

        # session_name = name or f"会话_{datetime.now().strftime('%m%d_%H%M')}"
        session_name = name or f"新建会话"
        session_data = {
            "name": session_name,
        }

        session = AgentSession(
            session_id=session_id,
            agent_id="chat-agent",
            user_id=user_id,
            session_data=session_data,
            created_at=now,
            updated_at=now,
        )

        created_session = await self.db.upsert_session(session)

        if not created_session:
            raise Exception("会话创建失败")

        return {
            "status": "success",
            "session_id": session_id,
            "name": session.session_data.get("name", "新会话"),
            "created_at": datetime.fromtimestamp(now).isoformat(),
        }

    async def list_sessions(self, user_id: str) -> Dict[str, Any]:
        """
        获取指定用户的所有会话（异步版本）

        改进：
        - 使用 Agno 的 get_sessions() 方法替代手动SQL
        - 异步方法，支持 AsyncPostgresDb
        - 代码更简洁
        - 利用 Agno 的数据库抽象层
        - 自动处理序列化/反序列化
        """
        try:
            # 使用 Agno 的 get_sessions 方法（异步）
            sessions = await self.db.get_sessions(
                session_type="agent",
                user_id=user_id,
                sort_by="updated_at",
                sort_order="desc"
            )

            session_list = []
            for session in sessions:
                try:
                    session_data = session.session_data or {}

                    session_list.append({
                        "id": session.session_id,
                        "name": session_data.get("name", "未命名会话") if isinstance(session_data, dict) else "未命名会话",
                        "created_at": datetime.fromtimestamp(session.created_at).isoformat() if session.created_at else None,
                        "updated_at": datetime.fromtimestamp(session.updated_at).isoformat() if session.updated_at else None,
                    })
                except Exception as e:
                    print(f"处理会话时出错: {e}")
                    continue

            return {
                "status": "success",
                "sessions": session_list,
            }
        except Exception as e:
            import traceback
            error_detail = f"{str(e)}\n{traceback.format_exc()}"
            print(f"list_sessions错误: {error_detail}")
            raise Exception(error_detail)

    async def update_session_name(self, session_id: str, user_id: str, name: str) -> Dict[str, Any]:
        """
        更新会话名称（异步版本）

        改进：
        - 使用 Agno 的 get_session() 和 upsert_session() 替代手动SQL
        - 异步方法，支持 AsyncPostgresDb
        - 代码更简洁
        - 利用 Agno 的数据库抽象层
        - 自动处理序列化/时间戳更新
        """
        try:
            # 使用 Agno 的 get_session 方法获取会话（异步）
            session = await self.db.get_session(session_id=session_id, session_type="agent")

            if not session:
                raise Exception("会话不存在或无权限访问")

            # 验证用户权限
            if session.user_id != user_id:
                raise Exception("无权访问此会话")

            # 更新会话名称
            session_data = session.session_data or {}
            if isinstance(session_data, dict):
                session_data["name"] = name
                session.session_data = session_data

            # 使用 Agno 的 upsert_session 方法更新（异步）
            now = int(time.time())
            session.updated_at = now
            await self.db.upsert_session(session)

            return {
                "status": "success",
                "message": "会话名称更新成功",
                "session_id": session_id,
                "name": name,
            }
        except Exception as e:
            import traceback
            error_detail = f"{str(e)}\n{traceback.format_exc()}"
            print(f"update_session_name错误: {error_detail}")
            raise Exception(error_detail)

    async def delete_session(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """
        删除会话（异步版本）

        改进：
        - 使用 Agno 的 get_session() 和 delete_session() 替代手动SQL
        - 异步方法，支持 AsyncPostgresDb
        - 代码更简洁
        - 利用 Agno 的数据库抽象层
        - 统一会话删除方式
        """
        try:
            # 使用 Agno 的 get_session 方法获取会话（异步）
            session = await self.db.get_session(session_id=session_id, session_type="agent")

            if not session:
                raise Exception("会话不存在或无权限访问")

            # 验证用户权限
            if session.user_id != user_id:
                raise Exception("无权访问此会话")

            # 使用 Agno 的 delete_session 方法删除（异步）
            # 注意：delete_session 不接受 session_type 参数
            await self.db.delete_session(session_id=session_id)

            return {
                "status": "success",
                "message": "会话删除成功",
                "session_id": session_id,
            }
        except Exception as e:
            import traceback
            error_detail = f"{str(e)}\n{traceback.format_exc()}"
            print(f"delete_session错误: {error_detail}")
            raise Exception(error_detail)

    async def delete_all_sessions(self, user_id: str) -> Dict[str, Any]:
        """
        删除用户的所有会话（异步版本）

        Args:
            user_id: 用户ID

        Returns:
            包含删除数量的响应
        """
        try:
            # 获取用户的所有会话（异步）
            sessions = await self.db.get_sessions(
                session_type="agent",
                user_id=user_id
            )

            deleted_count = 0
            failed_sessions = []

            # 逐个删除会话
            for session in sessions:
                try:
                    await self.db.delete_session(session_id=session.session_id)
                    deleted_count += 1
                except Exception as e:
                    failed_sessions.append({
                        "session_id": session.session_id,
                        "error": str(e)
                    })

            return {
                "status": "success",
                "message": f"成功删除 {deleted_count} 个会话",
                "deleted_count": deleted_count,
                "total_count": len(sessions),
                "failed_sessions": failed_sessions if failed_sessions else None
            }
        except Exception as e:
            import traceback
            error_detail = f"{str(e)}\n{traceback.format_exc()}"
            print(f"delete_all_sessions错误: {error_detail}")
            raise Exception(error_detail)

    def _clean_user_message_content(self, content: str) -> str:
        """
        清理用户消息内容，根据标记移除系统自动添加的内容

        支持的标记：
        - "rag:" - RAG对话，移除标记和知识库引用
        - "search:" - 搜索对话，移除标记
        - "quote:" - 划词对话，移除标记和引用内容
        - 文件内容追加段：移除 "以下是上传的文档内容：" 之后的部分

        Args:
            content: 原始消息内容

        Returns:
            清理后的消息内容
        """
        if not content or not isinstance(content, str):
            return content

        # 检查是否有对话类型标记
        if content.startswith("rag:"):
            # RAG对话：移除标记，然后清理知识库引用
            content = content[4:].lstrip()  # 移除 "rag:" 标记
        elif content.startswith("search:"):
            # 搜索对话：移除标记
            content = content[7:].lstrip()  # 移除 "search:" 标记
        elif content.startswith("quote:"):
            # 划词对话：移除标记和引用内容部分
            content = content[6:].lstrip()  # 移除 "quote:" 标记
            # 移除引用内容部分（从 "[引用内容]:" 开始到结尾）
            quote_marker = "[引用内容]:"
            quote_index = content.find(quote_marker)
            if quote_index != -1:
                content = content[:quote_index].rstrip()

        # 移除上传文件自动追加的内容（从 "以下是上传的文档内容：" 开始的部分）
        file_marker = "以下是上传的文档内容："
        marker_index = content.find(file_marker)
        if marker_index != -1:
            content = content[:marker_index].rstrip()

        # 定义需要移除的系统提示标记（支持中英文，按优先级排序）
        system_prompt_markers = [
            "Use the following references from the knowledge base if it helps:",
            "使用以下知识库引用（如果有助于回答）：",
            "以下是知识库中的相关内容：",
            "Use the following references",
            "使用以下引用",
            "<references>",
        ]

        # 查找第一个系统提示标记的位置
        min_index = len(content)
        for marker in system_prompt_markers:
            # 使用不区分大小写的搜索
            content_lower = content.lower()
            marker_lower = marker.lower()
            index = content_lower.find(marker_lower)
            if index != -1 and index < min_index:
                min_index = index

        # 如果找到了系统提示标记，截取之前的内容
        if min_index < len(content):
            cleaned_content = content[:min_index].rstrip()
            # 移除末尾可能的换行符和空白字符
            cleaned_content = cleaned_content.rstrip('\n\r\t ')
            return cleaned_content

        return content

    def _extract_intermediate_results(self, runs: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        从runs JSON中提取中间结果

        Returns:
            Dict[run_id, {
                "rag_files": List[Dict[str, Any]],  # RAG检索到的文件信息列表（包含 file_name, kb_name, source, relevance）
                "search_results": List[Dict[str, str]],  # 搜索结果列表，包含title和url
                "quote_content": str  # 划词内容
            }]
        """
        results = {}

        for run in runs:
            run_id = run.get("run_id", "")
            if not run_id:
                continue

            rag_files = []
            search_results = []
            quote_content = ""

            # 提取RAG文件名称
            if "tools" in run:
                for tool in run["tools"]:
                    tool_name = tool.get("tool_name", "")
                    tool_result = tool.get("result", "")

                    # 支持动态知识库工具和传统知识库工具
                    if tool_name in ["search_knowledge_base", "search_all_knowledge_bases"] and tool_result:
                        try:
                            # 解析JSON格式的结果
                            if isinstance(tool_result, str):
                                # 新格式：提取 ---REFERENCES--- 和 ---END-REFERENCES--- 之间的 JSON
                                import re
                                match = re.search(
                                    r'---REFERENCES---\s*\n(.*?)\n---END-REFERENCES---',
                                    tool_result,
                                    re.DOTALL
                                )
                                if match:
                                    refs_json = match.group(1).strip()
                                    refs = json.loads(refs_json)
                                else:
                                    # 旧格式：直接解析 JSON
                                    refs = json.loads(tool_result)
                            else:
                                refs = tool_result

                            if isinstance(refs, list):
                                seen_files = set()
                                for ref in refs:
                                    if not isinstance(ref, dict):
                                        continue
                                    filename = None
                                    # 新格式：直接取顶层字段
                                    filename = ref.get("filename")
                                    kb_name = ref.get("kb_name", "")
                                    kb_type = ref.get("kb_type", "")
                                    score = ref.get("score", 0)

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
                                    # 旧格式：兜底：name
                                    if not filename:
                                        filename = ref.get("name")

                                    # 使用唯一标识（filename + kb_name）去重
                                    file_key = f"{filename}_{kb_name}"
                                    if filename and file_key not in seen_files:
                                        rag_files.append({
                                            "file_name": filename,  # 使用 file_name（与前端一致）
                                            "kb_name": kb_name,
                                            "source": kb_type or "unknown",
                                            "relevance": score,
                                        })
                                        seen_files.add(file_key)
                        except (json.JSONDecodeError, TypeError):
                            pass

            # 提取搜索结果
            if "tools" in run:
                for tool in run["tools"]:
                    tool_name = tool.get("tool_name", "")
                    tool_result = tool.get("result", "")

                    if tool_name in ["baidu_search", "duckduckgo_search"] and tool_result:
                        # 解析搜索结果文本，提取标题和链接
                        lines = str(tool_result).split("\n")
                        current_title = ""
                        current_url = ""

                        for line in lines:
                            line = line.strip()
                            if not line:
                                continue

                            # 检查是否是标题行（通常以数字开头，后面跟着点或顿号）
                            if line and len(line) > 0 and line[0].isdigit():
                                # 保存上一个结果
                                if current_title:
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

                        # 保存最后一个结果
                        if current_title:
                            search_results.append({
                                "title": current_title,
                                "url": current_url
                            })

            # 提取划词内容
            input_content = run.get("input", {}).get("input_content", "")
            if "[引用内容]:" in input_content:
                quote_index = input_content.find("[引用内容]:")
                if quote_index != -1:
                    quote_content = input_content[quote_index + len("[引用内容]:"):].strip()

            results[run_id] = {
                "rag_files": rag_files,
                "search_results": search_results,
                "quote_content": quote_content
            }

        return results

    async def get_session_messages(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """
        获取会话消息历史（使用Agno内置方法，自动过滤工具调用）

        改进：
        1. 异步方法，支持 AsyncPostgresDb
        2. 使用 Agno 的 get_session() 替代手动SQL验证
        3. 统一使用 Agno 的数据库抽象层
        4. 减少直接的数据库访问
        """
        try:
            # 使用 Agno 的 get_session 方法获取会话（异步）
            session = await self.db.get_session(session_id=session_id, session_type="agent")

            if not session:
                raise Exception("会话不存在或无权限访问")

            # 验证用户权限
            if session.user_id != user_id:
                raise Exception("无权访问此会话")

            # 解析runs JSON以提取中间结果
            runs_data = []
            if session.runs:
                if isinstance(session.runs, str):
                    runs_data = json.loads(session.runs)
                elif isinstance(session.runs, list):
                    # 处理列表中的 RunOutput 对象
                    for run in session.runs:
                        if hasattr(run, 'to_dict'):  # Agno RunOutput 对象使用 to_dict()
                            runs_data.append(run.to_dict())
                        elif hasattr(run, 'model_dump'):  # Pydantic 模型使用 model_dump()
                            runs_data.append(run.model_dump())
                        elif isinstance(run, dict):
                            runs_data.append(run)
                        else:
                            # 尝试转换为字典
                            try:
                                runs_data.append(dict(run))
                            except:
                                pass

            # 提取中间结果，按run_id索引
            intermediate_results = self._extract_intermediate_results(runs_data)

            # ✅ 直接从 session.runs 构建 messages 列表
            # 不需要复杂的匹配逻辑，消息天然属于某个 run
            messages = []

            for run in session.runs:
                run_id = run.run_id

                # 获取当前 run 的中间结果
                run_result = intermediate_results.get(run_id, {})

                # ✅ 检查 messages 是否为 None
                if not run.messages:
                    continue

                # 遍历当前 run 的所有消息
                for msg in run.messages:
                    # 跳过历史消息
                    if msg.from_history:
                        continue

                    # 跳过 system 角色消息
                    if msg.role == "system":
                        continue

                    # 只处理 user 和 assistant 消息
                    if msg.role not in ["user", "assistant"]:
                        continue

                    # 处理时间戳
                    timestamp = datetime.now().isoformat()
                    if hasattr(msg, "created_at") and msg.created_at:
                        if isinstance(msg.created_at, datetime):
                            timestamp = msg.created_at.isoformat()
                        elif isinstance(msg.created_at, (int, float)):
                            timestamp = datetime.fromtimestamp(msg.created_at).isoformat()

                    # 处理内容
                    content = msg.content or ""
                    if msg.role == "user":
                        content = self._clean_user_message_content(content)

                    # 构建消息字典
                    message_dict = {
                        "id": getattr(msg, "id", str(uuid.uuid4())),
                        "role": msg.role,
                        "content": content,
                        "timestamp": timestamp,
                        "rag_files": [],
                        "search_results": [],
                        "quote_content": "",
                        "is_reasoning": False,
                    }

                    # ✅ assistant 消息：添加 thinking 和中间结果
                    if msg.role == "assistant":
                        # 从消息对象获取 reasoning_content（Agno 标准字段）
                        if hasattr(msg, "reasoning_content") and msg.reasoning_content:
                            message_dict["thinking"] = msg.reasoning_content
                        elif hasattr(msg, "thinking") and msg.thinking:
                            message_dict["thinking"] = msg.thinking

                        # 添加中间结果
                        message_dict["rag_files"] = run_result.get("rag_files", [])
                        message_dict["search_results"] = run_result.get("search_results", [])
                        message_dict["quote_content"] = run_result.get("quote_content", "")

                    # 追加消息
                    messages.append(message_dict)

            return {
                "status": "success",
                "messages": messages,
            }
        except Exception as e:
            import traceback
            error_detail = f"{str(e)}\n{traceback.format_exc()}"
            print(f"get_session_messages错误: {error_detail}")
            raise Exception(error_detail)

    async def get_session_messages_simple(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """
        获取会话消息历史（简化版本，用于普通对话）

        与 get_session_messages 的区别：
        - 不进行角色互换
        - 不过滤 assistant 消息
        - 不提取中间结果（rag_files, search_results）
        - 简单的 user/assistant 消息返回

        适用于：普通对话、非 Supervisor-Agent Workflow 的会话
        """
        try:
            # 使用 Agno 的 get_session 方法获取会话（异步）
            session = await self.db.get_session(session_id=session_id, session_type="agent")

            if not session:
                raise Exception("会话不存在或无权限访问")

            # 验证用户权限
            if session.user_id != user_id:
                raise Exception("无权访问此会话")

            # 获取所有消息，只过滤 system 和 tool
            chat_history = session.get_chat_history()

            # 转换为前端需要的格式
            messages = []
            for msg in chat_history:
                # 处理时间戳
                timestamp = datetime.now().isoformat()
                if hasattr(msg, "created_at") and msg.created_at:
                    if isinstance(msg.created_at, datetime):
                        timestamp = msg.created_at.isoformat()
                    elif isinstance(msg.created_at, (int, float)):
                        timestamp = datetime.fromtimestamp(msg.created_at).isoformat()

                # 清理用户消息内容
                content = msg.content
                if msg.role == "user":
                    content = self._clean_user_message_content(content)

                # 构建消息
                message_dict = {
                    "id": getattr(msg, "id", str(uuid.uuid4())),
                    "role": msg.role,
                    "content": content,
                    "timestamp": timestamp,
                }

                messages.append(message_dict)

            return {
                "status": "success",
                "messages": messages,
            }
        except Exception as e:
            import traceback
            error_detail = f"{str(e)}\n{traceback.format_exc()}"
            print(f"get_session_messages_simple错误: {error_detail}")
            raise Exception(error_detail)

    async def validate_session(self, session_id: str, user_id: str) -> tuple[bool, bool, Optional[Any]]:
        """
        验证会话是否存在且属于该用户（带缓存）

        改进：
        - 使用 Agno 的 get_session() 方法替代手动SQL
        - 代码更简洁
        - 利用 Agno 的数据库抽象层
        - 统一会话访问方式
        - 异步方法，支持 AsyncPostgresDb
        - 添加 5 分钟缓存，减少数据库查询
        - 返回是否为首次会话（基于会话是否有对话历史）

        Returns:
            tuple: (是否验证通过, 是否为首次会话, 会话对象)
        """
        import time

        # ✅ 检查缓存（5分钟有效期）
        if session_id in ChatService._session_cache:
            cached_user_id, timestamp = ChatService._session_cache[session_id]
            if time.time() - timestamp < 300:  # 5分钟内有效
                if cached_user_id == user_id:
                    # 从缓存中无法判断是否为首次会话，需要查数据库
                    pass
                else:
                    raise Exception("无权访问此会话")

        try:
            # 使用 Agno 的 get_session 方法（异步）
            session = await self.db.get_session(session_id=session_id, session_type="agent")

            is_first_session = False

            if not session:
                # 会话不存在
                raise Exception("会话不存在")
            elif session.user_id != user_id:
                raise Exception("无权访问此会话")

            # 判断是否为首次会话：会话名称为"新建会话"且没有对话历史
            session_data = session.session_data or {}
            current_name = session_data.get("name", "") if isinstance(session_data, dict) else ""

            # 检查会话是否有运行历史
            has_runs = session.runs is not None and len(session.runs) > 0

            # 首次会话条件：名称为默认值且无对话历史
            if (current_name in ["新建会话", "新会话", ""] or not current_name) and not has_runs:
                is_first_session = True
                print(f"[ChatService] 检测到首次会话: session_id={session_id}, name={current_name}, has_runs={has_runs}")
            else:
                print(f"[ChatService] 非首次会话: session_id={session_id}, name={current_name}, has_runs={has_runs}")

            # ✅ 缓存验证结果
            ChatService._session_cache[session_id] = (user_id, time.time())

            return (True, is_first_session, session)
        except Exception as e:
            raise Exception(f"会话验证失败: {str(e)}")

    def get_knowledge_bases(self, user_id: str) -> Dict[str, Any]:
        """获取用户的知识库列表（委托给 RAG 服务）"""
        try:
            from app.services.knowledge.knowledge_service import knowledge_service
            data = knowledge_service.list_knowledge_bases(user_id)
            return {
                "status": "success",
                "knowledge_bases": data,
            }
        except Exception as e:
            raise Exception(f"获取知识库列表失败: {str(e)}")

    async def handle_chat_stream(
        self,
        request,
        enable_search: bool = False,
        chat_type: str = "normal",
    ):
        """
        处理聊天请求的业务逻辑

        Args:
            request: ChatMessageRequest 对象
            enable_search: 是否启用搜索（已弃用，请使用 request.enable_search）
            chat_type: 聊天类型 (normal, search, rag, full)

        Returns:
            异步生成器，产生 SSE 事件
        """
        from app.utils.file_processing import FilePreprocessingService, process_base64_images
        from app.agno.runners.chat_runner import ChatRunner

        try:
            # 1. 验证会话，并检查是否为首次会话
            _, is_first_session, _ = await self.validate_session(request.session_id, request.user_id)

            # 2. 如果是首次会话，使用用户消息更新会话名称
            if is_first_session:
                # 清理用户消息内容，移除系统标记，提取纯文本
                clean_message = self._clean_user_message_content(request.message)

                # 限制会话名称长度（最多30个字符）
                session_name = clean_message[:30] if clean_message else "新会话"

                print(f"[ChatService] 首次会话，更新会话名称: {session_name}")

                # 异步更新会话名称
                try:
                    await self.update_session_name(request.session_id, request.user_id, session_name)
                except Exception as e:
                    # 更新失败不影响对话继续进行
                    print(f"[ChatService] 更新会话名称失败（非致命错误）: {e}")

            # 3. 处理多模态输入
            images = process_base64_images(request.images) if request.images else None

            # 4. 异步处理文件（避免阻塞事件循环）
            file_text_content = None
            if request.files:
                file_text_content = await FilePreprocessingService.preprocess_files_async(request.files)

            # 4. 构建消息内容
            message_content = request.message

            # 检测是否有划词引用
            has_quote = "[引用内容]:" in message_content

            # 5. 确定 enable_search 和 enable_rag 的值
            # FullFeatureChatRequest 支持 enable_search 和 enable_rag 参数
            actual_enable_search = enable_search
            actual_enable_rag = False

            if hasattr(request, 'enable_search'):
                actual_enable_search = request.enable_search
            if hasattr(request, 'enable_rag'):
                actual_enable_rag = request.enable_rag

            # 6. 根据对话类型和参数添加标记
            if actual_enable_rag and request.knowledge_base:
                message_content = f"rag:{message_content}"
            elif has_quote:
                message_content = f"quote:{message_content}"
            elif actual_enable_search:
                message_content = f"search:{message_content}"

            # 7. 添加文件内容
            if file_text_content:
                message_content = f"{request.message}\n\n以下是上传的文档内容：\n\n{file_text_content}"

            # 8. 创建智能体并执行
            # 对于 full 类型，根据参数动态配置工具
            if chat_type == "full":
                # full 类型：Agent 自主决策是否使用知识库检索工具，无需传递 knowledge_base
                agent = self.create_agent(
                    chat_type=chat_type,
                    model_id=request.model_id,
                    session_id=request.session_id,
                    user_id=request.user_id,
                    knowledge_base=None,  # Agent 会通过智能工具自动选择知识库
                    send_media_to_model=True,
                    enable_search=actual_enable_search,
                    enable_rag=actual_enable_rag,
                )
            else:
                # 其他类型保持原有逻辑
                agent = self.create_agent(
                    chat_type=chat_type,
                    model_id=request.model_id,
                    session_id=request.session_id,
                    user_id=request.user_id,
                    knowledge_base=request.knowledge_base if chat_type in ["rag"] else None,
                    send_media_to_model=True
                )

            runner = ChatRunner(agent)

            async def generate_response():
                async for event in runner.run_chat(message_content, images):
                    yield ChatRunner.format_sse_event(event)

            return generate_response()

        except Exception as e:
            import traceback
            error_detail = f"{str(e)}\n{traceback.format_exc()}"
            print(f"handle_chat_stream错误: {error_detail}")

            raise Exception(error_detail)

    async def handle_contract_review(
        self,
        request,
    ):
        """
        处理合同审查请求（无会话模式）

        Args:
            request: ContractReviewRequest 对象

        Returns:
            异步生成器，产生 SSE 事件
        """
        import time
        from app.utils.file_processing import FilePreprocessingService, process_base64_images
        from app.agno.runners.chat_runner import ChatRunner

        request_id = f"{request.user_id}_{int(time.time() * 1000)}"
        # print(f"[{request_id}] 合同审查请求开始")

        try:
            # 1. 处理多模态输入（虽然合同审查主要是文件，但保留图片支持）
            images = process_base64_images(request.images) if hasattr(request, 'images') and request.images else None
            # print(f"[{request_id}] 图片处理完成")

            # 2. 异步处理文件（合同审查必须有文件）
            file_text_content = None
            if not request.files:
                raise Exception("合同审查需要上传合同文件，请在files参数中提供")

            file_text_content = await FilePreprocessingService.preprocess_files_async(request.files)

            # 3. 构建消息内容
            message_content = request.message or "请审查这份合同，指出其中的风险条款"
            message_content = f"{message_content}\n\n以下是上传的合同内容：\n\n{file_text_content}"

            # 4. 创建合同审查 Agent（完全不使用 session）
            # 获取 temperature 参数
            temperature = 0.6  # 默认值
            if hasattr(request, 'temperature') and request.temperature is not None:
                temperature = request.temperature

            agent = self.create_agent(
                chat_type="contract_review",
                model_id=request.model_id,
                session_id=None,  # 明确不使用会话
                user_id=request.user_id,
                send_media_to_model=True,
                temperature=temperature,
            )

            runner = ChatRunner(agent)

            async def generate_response():
                try:
                    async for event in runner.run_chat(message_content, images):
                        yield ChatRunner.format_sse_event(event)
                except Exception as e:
                    yield ChatRunner.format_sse_event({
                        "type": "error",
                        "message": f"处理失败: {str(e)}"
                    })

            return generate_response()

        except Exception as e:
            import traceback
            error_detail = f"{str(e)}\n{traceback.format_exc()}"
            print(f"[{request_id}] handle_contract_review错误: {error_detail}")

            # 先捕获异常信息，避免嵌套函数作用域问题
            error_msg = str(e)

            # 返回错误流
            async def error_stream():
                yield ChatRunner.format_sse_event({
                    "type": "error",
                    "message": error_msg
                })
            return error_stream()

    async def handle_supervisor_chat_stream(self, request):
        """
        处理 Supervisor-Agent 模式的聊天请求

        工作流程：
        1. Supervisor Agent 分析用户输入
        2. 判断是否需要专业 Agent（简单问题直接回答）
        3. 如需专业 Agent，输出结构化决策（工具配置）
        4. 根据决策调用专业 Agent

        Args:
            request: FullFeatureChatRequest 对象

        Returns:
            异步生成器，产生 SSE 事件
        """
        from app.utils.file_processing import FilePreprocessingService, process_base64_images
        from app.agno.workflows.supervisor_agent_workflow import (
            create_supervisor_workflow,
            execute_supervisor_workflow_stream,
        )
        from app.agno.runners.chat_runner import ChatRunner

        try:
            # 1. 验证会话
            _, is_first_session, _ = await self.validate_session(request.session_id, request.user_id)

            # 2. 首次会话处理
            if is_first_session:
                clean_message = self._clean_user_message_content(request.message)
                session_name = clean_message[:30] if clean_message else "Supervisor会话"
                try:
                    await self.update_session_name(request.session_id, request.user_id, session_name)
                except Exception as e:
                    print(f"[ChatService] 更新会话名称失败: {e}")

            # 3. 处理多模态输入
            images = process_base64_images(request.images) if request.images else None
            file_text_content = None
            has_files = False

            if request.files:
                has_files = True
                file_text_content = await FilePreprocessingService.preprocess_files_async(request.files)

            # 4. 构建消息内容（分离用户原始消息和文件内容）
            # user_message: 用户原始消息（将保存到数据库）
            user_message = request.message

            # query_for_agent: 传递给 Agent 的完整查询（包含文件内容，用于处理）
            query_for_agent = request.message
            if has_files and file_text_content:
                query_for_agent = f"{request.message}\n\n[用户上传了 {len(request.files)} 个文件，文件内容如下]\n\n{file_text_content}"
            elif file_text_content:
                query_for_agent = f"{request.message}\n\n以下是上传的文档内容：\n\n{file_text_content}"

            # 5. 创建 Supervisor Workflow
            workflow = create_supervisor_workflow(
                model_id=request.model_id,
                session_id=request.session_id,
                user_id=request.user_id,
                send_media_to_model=True,
                db=self.db,  # 传递数据库实例，用于保存会话历史
                enable_search=request.enable_search,  # ✅ 传递全局搜索开关
                enable_rag=request.enable_rag,  # ✅ 传递全局 RAG 开关
            )

            # 6. 定义流式响应生成器
            async def response_stream():
                try:
                    async for event in execute_supervisor_workflow_stream(
                        workflow=workflow,
                        user_message=user_message,  # ✅ 用户原始消息（保存到数据库）
                        query_for_agent=query_for_agent,  # ✅ 完整查询（包含文件内容，用于 Agent 处理）
                        user_id=request.user_id,
                        session_id=request.session_id,  # ✅ 传递 session_id
                        images=images,
                        db=self.db,  # ✅ 传递 db 用于手动保存专家回答
                    ):
                        yield ChatRunner.format_sse_event(event)
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    yield ChatRunner.format_sse_event({
                        "type": "error",
                        "message": str(e)
                    })

            return response_stream()

        except Exception as e:
            print(f"[ChatService] Supervisor chat error: {e}")
            import traceback
            traceback.print_exc()

            # ✅ 立即捕获错误信息，避免闭包变量作用域问题
            error_msg = str(e)
            error_details = traceback.format_exc()

            async def error_stream():
                yield ChatRunner.format_sse_event({
                    "type": "error",
                    "message": error_msg,
                    "details": error_details
                })

            return error_stream()


# 全局服务实例
chat_service = ChatService()
