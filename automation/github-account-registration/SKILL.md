---
name: github-account-registration
description: Automate GitHub account registration (CLI-first) — OctoCaptcha/DataDome, sticky proxies, email verify, skip-phone policy; scaffold at /root/github-autoreg.
version: 1.0.0
---

# GitHub Account Registration (CLI)

## Paths
- Project: **`/root/github-autoreg`** (own folder only — never mix with webnovel/x trees)
- **Private GitHub repo:** `https://github.com/<HANDLE_REDACTED>/github-autoreg` (`private=true`, branch `main`; secrets/tokens/proxies/accounts gitignored)
- User preference: **folder khusus sendiri tiap project** + private repo when shipping code
- Entry: `register.py`, captcha: `captcha_octo.py`, **batch**: `batch_create.py`
- Proxies: `proxy.txt` (active Webshare-first), `proxy_webshare.txt`, `proxy_webnovel.txt` (backup — often 403 on GH)
- Output: `accounts.txt`, `tokens.txt`, `logs/attempts.jsonl`, `logs/batch_screen.log`, `logs/batch.log`, `sessions/<user>.json`
- Venv: `.venv/`
- Screen batch: **`github-autoreg`** (one batch only)
- **IMAP source of truth (same as Webnovel):** `/root/cf-tuyul/.env` (`IMAP_HOST/PORT/USER/PASS`)
  - `/root/webnovel-autoreg/.env` often has **empty** `IMAP_PASS` — do **not** stop there
  - Loader order must match Webnovel: local → webnovel-autoreg → **cf-tuyul** → hermes
- Account password: shared `PASSWORD` env (same Webnovel password pool)

## When to use
- User asks to create/register GitHub accounts
- Need more GitHub tokens for `api-key-leak` harvest
- Debug GitHub signup captcha / email verify / phone gate / classic PAT

## Hard truth (do not overpromise)
- Harder than Webnovel, but **full E2E is proven** (signup → DataDome → email launch-code → confirm → login).
- Success ≠ **high** API limits. New-account classic PAT may still be **core 60 / search 10** even when valid + no-expiration.
- First page may not show phone; phone can still appear after email verify on other attempts.
- User “pake sama webnovel” for IMAP = use **cf-tuyul** creds, not invent a new mailbox.

## Live signup fingerprint (proven 2026-07-21)
| Item | Value |
|---|---|
| URL | `https://github.com/signup` |
| Form | `POST /signup?social=false` |
| Fields | `user[email]`, `user[login]`, `user[password]`, `authenticity_token`, `octocaptcha-token` |
| Captcha | **OctoCaptcha + DataDome** |
| iframe | `https://octocaptcha.com/datadome?origin_page=github_signup_redesign` |
| reCAPTCHA / Turnstile sitekey | **none** |
| Success signal after captcha | redirect/page `account_verifications` / “Please verify your email” |

### Solver mapping
| Gate | Solver |
|---|---|
| Webnovel `11401` reCAPTCHA | does **not** apply |
| Webnovel CF managed | Capsolver `AntiCloudflareTask` — different product |
| GitHub OctoCaptcha | **DataDome / OctoCaptcha** — often **suppressed** (no paid solve) |
| Real DataDome challenge only | **2captcha `method=datadome`** (proxy required) → `datadome=…` |
| Capsolver DataDome | **last resort** — Windows Chrome UA required; multi-type 180s polls hang batch |

### Preferred signup path (try first)
1. GET `/signup` on **form-OK** proxy (200 + authenticity_token + octocaptcha iframe)
2. Optional username check: `/signup_check_new/username?suggest_usernames=true`
3. Inspect iframe. If HTML has `sessionToken: 'datadome-suppressed'` / `captcha-complete` / `captcha-suppressed` → **suppressed**
4. `POST /signup?social=false` with **empty `octocaptcha-token`** first
5. Success = `account_verifications` / “Please verify your email”
6. Paid DataDome solve **only** if submit stays on hard captcha wall

**Why:** forcing 2captcha on generic
`https://octocaptcha.com/datadome?origin_page=github_signup_redesign`
often → long `waiting…` then **`ERROR_CAPTCHA_UNSOLVABLE`/timeout**, while empty-token submit works on suppressed sessions.

### Paid DataDome policy (only if not suppressed)
1. Rank 2captcha by live balance
2. Permanent skip zero/neg, `ERROR_IP_NOT_ALLOWED`, bad keys → `logs/2captcha_skip_keys.txt`
3. **Max 2 keys**, **~50s poll each** (never 90s × many keys)
4. Same sticky proxy required; prefer real `captcha-delivery.com` URL over generic `origin_page=`
5. Capsolver: one short try, funded `CAP-…` only, docs Windows Chrome UA (mobile UA → `unsupported userAgent`)
6. If token starts with `datadome=`, inject cookie on `.github.com` before POST

