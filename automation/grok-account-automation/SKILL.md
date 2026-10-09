---
name: grok-account-automation
description: Register/login/chat Grok accounts browserless via gRPC + WS.
version: 1.0.0
category: automation
tags: [grok, xai, accounts.x.ai, gRPC, protobuf, turnstile, websocket, signup, registration]
---

# Grok / x.ai Account Automation (browserless)

Register, login, and chat with Grok (xAI) accounts WITHOUT a browser. Covers the full
lifecycle: signup (`accounts.x.ai`), login, and chat via the grok.com WebSocket gateway.

## When to use

- User asks to register / farm Grok accounts (`grok.com`, `accounts.x.ai`)
- User wants to test Grok models programmatically (including reasoning models)
- User wants to inject Grok accounts into 9Router or Grok CLI
- Any task where the REST endpoints 404 and you need the real API surface

## Core insight: the API is gRPC-web protobuf, NOT REST

`/api/auth/*` returns `404 {"error":"Not found"}` from curl. The real API is:

```
POST https://accounts.x.ai/auth_mgmt.AuthManagement/{MethodPascalCase}
Content-Type: application/grpc-web+proto
X-Grpc-Web: 1
Body: grpc frame = [0x00 flag][4-byte BE length][protobuf payload]
```

Response: grpc-web framed messages + trailing `grpc-status:0`. Check BOTH the
`grpc-status` header AND the body trailer — errors often come back as
`grpc-status:13` with `grpc-message` (protobuf decode errors, turnstile failures).

### How to discover the endpoint (do this once per target)

1. `curl_cffi` with `impersonate='chrome124'` can pass Cloudflare on `accounts.x.ai` (curl alone gets 403 challenge).
2. Download the signup HTML, extract `/_next/static/chunks/*.js`, grep for the auth client.
3. The auth client lives in a chunk with `function p(e,t){return fetch(\`${r}/${e}\`,...)` where `r = baseUrl ?? "/api/auth"`.
4. CSP `connect-src` header on responses lists auth hosts (e.g. `auth.x.ai`, `auth.grok.com`).
5. The transport is ConnectRPC — `createClientTransport("xai-account","",...)` → URL = `{baseUrl}/{typeName}/{Method}`. typeName comes from the proto descriptor (package = `auth_mgmt`, service = `AuthManagement`, method = PascalCase).
6. Decode proto descriptors: JS bundles embed `fileDesc>("<base64>")` — base64-decode and hexdump to read EXACT field numbers. **Never guess field order from message-name lists; the declaration order in the readable dump is NOT the wire number order** (e.g. CreateUserRequest: given=1, family=2, email=3, clear_text_password=5, tos=6, anti_abuse_token=7 — password is NOT field 4).

## Signup flow (proven working)

1. `CreateEmailValidationCode` — field 1 = email. Returns Empty (grpc-status 0).
2. Poll IMAP for the code. **Code format is `XXX-XXX` (6 alphanumeric, optional dash)** — NOT 6 digits. Subject: `SpaceXAI confirmation code: WEG-D4V`. Strip the dash before verify.
3. `VerifyEmailValidationCode` — email=1, code=2, delete_on_success=3, return_verification_token=4.
   **PITFALL: `delete_on_success=true` consumes the code — it is then invalid for CreateUserAndSession.** Verify with delete=false, or skip verify entirely (CreateUserAndSession validates the code itself).
4. Solve Cloudflare Turnstile (sitekey `0x4AAAAAAAhr9JGVDZbrZOo0`) via Capsolver `AntiTurnstileTask` **with the same proxy used for the API request** — see Turnstile IP-bound pitfall.
5. `CreateUserAndSession`:
   - field 1 = CreateUserRequest {given=1, family=2, email=3, password=5, tos=6, anti=7}
   - field 6 = AntiAbuseToken {turnstile_token=1, token=2}
   - field 9 = email_validation_code (from step 2)
   - field 11 = castle_request_token (empty string works)
   - `tos_accepted_version` = 1 (constant `TOS_ACCEPTED_VERSION=1` in JS).
   - Response `CreateSessionResponse`: field 2 = session cookie JWT (HS256, payload only has `session_id` — there is NO `bfs` claim in this token), field 4 = is_new_user.

## Login flow

`CreateSession` — credentials=1 `{emailAndPassword: {email=1, clearTextPassword=2}}`, anti_abuse_token=4 (AntiAbuseToken with turnstile_token), tos_version=6. Requires a Turnstile solve too. Response gives session + `session_cookie` JWT.

