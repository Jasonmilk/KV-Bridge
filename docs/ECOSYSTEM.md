# KV-Bridge 生态兼容性指南

## 核心理念
KV-Bridge 通过 **OpenAI 兼容 API** 作为唯一集成入口，与任何 AI Agent 框架解耦。框架特定的适配代码作为 **独立示例** 维护在 `community_adapters/` 目录，不作为核心代码的一部分。

## 支持的集成方式

| 方式 | 侵入性 | 说明 |
|:---|:---|:---|
| **OpenAI 兼容端点** | 零侵入 | 将 Agent 的 `base_url` 指向 `http://localhost:8687/v1` |
| **MCP Server（实验性）** | 零侵入 | 将 KV-Bridge 作为 MCP 工具，由支持 MCP 的 Agent 调用 |
| **社区适配器示例** | 参考实现 | 位于 `community_adapters/`，供开发者复制修改 |

## 与 Tuck 的关系
- **KV-Bridge**：上下文内存管理、前缀缓存优化，降低 Token 成本
- **Tuck**：安全审计、API Key 管理、提示词注入防护、最终遏制

两者通过 OpenAI 兼容协议集成，KV-Bridge 在 `tuck_enabled=true` 时将请求转发至 Tuck。

## 框架集成示例

### LangChain
```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="gpt-4o",
    base_url="http://localhost:8687/v1",
    api_key="your_openai_key"
)
```

### LlamaIndex
```python
from llama_index.llms.openai import OpenAI

llm = OpenAI(
    model="gpt-4o",
    api_base="http://localhost:8687/v1",
    api_key="your_openai_key"
)
```

### AutoGPT
修改 `openai_api_base` 配置为 `http://localhost:8687/v1` 即可。
