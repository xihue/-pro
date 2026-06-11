from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from app.models.conversation import Conversation
from app.models.message import Message

bp = Blueprint("chat", __name__)


@bp.route("/")
@login_required
def index():
    conversations = Conversation.list_by_user(current_user.id)
    return render_template("chat.html", conversations=conversations)


@bp.route("/<int:conv_id>")
@login_required
def view(conv_id):
    conversation = Conversation.get(conv_id)
    if conversation is None or conversation.user_id != current_user.id:
        return redirect(url_for("chat.index"))

    conversations = Conversation.list_by_user(current_user.id)
    messages = Message.list_by_conversation(conv_id)
    return render_template(
        "chat.html",
        conversations=conversations,
        current_conv_id=conv_id,
        messages=messages,
    )
