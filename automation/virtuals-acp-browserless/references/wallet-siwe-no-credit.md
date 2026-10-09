# Virtuals wallet SIWE create (no credit claim)

Isolated reverse path for **wallet login → create agent without enabling console / claiming $10**.

## Temp project (do not mix with production batch)

```text
/root/virtuals-browserless/tmp_wallet_create/wallet_create_probe.py
/root/virtuals-browserless/tmp_wallet_create/out/
```

**Rule:** when reversing wallet flow, leave production `vbcli.py` / running `screen virtuals-batch` alone unless user explicitly asks to change them.

## Proven Privy SIWE endpoints

```http
POST https://auth.privy.io/api/v1/siwe/init
{"address":"0x…","chainId":"eip155:1"}
→ {"nonce":"…","address":"0x…","expires_at":"…"}

POST https://auth.privy.io/api/v1/siwe/authenticate
{
  "message": "<siwe text>",
  "signature": "0x…",
  "chainId": "eip155:1",   # STRING required (number → 400 invalid_data)
  "walletClientType": "metamask",
  "connectorType": "injected",
  "mode": "login-or-sign-up"
}
→ token, identity_token, refresh_token, user.linked_accounts wallet
```

Optional after auth:
```http
POST https://auth.privy.io/api/v1/sessions {"refresh_token":"…"}
POST https://api2.virtuals.io/wallet/auth/privy {"accessToken":"<privy token>"}
POST https://api.acp.virtuals.io/auth/verify
  {"address":"0x…","token":"<privy token>","identityToken":"<identity>"}
```

Bearer for ACP agent APIs = **refreshed Privy token** (same as email path).

## SIWE message template (from Privy frontend SDK)

```text
app.virtuals.io wants you to sign in with your Ethereum account:
{address}

By signing, you are proving you own this wallet and logging in. This does not initiate a transaction or cost any fees.

URI: https://app.virtuals.io
Version: 1
Chain ID: {chain_id_number}
Nonce: {nonce}
Issued At: {iso8601}
Resources:
- https://privy.io
```

Sign with `eth_account` `encode_defunct(text=message)`.

## Create **without** credit claim

```http
POST https://api.acp.virtuals.io/agents
{"name":"…","description":"…","role":"HYBRID"}
```

**Do NOT call** `POST /agents/{id}/console` if the goal is create-only without free credit.

Optional read-only check:
```http
GET /agents/{id}/compute/account
```
(expect limit 0 if console never enabled)

## Live findings (2026-07-22)

| Step | Result |
|---|---|
| SIWE init/auth | ✅ |
| ACP verify | ✅ 201 |
| POST /agents (no console) | often **429** under same create-gate as email path |
| Credit claim | skipped by design |

Wallet login does **not** bypass create-agent rate limit / 403 gate. Auth can be healthy while create is locked.

## Run temp probe

```bash
cd /root/virtuals-browserless
.venv/bin/python tmp_wallet_create/wallet_create_probe.py
.venv/bin/python tmp_wallet_create/wallet_create_probe.py --proxy 'host:port:user:pass'
.venv/bin/python tmp_wallet_create/wallet_create_probe.py --no-proxy --with-console-check
```

`--with-console-check` only **reads** compute; it does not enable Hermes / claim $10.

## Pitfalls

1. `chainId` on authenticate must be **string** `eip155:1` (number fails validation).
2. Do not reuse email OTP flow assumptions for wallet path.
3. Do not enable console if user asked create-only / no credit.
4. Keep private keys only in local `tmp_wallet_create/out/wallet_private_*.json`; never print full PKs.
5. Under global create gate, wallet path still hits 429 — stop and wait cooldown instead of burning proxies.
