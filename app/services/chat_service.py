"""对话服务"""
import json
from flask import current_app
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.services.llm_client import chat_sync


def get_or_create_conversation(user_id, title=None):
    """获取用户最新的对话，或创建新对话"""
    conv = Conversation.get_latest(user_id)
    if conv is None:
        conv = Conversation.create(user_id, title or "新对话")
    return conv


def build_messages(conversation, user):
    """构建发送给 LLM 的完整消息列表"""
    messages = []

    # 系统消息
    system_content = f"""
用户信息：

{json.dumps(user.to_dict(), ensure_ascii=False)}

你是一个AI网页游戏工厂助手。

你可以：
1. 生成HTML5小游戏
2. 修改小游戏
3. 回答用户问题
"""
    messages.append({"role": "system", "content": system_content})

    # 历史消息
    history = Message.list_by_conversation(conversation.id)
    for msg in history:
        messages.append(msg.to_openai_format())

    return messages


def send_message_sync(user_input, user_id):
    """同步发送消息并获取回复"""
    user = User.get(user_id)
    conv = get_or_create_conversation(user_id)

    # 保存用户消息
    Message.create(conv.id, "user", user_input)

    # 构建消息
    messages = build_messages(conv, user)

    # 调用 LLM
    assistant_reply = chat_sync(messages=messages)

    # 保存助手回复
    Message.create(conv.id, "assistant", assistant_reply)

    # 自动生成对话标题
    if conv.title == "新对话":
        Conversation.update_title(conv.id, user_input[:30])

    # 重新获取 conv（title 已更新）
    conv = Conversation.get(conv.id)

    return assistant_reply, conv


def get_conversations_for_user(user_id):
    """获取用户的所有对话列表"""
    return Conversation.list_by_user(user_id)


def get_messages_for_conversation(conv_id, user_id):
    """获取对话的所有消息（验证所有权）"""
    conv = Conversation.get(conv_id)
    if conv is None or conv.user_id != user_id:
        return None
    return Message.list_by_conversation(conv.id)
