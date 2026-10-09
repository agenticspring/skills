# TokenHub browserless register notes (2026-07-21)

## Why browserless
User: same class as Webnovel/GitHub — no browser if possible. Playwright path exists (`register_claim.py`) but product goal is HTTP CLI.

## Proven prechecks
```text
POST /en/account/register/ajax?action=checkAccountExistReg
  data: email=<addr>
  → {"code":0,"data":{"exist":false}}

POST /en/account/register/ajax?action=checkBlackResource
  → {"code":0,"data":{"hit":false}}
```
Warm `GET /account/register` first for cookies (`qcmainCSRFToken`, language).

## Captcha
- Solve **before** send mail
- Prefer 2captcha `TencentTask` + Webshare (`proxy.txt`)
- appId `188959458` only
- Example success: `provider=2captcha-proxy`, `randstr=@i7r`, ticket prefix `t03tserver…`

## sendMailCode status
CLI tries variants of `sendMailCodeV2` / `sendMailCode` with:
```text
email/mail + captchaAppId/appId + ticket + randstr
(+ optional password/countryCode/accountType/birth)
```

Live outcome after valid captcha:
```text
sendMailCodeV2 → HTTP 200 {"code":51,"msg":"","data":{"__TEMP":1}}
```
→ **no IMAP OTP** within 150s.

Interpretation:
- Not a network miss
- Not “solver never worked” (captcha did solve)
- Payload/session still incomplete **or** ticket not accepted for that cookie jar

Next reverse targets (narrow, not blast):
1. Capture real browser HAR of successful Send code after captcha OK
2. Diff fields vs our variants
3. Ensure captcha ticket issued in same IP/session context as ajax (proxy alignment)
4. Decode `code=51` from more JS error maps if available

## register after OTP
Planned:
```text
registerAccountV2 / completeRegisterV2
  email, password, mailCode/code, captcha fields, country, accountType, birth
```
Not proven E2E yet.

## Claim
Browserless claim endpoint not fully mapped. After login cookies exist, open TokenHub Model Gallery or first API call. Do not claim success without console evidence.

## Run
```bash
cd /root/tencent-tokenhub
.venv/bin/python register_http.py
# artifacts
# logs/attempt_http1.log
# data/last_http_result.json
```
