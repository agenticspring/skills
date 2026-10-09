# IP Block Diagnostic — the REAL Cloudflare signup blocker

## Symptom
`bluk-cf` runs, browser launches, form fills, `✅ Turnstile solved` prints — but signup
never leaves `/sign-up`. Two different error strings appeared across runs:

1. Early runs (before widget-click tweak): `Signup failed: Redirect failed: https://dash.cloudflare.com/sign-up`
2. With full body dump, the actual page text was:
   ```
   Let us know you are human
   Sign up
   You are unable to sign up at this time        <-- THIS is the real blocker
   Already have an account? Log in
   ```
   (In other runs the same failure rendered as "Please complete the CAPTCHA and try again."
   — a generic CF error that masks the underlying abuse block.)

## Root cause
Cloudflare hard-blocks account signup from **datacenter / VPS IPs**. The test box
(empero, 82.39.206.183) has no residential egress. CF's anti-abuse system refuses the
signup outright — it is NOT a Turnstile/token-binding failure. The "complete the CAPTCHA"
string is a catch-all error CF shows on rejected signups regardless of actual cause.

## Proof the Turnstile path was a red herring
After `verify_cf()` the expected `input[name="cf-turnstile-response"]` is absent from the
parent DOM (exists:false, len:0). That is NORMAL for invisible/managed Turnstile (token
lives in shadow DOM / iframe). We wasted ~5 runs trying to bind it:
- clicking the widget after verify_cf()  -> still rejected
- headless=True                          -> verify_cf() stops solving entirely
- JS-inject value='1' + requestSubmit()  -> server-side rejected
- verify_cf() + wait 15s + submit        -> rejected (IP block, not captcha)

None addressed the IP block.

## Fix (mandatory)
Use a residential proxy. `bluk-cf` config already supports it:
```json
"proxy": "http://user:pass@host:port"
```
or `--proxy http://user:pass@host:port`. DataImpulse-style residential rotation is what
the original architecture diagram used. Re-test ONLY after confirming the browser's
egress IP changed (e.g. fetch https://api.ipify.org inside the page or check proxy logs).

## Debug discipline learned (do this next time)
On ANY signup failure, dump `document.body.innerText` (and the widget HOST/IFRAME html)
BEFORE touching Turnstile logic. If body contains "unable to sign up at this time" ->
stop and fix the proxy. Do not iterate on captcha code.

Also: pass `--retry 1` while debugging. Default `max_retry=3` with a 30s gap between
attempts re-fires signup from the same blocked IP and accelerates the reputation block.
