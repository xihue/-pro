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
from app.services.game_service import (
    generate_game, improve_game,
    generate_game_stream, improve_game_stream,
)
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
    """Real streaming game generation — tokens flow as they arrive"""

    def generate():
        yield f"data: {json.dumps({'type': 'meta', 'skill': 'game'})}\n\n"

        try:
            for event in generate_game_stream(user_input, user_id):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
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


# ── 游戏改进 API ──────────────────────────────────────

@bp.route("/game/<int:game_id>/improve", methods=["POST"])
@login_required
def improve_game_api(game_id):
    """基于已有游戏进行改进，生成新版本"""
    data = request.get_json()
    improvement_prompt = data.get("prompt", "").strip()

    if not improvement_prompt:
        return jsonify({"error": "改进需求不能为空"}), 400

    # 验证旧游戏存在且属于当前用户
    old_game = Game.get(game_id)
    if old_game is None or old_game.user_id != current_user.id:
        return jsonify({"error": "游戏不存在"}), 404

    try:
        new_game, html = improve_game(game_id, improvement_prompt, current_user.id)
        return jsonify({
            "game": new_game.to_dict(),
            "message": f"游戏「{new_game.title}」v{new_game.version} 改进成功！",
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/game/<int:game_id>/improve/stream", methods=["POST"])
@login_required
def improve_game_stream_api(game_id):
    """SSE streaming — improve game with real-time token output"""
    data = request.get_json()
    improvement_prompt = data.get("prompt", "").strip()

    if not improvement_prompt:
        return jsonify({"error": "改进需求不能为空"}), 400

    old_game = Game.get(game_id)
    if old_game is None or old_game.user_id != current_user.id:
        return jsonify({"error": "游戏不存在"}), 404

    def generate():
        try:
            for event in improve_game_stream(game_id, improvement_prompt, current_user.id):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
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


@bp.route("/game/<int:game_id>/versions", methods=["GET"])
@login_required
def get_version_chain(game_id):
    """获取某个游戏项目的所有版本"""
    game = Game.get(game_id)
    if game is None or game.user_id != current_user.id:
        return jsonify({"error": "游戏不存在"}), 404

    root_id = Game.find_root_id(game_id)
    versions = Game.get_version_chain(root_id)
    return jsonify([v.to_dict() for v in versions])


@bp.route("/projects", methods=["GET"])
@login_required
def list_projects():
    """列出用户的所有游戏项目（只返回根版本）"""
    projects = Game.list_projects_by_user(current_user.id)
    result = []
    for proj in projects:
        versions = Game.get_version_chain(proj.id)
        result.append({
            "project": proj.to_dict(),
            "version_count": len(versions),
            "versions": [v.to_dict() for v in versions],
        })
    return jsonify(result)
