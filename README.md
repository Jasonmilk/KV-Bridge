# KV-Bridge: Context Memory Allocator for AI Agents

KV-Bridge is a transparent proxy that optimizes LLM prompt caching by reordering static content to maximize prefix cache reuse, supporting multiple backends including Anthropic, OpenAI, vLLM, and SGLang.

## Features

- 🧊 **Iceberg Compiler**: Reorders prompt blocks by volatility to maximize cache hits
- 📁 **vFD Virtual Files**: Mount local files into prompts with automatic LRU caching
- 💰 **Economic Profiler**: Only optimizes when it's actually worth it, no quality tradeoffs
- 🌳 **Shadow Radix Tree**: Predicts cache hits and tracks TTL for commercial APIs
- 🔌 **Multi-backend Support**: Works with Anthropic, OpenAI, vLLM, and SGLang
- 📊 **OpenAI-compatible API**: Drop-in replacement for existing OpenAI clients

## Installation

```bash
# Clone the repository
git clone https://github.com/Jasonmilk/KV-Bridge.git
cd KV-Bridge

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys
```

## Quick Start

### Start the server

```bash
kv-bridge server
```

### Use with OpenAI client

Just point your OpenAI client to the KV-Bridge server:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8687/v1",
    api_key="your_api_key"  # This will be forwarded to the actual backend
)

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello! Analyze this file: {@ref: ./my_code.py}"}
    ]
)
```

## Commands

- `kv-bridge server`: Start the gateway server
- `kv-bridge stats`: Show cache statistics
- `kv-bridge shadow --analyze logs.json`: Analyze historical cache performance

## Architecture

KV-Bridge works in 5 steps:

1. **Parse**: Convert incoming messages into typed `PromptBlock`s with volatility scores
2. **Economic Decision**: Decide if reordering is worth it based on context size and potential savings
3. **Compile**: Reorder static blocks to the front, inject cache breakpoints
4. **Route**: Forward the optimized request to your chosen LLM backend
5. **Track**: Record cache hits to improve future predictions

## License

MIT
