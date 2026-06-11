"""用户模型 — 基于 sqlite3"""
import json
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import login_manager
from app.database import query_one, execute, commit


class User(UserMixin):
    """用户类，兼容 Flask-Login"""

    def __init__(self, row_dict):
        self._data = row_dict
        self.id = row_dict["id"]

    @property
    def username(self):
        return self._data["username"]

    @property
    def role(self):
        return self._data.get("role", "AI网页游戏开发者")

    @property
    def goal(self):
        return self._data.get("goal", "开发AI游戏工厂")

    @property
    def skills(self):
        try:
            return json.loads(self._data.get("skills", "[]"))
        except (json.JSONDecodeError, TypeError):
            return []

    @property
    def created_at(self):
        return self._data.get("created_at")

    def check_password(self, password):
        return check_password_hash(self._data["password_hash"], password)

    def to_dict(self):
        return {
            "name": self.username,
            "role": self.role,
            "goal": self.goal,
            "skills": self.skills,
        }

    # ── 静态方法 ──────────────────────────────

    @staticmethod
    def get(user_id):
        row = query_one("SELECT * FROM user WHERE id = ?", (user_id,))
        return User(row) if row else None

    @staticmethod
    def get_by_username(username):
        row = query_one("SELECT * FROM user WHERE username = ?", (username,))
        return User(row) if row else None

    @staticmethod
    def create(username, password):
        """创建用户，返回 User"""
        execute(
            "INSERT INTO user (username, password_hash) VALUES (?, ?)",
            (username, generate_password_hash(password)),
        )
        commit()
        return User.get_by_username(username)

    def __repr__(self):
        return f"<User {self.username}>"


@login_manager.user_loader
def load_user(user_id):
    return User.get(int(user_id))
