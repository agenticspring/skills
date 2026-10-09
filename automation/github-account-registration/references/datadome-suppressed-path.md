# GitHub OctoCaptcha: suppressed path vs paid DataDome

## Discovery (2026-07-21 investigation)
On several Webshare proxies, the OctoCaptcha iframe is **not** a full DataDome slider challenge.

Iframe body signals:
```text
window.ddjskey = "2CF892E038EE5D8217D27787467ED2"
postMessage({ event: 'captcha-suppressed' })
postMessage({ event: 'captcha-complete', sessionToken: 'datadome-suppressed' })
```

Also loads `https://js.datadome.co/tags.js` only — often **no** `geo.captcha-delivery.com` challenge URL.

## Preferred flow
1. Open `https://github.com/signup` on form-OK proxy (200 + authenticity_token).
2. Read iframe `https://octocaptcha.com/datadome?origin_page=github_signup_redesign`.
3. If suppressed markers present → **do not** call 2captcha/Capsolver.
4. `POST /signup?social=false` with empty `octocaptcha-token` (and normal email/user/password/authenticity_token).
5. Proven success signal: `https://github.com/account_verifications` + title “Please verify your email address”.
6. Cookie `datadome=…` may appear after successful POST even without paid solve.

## Why paid solve thrash happens
Batch sent generic:
```text
captcha_url = https://octocaptcha.com/datadome?origin_page=github_signup_redesign
method = datadome
```
to 2captcha for every account.

Observed outcomes:
- long `CAPCHA_NOT_READY` polls (50–90s)
- then `ERROR_CAPTCHA_UNSOLVABLE` on task ids (e.g. 83315649989, 83315654594, …)
- `ERROR_IP_NOT_ALLOWED` on some keys (VPS IP not whitelisted)
- `ERROR_ZERO_BALANCE` on drained keys

This looks like “stuck waiting” in logs but is usually **unsolvable task + key rotation**, not a frozen Python process.

## Fail-fast solver policy
- Max **2** 2captcha keys per attempt
- ~**50s** poll per key
- Permanent skip: zero/neg balance, `IP_NOT_ALLOWED`, missing keys → `logs/2captcha_skip_keys.txt`
- Capsolver DataDome only as last short try; requires funded `CAP-…` + **Windows Chrome UA** (mobile UA → `unsupported userAgent`)
- Never IMAP-wait after submit 403 / non-verify response

## Proxy note
Webshare list is mixed. Re-probe each run:
- form OK sample can be ~6/10
- 403 sample ~4/10
Do not burn captcha balance on proxies that cannot open the form.

## Relation to earlier paid E2E success
One earlier account succeeded with 2captcha-datadome (~22s) then email confirm. That path still exists when a **real** challenge is required. It is not the default for suppressed sessions — try no-captcha first.