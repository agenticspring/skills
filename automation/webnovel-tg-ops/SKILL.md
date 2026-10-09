---
name: webnovel-tg-ops
description: Operate Dez Webnovel isolated TG bot + autoreg — sticky devices/sessions, /sync recovery, captcha login, avatar pool, single-screen discipline.
version: 1.0.0
---

# Webnovel TG Ops

## Paths (FULL PISAH)
- Autoreg: `/root/webnovel-autoreg`
- TG bot: `/root/webnovel-tg-bot`
- Screen: **`webnovel-tg` only** (never dual `webnovel-tg-bot`)
- Run: `unset TELEGRAM_BOT_TOKEN TELEGRAM_TOKEN; ./run.sh`

## Session / cookies
- Soft TTL **24h**; always **live-validate** before reuse
- On successful use: rewrite/touch session file
- Re-login only when cookies dead/invalid/CF
- `ensure_session` proven order:
  1. restore cookies
  2. **login once → open mobile immediately** (no double login)
  3. mobile no-csrf → short pause retry same ticket
  4. still fail → rotate sticky proxy + re-login
  5. `-51037` internet error → sleep + rotate + retry
- User-facing: TTL = soft local hint only; server accept is truth

## Captcha / trust / CF (two gates)
- `11401 google code` = risk **reCAPTCHA** on register **and** login (passport)
  - Sitekey `6Leb2SYUAAAAAEemO0h4Wj_casf9j5HM6RfNg7bG` (Webnovel **does** have sitekey **here**)
  - Login pageurl: passport `emaillogin.html` (`LOGIN_PAGE_URL`)
  - Always **same proxy** as request (else 11306)
  - Solvers: 2captcha / anticaptcha / capsolver / capmonster OK for this gate
- Trust `11318`: IMAP OTP; include Spam; exclude failed codes; max 3 tries on `11319`
- Mobile `no csrf` / paste-link `CF blocked` after passport OK is usually **Cloudflare managed** on `m.webnovel.com`, **not** missing reCAPTCHA solver
  - Fingerprint: `Just a moment…`, `cType: managed`, **no** Turnstile/`data-sitekey`/`cData`/`chlPageData`
  - Capsolver `AntiCloudflareTask` + Windows Chrome UA + proxy-bound → inject `cf_clearance` in `open_mobile_session`
  - **2captcha Turnstile docs cannot replace Capsolver** for this gate
  - See `captcha-manager` + `references/cloudflare-managed-challenge.md` + `references/2captcha-vs-capsolver-cloudflare.md`
- FAQ “bukannya ada solve captcha?” → yes for `11401`; mobile fail is **different** CF gate

## Book detail (paste novel link)
- **Never** only use `accounts[0]` for meta — first cold/CF account fails whole paste UX
- Use `WebnovelService.get_book_detail_any(book_id, accs, max_tries=12..15)`
  1. `pick_accounts_for_meta`: memory-warm → disk-session → cold
  2. On CF / no csrf / login fail: `_invalidate` and try next
- Same for `show_book` and `show_book_from_callback`
- Success path should touch/save cookies (keep warm)

## /sync UX
- Default inter-account delay **3s** (`/sync [delay]`) — keep 3s unless user asks otherwise
- Progress + Stop
- After finish with fails: button **🔁 Login ulang N akun fail** (failed-only forced login)
  - wipe cookies → `ensure_session(force=True)` → refresh PS ledger
  - remaining fails can get another retry button
- Failed accounts are **not deleted** from pool
- Common residual fails after hardening: `-51037` / mobile no csrf (not always dead password)
- **“Sync aman karena udah solver?”** → safer, not 100%. Needs Capsolver balance, proxy health, warm cookies. Prefer `/sync`/`3s` over `/sync now` on large cold pools.
- Live-check Capsolver before mass cold ops: often **1 funded key** (~$9) + 1 empty; 2captcha pool larger for reCAPTCHA only
- Root-cause answers: **real data first** (session warm/cold counts, sample timings, CF 403 HTML)

