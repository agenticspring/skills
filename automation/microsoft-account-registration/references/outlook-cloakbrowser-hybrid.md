# Outlook CloakBrowser hybrid architecture

Source: user zip `outlook-creator-sanitized` extracted under `/tmp/outlook-creator-sanitized/outlook-creator/` (2026-07-25).

## Files
- `outlook_creator.py` — hybrid Playwright CDP + curl_cffi CreateAccount
- `register.py` — simpler CloakBrowser form-fill loop (stops on captcha/phone/blocked)
- `.env.example` — residential proxy: `PROXY_LOGIN`, `PROXY_PASSWORD`, `PROXY_HOST`, `PROXY_PORT`

## Core rule (proven in code comments + our API probes)
**`risk/verify` must run in browser context** on `login.microsoftonline.com` (same-origin XHR).  
Calling `risk/verify` via curl_cffi / mismatched TLS tends to **`403 riskBlock` / AADSTS7005106**.

curl_cffi is for:
- `CheckAvailableSigninNames`
- `CreateAccount`

Not for HUMAN clearance.

## Flow (from zip docstring / implementation)
1. Connect Playwright to **CloakBrowser** profile via CDP (`…/api/profiles/{id}/cdp`).
2. Optionally set residential proxy on the profile (session id in username) and relaunch if changed.
3. Load `signup.live.com/signup`; intercept **`risk/initialize`** → `continuationToken`.
4. Poll until **both** CT and **`_px3`** exist (CT can land ~1.5s; `_px3` often later ~5s+). Early exit on CT-only → “px3 MISSING”.
5. Browser **`risk/verify` #1** → HumanCaptcha challenge payload.
6. Load `iframe.hsprotect.net` challenge; let **native PX/HUMAN** in anti-detect browser produce new `_px3` (not synthetic hold-only).
7. Browser **`risk/verify` #2** with new `_px3` + `challengeSolution` → final CT.
8. curl_cffi **CreateAccount** with canary/uaid/cookies.

## Constants useful elsewhere
- Risk base: `https://login.microsoftonline.com/9188040d-6c67-4c5b-b112-36a304b66dad/api/v1.0/risk/{initialize,verify}`
- Create: `https://signup.live.com/API/CreateAccount`
- Check: `https://signup.live.com/API/CheckAvailableSigninNames`
- HPGID `200225`, SCID `100118`, UIFLVR `1001`
- HUMAN app id observed live: `PXzC5j78di`

## VPS gap
As of inventory check: **no CloakBrowser binary/docker**, no DataImpulse residential env keys. Only Webshare/DC pools + Playwright Chromium. Adopting this zip means install CloakBrowser Manager + profile + residential proxy before promising E2E.

## Relation to `/root/outlook-autoreg`
Local toolkit already has form + hold + PX capture + CreateAccount API. Next adoption step is replace “Playwright stealth hold” with **CDP anti-detect browser** and implement **browser-side risk/verify #1/#2** exactly as this zip — not more Capsolver FunCaptcha.