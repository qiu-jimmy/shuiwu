"""
会话记忆存储服务 (Session Store)
=================================
处理多轮对话期间的记忆存取，负责按照用户会话和对话的轮次进行历史消息聚合。
为 LLM 的多轮上下文问答提供了必要的基石支持。
"""

from datetime import datetime
from uuid import uuid4


class InMemorySessionStore:
    """
    开发测试专用的内存级会话存储库。
    应用重启后数据丢失。未来可重构替换为对 PostgreSQL 或 Redis 的存储集成。
    """

    def __init__(self) -> None:
        """初始化一个用于缓存会话和其对应信息的内部字典。"""
        self.sessions: dict[str, dict] = {}
        self.messages: dict[str, list[dict]] = {}

    async def create_session(self, user_id: str, name: str) -> dict:
        """
        建立一个新的聊天上下文会话窗口。
        
        :param user_id: 用户唯一标识符。
        :param name: 显示给用户的前端侧边栏标题（如“新建会话”）。
        :return: 创建好并附带自动生成 UUID 的会话字典元数据。
        """
        session_id = str(uuid4())
        session = {
            "session_id": session_id,
            "user_id": user_id,
            "name": name,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        self.sessions[session_id] = session
        self.messages[session_id] = []
        return session

    async def list_sessions(self, user_id: str) -> list[dict]:
        """
        列举指定用户所创建出的所有历史会话信息（供前端历史侧边栏使用）。
        """
        return [session for session in self.sessions.values() if session["user_id"] == user_id]

    async def append_message(self, user_id: str, session_id: str, role: str, content: str) -> None:
        """
        插入一条新的发言记录（无论是用户还是大模型产生的）。
        
        :param user_id: 该会话归属用户的标识。
        :param session_id: 目标会话窗口标识。
        :param role: 发言者的角色（应为 'user' 或 'assistant'）。
        :param content: 发言的完整文本内容。
        """
        # 若指定会话未被初始化，系统自动为其兜底创建一个。
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "session_id": session_id,
                "user_id": user_id,
                "name": content[:30] or "新会话",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            self.messages[session_id] = []
            
        self.messages.setdefault(session_id, []).append(
            {
                "id": str(uuid4()),
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
            }
        )

    async def get_messages(self, user_id: str, session_id: str) -> list[dict]:
        """
        按时间线拉取指定会话的所有历史发言列表，同时进行越权读取的安全控制。
        """
        session = self.sessions.get(session_id)
        if not session:
            return []
        if session["user_id"] != user_id:
            raise PermissionError("无权访问此会话")
        return self.messages.get(session_id, [])
