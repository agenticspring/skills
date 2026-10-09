# Register risk captcha `11401` + verify fail `11306`

## Browser truth (`login_v6.js`)
- `registerCallback`: on `code==11401` → `handleNextAction(data.data.nextAction)`.
- `handleNextAction(1)` sets `nextAction=1` and renders Google reCAPTCHA (`#google-code-html`).
- Resubmit register with `validateCode = grecaptcha response` and `nextAction=1`.

## Sitekey (static in JS, re-check if fails)
```
6Leb2SYUAAAAAEemO0h4Wj_casf9j5HM6RfNg7bG
```
Page URL:
```
https://passport.webnovel.com/register.html?appid=900&areaid=1&target=iframe&returnurl=https%3A%2F%2Fwww.webnovel.com%2F
```

## Codes
| Code | Meaning | Action |
|------|---------|--------|
| `11401` | Risk reCAPTCHA (`nextAction=1`) | Solve + resubmit; **never** label Banned |
| `11306` | Captcha verification failed | Fresh **proxy-bound** token; usually IP mismatch |
| `-11051/-11055/-11053` | Harder ban-ish | Rotate sticky proxy |

## CRITICAL: same proxy as register (11306)
Webnovel validates captcha against the client IP of `doregister`.

- **Wrong:** solve proxyless (solver IP A), submit via account proxy B → often `11306 Verification failed`
- **Right:** solve with **proxy-bound** task using the **exact same HTTP proxy** as register

Provider task types when proxy present:
- Anti-captcha: `RecaptchaV2Task` + proxy fields (not only Proxyless)
- Capsolver: `ReCaptchaV2Task` + proxy fields
- 2captcha: `userrecaptcha` + `proxy` + `proxytype=HTTP`
- Proxyless is fallback only

## Bot implementation
- Module: `/root/webnovel-autoreg/captcha_solver.py`
- `register()` first call without token; on `11401` + `solve_captcha=True`:
  1. Solve reCAPTCHA v2 **proxy-bound** (prefer anticaptcha-proxy)
  2. Second `doregister` with `validateCode=token`, `nextAction=1`
  3. On `11306`, retry once with a fresh proxy-bound token
- Log labels: `🔐 Risk captcha` — never `Banned (11401)`.
- True ban set: `-11051, -11055, -11053` (proxy rotate via `rotate_profile_proxy`).

## Providers / keys
Order for Webnovel register: **anticaptcha-proxy → capsolver-proxy → 2captcha-proxy → proxyless fallback**.  
Rank keys by live balance into project `.env` (bot or autoreg). Primary 2captcha may be drained — try next key/provider.  
TG bot `/create` must inject ranked captcha keys from bot `.env` into child env.

## Live proof
- 2026-07-20: `11401` → token → register `0` (initial proxyless path sometimes worked).
- 2026-07-20 later: mass create got `11306` after token; fixed by **proxy-bound** solve (`provider=anticaptcha-proxy`) → full E2E:
  `register0 → confirm → avatar → login0` (e.g. `ella.rodriguez913@<REDACTED>`).

## Pitfalls
- Token issued ≠ accepted: length-valid tokens can still 11306 if IP mismatches.
- Do **not** burn all proxies on 11401 as if IP-banned; captcha first.
- Sticky rebind via `rotate_profile_proxy` only for real bans / residual risk.
- Mass create + hot proxies → more 11401; budget captcha cost + slowdown.
