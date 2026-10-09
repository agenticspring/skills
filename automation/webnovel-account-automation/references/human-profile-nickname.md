# Human email + nickname (Webnovel create polish)

**Date:** 2026-07-21  
**Code:** `/root/webnovel-autoreg/signup.py` — `gen_identity`, `gen_human_nickname`, `set_nickname`, `set_nickname_with_retries`  
**Bot parser:** `/root/webnovel-tg-bot/wn/client.py` — `Account.nickname` (5th accounts field)

## Problem
Fresh Webnovel accounts default to:
```text
nickName = userName = penName = Daoist + random
e.g. Daoist4Qd6gI
```
With stylized avatars only, **Daoist*** still fingerprints farm/create bots.

User ask: make **email + username** look like real humans on `/create`.

## Email patterns (good)
```text
leonardo.kuiper328@<REDACTED>
oliviajensen992@<REDACTED>
john_baker@<REDACTED>
ryan_harris131@<REDACTED>
```
Avoid: `gh.xxx`, pure sequential robots, obvious bot prefixes.

## Nickname rules (product)
From settings JS errors:
- Valid: **3–18** chars, **letters/numbers/underscore only**
- Invalid short/long → API `-107003`
- Spaces/symbols → `-107004`
Prefer natural 6–14 chars; avoid every account starting with same soft prefix (`Bookish`/`Cozy` spam).

Examples that pass checkUserName:
```text
LunaReads, Kai_NightOwl, MiraReads35, Emma_Arc, Ava_Books
```

## APIs (mobile PCM, same session as avatar)
Warm: `GET https://m.webnovel.com/id/settings` for csrf.

### Check availability
```http
GET /go/pcm/user/checkUserName?_csrfToken=...&userName=LunaReads
→ {"code":0,"msg":"Success"}  # available
```

### Set name
```http
POST /go/pcm/user/setUserSettings?_csrfToken=...
Content-Type: application/x-www-form-urlencoded

name=LunaReads&gender=0&country=GO&sign=
→ {"code":0,"msg":"Success"}
```

### Verify
```http
GET /go/pcm/user/userInfoAjax?_csrfToken=...
→ profile.nickName / userName / penName updated
```

Also: `GET /go/pcm/user/getUserSettings` shows `settings.name` / `thirdPartyName` (often `Daoist` pre-rename).

**Not found (404):** `setUserInfo`, `setNickName`, `updateNickName` as bare paths — use **setUserSettings**.

## Create pipeline order
```text
confirm → open_mobile_session
  → setUserAvatar
  → checkUserName + setUserSettings (retry human nicks)
  → login_check
  → save email:pass:userid:avatar:nickname
```

## Live proof
- Session account `leon.andersen681@…`: `Daoist2Snvy8` → **`BookishLeon`** via setUserSettings.
- Form/json variants both returned code=0; form is canonical.

## Ops notes
- `/create` does **not** need TG bot restart after signup.py edit (child process).
- Optional: batch rename remaining `Daoist*` using sticky sessions + same API.
- Capsolver multi-key: loader reads all `CAPSOLVER_API_KEY*` from bot `.env` + hermes; inject new keys into **both** if create/CF must use them.
