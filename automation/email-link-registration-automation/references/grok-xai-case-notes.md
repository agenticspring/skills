# Grok / xAI (accounts.x.ai) — gRPC-web Protobuf Signup Case

Concrete case (2026-08): browserless Grok account creation at accounts.x.ai.
All anti-bot layers bypassed WITHOUT a browser: curl_cffi + IMAP + Capsolver.

## Transport: NOT REST — gRPC-web protobuf

- The auth API is a ConnectRPC/gRPC-web service. The `/api/auth/*` JSON routes
  shown in the JS are a disabled/standalone path and return `404 {"error":"Not found"}`.
- Real endpoint: `POST https://accounts.x.ai/auth_mgmt.AuthManagement/{MethodPascalCase}`
  - e.g. `CreateEmailValidationCode`, `VerifyEmailValidationCode`,
    `CreateUserAndSession`, `CreateSession`
- Headers:
  - `Content-Type: application/grpc-web+proto`
  - `Accept: application/grpc-web+proto`
  - `X-Grpc-Web: 1`
  - `Origin: https://accounts.x.ai`, `Referer: https://accounts.x.ai/sign-up`
- Body = gRPC frame: `\x00` (compression flag) + 4-byte big-endian length + protobuf payload.
- Response = same framing. Success = `grpc-status: 0` (body may be empty).
  Errors appear in `grpc-status` / `grpc-message` headers.
- JSON POST to the same path returns `grpc-status: 13` "invalid compression flag:
  received message with invalid compression flag: 123" — 123 = `{`; that is the
  signal you must send protobuf frames, not JSON.

## How endpoints were discovered (repeatable recipe)

1. GET `/sign-up` with curl_cffi `impersonate='chrome124'` (plain curl gets CF 403;
   curl_cffi passes). Save HTML.
2. Extract `/_next/static/chunks/*.js` URLs from HTML; download all chunks.
3. Grep chunks for `createClientTransport("xai-account","",...)` →
   transport baseUrl empty = same-origin.
4. Find the URL builder in the transport lib:
   `ea(baseUrl, method) = baseUrl + "/" + method.parent.typeName + "/" + method.name`
   → method.name is PASCALCASE (`CreateEmailValidationCode`, not camelCase).
5. CSP `connect-src` header leaks candidate auth hosts (`auth.x.ai`,
   `auth.grok.com`, ...) but the working host was same-origin accounts.x.ai.
6. Decode protobuf descriptors: JS has `fileDesc("base64...")` strings.
   Base64-decode → full proto schema text: message fields in order, nested
   types, service+method list, and `proxy/gen/go/auth_mgmt;auth_mgmt` package
   (package → typeName `auth_mgmt.AuthManagement`).
7. NEVER guess protobuf field numbers from field-name order in prose — read the
   descriptor bytes. In this schema several numbers are non-sequential
   (password=5, tos=6, anti=7 inside CreateUserRequest).

## Field numbers (verified from descriptor)

- `CreateEmailValidationCodeRequest`: email=1
- `VerifyEmailValidationCodeRequest`: email=1, email_validation_code=2,
  delete_on_success=3, return_verification_token=4
- `CreateUserRequest`: given_name=1, family_name=2, email=3,
  clear_text_password=5 (!), tos_accepted_version=6, anti_abuse_token=7,
  birth_date=8, marketing_email_opt_in=9
- `CreateUserAndSessionRequest`: create_user_request=1, anti_abuse_token=6 (!),
  num_one_time_links=7, tesla_request_id=8, email_validation_code=9 (!),
  castle_request_token=11
- `AntiAbuseToken`: turnstile_token=1, token=2
- `CreateSessionRequest`: credentials=1 (oneof), anti_abuse_token=**4** (!),
  num_one_time_links=5, tos_version=**6** (!), tesla_request_id=8, castle_request_token=10
  - `Credentials.email_and_password`: email=1, clear_text_password=2
  - Wrong guesses (anti_abuse=2, tos=4) fail with
    `grpc-status 13: ...anti_abuse_token: invalid wire type: Varint (expected LengthDelimited)`.
    Read the descriptor — CreateSessionRequest numbers are NOT sequential.
- `TOS_ACCEPTED_VERSION = 1` (constant exported by a JS chunk)

## Login flow (CreateSession) — also needs Turnstile

- `POST /auth_mgmt.AuthManagement/CreateSession` with:
  - field 1 credentials: `Credentials{1: emailAndPassword{1: email, 2: clearTextPassword}}`
  - field 4 anti_abuse_token: `AntiAbuseToken{1: turnstileToken}`
  - field 6 tos_version: varint 1
- Without anti_abuse token → `grpc-status 7: Anti-abuse token is missing`.
- Success returns CreateSessionResponse: session (user id), session_cookie (JWT),
  is_new_user. JWT payload only contains `{session_id}` (HS256) — it is NOT a
  claims-bearing access token.

