# Grok AuthManagement protobuf descriptors (decoded from JS fileDesc)

Discovered 2026-08 from `accounts.x.ai/sign-up` Next.js chunks. The proto file is
`prod/mc/auth-proto/proto/auth_mgmt/auth_mgmt.proto`, package `auth_mgmt`, service
`AuthManagement`. Wire field numbers were hexdumped from the base64 `fileDesc(...)`
blobs — **declaration order in the readable dump is NOT the wire order**.

## gRPC-web framing

```
POST https://accounts.x.ai/auth_mgmt.AuthManagement/{Method}
Content-Type: application/grpc-web+proto
X-Grpc-Web: 1
Body: b'\x00' + struct.pack('>I', len(payload)) + payload
```

Response parse: repeated `[flag:1][len:4][payload]`; final frame is the
`grpc-status:0\r\n` trailer. Errors surface as `grpc-status:13` +
`grpc-message` header OR in the body trailer. Always read the header first
(grpc-web puts status in headers when it fails to decode the body).

## Field numbers (verified)

### CreateEmailValidationCodeRequest
- 1 = email (string)

### VerifyEmailValidationCodeRequest
- 1 = email
- 2 = email_validation_code (string; strip dash from `XXX-XXX`)
- 3 = delete_on_success (bool) — **true consumes the code**
- 4 = return_verification_token (bool)

### CreateUserRequest (nested inside CreateUserAndSessionRequest)
- 1 = given_name
- 2 = family_name
- 3 = email
- **5 = clear_text_password** (NOT 4!)
- **6 = tos_accepted_version** (int32; value 1)
- **7 = anti_abuse_token** (AntiAbuseToken message)

### CreateUserAndSessionRequest
- 1 = create_user_request (CreateUserRequest, length-delimited nested)
- **6 = anti_abuse_token** (AntiAbuseToken) — NOT 2
- 7 = num_one_time_links
- 8 = tesla_request_id
- **9 = email_validation_code**
- **11 = castle_request_token** (empty string accepted)

### AntiAbuseToken
- 1 = turnstile_token (string)
- 2 = token (string)

### CreateSessionRequest (login)
- 1 = credentials (Credentials message)
  - 1 = email_and_password (EmailAndPasswordRequest: 1=email, 2=clear_text_password)
  - 2 = oauth, 3 = apple, 4 = id_token, 5 = oauth_data_token, 6 = workos
- **4 = anti_abuse_token** (AntiAbuseToken) — login ALSO requires Turnstile
- 5 = num_one_time_links
- **6 = tos_version** (int32)
- 8 = tesla_request_id
- 10 = castle_request_token

### CreateSessionResponse
- 1 = session (user id inside)
- 2 = session_cookie (JWT, HS256; payload = `{"session_id": "..."}` only)
- 3 = one_time_link_tokens
- 4 = is_new_user (bool)

## Other RPCs seen (all under /auth_mgmt.AuthManagement/)
- GetUser (Empty) — needs session cookie; `grpc-status:16` if you pass the JWT as Bearer (that's for management keys, not user sessions)
- ListActiveSessions (Empty) — works with session cookie
- GetConsumerSubscriptions (Empty) — empty = free tier, no paid subscription
- ListModels (Empty) — full model catalog (grok-4.5, grok-4.20, grok-code-fast-1, etc.)
- CreateGrokCliOnetimeCode (Empty) — returns grpc-status:12 "Legacy CLI token creation is disabled. Use OAuth2 login instead"
- GetAuthUrl — takes `antiAbuseToken.turnstileToken` as query-style dotted param

## Protobuf helpers (minimal Python)

```python
def _varint(n):
    out = b''
    while True:
        b = n & 0x7F; n >>= 7
        if n: out += bytes([b | 0x80])
        else: out += bytes([b]); return out

def proto_string(field_num, s):
    tag = (field_num << 3) | 2
    b = s.encode() if isinstance(s, str) else s
    return bytes([tag]) + _varint(len(b)) + b

def proto_varint(field_num, val):
    return bytes([(field_num << 3) | 0]) + _varint(val)

def grpc_frame(payload):
    return b'\x00' + struct.pack('>I', len(payload)) + payload
```

## Endpoint discovery recipe

1. `requests.Session(impersonate='chrome124')` GET `https://accounts.x.ai/sign-up` → 200 (plain curl → 403 CF challenge).
2. `src="(/_next/static/chunks/...)"` from HTML → download chunks.
3. grep chunks for `function p(e,t){return fetch` → baseUrl default `/api/auth` (which 404s).
4. The real transport: `createClientTransport("xai-account","",...)` in a chunk; URL builder `ea(e,t){return e.toString().replace(/\/?$/, '/'+t.parent.typeName+'/'+t.name)}`.
5. CSP `connect-src` header lists `auth.x.ai`, `auth.grok.com` etc. — but the gRPC endpoint stays on `accounts.x.ai` same-origin.
6. typeName from `fileDesc` base64 decode: `prod/mc/auth-proto/proto/auth_mgmt/auth_mgmt.proto auth_mgmt ... AuthManagement`.
7. Method name = PascalCase (e.g. `CreateEmailValidationCode`), NOT camelCase — the camelCase path 404s.
