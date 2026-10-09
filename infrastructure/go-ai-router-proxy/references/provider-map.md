# 9Router Provider Definitions (reverse-engineered 2026-08-09)

Exact transport + OAuth params extracted from 9Router Next.js build chunks
(`/usr/lib/node_modules/9router/app/.next-cli-build/static/chunks/`). Use when adding
providers to spring-router or replicating 9Router behavior.

## grok-cli (gcli / alias grok-build, gb)

```js
{
  id: "grok-cli", priority: 275, alias: "gcli", aliases: ["grok-build", "gb"],
  category: "oauth",
  thinkingConfig: { options: ["low","medium","high","xhigh"], defaultMode: "high" },
  transport: {
    baseUrl: `${d}/responses`,            // d = https://cli-chat-proxy.grok.com/v1
    format: "openai-responses", forceStream: true,
    modelsUrl: `${d}/models`, userUrl: `${d}/user`, billingUrl: `${d}/billing`,
    clientVersion: r, clientIdentifier: l, tokenAuth: "xai-grok-cli",
    headers: { "User-Agent": p, "x-grok-client-identifier": l, "x-grok-client-version": r },
    usage: { url: `${d}/billing?format=credits`, userUrl: `${d}/user?include=subscription` },
    retry: { 429: {attempts:2,delayMs:2000}, 502: {attempts:2,delayMs:1500}, 503: {attempts:2,delayMs:1500} }
  },
  models: [
    { id:"grok-build", name:"Grok Build", contextLength:500000, maxOutputTokens:64000 },
    { id:"grok-4.5", name:"Grok 4.5" },
    { id:"grok-4.5-high",   name:"Grok 4.5 (High)",   upstreamModelId:"grok-4.5" },
    { id:"grok-4.5-medium", name:"Grok 4.5 (Medium)", upstreamModelId:"grok-4.5" },
    { id:"grok-4.5-low",    name:"Grok 4.5 (Low)",    upstreamModelId:"grok-4.5" },
  ],
  oauth: {
    clientId: "b1a00492-073a-47ea-816f-4c329264a828",
    deviceCodeUrl: "https://auth.x.ai/oauth2/device/code",
    tokenUrl: "https://auth.x.ai/oauth2/token",
    refreshUrl: "https://auth.x.ai/oauth2/token",
    scope: "openid profile email offline_access grok-cli:access api:access conversations:read conversations:write",
    referrer: "grok-build", refreshLeadMs: 300000
  }
}
```

### Known working auth headers (grok CLI / 9Router)
```
Authorization: Bearer <access_token>
x-xai-token-auth: xai-grok-cli
x-grok-client-identifier: 9router
x-grok-client-version: 0.2.93
User-Agent: grok-pager/0.2.93 grok-shell/0.2.93 (linux; x86_64)
```
**Version gate:** x-grok-client-version must be >= server's min (e.g. 0.1.202 in Aug 2026).
Older → `426 {"error":"Your Grok CLI version (0.1.0) is outdated..."}`.

### Chat request transform (OpenAI chat → grok Responses)
```json
{ "model":"grok-4.5",
  "input":[{"role":"user","content":[{"type":"input_text","text":"hi"}]}],
  "reasoning":{"effort":"high"}, "stream":true }
```

### SSE events (streaming)
- `response.created`, `response.in_progress`
- `response.output_item.added`, `response.content_part.added`
- **`response.output_text.delta`** → `data: {"type":"response.output_text.delta","delta":"144",...}` (delta = plain string)
- `response.output_text.done`, `response.content_part.done`, `response.output_item.done`
- `response.completed` (terminal; includes usage)

## codex (cx) — OpenAI Codex CLI

```js
{
  id: "codex", alias: "cx", category: "oauth",
  thinkingConfig: { options: ["auto","none","low","medium","high"], defaultMode: "auto" },
  transport: {
    baseUrl: "https://chatgpt.com/backend-api/codex/responses",
    format: "openai-responses", forceStream: true,
    headers: { originator: "codex_cli_rs", "User-Agent": "codex_cli_rs/0.136.0" },
    usage: { url: "https://chatgpt.com/backend-api/wham/usage",
             resetCreditsUrl: ".../rate-limit-reset-credits",
             resetCreditsConsumeUrl: ".../rate-limit-reset-credits/consume" }
  },
  models: gpt-5.6-sol, gpt-5.6-sol-review, gpt-5.6-terra, gpt-5.6-terra-review,
          gpt-5.6-luna, gpt-5.6-luna-review, gpt-5.5, gpt-5.5-review,
          gpt-5.4, gpt-5.4-review, gpt-5.4-mini, gpt-5.4-mini-review,
          gpt-5.3-codex-spark, gpt-5.5-image, gpt-5.4-image, ...
  oauth: {
    clientId: "app_EMoamEEZ73f0CkXaXp7hrann",
    authorizeUrl: "https://auth.openai.com/oauth/authorize",
    tokenUrl: "https://auth.openai.com/oauth/token",
    scope: "openid profile email offline_access",
    codeChallengeMethod: "S256", fixedPort: 1455, callbackPath: "/auth/callback",
    extraParams: { id_token_add_organizations:"true", codex_cli_simplified_flow:"true", originator:"codex_cli_rs" },
    refreshLeadMs: 432000000,          // 5 days
    refresh: { encoding:"form", scope:"openid profile email offline_access" },
    maxRefreshAgeMs: 691200000,        // 8 days
    trackRefreshAt: true
  }
}
```
Note: codex uses **authorize-code (PKCE S256)** flow, NOT device-code. Local callback port 1455.

## Generic OAuth refresh shape (from 9Router core chunk 3943.js)
```
POST refreshUrl (or tokenUrl)
Content-Type: application/x-www-form-urlencoded
body: grant_type=refresh_token&refresh_token=...&client_id=...
(optionally client_secret, encoding json or form)
```
