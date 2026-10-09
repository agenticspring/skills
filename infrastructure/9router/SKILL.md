---
name: 9router
description: 9Router AI Router & Token Saver — manage providers, API keys, combos, tunnel, CLI tools integration. Local proxy on port 20128 serving AI models to Hermes and other CLI tools.
version: 1.0.0
author: spring
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [9router, AI-Router, Token-Saver, Proxy, Providers, Xiaomi, MiMo]
    related_skills: [hermes-agent]
---

# 9Router — AI Router & Token Saver

## ⚠️ CRITICAL WARNING

**9Router runs on localhost:20128 and serves the model that Hermes (spring 🌸) uses. If 9Router dies, spring dies. NEVER restart, kill, or modify the 9Router process. All operations must be READ-ONLY unless explicitly instructed by the user.**

## Overview

9Router is a Node.js AI router proxy that connects to 40+ AI providers and 100+ models. It provides:
- **RTK Token Saver** — auto-compress tool output, save 20-40% tokens
- **Auto Fallback** — chain models, auto-switch on failure
- **Multi-Account** — round-robin between accounts per provider
- **Dashboard** — Web UI at http://localhost:20128/dashboard
- **CLI Tools** — auto-configure Claude Code, Codex, OpenCode, etc.
- **Tunnel** — expose to internet via tunnel.9router.com

## Current Setup (as of 2026-07-06)

| Detail | Value |
|--------|-------|
| Version | 0.5.18 |
| Install Path | /usr/lib/node_modules/9router/ |
| Data Dir | ~/.9router/ |
| Port | 20128 |
| Process | /usr/bin/node /usr/lib/node_modules/9router/cli.js --tray --skip-update -p 20128 |
| Database | ~/.9router/db/data.sqlite |
| Active Model | mimo/mimo-v2.5-pro (Xiaomi MiMo) |

## Architecture

```
Client (Hermes/CLI)
    │
    ▼
9Router (localhost:20128)
    │
    ├── RTK Compress (tool_result)
    ├── Provider Router (pick best)
    ├── Fallback Chain (combos)
    │
    ▼
Provider API (Xiaomi/Anthropic/OpenAI/etc)
```

## File Structure

```
~/.9router/
├── auth/cli-secret          # CLI auth secret (0600)
├── bin/                     # Binary files
├── db/
│   ├── data.sqlite          # Main database
│   ├── data.sqlite-shm      # Shared memory
│   ├── data.sqlite-wal      # Write-ahead log
│   └── backups/             # DB backups
├── jwt-secret               # JWT signing secret
├── machine-id               # Unique machine ID
├── logs/                    # App logs
├── mitm/                    # MITM proxy data
└── runtime/                 # Runtime data
```

## Providers (50+ Total)

From source code analysis, 9Router supports these providers:

### OAuth Providers (need browser login)

| Alias | Provider | ID |
|-------|----------|-----|
| cc | Claude Code | claude |
| cx | OpenAI Codex | codex |
| gc | Gemini CLI | gemini-cli |
| gh | GitHub Copilot | github |
| ag | Antigravity | antigravity |
| if | iFlow AI | iflow |
| qw | Qwen Code | qwen |
| kr | Kiro AI | kiro |
| cl | Cline | cline |
| clinepass | ClinePass | clinepass |
| cbcn | CodeBuddy CN | codebuddy-cn |
| xai | xAI (Grok) | xai |

### API Key Providers

