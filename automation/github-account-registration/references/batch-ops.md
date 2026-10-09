# GitHub autoreg batch ops (updated 2026-07-21)

## Screen
```bash
/usr/bin/screen -dmS github-autoreg /bin/bash -lc \
  'cd /root/github-autoreg && .venv/bin/python -u batch_create.py 10 --delay 25 2>&1 | tee -a logs/batch_screen.log'
pgrep -af 'batch_create.py'   # always verify after start (approval gates can cut start)
screen -r github-autoreg
tail -f /root/github-autoreg/logs/batch_screen.log
# stop
screen -S github-autoreg -X quit
```

## Pipeline per account (no-captcha-first)
1. Pick Webshare proxy until `GET /signup` returns auth token + octocaptcha
2. Optional username check: `/signup_check_new/username?suggest_usernames=true`
3. **Attempts 1–2:** `POST /signup?social=false` with **empty `octocaptcha-token`** (suppressed path)
4. **Attempt 3 only:** paid DataDome (2captcha max 2 keys / ~50s; Capsolver short)
5. **Fail-fast** unless landed on email verify (`account_verifications` / verify your email / launch code)
6. IMAP from **`/root/cf-tuyul/.env`** → `🚀 Your GitHub launch code`
7. Open `/account_verifications/confirm/<uuid>/<code>`
8. Login → session cookies → classic PAT:
   - form-driven payload; force `oauth_access[default_expires_at]=none`
   - include empty `oauth_access[custom_expires_at]` if present
   - **scopes optional** — empty scopes proven OK; forcing scopes can 422
9. Append `ghp_` to `tokens.txt` + `/root/api-key-leak/data/tokens.txt`

## Hang: “solving DataDome…” for many minutes
**Cause A:** Capsolver-first multi-type ~180s timeouts.  
**Cause B:** 2captcha thrash on **suppressed** OctoCaptcha generic iframe → wait → UNSOLVABLE × many keys.  
**Fix:** no-captcha-first; if paid: max 2 keys / ~50s; permanent skip zero/IP-blocked keys.

## Hang: submit 403 then IMAP wait 3 minutes
**Cause:** treating any POST as success and always polling mail.  
**Fix:** only IMAP if verify page reached; on 403/429 rotate proxy, no mail poll.

## PAT create (proven payload)
```
authenticity_token
oauth_access[description] = note
oauth_access[default_expires_at] = none
oauth_access[custom_expires_at] = ""   # often required empty field from form
# scopes: omit first (empty OK for public search)
```
- Prefer rebuild from form hidden inputs and override expires to `none`
- 422 “Oh no” often = bad form shape / missing custom field — not always “token API dead”
- Validate: `/user` + `/rate_limit`; new accounts often **search 10 / core 60**

## PAT permission reality
| Item | Needed for api-key-leak public scrape? |
|---|---|
| classic `ghp_` | yes |
| no expiration (`none`) | yes (user requested) |
| empty scopes | OK for public search |
| scopes public_repo/read:user/user:email | optional; may 422 — try empty first |
| high search/core limits | **not guaranteed** on brand-new accounts (~10/60 common) |

## Isolation
- Do not restart `webnovel-tg` or kill `api-key-leak` while iterating github batch
- Keep Webnovel proxies out of github mass signup (use Webshare-class)
- User “bot gua matikan” → confirm no `batch_create` / no `github-autoreg` screen before rework
