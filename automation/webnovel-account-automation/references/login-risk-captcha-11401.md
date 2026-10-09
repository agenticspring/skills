# Login risk captcha 11401 (sync / PS cold path)

## Symptom
`/sync` or force session on accounts **without** `sessions/<email>.json`:
```
login failed code=11401 msg=google code
```
or after older soft-accept:
```
mobile session failed / no csrf
```
(because no ticket was issued).

## Cause
Webnovel `checkcode` risk gate — same class as register `11401`, different pageurl.

## Fix (implemented in `signup.login_check`, 2026-07-21)
1. Detect `code == 11401`
2. Solve reCAPTCHA v2:
   - sitekey: `6Leb2SYUAAAAAEemO0h4Wj_casf9j5HM6RfNg7bG`
   - pageurl: `https://passport.webnovel.com/emaillogin.html?appid=900&areaid=1&target=iframe&returnurl=...`
   - **proxy-bound** to sticky account proxy
3. Resubmit `checkcode` with `nextAction=1` + `validateCode=<token>` (+ sessionKey if present)
4. Outcomes:
   - `0` → ticket/userid → open mobile session → save cookies
   - `11318` → device trust OTP flow
   - `11306` / still `11401` → one more proxy-bound solve
   - `-51037 Internet error` → retry same token once after short sleep

## Do not
- Return login `11401` as soft success without ticket (breaks PCM)
- Use proxyless token with proxied login (same `11306` class as register)
- Confuse with hard ban codes

## Related
- Register twin: `references/register-risk-captcha-11401.md`
- Trust OTP: `webnovel-signup` device-trust section + Spam/11319 multi-try
