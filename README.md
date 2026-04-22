# KV-Bridge v1.1

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

**KV-Bridge** is a zero-config, transparent proxy that maximizes LLM prefix cache reuse. It works as a drop-in OpenAI-compatible gateway, intelligently reordering prompts to save up to 90% on input token costs—without touching your existing code.

> **Current Status**: v1.1 – Production‑ready with Tuck gateway integration, zero‑config CLI, request header routing, and built‑in observability.

## ✨ Features

- **🧊 Iceberg Compiler**: Reorders static vs. dynamic content to put cacheable prefixes first.
- **📁 vFD Virtual Files**: Mount local files into prompts with `{@ref: path}` syntax and automatic LRU caching.
- **💰 Economic Profiler**: Only optimizes when it saves real money—never sacrifices quality for marginal gains.
- **🌳 Shadow Radix Tree**: Predicts and tracks commercial API cache hits and TTLs.
- **🔌 Multi‑backend**: Anthropic, OpenAI, vLLM, SGLang, and any OpenAI‑compatible endpoint.
- **🔐 Tuck Gateway Integration**: Route all requests through Tuck for security, audit, and unified key management.
- **⚡ Zero‑config CLI**: Start with `kv-bridge server --anthropic-key xxx`—no `.env` file required.
- **📊 Built‑in Observability**: `kv-bridge stats` shows live cost savings in your terminal. No external DB needed.

## 🚀 Quick Start

### One‑liner (zero config)

```bash
pip install kv-bridge
kv-bridge server --anthropic-key sk-ant-xxx --openai-key sk-xxx
```

That's it. Your gateway is running at `http://localhost:8687`.

### Use with any OpenAI client

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8687/v1",
    api_key="any-value"      # forwarded to backend; use X‑KV‑API‑Key header to override
)

response = client.chat.completions.create(
    model="claude-3-5-sonnet-20241022",          # or gpt-4o, or your vLLM model
    messages=[
        {"role": "system", "content": "You are a senior engineer."},
        {"role": "user", "content": "Review this file: {@ref: ./src/main.py}"}
    ],
    extra_headers={"X-KV-Backend": "anthropic"}   # optional – override default backend
)
```

### Check your savings

```bash
kv-bridge stats
```

```
┌───────────┬───────────┬───────────────┬────────────┐
│ Backend   │ Requests  │ Tokens Saved  │ Cost Saved │
├───────────┼───────────┼───────────────┼────────────┤
│ anthropic │ 1,247     │ 892,000       │ $2.68      │
│ openai    │ 456       │ 234,000       │ $0.70      │
└───────────┴───────────┴───────────────┴────────────┘
```

## 📋 Commands

| Command | Description |
|:---|:---|
| `kv-bridge server` | Start the gateway (supports `--memory-mode`, `--anthropic-key`, `--default-backend`, etc.) |
| `kv-bridge stats` | Display live cache statistics (works in memory or persistent mode) |
| `kv-bridge shadow --analyze <log>` | Analyze historical cache performance from JSON logs |

## 🔧 Configuration

KV-Bridge works with zero configuration. All settings can be passed via CLI, environment variables (`KVB_*`), or a `.env` file.

**Key options:**

| Variable / CLI flag | Default | Description |
|:---|:---|:---|
| `--anthropic-key` / `KVB_ANTHROPIC_API_KEY` | – | Anthropic API key |
| `--openai-key` / `KVB_OPENAI_API_KEY` | – | OpenAI API key |
| `--default-backend` / `KVB_DEFAULT_BACKEND` | `composite` | `anthropic`, `openai`, `vllm`, `sglang` |
| `--memory-mode` / `KVB_MEMORY_MODE` | `false` | Store metrics in memory (no persistent DB) |
| `KVB_TUCK_ENABLED` | `true` | Route through Tuck gateway when available |

## 🧠 Architecture

KV-Bridge operates as a pipeline:

1. **Parse** – Convert messages into typed `PromptBlock`s with volatility scores.
2. **Economic Decision** – Skip reordering if the context is short or savings are too small.
3. **Compile** – Reorder static blocks to the front, inject cache breakpoints, and add attention anchors.
4. **Route** – Forward to the selected backend (or Tuck) with the optimal request shape.
5. **Track** – Record cache hits and update the shadow tree for future predictions.

## 📖 Documentation

- [KV-Bridge Whitepaper](docs/WHITEPAPER.md) – The philosophy and design.
- [KV-Bridge Engineering Manual](docs/ENGINEERING.md) – Detailed specs and AI Coder rules.

## 🤝 AI Coder Collaboration

This project follows a strict **AI Coder Iron Law** checklist to ensure LLM‑generated code stays consistent and testable. Every module is developed test‑first with mock implementations validated before real backend integration.

## 📌 Roadmap

| Milestone | Status |
|:---|:---|
| **v0.1.0** – Core compiler, adapters, shadow tree | ✅ Complete |
| **v1.0.0** – vFD allocator, economic profiler, persistent metrics | ✅ Complete |
| **v1.1.0** – Zero‑config CLI, request header routing, Tuck integration | ✅ Complete |
| **v1.2.0** – Web UI for live monitoring | 🚧 Next |
| **v2.0.0** – Distributed cache sharing across instances | 📅 Planned |

## 📄 License

MIT © [Jason Milk](https://github.com/Jasonmilk)
