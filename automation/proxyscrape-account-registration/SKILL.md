---
name: proxyscrape-account-registration
description: Register ProxyScrape dashboard accounts browserlessly — CF Turnstile, IMAP verification codes, domain quality for Premium trial, register via proxy pool, export/inject trial proxies, webnovel-tg /proxy ops.
version: 1.1.0
category: automation
---

# ProxyScrape Account Registration

Use when creating **ProxyScrape** dashboard accounts (`dashboard.proxyscrape.com/v2/sign-up`), claiming free/premium trial proxies, exporting proxy lists, or operating **webnovel-tg `/proxy` / `/proxycreate`** auto-inject.

## Project isolation
- Own folder: `/root/proxyscrape-autoreg` (private `<HANDLE_REDACTED>/proxyscrape-autoreg`)
- CLI: **`pscli.py`** (`register|claim|export|login`); `register.py` thin wrapper
- Secrets: local `.env` (IMAP from cf-tuyul, captcha keys from hermes/bot envs)
- Ledger: `accounts.txt` (`email:pass:status:note`)
- Exports: `data/proxies_http.txt`, `data/proxies_hupu.txt`, `data/exports/<email>_<ts>/`
- TG inject: `/root/webnovel-tg-bot/wn/proxyscrape_mgr.py` → bot `proxy.txt`
- Do not commit secrets; keep CLI standalone

## Preferred flow (browserless)
```text
curl_cffi chrome124 (+ rotating register proxy)
  → GET /v2/sign-up
  → Capsolver/2captcha Turnstile (sitekey 0x4AAAAAAAFWUVCKyusT9T8r)
  → POST /v2/v4/account/auth/register  (email, password, cf_turnstile_token)
  → IMAP poll exact TO
  → POST /v2/v4/account/verify-email  (verificationCode + Bearer)
  → login prove (fresh Turnstile)
  → GET /v2/v4/account/{id}/services/overview → proxy_username/password
  → GET .../datacenter_shared/proxy-list?format=txt&type=displayproxies&protocol=http
  → export; optional inject webnovel proxy.txt as host:port:user:pass
```

CLI:
```bash
cd /root/proxyscrape-autoreg
.venv/bin/python pscli.py register
.venv/bin/python pscli.py register -n 3 --delay 20 --domain <REDACTED>
.venv/bin/python pscli.py register --proxy host:port:user:pass
.venv/bin/python pscli.py register --no-proxy
.venv/bin/python pscli.py claim EMAIL PASS
.venv/bin/python pscli.py login EMAIL PASS
```

## Endpoints (live)
| Action | Path |
|---|---|
| Register | `POST /v2/v4/account/auth/register` |
| Login | `POST /v2/v4/account/auth/login` |
| Verify email | `POST /v2/v4/account/verify-email` |
| Resend code | `POST /v2/v4/account/reset-verification-code` (Bearer) |
| Refresh | `POST /v2/v4/account/auth/refresh` |
| Services overview | `GET /v2/v4/account/{id}/services/overview` |
| Proxy list | `GET /v2/v4/account/{id}/datacenter_shared/proxy-list?format=txt&type=displayproxies&protocol=http` |

Content-Type: `application/x-www-form-urlencoded` (JS builds FormData but sets that header).

Password policy (client): min 8, upper + lower + digit + special.

## Register egress proxy (preferred)
User: **register pake proxy**. When a pool exists, do not default bare VPS IP.

`register_and_claim(use_proxy=True)` candidate order:
1. `PROXYSCRAPE_REGISTER_PROXY_FILE` / `REGISTER_PROXY_FILE`
2. local `register_proxy.txt` / `proxy.txt`
3. `/root/webnovel-tg-bot/proxy.txt` (TG path sets this)
4. github-autoreg webshare / webnovel-autoreg proxy files
5. direct last resort

Formats: `host:port:user:pass`, `user:pass@host:port`, `http://...`. Rotate on 403/429/5xx. Turnstile may stay proxyless; register HTTP should use proxy when available. CLI: `--proxy` / `--no-proxy`.

## Captcha
- Widget: **Cloudflare Turnstile**
- Sitekey: `0x4AAAAAAAFWUVCKyusT9T8r` (from signup chunk)
- Capsolver: `AntiTurnstileTaskProxyLess` (skip zero-balance keys)
- 2captcha: `TurnstileTaskProxyless`
- Login also requires a **fresh** Turnstile token

## Email verification
- Subject: `ProxyScrape - Email Verification`
- Body text: `Here is your email verification code: <hex/alnum>`
- **Field name is `verificationCode`** (not `code` / `otp` alone — those return `Verification code is not set.`)
- Resend works with Bearer after register/login
- IMAP: bind to exact target address; search `INBOX` + `[Gmail]/Semua Email`

