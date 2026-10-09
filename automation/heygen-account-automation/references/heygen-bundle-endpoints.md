# HeyGen Bundle Reverse-Engineering Notes (2026-08)

Source bundles (fetch with `curl` from `app.heygen.com`):
- `main-CZ3lbx7y.js` → loader → `main.app-A98W5vYf.js` (1.29MB, all app logic)
- `vendor-BNxEtVq_.js` (2.7MB, libs)
- `subscription-LOajjRch.js` (36KB, cancellation/retention coupon logic)
- auth bundle: `auth.heygen.com/assets/index-BitATHsw.js` (811KB)
- HAR from browser session is gold: shows real auth headers + endpoints.

## Auth headers (from HAR, mobile_web)

```
x-client-surface: mobile_web
x-guest-session-token: <base64 {"token":"...","token_type":"regular","created_at":...}>
x-language-override: id-ID
x-ver: 4.1.0
x-zid: <random 30-char id>
```

`x-guest-session-token` is a base64-encoded JSON object — NOT a JWT. The app
mints it via `GET /v1/pacific/account/free.get?zid=<rand>&sid=<ms>` →
`data.session_token`. Guest token expires in ~1h.

## Account / auth endpoints (app bundle + auth bundle)

| Endpoint | Purpose | Notes |
|---|---|---|
| `GET /v1/pacific/account/free.get` | guest session mint | returns session_token, features, user_name |
| `POST /v1/pacific/request_verification` | signup code send | FORM-encoded; reCAPTCHA v2 under `g-recaptcha-response` |
| `POST /v1/pacific/account/email.request` | reset-password code | 404 "Username not found" for unknown users — NOT signup |
| `POST /v1/pacific/account/email.verify` | verify code | `{email, code}` |
| `POST /v1/pacific/account/password.update` | set password | `{email, new_password, verified_code}` |
| `POST /v1/pacific/account/email.set` | bind email | 401 without auth |
| `POST /v1/pacific/login` | login | `{login_type, account, password, code, fingerprint, turnstile_token}` |
| `POST /v1/pacific/account/magic_link` | magic link send | alternative login |
| `POST /v1/pacific/account/magic_link/verify` | magic link consume | `{token, fingerprint, redirect_path}` |

## Coupon endpoints (retention, not promo)

```js
getSubscriptionCouponEligibility: n => e.get("/v2/subscription_coupon.eligible", n)
applySubscriptionCoupon:          n => e.post("/v2/subscription_coupon.apply", n)
```

From `subscription-LOajjRch.js`:
```js
B = {
  COUPON_40_OFF_2_MONTHS: "Cancellation_Coupon_40_OFF_2_MONTHS",
  MONTHS_FREE_2_MONTHS:   "Cancellation_Coupon_2_MONTHS_FREE",
}
// coupon_type enum: only CANCEL_SUBSCRIPTION accepted
// apply body: {coupon_name, coupon_type: "cancel_subscription", offer_status: "accept"}
```
These are shown to users cancelling a subscription (retention offers). The
enum rejects everything except `cancel_subscription`, so a generic promo code
cannot be validated through this endpoint.

## Promo code state

Redux account store has `promoCodeValid: false` default and only
`setCodeValid` writes it; no UI in the bundle ever sets it → there is no
manual "redeem code" page in `app.heygen.com`. `promoCode` string appears only
in unrelated video-translation payloads. Promo codes (e.g. `HP3FREE-TG29P`)
are presumed tied to signup/checkout via partner referrer.

## Omen partner pages (www.heygen.com/en-in/omen, /partners/omen)

- Next.js marketing pages, server-rendered RSC.
- "Claim Your Free Trial" form: `<input type="email" name="email">` + submit →
  fires only analytics (GTM, Reddit, Twitter, LinkedIn pixels). NO API call,
  NO code in response. `HP3FREE` string absent from both pages.
- The two pages are identical in content.

## reCAPTCHA / Turnstile keys

From app bundle `HEYGEN_*` constants:
- `HEYGEN_RECAPTCHA_KEY` = `6LdoGpsoAAAAAGphPKSXLJM7wl1eP7KM7Cmyk-ur` (v3)
- `HEYGEN_RECAPTCHA_V2_KEY` = `6LdkSxUpAAAAAIRFSKzvrcHD0YXgEWkjt6WU8xL0` (v2 — used by request_verification)
- `HEYGEN_RECAPTCHA_V2_VT_KEY` = `6LcWsp8qAAAAAEE7Y4pw3umtLaLIXuAHn6Kv11QO`
- `HEYGEN_TURNSTILE_SITE_KEY` = `0x4AAAAAAB59VlMqoRanWuKq` (login/signup)

## Error codes observed

- 40047 "Username not found" — email.request on unknown user (reset-password path)
- 400668 "Invalid recaptcha token" — wrong field name / bad captcha on request_verification
- 400669 "Please try again after 1 minute" — rate-limited after failed attempts
- 400112 "Unauthorized" — missing/invalid auth (needs guest token or login token)
- 400175 "coupon_type is invalid" — wrong enum value on coupon endpoint
