# GitHub signup spike notes (2026-07-21)

## Page fingerprint
- URLs: `/signup`, `/join` → same redesign form
- Form action: `POST /signup?social=false`
- `authenticity_token` present (length ~88)
- Hidden/required: `octocaptcha-token` with `data-datadome-captcha="true"`
- iframe: `https://octocaptcha.com/datadome?origin_page=github_signup_redesign`
- No `data-sitekey`, no Turnstile widget, no classic reCAPTCHA on first paint
- Phone field **not** on first page

## iframe probe
- `octocaptcha.com` HTML can mention Arkose/FunCaptcha assets
- Live datadome iframe probe: **datadome=true**, arkose/funcaptcha false on that response
- Treat primary gate as **DataDome via OctoCaptcha**, not Webnovel-style CF managed

## Proxy probe (signup form open)
### Webnovel pool sample (8)
- Most **403**, no auth token
- Only 2/8 returned 200 + authenticity_token + octocaptcha

### Webshare 10 (user list)
- **7/10 OK** (200 + auth + octocaptcha + datadome iframe)
- Failures: 3× 403
- Better default pool for github-autoreg

### Direct VPS
- 200 + full form (~298KB HTML)

## Captcha solve proof
- Proxy: Webshare OK host
- Solver: **2captcha `method=datadome`**
- Result: token `datadome=…` (~186 chars), ~22s
- Capsolver DataDome task name variants may error by account/plan — try but do not assume

## Real submit proof (1 account)
1. Open form on Webshare proxy  
2. Solve DataDome  
3. POST signup  
4. Landed `https://github.com/account_verifications`  
5. Reason: **email_verify_required** (title: Please verify your email address)  
6. Phone not hit in that attempt  
7. IMAP auto-verify blocked when `IMAP_PASS` unset in env chain  

Pending example shape (do not restate secrets):
- email `gh.*@<REDACTED>`, status `pending_email` in `accounts.txt`

## Practical checklist before next real submit
- [ ] Proxy opens form (not 403)
- [ ] DataDome token obtained
- [ ] `IMAP_PASS` present for catch-all domain
- [ ] SKIP_PHONE policy clear
- [ ] Log to `logs/attempts.jsonl`
