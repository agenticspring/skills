# Grok / x.ai Registration Case (2026-08)

Full working detail for browserless Grok account creation. Base: `https://accounts.x.ai`, proto package `auth_mgmt`, service `auth_mgmt.AuthManagement`.

## Endpoint pattern
```
POST https://accounts.x.ai/auth_mgmt.AuthManagement/<MethodPascalCase>
```
All RPCs are gRPC-web frames. `createClientTransport("xai-account", "", {...})` → baseUrl `""` (same-origin). The `/api/auth/*` REST paths in JS (e.g. `sign-up/create-account`) are NOT the live endpoints — they 404 from curl.

## Field numbers (from fileDesc descriptor, authoritative)
### CreateEmailValidationCodeRequest
- 1 = email (string)
- 2 = email_template (enum, optional)
- 3 = castle_request_token (string, optional)

### VerifyEmailValidationCodeRequest
- 1 = email
- 2 = email_validation_code
- 3 = delete_on_success (bool)
- 4 = return_verification_token (bool)

### CreateUserRequest (nested in CreateUserAndSessionRequest.create_user_request)
- 1 = given_name
- 2 = family_name
- 3 = email
- 5 = clear_text_password   (NOT 4!)
- 6 = tos_accepted_version (int32; Grok value = 1, const TOS_ACCEPTED_VERSION=1)
- 7 = anti_abuse_token (AntiAbuseToken message)
- 8 = birth_date (Timestamp)
- 9 = marketing_email_opt_in (bool)

### AntiAbuseToken
- 1 = turnstile_token (string)
- 2 = token (string)

### CreateUserAndSessionRequest
- 1 = create_user_request (CreateUserRequest)
- 6 = anti_abuse_token   (NOT 2!)
- 7 = num_one_time_links
- 8 = tesla_request_id
- 9 = email_validation_code   (NOT 5!)
- 11 = castle_request_token   (NOT 6!)

### CreateSessionRequest (login)
- 1 = credentials (Credentials oneof)
  - Credentials.1 = email_and_password (EmailAndPasswordRequest)
    - EmailAndPasswordRequest.1 = email
    - EmailAndPasswordRequest.2 = clear_text_password
- 4 = anti_abuse_token   (NOT 2!)
- 5 = num_one_time_links
- 6 = tos_version   (NOT 4!)
- 8 = tesla_request_id
- 10 = castle_request_token

### CreateSessionResponse
- 1 = session (message: user id + device/session info)
- 2 = session_cookie (JWT string — use as the auth session cookie)
- 3 = one_time_link_tokens
- 4 = is_new_user (bool; 1 on fresh signup)

## Working flow (4 RPCs)
1. `CreateEmailValidationCode` — payload `proto_string(1, email)`. → 200, email sent.
2. Poll IMAP (exact To: match), code regex `([A-Z0-9]{3}-?[A-Z0-9]{3})` on Subject → e.g. `WEG-D4V`.
3. `VerifyEmailValidationCode` — `proto_string(1,email) + proto_string(2,code) + proto_bool(3,False) + proto_bool(4,False)`. Keep delete_on_success=False if the code is still needed for step 4. Returns JWT in field 1 when return_verification_token=True.
4. Solve Turnstile through the SAME proxy (sitekey `0x4AAAAAAAhr9JGVDZbrZOo0`).
   `CreateUserAndSession` — `proto_bytes(1, create_user) + proto_bytes(6, anti) + proto_string(9, code) + proto_string(11, "")` where anti = `proto_string(1, turnstile_token)`.
   → 200, response 493 bytes, is_new_user=1.

Login: `CreateSession` — `proto_bytes(1, creds) + proto_bytes(4, anti) + proto_varint(6, 1)` where creds = `proto_bytes(1, emailpw)`, emailpw = `proto_string(1,email)+proto_string(2,password)`. Requires fresh Turnstile too.

## Verification
- `ListActiveSessions` (Empty body) with session cookie → 200 + session list.
- `GetUser` (Empty body) with session cookie → 200 + email, names, entitlements `user:grok-web-access`, `user:grok-code-cli`.
- GetUser with JWT as `Authorization: Bearer` → grpc-status 16 (`invalid bearer token` — management keys only).

## Runtime facts
- Verification email: From `SpaceXAI <noreply@x.ai>`, Subject `SpaceXAI confirmation code: XXX-XXX`.
- Password policy: GrokCLI2026! style passes; plain short passwords get WeakPassword warnings.
- Session cookies set via `s.cookies.set(name, jwt, domain="accounts.x.ai")` for authenticated RPCs.
- CSP `connect-src` on accounts.x.ai lists: auth.x.ai, auth.grok.com, auth.grokusercontent.com, auth.grokipedia.com (hint only — live API is same-origin gRPC path).
- Turnstile sitekey: `0x4AAAAAAAhr9JGVDZbrZOo0` (signup page).
- Castle publishable key: `pk_p8GGWvD3TmFJZRsX3BQcqAv9aFVispNz` (client-side only; castle_request_token can be sent empty — signup does not require a valid Castle token).
