"""REST API + SSE 流式接口"""
import json
from flask import (
    Blueprint, request, jsonify, Response, stream_with_context,
    current_app,
)
from flask_login import login_required, current_user
from app.models.game import Game
from app.models.conversation import Conversation
from app.models.message import Message
from app.services.router_service import route_task
from app.services.game_service import generate_game
from app.services.chat_service import (
    send_message_sync, build_messages,
)
from app.services.llm_client import chat_stream

bp = Blueprint("api", __name__)


# ── 对话 API ─────────────────────────────────────────

@bp.route("/conversations", methods=["GET"])
@login_required
def list_conversations():
    convs = Conversation.list_by_user(current_user.id)
    return jsonify([c.to_dict() for c in convs])


@bp.route("/conversations", methods=["POST"])
@login_required
def create_conversation():
    title = request.json.get("title", "新对话") if request.is_json else "新对话"
    conv = Conversation.create(current_user.id, title)
    return jsonify(conv.to_dict()), 201


@bp.route("/conversations/<int:conv_id>", methods=["DELETE"])
@login_required
def delete_conversation(conv_id):
    conv = Conversation.get(conv_id)
    if conv is None or conv.user_id != current_user.id:
        return jsonify({"error": "对话不存在"}), 404

    Conversation.delete(conv.id)
    return jsonify({"ok": True})


@bp.route("/conversations/<int:conv_id>/messages", methods=["GET"])
@login_required
def list_messages(conv_id):
    conv = Conversation.get(conv_id)
    if conv is None or conv.user_id != current_user.id:
        return jsonify({"error": "对话不存在"}), 404

    messages = Message.list_by_conversation(conv_id)
    return jsonify([m.to_dict() for m in messages])


# ── 聊天（阻塞式） ────────────────────────────────────

@bp.route("/chat/send", methods=["POST"])
@login_required
def chat_send():
    data = request.get_json()
    user_input = data.get("message", "").strip()

    if not user_input:
        return jsonify({"error": "消息不能为空"}), 400

    skill = route_task(user_input)

    if skill == "game":
        game, html = generate_game(user_input, current_user.id)
        return jsonify({
            "type": "game",
            "game": game.to_dict(),
            "message": f"游戏「{game.title}」生成成功！",
        })
    else:
        reply, conv = send_message_sync(user_input, current_user.id)
        return jsonify({
            "type": "chat",
            "conversation": conv.to_dict(),
            "message": reply,
        })


# ── 聊天（SSE 流式） ──────────────────────────────────

@bp.route("/chat/stream", methods=["POST"])
@login_required
def chat_stream_endpoint():
    data = request.get_json()
    user_input = data.get("message", "").strip()
    conv_id = data.get("conversation_id")

    if not user_input:
        return jsonify({"error": "消息不能为空"}), 400

    # 路由判断（带兜底保护，路由失败不影响聊天功能）
    try:
        skill = route_task(user_input)
    except Exception as e:
        print(f"[API] Router fallback: {e}")
        skill = "chat"

    if skill == "game":
        return _handle_game_stream(user_input, current_user.id)

    # 普通对话流式
    def generate():
        user = current_user

        if conv_id:
            conv = Conversation.get(int(conv_id))
            if conv is None or conv.user_id != user.id:
                yield f"data: {json.dumps({'error': '对话不存在'})}\n\n"
                return
        else:
            conv = Conversation.create(user.id)

        # 保存用户消息
        Message.create(conv.id, "user", user_input)

        # 构建消息
        messages = build_messages(conv, user)

        # 发送对话 ID
        yield f"data: {json.dumps({'type': 'meta', 'conversation_id': conv.id})}\n\n"

        # 流式发送
        full_reply = []
        try:
            for token in chat_stream(messages=messages):
                full_reply.append(token)
                yield f"data: {json.dumps({'type': 'token', 'content': token}, ensure_ascii=False)}\n\n"
        except Exception as e:
            error_msg = f"[对话出错: {e}]"
            full_reply.append(error_msg)
            yield f"data: {json.dumps({'type': 'token', 'content': error_msg}, ensure_ascii=False)}\n\n"

        # 保存完整回复
        reply = "".join(full_reply)
        Message.create(conv.id, "assistant", reply)

        if conv.title == "新对话":
            from app.models.conversation import Conversation as C
            C.update_title(conv.id, user_input[:30])

        yield f"data: {json.dumps({'type': 'done', 'conversation_id': conv.id})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def _handle_game_stream(user_input, user_id):
    """游戏生成的 SSE 流 — 内联方式，避免线程上下文问题"""

    def generate():
        yield f"data: {json.dumps({'type': 'meta', 'skill': 'game'})}\n\n"
        yield f"data: {json.dumps({'type': 'status', 'message': '正在生成游戏...'}, ensure_ascii=False)}\n\n"

        try:
            game, html = generate_game(user_input, user_id)
            yield f"data: {json.dumps({'type': 'done', 'game': game.to_dict()}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── 游戏 API ──────────────────────────────────────────

@bp.route("/game/generate", methods=["POST"])
@login_required
def generate_game_api():
    data = request.get_json()
    user_input = data.get("prompt", "").strip()

    if not user_input:
        return jsonify({"error": "需求不能为空"}), 400

    try:
        game, html = generate_game(user_input, current_user.id)
        return jsonify({
            "game": game.to_dict(),
            "message": f"游戏「{game.title}」生成成功！",
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/games", methods=["GET"])
@login_required
def list_games():
    games = Game.list_by_user(current_user.id)
    return jsonify([g.to_dict() for g in games])


@bp.route("/games/<int:game_id>", methods=["DELETE"])
@login_required
def delete_game(game_id):
    import os

    game = Game.get(game_id)
    if game is None or game.user_id != current_user.id:
        return jsonify({"error": "游戏不存在"}), 404

    # 删除文件
    games_dir = current_app.config["GAMES_DIR"]
    filepath = os.path.join(games_dir, game.filename)
    if os.path.exists(filepath):
        os.remove(filepath)

    Game.delete(game_id)
    return jsonify({"ok": True})
