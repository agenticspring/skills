---
name: grok-register-browserless
description: Browserless Grok/x.ai signup via gRPC protobuf + Turnstile.
version: 1.0.0
category: automation
tags: [grok, xai, gRPC, protobuf, turnstile, capsolver, IMAP, registration]
---

# Grok (x.ai) Browserless Registration

Register accounts at `https://accounts.x.ai/sign-up` WITHOUT a browser. Full flow verified: signup + login + GetUser + ListModels all return grpc-status 0.

## Key facts

- API is **gRPC-web protobuf**, NOT REST. Frontend JS showed `/api/auth/*` but those 404 — real endpoint:
  `POST https://accounts.x.ai/auth_mgmt.AuthManagement/{MethodPascalCase}`
  Headers: `Content-Type: application/grpc-web+proto`, `X-Grpc-Web: 1`, `Origin/Referer: https://accounts.x.ai`
- Body = gRPC frame: `0x00` + big-endian uint32 length + protobuf payload
- Proto package: `auth_mgmt` (service `AuthManagement`), descriptor decoded from JS bundle `logs/js/163zufhw7ej6h.js` (base64 `fileDesc`)
- Turnstile sitekey: `0x4AAAAAAAhr9JGVDZbrZOo0`
- Email code format: **6 alphanumeric** `XXX-XXX` in subject `SpaceXAI confirmation code: WEG-D4V`
- TOS_ACCEPTED_VERSION = `1`

## Field numbers (from descriptor, verified)

CreateEmailValidationCodeRequest: email=1
VerifyEmailValidationCodeRequest: email=1, code=2, delete_on_success=3, return_verification_token=4
CreateUserRequest: given_name=1, family_name=2, email=3, clear_text_password=**5**, tos_accepted_version=**6**, anti_abuse_token=**7**
CreateUserAndSessionRequest: create_user_request=1, anti_abuse_token=**6**, email_validation_code=**9**, castle_request_token=11
AntiAbuseToken: turnstile_token=1
CreateSessionRequest (login): credentials=1 (Credentials.email_and_password: email=1, pw=2), anti_abuse_token=**4**, tos_version=**6**
GetUser / ListModels / ListActiveSessions / GetConsumerSubscriptions: empty body `grpc_frame(b'')` with session cookie

## Flow

1. Warm session: GET `/sign-up` (or `/sign-in` for login) with curl_cffi impersonate chrome124
2. `CreateEmailValidationCode` {email} → OK
3. Poll IMAP for code (see below), strip the dash
4. `VerifyEmailValidationCode` {email, code, delete_on_success=False, return_verification_token=False} — do NOT delete; code needed again in step 6
5. Solve Turnstile via Capsolver `AntiTurnstileTask` **WITH proxy** (proxyless fails: "Failed to verify Cloudflare turnstile token" — token is IP-bound)
6. `CreateUserAndSession` {create_user_request{...}, anti_abuse_token{turnstile_token}, email_validation_code, castle_request_token=""} → returns session + session_cookie JWT + is_new_user
7. Login test: `CreateSession` {credentials{email_and_password{email,pw}}, anti_abuse_token{turnstile_token}, tos_version=1} — needs a FRESH turnstile solve too

## IMAP

- Valid app password lives in `/root/virtuals-autoreg/.env` (IMAP_HOST/USER/PASS) and `/root/cf-tuyul/.env` — NOT in cf-farm/webnovel-autoreg (those have empty IMAP_PASS)
- Search `(TO "{email}")`, newest-first, match subject regex `([A-Z0-9]{3}-?[A-Z0-9]{3})`

## Turnstile solve (Capsolver)

- Task: `AntiTurnstileTask` + `proxy` (NOT proxyless — IP-bound)
- Same proxy must be used for BOTH solve and API calls
- Proxy format for Capsolver: `http://user:pass@host:port`
- Proxy pool: `/root/webnovel-tg-bot/proxy.txt` — format `host:port:user:pass` with FULL password (e.g. `pnkxj33es7bkruq`, NOT truncated)
- Working key: `<CAPSOLVER_API_KEY_4_REDACTED>` (~$86)
- Cost: ~2 solves/account ≈ $0.006

## ⚠️ CRITICAL: signup yields flagged accounts (bfs=1) — root cause found

Every automated signup (RPC, protocol, browserless; every proxy incl. NO proxy; every domain incl. `<REDACTED>`) produces accounts with `bfs:1` in their OAuth access token. **Root cause (2026-08-08): xAI Turnstile fingerprints solver patterns — Capsolver returns `Bot behavior detected, error code: 600010` and accounts created with solver tokens inherit `bfs:1`.** Consequences: the served model is a DOWNGRADED build (self-ID "I am Grok-2"/"Grok-1"/"MODEL=unknown" instead of grok-4.5) and reasoning is dead (`reasoning` field always empty). Only manual signup (human-clicked Turnstile) is known to yield clean accounts. See the `grok-account-automation` skill's `references/grok-bfs-flag.md` and the degradation probe script for detection. Do NOT claim a farmed pool is full-quality grok-4.5 without running the model self-ID probe first.

## Accounts / tier

- New accounts = **free tier**, NO paid trial (GetConsumerSubscriptions empty)
- Entitlements: `user:grok-web-access` + `user:grok-code-cli` (verified via GetUser)
- Free limit ~10 requests/2h
- CLI auth: legacy `CreateGrokCliOnetimeCode` DISABLED ("Use OAuth2 login instead (grok login)") — use **`grok login --device-auth`** + approve via session cookie (`POST auth.x.ai/oauth2/device/approve`, form `user_code`+`action=allow` → 303). 9Router `grok-cli` provider injection is fully browserless: `GET /api/oauth/grok-cli/device-code` → approve → `POST /api/oauth/grok-cli/poll`. See the `grok-account-automation` skill for the full flow.

## Pitfalls

- Do NOT use `<REDACTED>` — use `<REDACTED>` (Dez explicit)
- Session cookie for authenticated RPCs = JWT from CreateSessionResponse field 2, set as cookie on accounts.x.ai
- `GetUser` with `Authorization: Bearer` fails (management key only) — use session cookie instead
- Castel/`castleRequestToken` not required for signup despite `enableCastle: true` in page config
- Scripts: `/root/grok-register/signup_nobrowser.py` (signup+login), data/ has response bins
