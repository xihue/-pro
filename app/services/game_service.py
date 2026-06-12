# -*- coding: utf-8 -*-
"""Game generation service — sync + streaming variants"""
import os
import re
from flask import current_app
from app.models.game import Game
from app.services.llm_client import chat_sync, chat_stream


# ── Naming ──────────────────────────────────────────────

def extract_game_name(html, user_request):
    """Extract game name from HTML <title> or user request. No extra LLM call."""
    # 1. From <title> tag — fast, no API cost
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if match:
        title = match.group(1).strip()
        if title and len(title) <= 30 and "<" not in title and "{" not in title:
            return title

    # 2. Fallback: truncate user request
    fallback = user_request.strip()
    if len(fallback) > 20:
        fallback = fallback[:20] + "..."
    return fallback or "Game"


def get_next_version(game_name):
    """Get next version number for a game name"""
    games_dir = current_app.config["GAMES_DIR"]
    os.makedirs(games_dir, exist_ok=True)

    safe_name = re.sub(r'[\\/:*?"<>|]', "", game_name)

    version = 1
    while os.path.exists(os.path.join(games_dir, f"{safe_name}_v{version}.html")):
        version += 1
    return version, safe_name


# ── Sync (blocking) variants ────────────────────────────

_GAME_PROMPT = """You are an HTML5 game development expert.

User request:

{user_request}

Task:

Generate a complete, playable HTML5 game.

Requirements:

1. Single-file HTML
2. Inline CSS
3. Inline JavaScript
4. Game must be playable
5. Start screen
6. End screen
7. Scoring system
8. Nice visual design
9. Use percentage/vw/vh for responsive Canvas/game area
10. Put a short Chinese game name in the <title> tag
11. No explanations
12. No markdown code blocks

Return HTML source directly.
"""

_IMPROVE_PROMPT = """You are an HTML5 game development expert.

## Original Game Code

Here is the complete HTML source of the existing game:

```html
{old_html}
```

## Improvement Request

{improvement_prompt}

## Task

Modify the existing game code to implement the requested improvements. Do NOT rewrite from scratch.

Requirements:
1. Single-file HTML with inline CSS and JavaScript
2. **Keep all original game features**, only add/modify what the user requested
3. Game must be playable
4. Start screen and end screen
5. Scoring system
6. Use percentage/vw/vh for responsive Canvas/game area
7. Keep the original game name in the <title> tag
8. Nice visual design
9. **No explanations**
10. **No markdown code blocks**

Return the complete improved HTML source directly.
"""


def generate_game(user_request, user_id):
    """Blocking game generation. Returns (game_record, html_content)."""
    prompt = _GAME_PROMPT.format(user_request=user_request)
    html = chat_sync(messages=[{"role": "user", "content": prompt}])

    html = _clean_html(html)
    game_name = extract_game_name(html, user_request)
    version, safe_name = get_next_version(game_name)
    filename = f"{safe_name}_v{version}.html"

    _save_html(filename, html)

    game = Game.create(
        user_id=user_id,
        title=game_name,
        description=user_request,
        filename=filename,
        version=version,
        status="completed",
    )
    return game, html


def improve_game(game_id, improvement_prompt, user_id):
    """Blocking game improvement. Returns (new_game_record, new_html_content)."""
    games_dir = current_app.config["GAMES_DIR"]

    old_game = Game.get(game_id)
    if old_game is None:
        raise ValueError(f"Game {game_id} not found")

    old_filepath = os.path.join(games_dir, old_game.filename)
    if not os.path.exists(old_filepath):
        raise ValueError(f"Game file {old_game.filename} not found")

    with open(old_filepath, "r", encoding="utf-8") as f:
        old_html = f.read()

    prompt = _IMPROVE_PROMPT.format(
        old_html=old_html,
        improvement_prompt=improvement_prompt,
    )
    new_html = chat_sync(messages=[{"role": "user", "content": prompt}])
    new_html = _clean_html(new_html)

    return _finish_improve(old_game, new_html, improvement_prompt, user_id)


# ── Streaming variants ──────────────────────────────────

def generate_game_stream(user_request, user_id):
    """Streaming game generation. Yields SSE event dicts.

    Events: {type: "status", message: ...} | {type: "token", content: ...} | {type: "done", game: {...}}
    """
    prompt = _GAME_PROMPT.format(user_request=user_request)

    yield {"type": "status", "message": "AI is thinking..."}

    chunks = []
    try:
        for token in chat_stream(messages=[{"role": "user", "content": prompt}]):
            chunks.append(token)
            yield {"type": "token", "content": token}
    except Exception as e:
        yield {"type": "error", "message": str(e)}
        return

    html = _clean_html("".join(chunks))
    game_name = extract_game_name(html, user_request)
    version, safe_name = get_next_version(game_name)
    filename = f"{safe_name}_v{version}.html"

    _save_html(filename, html)

    game = Game.create(
        user_id=user_id,
        title=game_name,
        description=user_request,
        filename=filename,
        version=version,
        status="completed",
    )

    yield {"type": "done", "game": game.to_dict()}


def improve_game_stream(game_id, improvement_prompt, user_id):
    """Streaming game improvement. Yields SSE event dicts.

    Events: {type: "status", message: ...} | {type: "token", content: ...} | {type: "done", game: {...}}
    """
    games_dir = current_app.config["GAMES_DIR"]

    old_game = Game.get(game_id)
    if old_game is None:
        yield {"type": "error", "message": f"Game {game_id} not found"}
        return

    old_filepath = os.path.join(games_dir, old_game.filename)
    if not os.path.exists(old_filepath):
        yield {"type": "error", "message": f"File {old_game.filename} not found"}
        return

    with open(old_filepath, "r", encoding="utf-8") as f:
        old_html = f.read()

    prompt = _IMPROVE_PROMPT.format(
        old_html=old_html,
        improvement_prompt=improvement_prompt,
    )

    yield {"type": "status", "message": f"Reading v{old_game.version} source, preparing improvements..."}

    chunks = []
    try:
        for token in chat_stream(messages=[{"role": "user", "content": prompt}]):
            chunks.append(token)
            yield {"type": "token", "content": token}
    except Exception as e:
        yield {"type": "error", "message": str(e)}
        return

    new_html = _clean_html("".join(chunks))
    new_game, _ = _finish_improve(old_game, new_html, improvement_prompt, user_id)

    yield {"type": "done", "game": new_game.to_dict()}


# ── Helpers ─────────────────────────────────────────────

def _clean_html(html):
    html = html.replace("```html", "")
    html = html.replace("```", "")
    return html.strip()


def _save_html(filename, html):
    games_dir = current_app.config["GAMES_DIR"]
    os.makedirs(games_dir, exist_ok=True)
    filepath = os.path.join(games_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)


def _finish_improve(old_game, new_html, improvement_prompt, user_id):
    game_name = old_game.title
    version, safe_name = get_next_version(game_name)
    filename = f"{safe_name}_v{version}.html"

    _save_html(filename, new_html)

    new_game = Game.create(
        user_id=user_id,
        title=game_name,
        description=improvement_prompt,
        filename=filename,
        version=version,
        status="completed",
        parent_id=old_game.id,
    )
    return new_game, new_html