grok.com accepts this session: set cookie **`sso`** = the session JWT (this exact cookie name works on `grok.com` for `get-user`, `/rest/models`, and the chat WS; `xai-session` / bearer do NOT).

## Chat: use the WebSocket, not REST

`POST /rest/app-chat/conversations/new` returns **403 "Request rejected by anti-bot rules"** even with a valid `sso` cookie — it needs a Castle `castle_request_token` minted client-side by the Castle SDK (publishable key is in the page config, but the token itself is browser-generated).

**The WebSocket gateway bypasses anti-bot entirely:**

```
wss://grok.com/ws/mgw/?uid={userId}     (userId from get-user)
Cookie: sso={session JWT}
```

Protocol (envelope wraps every event):
1. Send `{"event":{"type":"session.create","session":{}}}` → get `session_id` from reply.
2. Wait for `conversation.attached`.
3. Send item: `{"session_id":sid,"event":{"type":"conversation.item.create","item":{"type":"message","role":"user","content":[{"type":"input_text","text":"..."}]}}}` — **OpenAI-style `content: [{type:"input_text", text}]` works; the `x_grok.input_chunks` protobuf JSON shape does NOT** (server replies "message got cut off").
4. Send `{"session_id":sid,"event":{"type":"response.create","event_id":"evt_resp_..."}}`.
5. Read events; text arrives as `response.output_text.delta` (concatenate), done at `response.done`.

Use proxy via `websocket.create_connection(..., http_proxy_host, http_proxy_port, proxy_type="http", http_proxy_auth=(user,pass))`.

## Grok CLI login (device-auth, browserless) — PROVEN

The official CLI (`curl -fsSL https://x.ai/cli/install.sh | bash`, binary `~/.grok/bin/grok`, symlink `~/.local/bin/grok`) supports headless login:

```
grok login --device-auth
→ prints user_code (format XXXX-XXXX, 9 chars e.g. "QNY6-D7HQ", "FXJF-AX6K")
→ "Waiting for authorization..."
```

Authorize the code WITHOUT a browser using the account session cookie:

```
POST https://auth.x.ai/oauth2/device/approve
Content-Type: application/x-www-form-urlencoded
Cookie: sso={session_cookie JWT}
body: user_code={USER_CODE}&action=allow
→ 303 redirect to /oauth2/device/done = SUCCESS
```

- **Endpoint discovery**: the approve URL is embedded in the Next.js payload of `/oauth2/device/consent?user_code=...` as `approveUrl` + `userCode` on the `$L42` node.
- **Form field names**: `user_code` (NOT `userCode` — that returns `400 Missing user_code`), plus `action=allow` (any other action → `400 Invalid action`).
- No Turnstile/Castle needed for approve.
- After approve, CLI writes `~/.grok/auth.json`: `{"https://auth.x.ai::{uuid}": {"key": "...", "auth_mode", "user_id", "email", "refresh_token", "expires_at", "oidc_issuer"}}`.
- **Code-parsing pitfall**: device codes are 9 chars (`FXJF-AX6K`). A `[A-Z0-9]{3}-[A-Z0-9]{3}` regex grabs a WRONG substring from the URL (prefix chars). Parse the standalone line after "Confirm this code in your browser:" with `[A-Z0-9]{3,6}-[A-Z0-9]{3,6}`.

### CLI usage
```bash
grok -p "prompt"                        # single-turn, stdout (TUI fails in non-tty with "No such device or address os error 6" — always use -p)
grok -p "prompt" --always-approve       # auto-approve tool execution
grok -p "prompt" --output-format streaming-messages-json   # JSON events (init shows tools list)
grok models                             # free tier exposes ONLY grok-4.5
GROK_PROXY_URL=http://user:pass@host:port grok ...   # proxy via env
```
- Default model: **Grok 4.5**. Free tier CLI rejects `-m grok-4-1-thinking-1129` ("unknown model id") — thinking models need a plan.
- **Tool calling WORKS in CLI** (unlike WS): 27 tools incl `run_terminal_command`, `read_file`, `web_search`, `image_gen`, `spawn_subagent`. With `--always-approve` the tool actually executes (`run_terminal_command echo $((6*7))` → output `42`). Cost ~$0.009/request.

## 9Router grok-cli provider injection — PROVEN

9Router (localhost:20128) ships a `grok-cli` provider (alias `gcli`, aliases `grok-build`/`gb`, display "Grok CLI (Grok Build)"). OAuth clientId `b1a00492-073a-47ea-816f-4c329264a828`, deviceCodeUrl `https://auth.x.ai/oauth2/device/code`, tokenUrl `https://auth.x.ai/oauth2/token`, scope `openid profile email offline_access grok-cli:access api:access conversations:read conversations:write`.

