---
name: webnovel-signup
description: "Automate Webnovel account registration — curl_cffi/urllib, RSA PKCS1 v1.5, JSONP, IMAP, device trust, optional profile avatar."
version: 1.2.0
author: spring (<HANDLE_REDACTED>)
platforms: [linux, macos, android]
prerequisites:
  commands: [python3]
  env_vars: [IMAP_HOST, IMAP_PORT, IMAP_USER, IMAP_PASS, DOMAIN]
---

# Webnovel Signup Automation

Mass account registration for Webnovel. Passport/ptlogin is mostly stdlib-HTTP; **PCM APIs** (avatar, powerstone, library) need curl_cffi (CF on `m.webnovel.com`).

Canonical project: `/root/webnovel-autoreg` (`<HANDLE_REDACTED>/webnovel-autoreg`).
Run on VPS: `./run.sh N` or `.venv/bin/python signup.py N` — bare system `python3` may lack curl_cffi.

## Architecture

```
www.webnovel.com        ← Cloudflare JS challenge
m.webnovel.com          ← mobile PCM APIs (avatar); use curl_cffi chrome124
passport.webnovel.com   ← NO Cloudflare — direct HTTP works
ptlogin.webnovel.com    ← API subdomain, JSONP endpoints
www.yueimg.com          ← Static JS assets (pubkey in login_v6.js)
post.eu.spmailtechnol.com ← email tracking CDN for activation CTAs
```

## Registration Flow (proven end-to-end)

1. **Get RSA pubkey** — fetch `login_v6.js`, extract `LoginV1.config.pubkey` every run
2. **Get CSRF token** — visit register page, call `getInparams` JSONP → cookie
3. **RSA-encrypt password** — PKCS1 v1.5 with DER-decoded n/e, base64 output
4. **Submit register** — GET JSONP `ptlogin.webnovel.com/login/doregister`
   - Match browser payload: `accountType=102`, `email`+`account`, encrypted `password`, `validateCode=`, **`nextAction=` empty**, `appid/areaid/target/returnurl`
   - Avoid extra fields like `backUrl` / `fromuid=0` unless browser sends them
   - **If `code=11401`:** this is **risk reCAPTCHA**, not ban. Solve Google reCAPTCHA v2 (sitekey `6Leb2SYUAAAAAEemO0h4Wj_casf9j5HM6RfNg7bG` from `login_v6.js`) and resubmit with `nextAction=1` + `validateCode=<token>`. Module: `captcha_solver.py`. Log as `Risk captcha`, never `Banned (11401)`.
   - **CRITICAL — same proxy as register:** solve captcha with **proxy-bound** task using the **exact same proxy** as `doregister`. Proxyless tokens often return **`11306 Verification failed`** even when token length looks valid. Prefer `anticaptcha-proxy` / `capsolver-proxy` / `2captcha-proxy`; retry once on 11306 with a fresh token.
5. **Poll IMAP for that exact address only** — never bare `UNSEEN FROM webnovel` (steals other catch-all mails)
6. **Extract CTA tracking link** — prefer longest HTML `href=".../f/a/..."` (not `/q/` pixel)
7. **Follow tracking → confirm.html** — try direct/no-proxy first if proxy CDN 403s
8. **Confirm endpoint** — `ptlogin.webnovel.com/login/confirm` with **jQuery-style double-encoded emailkey** → `ticket`/`userId`/`uKey`
9. **Profile avatar (when in scope)** — immediately after confirm ticket:
   - curl_cffi `chrome124` session on `m.webnovel.com`
   - seed `uid`/`ukey` from confirm `userId`/`uKey`
   - bootstrap CSRF via `GET /id`
   - `GET /go/pcm/login/login?_csrfToken=&ticket=&guid=` (must include csrf)
   - prove `userInfoAjax` `code=0`
   - `POST /go/pcm/user/setUserAvatar?_csrfToken=` multipart field `image` via **CurlMime**
   - unique image per account (local `avatars/` → randomuser → dicebear)
10. **Login proof** — `ptlogin.webnovel.com/login/checkcode` with same password
11. **Device trust (11318)** — if Untrusted Device, auto-complete Guard OTP (see below)
12. Save ledger only when gates pass

