# 2captcha vs Capsolver for Cloudflare (Webnovel mobile)

Research + live tests 2026-07-21. Do not conflate docs titles with task types.

## What 2captcha actually ships
Docs: https://2captcha.com/api-docs/cloudflare-turnstile

Only **Turnstile** task types:
- `TurnstileTask` / `TurnstileTaskProxyless`

Two modes, both still Turnstile:
1. **Standalone widget** → needs `websiteKey` / `data-sitekey`
2. **Challenge page with Turnstile** → needs browser intercept of `turnstile.render`:
   - `sitekey`
   - `cData`
   - `chlPageData`
   - `action`
   - then inject token into page callback (Puppeteer/Selenium style)

2captcha does **not** expose Capsolver-style `AntiCloudflareTask` that returns `cf_clearance` from URL+proxy alone.

## Live API probes (our keys)
| createTask type | Result |
|---|---|
| `AntiCloudflareTask` | `ERROR_TASK_ABSENT` |
| `CloudflareChallengeTask` | `ERROR_TASK_ABSENT` |
| `CloudflareTask` | `ERROR_TASK_ABSENT` |
| `TurnstileTask` without sitekey | `ERROR_BAD_PARAMETERS` |
| legacy `method=turnstile` without sitekey | `ERROR_SITEKEY` |

## Live page probe: `https://m.webnovel.com/id`
Via sticky HTTP proxy + chrome124 (Windows + Android UA, 1st and 2nd hit):
```
status: 403
title: Just a moment...
cType: managed
turnstile / cf-turnstile / data-sitekey: NONE
cData / chlPageData / turnstile.js: NONE
```
Only CF managed opt fields (`cRay`, `cH`, `cUPMDTk`, `md`, …).

Conclusion: Webnovel mobile is **managed challenge without Turnstile params**.  
2captcha Turnstile API **cannot** be fed from curl_cffi HTML alone.

## Capsolver (proven replacement for this gate)
Task: `AntiCloudflareTask`  
Needs: `websiteURL` + proxy `ip:port:user:pass` + **Windows Chrome UA**  
Returns: `cookies.cf_clearance` (+ optional `userAgent`)  
Wire into `open_mobile_session` → re-GET → `_csrfToken` → ticket exchange.

Live recovery: cold accounts that were `no csrf` became PS-readable after Capsolver CF.

## Capmonster / Anti-Captcha as Capsolver backups? (createTask probes 2026-07-21)
Isolated curl probes (short timeouts; no bot restart):

| Provider | Task | Result | Meaning |
|---|---|---|---|
| **Capsolver** | `AntiCloudflareTask` | `errorId=0` + `taskId` | **accepted** (proven E2E earlier) |
| **Capmonster** | `AntiCloudflareTask` | `ERROR_TASK_ABSENT` | **no managed-CF clearancer** |
| **Capmonster** | `TurnstileTask` (dummy sitekey) | type accepted | Turnstile only — wrong gate |
| **Anti-Captcha** | balance + createTask | **connect timeout** from this VPS | **unreachable** ≠ invalid ≠ CF-capable |

**“Provider captcha yang support CF kayak Capsolver”:**
- Proven managed CF (`cf_clearance`) on Webnovel mobile: **Capsolver only**
- Capmonster is **not** a drop-in backup
- Anti-Captcha cannot be claimed as backup until API reachable + real CF task proven
- Keep Anti-Captcha / 2captcha / Capmonster for **reCAPTCHA `11401`**

Probe recipe (create-only, cheap) — use Windows Chrome UA + same sticky proxy string `ip:port:user:pass`.  
Do **not** poll dummy Turnstile tasks to “test CF”.

## When user asks "ini docs 2captcha cloudflare-turnstile?"
Answer: **related topic, wrong task type for our gate.**  
That page is Turnstile. Our gate is managed CF without sitekey. Capsolver remains the proven path.

## Optional heavier path (not default)
If a site **does** load Turnstile on challenge, 2captcha can work via full browser intercept (docs Selenium/Puppeteer).  
For Webnovel mobile as probed, Turnstile never appears in HTML → skip that path unless a new probe shows sitekey/cData.

## Cost note
CF managed solves drain Capsolver faster than reCAPTCHA `11401`. Keep 2captcha/anticaptcha for reCAPTCHA; reserve Capsolver balance for mobile CF.  
Live inventory often: Capsolver **1 funded key** + empty secondary; re-check before mass cold `/sync`.