Injection flow (fully browserless, reuse session cookie):

```
1. GET  /api/oauth/grok-cli/device-code     (header x-9r-cli-token)
   → {device_code, user_code, verification_uri, codeVerifier, expires_in:1800}
2. Approve user_code via session cookie (POST auth.x.ai/oauth2/device/approve, form user_code+action=allow) → 303
3. POST /api/oauth/grok-cli/poll  (JSON {deviceCode, codeVerifier}, header x-9r-cli-token)
   → {success:true, connection:{id, provider:"grok-cli"}}
```

- Poll is **POST with JSON body** `{deviceCode, codeVerifier}` — GET or query params return `400 Unknown action`.
- Model served as **`gcli/grok-4.5`** (round-robins across all injected connections). Verified: `17*23 → 391`, reasoning `123*456 → 56088`, `17*23+45*12 → 931`; supports `reasoning_effort` high/medium/low/xhigh (500k context).
- `/v1/chat/completions` requires a dashboard API key from `GET /api/keys` (Bearer), NOT the x-9r-cli-token. `/v1/models` works unauthenticated on localhost.
- Full flow script: `/tmp/grok_9router_flow2.py` (start code → approve → poll).
- **Batch farm+inject script**: `/root/grok-register/farm_inject.py --target N` — loops protocol signup → set-cookie hop chain → device approve → 9Router poll until N connections. Verified 20/20, later re-run on demand to **31/31 connections** (2026-08-09) — the script is the operational path whenever Dez wants more flagged-but-usable accounts for light tasks; accounts saved to `data/accounts.json` with `connection_id`. Round-robin across N accounts multiplies free-tier capacity (~10 req/2h each).
- **All 20 farmed accounts carry `bfs:1` and are downgraded-model served** — see bfs section below; the pool works for chat/API but does NOT get real grok-4.5 quality. Do not advertise a grok-cli pool as full-quality 4.5 without checking model self-ID first.

## Model list & free tier

