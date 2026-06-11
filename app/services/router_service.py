"""技能路由服务 — 从 agent/router.py 迁移"""
from app.services.llm_client import chat_sync


def route_task(user_input):
    """判断用户意图：game 或 chat"""
    prompt = f"""
你是Agent路由器。

可用技能：

game
chat

规则：

1. 用户要求：

制作游戏
生成游戏
小游戏
贪吃蛇
飞机大战
俄罗斯方块
塔防
跑酷
射击
HTML游戏

返回：

game

2. 其它情况：

chat

用户输入：

{user_input}

只能返回：

game
chat
"""

    result = chat_sync(
        messages=[{"role": "user", "content": prompt}]
    )

    result = result.strip().lower()

    if "game" in result:
        return "game"

    return "chat"
