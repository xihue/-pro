"""数据库层 — 基于 Python 标准库 sqlite3"""
import sqlite3
import os
from flask import g, current_app


DATABASE_NAME = "app.db"


def get_db_path():
    """获取数据库文件路径"""
    instance_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "instance"
    )
    os.makedirs(instance_dir, exist_ok=True)
    return os.path.join(instance_dir, DATABASE_NAME)


def get_db():
    """获取当前请求的数据库连接"""
    if "db" not in g:
        g.db = sqlite3.connect(get_db_path())
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


def close_db(exception=None):
    """关闭数据库连接"""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app):
    """初始化数据库（注册 teardown，创建表）"""
    app.teardown_appcontext(close_db)
    with app.app_context():
        db = sqlite3.connect(get_db_path())
        db.row_factory = sqlite3.Row
        db.executescript(SCHEMA)
        db.commit()
        # 创建默认用户
        from werkzeug.security import generate_password_hash

        existing = db.execute("SELECT id FROM user LIMIT 1").fetchone()
        if not existing:
            db.execute(
                "INSERT INTO user (username, password_hash, role, goal, skills) VALUES (?, ?, ?, ?, ?)",
                (
                    "naruto",
                    generate_password_hash("1234"),
                    "AI网页游戏开发者",
                    "开发AI游戏工厂",
                    '["HTML", "CSS", "JavaScript", "Python", "API调用"]',
                ),
            )
            db.commit()
        db.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS user (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    UNIQUE NOT NULL,
    password_hash TEXT    NOT NULL,
    role          TEXT    DEFAULT 'AI网页游戏开发者',
    goal          TEXT    DEFAULT '开发AI游戏工厂',
    skills        TEXT    DEFAULT '[]',
    created_at    TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS game (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES user(id),
    title         TEXT    NOT NULL,
    description   TEXT,
    filename      TEXT    NOT NULL,
    version       INTEGER DEFAULT 1,
    status        TEXT    DEFAULT 'completed',
    created_at    TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS conversation (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES user(id),
    title         TEXT,
    created_at    TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS message (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL REFERENCES conversation(id),
    role            TEXT    NOT NULL,
    content         TEXT    NOT NULL,
    created_at      TEXT    DEFAULT (datetime('now'))
);
"""


# ── 查询辅助 ──────────────────────────────────────

def query_one(sql, params=()):
    """执行查询，返回单行 dict"""
    db = get_db()
    row = db.execute(sql, params).fetchone()
    return dict(row) if row else None


def query_all(sql, params=()):
    """执行查询，返回列表[dict]"""
    db = get_db()
    rows = db.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def execute(sql, params=()):
    """执行写操作，返回 cursor"""
    db = get_db()
    return db.execute(sql, params)


def commit():
    """提交事务"""
    get_db().commit()
