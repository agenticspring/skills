---
name: webnovel-account-automation
description: Automate Webnovel account register/confirm/login/avatar with strict end-to-end success gates.
version: 0.5.0
category: automation
---

# Webnovel Account Automation

Use this skill when working on Webnovel account creation, email confirmation, login verification, profile avatar upload, **powerstone vote**, **library/bookmark**, or reverse-engineering Webnovel auth/PCM flows.

For low-level HTTP/RSA/JSONP implementation detail, also load `webnovel-signup`.

## Mandatory success criteria

Do **not** mark an account as successful unless all of these are true:

1. Registration endpoint returns success (`code=0` + `emailkey`).
2. Confirmation email is located for the **exact target address** (catch-all safe).
3. The confirmation flow is exercised via `login/confirm` (double-encoded `emailkey`) far enough to return `ticket` + `userId` (+ `uKey` when present).
4. Prefer a fresh login check (`checkcode` `0`, `11318`, or captcha-after-password `11401`).
5. **If profile-photo step is in scope:** mobile session exchange + `setUserAvatar` returns `code=0` (see pitfalls 9–11). Prefer avatar right after confirm ticket (fresh) before re-login.
6. **If anti-bot profile polish is in scope (default for `/create`):** set human nickname via `setUserSettings` so profile is **not** left as default `Daoistxxxx` (see pitfall 24). Prefer nick in the same mobile session as avatar.
7. Only then save the account to the success ledger (`email:password:userid:avatar_path:nickname` when known).

### Soft-ok exception (2026-07-22, mandatory)
If **email confirmed** (`ticket`+`userId` from confirm) and profile polish ran (avatar and/or nick OK), but passport `login_check` fails with soft flakes:
- `no csrf` / missing `_csrfToken`
- CF / Just a moment / timeout on passport bootstrap

Then **do NOT purge / fail the account**. Retry login_check once; if still flaky → **soft-ok save** using confirm ticket/userid. Bot TG will **auto re-login on demand** later via `ensure_session` when cookies missing.

Hard fail only when confirm never issued ticket/userid (or true bad-password after real checkcode).

Default `Daoist*` nick after create = incomplete polish (may still login, but user treats it as bot-detectable).

## Critical pitfalls

### 1. Registration callback success is not enough
Webnovel can return a successful registration callback while the account is still unusable. Treat registration as only the first gate.

### 1b. Passport `login_check` `no csrf` is not always a dead account
Confirm ticket + avatar/nick OK, then `login_check` `-1 no csrf`, used to purge/fail the create. That is a **passport bootstrap flake**, not unconfirmed email. Soft-ok save + later `ensure_session` re-login. Details: `references/create-soft-ok-login-csrf.md`.

### 2. Email arrival is not confirmation
IMAP seeing a Webnovel mail is not activation. Hit confirm endpoint and prove ticket issuance.

### 3. Prefer the CTA tracking link, not the pixel
- `.../f/a/...` = CTA
- `.../q/...` = 1x1 beacon (ignore)

Prefer HTML `href=` and pick the longest `/f/a/` URL.

### 4. Catch-all IMAP poison
Never fall back to bare `UNSEEN FROM "webnovel"`. On catch-all domains this grabs **other accounts'** activation mails and produces false green paths. Require the target address in To/Delivered-To/body.

### 4b. Multi-domain register pool
New creates use **round-robin** domains from env `DOMAINS` (default `<REDACTED>,<REDACTED>,<REDACTED>`). Do not hardcode single `<REDACTED>`. See `references/register-domain-round-robin.md`. Product split: Webnovel may use `<REDACTED>`; ProxyScrape trial should still prefer `<REDACTED>`.

### 5. emailkey double-encoding
Confirm requests must send jQuery-style **double-encoded** emailkey from the confirm URL query. Single-encoded/decoded keys fail with empty-key / request-error codes.

### 6. Runtime RSA pubkey
Do not hardcode. Extract from live `login_v6.js` each run.

