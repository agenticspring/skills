# Session recovery A+B (test-before-implement)

## User rule
When changing recovery for failed sync accounts: **test the strategy on 1–2 real fail accounts before coding it into the bot.**

## Strategies that worked / didn't (2026-07-21)

### A — Login once → open mobile immediately ✅
```
login_check (ticket)
→ open_mobile_session(ticket, userid, ukey, proxy)  # same ticket, no re-login
→ if csrf + (login_ok|info_ok): save cookies + PS
```
Proven on `haruki.gupta206`: PS balance=1; second call restored from disk in ~0.5s.

### B — Mobile no-csrf / fail → rotate + re-login ✅ (conditional)
```
open mobile fails (no csrf / info fail)
→ rotate_profile_proxy(email, dead_proxy=...)
→ login_check again on new proxy
→ open_mobile immediately
```
Use after A fails. Sticky rebind required (pool.random alone snaps back).

### C — Sleep + same ticket
Optional ~1–3s pause before reopening same ticket (csrf race). Minor; A usually enough.

### What does NOT fix
| Symptom | Why recovery stalls |
|---------|---------------------|
| `-51037` / `-51035` Internet error after captcha | No ticket issued — cannot open mobile until passport accepts login |
| Captcha token OK then Internet error | Retry with backoff + proxy rotate; don't infinite-solve |
| Login OK, exchange `1001 parameters error` | Bad/empty ticket/guid/csrf combo — re-login fresh ticket |
| Dual `bot.main` / dual screen | Progress + Stop die; cleanup to **one** `screen -S webnovel-tg` |

## Implementation map
- Code: `/root/webnovel-tg-bot/wn/client.py` → `ensure_session`, `_login_once`, `_mobile_usable`
- Cookies: `/root/webnovel-tg-bot/wn/session_store.py` (TTL 24h + touch)
- Login captcha/OTP: `/root/webnovel-autoreg/signup.py` → `login_check`, `poll_trust_code`

## Ops
After recovery deploy: single bot instance only.
```bash
# keep only:
screen -r webnovel-tg
# zombie names like webnovel-tg-bot with stopped process → quit
```
