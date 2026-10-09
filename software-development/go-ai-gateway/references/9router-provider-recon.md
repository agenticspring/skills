# Reversing a provider config from 9Router JS bundles

9Router (Node/Next.js, installed at `/usr/lib/node_modules/9router/`) embeds the
full provider registry as minified JS. This is how grok-cli and codex were
reverse-engineered without docs.

## Where to look

Provider definitions with transport+OAuth live in:

```
/usr/lib/node_modules/9router/app/.next-cli-build/static/chunks/*.js    (client)
/usr/lib/node_modules/9router/app/.next-cli-build/server/chunks/*.js    (server)
```

The big chunk `1321-3cb00d56de5fba92.js` holds most OAuth providers; server chunks
`2573.js` / `7011.js` duplicate them with server-side logic.

## Extraction recipe

```python
import re, glob
for f in glob.glob('/usr/lib/node_modules/9router/app/.next-cli-build/static/chunks/*.js'):
    txt = open(f, errors='ignore').read()
    if 'id:"grok-cli"' in txt:
        i = txt.find('id:"grok-cli"')
        print(txt[i-200:i+2500])
```

Patterns to grep for a provider:
- `id:"<provider>"` — start of the provider object
- `oauth:{clientId:"..."` — OAuth block
- `transport:{baseUrl:"..."` — transport block
- `refreshLeadMs:` — token refresh lead
- `tokenAuth:"xai-grok-cli"` — special auth mode

## Key extracted facts (verified)

### grok-cli
```
id:"grok-cli", alias:"gcli", aliases:["grok-build","gb"], priority:275, category:oauth
transport.baseUrl = `${d}/responses` (d = https://cli-chat-proxy.grok.com/v1)
format "openai-responses", forceStream, tokenAuth "xai-grok-cli"
clientVersion/clientIdentifier headers, User-Agent "grok-pager/0.2.93 grok-shell/0.2.93 (linux; x86_64)"
oauth: clientId b1a00492-073a-47ea-816f-4c329264a828
  deviceCodeUrl https://auth.x.ai/oauth2/device/code
  tokenUrl https://auth.x.ai/oauth2/token
  scope "openid profile email offline_access grok-cli:access api:access conversations:read conversations:write"
  referrer "grok-build", refreshLeadMs 300000
models: grok-build (500k ctx, 64k out), grok-4.5, grok-4.5-high/medium/low (upstream grok-4.5)
```

### codex
```
id:"codex", alias:"cx", category:oauth, deprecated RISK_NOTICE in 0.5.45
transport.baseUrl https://chatgpt.com/backend-api/codex/responses, format openai-responses
headers {originator:"codex_cli_rs"}, User-Agent "codex_cli_rs/0.136.0"
oauth: clientId app_EMoamEEZ73f0CkXaXp7hrann
  authorizeUrl https://auth.openai.com/oauth/authorize
  tokenUrl https://auth.openai.com/oauth/token
  scope "openid profile email offline_access"
  codeChallengeMethod S256, fixedPort 1455, callbackPath /auth/callback
  extraParams {id_token_add_organizations:"true", codex_cli_simplified_flow:"true", originator:"codex_cli_rs"}
  refreshLeadMs 432000000, maxRefreshAgeMs 691200000, trackRefreshAt
models: gpt-5.6-sol / -terra / -luna (+ -review variants), gpt-5.5, gpt-5.4, gpt-5.4-mini
```

## Generic refresh implementation (from 3943.js)

OAuth refresh body defaults to form-encoding:

```
grant_type=refresh_token&refresh_token=<rt>&client_id=<cid>
[+ client_secret if includeClientSecret]
```

`refreshLeadMs` means: refresh when `now >= expiresAt - refreshLeadMs`.
Codex refresh lead is 5 days, max age 8 days — the token MUST be refreshed before
8 days or it cannot be refreshed at all.

## Pitfalls while reversing

- Strings are escaped (`\"` for quotes) in minified JS; unescape before matching.
- `grok-web` is a SEPARATE cookie-based provider (sso= cookie, REST chat) — not the
  same as `grok-cli` (OAuth device flow). Don't confuse them.
- The transport base URL appears as a template literal (`${d}`); resolve the const
  that defines `d` (for grok-cli it's `https://cli-chat-proxy.grok.com/v1`).
- 9Router version bumps change client IDs/version headers — re-check on upgrade.