## Proxy rules (critical)
| Pool | GitHub signup form |
|---|---|
| Webnovel DC proxies (ProxyScrape-style) | often **403** before form (sample ~2/8) |
| **Webshare residential/list** | much better (sample **7/10** OK) |
| Direct VPS | form OK, but riskier for mass |

**Use Webshare (or other GitHub-friendly) for github-autoreg.**  
Do **not** assume Webnovel `proxy.txt` works for GitHub.

```bash
# probe pools before mass attempts
# OK = status 200 + authenticity_token + octocaptcha present
```

Active setup pattern:
- `proxy_webshare.txt` = user-supplied good list
- `proxy.txt` = good proxies first for github-autoreg only
- Keep webnovel proxies isolated under webnovel-tg-bot

## Standard ops
```bash
cd /root/github-autoreg
source .venv/bin/activate
python register.py --spike
python register.py --dry-run 1
python register.py 1 --submit   # only after spike+solve proven

# mass batch: no-captcha-first → IMAP → login → classic PAT no-exp → inject api-key-leak
/usr/bin/screen -dmS github-autoreg /bin/bash -lc \
  'cd /root/github-autoreg && .venv/bin/python -u batch_create.py 10 --delay 25 2>&1 | tee -a logs/batch_screen.log'
screen -r github-autoreg
tail -f logs/batch_screen.log
pgrep -af 'batch_create.py'   # verify alive after start
```

Defaults:
- Env load: github `.env` → webnovel-autoreg → **cf-tuyul** → hermes
- `SKIP_PHONE=1` — stop if phone required; not full success
- Never mass batch until 1 E2E email-verified account works
- Batch attempts: **1–2 empty `octocaptcha-token`**, **3 = paid DataDome fallback**
- Batch PAT: form-driven `default_expires_at=none` + empty `custom_expires_at`; **scopes optional** (empty proven OK; scopes can 422)
- On success append `ghp_` to `/root/api-key-leak/data/tokens.txt` then **restart** `api-key-leak` so log shows `Loaded N GitHub token(s)` (no hot-reload)
- One-shot `batch_create.py N` **exits when finished** — screen `github-autoreg` disappearing after `BATCH DONE success=…` is normal (user monitors; do not treat as crash)

### Batch fail-fast (anti-stuck)
| Signal | Action |
|---|---|
| Stuck on `solving DataDome…` with no `[captcha]` lines | Capsolver multi-type hang — kill; prefer **suppressed/no-captcha** + short 2captcha |
| Repeated `2captcha waiting… timeout` × keys | unsolvable generic iframe — max 2 keys/50s; try empty-token POST |
| `ERROR_CAPTCHA_UNSOLVABLE` | stop rotating every key for same URL |
| `ERROR_IP_NOT_ALLOWED` | permanent skip key (VPS IP not whitelisted) |
| `submit status=403/429` | **Do not IMAP-wait** — mark `submit_403`, rotate proxy once |
| Submit not landing `account_verifications` | fail fast — no 180s mail poll |
| Proxy GET signup 403 | rotate until form opens (mixed Webshare often ~4/10 bad) |
| **`no_proxy_opens_signup` on every attempt** | **whole pool dead for GH** — stop mass batch; refresh Webshare / probe GET `/signup` 200 before rerun (proven batch **0/10** all proxies 403) |
| 2captcha `ERROR_ZERO_BALANCE` | permanent skip; pre-rank balances |
| User says bot dimatikan | confirm no `batch_create` / no `github-autoreg` screen before re-work |

### Leave-in-screen preference (user)
When user says **“tinggal di screen ga usah pantau”** / **“biarkan”**:
1. Start `screen -dmS github-autoreg … batch_create.py N …`
2. Verify once: `pgrep -af batch_create` + first log lines
3. **Do not** keep polling the batch; hand off monitor commands and stop
4. Screen disappearing after `BATCH DONE success=…` is normal (one-shot exit)
5. On later “cek log”: read `logs/batch_screen.log` + counts only; if `success=0` and reason is proxy, say **proxy** is the blocker — don’t claim captcha/email failure

## E2E success criteria (proven path)
1. Signup form opens on **GitHub-friendly** sticky proxy (Webshare-class)
2. Prefer **suppressed / empty octocaptcha-token** when iframe is `datadome-suppressed`; else paid DataDome token + cookie inject
3. `POST /signup?social=false` → `account_verifications` / “Please verify your email”
4. IMAP (cf-tuyul) finds **`🚀 Your GitHub launch code`**
5. Prefer confirm URL: `https://github.com/account_verifications/confirm/<uuid>/<launch_code>`
6. Login → `meta name="user-login"` / `data-login` + cookies `logged_in`/`user_session`
7. Mark `login_ok` only after that (not mere `pending_email`)