### 7. Login/register codes — `11401` is risk captcha, NOT ban
Interpret codes correctly:

| Code | Where | Meaning | Action |
|------|-------|---------|--------|
| `0` | login/register | OK | proceed |
| `11313` | login | bad password / unusable | fail account |
| `11314` | reset | account missing | fail |
| `11318` | login | password OK, untrusted device | auto Guard OTP |
| **`11401`** | **login or register** | **risk reCAPTCHA gate** | **solve captcha, do NOT label Banned** |
| `-11051/-11055/-11053` | register | real ban-ish | rotate proxy / stop |

**Register `11401` (proven 2026-07-20):** browser `registerCallback` stores `sessionKey`, `handleNextAction(1)` shows Google reCAPTCHA, resubmits `doregister` with:
- `nextAction=1`
- `validateCode=<g-recaptcha-response>`
- sitekey from `login_v6.js`: **`6Leb2SYUAAAAAEemO0h4Wj_casf9j5HM6RfNg7bG`**
- pageurl: `https://passport.webnovel.com/register.html?appid=900&areaid=1...`

Implementation: `/root/webnovel-autoreg/captcha_solver.py`. Live path: `11401` → **proxy-bound** token → register `code=0`.

### 7b. `11306 Verification failed` = captcha IP mismatch (critical)
After token is obtained, register can still fail with **`11306 Verification failed`**. Root cause (proven 2026-07-20):
- Captcha solved **proxyless** (solver worker IP A)
- `doregister` submitted via account **proxy IP B**
- Webnovel validates token against client IP → rejects

**Mandatory fix:**
1. Prefer **proxy-bound** captcha tasks (`RecaptchaV2Task` / `ReCaptchaV2Task` with same HTTP proxy as register, not only `*Proxyless`)
2. Provider order for Webnovel register: `anticaptcha-proxy` → `capsolver-proxy` → `2captcha-proxy` → proxyless fallback only
3. On `11306`, **retry once** with a fresh proxy-bound token (same session/csrf/password)
4. Log provider used (`LAST_CAPTCHA_PROVIDER`) for debugging
5. Rank captcha keys by live balance into bot `.env`; inject into `/create` child env (do not rely on empty primary 2captcha)

Details: `references/register-risk-captcha-11401.md`.
### 8. Device trust OTP is alphanumeric Guard code
Trust mail subject: `Webnovel Support` / `Dukungan Webnovel`.
Body: `Webnovel Guard code ... : BRAAOz` (mixed alnum, usually 6 chars).
Never treat footer years (`2019`) as OTP. Complete via `sendTrustEmail` → IMAP Guard parse → `checkTrust`.

### 9. Mobile session for password proof vs avatar
Passport `checkcode` password acceptance is enough to mark **loginable**.
**Avatar upload is a separate gate** and needs a real `m.webnovel.com` session:

1. Seed cookies `uid` + `ukey` from confirm/login payload (`uKey` field).
2. Bootstrap `https://m.webnovel.com/id` for `_csrfToken` — curl_cffi `impersonate=chrome124` (chrome131 often CF-blocks).
3. **Required:** `GET /go/pcm/login/login?_csrfToken=&ticket=&guid=` with `Content-Type: application/json`. Missing csrf → `400 {}`.
4. Prove: `userInfoAjax?_csrfToken=` → `code=0` (not session invalidate -401).
5. Upload: `POST setUserAvatar?_csrfToken=` multipart field `image` via **CurlMime** (`files=` unsupported).
6. Success: `{"code":0,"msg":"Success"}`.

Bare `uid`/`ukey` + `www/?ticket=` alone does **not** authenticate PCM APIs.

### 10. Prefer confirm ticket for avatar, then login proof
Confirm issues fresh `ticket`+`userId`+`uKey`. Use that ticket immediately for avatar, then `checkcode` login proof.
### 11. Unique avatars per account — pool format v2 (2026-07-25)

