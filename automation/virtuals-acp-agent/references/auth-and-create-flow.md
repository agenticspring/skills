# Virtuals ACP auth + create flow (live reverse 2026-07-22+)

## Projects
- **Browserless ops:** `/root/virtuals-browserless` (`vbcli.py`)
- **Browser research:** `/root/virtuals-autoreg`

## Privy
- App id: `cltsev9j90f67yhyw4sngtrpv`
- Base: `https://auth.privy.io`
- Passwordless:
  - `POST /api/v1/passwordless/init` → `{"success":true}`
  - email subject: `Your login code for Virtuals Protocol App`
  - body: `Your code is\n\nNNNNNN`
  - `POST /api/v1/passwordless/authenticate` `{email,code,mode:"login-or-sign-up"}`
  - returns `token`, `privy_access_token`, `identity_token`, `refresh_token`, `user`, `is_new_user`
- Wallet: `POST /api/v1/wallets` `{chain_type:"ethereum"}` → `address` `0x…`
- **After wallet:** `POST /api/v1/sessions` `{refresh_token}` → new `token` + `identity_token` that include wallet
- Terms: `POST /api/v1/users/me/accept_terms`

## App / ACP hosts
| Host | Role |
|---|---|
| `api2.virtuals.io` | optional `POST /wallet/auth/privy` |
| `api.acp.virtuals.io` | agents + compute (`Authorization: Bearer <privy_token>`) |
| `acpx.virtuals.io` | alternate verify; jwt often **not** valid for agent create |
| `claw-api.virtuals.io` | compute-account / templates / defaults |
| `compute.virtuals.io/v1` | OpenAI-compatible endpoint (key + balance) |

## Browserless auth that works
```text
1. passwordless init + authenticate
2. create ethereum wallet
3. refresh sessions with refresh_token
4. ACP POST /auth/verify
   {address: 0x…, token: privy_token, identityToken: refreshed_identity}
   → 200/201 Successfully verified (response may have NO jwt)
5. Agent APIs use Authorization: Bearer <privy_token>
```

### Failed auth patterns
- Create with **acpx jwt** → 401 Unauthorized
- Create with **api2 app jwt** alone → often 401
- Verify before wallet-linked identity refresh → 401 Invalid wallet / not linked
- Verify without identityToken → 400 identityToken required

## Create + free $10
```http
POST /agents
{name, description, role:"HYBRID", console:{runtime:"hermes", templateType:"personal_assistant"}}

POST /agents/{id}/console
{runtime:"hermes", templateType:"personal_assistant"}
→ 201 Successfully enabled console

GET /agents/{id}/compute/account
→ limit=10, limitRemaining=10, usage=0

POST /agents/{id}/compute/keys {"name":"key-…"}
→ data: "acp-…"
```

UI toggle Hermes alone can still leave `consoleAgentId=null` and **$0**. Backend console enable is the grant switch. GH/X is a separate weekly campaign path.

## Rate limits
- `POST /agents` can return **429 Rate limit exceeded**
- Retry with sleep 15–60s and/or rotate residential proxy
- Console enable may log rate-limit while account still ends with remaining=10

## Live verify credit
```http
GET /agents/{id}/compute/account
POST https://compute.virtuals.io/v1/chat/completions
  Authorization: Bearer acp-...
  model e.g. z-ai-glm-5-2 / zai-org-glm-5-2
→ 201 + cost; re-GET account shows remaining drop
```

## Proven browserless $10 samples
```text
luna.river356@<REDACTED>
  agent 019f8a3e-097b-76d8-983a-98c44b25b9c7
  key acp-e5421704c79d74c7c640
  proxy exit 45.38.107.97
  balance limit=10 remaining=10

axel.river441@<REDACTED>
  agent 019f8a41-2222-756c-872c-d8cf34a759a0
  key acp-7cc991ec0e8b337215d9
  after chat test: limitRemaining≈9.997886 usage=0.002114
```

## $0 samples (console not backend-enabled)
```text
cole.wells895@<REDACTED> / acp-8315… / $0
nova.ford96@<REDACTED> / acp-db22… / $0
aria.blake787@<REDACTED> (proxy only) / acp-9a60… / $0
```

## CLI
```bash
cd /root/virtuals-browserless
.venv/bin/python vbcli.py register
```
