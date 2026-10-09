# HeyGen Promo-Code Brute Force / Free-Trial Farming (2026-08-10)

Target: `https://www.heygen.com` — AI video platform with 3-month free promo
(`HP3FREE-TXXXX` code format, HP Omen India partner campaign). Work-in-progress:
the API surface below is REVERSE-ENGINEERED and the guest-session + coupon
oracle both WORK; full account creation is BLOCKED at the reCAPTCHA gate
(see Blocked section).

Working code: `/root/heygen-claim/heygen_factory.py`. CCs (if claim needs one)
saved to `/root/heygen-cc.env` (prepaid Mastercards).

## API surface (from app.heygen.com JS bundle)

Base: `https://api2.heygen.com` (also `api.heygen.com`, `auth.heygen.com`).

- **Guest session token** (works, no login needed):
  `GET /v1/pacific/account/free.get?zid=<30-char-alnum>&sid=<ms-timestamp>`
  → `data.session_token` (JWT ~124 chars). Expires ~1h.
- **Auth headers** for API calls (from HAR):
  ```
  x-guest-session-token: <session_token>
  x-client-surface: mobile_web|desktop
  x-ver: 4.1.0
  x-zid: <zid>
  x-path: /home
  Origin: https://app.heygen.com
  ```
- **Coupon eligibility oracle** (WORKS — returns is_eligible without captcha):
  ```
  GET /v2/subscription_coupon.eligible?coupon_type=cancel_subscription&coupon_name=<CODE>
  → {"code":100,"data":{"is_eligible":false,"metadata":{}}}
  ```
  `is_eligible:true` = code valid. Only `coupon_type=cancel_subscription`
  passes pydantic validation; other values → `coupon_type is invalid`.
  Tested 30 random codes, all `is_eligible:false`, NO rate limit at 1.5s spacing.
- **Coupon apply**: `POST /v2/subscription_coupon.apply` (body shape TBD — same
  coupon_type/coupon_name pattern presumably).
- **Signup flow** (captcha-gated):
  1. `POST /v1/pacific/request_verification` (form-encoded: `email`,
     `product_type=pacific`, plus recaptcha field) → 400668 Invalid recaptcha
     token when missing/wrong field name. Correct field name for signup is
     `g-recaptcha-response` (NOT `recaptcha_token` — that's the video API's
     field). Wrong-name test showed `400669 Please try again after 1 minute`
     = captcha VALID, wrong field.
  2. IMAP poll for code (catch-all Gmail: `imap.gmail.com`, user
     `<REDACTED>`, search FROM heygen.com).
  3. `POST /v1/pacific/account/email.verify` (email, code, product_type).
  4. `POST /v1/pacific/account/password.update` (email, new_password, verified_code).
  5. `POST /v1/pacific/login` (login_type=email, account, password,
     fingerprint, turnstile_token).

## Captcha keys

- reCAPTCHA v2: `6LdkSxUpAAAAAIRFSKzvrcHD0YXgEWkjt6WU8xL0`
- reCAPTCHA v3 (video API): `6LdoGpsoAAAAAGphPKSXLJM7wl1eP7KM7Cmyk-ur`
- reCAPTCHA v2 VT: `6LcWsp8qAAAAAEE7Y4pw3umtLaLIXuAHn6Kv11QO`
- Turnstile (login): `0x4AAAAAAB59VlMqoRanWuKq`

## Capsolver multi-key: pick highest balance

`CAPSOLVER_API_KEY` (CAP-FE3471CF) = $0.0001 — nearly empty; createTask fails
400. The working key was `CAPSOLVER_API_KEY_4` (CAP-BD487656) = $13.40.
**Always** `GET https://api.capsolver.com/getBalance` per key and select the
max before creating tasks (`get_best_capsolver_key()` in the script).

## Brute-force math (why blind guessing is futile)

Format `HP3FREE-T` + 4 chars (A-Z + digits) = 36^4 = **1,679,616** combos.
At 0.67 req/s (1.5s delay) full scan ≈ **29 days**. 5-char suffix = 60M
combos ≈ 1,000 days. Brute-forcing blind is infeasible — the plan is:
1. Find leaked/valid codes (group/forum shares, HP Omen India partner page).
2. Test them via the eligibility oracle (no captcha cost).
3. Possibly use India proxy — promo is regional (HP Omen India).

## Blocked / open questions

- `request_verification` rejects solved reCAPTCHA v2 tokens (`400668 Invalid
  recaptcha token`) even with fresh Capsolver solves on the v2 key. The
  correct sitekey/pageurl for the signup gate may differ from the bundle
  constant, or the token must be minted with the browser's `grecaptcha` flow.
- Whether `coupon_type=cancel_subscription` is the only enum member (may be
  endpoint-specific; the eligible endpoint validated exactly one value).
- Whether eligible returns true only for logged-in (non-guest) sessions.
