---
name: cf-bulk-register
description: Bulk-register Cloudflare accounts (free Workers AI tier) via nodriver headless browser + Turnstile bypass, verify email via Gmail IMAP catch-all, create Workers AI API tokens, export to 9Router format. Based on iAm-182/bluk-cf adapted to a personal domain + Gmail.
version: 1.0.0
author: spring
license: MIT
platforms: [linux]
---

# CF Bulk Register — Cloudflare Account Farming (Workers AI free tier)

## Goal
Create N Cloudflare accounts (each = 10K neurons/day Workers AI free tier),
verify email via a personal catch-all domain → Gmail IMAP, create an API token
with Workers AI Read+Write perms, validate it, and export to 9Router txt format.

## Why nodriver (not raw CDP / xdotool)
- `page.verify_cf()` is the ONLY reliable Turnstile bypass (July 2026). No OpenCV,
  no xdotool pixel clicking, no template matching. xdotool/coordinate clicking is
  brittle and breaks on CF layout shifts.
- nodriver wraps CDP with anti-detect defaults.

## Base repo (use this, don't reinvent)
`github.com/iAm-182/bluk-cf` — already has: nodriver signup flow, Turnstile
bypass via `page.verify_cf()`, token creator (API `POST /api/v4/user/tokens` +
UI fallback), token validator, live dashboard, 9Router txt export.

Its email layer uses a **temp-mail API** (`mail_api` + jwt). We REPLACE that with
Gmail IMAP catch-all (see references/gmail-imap-adaptation.md).

## Operational requirements (Linux, running as root on VPS)
1. **Xvfb required** even for `headless=False`: start `Xvfb :99 -screen 0 1280x800x24`
   and `export DISPLAY=:99` before running. Without a display, nodriver fails with
   the misleading "running as root need no_sandbox=True" error — that message is
   GENERIC (means browser process died before CDP came up), NOT strictly a sandbox issue.
2. **Chromium**: snap chromium at `/usr/bin/chromium-browser` works. Pass
   `CHROME_BIN=/usr/bin/chromium-browser` and in code set `uc.start(sandbox=False,
   browser_executable_path=CHROME_BIN, browser_args=["--no-sandbox","--disable-setuid-sandbox","--disable-dev-shm-usage"])`.
3. **Run in a venv**: `python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt`
   (deps: nodriver, opencv-python-headless, httpx, Pillow, rich, playwright).

