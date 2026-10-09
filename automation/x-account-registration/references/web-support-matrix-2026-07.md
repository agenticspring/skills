# X web create-account support matrix (2026-07-21 recheck)

Live recheck: direct VPS + 4 Webshare proxies. Emails per network: `@<REDACTED>`, `@gmail.com`, `@outlook.com`.

## Methods

| Method | Web supported? | Notes |
|--------|----------------|-------|
| Phone SMS | Yes | Primary: Continue with phone / `begin_signup_phone` |
| Google SSO | Yes | Continue with Google / `begin_signup_sso` |
| Apple SSO | Yes | Continue with Apple |
| Email OTP full in browser | **No** (tested) | Unknown email → app install + phone CTA |
| Custom-domain email-only | **No full web complete** | Same pivot as Gmail/Outlook — **not a domain ban** |

## Evidence summary

- `POST .../begin_signup_email` → **15/15** `APP_PIVOT+PHONE/not_registered`
- Classic `POST /1.1/onboarding/task.json` Signup → **366 Missing data** (direct + proxy)
- Landing: phone / Google / Apple primary; email field is login/detect style

## Product strings (begin_signup_email)

- `This email or username is not registered yet`
- `download_app_pivot` / `Get the app to finish signing up`
- `Create an account on the app` + `app_install` redirect
- `Sign up with Phone` → `begin_signup_phone`

## Policy impact

With `SKIP_PHONE=1`, **web mass email autoreg is not product-feasible**.  
Do not burn FunCaptcha $ on web email path until a real browser/app HAR shows email-OTP complete.

## Artifacts

- Vault: `Research/X Web Signup Support Matrix.md`
- Dumps: `/root/x-autoreg/data/web_recheck_results.json`, `recheck_*.bin`
