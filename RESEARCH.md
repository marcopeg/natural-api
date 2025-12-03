

# Codex CLI Research Summary

## 1. Recap of the conversation

### 1.1 Current setup
- Using OpenAI Codex CLI on macOS.
- Authentication currently via ChatGPT Plus browser OAuth.
- You built a Python FastAPI wrapper that:
  - Exposes a local HTTP server.
  - Calls Codex CLI behind the scenes.
  - Returns Codex output to the client.
- Fully working locally.

### 1.2 Problems you wanted to solve
1. **Headless VPS support** — No browser available for OAuth flow.
2. **Codex authentication** — Need confirmation that Codex can use API keys instead of OAuth.
3. **Dockerization** — Want to run Codex CLI + FastAPI inside one container using environment variables.
4. **Custom endpoints/providers** — Want to direct Codex CLI to OpenRouter, local LLMs, or custom API base URLs.
5. **Existing projects** — Wanted real-world precedents/tutorials and validated sources.

---

## 2. Solutions & key points

### 2.1 Codex CLI *can* use OpenAI API keys (no browser required)
Codex supports:
- `OPENAI_API_KEY` environment variable.
- `preferred_auth_method = "apikey"` in `~/.codex/config.toml`.
- Non-interactive authentication (stdin).

This is officially documented.

### 2.2 How Codex reads API keys
- Reads from the environment via `OPENAI_API_KEY`.
- Controlled via:
  ```
  ~/.codex/config.toml
  preferred_auth_method = "apikey"
  ```
- Works on VPS and inside Docker.

### 2.3 Codex inside Docker
Confirmed by multiple existing implementations:
- Mount volumes for:
  - Codex config (`~/.codex`)
  - Workspace
- Inject API keys via `ENV OPENAI_API_KEY=...`
- Run Codex in non-interactive mode via:
  ```
  codex exec --json "prompt here"
  ```

### 2.4 Changing Codex backend (OpenRouter, Ollama, local models)
Codex supports custom providers via `config.toml`:

```
[model_providers.myprovider]
base_url = "http://localhost:11434/v1"
env_key = "MY_API_KEY"
wire_api = "chat"
```

Supports:
- OpenAI alternatives
- OpenRouter
- Ollama
- Local LLMs

Also supports `--oss` for quick local use.

### 2.5 Existing near-identical projects
#### FastAPI wrappers:
- Codex-Wrapper: FastAPI → Codex CLI → OpenAI-compatible API.

#### Codex in Docker:
- Diatonic-AI/codex-cli-docker-mcp
- DeepBlueDynamics/codex-container
- diablotin74/codex-cli (Docker Hub)
- benyamin/codex-sandbox (Docker Hub)

#### Codex-like OSS tools:
- Open Codex (multi-provider, local LLMs)
- Forks that support OpenAI, Gemini, OpenRouter, Ollama.

---

## 3. Curated sources

### 3.1 Documentation
- Codex quickstart (API key usage)
- Codex CLI reference
- Codex configuration (model providers)
- MCP integration documentation
- OpenAI API key docs
- Codex GitHub repository

### 3.2 Tutorials
- DataCamp Codex CLI tutorial
- Analytics Vidhya: install/use Codex locally
- Skywork AI: comprehensive Codex CLI guide
- ResearchAudio: deep-dive on Codex automated workflows
- Docker installation tutorials for Codex

### 3.3 Existing repository examples
- Codex-Wrapper (FastAPI around Codex)
- codex-cli-docker-mcp
- codex-container
- Open Codex (local-first Codex-like CLI)
- Codex-related MCP utilities

---

This document summarizes the full conversation and provides verified sources, patterns, and project references related to Codex CLI authentication, containerization, custom providers, and FastAPI integration.