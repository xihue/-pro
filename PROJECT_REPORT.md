# AI 网页游戏工厂 — 项目报告

> 文档生成日期：2026-06-11  
> 版本：v2.0（Flask Web 版）

---

## 1. 项目概述

**AI 网页游戏工厂**是一个基于 Flask 的 Web 应用，用户通过自然语言描述需求，AI 自动生成完整的 HTML5 小游戏。项目从 CLI Agent 框架（v1.0）演进而来，现已支持用户注册登录、多轮 AI 对话、流式响应、游戏生成与管理等完整功能。

| 维度 | 说明 |
|------|------|
| **项目名称** | AI 网页游戏工厂 |
| **技术栈** | Python 3.10+ / Flask / SQLite / DeepSeek API |
| **定位** | AI 应用 × 全栈开发作品集项目 |
| **运行方式** | `python run.py`，浏览器访问 `localhost:5000` |

---

## 2. 项目结构

```
personal agentV1项目一/
│
├── run.py                         # 启动入口
├── config.py                      # CLI 版本的旧配置（保留兼容）
├── requirements.txt               # Python 依赖
│
├── app/                           # Flask 应用主模块
│   ├── __init__.py                # 工厂函数 create_app()
│   ├── config.py                  # Flask 配置（数据库、API、路径）
│   ├── database.py                # 数据库层（sqlite3 封装）
│   ├── extensions.py              # Flask 扩展（LoginManager）
│   │
│   ├── models/                    # 数据模型（纯 sqlite3，无 ORM）
│   │   ├── user.py                # 用户模型（兼容 Flask-Login）
│   │   ├── game.py                # 游戏记录模型
│   │   ├── conversation.py        # 对话会话模型
│   │   └── message.py             # 消息模型（OpenAI 格式兼容）
│   │
│   ├── routes/                    # 路由 / 控制器
│   │   ├── main.py                # 首页仪表盘
│   │   ├── auth.py                # 登录 / 注册 / 退出
│   │   ├── chat.py                # AI 对话页面
│   │   ├── game.py                # 游戏生成 / 列表 / 试玩页面
│   │   └── api.py                 # REST API + SSE 流式接口
│   │
│   ├── services/                  # 业务逻辑层
│   │   ├── llm_client.py          # LLM 调用封装（流式 + 非流式）
│   │   ├── router_service.py      # 意图路由（game / chat 分流）
│   │   ├── game_service.py        # 游戏生成核心逻辑
│   │   └── chat_service.py        # 对话管理服务
│   │
│   ├── templates/                 # Jinja2 模板（7 个页面）
│   │   ├── base.html              # 基础布局（导航栏 + 页脚）
│   │   ├── index.html             # 仪表盘首页
│   │   ├── chat.html              # AI 对话页（侧边栏 + 流式气泡）
│   │   ├── game_create.html       # 游戏生成页（快捷标签 + SSE）
│   │   ├── game_play.html         # 游戏试玩页（响应式 iframe）
│   │   ├── game_list.html         # 游戏大厅
│   │   └── auth/                  # 登录 / 注册页
│   │
│   └── static/css/style.css      # 全局样式
│
├── agent/                         # 旧 CLI 版本的 router（保留）
├── skills/                        # 旧 CLI 版本的技能模块（保留）
├── tools/                         # 旧 CLI 版本的工具模块（保留）
├── prompts/                       # 提示词模板
├── storage/games/                 # 生成的游戏 HTML 文件
├── memory/                        # 用户画像 + 对话历史
└── output/                        # 旧版输出文件
```

### 文件统计

| 类别 | 文件数 | 说明 |
|------|--------|------|
| Python 源文件 | 20 | Flask 应用 + 服务层 + 模型 + 路由 |
| HTML 模板 | 7 | Jinja2 渲染的页面 |
| CSS 样式 | 1 | 全局样式 + 页面内联样式 |
| 配置文件 | 3 | config.py / requirements.txt / prompts |
| **总计** | **31** | 不含 `__pycache__`、`.git`、数据库 |

---

## 3. 架构设计

### 3.1 分层架构

```
┌──────────────────────────────────────────┐
│              浏览器 (HTML/JS)             │
│     SSE 流式接收  ·  AJAX 请求           │
└──────────────┬───────────────────────────┘
               │ HTTP / SSE
               ▼
┌──────────────────────────────────────────┐
│            routes/ (控制器层)             │
│   main  ·  auth  ·  chat  ·  game  · api │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│           services/ (业务逻辑层)          │
│   router  ·  chat  ·  game  ·  llm       │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│          models/ + database.py (数据层)   │
│   User  ·  Game  ·  Conversation  ·  Message │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│        SQLite  /  文件系统  /  DeepSeek API│
└──────────────────────────────────────────┘
```