| ID | Alias | Display Name |
|----|-------|-------------|
| openai | openai | OpenAI |
| anthropic | anthropic | Anthropic |
| gemini | gemini | Gemini |
| openrouter | openrouter | OpenRouter |
| glm | glm | GLM Coding |
| minimax | minimax | Minimax Coding |
| kimi | kimi | Kimi Coding |
| xiaomi-mimo | mimo | Xiaomi MiMo |
| xiaomi-tokenplan | xmtp | Xiaomi MiMo (Token Plan) |
| alicode-intl | alicode-intl | Alibaba Intl |
| alicode | alicode | Alibaba |
| blackbox | bb | Blackbox AI |
| cerebras | cb | Cerebras |
| chutes | ch | Chutes AI |
| cloudflare-ai | cf | Cloudflare |
| ollama | ollama | Ollama Cloud |
| opencode-go | ocg | OpenCode Go |
| perplexity | pplx | Perplexity |
| siliconflow | siliconflow | SiliconFlow |
| together | tg | Together AI |
| venice | vn | Venice AI |
| vercel-ai-gateway | vercel | Vercel AI Gateway |
| vertex | vx | Vertex AI |
| vertex-partner | vp | Vertex Partner |
| volcengine-ark | ark | Volcengine Ark |
| voyage-ai | voyage | Voyage AI |
| azure | azure | Azure OpenAI |
| aws-polly | polly | AWS Polly |
| byteplus | bpm | BytePlus ModelArk |
| deepseek | deepseek | DeepSeek |
| mistral | mistral | Mistral |
| groq | groq | Groq |

### Free Providers (no auth needed)

| ID | Alias | Display Name |
|----|-------|-------------|
| opencode | oc | OpenCode Free |
| qoder | qd | Qoder |
| searxng | searxng | SearXNG |

### Web/Cookie Providers

| ID | Alias | Display Name |
|----|-------|-------------|
| perplexity-web | pw | Perplexity Web |

### Image Providers

| ID | Display Name |
|----|-------------|
| black-forest-labs | Black Forest Labs (FLUX) |
| recraft | Recraft |
| runwayml | Runway ML |
| stability-ai | Stability AI |
| sdwebui | SD WebUI |
| topaz | Topaz |

### Audio/TTS Providers

| ID | Display Name |
|----|-------------|
| assemblyai | AssemblyAI (STT) |
| cartesia | Cartesia (TTS) |
| playht | PlayHT (TTS) |
| tortoise | Tortoise TTS |

### Search Providers

| ID | Display Name |
|----|-------------|
| brave-search | Brave Search |
| searchapi | SearchAPI |
| serper | Serper |
| tavily | Tavily |
| youcom | You.com Search |

### Summary

| Category | Count |
|----------|-------|
| OAuth | ~12 |
| API Key | ~30+ |
| Free | ~3 |
| Image | ~6 |
| Audio/TTS | ~4 |
| Search | ~5 |
| **TOTAL** | **50+** |

### Xiaomi Token Plan (NOT YET ADDED)

| Detail | Value |
|--------|-------|
| Provider ID | `xiaomi-tokenplan` |
| Alias | `xmtp` |
| Display Name | Xiaomi MiMo (Token Plan) |
| API Key Format | `tp-xxx` (prefix tp-) |
| Auth Type | API Key |
| Default Region | Singapore (sgp) |
| Regions | 🇸🇬 SGP, 🇨🇳 CN, 🇳🇱 AMS |
| Endpoint SGP | `https://token-plan-sgp.xiaomimimo.com/v1` |
| Endpoint CN | `https://token-plan-cn.xiaomimimo.com/v1` |
| Endpoint AMS | `https://token-plan-ams.xiaomimimo.com/v1` |

Models (9):
- `mimo-v2.5-pro` — MiMo V2.5 Pro
- `mimo-v2.5-pro-claude` — MiMo V2.5 Pro (Claude Native, targetFormat: claude)
- `mimo-v2.5` — MiMo V2.5
- `mimo-v2-pro` — MiMo V2 Pro
**Adding Token Plan provider via API:**
```bash
MACHINE_ID=$(cat ~/.9router/machine-id)
CLI_SECRET=$(cat ~/.9router/auth/cli-secret)
CLI_TOKEN=$(echo -n "${MACHINE_ID}9r-cli-auth${CLI_SECRET}" | sha256sum | cut -c1-16)

curl -X POST http://localhost:20128/api/providers \
  -H "Content-Type: application/json" \
  -H "x-9r-cli-token: $CLI_TOKEN" \
  -d '{
    "provider": "xiaomi-tokenplan",
    "name": "MiMo Token Plan",
    "apiKey": "tp-YOUR_KEY_HERE",
    "providerSpecificData": { "region": "sgp" }
  }'
```

