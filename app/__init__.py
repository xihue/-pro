from flask import Flask
from app.config import Config
from app.extensions import login_manager
from app import database


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 初始化数据库（创建表 + 默认用户）
    database.init_app(app)

    # 初始化 Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "请先登录"

    # 注册蓝图
    from app.routes.main import bp as main_bp
    from app.routes.auth import bp as auth_bp
    from app.routes.chat import bp as chat_bp
    from app.routes.game import bp as game_bp
    from app.routes.api import bp as api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(chat_bp, url_prefix="/chat")
    app.register_blueprint(game_bp, url_prefix="/game")
    app.register_blueprint(api_bp, url_prefix="/api")

    # 确保存储目录存在
    import os

    os.makedirs(app.config["GAMES_DIR"], exist_ok=True)

    return app