## Config (config.json)
```json
{
  "mail_mode": "gmail_imap",
  "gmail_user": "you@gmail.com",
  "gmail_app_password": "xxxx xxxx xxxx xxxx",   // 16-char Gmail APP password, NOT login password
  "imap_host": "imap.gmail.com",
  "mail_domains": ["yourdomain.bond"],
  "proxy": null,            // single proxy "http://user:pass@host:port"
  "proxy_file": "proxies.txt",  // OR a file, one proxy per line → rotated per attempt
  "headless": false,
  "delay_between_accounts": 60,
  "retry_attempts": 3,
  "token_name": "workers-ai-auto",
  "email_verify_timeout": 180,
  "email_verify_poll_interval": 8,
  "output_file": "results.json"
}
```
Note: repo's EmailGenerator reads `.env` with `key: value` (colon) format in some
setups; sync config.json from it via a small python script (don't hand-edit twice).

## Run
```
Xvfb :99 -screen 0 1280x800x24 &   # background, long-lived
export DISPLAY=:99
cd /root/bluk-cf && . .venv/bin/activate
export CHROME_BIN=/usr/bin/chromium-browser
python3 main.py --accounts 1 --no-dashboard --delay 10
```

## Critical pre-req: proxy quality determines success rate

Two hard blockers, in order:
1. **Domain + Email Routing catch-all MUST be live** in Cloudflare (else verification mail
   never arrives). Verify this first.
2. **The VPS IP itself will be blocked after 1-2 successful signups.** CF flags datacenter
   IPs quickly. After the first successful account, subsequent attempts from the same IP
   get **"Just a moment..." 403 (WAF challenge)** .
   - **Proxy rotation with banned-IP tracking is mandatory.** Pure random rotation wastes
     attempts on known-dead IPs. The `cf_sat_set.py` approach uses `random_proxy(banned=set())`
     — every proxy that fails a bootstrap attempt is added to a `_banned_proxies` set for the
     rest of that session, so subsequent retries always pick a fresh untested IP.
   - **SOME datacenter proxies work.** In testing: Leaseweb UK datacenter IPs (from Webshare
     premium) successfully completed signup, while other Webshare IPs in the same batch got
     403'd. Pure residential is safer but not strictly mandatory — rotate aggressively and
     skip failed IPs.
   - Proxyscrape premium HTTP proxies (100 tested) ALL returned 403. Webshare premium (10
     tested) had ~30% success rate. Proxies that pass `dash.cloudflare.com/sign-up` bootstrap
     tend to work for the whole flow.
   - Preflight a random proxy sample: `curl -x <proxy> -s -o /dev/null -w '%{http_code}'`
     `https://dash.cloudflare.com/sign-up` → `403` = blocked, skip; clean 200 = usable.
     See `references/proxy-requirements.md`.

## Turnstile note
`page.verify_cf()` solves the challenge fine. Do NOT iterate on widget clicks / token
injection / headless toggles when signup fails — that was a dead end caused by the IP
block above. Diagnose by dumping `document.body.innerText` first.

## Workers AI token permission group IDs (hardcoded in token_creator.py)
- Read:  a92d2450e05d4e7bb7d0a64968f83d11
- Write: bacc64e0f6c34fc0883a1223f938a104

## Alternative: curl_cffi API-only approach (`cf_sat_set.py`)
Located at `/root/cf-tuyul/cf_sat_set.py` on empero. API-only (no browser, no Xvfb) —
uses `curl_cffi` Chrome TLS impersonation + Turnstile solver. Setup: venv with
`curl_cffi` + `python-dotenv`, `.env` with captcha key(s) + `DOMAIN` + IMAP creds.
Run with `.venv/bin/python` (NOT system python3 — system Python 3.12 won't find
curl_cffi). Auto-injects into 9Router. See `references/curl-cffi-api-approach.md` for
full flow and comparison with nodriver.

**Turnstile solver priority:** Solverify first → 2captcha fallback. At least ONE of
`SOLVERIFY_API_KEY` or `TWOCAPTCHA_API_KEY` must be set in `.env`. The function
`get_captcha_keys()` returns a dict `{solverify, 2captcha}`; `solve_turnstile_any()`
tries Solverify primary, then 2captcha if Solverify key is empty or solve fails.
Both solvers are serialized via `_captcha_sem` to avoid rate limits.

## 9Router export
`python3 main.py --accounts 5 --export-txt keys.txt` writes cfut_ tokens in
9Router-friendly format (Name / API Key / Account ID / Priority / Proxy Pool).
Wire these into 9router as a custom cloudflare-ai provider node (see 9router skill).

## Pitfalls
- "Failed to connect to browser / need no_sandbox=True" = usually NO DISPLAY. Start Xvfb.
- Temp-mail API path is legacy; set `"mail_mode": "gmail_imap"` to use Gmail.
- Gmail needs IMAP enabled + an App Password (not the account password).
- **Proxy is MANDATORY — and it MUST be RESIDENTIAL.** Datacenter proxies (incl. paid
  Proxyscrape premium) return **403** from `dash.cloudflare.com/sign-up` and don't unblock
  signup. Test with `curl -x` first; 403 = blocked, skip it. Preflight probe + provider
  guidance + symptom map: `references/proxy-requirements.md`.
- **`proxy_file` rotation**: put one `http://user:pass@host:port` per line in the file named
  by `"proxy_file"`; `main.py` picks a random one per attempt (good for burning fresh IPs).
- "Turnstile solved" + form still rejected = IP block, NOT a captcha bug. Don't re-fix Turnstile.
- nodriver browser subprocess lingers; `pkill -f chromium` between runs if stuck.
- Debug with `--retry 1` to avoid re-firing signups from a blocked IP (default max_retry=3).
- **curl_cffi approach**: at least one of `SOLVERIFY_API_KEY` or `TWOCAPTCHA_API_KEY` must be set in `.env`. Solverify is tried first; 2captcha falls back automatically. Empty keys from cf-farm copy will error "No SOLVERIFY_API_KEY or TWOCAPTCHA_API_KEY in .env".
- **curl_cffi approach**: venv is Python 3.11; must use `source .venv/bin/activate` OR `.venv/bin/python` directly. System `python3` is 3.12 and won't find `curl_cffi`.
- **Gmail auto-archives CF emails**: Emails from `noreply@notify.cloudflare.com` are auto-archived by Gmail to `[Gmail]/All Mail` (locale: `[Gmail]/Semua Email` for Indonesian). They NEVER appear in `INBOX`. Script must search All Mail, not INBOX — otherwise verification token polling fails with timeout. Tested and confirmed.
- **2captcha Turnstile response**: `res.php` returns `{"status":1,"request":"TOKEN_VALUE"}` on success, NOT a separate `solution` field. The `request` field IS the token. Parse with `res.get("status")==1` and `res["request"]`.
- **Token propagation delay**: Workers AI API token can return `10000` auth error for up to 10-15 seconds after creation. Always wait 12s before `verify_token()`.
- **Proxy rotation must skip failed IPs**: Pure `random.choice()` can pick the same dead IP 3+ times. The `cf_sat_set.py` approach tracks failed proxies in `_banned_proxies` per session and skips them. If all proxies are banned, the script returns None (account failed with no remaining proxies).
- **Not all datacenter proxies are equal**: Webshare premium datacenter IPs had ~30% success rate against CF signup; Proxyscrape premium had 0%. Proxy origin/provider matters — test batches before relying on them.
- **Each proxy IP = exactly 1 account max**: Cloudflare flags an IP after ONE successful signup. Even a proxy that completed the full flow cannot be reused for another account. 10 proxies = 10 accounts max per batch, no reusing. This is the single most important constraint on farm volume — you need N unique IPs for N accounts.
- **Proxy file format compatibility**: The script's `_parse_proxy_line()` natively supports `host:port:user:pass` (4-part split → `http://user:pass@host:port`) AND `http://`/`socks5://` URLs. The format `user:pass@host:port` is NOT supported (the `@` breaks the split). Webshare and most premium lists use the 4-part format which works out of the box. Proxyscrape lists use `user:pass@host:port` which requires `sed 's/^/http://'` conversion.
