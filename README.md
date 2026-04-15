# 📊 稿件指标智能查询系统

多模型协作（GPT + Gemini + Claude）的稿件指标智能查询 Web 系统，针对新闻媒体生产系统中的稿件指标查询场景。

## 模型分工

| 模型 | 职责 |
|------|------|
| **GPT** | 意图识别、歧义判断、业务逻辑校验、SQL 审查 |
| **Gemini** | UI 设计、图表推荐、自然语言总结渲染 |
| **Claude** | SQL 生成、代码工程实现、代码审查 |
| **交叉验证层** | 多模型互审，保证结果准确性 |

## 目录结构

```
article-metric-agent/
├── main.py                     # FastAPI 入口
├── config.py                   # 三模型 API Keys 及配置
├── requirements.txt            # 依赖列表
├── .env.example                # 环境变量示例
├── gpt/
│   ├── intent_agent.py         # 意图识别 + 歧义判断（GPT）
│   ├── logic_validator.py      # 业务规则校验（GPT）
│   └── anomaly_analyzer.py     # 数据异常归因分析（GPT）
├── claude/
│   ├── sql_generator.py        # SQL 生成（Claude）
│   ├── code_reviewer.py        # 代码/SQL 审查（Claude）
│   └── api_server.py           # FastAPI 路由和接口定义
├── gemini/
│   ├── ui_designer.py          # UI 交互方案生成（Gemini）
│   ├── chart_advisor.py        # 图表类型推荐，返回 ECharts 配置（Gemini）
│   └── summary_renderer.py     # 自然语言结果总结渲染（Gemini）
├── validator/
│   ├── cross_validator.py      # 多模型互审核心逻辑
│   └── test_cases.py           # 自动化测试用例（12个）
├── metrics/
│   └── article_signed.yaml     # 稿件签发通过量完整语义化定义
├── core/
│   ├── llm_client.py           # 三模型统一客户端
│   ├── orchestrator.py         # 总调度，串联所有 Agent
│   ├── metric_store.py         # 指标字典加载与向量检索
│   ├── vector_store.py         # 向量库（chromadb 本地）
│   ├── db_client.py            # SQLite 模拟数据库 + 1000 条模拟数据
│   └── memory_agent.py         # 用户偏好与对话上下文记忆
└── web/
    ├── index.html              # 主页面（对话式交互界面）
    └── static/
        ├── style.css
        └── app.js
```

## 安装步骤

### 1. 克隆仓库

```bash
git clone https://github.com/dfkm18939-ship-it/article-metric-agent.git
cd article-metric-agent
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入三个模型的 API Key：

```
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

## 运行方法

```bash
python main.py
```

或使用 uvicorn：

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

启动后访问 http://localhost:8000

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/query` | 完整查询流程 |
| `POST` | `/api/clarify` | 用户选择澄清选项后继续 |
| `GET` | `/api/metrics` | 返回所有指标列表 |
| `GET` | `/api/history/{user_id}` | 返回用户查询历史 |
| `GET` | `/` | 返回主页面 |

## 运行测试

```bash
python -m validator.test_cases
```

## 查询流程

```
用户提问
  ↓
GPT 意图识别（+ 歧义判断）
  ↓ need_clarify=true → 返回澄清选项
Claude 验证意图可执行性
  ↓
Claude 生成 SQL
  ↓
GPT 验证 SQL 业务逻辑（最多重试 2 次）
  ↓
SQLite 执行查询
  ↓
Gemini 推荐图表 + 生成文字总结
  ↓
GPT 验证展示准确性
  ↓
返回完整结果
```