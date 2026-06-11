"""游戏生成服务"""
import os
import re
from flask import current_app
from app.models.game import Game
from app.services.llm_client import chat_sync


def extract_game_name(html, user_request):
    """智能提取游戏名称：优先从HTML &lt;title&gt;标签提取，其次LLM命名，最后兜底"""
    # 1. 从 <title> 标签提取
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if match:
        title = match.group(1).strip()
        # 过滤掉明显不是游戏名的 title（过长、含代码等）
        if title and len(title) <= 30 and "<" not in title and "{" not in title:
            return title

    # 2. LLM 提取游戏名（只用前3000字符，轻量调用）
    try:
        naming_prompt = f"""从以下HTML代码中提取游戏的简短中文名称（不超过10个字）。

只返回游戏名称，不要解释。
例如："贪吃蛇"、"飞机大战"、"俄罗斯方块"

HTML片段：
{html[:3000]}"""
        name = chat_sync(messages=[{"role": "user", "content": naming_prompt}])
        name = name.strip().strip("。.！!，,：:。\"'“”")
        if name and len(name) <= 20:
            return name
    except Exception:
        pass

    # 3. 兜底：截断用户请求
    fallback = user_request.strip()
    if len(fallback) > 20:
        fallback = fallback[:20] + "…"
    return fallback or "小游戏"


def get_next_version(game_name):
    """获取下一个版本号（清理文件名中的非法字符）"""
    games_dir = current_app.config["GAMES_DIR"]
    os.makedirs(games_dir, exist_ok=True)

    # 清理文件名中的非法字符
    safe_name = re.sub(r'[\\/:*?"<>|]', "", game_name)

    version = 1
    while os.path.exists(os.path.join(games_dir, f"{safe_name}_v{version}.html")):
        version += 1
    return version, safe_name


def generate_game(user_request, user_id):
    """生成 HTML5 游戏，返回 (game_record, html_content)"""
    prompt = f"""你是一名HTML5游戏开发专家。

用户需求：

{user_request}

任务：

生成一个完整可运行的HTML5小游戏。

要求：

1. 单文件HTML
2. 内嵌CSS
3. 内嵌JavaScript
4. 游戏必须可玩
5. 有开始界面
6. 有结束界面
7. 有计分系统
8. 页面美观
9. Canvas/游戏区域使用百分比或vw/vh自适应布局，适配不同屏幕尺寸
10. 在&lt;title&gt;标签中写一个简洁的游戏中文名称
11. 不要解释
12. 不要Markdown代码块

直接返回HTML源码。
"""

    html = chat_sync(messages=[{"role": "user", "content": prompt}])

    # 清理代码块标记
    html = html.replace("```html", "")
    html = html.replace("```", "")
    html = html.strip()

    # 智能命名
    game_name = extract_game_name(html, user_request)
    version, safe_name = get_next_version(game_name)
    filename = f"{safe_name}_v{version}.html"

    # 保存文件
    games_dir = current_app.config["GAMES_DIR"]
    os.makedirs(games_dir, exist_ok=True)
    filepath = os.path.join(games_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    # 创建数据库记录（标题用提取的游戏名）
    game = Game.create(
        user_id=user_id,
        title=game_name,
        description=user_request,
        filename=filename,
        version=version,
        status="completed",
    )

    return game, html