### 3.2 核心设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 数据库 | sqlite3（原生） | 零依赖，无需安装数据库服务 |
| ORM | 无（手写 SQL） | 代码量可控，学习价值高 |
| 前端框架 | 无（原生 JS + Jinja2） | 保持简单，不引入构建工具链 |
| 实时通信 | SSE（Server-Sent Events） | 单向流式推送足够，比 WebSocket 简单 |
| LLM 后端 | DeepSeek API（OpenAI 兼容） | 性价比高，接口标准 |
| 认证 | Flask-Login + session | 轻量，无需 JWT 的复杂度 |

### 3.3 数据流：一次游戏生成请求

```
用户输入 "贪吃蛇游戏"
        │
        ▼
POST /api/chat/stream  ──→  router_service.route_task()
        │                        │
        │                   返回 "game"
        │                        │
        ▼                        ▼
_handle_game_stream()    game_service.generate_game()
        │                        │
        │                   1. 构建 Prompt
        │                   2. 调用 DeepSeek API 生成 HTML
        │                   3. 清理代码块标记
        │                   4. extract_game_name()
        │                      ├─ 正则提取 <title>
        │                      ├─ LLM 命名（备用）
        │                      └─ 截断兜底
        │                   5. 写入 storage/games/
        │                   6. 创建数据库记录
        │                        │
        ▼                        ▼
SSE 推送:                   返回 (game, html)
  data: {type: "status", message: "正在生成游戏..."}
  data: {type: "done", game: {id, title, play_path}}
        │
        ▼
前端接收 → 显示完成提示 → 跳转试玩页
```

---

## 4. 功能清单

### 4.1 用户系统
- [x] 用户注册（用户名 + 密码）
- [x] 用户登录 / 退出
- [x] 登录状态持久化（Flask-Login session）
- [x] 密码哈希存储（Werkzeug）

### 4.2 AI 对话
- [x] 多轮对话（带上下文）
- [x] 流式响应（SSE，逐 token 推送）
- [x] 多会话管理（新建 / 切换 / 删除）
- [x] 自动生成对话标题
- [x] 游戏生成意图自动识别

### 4.3 游戏生成
- [x] 自然语言描述生成 HTML5 游戏
- [x] 8 个快捷标签（贪吃蛇、飞机大战 等）
- [x] 流式状态推送（前端实时显示进度）
- [x] 智能游戏命名（三级策略）
- [x] 版本管理（同名游戏自动递增版本号）
- [x] 文件名非法字符清理

### 4.4 游戏管理
- [x] 游戏列表（卡片展示）
- [x] 游戏试玩（内嵌 iframe）
- [x] 响应式窗口（80vh 自适应高度）
- [x] 全屏模式
- [x] 重新生成
- [x] 删除游戏

### 4.5 首页仪表盘
- [x] 数据概览（游戏数、对话数）
- [x] 快捷入口卡片
- [x] 最近生成列表

---

## 5. 数据库设计

### 5.1 ER 关系

```
User (1) ────< (N) Game
User (1) ────< (N) Conversation
Conversation (1) ────< (N) Message
```

### 5.2 表结构

**user** — 用户表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| username | TEXT UNIQUE | 用户名 |
| password_hash | TEXT | 密码哈希 |
| role | TEXT | 角色（默认 "AI网页游戏开发者"） |
| goal | TEXT | 目标（默认 "开发AI游戏工厂"） |
| skills | TEXT | 技能列表 JSON |
| created_at | TEXT | 创建时间 |

**game** — 游戏记录表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| user_id | INTEGER FK | 所属用户 |
| title | TEXT | 游戏名称（智能提取） |
| description | TEXT | 原始需求描述 |
| filename | TEXT | 存储文件名 |
| version | INTEGER | 版本号（从 1 起） |
| status | TEXT | 状态（completed/generating/failed） |
| created_at | TEXT | 创建时间 |

**conversation** — 对话表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| user_id | INTEGER FK | 所属用户 |
| title | TEXT | 对话标题（自动生成） |
| created_at | TEXT | 创建时间 |

**message** — 消息表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| conversation_id | INTEGER FK | 所属对话 |
| role | TEXT | 角色（user/assistant/system） |
| content | TEXT | 消息内容 |
| created_at | TEXT | 创建时间 |

---

## 6. API 接口