User preference (2026-07-20): **no real-face template photos** for new accounts.  
User preference (2026-07-25): **do NOT use AI image generation** — "Cari aja di internet gambarnya. Jangan generate karena buang buang token." Always download from free internet sources (Dicebear, Robohash, Unsplash/Picsum).

**Pool naming convention (v2):** `pool_<theme>_<style>_<nn>.png`  
- **Themes** (5): `anime`, `mainan`, `gunung`, `game`, `pemandangan`  
- **Styles** (4): `2d`, `cartoon`, `3d`, `realistis`  
- **Variants**: 5 per theme+style = 100 files total  
- **Sources**:  
  - Character themes: Dicebear (adventurer/fun-emoji/bottts/avataaars), Robohash, pixel-art  
  - Toy/mainan: Robohash set3, Dicebear bottts  
  - Landscape themes (gunung/pemandangan): Unsplash landscape photo IDs, Picsum  
- **Style filters**: PIL enhancements per style (2D=color+contrast, cartoon=color+edge, 3D=vignette, realistis=sharpness)  
- **Label strip**: bottom 28px bar + `theme/style/nn` text for inventory clarity  

**Fallback order (code in `fetch_unique_avatar`):**  
1. Unused local pool files matching `pool_*` — try all 100, skip any `local:pool_*` key already in `avatars_used.txt`  
2. Remote stylized fallback (Dicebear fun-emoji / bottts / pixel-art / robohash animals) — **never** randomuser.me real portraits  
3. Existing accounts keep their already-uploaded `used_*` files; do not mass-replace old avatars unless asked

**When replacing pool:**  
1. Delete old files (`pool_*` and `used_*` in avatars dir)  
2. Reset `avatars_used.txt` to empty  
3. Download ~100 new assets from free internet sources (Dicebear/Robohash/Unsplash) — NOT AI generation  
4. Save as `pool_<theme>_<style>_<nn>.png` so old `used_*` keys don't interfere

### 24. Human-like email + nickname on create (anti-bot fingerprint)
User requirement (2026-07-21): new accounts must look human — **email + display name**, not farm defaults.  
Follow-up: **“Jangan mirip mirip namanya”** — diversity is mandatory; template farms are wrong.

**Why:** Fresh profiles always start as `nickName/userName/penName = Daoist` + random (`Daoist4Qd6gI`, …). Stylized avatars alone still look botty with that nick. A second failure mode is **template nicks**: `First_Arc` / `First_Books` / `BookishX` / `CozyX` across the pool.

**Email (`gen_identity` in `signup.py`):**
- Real first/last pools (usa/asia/europe)
- Locals like `first.last12`, `firstlast99`, `f_last88` — **not** `gh.*` / `user123`
- Domains: **round-robin** via env `DOMAINS` (default `<REDACTED>,<REDACTED>,<REDACTED>`; legacy `<REDACTED>` **retired** for new creates; old accounts keep old domain)
  - `next_domain()` / `gen_identity()` in `signup.py`
  - `/create` child injects `DOMAINS` from bot `.env` (`wn/create_accounts.py`)
  - IMAP Gmail catch-all must cover **all** active domains

**Nickname rules (Webnovel settings JS):**
- `[A-Za-z0-9_]{3,18}` only (spaces → check `-107004`; short/long → `-107003`; taken → `-107005`)
- Prefer length **6–14**, few digits
- **Reject template shapes** (hard):
  - `Daoist*`
  - `Name_(Arc|Books|Calm|Bloom|Ink|Bright|Pages|Novels|Cosy)`
  - Dominant soft prefixes: `Bookish*`, `Cozy*`, `Golden*`, `Hidden*`, `Ivory*`
- Generator must use **diverse vocab + multiple structures** (noun/verb/adj mix, alternate first/last)
- Track **global used nicknames** during batch rename/create so pool nicks stay unique

