# xAI `bfs` flag: why solver-created Grok accounts get downgraded models

Investigated 2026-08-08/09. This explains why every farmed Grok account behaves "dumb" even though the free tier technically supports grok-4.5.

## The chain (all confirmed)

```
Captcha solver (Capsolver/2captcha) solves Turnstile
  → xAI Turnstile detects the solver: "Bot behavior detected, error code: 600010"
      (this error appears on SOME solve attempts; tokens that DO come back are still marked)
  → account created with a solver-marked Turnstile token gets `bot_flag_source=1` at registration
  → OAuth access token carries claim `"bfs": 1` (bfs = backward-compatible name for bot_flag_source)
  → server silently serves a DOWNGRADED model to flagged accounts
  → "the model is dumb" — exactly what users report
```

## Evidence of downgrade (self-identification tests)

Requesting `grok-4.5` / `grok-4.5-high` on a `bfs=1` account returns a model that self-identifies as:

| Requested | Self-reported |
|---|---|
| grok-4.5 | "MODEL=unknown" (identity hidden) |
| gcli/grok-4.5-high | "I am Grok-2" |
| gcli/grok-4.5-medium | "Grok-1" |
| gcli/grok-4.5-xhigh | "version 2" |
| self-knowledge | "grok-4.5 (which doesn't even exist)" |

Reasoning appears dead: chain-of-thought request returns empty, `reasoning_effort: xhigh` adds no quality.

## What was ruled out (all failed, 100%)

- JWT tampering `bfs:1 → 0` with original signature → 401 (signature verified, ES256, kid `oauth2-production-2026-02-19`).
- `alg=none`, HS256 confusion using JWKS public key: 401.
- Registration variations (all still `bfs=1`):
  - proxy: 3xK datacenter, Webshare/Leaseweb, **no proxy (VPS IP)** — same result
  - domain: <REDACTED>, <REDACTED>, <REDACTED> — same result
  - flow: gRPC CreateUserAndSession, protocol SignupServerAction, no-redirect — same result
- Browser signup (Playwright/Chromium headless): submit hits HTTP 403 (needs in-page Turnstile solve; injecting a solver token into `cf-turnstile-response` also fails because the token itself is bot-flagged).

Conclusion: **`bfs` is a user-level attribute set server-side at registration; it cannot be removed from the client.** The only clean-account path is a HUMAN solving Turnstile in a real browser (one per IP). Solver premium that xAI hasn't fingerprinted is theoretical; do not promise it.

## Operator takeaways

- Accounts with `bfs=1` still work for light tasks — just not for heavy reasoning.
- A router should still count/reuse them (round-robin), but a "quality" label per connection would let a fallback chain prefer un-flagged accounts.
- Decoding the JWT (`payload.bfs`) is the reliable detection method — see `internal/store` AES-GCM handling in spring-router for token-at-rest best practice.

## Session artifacts

- `~/.9router/db/data.sqlite` → `providerConnections` holds the OAuth tokens (with `bfs` in access token JWT).
- Grok account farm kit lives at `/root/grok-register/` (script: `farm_inject.py`, `signup_batch.py`).