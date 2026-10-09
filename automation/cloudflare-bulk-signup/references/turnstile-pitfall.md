# Turnstile "solved but not bound" - diagnostic transcript

## Symptom
- signup_flow.py runs `await verify_cf(page)` -> prints `Turnstile solved: OK...`
- Submit clicked, but CF stays on /sign-up and body shows:
  `Please complete the CAPTCHA and try again.`
- Body dump (signup_fail.txt) shows widget still at "Let us know you are human".

## Diagnostic
Right after verify_cf(), evaluated:
```js
(() => { const r=document.querySelector('input[name="cf-turnstile-response"]');
         return {exists:!!r, len:r?(r.value||'').length:0}; })()
```
Result: `{exists:false, len:0}`.
=> The response token is NOT present in the parent form DOM. CF's signup uses
invisible/managed Turnstile; the response field lives in shadow DOM / the
challenges.cloudflare.com iframe, not as a visible parent input. So solving the
challenge does not satisfy the form's submit-validation gate.

## What was tried (ALL FAILED to bind the token)
1. Click the Turnstile iframe / checkbox element after verify_cf()
   (page.find('iframe[src*="challenges.cloudflare.com"]').click(), plus fallbacks
   #cf-turnstile, .cf-turnstile, coordinate click). Still "complete CAPTCHA".
2. headless=True -> verify_cf() never prints "solved"; submit fails immediately.
   Use headless=False + Xvfb.
3. verify_cf() + await asyncio.sleep(15) + submit. Still rejected.

## Open candidates (NOT yet validated - leave here for next session)
- (A) Click the visible widget BEFORE verify_cf() so the success callback fires
  into the parent form, then let verify_cf() confirm.
- (B) After solve, submit via JS (document.querySelector('form').requestSubmit()
  or dispatch submit) and retry once if CF returns the CAPTCHA error.
- (C) Abandon verify_cf(); use xdotool real X11 click on the widget's Xvfb
  coordinates (the original architecture diagram's approach). Requires one-time
  coord calibration: open signup in Xvfb, locate widget, record x/y.
- (D) headless=True with explicit --headless=new for snap chromium (different
  headless stack than default nodriver headless).

## Why this matters
The token-solve step is NOT the blocker - token binding to the form is. Any future
attempt should re-run the exists:false/len:0 diagnostic to confirm whether a
candidate fix actually bound the token before declaring victory.
