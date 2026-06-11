"""统一的 LLM 调用客户端，支持流式和非流式"""
from openai import OpenAI
from flask import current_app


def get_client():
    """获取 OpenAI 兼容客户端实例"""
    return OpenAI(
        api_key=current_app.config["API_KEY"],
        base_url=current_app.config["BASE_URL"],
    )


def chat_sync(messages, model=None):
    """非流式对话"""
    client = get_client()
    model = model or current_app.config["MODEL"]

    response = client.chat.completions.create(
        model=model,
        messages=messages,
    )

    return response.choices[0].message.content


def chat_stream(messages, model=None):
    """流式对话，返回生成器"""
    client = get_client()
    model = model or current_app.config["MODEL"]

    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
    )

    for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


def chat_stream_full(messages, model=None):
    """流式对话，返回 (content_generator, full_response_collector)"""
    client = get_client()
    model = model or current_app.config["MODEL"]

    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
    )

    full_response = []

    def generate():
        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                full_response.append(content)
                yield content

    return generate(), full_response
