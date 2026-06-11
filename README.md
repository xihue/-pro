# 🎮 AI 网页游戏工厂

> 基于 Flask + DeepSeek API 的 AI 应用，用自然语言描述你想要的游戏，AI 自动生成完整的 HTML5 可玩网页游戏。

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1-green)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## ✨ 功能

| 模块 | 功能 |
|------|------|
| 👤 用户系统 | 注册、登录、退出，密码哈希存储 |
| 💬 AI 对话 | 多轮对话、流式响应、多会话切换、自动标题 |
| 🎮 游戏生成 | 自然语言描述 → 完整 HTML5 游戏，智能命名，版本管理 |
| 🕹️ 游戏管理 | 列表浏览、内嵌试玩、全屏模式、重新生成、删除 |

## 🖼️ 截图

| 首页 | AI 对话 | 生成游戏 |
|------|---------|----------|
| 仪表盘 + 统计数据 | 流式气泡 + 侧边栏 | 快捷标签 + 一键生成 |

> 启动后访问 `http://localhost:5000` 即可体验。

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

复制模板文件并填入你的 DeepSeek API Key：

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 Key：
# DEEPSEEK_API_KEY=sk-your-key-here
```

> 没有 Key？去 [DeepSeek 开放平台](https://platform.deepseek.com/api_keys) 免费注册获取。

### 3. 启动

```bash
python run.py
```

浏览器打开 **http://localhost:5000**，默认账户：`naruto` / `1234`

## 🧱 项目结构

```
AI-Game-Factory/
├── run.py                     # 启动入口
├── requirements.txt           # Python 依赖
├── .env.example               # API Key 配置模板
│
├── app/                       # Flask 应用
│   ├── __init__.py            # 工厂函数
│   ├── config.py              # 配置（API / 路径）
│   ├── database.py            # 数据库层（sqlite3）
│   ├── extensions.py          # Flask-Login
│   │
│   ├── models/                # 数据模型
│   │   ├── user.py            # 用户
│   │   ├── game.py            # 游戏记录
│   │   ├── conversation.py    # 对话会话
│   │   └── message.py         # 消息
│   │
│   ├── routes/                # 路由 / 控制器
│   │   ├── main.py            # 首页仪表盘
│   │   ├── auth.py            # 登录 / 注册
│   │   ├── chat.py            # AI 对话页面
│   │   ├── game.py            # 游戏页面
│   │   └── api.py             # REST API + SSE
│   │
│   ├── services/              # 业务逻辑
│   │   ├── llm_client.py      # LLM 调用（流式 + 非流式）
│   │   ├── router_service.py  # 意图路由（游戏 / 对话）
│   │   ├── game_service.py    # 游戏生成
│   │   └── chat_service.py    # 对话管理
│   │
│   ├── templates/             # 7 个 Jinja2 页面
│   └── static/                # CSS 样式
│
└── storage/games/             # 生成的游戏 HTML
```

## 🏗️ 架构

```
浏览器 (HTML/JS)  ←─ SSE 流式 ─→  routes/ (控制器)
                                        │
                                   services/ (业务)
                                        │
                              models/ + database.py (数据)
                                        │
                         SQLite / 文件系统 / DeepSeek API
```

### 一次游戏生成的完整流程

```
用户输入 "贪吃蛇游戏"
  → LLM 意图路由 → "game"
    → 构建 Prompt → DeepSeek 生成 HTML
      → 清理代码块 → 智能提取游戏名
        → 写入文件 → 创建数据库记录
          → SSE 推送完成信号 → 前端自动跳转试玩页
```

### 核心设计选择

| 维度 | 选择 | 理由 |
|------|------|------|
| 数据库 | sqlite3（手写 SQL） | 零依赖、代码透明 |
| 前端 | 原生 JS + Jinja2 | 无构建工具链，保持简单 |
| 实时通信 | SSE | 流式推送够用，比 WebSocket 简单 |
| LLM | DeepSeek（OpenAI 兼容） | 性价比高，接口标准 |
| 认证 | Flask-Login + Session | 轻量，无需 JWT |

## 📡 API

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/conversations` | 对话列表 | ✅ |
| POST | `/api/conversations` | 创建对话 | ✅ |
| POST | `/api/chat/stream` | **流式**消息（SSE） | ✅ |
| POST | `/api/game/generate` | 生成游戏 | ✅ |
| GET | `/api/games` | 游戏列表 | ✅ |
| DELETE | `/api/games/<id>` | 删除游戏 | ✅ |

## 🔧 技术栈

| 组件 | 技术 |
|------|------|
| 语言 | Python 3.10+ |
| 框架 | Flask 3.1 |
| 数据库 | SQLite（原生 sqlite3） |
| 认证 | Flask-Login + Werkzeug |
| LLM | DeepSeek API（OpenAI 兼容） |
| 前端 | Jinja2 + 原生 JavaScript + SSE |
| 依赖 | 仅 5 个包，无 LangChain / ORM / JS 框架 |

## 📄 License

MIT — 自由使用、修改、分发。
