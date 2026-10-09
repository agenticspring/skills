# CF mobile session failures (m.webnovel.com)

## Symptom (TG `/sync` / power / bookmark)

```
Expecting value: line 1 column 1 (char 0)   # legacy
CF blocked (Just a moment / 403)           # preferred
no csrf + login/info failed                # often CF underneath
mobile session failed for email@...        # too generic — expand
```

Bot expected JSON from PCM APIs; received HTML or incomplete session.

## Root cause (proven 2026-07-20 / 2026-07-21)

`GET m.webnovel.com/id` (bootstrap) and often PCM APIs return:

```
HTTP 403
<title>Just a moment...</title>   ← Cloudflare managed challenge (cType: managed)
```

Passport login can still succeed (`checkcode code=0` + ticket). Failure is **mobile PCM CF / session exchange**, not wrong password.

**Critical distinction:** reCAPTCHA solver (`11401`) does **not** clear this. Separate Cloudflare solver required.

### Correlated fingerprint
- Cold accounts without `sessions/*.json` hit CF bootstrap more
- Warm cookie restore often skips CF
- Burst delay 0s mass power/bookmark → many cold logins → more CF
- chrome120 historically worse; chrome124 preferred for curl_cffi impersonate

## Fix pattern (layered)

1. **Prefer warm sessions** for bulk ops and book detail (`pick_accounts_for_meta` / restore cookies first)
2. **CF managed solver** (primary for cold mobile open, 2026-07-21):
   - Capsolver `AntiCloudflareTask` with **Windows Chrome UA** + **same sticky proxy**
   - Inject `cf_clearance` → re-GET `/id` → csrf → ticket exchange
   - Module: `captcha_solver.solve_cloudflare_challenge` + hooks in `open_mobile_session`
   - Details: `captcha-manager/references/cloudflare-managed-challenge.md`
3. **Migrate profiles** — mobile `impersonate=chrome124` (drop chrome120)
4. **Detect CF** in client `_get` / open_mobile:
   - status 403 / `just a moment` / non-JSON HTML
5. **Retry ladder** if CF solve fails:
   - force chrome124 + Windows UA path
   - rotate sticky proxy + full re-login (up to ~3)
   - surface specific reason strings

## Real diagnosis (2026-07-21)
```
login_check code=0 ticket=True
bootstrap m.webnovel.com/id → 403 Just a moment, csrf=False
→ no csrf + login/info failed
→ Capsolver CF → cf_clearance → SUCCESS + PS readable
```

## Test checklist
- Cold fail emails after CF solver: csrf present, userInfo/PS OK
- Warm restore still ~0.2–0.7s without CF cost
- Capsolver balance checked before mass cold re-login
- Failed accounts remain in `accounts.txt`

## Related
- Device sticky: `device-isolation.md`
- PCM session: `profile-avatar-upload.md`
- Sync policy: `sync-and-failed-accounts.md`
- CF solver detail: `captcha-manager/references/cloudflare-managed-challenge.md`