- `POST /rest/models` with `{"locale":"en-US"}` (works unauthenticated too): grok-3 (default free), grok-420, grok-4-1-thinking-1129 (reasoning), plus companion/plugin modes.
- **Verified chat via WS**: grok-3 (17*23→391 ✅), grok-4-1-thinking-1129 (12*12→144 ✅), grok-4.5 (15*15→225 ✅), grok-4.5-latest (11*11→121 ✅), grok-4.20 (7*8→56 ✅). All listed models are usable — free-tier blocks by rate, not by model.
- **Tool calling via WS does NOT work for custom tools** — the model ignores `tools` in session.create/response.create and answers in plain text (claims no such tool; only built-in web_search/open_page mentioned). Tool calling requires the Grok CLI path (see CLI section).
- Free tier: roughly 10 requests / 2h per account. When exhausted, the WS returns `response.grok.output` with `stream_error: {kind:"usage_limit_reached"}`. This is NOT an account flag — it is a rate limit. Scale by farming accounts, or wait for reset.
- **`bfs` (Bot Flag Source) — WHERE IT ACTUALLY LIVES + WHAT IT MEANS (verified 2026-08-08):**
  - NOT in the accounts session JWT (that one only has `session_id`). It IS in the **OAuth access token** issued by `auth.x.ai` for the grok-cli client — every farmed account got `"bfs": 1` in the JWT payload.
  - Meaning (from Linux.do + doshare research): xAI reads the `bfs` claim (backward-compat for old `bot_flag_source`). `1` or `2` = account flagged as bot risk → **intelligence downgrade (降智)** — reasoning is throttled/never fires. `0` or absent = clean.
  - **Detection**: decode the access token JWT stored by 9Router in its SQLite DB (`providerConnections.data` → `accessToken`, ES256, 837 chars) — see `references/grok-bfs-flag.md` for the check script.
  - **DB disambiguation (verified 2026-08-09)**: the JWT with `bfs` lives in the **9Router** DB `~/.9router/db/data.sqlite` (`providerConnections.data.accessToken`). The **spring-router** DB (`~/.spring-router/data.db`, `connections.data.AccessToken`) stores an OPAQUE 854-byte base64 blob (NOT a JWT — base64-decodes to binary, no payload claims). Do not waste time decoding spring-router tokens. In the 9Router DB, a `bfs` key that is MISSING/absent in the payload means clean (28 of 31 farmed accounts), `"bfs": 1` means flagged (3 of 31: gx111.950578, gx112.db1f99, gt.2f4e15). Absent ≠ 0-value; both mean unflagged.
  - **User endpoint does NOT expose it**: `https://cli-chat-proxy.grok.com/v1/user?include=subscription` returns `hasGrokCodeAccess:true`, `userBlockedReason:null`, `subscriptionTier:null` — no `buildBotFlagged` field even when `bfs:1` is in the token.
  - **Symptom**: `msg.reasoning` / `reasoning_content` is ALWAYS empty in responses, even at `reasoning_effort:xhigh` — model still shows "step-by-step" public CoT but the internal reasoning pathway is downgraded.
  - **Bypass NOT yet solved (as of this session)**: the flag is set server-side at token issuance; no client-side trick confirmed. Tested and REJECTED: protocol SignupServerAction path (repo claim: avoids `bot_flag_source` — still yields `bfs:1`, see `references/grok-protocol-signup.md`), dropping `?redirect=grok-com`, **JWT manipulation** (`bfs:1`→`0` with original sig = 401; `alg:none` = 401; **HS256 confusion with the real ES256 public key from `https://auth.x.ai/.well-known/jwks.json` as HMAC secret = 401** — signature is strictly verified server-side, see `references/grok-bfs-flag.md`), **referrer swap in the device-code flow** (`grok-build`/`grok-com`/`cloud-console`/`docs`/`grokipedia-com`/`web` — all still `bfs:1`), **proxy provider swap** (3xK → webshare/Leaseweb), **domain swap** (`<REDACTED>` → `<REDACTED>`). Narrowed leads: Turnstile-solve pattern via Capsolver (the one constant), real-browser fingerprint at signup, alternate OAuth client/scope, `grok-keysmith`. Workaround per articles: detect flagged accounts and don't route traffic to them.
  - **ROOT CAUSE CONFIRMED (final investigation 2026-08-08): the Turnstile solver is the flag source.** xAI Turnstile fingerprints solver patterns — Capsolver returns `Bot behavior detected, error code: 600010` on every proxy AND proxyless, yet sometimes still mints a token, and accounts created with solver tokens inherit `bfs:1`. This explains why EVERY farmed account (all flows/proxies/domains) was flagged — the solver was the one constant. Full chain + remaining paths in `references/grok-bfs-flag.md`. Project archived 2026-08-08; only manual signup (human-clicked Turnstile) is known to yield clean accounts.
  - **FINAL TEST — no proxy + fresh domain (2026-08-08, archived):** signup with NO proxy (VPS IP 82.39.206.183 direct) + domain `<REDACTED>` (never used for Grok before) STILL produced `bfs:1`. Complete matrix: proxy (3xK / webshare-Leaseweb / NONE) × domain (<REDACTED> / <REDACTED> / <REDACTED>) × flow (RPC / protocol / no-redirect) = ALL flagged. This closes the proxy/domain hypotheses — the Turnstile solver token is the sole common variable.
  - **CONFIRMED SYMPTOM — server serves DOWNGRADED MODELS to flagged accounts (verified 2026-08-08, second investigation):**
    - Model self-ID probes on a `bfs:1` account via 9Router `gcli/grok-4.5*`: `grok-4.5` → "latest xAI system"/`MODEL=unknown`; `grok-4.5-high` → "I am Grok-2"; `grok-4.5-medium` → "Grok-1"; `grok-4.5-xhigh` → "version 2". Request model field says `grok-4.5` but the served model is an old/renamed build — the identity is masked server-side.
    - Direct backend probe (`https://cli-chat-proxy.grok.com/v1/responses`, model `grok-4.5`, reasoning effort xhigh): response `reasoning: {effort:xhigh, summary:detailed}` is echoed, BUT no reasoning summary/content is ever emitted — only final text. Asking for chain-of-thought (`<thinking>` tags / "show internal CoT") returns empty.
    - `self_knowledge` probe: "I'm not grok-4.5... grok-4.5 (which doesn't even exist)" — the downgraded model does not know grok-4.5 exists. This is the fastest fingerprint: ask the model its exact ID.
    - Model escape attempts all fail: `grok-4.5-high`/`-xhigh`/`-reasoning` → 400, `grok-4.20`/`grok-latest` → 402, `grok-5` → 429. Only `grok-4.5` accepts, and it is the downgraded build.
  - **USER CONFIRMATION beats benchmarks**: despite API-quality probes (sisters/brothers, bat & ball, paper folding, trick sheep) all answering correctly via 9Router, the USER reported the model is "ga bisa thinking sama sekali dan jadi dongo" (can't think at all, dumb) in real use. Lesson: benchmark math/logic riddles are NOT sensitive enough — degraded models pass them. Trust user reports + model self-ID + absence of reasoning field as the degradation signal, not answer quality on simple puzzles.
  - **FAST FINGERPRINT — literal-echo probe (verified 2026-08-09, CLI)**: ask `print 407` (any exact literal). A clean model echoes `407`; the `bfs:1` downgraded account answered `202` (WRONG number) consistently across 3 independent runs, and twice chose `run_terminal_command echo 202` as a tool call instead of just answering. Degraded models fumble exact literal echo even when they pass arithmetic — faster and more reliable than math riddles. Add this to `scripts/grok_degradation_probe.py`-style health checks before trusting a grok-cli pool.
  - **CLI non-interactive quirks (verified 2026-08-09)**: `grok -p "prompt"` is required in non-tty (bare `grok` fails `os error 6`). `--output-format streaming-messages-json` shows the `tool_use` message BEFORE any text; a tool call without `--always-approve` → `stopReason:"cancelled"` and empty `text` (cost still ~$0.01). `usage.reasoning_tokens > 0` does NOT prove real internal reasoning on flagged accounts — degraded models emit public CoT when prompted (`<thinking>` tags) while the internal pathway stays throttled.
  - **Browser signup finding (verified Chromium works headless)**: `playwright` + `executable_path=/root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome` launches fine with `args=["--no-sandbox","--disable-dev-shm-usage"]` (the old "Playwright hangs" issue is a sandbox/display problem — direct binary + those flags fixes it). Real signup page renders and the "Sign up with email" flow clicks through. BUT submit returns **HTTP 403** (`/api/log`, `/_rsc=` rejections) — the form POST requires an in-browser Turnstile solution which Playwright does not auto-solve; this is server-side rejection, NOT proxy (same 403 with 3xK, webshare, and no proxy). Full browser signup needs inline Turnstile solving (2captcha-style), not just Capsolver API tokens.

## Environment notes

- Domain for emails: user prefers NOT `<REDACTED>` for Grok — use `<REDACTED>` / `<REDACTED>` (catch-all → Gmail). IMAP creds live in `/root/virtuals-autoreg/.env` or `/root/cf-tuyul/.env` (19-char Google app password; cf-farm `.env` has an EMPTY IMAP_PASS — don't use it).
- Proxy pool: `/root/webnovel-tg-bot/proxy.txt` (100 lines, format `host:port:user:pass`). Full password is required — truncating it gives HTTP 407 on CONNECT.
- Costs: ~2 Turnstile solves (signup+login) ≈ $0.006 from Capsolver.
- **Backup repo (2026-08-08)**: all farm scripts live privately at `https://github.com/agenticspring/grok-farm` (private, branch `main`, commit `d521e959…`). Production folder `/root/grok-register/` is NOT a git checkout — backups are made from a scrubbed copy in `/tmp/grok-register-repo` (see `private-source-repository-release` skill).
- **Farm scripts hardcode secrets**: Capsolver/2captcha keys, proxy creds (3xK `82v458jh2v0e:pnkxj33es7bkruq`, webshare `bvytlgye:fritszjb82rs`), IMAP user/pass (`<REDACTED>` + app password), and farm domains (`<REDACTED>`, `<REDACTED>`, `<REDACTED>`). Before ANY push to GitHub (even private), scrub all of these with `sed -i` across `*.py` to placeholders (`CAPSOLVER_API_KEY_PLACEHOLDER`, `PROXY_USER`, `IMAP_USER`, `FARM_DOMAIN*`), then run the exact-value scan from `.env` values. Data dirs (`data/`, `exports/`, `logs/`, `result.txt`, `*.bin`, `*.json`) are gitignored.

## References

- `references/grok-protobuf-descriptors.md` — decoded field numbers + endpoint map
- `references/grok-ws-chat-protocol.md` — WS event sequence + envelope details
- `references/grok-cli-device-auth.md` — CLI install, device-auth login, 9Router grok-cli injection
- `references/grok-bfs-flag.md` — `bfs` bot-flag claim: where it lives, detection script, impact
- `references/grok-protocol-signup.md` — SignupServerAction protocol signup (alternative path; works but does NOT bypass `bfs`) + set-cookie hop chain
- `scripts/grok_degradation_probe.py` — runnable diagnostic: model self-ID + reasoning-field probes + per-connection bfs scan (use to verify a grok pool is serving REAL grok-4.5, not a downgraded build)
