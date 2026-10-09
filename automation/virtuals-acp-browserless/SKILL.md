---
name: virtuals-acp-browserless
description: Browserless automation for Virtuals ACP account + agent creation, Hermes console enable, compute-credit verification, and API-key issuance.
version: 1.0.0
author: spring
license: MIT
platforms: [linux]
---

# Virtuals ACP Browserless

Automate Virtuals Protocol ACP without a browser when the goal is:
- create a fresh account with email OTP
- provision the embedded wallet
- create an ACP agent
- enable **Hermes** console with `personal_assistant`
- verify whether the account received the **$10** compute grant
- create a compute API key (`acp-...`)

## When to use

Use this skill when the user wants repeatable, headless creation instead of Playwright/UI clicking, or when you need to debug why the backend did not grant compute credits even though the UI looked correct.

## Core flow

1. **Privy passwordless login** via email OTP.
2. **Create embedded EVM wallet** with Privy.
3. **Refresh the Privy session after wallet creation**.
   - This is critical: the refreshed session returns an `identity_token` that includes the wallet link.
4. **ACP auth/verify** using:
   - `address = wallet address`
   - `token = refreshed Privy token`
   - `identityToken = refreshed identity token`
5. **Create agent** with console payload included.
6. **Immediately force backend console enable** with:
   - `POST /agents/{id}/console`
   - body: `{"runtime":"hermes","templateType":"personal_assistant"}`
7. **Poll compute/account** until `limit` / `limitRemaining` appear.
8. **Create compute API key**.

## Critical findings

### 1) UI selection is not enough
The UI can show:
- Console ON
- Hermes selected
- Personal Assistance selected

...while the backend still stores:
- `consoleAgentId = null`
- compute runtime not provisioned as Hermes
- credit remains `0`

Do not trust the UI alone. Verify backend state.

### 2) The real credit trigger is backend console enable
The successful path that produced the grant was:

```http
POST /agents/{id}/console
Content-Type: application/json
Authorization: Bearer <refreshed_privy_token>

{"runtime":"hermes","templateType":"personal_assistant"}
```

A successful response to that call was followed by:

```json
{"limit":10,"limitRemaining":10,"usage":0}
```

in `GET /agents/{id}/compute/account`.

### 3) For ACP agent APIs, use the refreshed Privy token as Bearer
The working auth pattern for browserless creation was:
- ACP `/auth/verify` succeeds with refreshed Privy token + refreshed identity token.
- **Agent creation still uses the refreshed Privy token as the Authorization bearer**.
- Using the app token from `api2 /wallet/auth/privy` as the create-agent bearer produced `401 Unauthorized` in browserless tests.

### 4) Refresh the session after wallet creation
Without a session refresh after wallet creation, ACP auth can fail with wallet-link errors because the wallet is not present in the identity payload yet.

## Rate-limit / create-gate handling

If `POST /agents` returns 429 or 403 Forbidden with auth OK, treat **create as gated**, not auth.

Live pattern: OTP/wallet/verify/GET /agents can all pass while POST /agents returns 403 then 429. Headers may include `retry-after: ~86392` (~24h).

Handling:
1. first 429 on an IP → rotate immediately
2. on rotate: new email + new OTP (never reuse OTP)
3. repeated 403 with verify 201 = create policy/gate
4. many IPs all 403/429 → stop farming and wait cooldown
5. do not burn the full proxy pool against a locked create endpoint

See `references/create-gate-403-429.md`.

## Verification checklist

Successful run should prove all of the following:
- account email exists
- agent id exists
- `GET /agents/{id}/compute/account` returns `limit` and `limitRemaining`
- `limitRemaining >= 10` or a visible `$10.00` in compute UI
- `POST /agents/{id}/compute/keys` returns an `acp-...` key
- backend/runtime evidence shows Hermes was provisioned

## Pitfalls

- **Do not stop after agent creation.** Agent creation alone can leave credits at `0`.
- **Do not assume proxy reputation is the only variable.** One important failure mode was incomplete backend console provisioning, not just bad IPs.
- **Do not rely on app-token bearer for browserless `POST /agents`.** Use refreshed Privy token for create-agent requests.
- **Do not trust `defaultLimit` or static frontend defaults** as proof of granted credits. Only trust live `compute/account` values.

## Outputs to save

Recommended outputs per run:
- email
- wallet address
- agent id / agent URL
- runtime
- compute balance (`limit`, `limitRemaining`, `usage`)
- API key name + issued `acp-...` key
- proxy exit IP used for the successful run

## Project layout (ops)

```text
/root/virtuals-browserless/
  vbcli.py
  .env              # secrets only: IMAP + DOMAIN
  data/proxy.txt    # proxies NOT in .env
  api.txt           # ONLY done_$10 keys, one per line
  accounts.txt
  exports/virtuals_accounts.xlsx
```

Seed proxies from `/root/webnovel-tg-bot/proxy.txt` into `data/proxy.txt` (never store `PROXY_URL` in `.env`).

### Domain matrix (ops-proven)
| Domain | Login | Create agent | $10 grant |
|---|---|---|---|
| `<REDACTED>` | ✅ | ✅ when gate open | ✅ proven |
| `<REDACTED>` | ✅ | early ✅ / later 403–429 | early ✅ |
| `<REDACTED>` | ✅ | gated | 0 |
| `<REDACTED>` | ✅ | gated | 0 |

Prefer **`<REDACTED>`** for farming after create-gate pressure.

### Outputs policy
- `api.txt` = **only** keys with status `done_$10` (one key per line)
- never append failed / no-credit keys
- live-check keys with `GET compute.virtuals.io/v1/models` (+ tiny chat) when user asks

### Isolation
- live batch (`vbcli.py` / `screen virtuals-batch`) stays untouched during reverse experiments
- wallet/SIWE probes only under `tmp_wallet_create/`
- wallet SIWE can create agents; console enable requires **email linked** or free credit stays `$0`

## References

- `references/virtuals-credit-and-console.md` — credit/console findings
- `references/create-gate-403-429.md` — create-agent gate (403/429, retry-after)
- `references/wallet-siwe-no-credit.md` — wallet create OK / console 403 without email
- `references/domain-and-wallet-gates.md` — domain A/B + wallet vs email gates
- `references/ops-layout-and-domains.md` — ops layout, proxy file policy, api.txt rules
