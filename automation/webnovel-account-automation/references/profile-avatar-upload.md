# Webnovel profile avatar upload (proven)

## Goal
After register + email confirm, set a **unique** profile photo per account via mobile PCM API.

## Endpoints
| Step | Method | URL |
|------|--------|-----|
| Bootstrap CSRF | GET | `https://m.webnovel.com/id` |
| Session exchange | GET | `https://m.webnovel.com/go/pcm/login/login?_csrfToken=&ticket=&guid=` |
| Session proof | GET | `https://m.webnovel.com/go/pcm/user/userInfoAjax?_csrfToken=` |
| Avatar upload | POST | `https://m.webnovel.com/go/pcm/user/setUserAvatar?_csrfToken=` multipart `image` |

Confirm/login also set cookies:
- `Set-Cookie: uid=<userid>; domain=webnovel.com`
- `Set-Cookie: ukey=<uKey>; domain=webnovel.com`

Confirm JSON payload fields: `ticket`, `userId`, `uKey` (capital K).

## curl_cffi notes
- Prefer `impersonate="chrome124"` for `m.webnovel.com` (chrome131 often CF-challenges).
- Upload with `CurlMime` + `multipart=`:
```python
from curl_cffi import CurlMime
mp = CurlMime()
mp.addpart(name="image", content_type="image/jpeg", filename="a.jpg", data=img_bytes)
s.post(url, multipart=mp, headers={"Origin": "https://m.webnovel.com", "Referer": "https://m.webnovel.com/id/settings"})
```
- Do **not** use `files=` — curl_cffi rejects it.

## login/login contract (from mobile callback JS)
```js
// pages/login/callback-*.js
v().read({ url: "/go/pcm/login/login", data: { ticket, guid } })
// read() merges {_csrfToken from cookie} and GET-stringifies query
```
Success:
```json
{"code":0,"data":{"UserId":...,"Name":"...","LoginType":2005},"msg":"Success"}
```
Without csrf → `400 {}`.

## What does NOT work
- `uid`/`ukey` cookies alone + `www.webnovel.com/?ticket=` → `user session invalidate` / Result -401 on PCM APIs
- `login/login` without `_csrfToken`
- HAR-only mobile path without chrome124 (CF "Just a moment")
- Treating register/confirm green as profile-ready without userInfo proof

## Avatar uniqueness (new creates — stylized only)
User preference: **not** real-person stock faces.

1. Local unused `avatars/pool_*.{png,jpg}` (preferred):
   - `pool_fun_*` — colorful social/emoji 2D
   - `pool_animal_*` — animal avatars (robohash set4 class)
   - `pool_gamebot_*` — robot/game
   - `pool_pixel_*` — pixel-art game
   - `pool_cyber_*` — neon/cyberpunk-ish shapes/thumbs
2. Remote stylized fallback only: Dicebear fun-emoji/bottts/pixel-art or robohash animals
3. **Do not** use `randomuser.me` portraits for new accounts
4. Existing accounts: leave already-uploaded `used_*` alone unless user asks to re-avatar

Track keys in `avatars_used.txt`. Pick unused `pool_*` first; rotate start index by email hash so creates don't always take the same first file.

## Ledger format
```
email:password:userid:/path/to/avatar.jpg
```

## Canonical implementation
`/root/webnovel-autoreg/signup.py` — `open_mobile_session`, `upload_avatar`, `fetch_unique_avatar`.