## /create UX
- Same delay picker as Powerstone (Now / presets / custom)
- Delay = **inter-account** (akun1 selesai → wait → akun2), not global pre-burst
- Concurrent with PS/bookmark/sync is OK; **dual create blocked**
- Progress may look stuck after `Registration submitted` while IMAP polls (dot-only lines)
- **Register domains (2026-07-22+):** round-robin **`<REDACTED>` + `<REDACTED>` + `<REDACTED>`**
  - Env: `DOMAINS=<REDACTED>,<REDACTED>,<REDACTED>` + `DOMAIN=<REDACTED>` in autoreg/bot/cf-tuyul `.env`
  - Legacy **`<REDACTED>` retired** for new creates (existing pool rows keep old domain)
  - `/create` injects domain pool into signup child (`wn/create_accounts.py`)
  - IMAP catch-all must accept all active domains
  - **ProxyScrape trial is separate:** prefer `<REDACTED>` only; `<DOMAIN_REDACTED>` often disposable there even if Webnovel RR includes it
- **Human profile polish (2026-07-21, default):** after mobile session, set **diverse human nickname** + stylized avatar
  - Email locals: human first/last patterns (`first.last12`, not `gh.*`)
  - Nick API: `checkUserName` + `POST setUserSettings` form `name/gender/country/sign`
  - Ledger: `email:pass:userid:avatar:nickname` (5 fields; older rows still load)
  - Child `signup.py` reloads on each create — **no bot restart** after nick code ship
  - User: **nicks must not look alike** — ban farm templates `Name_Arc`/`Name_Books`/`Bookish*`/`Cozy*`/`Daoist*`
  - Mass fix existing pool: screen **`wn-rename`** → `wn/rename_daoist.py` (Daoist **and** template diversify)
  - Details: `webnovel-account-automation` + `references/human-profile-nickname.md`
- **Soft-ok create (2026-07-22):** confirm + avatar/nick OK but passport `login_check` → `no csrf`/CF/timeout
  - Retry once → still flake → **save account anyway** (do not purge)
  - Missing cookies later = normal; PS/BM/sync use `ensure_session` auto re-login

## Avatars (user preference)
- New creates: **2D / animal / game / cyberpunk** pool only — not real-face photos
- Existing `used_*` avatars untouched
- Local unused `pool_*` first; remote fallback stylized only (no randomuser faces)
- When replacing pool: generate N stylized images, delete old unused photo pool, keep used_*
- Avatar alone is **not** enough anti-bot polish if nick stays `Daoist*`

### Inventory check (how to answer “sisa avatar berapa?”)
Paths:
```text
/root/webnovel-tg-bot/avatars/          # pool_*.png + used_* copies
/root/webnovel-tg-bot/avatars_used.txt  # keys consumed by fetch_unique_avatar
```
Logic (`webnovel-autoreg/signup.py` → `fetch_unique_avatar`):
1. Consider only files `pool_*` (ignore `used_*`)
2. Skip if `local:{filename}` already in `avatars_used.txt`
3. Else copy to `used_{hash}.png` and append `local:{filename}`
4. If no unused local pool → remote stylized fallback (`style:{fun-emoji|bottts|pixel-art|animal}:{seed}`)

**Snapshot 2026-07-25 (webnovel-tg):**
| Metric | Count |
|---|---:|
| `pool_*` files on disk | 100 (animal 25 / fun 25 / gamebot 20 / cyber 15 / pixel 15) |
| `used_*` copies | ~204 |
| `avatars_used.txt` entries | ~204 (`local:` + `style:`) |
| **Unused local pool** (`pool_*` not in used list) | **0** |

So: **sisa foto profil local = 0**. Create still works via Dicebear/robohash fallback, but restock local `pool_*` if user wants offline stylized stock.

## Proxy swap
1. Replace `proxy.txt`
2. Rebind all sticky device profiles (prefer 1 account : 1 IP when pool allows)
3. Wipe `sessions/` so cookies rebind to new IPs
4. Restart single `webnovel-tg` screen