**Adding Token Plan provider via API:**
```bash
MACHINE_ID=$(cat ~/.9router/machine-id)
CLI_SECRET=$(cat ~/.9router/auth/cli-secret)
CLI_TOKEN=$(echo -n "${MACHINE_ID}9r-cli-auth${CLI_SECRET}" | sha256sum | cut -c1-16)

curl -X POST http://localhost:20128/api/providers \
  -H "Content-Type: application/json" \
  -H "x-9r-cli-token: $CLI_TOKEN" \
  -d '{
    "provider": "xiaomi-tokenplan",
    "name": "MiMo Token Plan",
    "apiKey": "tp-YOUR_KEY_HERE",
    "providerSpecificData": { "region": "sgp" }
  }'
```

## API Endpoints (READ-ONLY Reference)

### Models
```
GET /v1/models                    # List available models
POST /v1/chat/completions         # Chat completion (OpenAI compatible)
```

### Providers
```
GET  /api/providers               # List all providers
GET  /api/providers/:id           # Get provider by ID
POST /api/providers               # Add provider
PUT  /api/providers/:id           # Update provider
DELETE /api/providers/:id         # Delete provider
POST /api/providers/:id/test      # Test connection
GET  /api/providers/:id/models    # Get provider models
```

### API Keys
```
GET    /api/keys                  # List API keys
POST   /api/keys                  # Create API key
DELETE /api/keys/:id              # Delete API key
```

### Combos (Model Chains)
```
GET    /api/combos                # List combos
GET    /api/combos/:id            # Get combo
POST   /api/combos                # Create combo
PUT    /api/combos/:id            # Update combo
DELETE /api/combos/:id            # Delete combo
```

### Settings
```
GET   /api/settings               # Get settings
PATCH /api/settings               # Update settings
```

### Tunnel
```
GET  /api/tunnel/status           # Tunnel status
POST /api/tunnel/enable           # Enable tunnel
POST /api/tunnel/disable          # Disable tunnel
```

### CLI Tools
```
GET    /api/cli-tools/:tool-settings    # Get tool config
POST   /api/cli-tools/:tool-settings    # Apply tool config
DELETE /api/cli-tools/:tool-settings    # Reset tool config
```

### Provider Nodes (Custom)
```
GET    /api/provider-nodes        # List custom nodes
POST   /api/provider-nodes        # Add custom node
PUT    /api/provider-nodes/:id    # Update node
DELETE /api/provider-nodes/:id    # Delete node
POST   /api/provider-nodes/validate  # Validate node
```

### OAuth
```
GET  /api/oauth/:provider/authorize    # Get auth URL
POST /api/oauth/:provider/exchange     # Exchange code
GET  /api/oauth/:provider/device-code  # Device code flow
POST /api/oauth/:provider/poll         # Poll token
```

### Auth
```
POST /api/auth/reset-password    # Reset dashboard password
```

## CLI Authentication

All API calls need `x-9r-cli-token` header. Use the helper script to generate it:

```bash
# Quick one-liner
source ~/.hermes/skills/infrastructure/9router/scripts/get-cli-token.sh

# Or manually:
MACHINE_ID=$(cat ~/.9router/machine-id)
CLI_SECRET=$(cat ~/.9router/auth/cli-secret)
CLI_TOKEN=$(echo -n "${MACHINE_ID}9r-cli-auth${CLI_SECRET}" | sha256sum | cut -c1-16)
```

```javascript
// In code:
token = SHA256(machineId + "9r-cli-auth" + cliSecret).substring(0, 16)
```

- machineId: ~/.9router/machine-id
- cliSecret: ~/.9router/auth/cli-secret
- Script: `scripts/get-cli-token.sh`

