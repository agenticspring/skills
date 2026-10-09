# Sticky PCM session cookies (Webnovel TG bot)

## Why
Full passport login on every `/sync` or power action is slow and often triggers trust OTP (`11318`). After a successful mobile session, persist cookies and reuse until invalid.

## Where
- Dir: `/root/webnovel-tg-bot/sessions/` (gitignored)
- File: `<email>.json`
- Code: `wn/session_store.py`, `WebnovelService.ensure_session`

## Save after successful mobile session
Capture full cookie jar from curl_cffi session:
- Prefer `session.cookies.jar` (real Cookie objects with name/value/domain)
- Fallback `session.cookies.get_dict()`
- **Bug:** iterating `for c in session.cookies` can yield bare strings → names become `None` and only forced csrf/uid remain

Always include at least:
- `uid`, `ukey` (or `ywguid`/`ywkey`)
- `_csrfToken`
- sticky `proxy`, `impersonate`, `user_agent`

## Restore path
1. Load JSON
2. Build curl_cffi Session with sticky chrome124 UA/impersonate
3. `cookies.set(name, value, domain, path)` for each
4. Live validate: `GET /go/pcm/user/userInfoAjax?_csrfToken=`
5. Accept only `status=200` + JSON `code=0`
6. Reject/delete on CF (`403` / `Just a moment`) or non-JSON

## ensure_session order (hardened 2026-07-21, recovery A+B)
Proven sequence — **test before reordering**:

1. Memory cache — csrf + (login_ok **or** info_ok), not CF
2. Disk restore → live `userInfoAjax code=0` → **auto cookie mgmt** (rewrite/touch soft TTL)
3. Full `login_check` **once** (auto 11401 captcha + 11318 trust OTP) → ticket
4. **Strategy A:** `open_mobile_session` **immediately** with that ticket (no second passport login)
5. Same-ticket tiny pause (~1s) + reopen once if csrf race
6. **Strategy B:** if still no csrf / mobile fail → `rotate_profile_proxy` + re-login + open (≤3 attempts)
7. Transient `-51037` / Internet error → short backoff + rotate + retry (do not spam captcha forever)
8. Persist cookies on success; invalidate disk+memory on CF/auth death — **never delete account**

### Anti-pattern: double login
Do **not** call `login_check` again just to open mobile when a ticket already exists. Double login wastes OTP/captcha and was the root of many false fails.

### Live probe (pre-implement test, 2026-07-21)
| Account | Result |
|---------|--------|
| `haruki.gupta206` | Strategy A: login → open mobile → PS balance=1; 2nd call restore ~0.5s |
| `leon.andersen681` | same success + cookie reuse |
| `nicholas.mitchell45` | captcha token OK then `-51037` / later mobile `no csrf` — recovery cannot invent a ticket |
| `amelia.mueller129` | login path OK-ish, mobile still `no csrf` residual |

## Auto cookie management (product)
| Knob | Value |
|------|-------|
| Soft TTL | **24h** (`DEFAULT_TTL_SEC = 86400`) — was 6h; still **live-validate**, not hard expiry |
| On successful restore / PS balance | rewrite cookies or `touch()` saved_at |
| On login+mobile success | save full jar |
| On CF / invalidate / non-JSON | delete session file only |

Soft TTL is **local**. Webnovel can kill cookies earlier (especially `__cf_bm`). Longer soft TTL only stops the bot from being overly suspicious; it does **not** force server-side lifetime.

## Cookies dead vs OTP
| Situation | OTP? |
|-----------|------|
| Cookies valid | no login, no OTP |
| Cookies dead, login code=0 | re-login, **no** OTP |
| Cookies dead, login 11318 | **yes** — auto Guard OTP via IMAP (Spam folder + multi-try on 11319) |
| Login 11401 | auto reCAPTCHA (proxy-bound), then may become 0 or 11318 |
| Fail before login (`-51037`) | may never hit OTP |

## Proven timings
- Full login: ~3–10s (longer with captcha/OTP)
- Cookie restore: ~0.4–0.7s
- Balance via restored session: works

## What register alone does NOT give
`doregister` ≠ PCM cookies. Cookies become useful only after confirm ticket + mobile `login/login` (and subsequent PCM calls).

## Related
- `sync-and-failed-accounts.md`
- `login-risk-captcha-11401.md`
- `cf-mobile-session.md`
- `session-recovery-ab.md`
