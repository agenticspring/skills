# Create soft-ok when passport login_check lacks CSRF

## Symptom (user log)
```text
✅ Confirmed ... ticket/userid
✅ Avatar uploaded
✅ Nickname set
❌ Login check failed code=-1 msg=no csrf
❌ Not counted as success because confirm/login finalization failed
```

## Root cause
After confirm, avatar/nick use **mobile** session from confirm ticket (`m.webnovel.com`) — often OK.

Final gate `login_check()` opens a **fresh passport** session (`passport.webnovel.com` → `getInparams` → cookie `_csrfToken`). If that cookie never appears (CF/flake/timeout), code returns `-1 no csrf` **before** password check.

Old behavior: purge / fail account even though email is verified and profile polished.

## Correct policy (2026-07-22)
In `mark_verified_account` (`signup.py`):

1. Always try `login_check` after confirm polish
2. Softable messages: `no csrf`, csrf, just a moment, cloudflare, timeout
3. Softable **only if** confirm issued `ticket` + `userid`
4. Retry login_check once (~1.5s pause)
5. If still soft-fail → **save** with confirm ticket/userid (soft-ok)
6. Hard fail / purge only when confirm never completed

## Why this is safe
- Confirm ticket proves account exists and email verified
- Register already accepted password encryption path
- TG bot `ensure_session` auto re-logins later when cookies missing
- Soft-ok accounts may lack `sessions/*.json` until first PS/BM/sync

## Code markers
```text
soft_login = True
✅ Keeping account: email confirmed + avatar + nick — passport csrf flake ignored
✅ Account saved (soft-ok: ...)
✅ Marked success (register + confirm + profile; login_check may soft-ok)
```
