---
name: captcha-manager
description: Test, validate, and manage multi-provider captcha API keys — balance checks, IP block detection, key rotation, and .env integration.
version: 1.0.0
author: spring
metadata:
  hermes:
    tags: [captcha, 2captcha, anti-captcha, capsolver, capmonster, API-keys, automation]
    related_skills: [agentx]
---

# Captcha Manager — Multi-Provider Key Testing & Management

Test captcha API keys across providers, check balances, detect IP blocks, and manage keys in `.env`.

## When to Use
- User gives you a captcha API key to test
- User asks to check balances across captcha providers
- User wants to seed keys into harvester skip lists
- Managing multiple captcha keys in `.env`

## Provider API Endpoints

### 2captcha
```bash
# Balance check
curl -s "https://2captcha.com/res.php?key=YOUR_KEY&action=getbalance"

# IP block test (returns ERROR_WRONG_CAPTCHA_ID if NOT blocked)
curl -s "https://2captcha.com/res.php?key=YOUR_KEY&action=reportbad&id=1"
```
- Balance: returns float (e.g. `6.75083`)
- IP blocked: returns `ERROR_IP_BLOCKED` or similar error with "IP" in message
- Invalid key: returns `ERROR_WRONG_USER_KEY`
- **Always test IP block** — key may work for balance but be blocked for actual solving

### Anti-Captcha
```bash
curl -s --max-time 15 -X POST "https://api.anti-captcha.com/getBalance" \
  -H "Content-Type: application/json" \
  -d '{"clientKey": "YOUR_KEY"}'
```
- Returns JSON: `{"balance": 47.80, "errorId": 0}`
- Error: `{"errorId": 1, "errorCode": "ERROR_KEY_DOES_NOT_EXIST"}`
- **Note**: API may timeout from some VPS IPs — report as "unreachable" not "invalid"

### Capsolver
```bash
curl -s --max-time 10 -X POST "https://api.capsolver.com/getBalance" \
  -H "Content-Type: application/json" \
  -d '{"clientKey": "YOUR_KEY"}'
```
- Returns: `{"balance": 1.5, "errorId": 0}`
- Error: `{"errorCode": "ERROR_KEY_DOES_NOT_EXIST"}`

### Capmonster
```bash
curl -s --max-time 10 -X POST "https://api.capmonster.cloud/getBalance" \
  -H "Content-Type: application/json" \
  -d '{"clientKey": "YOUR_KEY"}'
```
- Returns: `{"balance": 2.0, "errorId": 0}`
- Error: `{"errorCode": "ERROR_KEY_DOES_NOT_EXIST"}`

### Rucaptcha
```bash
# Balance check — SAME API format as 2captcha, different domain
curl -s "https://rucaptcha.com/res.php?key=YOUR_KEY&action=getbalance"

# IP block test (returns ERROR_WRONG_CAPTCHA_ID if NOT blocked)
curl -s "https://rucaptcha.com/res.php?key=YOUR_KEY&action=reportbad&id=1"
```
- Same response format as 2captcha (float balance, `ERROR_WRONG_CAPTCHA_ID` for IP test)
- **Shared backend**: a single key often works on BOTH `2captcha.com` and `rucaptcha.com` — always test both domains for any key found (harvester often labels them differently)

## Workflow: Test a New Key from Harvester

Canonical path: **`/root/api-key-leak`** (repo `DezXBT/api-key-leak`). Not `/root/api-key-harvester`.
Writes to `found/<provider>.txt` (`| balance | key | source |`). Daily workflow:
1. Captcha-focused providers when farming Webnovel CF budget: `2captcha,capsolver,capmonster,anti-captcha,rucaptcha,...`
2. `cat found/2captcha.txt found/rucaptcha.txt found/capmonster.txt found/anti-captcha.txt found/capsolver.txt`
3. Validate each key against ALL provider endpoints (labels can be wrong)
4. Positive balance → product bot `.env` sequential vars
5. Seed `existing/<provider>.txt`
6. GitHub tokens: **only** `data/tokens.txt` (600, gitignored). `unset GH_TOKEN GITHUB_TOKEN GH_TOKENS` before start.