### 6.1 REST API

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/conversations` | 获取对话列表 | ✅ |
| POST | `/api/conversations` | 创建新对话 | ✅ |
| DELETE | `/api/conversations/<id>` | 删除对话 | ✅ |
| GET | `/api/conversations/<id>/messages` | 获取对话消息 | ✅ |
| POST | `/api/chat/send` | 同步发送消息 | ✅ |
| POST | `/api/chat/stream` | **流式**发送消息（SSE） | ✅ |
| POST | `/api/game/generate` | 同步生成游戏 | ✅ |
| GET | `/api/games` | 获取游戏列表 | ✅ |
| DELETE | `/api/games/<id>` | 删除游戏 | ✅ |

### 6.2 SSE 事件类型

| type | 触发时机 | payload |
|------|---------|---------|
| `meta` | 流式开始 | `{skill, conversation_id}` |
| `status` | 状态更新 | `{message}` |
| `token` | 对话流式逐 token | `{content}` |
| `done` | 对话完成 | `{conversation_id}` |
| `done` + `game` | 游戏生成完成 | `{game: {id, title, play_path, ...}}` |
| `error` | 发生错误 | `{message}` |

---

## 7. 游戏生成命名策略

v2.1 版本已将命名从"暴力删词"升级为三级智能策略：

| 优先级 | 策略 | 示例 |
|--------|------|------|
| 1 | 从 HTML `<title>` 标签正则提取 | `<title>贪吃蛇</title>` → "贪吃蛇" |
| 2 | LLM 从 HTML 代码推理命名（轻量调用） | 提取不到 title → LLM 命名 |
| 3 | 用户请求截断兜底 | "生成一个超长描述游戏..." → "生成一个超长描述游戏…" |

---

## 8. 技术亮点

1. **SSE 流式响应** — 游戏生成和 AI 对话均使用 Server-Sent Events 实时推送，用户体验流畅
2. **智能意图路由** — 用户输入先经过 LLM 判断是"游戏生成"还是"普通对话"，自动分流
3. **无 ORM 的数据库层** — 手写 SQL + WAL 模式 + 外键约束，代码透明可控
4. **纯原生前端** — 零 JS 框架依赖，SSE 解析、DOM 操作全部手写
5. **Jinja2 模板继承** — base.html 统一布局，各页面只写差异部分
6. **响应式游戏窗口** — iframe 使用 `80vh` 自适应 + `min-height`/`max-height` 限制

---

## 9. 已知限制

| 限制 | 影响 | 建议改进方向 |
|------|------|-------------|
| 无 API Key 管理 | 所有用户共享同一个 API Key | 支持用户自行配置 API Key |
| 无流控限制 | 可能被滥用 | 加请求频率限制 |
| 同步 LLM 调用阻塞 | 游戏生成期间用户需等待 | 改为异步任务队列（Celery） |
| 无游戏修改功能 | 无法在已有游戏基础上迭代 | 加游戏编辑/迭代接口 |
| SQLite 单文件 | 并发写入瓶颈 | 部署时迁移到 PostgreSQL |
| 无前端框架 | 复杂交互时代码难维护 | 考虑引入 Alpine.js 或 Vue |

---

## 10. 运行说明

### 环境要求
- Python 3.10+
- DeepSeek API Key

### 安装启动

```bash
# 1. 进入项目目录
cd "personal agentV1项目一"

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 API Key（编辑 app/config.py 或设置环境变量）
# 环境变量方式：
#   export DEEPSEEK_API_KEY=sk-your-key

# 4. 启动
python run.py

# 5. 浏览器访问
# http://localhost:5000
```

### 默认账户
| 用户名 | 密码 |
|--------|------|
| naruto | 1234 |

---

## 11. 依赖清单

```
Flask==3.1.*              # Web 框架
Flask-Login==0.6.*        # 用户认证
openai>=1.0               # LLM API 客户端（OpenAI 兼容）
python-dotenv==1.1.*      # 环境变量加载
Werkzeug==3.1.*           # WSGI 工具库（密码哈希）
```

---

## 12. 演进历史

| 版本 | 日期 | 变化 |
|------|------|------|
| v1.0 | 2026-06-11 | CLI Agent 框架：技能插件系统、关键词+LLM混合路由、MemoryStore |
| v2.0 | 2026-06-11 | Flask Web 化：用户系统、多轮对话、流式响应、游戏CRUD |
| v2.1 | 2026-06-11 | Bug 修复：SSE 事件匹配、智能游戏命名、响应式游戏窗口 |

---

## 13. 后续路线图

详见 [原始项目讨论](./ARCHITECTURE.md)，核心方向：

- **短期**：添加日志系统、单元测试、流式输出优化
- **中期**：FastAPI 重构、RAG 知识库、Function Calling、Docker 部署
- **长期**：多 Agent 协作、支付集成、生产级 SaaS 产品

---

> 完整的架构设计讨论和扩展方案见原始项目 `ARCHITECTURE.md`。
