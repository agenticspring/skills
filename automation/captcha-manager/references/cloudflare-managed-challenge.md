# Cloudflare managed challenge (Webnovel mobile)

## Fingerprint
- URL: `https://m.webnovel.com/...`
- Status: **403**
- HTML title: `Just a moment...`
- Markers: `cType: 'managed'`, `cRay`, `challenge-platform`, `__cf_chl_tk`
- **No** `data-sitekey` / Turnstile widget (not Turnstile-only)
- Cookies before solve: often only `__cf_bm`

## Not the same as reCAPTCHA
| | reCAPTCHA `11401` | CF managed |
|--|-------------------|------------|
| Domain | passport/ptlogin | m.webnovel.com |
| Solver | `solve_recaptcha_v2` | `solve_cloudflare_challenge` |
| Token field | `validateCode` / g-recaptcha-response | `cf_clearance` cookie |
| When | login/register risk | mobile bootstrap / PCM |

## Capsolver task (proven)
```json
{
  "type": "AntiCloudflareTask",
  "websiteURL": "https://m.webnovel.com/id",
  "proxy": "ip:port:user:pass",
  "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}
```
Solution typically: `{ "cookies": { "cf_clearance": "..." }, "token": "...", "userAgent": "..." }`

## Session apply
1. Set session UA to Windows Chrome (or solver UA)
2. `cookies.set("cf_clearance", value, domain=".webnovel.com")`
3. Re-GET `/id` → expect `_csrfToken`
4. Continue `login/login?ticket&guid` + `userInfoAjax`

## Live proof (2026-07-21)
- Fail accounts `jun.kato209`, `elizabeth.clark80`: passport OK, mobile CF → after Capsolver CF: `csrf=True`, PS balance readable
- Capsolver balance drains on CF tasks; keep reCAPTCHA keys separate for 11401

## Module
`/root/webnovel-autoreg/captcha_solver.py` — `solve_cloudflare_challenge`, `apply_cf_solution_to_session`
`/root/webnovel-autoreg/signup.py` — `open_mobile_session` CF hooks
