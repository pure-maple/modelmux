# 三大 CLI 第三方模型兼容性深度分析

## 协议兼容性总览

| 维度 | Claude Code | Codex CLI | Gemini CLI |
|------|------------|-----------|------------|
| **原生协议** | Anthropic Messages API | OpenAI Responses/Chat API | Google GenAI API |
| **自定义端点** | `ANTHROPIC_BASE_URL` | `base_url` in config.toml | `GOOGLE_GEMINI_BASE_URL` |
| **API 密钥** | `ANTHROPIC_AUTH_TOKEN` | `<PROVIDER>_API_KEY` / auth.json | `GEMINI_API_KEY` |
| **模型覆盖** | `ANTHROPIC_MODEL` + 分层变量 | `model` in config / `--model` | `GEMINI_MODEL` / `--model` |
| **多 Provider 设计** | 无（靠环境变量覆盖） | **有**（内置 Provider 注册表） | 无（仅 Google GenAI） |
| **OpenAI 兼容** | 不兼容（需代理转换） | **原生支持** | 不兼容 |
| **第三方灵活度** | ★★★☆☆ | ★★★★★ | ★★☆☆☆ |

## Claude Code 第三方模型接入

### 配置方式

通过 `~/.claude/settings.json` 的 `env` 块或 shell 环境变量：

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
    "ANTHROPIC_AUTH_TOKEN": "<api-key>",
    "ANTHROPIC_MODEL": "DeepSeek-V3.2",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "DeepSeek-V3.2",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "DeepSeek-V3.2",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "DeepSeek-V3.2"
  }
}
```

### 已知兼容的第三方端点

| Provider | Base URL | 备注 |
|----------|---------|------|
| DeepSeek | `https://api.deepseek.com/anthropic` | 原生 Anthropic 兼容 |
| 智谱 GLM | `https://open.bigmodel.cn/api/anthropic` | 原生 Anthropic 兼容 |
| 阿里百炼 | `https://dashscope.aliyuncs.com/apps/anthropic` | 原生 Anthropic 兼容 |
| Kimi | 需确认 | 部分 Anthropic 兼容 |
| AWS Bedrock | 需 `CLAUDE_CODE_USE_BEDROCK=1` | 官方支持 |
| Azure Foundry | 需 `CLAUDE_CODE_USE_FOUNDRY=1` | 官方支持 |
| Google Vertex | 需 `CLAUDE_CODE_USE_VERTEX=1` | 官方支持 |

### 限制

- **只支持 Anthropic Messages API 协议**
- 纯 OpenAI 兼容端点（如 Qwen via OpenAI format）需要代理转换
- 没有内置的 Provider 管理机制，全靠环境变量覆盖
- 切换 Provider 需要修改多个环境变量

## Codex CLI 第三方模型接入

### 配置方式

`~/.codex/config.toml` 内置 Provider 注册表：

```toml
model_provider = "custom_provider"
model = "qwen3-coder"

[model_providers.custom_provider]
name = "Alibaba DashScope"
base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
wire_api = "chat"          # "responses" (OpenAI Responses) 或 "chat" (Chat Completions)
requires_openai_auth = true
env_key = "DASHSCOPE_API_KEY"
```

### 内置 Provider

`openai`, `openrouter`, `azure`, `gemini`, `ollama`, `mistral`, `deepseek`, `xai`, `groq`, `arceeai`

### 优势

- **最灵活的第三方支持**——专门设计了可插拔 Provider 架构
- 支持两种 API 协议：OpenAI Responses API 和 Chat Completions
- 几乎所有 OpenAI 兼容端点都能直接接入
- Profile 机制允许保存多套 Provider 配置快速切换

### 限制

- 不支持 Anthropic Messages API 协议（不能直接调用 Claude 模型，除非通过 OpenAI 兼容网关）

## Gemini CLI 第三方模型接入

### 配置方式

通过 `~/.gemini/.env` 或环境变量：

```bash
GOOGLE_GEMINI_BASE_URL="https://your-relay.com"
GEMINI_API_KEY="your-api-key"
GEMINI_MODEL="gemini-3-pro"
```

### 限制

- **仅支持 Google GenAI API 协议**——最封闭
- 不能直接使用非 Gemini 模型
- 中继服务必须提供 GenAI 兼容接口
- 无 Provider 注册表，仅靠环境变量
- 实验性 gemmaModelRouter 仅支持本地 Gemma 模型

### 可用中继

cc-switch 中记录的 Gemini 中继服务：PackyCode、Cubence、AIGoCode 等

## cc-switch 架构分析

### 定位

cc-switch 是**配置管理工具**（切换 CLI 连接的模型/Provider），而我们的 modelmux 是**任务编排工具**（跨 CLI 分发任务）。两者互补。

### 核心机制

1. **直接写入 CLI 原生配置文件**：
   - Claude Code → `settings.json` env 块
   - Codex CLI → `auth.json` + `config.toml`
   - Gemini CLI → `.env` 文件

2. **本地代理服务器**（Rust 实现）：
   - Anthropic ↔ OpenAI API 格式互转
   - 自动故障转移 + 断路器
   - Provider 健康监控
   - 热切换（不需要重启 CLI）

3. **50+ 预设 Provider 配置**：一键切换到 DeepSeek、智谱、Ollama 等

### 对我们的启发

- **不要重复 cc-switch 的 GUI 配置管理**——那是它的领域
- **可以借鉴 env 注入机制**——在 subprocess 启动时注入环境变量，实现按任务级别的 Provider 切换
- **可以与 cc-switch 共存**——用户用 cc-switch 管理全局 Provider，用 modelmux 管理任务级别的编排