## Device trust (11318) — proven

When `checkcode` returns `code=11318`:
1. Read `data.encry` + `data.sessionKey` from the checkcode response
2. Call `GET ptlogin.webnovel.com/login/sendTrustEmail` with `method=LoginV1.trustEmailCallback` + `encry`
3. Poll IMAP for **exact target address** mails with subject like `Webnovel Support` / `Dukungan Webnovel` (prefer `after_ts` around sendTrustEmail)
4. Extract **alphanumeric Guard code** from body text:
   - Example: `Here is the Webnovel Guard code you need to login to account 「 name 」: BRAAOz`
   - Code is typically **6 mixed alnum chars** (e.g. `BRAAOz`, `xW0Isq`) — **NOT** numeric years like `2019`
5. Call `GET ptlogin.webnovel.com/login/checkTrust` with `method=LoginV1.checkTrustCodeCallback`, `encry`, `trustcode`, `sessionKey`
6. `code=0` → device trusted / full login jump path

**11401 google code** is reCAPTCHA risk on **login and register**. Not 11313, not a hard ban.
- Login: password often already accepted; captcha is risk gate.
- Register: browser forces captcha then resubmit (`nextAction=1` + `validateCode`). Auto-solve via `captcha_solver.py` before failing the account.

## Key Techniques

### RSA PKCS1 v1.5 (pure Python, zero deps)
```python
k = 128  # 1024-bit = 128 bytes
ps = bytes(random.randint(1, 255) for _ in range(k - 3 - len(pwd)))
eb = b"\x00\x02" + ps + b"\x00" + pwd
m = int.from_bytes(eb, "big")
c = pow(m, e, n)
b64 = base64.b64encode(c.to_bytes(k, "big")).decode()
```

### DER Decode Public Key
Parse SubjectPublicKeyInfo:
- Outer SEQUENCE → AlgorithmIdentifier SEQUENCE → BIT STRING → inner RSAPublicKey SEQUENCE → INTEGER n, INTEGER e
- See `references/der-rsa.md` for full decoder

### Password Rules
- 6-18 alphanumeric ONLY (no symbols, no spaces)
- MUST contain BOTH letters and digits
- Client regex: `/^(?!([a-zA-Z]+|\d+)$)[a-zA-Z\d]{6,18}$/`
- Prefer fixed password from `.env` `PASSWORD=` (never hardcode in source/README)

### Email Verification + Confirm
- Prefer HTML `href=` CTAs; pick the **longest** `post.eu.spmailtechnol.com/f/a/...`
- `/q/` links are 1x1 GIF beacons — ignore
- Follow redirect to `passport.webnovel.com/confirm.html?emailkey=...`
- Confirm via JSONP `login/confirm` (not HTML-open alone)
- **emailkey encoding (critical):** browser keeps the raw once-encoded query value, then jQuery encodes again → wire form is **double-encoded** (`%2F`→`%252F`, `%3D`→`%253D`). Decoded or single-encoded yields `11311 Email key is empty` or `code=2`
- Accept confirm when response has `ticket` + `userId` and code in `{0, 4}` (`4` = already confirmed / try login, still returns ticket)
- Require target address in To/Delivered-To/body before using a mail

### Login proof codes (`login/checkcode`)
| code | meaning | password OK? |
|------|---------|--------------|
| `0` | full login ok | yes |
| `11318` | Untrusted Device (trust email) | yes |
| `11401` + google/nextAction | risk reCAPTCHA (login **or** register) | login: password OK; register: solve+resubmit before fail |
| `11313` | email/password incorrect | no |
| `11314` (reset endpoint) | account does not exist | no |

Save to `accounts.txt` only when password is accepted (`0` / `11318` / captcha-after-password `11401`).
When avatar is in scope, also require `setUserAvatar` `code=0` before counting full success.

## Profile avatar (proven)

```
confirm → uid/ukey cookies + ticket/userId/uKey
       → curl_cffi chrome124 → m.webnovel.com/id (csrf)
       → GET /go/pcm/login/login?_csrfToken&ticket&guid
       → userInfoAjax code=0
       → POST setUserAvatar multipart image (CurlMime)
```

