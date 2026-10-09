# Webnovel device trust (11318)

## When it appears
`POST/GET ptlogin.webnovel.com/login/checkcode` returns:
```json
{"code":11318,"msg":"Untrusted Device","data":{"encry":"...","sessionKey":"...","nextAction":3,...}}
```
Password is already correct. Browser shows "special code" email gate.

## Frontend path (login_v6.js)
1. `checkCodeCallback` on 11318 calls `sendTrustEmail` with `encry`
2. `trustEmailCallback` on success shows step2 OTP UI
3. User submits via `checkTrustCode()` → `login/checkTrust` with:
   - `encry`
   - `trustcode` (from input `.trustcode`)
   - `sessionKey`
   - `method=LoginV1.checkTrustCodeCallback`

## Email shape
- Subjects observed: `Webnovel Support`, `Dukungan Webnovel`
- Body contains: `Webnovel Guard code you need to login to account 「 {local} 」: {CODE}`
- Code: **alphanumeric 4–12** (usually 6), case-sensitive as mailed
- Do **not** scrape bare 4-digit years (`2019` appears in footer ©)

## IMAP extraction rules
- Require target address in To/Delivered-To/body (catch-all safe)
- Prefer newest Support/Guard mails for that address after `sendTrustEmail`
- Regex priority:
  1. `guard\s*code[^:]*:\s*([A-Za-z0-9]{4,12})`
  2. `code you need to login[^:]*:\s*([A-Za-z0-9]{4,12})`
  3. `」\s*:\s*([A-Za-z0-9]{4,12})`
- Reject junk tokens: webnovel, account, login, years, local-part alone

## Success / failure codes
| step | code | meaning |
|------|------|---------|
| sendTrustEmail | 0 | OTP mailed |
| checkTrust | 0 | device trusted; jump returnurl |
| checkTrust | 11319 | wrong/expired OTP |
| checkcode later | 0 | full login |
| checkcode | 11401 + google | password OK but captcha risk (separate) |

## Implementation notes
- Keep same cookie/session jar across checkcode → sendTrustEmail → checkTrust
- Prefer encry from sendTrustEmail response if returned, else checkcode encry
- OTP is single-use; do not reuse across proxy retries
- Canonical automation: `/root/webnovel-autoreg/signup.py` `login_check(complete_trust=True)`
