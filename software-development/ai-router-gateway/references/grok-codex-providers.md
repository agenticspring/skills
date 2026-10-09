# Grok CLI + Codex provider configs (reverse-engineered from 9Router v0.5.45)

Source: `/usr/lib/node_modules/9router/app/.next-cli-build/static/chunks/1321-*.js` + server chunks.
These are PUBLIC client IDs (shipped in 9Router's public source) — not secrets. Use as config templates.

## grok-cli (Grok Build subscription via cli-chat-proxy.grok.com)

```yaml
- id: grok-cli
  alias: gcli
  category: oauth
  strategy: round-robin
  transport:
    baseUrl: https://cli-chat-proxy.grok.com/v1
    format: openai-responses     # NOT openai-chat — uses /responses endpoint
    forceStream: true
    modelsUrl: https://cli-chat-proxy.grok.com/v1/models
    userUrl: https://cli-chat-proxy.grok.com/v1/user
    billingUrl: https://cli-chat-proxy.grok.com/v1/billing
    tokenAuth: xai-grok-cli      # special auth header mode
    headers:
      User-Agent: grok-pager/0.2.93 grok-shell/0.2.93 (linux; x86_64)
      x-grok-client-version: 0.1.202   # MUST be >= 0.1.202 else 426
  oauth:
    clientId: b1a00492-073a-47ea-816f-4c329264a828
    deviceCodeUrl: https://auth.x.ai/oauth2/device/code
    tokenUrl: https://auth.x.ai/oauth2/token
    scope: "openid profile email offline_access grok-cli:access api:access conversations:read conversations:write"
    referrer: grok-build
    refreshLeadMs: 300000        # refresh 5 min before expiry
  models:
    - id: grok-4.5               # upstreamModelId alias trick:
    - id: grok-4.5-high          #   upstream: grok-4.5 + reasoning_effort high
    - id: grok-4.5-medium        #   upstream: grok-4.5 + effort medium
    - id: grok-4.5-low           #   upstream: grok-4.5 + effort low
    - id: grok-build             # 500k context, 64k max output
```

Auth headers actually sent (from provider impl):
```
Authorization: Bearer <accessToken>
x-xai-token-auth: xai-grok-cli
x-grok-client-identifier: <client-ident>
x-grok-client-version: <version>
x-email: <email>          # optional
x-userid: <principalId>   # optional
```

9Router connection storage (SQLite `providerConnections.data` JSON): `accessToken, refreshToken, idToken, expiresAt (RFC3339), expiresIn: 21600 (6h), scope, testStatus, providerSpecificData.authMethod=device_code, lastRefreshAt`.

## codex (OpenAI Codex — ChatGPT Plus backend)

```yaml
- id: codex
  alias: cx
  category: oauth
  strategy: round-robin
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
    fixedPort: 1455              # local callback port (fixed!)
    callbackPath: /auth/callback
    extraParams:
      id_token_add_organizations: "true"
      codex_cli_simplified_flow: "true"
      originator: codex_cli_rs
    refreshLeadMs: 432000000     # 5 days
    maxRefreshAgeMs: 691200000   # 8 days
    trackRefreshAt: true
    refresh:
      encoding: form             # form-encoded refresh
      scope: "openid profile email offline_access"
  models:
    - id: gpt-5.6-sol
    - id: gpt-5.6-sol-review     # upstream: gpt-5.6-sol, quotaFamily: review
    - id: gpt-5.6-terra
    - id: gpt-5.6-luna
    - id: gpt-5.5
    - id: gpt-5.4
    - id: gpt-5.4-mini
```

Codex uses authorize-code + PKCE S256 (not device flow). Callback runs on localhost:1455. The `codex_cli_simplified_flow=true` param is important for CLI login to work.

## Generic refresh logic (from 9Router chunk 3943)

```js
body = {grant_type:"refresh_token", refresh_token, client_id}
format = bodyFormat==="json" ? JSON : URLSearchParams   // codex/oauth refresh: form
includeClientSecret if provider has clientSecret
Content-Type: application/x-www-form-urlencoded (form) | application/json (json)
```

URL-encode refresh_token when building the form — xAI refresh tokens contain `+` and `&`.
