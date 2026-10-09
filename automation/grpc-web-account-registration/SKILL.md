---
name: grpc-web-account-registration
description: Register accounts browserless on gRPC-web/ConnectRPC sites.
version: 1.0.0
category: automation
tags: [registration, grpc-web, connectrpc, protobuf, browserless, turnstile, xai, grok]
---

# gRPC-web Account Registration (browserless)

Use when a site's signup runs through a gRPC-web / ConnectRPC protobuf API (common in Next.js apps with `@connectrpc/connect-web`), and you want to create accounts WITHOUT a browser. Proven on x.ai / Grok (`accounts.x.ai`) 2026-08.

## When to use
- Site frontend uses ConnectRPC / gRPC-web (look for `createClientTransport`, `TransportProvider`, proto `fileDesc` in JS bundles).
- REST guesses (`/api/auth/...`) return 404 JSON while the browser works fine — the real endpoint is `/{package}.{Service}/{MethodPascalCase}`.
- User wants browserless farming; avoid Camoufox/Playwright cost.

## Dez preferences (Grok farm)
- Domain: use `<REDACTED>` (or `<REDACTED>`) — **NOT `<REDACTED>`** (explicit user instruction 2026-08).
- Register with random first/last names + strong password (`GrokCLI2026!` style); capture `email:password` to `result.txt`.
- Goal: accounts usable for Grok CLI (entitlements `user:grok-code-cli`), injectable into 9Router `grok-cli` provider.

## Core discovery path (do in this order)
1. **Warm the page** with curl_cffi `impersonate=chrome124` — x.ai pages 403 on plain curl but pass with impersonation.
2. **Read the CSP header** of the warm response — `connect-src` leaks the real API hosts (x.ai: `auth.x.ai`, `auth.grok.com`, ...). But those hosts 404 too; the API is actually same-origin behind a gRPC path.
3. **Download JS chunks** listed in the HTML (`src=".../_next/static/chunks/...`), save each to `logs/js/`.
4. **Find the transport**: grep chunks for `createClientTransport` / `TransportProvider`. x.ai: `createClientTransport("xai-account", "", {...})` → baseUrl empty = same-origin; URL = `{baseUrl}/{typeName}/{Method}` where `ea(e,t)` builds `/${t.parent.typeName}/${t.name}`.
5. **Decode proto descriptor**: chunks contain `fileDesc("<base64>")` — base64-decode; the big one (~100KB) holds all message field numbers. Dump the hex region around a message name (`CreateUserRequest`) to read `18 05` = field 5 etc. Do NOT guess field numbers — the descriptor is authoritative and numbers are non-obvious (x.ai `CreateUserRequest` has password at field 5, tos at 6, anti_abuse at 7).
6. **List RPC methods**: descriptors expose `method.<Name>` in order; service `typeName` = `<proto_package>.<Service>` (x.ai: `auth_mgmt.AuthManagement`).

## Call format (gRPC-web)
```
POST https://<host>/<package>.<Service>/<MethodPascalCase>
Content-Type: application/grpc-web+proto
X-Grpc-Web: 1
Accept: application/grpc-web+proto
Origin: https://<page-host>
Body: grpc frame = b'\x00' + struct.pack('>I', len(proto)) + proto
```
- JSON body → `grpc-status: 13 invalid compression flag: 123` (server read `{` as flag). Must send protobuf frames.
- Response is framed: `[flag:1][len:4][payload]` repeated; trailers include `grpc-status`. Also check the `grpc-status`/`grpc-message` HTTP headers — grpc-web errors often live there with empty body.
- Success = `grpc-status: 0` or absent; non-zero = error code (3=invalid arg, 7=missing anti-abuse, 13=decode/internal).

## Turnstile (Cloudflare) — MUST be IP-bound
- Sitekey is in page/JS (`0x4AAAAAAAhr9JGVDZbrZOo0` for x.ai signup).
- Capsolver `AntiTurnstileTaskProxyLess` gives a token that FAILS server-side (`Failed to verify Cloudflare turnstile token`) because the token is bound to the solver's IP, not yours.
- **Fix**: solve with `AntiTurnstileTask` + `proxy` AND send the API request through the SAME proxy (`proxies={"http":..., "https":...}` per-request in curl_cffi; session-level `s.proxies` can 407).
- x.ai AntiAbuseToken protobuf: `turnstile_token` = field 1.

## Verification-code gotcha
Grok/x.ai sends a 6-char ALPHANUMERIC code `XXX-XXX` (e.g. `WEG-D4V`), not 6 digits. Poll IMAP by exact To: and regex `([A-Z0-9]{3}-?[A-Z0-9]{3})` from the Subject. VerifyEmailValidationCode with `delete_on_success=true` burns the code — keep it false if you still need it for CreateUserAndSession.

## Proxy pitfalls
- `host:port:user:pass` — use the FULL password from the proxy file. A truncated password (e.g. `pnkxj33` instead of `pnkxj33es7bkruq`) gives `CONNECT tunnel failed 407` on first request while a later test with the full line succeeds. Always `head -1 proxy.txt` and copy the exact line.
- Test a proxy 2x before relying on it; some are flaky.

## Verification (prove usable, not just created)
1. `CreateSession` (login) with same credentials + fresh turnstile → grpc-status 0 + session JWT.
2. `ListActiveSessions` and `GetUser` with the session cookie → confirm entitlements (x.ai: `user:grok-web-access`, `user:grok-code-cli` = usable for Grok CLI).
- GetUser with a user JWT as Bearer fails (`invalid bearer token` — that's for management keys); use the session cookie instead.

## References
- `references/grok-xai-case.md` — full x.ai field numbers, RPC list, request/response byte structure, working flow order.
