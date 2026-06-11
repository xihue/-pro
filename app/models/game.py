"""游戏模型 — 基于 sqlite3"""
import os
from datetime import datetime
from flask import current_app
from app.database import query_one, query_all, execute, commit


def _parse_dt(s):
    """把 sqlite 时间字符串转成 datetime 对象"""
    if s is None:
        return None
    if isinstance(s, datetime):
        return s
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return s


class Game:
    def __init__(self, row_dict):
        self._data = dict(row_dict) if row_dict else {}

    @property
    def id(self): return self._data["id"]

    @property
    def user_id(self): return self._data["user_id"]

    @property
    def title(self): return self._data["title"]

    @property
    def description(self): return self._data.get("description", "")

    @property
    def filename(self): return self._data["filename"]

    @property
    def version(self): return self._data.get("version", 1)

    @property
    def status(self): return self._data.get("status", "completed")

    @property
    def created_at(self):
        raw = self._data.get("created_at")
        return _parse_dt(raw) if raw else None

    @property
    def play_path(self):
        return f"/game/games/{self.filename}"

    def to_dict(self):
        # 将 datetime 转为字符串，避免 json.dumps 序列化错误
        cat = self.created_at
        if cat and hasattr(cat, 'strftime'):
            cat = cat.strftime('%Y-%m-%d %H:%M:%S')
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "play_path": self.play_path,
            "version": self.version,
            "status": self.status,
            "created_at": cat,
        }

    # ── 静态方法 ──────────────────────────────

    @staticmethod
    def get(game_id):
        row = query_one("SELECT * FROM game WHERE id = ?", (game_id,))
        return Game(row) if row else None

    @staticmethod
    def list_by_user(user_id, limit=None, offset=None):
        sql = "SELECT * FROM game WHERE user_id = ? ORDER BY created_at DESC"
        params = [user_id]
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        if offset is not None:
            sql += " OFFSET ?"
            params.append(offset)
        return [Game(r) for r in query_all(sql, tuple(params))]

    @staticmethod
    def count_by_user(user_id):
        row = query_one(
            "SELECT COUNT(*) as cnt FROM game WHERE user_id = ?", (user_id,)
        )
        return row["cnt"] if row else 0

    @staticmethod
    def create(user_id, title, description, filename, version=1, status="completed"):
        execute(
            "INSERT INTO game (user_id, title, description, filename, version, status) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, title, description, filename, version, status),
        )
        commit()
        row = query_one("SELECT * FROM game WHERE id = last_insert_rowid()")
        return Game(row) if row else None

    @staticmethod
    def update_status(game_id, status):
        execute("UPDATE game SET status = ? WHERE id = ?", (status, game_id))
        commit()

    @staticmethod
    def delete(game_id):
        execute("DELETE FROM game WHERE id = ?", (game_id,))
        commit()

    def __repr__(self):
        return f"<Game {self.title} v{self.version}>"
