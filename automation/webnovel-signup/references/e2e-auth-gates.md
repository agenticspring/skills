# Webnovel E2E Auth Gates (validated)

Source run: `/root/webnovel-autoreg` — first fully proven HTTP account `elizabeth.clark80@<REDACTED>` (register → confirm → login `code=0`).

## Success ladder

1. `doregister` → `code=0` + `data.emailkey` present  
   - Status text: **Registration submitted** only
2. IMAP finds activation mail for **that exact address**
3. Extract longest `/f/a/` CTA (not `/q/`)
4. Resolve to `confirm.html?emailkey=...`
5. `login/confirm` with double-encoded emailkey → `ticket` + `userId`, code `0` or `4`
6. `login/checkcode` password accepted
7. If `11318`, auto device trust: `sendTrustEmail` → Guard OTP (alnum like `xW0Isq`) → `checkTrust` → prefer final `code=0`
8. Append `email:password` to ledger only after password accepted (and trust completed when required)

If any step fails → do not save.

Guard OTP detail: `device-trust-11318.md`.

## Confirm emailkey encoding

Browser `LoginV1.jsonp` keeps `emailkey` as the **raw once-encoded** query substring, then jQuery serializes again:

- URL: `emailkey=...%2F...%3D%3D`
- Wire request: `emailkey=...%252F...%253D%253D`

Wrong encodings seen live:
- decoded plaintext → `11311 Email key is empty`
- once-encoded only → flaky / `code=2 Request Error` on some keys
- double-encoded + referer/bootstrap confirm page → stable `code=0` with ticket

Also accept `code=4` (“already registered… try logging in”) when ticket+userid present.

## IMAP catch-all rules

Bad pattern (caused false confirms):
```text
search UNSEEN FROM "webnovel"
```
On catch-all Gmail this returns **other accounts'** activation mails.

Required:
- search `TO "target@domain"` and/or `TEXT "target@domain"`
- require target address in To / Delivered-To / X-Original-To / body before accepting
- prefer HTML `href="https://post.eu.spmailtechnol.com/f/a/..."` and pick **longest**

## Login / reset code map

| Endpoint | code | Meaning |
|----------|------|---------|
| checkcode | 0 | login ok |
| checkcode | 11313 | bad email/password or unusable account |
| checkcode | 11318 | password ok, device trust email |
| checkcode | 11401 + google/nextAction | password ok, risk captcha |
| resetPwsMail | 0 | account exists, reset mail queued |
| resetPwsMail | 11314 | account does not exist |
| resetPwsMail | 11401 nextAction=1 | account likely exists, captcha gate |

If register+confirm looked green but reset is `11314` and checkcode is `11313`, the earlier green path used the **wrong email/CTA**.

## Register payload (browser-aligned)

```
callback, _csrfToken, method=LoginV1.registerCallback,
accountType=102, email, account, password=<rsa b64>,
validateCode=, nextAction=, format=jsonp,
appid=900, areaid=1, target=iframe, returnurl=...
```

Avoid inventing `backUrl` / `fromuid=0` unless live browser sends them.

## Env loader

Project `.env` may contain blank `IMAP_PASS=`. Allow later credential files (e.g. `/root/cf-tuyul/.env`) to fill empty values for IMAP/DOMAIN/PASSWORD.

## Status wording

- Registration submitted
- Verification email found
- Confirm URL resolved
- Confirmed (ticket/userid)
- Login proven
- Success (ledger write)