Pitfalls specific to avatar:
- Missing `_csrfToken` on `login/login` → `400 {}`
- `uid`/`ukey` alone without `login/login` → PCM `user session invalidate` (-401)
- curl_cffi `files=` unsupported → use `CurlMime` + `multipart=`
- Prefer confirm ticket immediately (fresh); login ticket is second chance
- Unique **stylized** avatars only for new creates (`pool_fun/animal/gamebot/pixel/cyber`); do **not** fallback to randomuser real faces; track `avatars_used.txt`; leave existing `used_*` alone

See `webnovel-account-automation` → `references/profile-avatar-upload.md`.

### Avatar pool restock — free internet sources (no AI generation)

When the local `pool_*` avatars are exhausted, restock from free APIs (never AI image generation — user preference, wasteful tokens):

1. **Clear old pool** — remove `pool_*` and `used_*` files from `avatars/`; empty `avatars_used.txt`
2. **Themes x Styles x 5 variants = 100** — 5 themes × 4 styles × 5 per combo
   - Themes: `anime` (Dicebear adventurer/lorelei/fun-emoji/bottts/avataaars), `mainan` (Robohash set3), `gunung` (Unsplash mountain photos), `game` (Dicebear pixel-art/fun-emoji/bottts/notionists), `pemandangan` (Unsplash landscape photos)
   - Styles: `2d`, `cartoon`, `3d`, `realistis` — applied as PIL filters (color/contrast/sharpness/smooth)
3. **Free sources** (no API key, no AI tokens):
   - `api.dicebear.com/9.x/{style}/png` — character/avatar styles
   - `robohash.org/{seed}.png?set=set3` — robot/toy styles
   - `images.unsplash.com/photo-{id}?w=512&h=512&fit=crop` — landscape photos
   - `picsum.photos/seed/{seed}/512/512` — fallback random photos
4. **Style filter** — apply lightweight PIL tweaks per style (see `references/avatar-pool-restock.md`)
5. **Naming** — `pool_{theme}_{style}_{00-04}.png`
6. **Used tracking** — `avatars_used.txt` records `local:{filename}` per used avatar; `fetch_unique_avatar` in signup code checks this set before picking from pool

See `references/avatar-pool-restock.md` for runnable restock script.

## References

## Sticky device isolation (multi-account)

Do **not** use one fixed UA/proxy for every email.

