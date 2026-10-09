---
name: virtuals-acp-agent
description: Create Virtuals Protocol ACP agents (app.virtuals.io) — Privy email OTP, embedded wallet, Hermes console, compute API keys; free $10 after backend console enable (not bare create).
version: 1.1.0
category: automation
---

# Virtuals ACP Agent Create

Use when user asks about **Virtuals Protocol**, `app.virtuals.io`, ACP agents, Hermes runtime console, compute API keys (`acp-…`), or free inference credits on Virtuals.

## Project isolation
- **Browserless (preferred ops):** `/root/virtuals-browserless` — CLI `vbcli.py`
- **Browser / research WIP:** `/root/virtuals-autoreg`
- Secrets: IMAP from `/root/cf-tuyul/.env` or project `.env`; never commit tokens/keys
- Ledger: `accounts.txt`, `exports/virtuals_accounts.xlsx`
- Prefer reverse → browser proof → **browserless HTTP** (Dez: “folder khusus” + no-browser when possible)
- Prefer domain **`<REDACTED>`**; OTP also works on `<REDACTED>` and `<REDACTED>`
- Proxies live in **`data/proxy.txt`** (seed from Webnovel). **Never** put proxies in `.env`
- `api.txt` = **only** keys from `done_$10` (one key per line, no metadata)

## User SOP (1 account = 1 wallet = 1 email)
```text
1. https://app.virtuals.io/acp/new
2. Login email domain + IMAP OTP (Privy)
3. Accept ToS/cookies/popups
4. Identity: random Agent Name + Description
5. Console ON → Runtime "Hermes Agent" → Template "Personal Assistance Agent"
6. Token: Skip (Agent Card OFF)
7. Launch Agent → Register Agent
8. CRITICAL: ensure console is backend-enabled (see Free $10 below)
9. Open /acp/agents/<id>?tab=compute → verify limitRemaining
10. Create API key; save once
11. Clean browser footprint before next account
```

## Free $10 — live truth (2026-07-22, corrected)
**UI Console toggle alone is NOT enough.** After Register, agent create often returns:
- `consoleAgentId: null`
- claw may show `runtime: openclaw` / `walletBalance: "0"`
- `GET .../compute/account` → `limit=0`, `limitRemaining=0`

### Auto-grant path (proven, NO GitHub/X)
Immediately after agent create, with ACP JWT:
```http
POST https://api.acp.virtuals.io/agents/{id}/console
{"runtime":"hermes","templateType":"personal_assistant"}
```
→ `201 Successfully enabled console`

Then:
```http
GET https://api.acp.virtuals.io/agents/{id}/compute/account
→ limit=10, limitRemaining=10, usage=0
```
UI shows **$10.00**. Claw compute-account can show `runtime: hermes`.

**Proven sample ($10):**
```text
email: cole.stone35@<REDACTED>
proxy exit: 31.56.127.193
agent: 019f8a2d-7c85-7699-9b1a-cb7dd05edab9
api_key: acp-19635df35574a17e8e86
balance: limit=10 remaining=10 (ui $10.00)
```

### Also exists: GH/X weekly free-inference campaign
Compute UI still has developer-campaign path (GitHub/X enroll/claim). That is a **separate** free weekly flow — not required for the initial $10 after console enable.

### IP / proxy note
- Direct VPS IP and Webshare residential both created agents
- Proxy alone did **not** grant $10 without console enable
- Prefer proxy for cleanliness, but **backend console enable is the real switch**

**Never claim free $10 from bare register** without `compute/account` verification.

## Live outcomes matrix
| Step | Result |
|---|---|
| Email OTP | ✅ cyou + bond |
| Agent create | ✅ |
| UI Console Hermes selected | ⚠️ often still `consoleAgentId=null` at create |
| `POST .../console` hermes+personal_assistant | ✅ **$10 auto** |
| API key | ✅ `POST .../compute/keys` → string `acp-…` |
| GH/X only | optional campaign path; not required for first $10 |