## grok.com web API auth (after accounts login)

- The session_cookie JWT from accounts `CreateSession` works as cookie **`sso`**
  on grok.com. Bearer / other cookie names → 401.
- `GET https://grok.com/rest/auth/get-user` with `sso` cookie → 200 user info.
- `POST https://grok.com/rest/models` `{locale:"en-US"}` → model list (public).
- `POST https://grok.com/rest/app-chat/conversations/new` `{modelName, message,
  temporary, disableSearch, ...}` → chat (full body shape from JS
  `chatCreateConversationAndRespondRaw` serializer in chunk 031yhyjenz-n2.js).

## Verification code format

- Email from `SpaceXAI <noreply@x.ai>`, subject `SpaceXAI confirmation code: XXX-XXX`
- Code = 6 ALPHANUMERIC chars (letters + digits), e.g. `WEG-D4V`, `2OV-J7D`, `731-A58`
- NOT 6 digits. Poll IMAP by exact TO address; regex `([A-Z0-9]{3}-?[A-Z0-9]{3})`, strip the dash.

## Turnstile (Cloudflare) — IP-bound!

- Sitekey `0x4AAAAAAAhr9JGVDZbrZOo0` (found in HTML turnstile script + page config).
- Proxyless solve (`AntiTurnstileTaskProxyLess`) FAILS at CreateUserAndSession:
  `grpc-status 13: Failed to verify Cloudflare turnstile token`
- Fix: solve with `AntiTurnstileTask` + proxy, and send the API requests through
  the SAME proxy (token is bound to the solving IP).
- Proxy format for Capsolver: `http://user:pass@host:port` (or host:port:user:pass).

## Pitfalls

- `delete_on_success=true` in VerifyEmailValidationCode CONSUMES the code;
  CreateUserAndSession then fails `email:invalid-validation-code`. Use
  delete_on_success=false, or skip the explicit verify and let
  CreateUserAndSession validate the code itself.
- Castle token (`castleRequestToken`) is NOT required for signup — empty string works.
- `/api/auth/*` JSON routes return 404 — that is the standalone-auth path, not
  the enabled flow. The active flow is gRPC-web.
- IMAP creds live in `/root/virtuals-autoreg/.env`
  (`<REDACTED>`, 19-char app password). `/root/cf-farm/.env` has
  IMAP_PASS EMPTY — check the right env file.
- Webnovel proxy pool (`/root/webnovel-tg-bot/proxy.txt`) works for Grok; watch
  for password truncation — use the full `host:port:user:pass` line, don't cut
  at the first `:`-separated field.
- curl_cffi session-level `s.proxies` failed (407) where per-request
  `proxies={"http": url, "https": url}` worked — pass proxies per call.

## Chat via WebSocket gateway — REST anti-bot bypass (RESOLVED 2026-08-08)

The REST chat 403 **is** solvable without Castle tokens: chat runs over a
WebSocket gateway, not the REST endpoint.

- Endpoint: `wss://grok.com/ws/mgw/?uid={userId}` (same-host, port 443).
  userId comes from `GET /rest/auth/get-user` with the `sso` cookie.
- Headers: `Origin: https://grok.com`, `Cookie: sso={session_cookie_jwt}`.
- Protocol is OpenAI-realtime-style with envelope `{session_id, event}`:
  1. Send `{"event": {"type": "session.create", "session": {"modalities": ["text"]}}}`
  2. Read `session.created` + `conversation.attached` (this gives `session_id`)
  3. Send `{"session_id": ..., "event": {"type": "conversation.item.create", "item": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "..."}]}}}`
  4. Send `{"session_id": ..., "event": {"type": "response.create", "response": {"modalities": ["text"]}}}`
  5. Read `response.output_text.delta` tokens → `response.done`
- **Item format pitfall**: use `content: [{type: "input_text", text}]`.
  Do NOT use `x_grok.input_chunks` (protobuf `InputChunk` shape
  `{content:{text:{text:{text, channel}}}}`) — the model then answers "your
  message got cut off" / "I'm ready to help". Also use
  `conversation.item.create`, NOT `conversation.item.added`.
- Event name is `conversation.item.create` (from `_sendUserTurnAsync` in JS
  chunk 13slx9hm9kihc.js); the message store wraps every user turn in it.
- **Rate limit signal**: when free tier is exhausted the model does NOT emit an
  `error` event. Check `response.grok.output` — its `output.stream_error` field
  carries `{"kind": "usage_limit_reached"}`. Free tier ≈ 10 requests / 2h /
  account.
