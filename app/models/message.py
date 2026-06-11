"""消息模型 — 基于 sqlite3"""
from app.database import query_one, query_all, execute, commit


class Message:
    def __init__(self, row_dict):
        self._data = row_dict

    @property
    def id(self): return self._data["id"]

    @property
    def conversation_id(self): return self._data["conversation_id"]

    @property
    def role(self): return self._data["role"]

    @property
    def content(self): return self._data["content"]

    @property
    def created_at(self): return self._data.get("created_at")

    def to_dict(self):
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at,
        }

    def to_openai_format(self):
        return {"role": self.role, "content": self.content}

    # ── 静态方法 ──────────────────────────────

    @staticmethod
    def get(msg_id):
        row = query_one("SELECT * FROM message WHERE id = ?", (msg_id,))
        return Message(row) if row else None

    @staticmethod
    def list_by_conversation(conv_id):
        rows = query_all(
            "SELECT * FROM message WHERE conversation_id = ? ORDER BY created_at",
            (conv_id,),
        )
        return [Message(r) for r in rows]

    @staticmethod
    def create(conversation_id, role, content):
        execute(
            "INSERT INTO message (conversation_id, role, content) VALUES (?, ?, ?)",
            (conversation_id, role, content),
        )
        commit()

    @staticmethod
    def delete_by_conversation(conv_id):
        execute("DELETE FROM message WHERE conversation_id = ?", (conv_id,))
        commit()

    def __repr__(self):
        return f"<Message {self.id} [{self.role}]>"