## Auth architecture (browserless proven)
```text
Privy appId: cltsev9j90f67yhyw4sngtrpv
loginMethods: email | wallet

POST auth.privy.io/api/v1/passwordless/init {email}
IMAP 6-digit ("Your code is NNNNNN" / subject Virtuals login code)
POST .../passwordless/authenticate {email,code,mode:login-or-sign-up}
  → token, identity_token, refresh_token, ...
POST .../wallets {chain_type:ethereum}            # required
POST .../sessions {refresh_token}                 # CRITICAL after wallet
  → NEW token + identity_token (must include wallet)
POST .../users/me/accept_terms
# optional: POST api2.virtuals.io/wallet/auth/privy {accessToken}

POST api.acp.virtuals.io/auth/verify
  {address: 0x…, token: privy_token, identityToken: refreshed_identity}
  → 200/201 "Successfully verified" (body often has NO jwt field)

# Bearer for agent/compute APIs = Privy token (refreshed), NOT acpx jwt
POST api.acp.virtuals.io/agents {name,description,role:HYBRID,console:{runtime:hermes,templateType:personal_assistant}}
POST api.acp.virtuals.io/agents/{id}/console {runtime:hermes,templateType:personal_assistant}  # $10 gate
GET  api.acp.virtuals.io/agents/{id}/compute/account  → limit/remaining 10
POST api.acp.virtuals.io/agents/{id}/compute/keys {name} → data:"acp-..."
```

### Live verify free credit (strict)
```http
GET /agents/{id}/compute/account  → limitRemaining ~10
POST compute.virtuals.io/v1/chat/completions Authorization: Bearer acp-...
  → 201 + cost; re-GET account shows usage/remaining drop
```
Never claim `$10` from create logs alone without `compute/account` (and ideally a tiny chat spend).

### Auth pitfalls
- Email-only without EVM wallet → `No wallet accounts linked`
- ACP verify needs **wallet address**, not email
- **Must refresh Privy session AFTER wallet create** or identity lacks wallet → verify 401
- ACP verify success may return **no jwt** — use **Privy token as Authorization** for `/agents`
- acpx JWT often **401 Unauthorized** on `api.acp.virtuals.io` agent create
- Create can **429 Rate limit** — sleep 15–60s and/or rotate proxy; retry create only
- UI create is often **multipart**; tool captures may show empty body
- OTP IMAP: exact TO + subject Virtuals; folders `INBOX` + `[Gmail]/All Mail` / `Semua Email`

## Console / template (must verify)
**Two layers:**
1. **UI:** Console switch ON + Hermes + Personal Assistance + Review shows Hermes
2. **Backend:** `POST /agents/{id}/console` with hermes/personal_assistant (or create payload that actually sticks)

If only UI layer succeeds → agent exists, API key may work, **balance stays $0**.

**Console toggle automation (proven):**
- Page has **2** switches: **0 = Console**, **1 = Agent Card** (keep card OFF / Skip token)
- `page.get_by_role("switch").nth(0)` → scroll_into_view → `click(force=True)` until `aria-checked`/`data-state` is `true`
- Do **not** soft-click once and assume ON — re-read attribute after each click
- After ON: wait for Hermes + Personal Assistance cards; click both; re-check switch still true
- Review modal must show **Runtime: Hermes Agent** before **Register Agent**
- After Register: always run backend console enable + re-read `compute/account`

## Browser automation notes
- Privy OTP = 6 single-digit boxes (`maxlength=1`); IMAP: exact TO + `Your code is NNNNNN`
- After OTP: if toast **No wallet accounts linked** / **Account not connected**, force  
  `POST auth.privy.io/api/v1/wallets {chain_type:ethereum}` + `accept_terms` + `api2 .../wallet/auth/privy`, then reload `/acp/new`
- Wait for Agent Name input visible before fill (avoid blind `input[type=text]`)
- Launch Agent opens **Review & Register** → must click **Register Agent**
- After create: force `POST .../console` if needed → then keys/balance
- API key: `POST /agents/{id}/compute/keys`; response `data` is **string** `acp-…`
- Capture ACP bearer from agent-create request headers for follow-up API calls

## Browserless CLI (ops default)
```bash
cd /root/virtuals-browserless
.venv/bin/python vbcli.py register
.venv/bin/python vbcli.py register -n 3 --delay 20
.venv/bin/python vbcli.py register --proxy 'http://user:pass@host:port'
.venv/bin/python vbcli.py register --no-proxy
.venv/bin/python vbcli.py register --max-proxies 3 --delay 20
```
Outputs: `accounts.txt`, `exports/virtuals_accounts.xlsx`, `data/last_result.json`

