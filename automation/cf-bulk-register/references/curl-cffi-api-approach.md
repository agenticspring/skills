# curl_cffi API-only CF Farming (`cf_sat_set.py`)

Alternative to the nodriver/browser approach — uses `curl_cffi` (Chrome TLS fingerprint
impersonation) + Turnstile solver (Solverify → 2captcha fallback). No browser, no Xvfb,
no Chromium needed.

## Location on empero
```
/root/cf-tuyul/
├── .venv/          ← curl_cffi 0.15.0 + python-dotenv
├── .env            ← SOLVERIFY_API_KEY, DOMAIN, IMAP creds
├── proxy.txt       ← one proxy per line (http://user:pass@host:port)
└── cf_sat_set.py
```

## Dependencies
```bash
python3 -m venv .venv
.venv/bin/pip install curl_cffi python-dotenv
```

## .env requirements
At least one captcha solver key required (Solverify preferred, 2captcha fallback):
```
DOMAIN=<REDACTED>
# Primary Turnstile solver
SOLVERIFY_API_KEY=<solverify_key>
# Fallback Turnstile solver (used if Solverify empty or fails)
TWOCAPTCHA_API_KEY=<2captcha_key>
# IMAP for email verification (Gmail catch-all)
IMAP_HOST=imap.gmail.com
IMAP_PORT=993
IMAP_USER=<REDACTED>
IMAP_PASS=<gmail_app_password>
```

## Run
```bash
cd /root/cf-tuyul && .venv/bin/python cf_sat_set.py --count 1
```
CRITICAL: use `.venv/bin/python`, NOT system `python3`. System Python (3.12) does not
have `curl_cffi` installed. The venv is Python 3.11.

## How it works
1. `GET /api/v4/system/bootstrap` — get security_token + country (uses proxy if configured)
2. `GET /api/v4/captcha/challenge?context=signup` — get Turnstile sitekey
3. `solve_turnstile_any(keys, sitekey)` — **Solverify first → 2captcha fallback**. Both are serialized
   globally via `_captcha_sem` to avoid rate limits. Function returns None if all solvers fail.
   - **Solverify**: POST `solver.solverify.net/createTask` → poll `getTaskResult` (max 45 x 3s)
   - **2captcha**: GET `2captcha.com/in.php?key=X&method=turnstile&sitekey=Y&pageurl=Z&action=signup&json=1`
     → poll `res.php?key=X&action=get&id=ID&json=1` (max 80 x 2s). Response: `{"status":1,"request":"TOKEN"}`.
     Known errors: `ERROR_CAPTCHA_UNSOLVABLE` (dead end), `CAPCHA_NOT_READY` (keep polling).
     Pricing: ~$0.08–0.10/solve. $8.32 balance = ~80–100 accounts.
4. `POST /api/v4/user/create` — create account with `cf_challenge_response` token
5. `POST /api/v4/persistence/user` — trigger verification email via `{"emailVerificationRequest":"welcome"}`
6. IMAP poll `[Gmail]/Semua Email` → extract `email-verification?token=...` (see Gmail section below)
7. `PUT /api/v4/user/email-verification` — verify with token
8. `GET /api/v4/accounts?per_page=100` — get account_id
9. `POST /api/v4/user/tokens` — create Workers AI API token (3 permission groups: Workers AI Read + Write + Account Read)
10. **12-second propagation delay** — token sometimes returns `10000` auth error immediately after creation. Wait 12s.
11. `POST /api.cloudflare.com/client/v4/accounts/{id}/ai/run/@cf/meta/llama-3.2-1b-instruct` — verify token works (expects `{"success":true,"result":{"response":"Hello"}}`)
12. Auto-inject into 9Router `providerConnections` table (hardened with retry for WAL contention)

## Gmail IMAP — search "All Mail" (NOT INBOX)
CF verification emails come FROM `noreply@notify.cloudflare.com` → Gmail auto-archives them
into `[Gmail]/Semua Email` (All Mail). They do NOT appear in `INBOX`. The script MUST
`mail.select('"[Gmail]/Semua Email"')` — searching `INBOX` finds zero emails.
This was the root cause of "email never arrives" reports after Cloudflare Email Routing
confirmed forward delivery. Tested and confirmed: All Mail had 9 CF emails; INBOX had 0.

Folder name is locale-dependent (`[Gmail]/Semua Email` on Indonesian Gmail, `[Gmail]/All Mail`
on English). The script's `get_verification_token` uses the Indonesian path since the user's
Gmail is Indonesian.

## Proxy format conversion
Proxy lists (Proxyscrape, etc.) often come as `user:pass@host:port` WITHOUT the `http://`
prefix. The script's `_parse_proxy_line()` does NOT recognize this format (it only handles
`host:port:user:pass` or `http://...`). Always convert to `http://user:pass@host:port`
before writing to `proxy.txt`:
```bash
sed 's/^/http://' raw_proxies.txt > proxy.txt
```

## Proxy support

Reads `proxy.txt` (one `http://user:pass@host:port` per line), picks per attempt.
**Banned-IP rotation:** `random_proxy(banned=set())` — every proxy that fails a bootstrap
attempt is tracked in a `_banned_proxies` set for that session, so each retry picks a
fresh untested IP. If all proxies are banned, the session fails gracefully with None.
Falls back to direct (no proxy) if file is empty or all IPs exhausted.

**IP burn rate (CRITICAL):** Each clean proxy IP works for exactly ONE account before
Cloudflare flags it. Even a successful account creation burns that IP permanently for
future signups. This means:
  - 10 proxies = max ~10 accounts before pool exhaustion
  - 100 proxies = ~100 accounts
  - For serious bulk farming (100+ accounts), need 100+ unique IPs
  - Reusing the same proxy across multiple accounts does NOT work — CF remembers

**Proxy quality varies by provider (tested on empero, Jul 2026):**
- Webshare premium datacenter (host:port:user:pass format, Leaseweb UK IPs): ~30%
  of IPs passed bootstrap. The IPs that worked were residential-adjacent DC (Leaseweb,
  ASN associated with UK consumers, not typical cloud/hosting). IPs routed through
  obvious cloud providers (DigitalOcean, Hetzner, AWS, GCP) always 403.
- Proxyscrape premium datacenter: 0% success rate — every IP returned 403 on bootstrap.
- VPS direct IP (Hetzner): works for 1-2 accounts then gets flagged permanently.
- Residential proxies (true ISP IPs) are safest but not tested in this session.
- **Heuristic:** If `curl -x proxy` to `dash.cloudflare.com/sign-up` returns 403
  CF challenge, that proxy is useless for signup. Skip it preemptively.

## 9Router auto-inject
After saving an account, `inject_to_9router()` inserts into:
```
~/.9router/db/data.sqlite → providerConnections
provider: cloudflare-ai
authType: apikey
name: WaguriAgent #N
```
Hardened against transient WAL checkpoint contention (retries with backoff).

## Comparison with nodriver approach
| Aspect | cf_sat_set.py (curl_cffi) | bluk-cf (nodriver) |
|--------|--------------------------|-------------------|
| Browser needed | No | Yes (Chromium + Xvfb) |
| Turnstile solver | Solverify → 2captcha (paid API) | page.verify_cf() (free) |
| Speed | Fast (API call chain) | Slower (page navigation) |
| Fingerprint | curl_cffi Chrome TLS | Real Chromium |
| Reliability | Depends on Solverify uptime | Proven verify_cf() |
| Proxy | proxy.txt rotation | config.json proxy/proxy_file |