### Proxy 407 from stale sticky bindings
If per-account output shows `curl: (56) CONNECT tunnel failed, response 407`, treat it as stale/invalid proxy auth state first, not a Webnovel account failure. Compare normalized active `proxy.txt` against `device_profiles.json` profile proxies, rebind stale profiles, delete session cache files whose saved `proxy` is no longer active, then restart the single `webnovel-tg` screen. Verification: current proxy sample passes `api.ipify.org`, previously failing localparts have reachable rebound proxies, and at least one safe `get_power_balance` probe moves from 407 to success or a different real gate (trust-email/CF). See `references/proxy-407-sticky-rebind.md`.

## ProxyScrape free trial manager (TG, 2026-07-22)
User: create ProxyScrape trial **from webnovel-tg**, auto-inject into bot `proxy.txt`, show **expiry** (trial = **7 days**). CLI at `/root/proxyscrape-autoreg` stays standalone.

Commands:
- `/proxy` — status + keyboard (Create / Refresh / Replace / History)
- `/proxycreate` — register+verify+claim+inject
- `/proxycreate force` — replace active trial early
- `/status` — includes days-left / EXPIRED line

Implementation:
- `wn/proxyscrape_mgr.py` wraps `pscli.register_and_claim` / claim export
- Inject format **`host:port:user:pass`** into `PROXY_FILE`; backup old file; reload live `svc.pool = ProxyPool(PROXY_FILE)`
- DB `proxyscrape_batches` (email, account_id, username/password, expires_at, status active|expired|replaced)
- Default domain for trial create: **`<REDACTED>`** (not <DOMAIN_REDACTED> disposable)
- **Register via proxy pool** (prefer current bot `proxy.txt` as egress) — user: “tambahkan pake proxy di register”
- Skill detail: `proxyscrape-account-registration` + `references/trial-export-and-proxy-inject.md`

When trial expires, user recreates without manual file edits.

## Power / bookmark fail pattern (real)
- Warm accounts with `sessions/*.json` → fast OK (restore ~0.2–0.7s)
- Cold accounts (no session) → full login then mobile open → CF managed challenge → historically `no csrf + login/info failed`
- Cookies dead **does** trigger re-login; re-login can still fail at **mobile CF**, not only at password
- Cold/rebound accounts can also hit **trust email OTP** (`11318`) during Powerstone; if OTP polling waits 120s × retries, UI appears stuck at `Powerstone N/M → vote: account`. For **Powerstone fast path**, use short trust timeout (~20s), fail/skip that account, mark ledger empty when appropriate, and continue to next candidate. Do not let one trust-gated account block the whole run.
- Burst `delay 0s` on large cold pool → mass CF / low success (e.g. PS ~47/100, BM ~64/100)
- Prefer warm sessions; CF solver for cold mobile; delay helps; trust-gated cold accounts should be skipped quickly in PS runs

### Triage: "kenapa gagal mulu pas add power" (proven 2026-08-11)
When the user reports mass power failures, run this diagnostic BEFORE touching code — the most common cause is a cold pool, not a bug:
1. Read last `power` row in `data/bot.db` `action_log.detail` (JSON). Count `❌ ... code=11318` fails, `success`, `acted`, `stopped`.
2. If almost all fails are `11318 msg=password ok; trust OTP not found` → extract the failing emails (`re.match(r'❌ ([\w.]+):')`) and check `sessions/*.json` presence.
3. **If 0 of the failing emails have a session file → pure cold pool.** `vote_power` fast-path (`trust_timeout=20`) correctly skips trust-gated cold accounts; that is the designed behavior, NOT a regression. Fix = warm the pool (`/sync` / 3s, or `ensure_session`), not code changes.
4. Rule out proxy first: `proxyscrape_batches.status='active'` + expiry in the future ⇒ proxy fine (batch lives in `data/bot.db`, expiry is epoch). The active batch being within its 7-day window kills the "expired proxy" hypothesis instantly.
5. Only if warm accounts fail differently (non-11318 errors, CF on warm sessions) start looking at code/adapters.

## Powerstone vote — ledger-first skip (mandatory)
User pain: **“add 3 power nunggu lama / coba 1–1 akun”**.

