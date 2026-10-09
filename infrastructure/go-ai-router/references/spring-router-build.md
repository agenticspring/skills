# spring-router — Build Log & Deep References (2026-08-08..09)

Repo: `https://github.com/agenticspring/spring-router` (PRIVATE, agenticspring account)
Workdir: `/root/spring-router/`, binary `bin/sr`, port **30128** (`127.0.0.1` only)
Version: 0.2.0. Verified working: grok-cli (31 accounts imported from 9Router), Codex (config-only, no accounts), generic custom nodes, streaming, fallback chains, auth.

## Layout

```
cmd/import-9router/   → standalone import tool (superseded by -import flag)
go.mod / main.go / import.go / refresh.go
internal/config/      → YAML config, defaults, OAuth/Transport/Combo structs
internal/gateway/     → Balancer (O(1) healthy pool), HealthChecker
internal/oauth/       → device-code + authorize-code (PKCE) manager
internal/provider/    → interface + registry
internal/provider/grokcli/  → Grok Build transport
internal/provider/openai/   → generic OpenAI-compatible (chat/responses formats)
internal/server/      → chi router, handlers, embedded dashboard (go:embed)
internal/store/       → SQLite (modernc), AES-GCM crypto, Cache wrapper
```

## Config example (grok-cli + codex)

```yaml
server:
  host: 127.0.0.1   # localhost only — NEVER 0.0.0.0 unless user explicitly asks
  port: 30128
  readTimeout: 30
  writeTimeout: 0        # 0 = streaming
  idleTimeout: 120

balancer:
  strategy: round-robin
  maxConsecutiveErrors: 3
  backoffBaseSeconds: 2
  backoffMaxSeconds: 60

refresh:
  intervalSeconds: 30
  leadMs: 300000

providers:
  - id: grok-cli
    alias: gcli
    category: oauth
    strategy: round-robin
    transport:
      baseUrl: https://cli-chat-proxy.grok.com/v1
      format: openai-responses
      forceStream: true
      modelsUrl: https://cli-chat-proxy.grok.com/v1/models
      userUrl: https://cli-chat-proxy.grok.com/v1/user
      tokenAuth: xai-grok-cli
      headers:
        User-Agent: grok-pager/0.2.93 grok-shell/0.2.93 (linux; x86_64)
    oauth:
      clientId: b1a00492-073a-47ea-816f-4c329264a828
      deviceCodeUrl: https://auth.x.ai/oauth2/device/code
      tokenUrl: https://auth.x.ai/oauth2/token
      refreshUrl: https://auth.x.ai/oauth2/token
      scope: "openid profile email offline_access grok-cli:access api:access conversations:read conversations:write"
      referrer: grok-build
      refreshLeadMs: 300000
    models:
      - id: grok-4.5
      - id: grok-4.5-high   (upstream: grok-4.5, effort high)
      - id: grok-4.5-medium (upstream: grok-4.5, effort medium)
      - id: grok-4.5-low    (upstream: grok-4.5, effort low)
      - id: grok-build      (contextLength 500000, maxOutputTokens 64000)

  - id: codex
    alias: cx
    category: oauth
    transport:
      baseUrl: https://chatgpt.com/backend-api/codex/responses
      format: openai-responses
      forceStream: true
      tokenAuth: bearer
      headers:
        originator: codex_cli_rs
        User-Agent: codex_cli_rs/0.136.0
    oauth:
      clientId: app_EMoamEEZ73f0CkXaXp7hrann
      authorizeUrl: https://auth.openai.com/oauth/authorize
      tokenUrl: https://auth.openai.com/oauth/token
      scope: "openid profile email offline_access"
      codeChallengeMethod: S256
      fixedPort: 1455
      callbackPath: /auth/callback
      extraParams:
        id_token_add_organizations: "true"
        codex_cli_simplified_flow: "true"
        originator: codex_cli_rs
    models:
      - id: gpt-5.6-sol
      - id: gpt-5.6-sol-review   (upstream gpt-5.6-sol)
      - id: gpt-5.6-terra
      - id: gpt-5.6-luna
      - id: gpt-5.5
      - id: gpt-5.4
      - id: gpt-5.4-mini
```

## OAuth flows implemented

- **Device code** (grok-cli): POST `deviceCodeUrl` with client_id+scope → user_code/device_code.
  Approve headlessly: POST `https://auth.x.ai/oauth2/device/approve` form `user_code` + `action=allow` with `sso` cookie → 303 means allow. Then poll tokenUrl with `grant_type=urn:ietf:params:oauth:grant-type:device_code`.
- **Authorize code + PKCE S256** (codex): build authorize URL with code_challenge, fixed localhost port (1455) callback; exchange `code` + `code_verifier` at tokenUrl.
- **Refresh**: form-encoded `grant_type=refresh_token`, generic. grok refresh lead 5 min; codex 5 days (long-lived).

## API surface

- `GET /` dashboard (embedded HTML), `/api/status` provider stats
- `GET /v1/models`
- `POST /v1/chat/completions` (stream + non-stream, OpenAI SSE format)
- `POST /admin/oauth/:provider/device-code`, `/poll`, `/authorize-url`, `/exchange`
- `GET/POST/DELETE /admin/nodes` (custom node CRUD)
- `GET/POST/DELETE /admin/providers` (9Router-style API-key provider add)
- `GET/POST/DELETE /admin/keys` (API key management, SHA-256 hashed)
- `GET /health`

Auth: `/v1/*` uses `Authorization: Bearer sr-...`; localhost (127.0.0.1) bypasses. Admin endpoints no auth (localhost-only by default).

## Scale benchmarks (Xeon Gold 6138, Go 1.22)

- Balancer Pick() with 100k connections: **61.86 ns/op, 0 allocs** (O(1))
- Same as 1k conns: 66.26 ns/op → removed the O(n) scan bottleneck
- Pool rebuild (dirty state, 100k): ~18.6 ms — rare, triggered by Report/Reenable
- `TestConcurrentPick100k`: 160k concurrent picks race-free
- Refresh batching: 50/tick, 200ms stagger, retry 60s on failure

## Key event shapes (responses SSE — grok & codex)

```
event: response.created
event: response.output_text.delta
data: {"type":"response.output_text.delta","delta":"144","content_index":0,...}
event: response.output_text.done
event: response.completed
```
Delta is a bare JSON string (`"delta":"text"`). OpenAI chat SSE chunks use `choices[].delta.content`.

## Pitfalls hit live

1. `x-grok-client-version` must be >= 0.1.202 — else `426 Upgrade Required` `{"error":"Your Grok CLI version (0.1.0) is outdated..."}`.
2. Configured `host: 127.0.0.1` — never `0.0.0.0` by default (user explicitly wants localhost-only).
3. Add custom providers to DB (`provider_nodes` table) so they survive restart — not just YAML.
4. API keys SHA-256 hashed at rest — plaintext shown once on creation.