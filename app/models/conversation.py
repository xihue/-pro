"""对话模型 — 基于 sqlite3"""
from app.database import query_one, query_all, execute, commit


class Conversation:
    def __init__(self, row_dict):
        self._data = row_dict

    @property
    def id(self): return self._data["id"]

    @property
    def user_id(self): return self._data["user_id"]

    @property
    def title(self): return self._data.get("title", "新对话")

    @property
    def created_at(self): return self._data.get("created_at")

    def message_count(self):
        row = query_one(
            "SELECT COUNT(*) as cnt FROM message WHERE conversation_id = ?",
            (self.id,),
        )
        return row["cnt"] if row else 0

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title or f"对话 {self.id}",
            "message_count": self.message_count(),
            "created_at": self.created_at,
        }

    # ── 静态方法 ──────────────────────────────

    @staticmethod
    def get(conv_id):
        row = query_one("SELECT * FROM conversation WHERE id = ?", (conv_id,))
        return Conversation(row) if row else None

    @staticmethod
    def list_by_user(user_id):
        rows = query_all(
            "SELECT * FROM conversation WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        return [Conversation(r) for r in rows]

    @staticmethod
    def get_latest(user_id):
        row = query_one(
            "SELECT * FROM conversation WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (user_id,),
        )
        return Conversation(row) if row else None

    @staticmethod
    def create(user_id, title="新对话"):
        execute(
            "INSERT INTO conversation (user_id, title) VALUES (?, ?)",
            (user_id, title),
        )
        commit()
        return Conversation.get_latest(user_id)

    @staticmethod
    def update_title(conv_id, title):
        execute("UPDATE conversation SET title = ? WHERE id = ?", (title, conv_id))
        commit()

    @staticmethod
    def delete(conv_id):
        execute("DELETE FROM message WHERE conversation_id = ?", (conv_id,))
        execute("DELETE FROM conversation WHERE id = ?", (conv_id,))
        commit()

    def __repr__(self):
        return f"<Conversation {self.id}: {self.title}>"