- Module: `device_profiles.py` → durable map in `device_profiles.json` (gitignored)
- Per email: sticky `proxy`, desktop UA/AL (passport), mobile UA + `impersonate` (PCM)
- Prefer **chrome124 only** for mobile impersonate; **chrome120 often CF-blocks** `m.webnovel.com` (`Just a moment` 403 → JSON parse fail); chrome131 also flaky
- Call `get_or_create_profile(email)` in register, login_check, and open_mobile_session
- Same email must reuse the same proxy/fingerprint across runs (sticky) **until ban**
- **Ban retry:** `mark_dead` + `rotate_profile_proxy(email, dead_proxy=...)` then pass new proxy into `register`. Pool `random()` alone is insufficient — sticky reload snaps back to banned IP (UI looks "stuck after 1 banned IP")
- If caller passes an explicit proxy into `register`, rebind sticky when it differs (`update_profile_proxy`)
- **Path overrides (for TG bot isolation):** honor env `DEVICE_PROFILES_FILE`, `WEBNOVEL_ACCOUNTS_FILE`, `WEBNOVEL_PROXY_FILE`, `WEBNOVEL_AVATAR_DIR`, `WEBNOVEL_AVATAR_USED_FILE` so `/create` from bot writes into bot pool, not autoreg defaults
- See `webnovel-account-automation/references/device-isolation.md`
## Pitfalls
- **Pubkey changes** — fetch `login_v6.js` each run
- **CSRF from cookie**, not body
- **Gmail locale folders**
- **HTML-only bodies**
- **Never IMAP `UNSEEN FROM webnovel` alone** on catch-all
- **CTA vs pixel** (`/f/a/` vs `/q/`); pick longest `/f/a/`
- **Double-encode emailkey**
- **Blank `.env` shadowing** valid fallback creds
- **PASSWORD only via `.env`**
- **JSONP parse `callback({...})`**
- **Trust OTP freshness** — pass `after_ts` around `sendTrustEmail`; Guard codes are **alphanumeric**
- **Avatar needs login/login+csrf** — not ticket land alone
- **chrome124 only** for m.webnovel PCM; chrome120 often CF `Just a moment` 403 (sync fails as JSON parse error); chrome131 flaky
- **CF on PCM** — `m.webnovel.com` **managed** challenge (`Just a moment`, `cType: managed`); not reCAPTCHA. Capsolver `AntiCloudflareTask` with **Windows Chrome UA** + same proxy → inject `cf_clearance` → re-bootstrap for csrf. Module: `captcha_solver.solve_cloudflare_challenge`. Do not claim “we have captcha” solves this unless CF path is wired.
- **Sticky device profiles** — never one UA/proxy for all emails (`device_profiles.py`)
- **Ban must rotate sticky proxy** — not only pool.random; use `rotate_profile_proxy`
- **11401 ≠ Banned** — risk reCAPTCHA; solve then resubmit; only `-11051/-11055/-11053` as hard ban codes
- **11306 Verification failed** — almost always captcha IP mismatch (proxyless token vs proxied register). Force proxy-bound solve + one retry; do not keep rotating random proxies blindly
- **SSH bare python3** may miss curl_cffi — use `./run.sh` / `.venv`
- **Powerstone/library** share avatar PCM session; see `webnovel-account-automation` → `references/powerstone-library.md`
- **Status wording:** `Registration submitted` → `Confirmed` → `Avatar uploaded` → `Login proven`
- **Sticky PCM cookies (TG bot):** after mobile `login/login`, save full cookie jar under `sessions/<email>.json`; next `/sync`/PS/bookmark restore+live-validate first; full login only if dead. See `webnovel-account-automation/references/sticky-session-cookies.md`
- **Proxy pool swap:** rewriting `proxy.txt` alone is insufficient — rebind sticky profiles + wipe sessions. See `webnovel-account-automation/references/proxy-pool-swap.md`
- **Inter-account create delay:** env `CREATE_DELAY_S` — after each account finishes (success or fail), sleep before next; no sleep after last. TG bot `/create` picks delay like Powerstone and injects this env.
- **“Stuck” after Registration submitted:** usually IMAP wait (~120s). Same-line `polling....` dots do not stream to TG (line-based). Timeout → not success → still sleeps CREATE_DELAY_S. Not a freeze if PID alive. Log pattern: `Registration submitted` → `[imap] polling.... timeout` → `Not counted as success` → `Delay Ns before next account`.
- **New-create avatars:** stylized `pool_fun/animal/gamebot/pixel/cyber` only; never randomuser faces; leave existing `used_*` alone.
- **Failed create ≠ delete pool accounts:** only omits writing that email to success ledger. Existing `accounts.txt` rows are never removed because a later `/sync` failed (product bot policy — see `webnovel-account-automation` §22).
## References
- `references/der-rsa.md` — DER + PKCS1 detail
- `references/imap-gmail.md` — Gmail folders
- `references/identity-pools.md` — name pools
- `references/login-flow.md` — checkcode flow
- `references/device-trust-11318.md` — Guard OTP auto-trust after Untrusted Device
- `references/e2e-auth-gates.md` — end-to-end success gates + live error codes from validated runs
- Companion: `webnovel-account-automation/references/profile-avatar-upload.md`
- Companion: `webnovel-account-automation/references/powerstone-library.md`

- Companion: `webnovel-account-automation/references/powerstone-library.md`
- Companion: `webnovel-account-automation` — success-gate discipline + PCM product actions + TG bot surface (**overlaps heavily** with this skill; curator candidate to merge into one umbrella later)
- `webnovel-account-automation/references/telegram-powerstone-bot.md` — admin TG bot shells this signup via `/create` into **bot-local pool** (env path overrides; unlimited N + stream + Stop)
- `email-link-registration-automation` — class-level email-link signup pattern
- `stdlib-automation` — zero-dep Python patterns