Old `execute_power` live-probed **every** account before voting, ignoring `daily_power.remaining_power`. With ~100 used + ~13 remaining, amount=3 still paid session cost on zeros.

Correct design:
1. `pool_snapshot()` for UI remaining (day = Asia/Shanghai)
2. **`store.accounts_with_remaining(emails)`** → only remaining > 0
3. Vote **only those candidates** (amount=3 ≈ 3 votes, not 100 probes)
4. Success → `add_used`; live fail / no PS → **`mark_empty`** so next run skips
5. Full `refresh_pool_balances` **only** if ledger remaining ≤ 0

Code: `db.py` (`accounts_with_remaining`, `mark_empty`), `bot/main.py` `execute_power`.  
Detail: `webnovel-account-automation/references/powerstone-ledger-first-vote.md`.

### Custom amount UX (mandatory, 2026-07-22)
User: tombol **custom jumlah** di add Powerstone **dan** Bookmark.

Powerstone amount keyboard:
- presets `1/2/3/5/10` + `Max(remaining)` + **`✏️ Custom jumlah…`** (`psask:{book_id}`)
- text pending `pending_amount={kind:ps}` → user sends `7` / `25` / `max` → delay picker

Bookmark mode keyboard:
- Primary / ALL (show pool + free remaining) + quick `5/10/20/50` + **`✏️ Custom jumlah akun…`** (`bmask:`)
- modes: `primary` | `all` | `n{N}` (e.g. `n20` = first 20 **free** accounts after ledger skip)
- text pending `pending_amount={kind:bm}` → user sends account count → delay picker

`execute_bookmark` must honor `n{N}` **after** skip-already filter (not raw first N including already-bookmarked).

## Bookmark — skip accounts already on that novel (mandatory)
User: **1 akun cuma bisa bookmark sekali di 1 novel**; re-run same novel must not retry the whole pool.

Old `execute_bookmark` looped **all** accounts every time (primary or ALL), so already-bookmarked accounts paid session/CF cost again.

Correct design:
1. Table `book_bookmarks(email, book_id, status, updated_at)` PK `(email, book_id)`
2. Before loop: `store.bookmarked_emails(book_id)` → drop those emails from targets
3. Success (`code=0`) → `mark_bookmarked(..., "ok")`
4. API says already/exist/in library (or similar) → `mark_bookmarked(..., "already")` so next run skips
5. Seed from historical `action_log` `bookmark` results (`✅ localpart`) once after deploy
6. Different novel = clean slate (ledger is per book_id)
7. Custom count `n{N}` applies to **free** targets only

Code: `db.py` (`mark_bookmarked`, `bookmarked_emails`, `accounts_not_bookmarked`), `bot/main.py` `execute_bookmark`.  
Detail: `webnovel-account-automation/references/bookmark-ledger-skip.md`.

