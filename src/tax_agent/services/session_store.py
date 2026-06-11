from datetime import datetime
from uuid import uuid4


class InMemorySessionStore:
    """Development-only store. Replace with old Agno sessions or a new DB table in P2."""

    def __init__(self) -> None:
        self.sessions: dict[str, dict] = {}
        self.messages: dict[str, list[dict]] = {}

    async def create_session(self, user_id: str, name: str) -> dict:
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
        return [session for session in self.sessions.values() if session["user_id"] == user_id]

    async def append_message(self, user_id: str, session_id: str, role: str, content: str) -> None:
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
        session = self.sessions.get(session_id)
        if not session:
            return []
        if session["user_id"] != user_id:
            raise PermissionError("无权访问此会话")
        return self.messages.get(session_id, [])