### Capsolver harvest shape
- Real keys: **`CAP-` + long alnum** (not bare UUID)
- Pattern: `CAP-[A-Za-z0-9]{20,100}`
- Never lowercase `CAP-` candidates
- Scan arch: all queries → global URL dedup → fetch once → multi-provider match → validate

## Workflow: Test a New Key

1. **Identify provider** — try all 4 endpoints in parallel (they're fast)
2. **Check balance** — parse response, reject negative/zero
3. **Test IP block** (2captcha only) — `reportbad?id=1` trick
4. **Save to .env** — use sequential vars: `TWOCAPTCHA_API_KEY`, `TWOCAPTCHA_API_KEY_2`, etc.
5. **Seed skip list** — append key to `existing/{provider}.txt` in harvester dir to prevent re-scanning

### Capsolver keys for Webnovel (dual inject)
When user pastes new `CAP-…` keys:
1. Live `getBalance` first (prefix + balance only in chat)
2. Append next free `CAPSOLVER_API_KEY_N` in **both** `/root/.hermes/.env` **and** `/root/webnovel-tg-bot/.env`
3. Autoreg create/CF child reads bot `.env` first — hermes-only inject is not enough
4. Verify `_keys_for_prefix("CAPSOLVER_API_KEY")` count + balances
5. Never print full keys

## .env Convention
```ini
TWOCAPTCHA_API_KEY=<primary>
TWOCAPTCHA_API_KEY_2=<secondary>
TWOCAPTCHA_API_KEY_3=<tertiary>
```
For other providers: `{PROVIDER}_API_KEY` (e.g. `ANTICAPTCHA_API_KEY`, `CAPSOLVER_API_KEY`, `CAPMONSTER_API_KEY`).
Harvester-discovered keys also land here with sequential suffixes (`_4`, `_5`, etc).

**Inventory snapshot (2026-07-08):** 8 active keys, ~$41 total. Andalan: `8673ea9a...` (2captcha, $17.04). Also rucaptcha `b9d54eed...` ($1.50), capsolver `CAP-FE3471CF...` ($3.98) + `CAP-143B25C1...` ($5.83), capmonster `4a8928f9...` ($0.82). Re-check balances before relying on any — they drain.

## Multi-Key Test Pattern (execute_code)
```python
from hermes_tools import terminal
import json

keys = ["key1", "key2", "key3"]
for key in keys:
    r = terminal(f'curl -s --max-time 10 "https://2captcha.com/res.php?key={key}&action=getbalance"')
    balance = r.get("output", "").strip()
    r2 = terminal(f'curl -s --max-time 10 "https://2captcha.com/res.php?key={key}&action=reportbad&id=1"')
    ip_status = "BLOCKED" if "IP" in r2.get("output", "") else "OK"
    try:
        bal = float(balance)
        status = "✅" if bal > 0 and ip_status == "OK" else "❌"
    except:
        status = "❌"
    print(f"{status} {key[:12]}... | Balance: ${balance} | IP: {ip_status}")
```

## Ranking keys for a product bot (Webnovel TG pattern)
When a bot needs captcha for register risk gates:
1. Live-check balances across all keys/providers
2. Rank by balance descending
3. Write **only positive-balance keys** into the product bot `.env` (primary = highest)
4. Prefer provider order by **live balance**, not hard-coded 2captcha-first (example ranked order: anticaptcha → capsolver → 2captcha backups → capmonster)
5. For Webnovel `doregister` risk reCAPTCHA, **proxy-bound solve** must use the same proxy as the register request — proxyless tokens often fail with site-side `11306 Verification failed` even when the solver returns a long token
6. Inject ranked captcha env into child `/create` process; do not assume parent Hermes `.env` alone is enough when the bot has an isolated `.env`
7. On mass create failures that still print `Captcha token ok` then `11306`, treat as proxy-IP mismatch first — not “solver dead”

## TWO different Webnovel gates (do not conflate)
| Error / page | Domain | Kind | Solver |
|---|---|---|---|
| `11401 google code` | `passport` / `ptlogin` | Google reCAPTCHA v2 | `solve_recaptcha_v2` (anticaptcha/capsolver/2captcha/capmonster) |
| `Just a moment…` 403 / `no csrf` after passport OK | **`m.webnovel.com`** | Cloudflare **managed** challenge (`cType: managed`) | **`solve_cloudflare_challenge`** (Capsolver `AntiCloudflareTask`) |

Having a reCAPTCHA solver **does not** fix mobile CF. Passport login can be `code=0` + ticket while mobile bootstrap is still CF-blocked.

## Cloudflare managed challenge (Webnovel mobile) — proven 2026-07-21
Module: `/root/webnovel-autoreg/captcha_solver.py`
- `solve_cloudflare_challenge(website_url, proxy, user_agent=None, html=None)`
- `apply_cf_solution_to_session(session, solution)`

### Capsolver `AntiCloudflareTask` rules (critical)
1. **Proxy required** — same sticky proxy as the curl session (IP-bound clearance)
2. **Windows Chrome UA only** — Capsolver rejects Android/mobile UA with `unsupported userAgent! we only support Chrome's userAgent on Windows`
3. Force UA like:
   `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36`
4. After solve, set **session UA to solver's `userAgent`** (or the Windows UA) and inject `cf_clearance`
5. Re-GET `https://m.webnovel.com/id` after clearance to obtain `_csrfToken`
6. Prefer **omit `html`** on createTask unless docs/provider require it (can break validation)
7. Proxy string format for Capsolver: `ip:port:user:pass`
8. CF solve is **paid + flaky** — expect retries; secondary Capsolver keys may be `$0`; 2captcha CF createTask often returns empty task on these keys
9. **cf_clearance is IP-bound AND still may not clear from curl.** Real case
   (nodeseek.com, 2026-08-01): solved `AntiCloudflareTask`, replayed the cookie
   through the SAME solve proxy with full browser headers (sec-fetch, accept-lang,
   etc.) — every path still 403 (`/`, `/api/boards`, `/search`, `/topic`). Same
   for a headless browser that egresses from a different IP. Do NOT burn balance
   iterating curl header variations. Before paying for a CF solve on a site you
   only need to READ, check for a non-CF mirror/alternate domain first —
   `nodeseek.cc` served the same forum with zero Cloudflare (200 + posts.rss +
   search.json). Treat nodeseek-style CF clearance as "need same-IP browser
   session", not "curl-able".

### Wire-in point
`open_mobile_session` in `signup.py`: on bootstrap/callback/login/login/userInfo `403 Just a moment` → `_try_cf_solve` → re-bootstrap → continue ticket exchange.

### Diagnosis pattern (real)
```
login_check code=0 ticket=True
GET m.webnovel.com/id → 403 Just a moment, csrf=False
→ without CF solve: no csrf + login/info failed
→ with Capsolver CF: cookies_set=1 [cf_clearance] → csrf + login_ok/info_ok
```

Details:
- `references/cloudflare-managed-challenge.md` — Capsolver wire-in
- `references/2captcha-vs-capsolver-cloudflare.md` — why 2captcha Turnstile docs do **not** replace Capsolver for Webnovel mobile
- GitHub OctoCaptcha/DataDome (different product): skill `github-account-registration` + `references/signup-spike.md`

## Pitfalls
- **Anti-captcha timeouts**: API may be unreachable from certain VPS. Report "unreachable", don't conclude key is invalid.
- **Negative balance**: 2captcha returns negative floats for drained keys. Filter these out.
- **Primary key can be empty while backups still have money** — always re-rank before mass create; don't trust an old primary.
- **IP block != invalid key**: A key can have balance but be IP-blocked. Always test both.
- **Harvester skip lists**: Always seed found keys to `existing/{provider}.txt` to avoid re-notification via webhook.
- **Don't expose full keys in Discord/chat responses** — show first 12 chars only (e.g. `82d7c3c7dfca...`)
- **Stripe hCaptcha unsolvable by 2Captcha**: As of 2026-07-07, 2Captcha returns `ERROR_CAPTCHA_UNSOLVABLE` for Stripe checkout hCaptcha (sitekey: `ec637546-e9b8-447a-ab81-b5fb6d8e24c2`). Stripe uses enterprise-level hCaptcha with fingerprinting.
- **Anti-Captcha CAN solve Stripe hCaptcha Enterprise**: Anti-Captcha (`api.anti-captcha.com`) successfully solves the same sitekey that 2Captcha cannot. Task type: `HCaptchaTaskProxyless` with `isInvisible: true` and `enterprisePayload: {rqdata: ""}`. Cost: ~$0.002 per solve. HOWEVER: token injection into page still fails because hCaptcha Enterprise uses server-side callback verification that requires in-browser solving.
- **hCaptcha Enterprise vs Regular**: Regular hCaptcha = solvable by all providers. Enterprise hCaptcha = only Anti-Captcha (and possibly Capsolver) can solve, but injection may still fail due to server-side verification.
- **Webnovel reCAPTCHA sitekey** (register risk): `6Leb2SYUAAAAAEemO0h4Wj_casf9j5HM6RfNg7bG` — use proxy-bound tasks when register goes through a proxy.
- **Turnstile token is IP-bound (Grok/xAI, 2026-08)**: `AntiTurnstileTaskProxyLess` returns a long token but the backend rejects it with `Failed to verify Cloudflare turnstile token` when the API call egresses from a different IP. Solve with `AntiTurnstileTask` + proxy AND send the registration/login API request through that same proxy. Both signup (`CreateUserAndSession`) and login (`CreateSession`) enforce this; login without it returns `grpc-status 7: Anti-abuse token is missing`.
- **xAI Turnstile fingerprints SOLVERS (2026-08-08)**: even proxy-bound `AntiTurnstileTask` now returns `ERROR_CAPTCHA_SOLVE_FAILED Bot behavior detected, error code: 600010` on every proxy AND proxyless — the solver pattern itself is detected, and tokens that do slip through cause the account to be flagged (`bfs:1` → server downgrades the served model). If a target site returns 600010, no Capsolver key/proxy variant will fix it; the only clean-account route is manual/human Turnstile click. See `grok-account-automation` for the full chain.
- **X/Twitter signup uses Arkose FunCaptcha**, not reCAPTCHA. Subtask `ArkoseEmail`/`ArkosePhone` → `ocf_arkose_challenge` with `data=` blob. Solve via FunCaptcha tasks; prefer proxy-bound if signup is proxied. See `x-account-registration` + `/root/x-autoreg/captcha_arkose.py`.
- **Token ok ≠ site accepts**: Webnovel long reCAPTCHA tokens still fail `11306` on IP mismatch; X FunCaptcha tokens are useless until Signup stops returning `366 Missing data`.
- **reCAPTCHA solver ≠ Cloudflare solver**: `11401` uses reCAPTCHA; mobile `Just a moment` is CF managed challenge — separate Capsolver `AntiCloudflareTask` path.
- **Capsolver CF UA lock-in**: Windows Chrome UA required; mobile Pixel UA → immediate reject.
- **CF costs more / drains Capsolver faster** than reCAPTCHA; re-check balance before mass cold `/sync` or mass power/bookmark that re-opens many mobile sessions.
- **2captcha “Cloudflare” docs ≠ managed clearancer**: Turnstile API needs sitekey/`cData`/`chlPageData`/`action`. Webnovel managed page has none → `ERROR_TASK_ABSENT` / `ERROR_BAD_PARAMETERS`. Capsolver `AntiCloudflareTask` is the proven path.
- **Capmonster is not Capsolver for CF managed**: `AntiCloudflareTask` → `ERROR_TASK_ABSENT`. Capmonster may accept `TurnstileTask` (wrong gate for Webnovel mobile).
- **Anti-Captcha timeout from VPS**: treat as **unreachable**, not invalid and not “supports CF managed”.
- **“Cuma berapa Capsolver key?”**: inventory unique `CAP-…` across bot/hermes/found; often **1 funded + 1 empty**, not many CF backups.
- **Harvester path `/root/api-key-leak`**: Capsolver regex must match `CAP-…`; never lowercase keys; fetch-once multi-provider scan.
- **GitHub signup is not Webnovel captcha**: first gate is **OctoCaptcha/DataDome** (`octocaptcha-token`, iframe `octocaptcha.com/datadome?origin_page=github_signup_redesign`) — no reCAPTCHA/Turnstile sitekey. See skill `github-account-registration`.
- **GitHub OctoCaptcha often suppressed**: iframe may post `sessionToken: 'datadome-suppressed'` / `captcha-complete`. Prefer **empty `octocaptcha-token` POST** before paying 2captcha. Generic `origin_page=` URL frequently → long wait then `ERROR_CAPTCHA_UNSOLVABLE`.
- **2captcha DataDome fail-fast**: max ~2 keys, ~50s each; permanent skip `ERROR_ZERO_BALANCE` / `ERROR_IP_NOT_ALLOWED` (whitelist). Soft IP check: `action=get&id=1` → `ERROR_WRONG_CAPTCHA_ID` = IP OK; `IP_NOT_ALLOWED` = skip key.
- **Capsolver DataDome ≠ CF managed**: DataDome needs docs Windows Chrome UA; wrong UA → `unsupported userAgent`. Secondary Capsolver key may be `$0`.
- **Proxy pool is product-specific**: Webnovel DC proxies often **403** on `github.com/signup`; Webshare mixed (~6–7/10 form-OK). Always probe target site before assuming “we have proxies”.
- **Negative 2captcha balances** (e.g. `-0.001`) = drained, not usable; IP probe `reportbad&id=1` → `ERROR_WRONG_CAPTCHA_ID` means IP not blocked.
- **Outlook / Microsoft HUMAN gate ≠ reCAPTCHA/CF/FunCaptcha:** late UI `Let's prove you're human` + `Press and hold` is **PerimeterX/HUMAN** (`iframe.hsprotect.net`, app id **`PXzC5j78di`**, control `aria-label="Press & Hold Human Challenge"`). Capsolver PerimeterX docs may be **Coming Soon**; createTask names (`AntiPerimeterXTask`, `PerimeterXTask`, `HumanTask`, …) returned **`ERROR_TYPE_NOT_SUPPORTED`**. Anti-Captcha PX types **`ERROR_TASK_NOT_SUPPORTED`**. 2captcha `method=perimeterx` behaved like image captcha (`ERROR_ZERO_CAPTCHA_FILESIZE`). **Do not** burn CF/reCAPTCHA/FunCaptcha balance claiming it clears this hold. Details: `references/outlook-human-perimeterx.md`.
- **Outlook form vs gate:** Webshare can pass email→password→birth→name; DC/Webnovel often early **We ran into a problem**. Incomplete `CreateAccount` → **`1347`**. No HUMAN clearance → **`1059` `field=humanCaptcha`**. Browser path may then **`risk/verify` 403 `AADSTS7005106` / `riskBlock`** → UI account creation blocked. Correct hold target + long press still may not clear HUMAN — not just “wrong selector”.
- **curl_cffi anti-detect does not delete Outlook HUMAN:** TLS impersonation helps early API; server still requires HUMAN sensor / can return 1059.
