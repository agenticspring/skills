# Virtuals ACP free credit reality (2026-07-22, corrected)

Target: `https://app.virtuals.io/acp/new` and agent compute tab.

## What works without funding
1. Privy **email OTP** on catch-all domain (`<REDACTED>` preferred; `<REDACTED>` also OK).
2. Embedded **EVM wallet** auto-created (Privy `POST /api/v1/wallets` `chain_type=ethereum`).
3. Agent create → page `/acp/agents/<uuid>`.
4. Compute API key create → `acp-<hex>`.
5. Endpoint base: `https://compute.virtuals.io/v1`.

## Free $10 auto-grant (proven)
**Not** bare register alone. **Not** only UI Console toggle.

After agent create, enable console on backend:
```http
POST https://api.acp.virtuals.io/agents/{id}/console
{"runtime":"hermes","templateType":"personal_assistant"}
→ 201 Successfully enabled console
```

Then account funds:
```http
GET /agents/{id}/compute/account
→ limit=10, limitRemaining=10, usage=0
UI: $10.00
```
**No GitHub/X required** for this initial grant (user friend path confirmed; live re-proven with proxy).

### Failure mode before this was known
- UI Hermes ON, Register OK, API key OK
- but `consoleAgentId: null` / claw `runtime: openclaw`
- `limitRemaining=0` forever until console API

### IP / proxy
- Direct VPS and residential proxy both can create agents
- Proxy alone did not unlock $10
- Console enable unlocked $10 (sample exit IP `31.56.127.193`)

## Secondary free path (still exists)
Compute tab developer-campaign: connect **GitHub or X** for free **weekly** inference credits / enroll-claim flow. Separate from the initial $10 console grant.

## Auth chain (browser reverse)
```text
Privy passwordless init/authenticate
  → accept_terms
  → create embedded ethereum wallet (required)
  → POST https://api2.virtuals.io/wallet/auth/privy {accessToken}
  → POST https://api.acp.virtuals.io/auth/verify {address, token, identityToken}
  → Authorization: Bearer <acp jwt>
  → POST https://api.acp.virtuals.io/agents  (multipart in UI)
  → POST /agents/{id}/console {runtime:hermes, templateType:personal_assistant}  # $10
  → GET  /agents/{id}/compute/account
  → POST /agents/{id}/compute/keys {name} → "acp-..."
```

### Auth pitfalls
- Email-only Privy user without wallet → `No wallet accounts linked` on api2 exchange.
- ACP verify with email as address → invalid wallet.
- Using acpx JWT on `api.acp.virtuals.io` may still 401 — prefer JWT from the same host you call.
- Browser UI create uses multipart; empty body capture in tooling does not mean empty request.

## Create payload shape (from page reverse)
```json
{
  "name": "AgentName",
  "description": ">= min chars",
  "role": "agent",
  "console": {
    "runtime": "hermes",
    "templateType": "personal_assistant"
  }
}
```
Even when UI selects this, backend may need explicit `POST .../console` after create.

Register modal: **Launch Agent** → **Register Agent**.

## API key
```text
POST /agents/{id}/compute/keys  {"name":"spring-key-1"}
→ 201 {"message":"Successfully created compute API key","data":"acp-..."}
```
Key can exist with **zero** balance if console never enabled.

## Ops project
- `/root/virtuals-autoreg/`
- Browser flow: `browser_create_agent_v2.py` (force console attach after create)
- Ledger: `exports/virtuals_accounts.xlsx`, `accounts.txt`

## Success checklist for “1 akun = saldo $10 + api key”
1. Email verified + wallet linked  
2. Agent id exists  
3. Backend console enabled (hermes + personal_assistant)  
4. `compute/account` **limitRemaining == 10** (or > 0)  
5. API key `acp-…` saved once  
6. XLS row complete  

If step 4 fails after console enable, report honestly with API body.