## Adding Providers via API

### API Key Provider
```bash
curl -X POST http://localhost:20128/api/providers \
  -H "Content-Type: application/json" \
  -H "x-9r-cli-token: <token>" \
  -d '{"provider": "openrouter", "name": "My OpenRouter", "apiKey": "***"}'
```

### Custom Provider Node (Two-Step Process)

**Step 1: Create the node** (defines endpoint + type)
```bash
curl -X POST http://localhost:20128/api/provider-nodes \
  -H "Content-Type: application/json" \
  -H "x-9r-cli-token: $CLI_TOKEN" \
  -d '{
    "name": "My Provider",
    "prefix": "myprefix",
    "apiType": "chat",
    "baseUrl": "https://api.example.com/v1",
    "type": "openai-compatible"
  }'
```

Required fields:
- `name` — display name
- `prefix` — model ID prefix (e.g., models become `prefix/model-name`)
- `apiType` — `"chat"` or `"responses"`
- `baseUrl` — API endpoint
- `type` — `"openai-compatible"` (default), `"anthropic-compatible"`, or `"custom-embedding"`

**Step 2: Add API key connections** (use the node ID from step 1)
```bash
NODE_ID="openai-compatible-chat-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
curl -X POST http://localhost:20128/api/providers \
  -H "Content-Type: application/json" \
  -H "x-9r-cli-token: $CLI_TOKEN" \
  -d "{\"provider\": \"$NODE_ID\", \"name\": \"key-1\", \"apiKey\": \"***\"}"
```

Multiple keys CAN be added to the same node (round-robin rotation works).

### Bulk Add Keys to Custom Provider

For adding hundreds/thousands of keys, use a shell script:
```bash
NODE_ID="openai-compatible-chat-xxx..."
while IFS= read -r key; do
  curl -s -X POST http://localhost:20128/api/providers \
    -H "Content-Type: application/json" \
    -H "x-9r-cli-token: $CLI_TOKEN" \
    -d "{\"provider\": \"$NODE_ID\", \"name\": \"key-$COUNT\", \"apiKey\": \"$key\"}"
done < keys.txt
```

Performance: ~1000 keys/minute with 5s timeout per request.

## Token Saver

### RTK (Real-Time Kompression)
- Auto-compress tool_result (git diff, grep, ls, etc.)
- Saves 20-40% tokens per request
- ON by default
- Toggle: PATCH /api/settings { rtkEnabled: true/false }

### Headroom
- Advanced optimization
- Default URL: http://localhost:8787
- Toggle: PATCH /api/settings { headroomEnabled: true/false }

## Combos (Model Chains)

Model A → Model B → Model C
- Auto-fallback if Model A fails/rate-limited
- Use cases: different models for different tasks
- Managed via /api/combos

## Tunnel

Expose 9Router to internet:
- URL format: https://<short-id>.tunnel.9router.com/v1
- Enable: POST /api/tunnel/enable
- Disable: POST /api/tunnel/disable
- Status: GET /api/tunnel/status

## CLI Tools Integration

| Tool | Config Method |
|------|---------------|
| Claude Code | ANTHROPIC_BASE_URL + ANTHROPIC_AUTH_TOKEN env vars |
| Codex CLI | TOML config (base_url, api_key, model) |
| Factory Droid | Custom model config |
| Open Claw | Provider config in settings |
| OpenCode | baseURL, apiKey, models config |

## Dashboard

- URL: http://localhost:20128/dashboard
- Default password: 123456
- Features: manage providers, API keys, combos, settings, tunnel
- Auth mode: password (default)

## Security

| Component | Detail |
|-----------|--------|
| Machine ID | Unique per machine |
| CLI Secret | Random 32-byte hex (0600 permissions) |
| CLI Token | SHA256 hash, 16 chars |
| JWT Secret | Server-side signing |
| Dashboard Auth | Password-based |

## Tech Stack