**Proven rename API (mobile PCM + csrf):**
```text
GET  /go/pcm/user/checkUserName?_csrfToken=&userName=
POST /go/pcm/user/setUserSettings?_csrfToken=
  form: name=<nick>&gender=0&country=GO&sign=
```
Success `code=0`. Verify `userInfoAjax` → nick/user/pen updated.  
404/wrong: bare `setUserInfo` / `setNickName` paths — use **setUserSettings**.

**Wire into create (default):**
```text
confirm ticket → open_mobile_session
  → setUserAvatar
  → checkUserName + setUserSettings (retry 6–10 diverse nicks, avoid used set)
  → login_check
  → save email:pass:userid:avatar:nickname
```
`/create` child loads `signup.py` fresh — **no TG bot restart** after nick code deploy.  
`wn/client.py` Account supports optional 5th field `nickname`.

**Mass rename existing pool (ops):**
```bash
/usr/bin/screen -dmS wn-rename /bin/bash -lc \
  'cd /root/webnovel-tg-bot && .venv/bin/python -u wn/rename_daoist.py 1.3 2>&1 | tee -a logs/rename_daoist.log'
```
- Targets Daoist* **and** template nicks from a bad first pass
- Uses sticky `sessions/*.json`; updates `accounts.txt` nickname field
- One-shot screen exits on DONE (normal)
- If batch produced lookalike templates, **stop and re-run diversify v2**
- User correction **“Jangan mirip mirip namanya”**: first pass that yields many `Name_Arc`/`Name_Books` is a **failed** polish — diversify immediately with global used-set

Details: `references/human-profile-nickname.md`.

### 12. Powerstone + library need the same mobile PCM session as avatar
Do not call power/library APIs with passport cookies alone. After `login/login`+csrf:

| Action | Endpoint | Proven params |
|--------|----------|----------------|
| Power on book | `GET /go/pcm/book/getRewardVotingPopup` | `bookId`, **`bookType=0`**, `_csrfToken` |
| User power | `GET /go/pcm/user/userInfoAjax` | → `availablePower` |
| Give powerstone | `POST /go/pcm/powerStone/vote` | form: `bookId`, `amount`, **`novelType=0`**, `_csrfToken` |
| Bookmark | `POST /go/pcm/library/addLibraryItemsAjax` | form: **`bookIds`**, `novelType=0`, `_csrfToken` |
| List library | `GET /go/pcm/library/library` | often `encryptType=1` |

Pitfalls: `bookType`/`novelType` **0** works even if detail `bookType=2`; wrong type → `1001`. New accounts often have **1** PS only. Bookmark field is **`bookIds`** (plural). Full notes: `references/powerstone-library.md`.

### 13. VPS runner / curl_cffi path
Canonical `/root/webnovel-autoreg` uses `.venv` + `./run.sh`. Bare SSH `python3` may be system 3.12 without curl_cffi (register/login OK, PCM avatar/power/library fail). Prefer `./run.sh N` or `.venv/bin/python signup.py N`.

### 14. Telegram product bot = FULL pool isolation (option 2)
Admin-only TG bot at `/root/webnovel-tg-bot` (`@webnovelpowerbot`, screen `webnovel-tg`).

**User chose full separation** from `webnovel-autoreg` data:

| Item | Bot path (canonical) |
|------|----------------------|
| Accounts | `/root/webnovel-tg-bot/accounts.txt` |
| Proxy | `/root/webnovel-tg-bot/proxy.txt` |
| Device profiles | `/root/webnovel-tg-bot/device_profiles.json` |
| Avatars | `/root/webnovel-tg-bot/avatars/` |

- Autoreg is **code source only** for `signup.py` during `/create`.
- `/create` forces env: `WEBNOVEL_ACCOUNTS_FILE`, `WEBNOVEL_PROXY_FILE`, `DEVICE_PROFILES_FILE`, `WEBNOVEL_AVATAR_DIR`, `WEBNOVEL_AVATAR_USED_FILE` → bot paths.
- Autoreg `signup.py` / `device_profiles.py` must honor those env overrides (not hardcode HERE-only paths).
- Seed/copy accounts once when splitting; do **not** assume shared file after that.
- Details: `references/telegram-powerstone-bot.md`.