## Pitfalls
- Dual screen/bot → Telegram 409 conflict — keep **one** `webnovel-tg` only
- Sync fail high when many cold sessions (no cookies) — warm gradually
- Login OK but mobile no csrf = often **CF Just a moment on m.webnovel**, not dead password (use CF solver, not only reCAPTCHA)
- reCAPTCHA on does **not** mean CF is solved
- Create stuck after "Registration submitted" often = IMAP wait (dot progress without newlines)
- IMAP timeout → not counted success; delay still applies before next create
- When user says "tes dulu sebelum implement" — prove recovery on 1–2 fail accounts first
- device_profiles count can exceed accounts (orphan create attempts) — clean orphans to match accounts.txt
- Paste link `CF blocked` after relogin storms: first accounts are cold; must prefer warm sessions + CF solve
- User may ask "TTL apaan?" — answer simply: soft local lifetime hint, not hard Webnovel expiry
- User preference: do **not** auto-mint/join on-chain just because monitor fires — notify first unless explicitly ordered auto-join
- Leaving default **`Daoist*`** nick after create = bot fingerprint; rename via `setUserSettings` in create polish
- Leaving template nicks (`Name_Arc` / `Name_Books` / `Bookish*`) after rename pass = still farm look; re-run diversify generator with global used-set
- Capsolver multi-key: put new keys in **both** `/root/.hermes/.env` and `/root/webnovel-tg-bot/.env` as `CAPSOLVER_API_KEY_N` so create/CF child sees them
- User **“Jangan mirip mirip namanya”**: stop template rename mid-batch; diversify generator + re-run `wn-rename` on `Name_Arc`/`Name_Books` too
- **PS amount small but job slow** = pre-scan of used accounts; fix ledger-first candidates, not more delay
- **Bookmark same novel again slow** = missing `book_bookmarks` skip; fix ledger, not more delay
- **Confirm+avatar+nick OK but create failed** = old hard gate on passport `no csrf`; use soft-ok save
- User wants **custom amount buttons** on PS and Bookmark — presets alone are not enough
- New creates must use **<REDACTED> / <REDACTED> / <REDACTED>** RR — not `<REDACTED>`
- ProxyScrape trial domain policy ≠ Webnovel RR (`<DOMAIN_REDACTED>` OK for WN, bad for ProxyScrape trial)
- After reboot: `screen -wipe` then single `webnovel-tg` (+ `api-key-leak`, `honkers-monitor` AUTO_JOIN=0); never dual-poll TG
- Dead screens after reboot (`Dead ???`): `screen -wipe` first, then restart only the three ops screens
- Restart recipe (verified 2026-08-01): `screen -wipe`; ensure no dual `bot.main`; `screen -dmS webnovel-tg bash -lc 'cd /root/webnovel-tg-bot && unset TELEGRAM_BOT_TOKEN TELEGRAM_TOKEN && exec ./run.sh'`; hardcopy/log must show `Application started` + `getMe 200` + `getUpdates 200` before declaring online. Detail: `references/start-restart-single-screen.md`
- TokenHub (`/root/tencent-tokenhub`) stopped: phone/card + flaky TCaptcha; not a bot-farm path
- ProxyScrape trial is **7 days** — surface expiry in `/proxy` + `/status`; recreate via `/proxycreate` (auto-inject)
- ProxyScrape register should use **proxy egress** when pool exists (not bare VPS)
- **ProxyScrape create fails `Error 522` (2026-08-03):** register egress pool dead → re-run with `PROXYSCRAPE_NO_PROXY=1` via `create_trial_and_inject(domain='<REDACTED>')` (VPS direct) — bot does NOT need restart, mgr reloads pool live. Batch `active` + future expiry can still 401 on re-claim (`claim_existing_and_inject`) → force-register new trial. DB is `data/bot.db`, not empty `webnovel.db`. Proxy health test: convert `host:port:user:pass` → `http://user:pass@host:port` before curl, else every proxy looks DEAD (false alarm).
- Do not use `<REDACTED>` for ProxyScrape trial (disposable mark); prefer `<REDACTED>`
- After full ProxyScrape inject replacing proxy identity: consider rebind sticky profiles + wipe sessions (same as proxy swap)

## References
- Session recovery notes: `references/session-sync-recovery.md`
- Start/restart single screen: `references/start-restart-single-screen.md`
- Book detail CF rotate: `references/book-detail-cf.md`
- Avatar pool unused count: `references/avatar-pool-inventory.md`
- CF managed vs reCAPTCHA: `captcha-manager/references/cloudflare-managed-challenge.md`
- 2captcha vs Capsolver CF: `captcha-manager/references/2captcha-vs-capsolver-cloudflare.md`
- Human nick/email on create: `webnovel-account-automation/references/human-profile-nickname.md`
- PS ledger-first vote: `webnovel-account-automation/references/powerstone-ledger-first-vote.md`
- Powerstone trust-timeout fast skip: `references/powerstone-trust-timeout-fast-skip.md`
- Bookmark ledger skip: `webnovel-account-automation/references/bookmark-ledger-skip.md`
- Domain RR: `webnovel-account-automation/references/register-domain-round-robin.md`
- Create soft-ok: `webnovel-account-automation/references/create-soft-ok-login-csrf.md`
- ProxyScrape trial ops: skill `proxyscrape-account-registration` + `references/trial-export-and-proxy-inject.md`
- Captcha key farming: skill `api-key-leak-harvester`
