from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models.game import Game
from app.models.conversation import Conversation

bp = Blueprint("main", __name__)


@bp.route("/")
@login_required
def index():
    game_count = Game.count_by_user(current_user.id)
    convs = Conversation.list_by_user(current_user.id)
    recent_games = Game.list_by_user(current_user.id, limit=4)

    return render_template(
        "index.html",
        game_count=game_count,
        conv_count=len(convs),
        recent_games=recent_games,
    )
