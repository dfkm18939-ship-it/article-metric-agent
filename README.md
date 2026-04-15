# 稿件指标智能助手

> 多模型协作的稿件指标智能查询系统，已统一接入 **GitHub Copilot API**，支持作为 **Copilot Extension** 使用。

---

## 架构图

```
用户输入（自然语言）
        │
        ▼
┌───────────────────────────────────────────────────┐
│                    Orchestrator                    │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────┐ │
│  │  GPT-4o     │  │ Claude-3.5   │  │ Gemini   │ │
│  │  意图理解   │  │ SQL 生成     │  │ 总结展示 │ │
│  │  逻辑校验   │  │ 代码审查     │  │ 图表推荐 │ │
│  └─────────────┘  └──────────────┘  └──────────┘ │
│           ↓              ↓               ↓         │
│  ┌────────────────────────────────────────────┐   │
│  │      CrossValidator（多模型互审）           │   │
│  └────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────┘
        │
        ▼
  ┌─────────────┐        ┌──────────────────────┐
  │  SQLite DB  │        │  Copilot Extension   │
  │  (本地/云)  │        │  POST /agent (SSE)   │
  └─────────────┘        └──────────────────────┘
```

### 三模型分工说明

| 模型 | 负责功能 | Copilot API 调用方法 |
|------|---------|-------------------|
| **GPT-4o** | 意图理解、逻辑校验、交叉验证 | `copilot.chat_with_gpt()` |
| **Claude 3.5 Sonnet** | SQL 生成、代码安全审查 | `copilot.chat_with_claude()` |
| **Gemini 1.5 Pro** | 结果总结、图表推荐 | `copilot.chat_with_gemini()` |

> **改造重点**：三个模型均通过同一 `GITHUB_TOKEN` 经由 GitHub Copilot API 调用，无需分别申请 OpenAI / Anthropic / Google API Key。

---

## 改造说明

```
改造前（三个独立 API）          改造后（统一 Copilot API）
────────────────────────────────────────────────────
OPENAI_API_KEY       →        GITHUB_TOKEN（一个）
ANTHROPIC_API_KEY    →        （删除）
GEMINI_API_KEY       →        （删除）

GPTClient            →        copilot.chat_with_gpt()
ClaudeClient         →        copilot.chat_with_claude()
GeminiClient         →        copilot.chat_with_gemini()

仅 Web 界面访问       →        + @article-metric-agent 对话访问
```

---

## 快速开始

```bash
git clone https://github.com/dfkm18939-ship-it/article-metric-agent
cd article-metric-agent
cp .env.example .env
# 只需填写一个 GITHUB_TOKEN
pip install -r requirements.txt
python init_db.py      # 初始化本地测试数据库（1000 条模拟数据）
python main.py         # 启动服务 → http://localhost:8000
```

---

## Copilot Extension 注册指南

1. 部署服务到公网（如 Railway / Render / 自建服务器）
2. 前往 [GitHub Settings → Developer Settings → GitHub Apps](https://github.com/settings/apps/new)
3. 填写 Webhook URL：`https://your-domain/agent`
4. 在 `.env` 中填写 `WEBHOOK_SECRET`
5. 安装 Extension 后，在 GitHub Issues / PR / Chat 中使用：

```
@article-metric-agent 今年签发了多少稿件？
@article-metric-agent 上个月各部门签发量对比
@article-metric-agent 本月签发趋势
```

---

## API 文档

| 路由 | 方法 | 说明 |
|------|------|------|
| `/` | GET | Web 对话界面 |
| `/agent` | POST | Copilot Extension 入口（SSE 流式响应） |
| `/api/query` | POST | 自然语言查询接口 |
| `/api/metrics` | GET | 列出所有支持的指标口径 |
| `/health` | GET | 健康检查 |
| `/.well-known/copilot-agent-manifest.json` | GET | Extension 注册配置 |

---

## 指标字典扩展指南

在 `claude/sql_generator.py` 的 `SQL_GENERATOR_SYSTEM_PROMPT` 中添加新指标的口径定义：

```python
# 例如添加"退稿量"指标
- 退稿量：status = 'rejected' AND created_at 在时间范围内
```

---

## 目录结构

```
article-metric-agent/
├── core/
│   ├── copilot_client.py   # GitHub Copilot API 统一客户端（核心）
│   └── orchestrator.py     # 多模型协作编排器
├── gpt/
│   ├── intent_agent.py     # 意图识别（GPT-4o）
│   ├── logic_validator.py  # 逻辑校验（GPT-4o）
│   └── anomaly_analyzer.py # 异常分析（GPT-4o）
├── claude/
│   ├── sql_generator.py    # SQL 生成（Claude 3.5 Sonnet）
│   ├── code_reviewer.py    # 代码审查（Claude 3.5 Sonnet）
│   └── api_server.py       # FastAPI 路由
├── gemini/
│   ├── summary_renderer.py # 结果总结（Gemini 1.5 Pro）
│   └── chart_advisor.py    # 图表推荐（Gemini 1.5 Pro）
├── validator/
│   └── cross_validator.py  # 多模型交叉验证
├── copilot_extension/
│   ├── handler.py          # Extension 处理器（SSE 流式）
│   ├── middleware.py       # 签名验证中间件
│   └── manifest.json       # Extension 注册配置
├── web/
│   └── index.html          # 对话式 Web 界面
├── main.py                 # FastAPI 主应用
├── config.py               # 统一配置
├── init_db.py              # 数据库初始化
├── requirements.txt        # 依赖（无 openai/anthropic/google-generativeai）
└── .env.example            # 只需填写 GITHUB_TOKEN
```