### 15. Hermes TELEGRAM_BOT_TOKEN clobber
Parent shell often exports a different `TELEGRAM_BOT_TOKEN`. Project `.env` load must use **override=True**; start with `unset TELEGRAM_BOT_TOKEN TELEGRAM_TOKEN` before `./run.sh`. Verify bot id/username with `getMe`. Guard admin on messages **and** callback queries.

### 16. Sticky per-account device isolation (mandatory)
Do **not** use one fixed UA/proxy for every email. Persist profile per email in **that pool's** `device_profiles.json` (gitignored):

| Field | Purpose |
|-------|---------|
| `proxy` | sticky IP (prefer unique when pool allows) |
| `desktop.ua` + `accept_language` | passport register/login (`LightSession`) |
| `mobile.ua` + `impersonate` + `accept_language` | `m.webnovel.com` PCM (`curl_cffi`) |

Rules:
1. `get_or_create_profile(email)` on **register**, **login_check**, and mobile session open.
2. Same email → same proxy/UA/impersonate forever (sticky) **until ban forces rotate**.
3. Prefer **chrome124 only** for mobile impersonate. **chrome120 often CF-blocks** `m.webnovel.com` (`Just a moment...` 403 HTML → JSON parse fails as `Expecting value: line 1 column 1`). chrome131 also flaky. Migrate existing profiles away from chrome120.
4. Account count > proxy count ⇒ IP reuse expected; still sticky, not random hop.
5. Bot uses **bot-local** `wn/device_profiles.py` + bot `device_profiles.json`. Autoreg uses its own. Never mix paths after isolation.
6. **Ban/retry MUST rebind sticky proxy** via `rotate_profile_proxy(email, dead_proxy=...)` then pass the new proxy into `register`/`update_profile_proxy`. `proxy_pool.random()` alone is NOT enough — next `get_or_create_profile` will snap back to the banned IP and look "stuck" on one dead proxy.
7. On CF during mobile session: detect `403` / `Just a moment` / non-JSON HTML. This is **Cloudflare managed challenge**, not reCAPTCHA `11401`. Use Capsolver `AntiCloudflareTask` (Windows Chrome UA + same proxy) via `solve_cloudflare_challenge` → inject `cf_clearance` → re-bootstrap for csrf. Also retry chrome124 / rotate sticky proxy. Surface `CF blocked` not cryptic JSON errors. Details: `captcha-manager/references/cloudflare-managed-challenge.md`, `references/cf-mobile-session.md`.
8. Details: `references/device-isolation.md`, `references/cf-mobile-session.md`.

### 17. Multi-account delay = INTER-ACCOUNT spacing (not start-delay)
When user picks delay for Powerstone / Bookmark / **Create** (e.g. `5m`), it means:

```
akun1 action → sleep 5m → akun2 action → sleep 5m → …
```

**Wrong:** wait 5m once, then blast all accounts back-to-back.  
**Right:** sleep **between** account actions; no sleep before first account. Stream progress between steps. Presets: Now/1m/5m/15m/30m/1h/… + custom `45s`/`10m`/`2h`.

**Create delay UX (mandatory, same as PS):**
1. `/create N` → show delay keyboard first (do not start immediately)
2. On pick / custom → `start_create_job(..., delay_s=..., delay_tok=...)`
3. Pass delay into create child via env `CREATE_DELAY_S` (signup.py sleeps between accounts; interruptible 1s chunks for Stop)
4. Progress header shows delay; summary includes delay used
### 18. Long jobs: unlimited target + live stream + Stop mid-run
User wants **no artificial max** on `/create N` (not capped at 5). For create, powerstone, and bookmark:

