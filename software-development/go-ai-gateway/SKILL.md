---
name: go-ai-gateway
description: "Go AI router proxies: providers, balancer, OAuth, SSE."
version: 1.0.0
author: spring
license: Private
platforms: [linux]
metadata:
  hermes:
    tags: [go, golang, gateway, router, openai, provider, oauth, balancer, sse, grok, codex]
    related_skills: [go-binary-daemon, grok-account-automation, 9router]
---

# Go AI Gateway Router

Build lightweight config-driven AI router proxies in Go (OpenAI-compatible frontend,
multi-provider upstreams). Proven architecture from `agenticspring/spring-router`
(Phase 1+2: grok-cli 31 accounts + Codex working).

Use when: user asks to build/own an AI router/gateway like 9Router in Go; add a
custom provider (grok-cli, Codex, OpenAI-compatible) to a Go gateway; or wants
a lightweight replacement for a Node AI router.

## Architecture (proven layout)

```
cmd/spring-router/main.go        # config load, registry wiring, graceful shutdown
internal/config/                 # YAML config: server, store, balancer, refresh, providers[]
internal/provider/               # Provider interface + Registry
internal/provider/openai/        # generic config-driven OpenAI-compatible provider
internal/provider/grokcli/       # grok-cli Responses-API provider
internal/gateway/balancer.go     # round-robin / random / least-busy + backoff
internal/oauth/oauth.go          # device-code flow (grok) + authorize-code PKCE (codex)
internal/store/                  # SQLite (modernc.org/sqlite, no CGO) + AES-256-GCM tokens at rest
internal/server/handlers/        # /v1/chat/completions, /v1/models, /admin/oauth/*
cmd/import-9router/              # migrate existing 9Router connections into own store
```

## Provider interface (one file per provider; generic ones are config-only)

Define a Provider interface: `ID()`, `Alias()`, `Models()`, `Transform(req)`,
`RoundTrip(ctx, conn, body)`, `Stream(ctx, conn, body, w)` (SSE), `Refresh(ctx, conn)`,
`HealthCheck(ctx, conn)`. Registry registers by ID + alias so `gcli/grok-4.5`
resolves to the right provider. Adding a new provider = 1 YAML entry + 1 Go file
(or config-only for OpenAI-compatible endpoints).

## Balancer + backoff lessons

- Connection struct carries runtime state: `CooldownUntil`, `RateLimitedUntil`,
  `ConsecutiveErrors`, `InFlight` (atomic). A channel-based lock (`make(chan struct{},1)`)
  avoids `sync.Mutex` on the hot path.
- Pick strategy filters healthy (active && cooldown passed && errors < max), then
  round-robin via `atomic counter % len`; least-busy sorts by InFlight.
- 429 → RateLimitedUntil; 5xx → CooldownUntil; > max consecutive errors → auto-disable;
  re-enable on successful health check.

## OAuth flows (both proven)

- **Device code (grok/xAI)**: POST deviceCodeUrl with client_id+scope → poll tokenUrl
  with `grant_type=urn:ietf:params:oauth:grant-type:device_code`. Refresh via
  `grant_type=refresh_token&refresh_token=...&client_id=...` (form-encoded).
- **Authorization code + PKCE (Codex/OpenAI)**: build authorize URL with
  `code_challenge=S256(verifier)`, `redirect_uri=http://localhost:{fixedPort}{callbackPath}`,
  then exchange `code`+`code_verifier`. Codex fixedPort 1455, callback `/auth/callback`.
- Refresh scheduler: tick ~30s, refresh when `now >= ExpiresAt - RefreshLead`
  (lead 300s grok, 5 days Codex — read provider's `refreshLeadMs`).

## SSE transform: grok Responses → OpenAI chat.completions

Grok Responses API streams `event: response.*` + `data: {...}`. Map:

- `response.created` / `response.in_progress` → ignore (or emit role chunk)
- `response.output_text.delta` → `data: {"choices":[{"delta":{"content":"..."}}]}`
  - **delta is a plain STRING field, NOT an object** — parsing it as object yields empty deltas.
- `response.completed` / `response.done` → emit `finish_reason:"stop"` then `data: [DONE]`

Non-stream: grok returns `output[].content[].text` (type `output_text`); id in
`response.id`, usage in `usage.{input_tokens,output_tokens}`.

## Critical upstream gates (pitfalls)

1. **xAI Grok CLI version gate — HTTP 426.** Default Go headers trigger
   `{"error":"Your Grok CLI version (X) is outdated. Please update to version 0.1.202 or later"}`
   from `cli-chat-proxy.grok.com/v1/responses`. Fix: send `x-grok-client-version: 0.1.202`
   (9router uses 0.2.93) + `x-xai-token-auth: xai-grok-cli` + `x-grok-client-identifier`.
   Wrong Accept/Content-Type also gives 426 — always set both to `application/json`.
2. **Grok free-tier accounts serve DOWNGRADED models (bfs flag)** — see
   `grok-account-automation` → `references/grok-bfs-flag.md`. Router can route flagged
   accounts but don't sell as full-quality 4.5. Probe model self-ID before trusting.
3. **Header naming**: transport uses `Authorization: Bearer {accessToken}`;
   `x-xai-token-auth: xai-grok-cli` is a separate identifying header, not the auth value.

## Codex provider (reverse-engineered, verified config)

Provider `codex` (alias `cx`) from 9Router v0.5.45:

- Base `https://chatgpt.com/backend-api/codex/responses`, format `openai-responses`,
  headers `{originator: codex_cli_rs}`, `User-Agent: codex_cli_rs/0.136.0`
- OAuth clientId `app_EMoamEEZ73f0CkXaXp7hrann`, authorizeUrl
  `https://auth.openai.com/oauth/authorize`, tokenUrl
  `https://auth.openai.com/oauth/token`, scope `openid profile email offline_access`
- PKCE S256, fixedPort 1455, callback `/auth/callback`
- extraParams: `id_token_add_organizations=true`, `codex_cli_simplified_flow=true`,
  `originator=codex_cli_rs`; refreshLeadMs 432000000 (5 days), maxRefreshAgeMs 691200000 (8 days)
- models: `gpt-5.6-sol`, `-terra`, `-luna`, `gpt-5.5`, `gpt-5.4`, `gpt-5.4-mini`

## Import from 9Router (reuse existing connections)

Read the running 9Router SQLite `providerConnections.data` JSON blobs, write into own
store. This is how `spring-router` inherited 31 grok-cli connections without re-auth.
See `references/spring-router-import.md` and `cmd/import-9router/` in the repo.

## Storing & running

- SQLite: `modernc.org/sqlite` (pure Go, no CGO — static build on Linux). Encrypt
  tokens at rest with AES-256-GCM; master key from env or `master.key` file (chmod 600).
- Run as background daemon via `terminal(background=true)` + `run.sh`, NOT `nohup &`
  (see `go-binary-daemon` lifecycle-guard pitfall).

## Verification checklist (before declaring a provider works)

1. Non-stream chat returns real answer text (not empty msg).
2. Stream ends with `finish_reason:stop` then `data: [DONE]`; deltas contain text.
3. `GET /v1/models` lists each provider's models as `alias/model`.
4. Round-robin across connections actually distributes (check via logs/usage).
5. Token refresh fires before expiry (`refreshing token` log).

## References

- `references/spring-router-import.md` — importing 9Router connections, store schema, AES-GCM crypto helpers
- `references/9router-provider-recon.md` — how to reverse a provider config from 9Router JS bundles (grok-cli + codex + generic patterns)