## Domain quality (critical for trial)
Register success ≠ Premium trial.

| Domain | Mail | Premium trial |
|---|---|---|
| `<REDACTED>` | ✅ (may need resend ~45s) | ✅ `Account 1 (Premium trial)` / `datacenter_shared` |
| `<REDACTED>` | ❌ often no mail | — |
| `<REDACTED>` | ✅ | ❌ **disposable** → email `Trial not created` |

**User rule (2026-07-22):** do **not** use `<REDACTED>` for ProxyScrape — domain already marked. Prefer `<REDACTED>` (or other clean domains). Login-only accounts without trial are incomplete for proxy farming.

After verify, check `userData.associatedSubaccounts` for trial label. Empty subaccounts + earlier “Trial not created” mail = no free proxies.

## Premium trial duration + export (proven)
- Length: **7 days** (`subscription_plan_days=7`)
- ~100 HTTP proxies, port **3129**, ~10GB, max_conn ~10
- Creds: `services.datacenter_shared.proxy_username` / `proxy_password`
- List requires `protocol=http`
- Webnovel inject format: **`host:port:user:pass`** (not URL form)
- Live-test: `curl -x http://user:pass@ip:port https://api.ipify.org`

## Webnovel TG integration
- `/proxy`, `/proxycreate` [`force`], buttons Create/Replace/History/Refresh
- `wn/proxyscrape_mgr.py` → claim → write bot `proxy.txt` → reload ProxyPool
- DB `proxyscrape_batches` tracks email/account/expiry/status
- `/status` shows days left / EXPIRED
- Default domain for TG create: **`<REDACTED>`**
- Details: `webnovel-tg-ops` + `references/trial-export-and-proxy-inject.md`

## Success criteria
1. `register` HTTP 200 + `access_token`
2. Verification email for **this** address
3. `verify-email` → `Verification successfully completed` via **`verificationCode`**
4. Login prove → `EmailVerified: true`
5. **If trial wanted:** Premium subaccount + non-empty proxy list
6. Optional inject consumer pool; save ledger with trial yes/no + expiry

## Pitfalls
- Treating register token as verified account
- Using `code` instead of `verificationCode`
- Catch-all poison: accepting any ProxyScrape mail (other users’ codes)
- Assuming all catch-all domains get trial — disposable detection is separate from MX delivery
- Capsolver primary key zero balance — rotate `CAPSOLVER_API_KEY_N`
- `<REDACTED>` deliverability flaky for this provider; don’t burn solvers looping it
- User said avoid marked domain `<REDACTED>` even if verify works
- Bare VPS register → more CF 429; prefer rotating proxy pool
- Proxy list without `protocol=http` looks empty/broken
- Injecting URL form into webnovel ProxyPool without converting to `host:port:user:pass`
- Trial is **7 days**, not unlimited — always surface expiry in ops UI
- **Proxy health test format trap (2026-08-03):** `proxy.txt` lines are `host:port:user:pass`; curl needs `http://user:pass@host:port`. Testing with raw format `-x http://host:port:user:pass` reports every proxy DEAD (false negative). Convert first: `hp=$(echo $p|awk -F: '{print $1":"$2}'); up=$(echo $p|awk -F: '{print $3":"$4}'); curl -x "http://$up@$hp" ...`. A "100/100 dead" verdict with raw format is a test bug, not a dead pool.
- **Error 522 during register (2026-08-03):** `register failed: Cloudflare 522 Connection timed out` from `/proxycreate` means the **register egress proxy pool is dead**, not that the provider is down. Verify with the converted curl test above, then re-run via VPS direct: `PROXYSCRAPE_NO_PROXY=1` (or `--no-proxy`). Do not assume the bot is broken.
- **Batch 'active' ≠ usable:** `proxyscrape_batches.status='active'` with future `expires_at` can still fail `login` with 401 (account invalidated server-side, proxy list rotated dead). Try `claim_existing_and_inject(email, password)` first to re-export fresh proxies from the same account; if login 401s, force-register a new trial instead of looping the dead account.
- **DB is `data/bot.db`, not `webnovel.db`:** webnovel-tg-bot has an empty `webnovel.db` (0 bytes) — the real `proxyscrape_batches` table lives in `data/bot.db`.
- **Manager function names:** `wn/proxyscrape_mgr.py` exposes `create_trial_and_inject` (register+claim+inject) and `claim_existing_and_inject` (re-export existing account). There is no `register_and_inject` — don't guess the name.

## References
- `references/proxyscrape-signup-flow.md` — endpoints, verify field, domain matrix, sample outcomes
- `references/trial-export-and-proxy-inject.md` — 7-day trial, list API, webnovel inject, TG commands
- Companion patterns: `browserless-web-automation`, `webnovel-tg-ops`, `captcha-manager` (Turnstile)