1. Stream progress to the same TG message — **throttle hard** (≈3–5s between edits; ignore flood). Edit spam → Telegram **429** → UI freezes and Stop appears broken.
2. Always show **🛑 Stop** inline button while running.
3. Stop is cooperative: set cancel flag; finish current HTTP step; skip remaining targets; report partial success.
4. **Create MUST run as background task** (`asyncio.create_task`) + Application **`concurrent_updates=True`**. If `/create` awaits signup inline on the handler, Stop callbacks never run until the job ends.
5. Create streams signup stdout (`PYTHONUNBUFFERED` / `python -u`); terminate process on stop/timeout.
6. Soft timeout for create ≈ `min(8h, max(15m, N*(4m+delay_s)))` unless stopped earlier.
7. Only **one** active create job at a time; refuse stacking.
8. Only **one** `bot.main` process per token. Dual instances → `409 Conflict` / terminated getUpdates — progress + Stop both die.
9. **Create + PS/bookmark/sync concurrently is ALLOWED** (user expects this). Safe because create is a separate `signup.py` child and PS uses per-account sessions. Risks: denser proxy/IMAP/captcha + more CF if both mass-run. Prefer delay on both when doing heavy parallel ops. Dual create still blocked.
10. Details: `references/tg-bot-isolation-and-jobs.md`.
### 19. Daily Powerstone remaining without mandatory `/sync` + **ledger-first vote**
Webnovel grants a fixed amount of Power Stones **daily at 00:00 (UTC+8)** by user level.

Product requirements (Dez):
1. Show remaining PS **without forcing `/sync`**
2. When voting N stones, **skip accounts already used today** — do **not** live-probe the whole pool first

Implementation:
1. Local ledger (`daily_power`) keyed by email + day in **Asia/Shanghai (UTC+8)**
2. Auto-seed today's grant from last known `last_total_power` (default 1 for new accounts)
3. Decrement on successful vote (`add_used`)
4. `/status` and novel cards call `pool_remaining(emails)` which seeds missing rows
5. `/sync` stays **optional** for live re-check against Webnovel APIs
6. After `/create` success, `seed_new_account(email, total=1)`
7. **`execute_power` must use `accounts_with_remaining()`** before any mass `get_power_balance`
   - amount=3 → open/vote ~3 remaining accounts, not scan 100 used
   - failed live vote (no PS) → `mark_empty(email)` so next run skips
   - full `refresh_pool_balances` only if ledger remaining ≤ 0

**Anti-pattern (user-visible slow “add 3 power”):**  
loop all accounts with `get_power_balance`/`ensure_session` then vote. Ledger already knows who has PS today.

Do not block status UX on live balance probe for every view.

Details: `references/powerstone-daily-ledger.md`, `references/powerstone-ledger-first-vote.md`.

### 19b. Bookmark ledger — one account, one novel (mandatory skip)
Product rule (Dez, 2026-07-21): **1 account can bookmark a given novel only once**. To bookmark again, use a **different novel**. Re-running the same book must **skip** already-bookmarked accounts, not retry the whole pool.

Implementation:
1. Table `book_bookmarks(email, book_id, status, updated_at)` PK `(email, book_id)`
2. `execute_bookmark` pre-filter: `targets = pool - bookmarked_emails(book_id)`
3. Success `code=0` → `mark_bookmarked(email, book_id, "ok")`
4. API already/exist/in-library (or similar msg / soft codes) → `mark_bookmarked(..., "already")`
5. Seed historical `action_log` bookmark `✅ localpart` lines into ledger after deploy (map local → full email via accounts.txt)
6. Primary mode still means first account only — but skip that first if already bookmarked for this book
7. Report: `Skip N already · tried M · success K`

**Anti-pattern:** loop all accounts for every bookmark of the same novel. Session/CF cost explodes with zero product gain.

Details: `references/bookmark-ledger-skip.md`, `references/powerstone-library.md`.