### Proven full E2E (2026-07-21)
- Paid path: Webshare + 2captcha-datadome + POST → email verify
- **Also proven:** good Webshare + **empty `octocaptcha-token`** → `account_verifications` when OctoCaptcha suppressed
- IMAP from **`/root/cf-tuyul/.env`** (not empty webnovel-autoreg `IMAP_PASS`)
- Gmail labels may be Indonesian (`[Gmail]/Semua Email`) — English `All Mail` can fail
- Confirm deep link → login_ok; session under `sessions/<username>.json`
- Classic PAT: `default_expires_at=none` + optional scopes; new accounts often still **search 10 / core 60**

## Classic PAT for scraping (after login_ok)
Goal: token for `api-key-leak` public code search.

```text
GET  /settings/tokens/new   → form action POST /settings/tokens
Fields:
  authenticity_token
  oauth_access[description]
  oauth_access[default_expires_at] = none   ← “No expiration”
Scopes for public scrape:
- Empty scopes are **permission-OK** for public code search
- When user asks “set permission”: send `oauth_access[scopes][]` = `public_repo`, `read:user`, `user:email` (batch default)
- Scopes do **not** fix new-account low search/core limits
```

### Create rules
1. Must be **logged-in browser session** (cookies), not only password in chat
2. `default_expires_at` values: `7|30|60|90|custom|none` — use **`none`** for non-expiring
3. Rebuild from form inputs when possible; force expires `none`; include empty `oauth_access[custom_expires_at]`
4. **Try without scopes first** (empty scopes OK for public search). Scopes can 422 on some form states
5. Wrong/missing expiration or incomplete form → **HTTP 422** “Oh no”
6. On success page, scrape `ghp_…` once (`data-clipboard-text` / new-access-token / regex)
7. Validate: `GET /user` + `/rate_limit`; report `X-OAuth-Scopes` honestly (empty is fine)
8. Save: `github-autoreg/tokens.txt` + append to `/root/api-key-leak/data/tokens.txt`
9. **Do not claim high limits** — new accounts often still **core 60 / search 10** even with no-exp PAT
10. Answer “sesuai spek scraping bot?”: format/expiration/public-search yes; quota/trust may still be weak

## Relation to api-key-leak
- Pipeline: register → verify → classic PAT no-exp → inject `data/tokens.txt`
- Still parallel-invest in harvester yield; new GH tokens help but are low-limit at birth
- Never inherit Hermes `GITHUB_TOKEN` into harvester process

## Pitfalls
- Treating GitHub captcha as reCAPTCHA/Turnstile because “we have captcha solvers”
- Using Webnovel proxy pool without probing GitHub (mass 403)
- DataDome Device Check / `authenticity_token_missing` on browser or CLI means GitHub returned a blocked page, not the signup form. See `references/datatome-device-check.md`.
- **IMAP_PASS empty in webnovel-autoreg/.env** while cf-tuyul has the real app password — always load cf-tuyul
- Gmail mailbox names locale-specific — probe `LIST`, don’t hardcode English-only
- Claiming success at captcha-token only — need POST + email confirm + login
- Saving phone-walled accounts as success when `SKIP_PHONE=1`
- PAT create 422 → almost always expiration field / form shape, not “token API dead”
- Valid `ghp_` with search limit 10 → not broken; **new-account throttle**
- Printing full passwords/tokens in chat only when user explicitly asks for them
- Dual-running experiments that restart **webnovel-tg** or kill harvester without need
- Octo iframe is DataDome first; Arkose assets elsewhere ≠ first gate FunCaptcha
- **Batch hang ~7+ min on `solving DataDome…`** = Capsolver multi-type long timeout — prefer suppressed/no-captcha + short 2captcha
- **Repeated `waiting… timeout` 3×** = generic OctoCaptcha iframe unsolvable; check `datadome-suppressed` before more paid solves
- **After submit 403 still waiting IMAP 3 min** = missing fail-fast; only poll mail if verify page reached
- Empty-scope PAT OK for public search; set scopes when user asks “permission”
- Screen start can get approval-cut — verify `pgrep -af batch_create` after start
- Capsolver secondary may be `$0`; primary can reject DataDome with `unsupported userAgent` if UA is mobile-style

## References
- `references/signup-spike.md` — live HTML/form/captcha + proxy probe
- `references/e2e-email-pat.md` — full E2E mail confirm + classic PAT no-exp notes
- `references/batch-ops.md` — 10-account screen batch, hang fixes, fail-fast
- `references/datadome-suppressed-path.md` — OctoCaptcha suppressed / no-captcha submit discovery
- `references/datatome-device-check.md` — browser-confirmed DataDome restriction page; `authenticity_token_missing` means blocked page, not parser bug
- `references/proxy-pool-dead.md` — all-proxy `no_proxy_opens_signup` / 0-success batch
- Captcha balances / CF vs reCAPTCHA: skill `captcha-manager`
- X FunCaptcha parallel: skill `x-account-registration`
- Token consumer: skill `api-key-leak-harvester`
