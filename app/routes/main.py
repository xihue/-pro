from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models.game import Game
from app.models.conversation import Conversation

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    """首页 — 未登录显示 Hero，已登录显示仪表盘"""
    if not current_user.is_authenticated:
        return render_template("hero.html")

    game_count = Game.count_by_user(current_user.id)
    convs = Conversation.list_by_user(current_user.id)
    recent_games = Game.list_by_user(current_user.id, limit=4)

    return render_template(
        "index.html",
        game_count=game_count,
        conv_count=len(convs),
        recent_games=recent_games,
    )


@bp.route("/hero")
def hero():
    """独立的 Hero 封面页"""
    return render_template("hero.html")


@bp.route("/s/<share_id>")
def shared_game(share_id):
    """公开分享页面 — 无需登录，任何人可访问"""
    game = Game.get_by_share_id(share_id)
    if game is None:
        return render_template("game_share_missing.html"), 404
    return render_template("game_share.html", game=game)