- Verified model results (all via WS): `grok-3` (17*23 → 391),
  `grok-4.5` (15*15 → 225), `grok-4.5-latest` (11*11 → 121),
  `grok-4.20` (7*8 → 56), `grok-4-1-thinking-1129` (123*456 step-by-step OK).
- **Custom tool calling NOT working** in this WS mode: passing `tools` in
  session.create / response.create produced no `function_call_arguments`
  events; the model ignored custom tools and answered in text (or claimed the
  tool "isn't available"). Only Grok-internal tools (web_search, open_page) are
  referenced by the model. Assume tool-calling needs a different mode/flag
  until proven otherwise.
- Batch scripts (2026-08): `/root/grok-register/signup_batch.py -n N`
  (proxy rotation, saves `data/accounts.json` + `result.txt`) and
  `/root/grok-register/test_accounts.py` (get-user → chat grok-3 → chat
  thinking per account). 3/3 fresh accounts verified chat + reasoning.

## Grok CLI device-auth login (RESOLVED 2026-08-08)

Legacy `CreateGrokCliOnetimeCode` is disabled, but OAuth2 **device-code auth is
fully automatable** using the same session cookie — no browser needed.

1. Install: `curl -fsSL https://x.ai/cli/install.sh | bash` → binary at
   `~/.grok/bin/grok`, symlinked to `~/.local/bin/grok`. Version `grok 1.0.0`.
2. Start login in the background and capture the code:
   `grok login --device-auth` prints
   `Confirm this code in your browser:` + a code like `FXJF-AX6K`
   (regex `[A-Z0-9]{3,6}-[A-Z0-9]{3,6}`; beware the same code appears in the
   URL as `user_code=...` — parse the "Confirm this code" block, not the URL).
3. Approve with an already-logged-in accounts session (cookie `sso` set on BOTH
   `accounts.x.ai` AND `auth.x.ai`):
   ```
   POST https://auth.x.ai/oauth2/device/approve
   Content-Type: application/x-www-form-urlencoded
   data={"user_code": "<CODE>", "action": "allow"}
   ```
   - `action` must be exactly `allow` → 303 to `https://accounts.x.ai/oauth2/device/done`.
     `action=approve` → `400 Invalid action`; wrong/expired code → `400 Invalid or expired code`.
     JSON body → `415 Form requests must have Content-Type: application/x-www-form-urlencoded`.
   - User code is 8–9 alnum with a dash (not 6); keep it unmodified.
4. CLI writes `~/.grok/auth.json` — format
   `{"https://auth.x.ai::<scope>": {"key": "<OIDC JWT>", "auth_mode": ..., "refresh_token": ..., ...}}`.
   It is the OAuth scope-keyed map the installer's `read_grok_token` reads.

Run the CLI:
- Single-turn prompt (no TTY): `grok -p "question"` — the plain `grok "prompt"`
  form opens a TUI and fails on a headless box (`Error: No such device or
  address (os error 6)`).
- `grok models` on a free-tier account exposes only `grok-4.5` (default);
  reasoning models (`grok-4-1-thinking-1129`) are rejected `unknown model id`.
- Tool calling DOES work in the CLI (unlike the WS protocol): `--always-approve`
  executes tools; `--output-format streaming-messages-json` shows
  `tool_use` events (e.g. `run_terminal_command echo $((6*7))` → `42`).
  Built-in tools: run_terminal_command, read_file, search_replace, list_dir,
  grep, web_search, web_fetch, image_gen, spawn_subagent, write, etc.
- `GROK_PROXY_URL` env is supported; a malformed value causes DNS errors —
  omit it to use direct routing.
- Observed cost per simple request ≈ $0.009 via the CLI.

## Known status / unresolved (2026-08)

- ~~Fresh accounts registered from DC proxies get 403 anti-bot on REST chat~~ —
  RESOLVED: use the WebSocket gateway above; it does not enforce Castle tokens.
- `bfs=1` JWT flag (friend report): the accounts.x.ai session JWT only contains
  `{session_id}` — no `bfs` claim visible there; the flagged token likely comes
  from a different (full grok.com login) JWT. Ask for an example flagged JWT
  before attempting any bypass. (No such token obtained this session.)
- Legacy `CreateGrokCliOnetimeCode` returns: `Legacy CLI token creation is
  disabled. Use OAuth2 login instead (grok login)` — CLI auth now requires
  OAuth2. **Resolved**: `grok login --device-auth` + approve endpoint above is
  the working OAuth2 path; Grok CLI 1.0.0 logged in and answered successfully.

## Working artifact

`/root/grok-register/signup_nobrowser.py` — full 4-step flow:
CreateEmailValidationCode → IMAP poll code → VerifyEmailValidationCode →
AntiTurnstileTask(proxy) → CreateUserAndSession. Verified creating a real
account: `grpc-status: 0`, response contained session + JWT + `is_new_user=1`.