| Component | Technology |
|-----------|------------|
| Runtime | Node.js |
| Web Framework | Next.js 16.1.6 |
| UI | React 19.2.4, Tailwind CSS 4 |
| Database | SQLite (better-sqlite3 + sql.js fallback) |
| Auth | jose (JWT), bcryptjs |
| Charts | Recharts |
| Code Editor | Monaco Editor |
| HTTP Client | undici |
| State | Zustand |

## Commands

```bash
# Start 9Router
9router                    # Default settings
9router --port 8080        # Custom port
9router --no-browser       # Don't open browser
9router --skip-update      # Skip update check

# Dashboard
http://localhost:20128/dashboard

# API endpoint
http://localhost:20128/v1
```

## Current Providers on This VPS (as of 2026-07-07)

| Provider | Type | Keys | Status |
|----------|------|------|--------|
| Xiaomi MiMo | API Key | 320 | ✅ Active |
| b.ai (custom) | Custom Node | 1,912 | ✅ Active |

**Total: 2,232 API keys across 2 providers.**

### b.ai Custom Provider

- **Node ID**: `openai-compatible-chat-fa24d9d0-a96b-407f-9d52-33b5d9c5ce35`
- **Prefix**: `bai`
- **Base URL**: `https://api.b.ai/v1`
- **API Type**: `chat`
- **Models**: GPT-5.5, Claude Opus 4.8, DeepSeek V4, Gemini 3.5 Flash, Kimi K2.5, GLM 5.2, MiniMax M3, etc.
- **API Key Format**: `sk-xxx` (51 chars, various prefixes: sk-2, sk-3, sk-4, sk-5, sk-6)
- **Total Keys**: 1,912 (harvested from b.ai farmer)

## Pitfalls

1. **NEVER kill/restart 9Router** — Hermes depends on it
2. **OAuth providers need browser** — can't auto-login from agent
3. **Rate limits** — each provider has its own limits
4. **Token expiry** — OAuth tokens expire, need re-auth
5. **SQLite locks** — don't modify DB directly while 9Router runs
6. **Port conflict** — if 20128 is taken, 9Router won't start
7. **Dashboard password** — default is 123456, should be changed
8. **Custom node creation requires `apiType`** — must be `"chat"` or `"responses"`, not optional
9. **Custom node IDs are auto-generated** — format: `openai-compatible-chat-{uuid}` or `anthropic-compatible-{uuid}`
10. **Provider connections ≠ provider nodes** — nodes define endpoints, connections hold API keys. Two-step process.
11. **CLI token can change** — if 9Router regenerates machine-id or cli-secret, re-run get-cli-token.sh
12. **Windows line endings (`\r`) corrupt API keys** — Files from Windows have `\r\n`. When reading keys line-by-line, the `\r` gets appended silently, causing `"Failed to create provider"`. Always strip first: `sed -i 's/\r//g' file.txt`. Verify with `cat -A file | head -3` (look for `^M`).
13. **Last line without newline** — Bulk key files may lack trailing newline, causing last key to be skipped in `while read` loops. Fix: `tail -c 1 file | grep -q '^$' || echo "" >> file`
14. **Multiple API keys per custom node works** — Despite earlier reports, v0.5.18 supports multiple connections to one custom node. Create node once, add N keys.
15. **Bulk add performance** — ~1000 keys/min with 5s timeout. Use `screen` for 500+ keys.
16. **API key file format** — Keys from different sources have different formats: b.ai keys are `sk-xxx` (51 chars), Xiaomi MiMo keys are `sk-sxxx` (51 chars), Token Plan keys are `tp-xxx`. Always verify key format before bulk adding.
17. **Provider test status** — New connections show `unknown` or `unavailable` until first use. This is normal — status updates to `active` after first successful API call through 9Router.

## Links

- Website: https://9router.com
- GitHub: https://github.com/decolua/9router
- NPM: https://www.npmjs.com/package/9router
- Docker: https://hub.docker.com/r/decolua/9router