### Proxy architecture (updated)
- **Do not store proxies in `.env`.** Keep `.env` for secrets only (IMAP credentials, password, domain).
- Store proxy inventory in a dedicated file, preferably:
  - `/root/virtuals-browserless/data/proxy.txt`
- Seed that file from Webnovel when needed:
  - source: `/root/webnovel-tg-bot/proxy.txt`
- Browserless runs should read proxies from the file-based pool and rotate there, not from `.env`.

### Fast 429 / create-gate handling
- Treat `429 Rate limit exceeded` on `POST /agents` as a **hot IP/proxy**, not an auth bug.
- Also treat repeated `403 Forbidden` on create (with auth/verify OK) as a **create gate**, not bad OTP/token.
- Live probe under gate: `GET /agents` 200 + `POST /agents` 403/429; `retry-after` can be **~24h**.
- On the **first** 429 from an IP, rotate immediately instead of burning long backoff on the same host.
- When rotating proxy/IP, also rotate identity: **new email + new OTP**. Never reuse the same OTP after changing proxy.
- If many proxies all 403/429: **stop farming** and wait cooldown — do not burn the whole pool.
- Domain A/B under gate: bond / my.id both login OK, create still blocked → **domain is not the blocker**.
- Details: companion skill `virtuals-acp-browserless` → `references/create-gate-403-429.md`.

**Proven browserless $10 samples:**
```text
luna.river356@<REDACTED>  agent 019f8a3e-097b-76d8-983a-98c44b25b9c7  key acp-e5421704c79d74c7c640
axel.river441@<REDACTED>  agent 019f8a41-2222-756c-872c-d8cf34a759a0  key acp-7cc991ec0e8b337215d9
  (live recheck: limitRemaining~9.997 after $0.002 chat test)
```

### Browser scripts (research / fallback)
- `/root/virtuals-autoreg/browser_create_agent_v2.py` — Playwright E2E + force console attach
- `/root/virtuals-autoreg/force_console_create.py` — experimental helper

## Success criteria (strict)
1. Email verified + EVM wallet linked  
2. Agent URL `/acp/agents/<uuid>`  
3. Console Hermes + personal_assistant **backend-applied** (`POST /console` 201 and/or compute runtime hermes)  
4. `compute/account` **limitRemaining > 0** when claiming free tier success  
5. API key `acp-…` saved  
6. XLS row written  

## Pitfalls
- Treating login/agent create alone as free LLM credit  
- Skipping Register modal after Launch  
- UI Console ON but **no** `POST .../console` → `consoleAgentId=null` → **$0**  
- Soft-click Console once and assuming ON — must re-read `aria-checked`  
- Reporting `$10` from claw `defaultLimit:10` without `compute/account`  
- Assuming only GH/X can unlock free credit — initial $10 can auto after console enable  
- Blaming IP alone — proxy without console enable still $0; console enable can grant $10  
- OTP OK but form blocked: **No wallet accounts linked** until embedded EVM wallet exists  
- Browserless: skipping **session refresh after wallet** → ACP verify 401 / create fails  
- Using **acpx jwt** as bearer for `/agents` → 401; use **Privy token**  
- Create **429** spam — backoff + proxy rotate; do not hammer same IP  
- Create **403 Forbidden** with verify 201 = create policy/gate, not auth failure  
- Multipart agent create hard to re-POST from incomplete network captures  
- Creating many embedded wallets in one Privy user during debug — prefer 1 wallet per new user  
- API key: response `data` is **string** `acp-…`; UI click **Create Key**  
- `notes: console_enable=Rate limit exceeded` can still be `done_$10` if account already has remaining=10  
- Never append non-`$10` keys into `api.txt`  
- Putting proxies in `.env` — use `data/proxy.txt` only  

## References
- `references/auth-and-create-flow.md` — endpoints, browserless auth, $10 grant, live samples
- Free-credit summary also in `credit-farming/references/virtuals-acp-free-credit.md`
- Companion: `browserless-web-automation`, `credit-farming`, `email-link-registration-automation` (OTP variant)
