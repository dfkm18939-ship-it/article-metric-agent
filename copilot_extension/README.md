# Copilot Extension 注册指南

## 简介

`article-metric-agent` 是一个 GitHub Copilot Extension，让你在 GitHub 任意对话界面中直接查询稿件生产指标：

```
@article-metric-agent 今年签发了多少稿件？
@article-metric-agent 本月各部门签发量对比
@article-metric-agent 上周退稿率异常分析
```

---

## 本地开发测试

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入你的 GitHub Token
```

### 3. 启动本地服务

```bash
python main.py
# 服务运行在 http://localhost:8000
```

### 4. 使用 ngrok 暴露本地端口

```bash
# 安装 ngrok
brew install ngrok   # macOS
# 或访问 https://ngrok.com/download

# 暴露本地 8000 端口
ngrok http 8000
# 记录 ngrok 给出的 https URL，例如 https://abc123.ngrok.io
```

---

## 在 GitHub 注册 Extension

1. 进入 **GitHub Settings → Developer settings → GitHub Apps**
2. 点击 **New GitHub App**，填写：
   - **GitHub App name**: `article-metric-agent`
   - **Homepage URL**: `https://your-ngrok-url`
   - **Callback URL**: `https://your-ngrok-url/copilot/callback`
   - **Webhook URL**: `https://your-ngrok-url/agent`
3. 在 **Copilot** 标签下：
   - 勾选 **Enable Copilot Extension**
   - 类型选择 **Agent**
4. 生成并保存 **Private Key**
5. 点击 **Install App** 安装到你的账号或组织

---

## 环境变量说明

| 变量 | 说明 | 是否必填 |
|------|------|----------|
| `GITHUB_TOKEN` | GitHub Personal Access Token（需要 `copilot` 权限） | ✅ 必填 |
| `SKIP_SIGNATURE_VERIFY` | 本地开发时跳过签名验证（设为 `true`） | 开发时填 |
| `DB_PATH` | SQLite 数据库路径 | 可选 |
| `VECTOR_STORE_PATH` | 向量存储路径 | 可选 |
| `APP_PORT` | 服务端口（默认 8000） | 可选 |

---

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/agent` | POST | Copilot Extension 主入口（SSE 流式响应） |
| `/copilot/health` | GET | 健康检查 |
| `/` | GET | Web UI 界面 |

---

## 生产部署注意事项

1. 生产环境**必须**实现完整的 ECDSA 签名验证（`copilot_extension/middleware.py`）
2. 删除 `SKIP_SIGNATURE_VERIFY=true` 配置
3. 将 `manifest.json` 中的 `your-domain.com` 替换为实际域名
4. 使用 HTTPS（GitHub 要求 Webhook 必须为 HTTPS）
