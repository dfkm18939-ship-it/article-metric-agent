# 📊 数据指标智能查询系统 — article-metric-agent

> 多模型协作的稿件指标智能查询 Web 系统，面向新闻媒体生产系统。

---

## 架构图

```
用户输入
  │
  ▼
┌─────────────────────────────────────────────────────────┐
│                     Orchestrator                        │
│  (core/orchestrator.py)  —  异步调度全流水线              │
└──┬──────────────┬─────────────────┬────────────────────┘
   │ GPT          │ Claude           │ Gemini
   ▼              ▼                  ▼
意图识别        SQL 生成           UI 设计
业务校验        代码审查           图表推荐
异常归因                          结果总结
   │              │                  │
   └──────────────┴──────────────────┘
                  │
          ┌───────▼──────┐
          │ CrossValidator│  多模型互审
          └───────┬──────┘
                  │
          ┌───────▼──────┐
          │  SQLite DB   │  本地模拟数据 (1000条)
          └──────────────┘
```

## 三模型分工

| 模型      | 职责                                         |
|-----------|----------------------------------------------|
| **GPT**   | 意图识别、歧义判断、业务逻辑 SQL 校验、异常归因   |
| **Gemini**| UI 交互设计、图表类型推荐、自然语言结果总结       |
| **Claude**| SQL 生成、代码/意图审查                         |

---

## 工程目录

```
article-metric-agent/
│
├── main.py                        # FastAPI 入口
├── config.py                      # 三模型 API Keys 及配置
├── requirements.txt               # 依赖列表
├── .env.example                   # 环境变量示例
│
├── gpt/
│   ├── intent_agent.py            # 意图识别 + 歧义判断（GPT）
│   ├── logic_validator.py         # 业务规则校验 SQL（GPT）
│   └── anomaly_analyzer.py        # 数据异常归因（GPT）
│
├── claude/
│   ├── sql_generator.py           # SQL 生成（Claude）
│   ├── code_reviewer.py           # 代码/SQL 审查（Claude）
│   └── api_server.py              # FastAPI 路由定义
│
├── gemini/
│   ├── ui_designer.py             # UI 交互方案生成（Gemini）
│   ├── chart_advisor.py           # 图表类型推荐（Gemini）
│   └── summary_renderer.py        # 自然语言结果总结（Gemini）
│
├── validator/
│   ├── cross_validator.py         # 多模型互审核心逻辑
│   └── test_cases.py              # 12 个自动化测试用例
│
├── metrics/
│   └── article_signed.yaml        # 稿件签发通过量完整语义化定义
│
├── core/
│   ├── llm_client.py              # 三模型统一客户端
│   ├── orchestrator.py            # 总调度，串联所有 Agent
│   ├── metric_store.py            # 指标字典加载与向量检索
│   ├── vector_store.py            # 向量库（ChromaDB 本地）
│   ├── db_client.py               # SQLite 模拟数据库（1000 条）
│   └── memory_agent.py            # 用户偏好与对话上下文记忆
│
└── web/
    ├── index.html                 # 主页面（对话式交互界面）
    └── static/
        ├── style.css
        └── app.js
```

---

## 快速开始

### 1. 环境配置

```bash
cp .env.example .env
# 编辑 .env，填入三个 API Key
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 运行

```bash
python main.py
# 或
uvicorn main:app --reload --port 8000
```

打开浏览器访问 http://localhost:8000

---

## API 文档

| 方法   | 路径                      | 说明                     |
|--------|---------------------------|--------------------------|
| POST   | `/api/query`              | 主查询接口               |
| POST   | `/api/clarify`            | 澄清选项处理接口          |
| GET    | `/api/metrics`            | 返回所有指标列表          |
| GET    | `/api/history/{user_id}`  | 用户查询历史             |
| GET    | `/`                       | 返回 Web 主页            |

### POST /api/query

```json
// 请求
{ "query": "今年签发了多少稿件", "user_id": "user_001" }

// 响应（结果）
{
  "type": "result",
  "caliber": "稿件签发通过量",
  "data": [{"signed_count": 342}],
  "sql": "SELECT COUNT(DISTINCT ...) ...",
  "chart": {"chart_type": "card", "card_value": 342},
  "time_range": {"start": "2026-01-01", "end": "2026-04-15"},
  "summary_html": "<div class=\"summary-content\">...</div>"
}

// 响应（需澄清）
{
  "type": "clarify",
  "html": "<div class=\"clarify-container\">...</div>"
}
```

### POST /api/clarify

```json
// 请求
{ "choice": "A", "user_id": "user_001", "original_query": "有多少稿件" }
```

---

## 指标字典扩展指南

在 `metrics/` 目录下新增 YAML 文件，遵循 `article_signed.yaml` 的结构：

```yaml
metric_id: your_metric_id
metric_name: 指标名称
metric_alias: [别名1, 别名2]
definition:
  简述: ...
calculation:
  统计方式: COUNT(DISTINCT ...)
  核心条件: ...
data_source:
  主表: your_table
  sql_template: |
    SELECT ... FROM ... WHERE ...
dimensions: [...]
business_rules: {...}
examples: [...]
```

重启应用后，新指标会自动被向量化并加入检索索引。

---

## 测试

运行本地单元测试（无需 API Key）：

```bash
python -m validator.test_cases
```

---

## 注意事项

1. `.env` 文件不提交，只提交 `.env.example`
2. ChromaDB 向量库首次运行自动初始化（需要 Gemini API Key）
3. 若无 API Key，系统降级为关键词匹配和模板 SQL，仍可本地演示
4. SQLite 数据库（`local_dev.db`）在首次启动时自动创建，含 1000 条模拟数据