### 20. Persist sticky login cookies — re-login ONLY when expired (mandatory)
Do **not** full-login every `/sync`, powerstone, or bookmark when a usable session already exists.

Product requirement (Dez): after register/confirm/login produces active cookies, **save them** and reuse until dead.

Canonical bot implementation:
- Store: `/root/webnovel-tg-bot/sessions/<email>.json` (gitignored)
- Module: `wn/session_store.py` + `WebnovelService.ensure_session`
- Save full curl_cffi cookie jar via `Cookies.jar` / `get_dict()` (iterating `Cookies` as strings loses names — bug pitfall)
- Critical fields: `uid`, `ukey`, `_csrfToken`, proxy, impersonate, ua

`ensure_session` order (hardened 2026-07-21):
1. In-memory cache (csrf + (login_ok **or** info_ok) + not cf_blocked)
2. Disk restore → rebuild curl_cffi session → **live validate** `userInfoAjax code=0`
3. Full `login_check` + `open_mobile_session` only if needed
4. On mobile fail: retry forced chrome124 → **rotate sticky proxy** + re-login (up to ~3 attempts)
5. On success, persist cookies again
6. On CF / non-JSON / clear auth failure → **invalidate** disk+memory only (never delete the account)

**Cookies dead ≠ always OTP.** Trust OTP (`11318`) only if Webnovel marks device untrusted after re-login. Auto-complete Guard OTP via IMAP when that happens. Many re-logins are code=0 with no OTP.

Proven timings: full login ~3–10s; cookie restore ~0.4–0.7s.

Register alone does **not** yield durable PCM cookies — only after confirm ticket + mobile `login/login`.

Details: `references/sticky-session-cookies.md`, `references/sync-and-failed-accounts.md`.

### 21. Replacing the whole proxy pool (safe procedure)
Replacing `proxy.txt` alone is **not** enough. Sticky profiles keep the **old** proxy URL, and saved sessions still point at old IPs.

Safe swap (proven 2026-07-20 with ProxyScrape premium HTTP list):
1. Backup old `proxy.txt` + `device_profiles.json`
2. Normalize new list to `host:port:user:pass` (ProxyPool format). Input `user:pass@host:port` must be converted.
3. Rewrite `proxy.txt`
4. **Rebind every email** in that pool's `device_profiles.json` to a new sticky proxy (prefer unique host per account when pool ≥ accounts)
5. **Delete all** `sessions/*.json` so next action re-logins on the new IP (expect 11318 trust OTP once per account)
6. Sample-health proxies against `m.webnovel.com` (expect 200, not CF challenge)
7. Spot-test 1–2 accounts: force session + balance
8. Restart TG bot process so runtime pool reloads

Do **not** leave old sticky proxies while only swapping the pool file — accounts keep calling dead IPs.

Details: `references/proxy-pool-swap.md`.

### 22. Failed accounts policy (sync / PS / bookmark) — NEVER auto-delete
When `/sync`, Powerstone, or bookmark fails for an account:

| Action | Result |
|--------|--------|
| `accounts.txt` row | **kept** |
| Device profile | **kept** (proxy may have been rotated by retry) |
| Session cookies | **invalidate/delete file** if CF/auth/non-JSON |
| Daily PS ledger | **not updated** from live for that account |
| TG report | listed under `⚠️ Gagal N akun: reason` |
| Other accounts | continue |

Failed = **skip this action**, not ban/remove from pool. Next `/sync` or PS still includes them.

**Create failures** are different: account never enters `accounts.txt` if confirm/login/avatar gates fail.

Surface specific reasons, not only `mobile session failed`:
- `CF blocked (Just a moment / 403)`
- `no csrf token`
- `ticket exchange/info failed`
- `login failed code=...`

Details: `references/sync-and-failed-accounts.md`.

### 23. `/sync` must be paced + stoppable (default inter-account delay)
Burst `/sync` over large pools (e.g. 100 accounts, few warm sessions) causes mass CF/mobile fails even when credentials are fine.

