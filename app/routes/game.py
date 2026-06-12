from flask import Blueprint, render_template, redirect, url_for, current_app, send_from_directory
from flask_login import login_required, current_user
from app.models.game import Game

bp = Blueprint("game", __name__)


# ── 需要登录的路由 ────────────────────────────────────


@bp.route("/create")
@login_required
def create():
    recent = Game.list_by_user(current_user.id, limit=10)
    return render_template("game_create.html", recent_games=recent)


@bp.route("/list")
@login_required
def list_games():
    games = Game.list_by_user(current_user.id)
    return render_template("game_list.html", games=games)


@bp.route("/play/<int:game_id>")
@login_required
def play(game_id):
    game = Game.get(game_id)
    if game is None or game.user_id != current_user.id:
        return redirect(url_for("game.list_games"))
    return render_template("game_play.html", game=game)


# 静态文件服务：提供 games 目录下的 HTML 文件
@bp.route("/games/<path:filename>")
def serve_game(filename):
    return send_from_directory(current_app.config["GAMES_DIR"], filename)
