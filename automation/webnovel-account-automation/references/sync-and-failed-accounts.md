# /sync failures & failed-account policy

## What `/sync` does
Live-probe each account's Powerstone via PCM session, update local daily ledger.

It is **optional** for UI remaining (ledger auto-seeds at 00:00 UTC+8). Use `/sync` to re-check live.

## UX (2026-07-21)
```
/sync           # default inter-account delay 3s
/sync now       # no delay
/sync 5s
/sync 1m
```
- Progress stream + 🛑 Stop
- One active sync job only
- Create may run concurrently (separate process); dual sync blocked

## ensure_session retry ladder (A+B, 2026-07-21)
1. Memory cache (csrf + login_ok/info_ok, not CF)
2. Disk cookies → live `userInfoAjax code=0` → **refresh soft TTL / rewrite jar**
3. Full `login_check` **once** (auto 11401 captcha + 11318 trust OTP)
4. **A:** `open_mobile_session` immediately with that ticket (no double login)
5. Same-ticket short pause + reopen once
6. **B:** `rotate_profile_proxy` + re-login + open (≤3 attempts)
7. `-51037` Internet error → backoff + rotate (not infinite captcha)
8. Persist cookies on success; invalidate cookies on CF/auth death

See `session-recovery-ab.md` for the pre-implement live tests.

## Error strings (prefer these)
| Message | Meaning |
|---------|---------|
| `CF blocked (Just a moment / 403)` | Cloudflare HTML challenge on m.webnovel |
| `no csrf token` / `no csrf + login/info failed` | mobile bootstrap/session exchange incomplete (login may still be OK) |
| `ticket exchange/info failed` | login/login or userInfo not healthy |
| `login failed code=11401 ...` | risk captcha — should auto-solve; residual if solve/network fails |
| `login failed code=-51037 ...` | transient Webnovel/proxy after captcha or login |
| `login failed code=11318 ... trust verify failed` | Guard OTP wrong/stale (multi-try should reduce) |
| generic `mobile session failed` | **legacy** — replace with reasons above |

## Failed account policy (product)
**Never auto-remove** accounts from `accounts.txt` because sync/PS/bookmark failed.

| Artifact | On fail |
|----------|---------|
| accounts.txt | keep |
| device_profiles | keep (proxy may already be rotated) |
| sessions/*.json | delete if session proven dead |
| daily_power ledger | skip live update for that email |
| TG output | list under Gagal with reason |

Next `/sync` or PS still includes the account.

### Create failures (different)
If register/confirm/login/avatar gates fail during `/create`, account is **not** written to success ledger.

### Vote vs balance
Powerstone job can report **vote success** while a later pool balance refresh fails (`login/bal CF blocked`). Do not tell the user the vote failed when only the refresh failed.

## Common mass-fail pattern
```
46 sisa / 46 total (100 akun)
⚠️ Gagal 54 akun: mobile session failed...
```
- Not 54 dead accounts
- Often: few warm sessions + burst traffic after proxy swap / session wipe
- Fix: paced `/sync 3s` or `/sync 5s`, chrome124 profiles, recovery A+B, cookie warm

## Improved pattern after cookie warm + login captcha (2026-07-21)
```
83 sisa / 83 total (100 akun)
⚠️ Gagal 17 akun: mostly -51037 + some no csrf
```
- ~17% residual fail on cold/transient is better than ~30% mass fail
- Probe 1 fail account before declaring pool dead: often login OK, mobile csrf fail
- Re-sync later usually recovers many `-51037`

## Related
- `cf-mobile-session.md`
- `sticky-session-cookies.md`
- `session-recovery-ab.md`
- `login-risk-captcha-11401.md`
- `device-isolation.md`