Canonical UX (2026-07-21):
```
/sync           → default delay 3s between accounts
/sync now       → no delay
/sync 5s | 1m   → custom inter-account delay
```
- Background job + progress stream + 🛑 Stop
- Reuse cookies when valid; re-login only when dead (may auto trust OTP)
- Only one sync job at a time
- Powerstone vote success can still be true while a later balance refresh fails — do not conflate vote fail with balance/session fail

## Recommended workflow

1. Reverse current frontend auth from live assets.
2. Extract runtime RSA pubkey.
3. Register with browser-aligned payload.
4. Poll IMAP for the exact address only.
5. Extract longest `/f/a/` CTA.
6. Resolve to confirm.html.
7. Call confirm endpoint with double-encoded emailkey → ticket/userid/ukey.
8. If avatar in scope: mobile `login/login`+csrf → unique photo → `setUserAvatar`.
9. If profile polish in scope (default `/create`): human nick via `checkUserName` + `setUserSettings` (not leave `Daoist*`).
10. Login-check the same credentials.
11. If `11318`, auto-run device trust Guard OTP flow to reach `code=0` when possible.
12. Save only fully verified accounts (`email:password:userid:avatar_path:nickname` when polish ran).

## Output discipline

- `Registration submitted` after register only
- `Confirmed` after ticket/userid
- `Avatar uploaded` only after setUserAvatar `code=0`
- `Nickname set` only after setUserSettings `code=0` + userInfo verify (not still `Daoist*`)
- `Login proven` / `Success` only after password accepted (+ avatar/nick when in scope)

## References

- `references/webnovel-auth-findings.md` — reverse-engineering notes
- `references/profile-avatar-upload.md` — mobile session + setUserAvatar proven path
- `references/human-profile-nickname.md` — human email/nick generators, anti-template diversity, setUserSettings / checkUserName, mass `wn-rename`
- `references/powerstone-library.md` — powerstone vote + library bookmark (live-proven)
- `references/telegram-powerstone-bot.md` — TG bot full pool isolation, unlimited /create, stream+Stop, inter-account delay
- `references/tg-bot-isolation-and-jobs.md` — **latest** option-2 isolation + unlimited create/stream/Stop (prefer if older telegram ref is stale)
- `references/device-isolation.md` — sticky proxy + desktop/mobile fingerprint (autoreg **and** bot paths)
- `references/register-risk-captcha-11401.md` — register `11401` reCAPTCHA sitekey + solve/resubmit (not Banned)
- `references/cf-mobile-session.md` — chrome120 CF `Just a moment` / JSON parse fail on sync; chrome124 + retry
- `references/powerstone-daily-ledger.md` — auto remaining without `/sync` (00:00 UTC+8 grant)
- `references/powerstone-ledger-first-vote.md` — skip used-today accounts; amount=N must not pre-scan whole pool
- `references/bookmark-ledger-skip.md` — one account can bookmark a novel once; skip already-bookmarked on re-run
- `references/register-domain-round-robin.md` — `<REDACTED>` + `<REDACTED>` + `<REDACTED>` RR; retire `<REDACTED>` for new creates
- `references/create-soft-ok-login-csrf.md` — confirm+polish OK but passport `no csrf` → save anyway
- `references/sticky-session-cookies.md` — persist PCM cookies; restore before login; invalidate on expire/CF
- `references/proxy-pool-swap.md` — safe full proxy replacement + sticky rebind + session wipe
- `references/create-delay-and-concurrency.md` — `/create` delay picker + safe concurrent create+PS
- `references/sync-and-failed-accounts.md` — `/sync` pacing, clear errors, retry/rotate, **failed ≠ delete account**
- Project mirror: `/root/webnovel-autoreg/docs/endpoints-powerstone-library.md`
- Companion: `webnovel-signup` (**overlaps heavily** — gates + RSA/JSONP/IMAP live there; product/PCM/TG gates live here; curator candidate to merge later)
