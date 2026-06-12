"""游戏模型 — 基于 sqlite3"""
import os
import secrets
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
    def parent_id(self): return self._data.get("parent_id")

    @property
    def share_id(self): return self._data.get("share_id")

    @property
    def share_link(self):
        """完整分享链接"""
        sid = self.share_id
        if not sid:
            return None
        return f"/s/{sid}"

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
            "parent_id": self.parent_id,
            "share_link": self.share_link,
            "share_id": self.share_id,
            "status": self.status,
            "created_at": cat,
        }

    # ── 静态方法 ──────────────────────────────

    @staticmethod
    def get(game_id):
        row = query_one("SELECT * FROM game WHERE id = ?", (game_id,))
        return Game(row) if row else None

    @staticmethod
    def get_by_share_id(share_id):
        row = query_one("SELECT * FROM game WHERE share_id = ?", (share_id,))
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
    def list_projects_by_user(user_id):
        """只返回根版本（parent_id IS NULL），即每个项目的入口"""
        rows = query_all(
            "SELECT * FROM game WHERE user_id = ? AND parent_id IS NULL ORDER BY created_at DESC",
            (user_id,),
        )
        return [Game(r) for r in rows]

    @staticmethod
    def get_version_chain(root_id):
        """从根版本开始，沿 parent_id 链找出所有后代版本，按版本号排序"""
        versions = []
        root = Game.get(root_id)
        if root is None:
            return versions
        versions.append(root)

        # 递归查找所有子版本（BFS）
        queue = [root_id]
        while queue:
            parent = queue.pop(0)
            children = query_all(
                "SELECT * FROM game WHERE parent_id = ? ORDER BY version ASC",
                (parent,),
            )
            for child in children:
                game = Game(child)
                versions.append(game)
                queue.append(game.id)

        # 按版本号排序
        versions.sort(key=lambda g: g.version)
        return versions

    @staticmethod
    def find_root_id(game_id):
        """沿着 parent_id 链向上查找根版本 ID"""
        current = Game.get(game_id)
        if current is None:
            return None
        while current.parent_id:
            parent = Game.get(current.parent_id)
            if parent is None:
                break
            current = parent
        return current.id

    @staticmethod
    def create(user_id, title, description, filename, version=1, status="completed", parent_id=None):
        share_id = secrets.token_urlsafe(6)  # 8-char share ID
        execute(
            "INSERT INTO game (user_id, title, description, filename, version, status, parent_id, share_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, title, description, filename, version, status, parent_id, share_id),
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
        # 先更新子版本的 parent_id，让它们指向被删版本的父级（链不断开）
        game = Game.get(game_id)
        if game:
            new_parent = game.parent_id
            execute(
                "UPDATE game SET parent_id = ? WHERE parent_id = ?",
                (new_parent, game_id),
            )
        execute("DELETE FROM game WHERE id = ?", (game_id,))
        commit()

    def __repr__(self):
        return f"<Game {self.title} v{self.version}>"
