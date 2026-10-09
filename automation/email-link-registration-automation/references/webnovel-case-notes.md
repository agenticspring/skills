# Webnovel Case Notes

Session notes for Webnovel signup/login automation. Implementation skill: `webnovel-signup`. Success-gate skill: `webnovel-account-automation`.

## Proven end-to-end (HTTP stdlib path)

Validated account path produced login-proven ledger entry, e.g. `elizabeth.clark80@<REDACTED>` with:
1. register `code=0` + emailkey
2. correct catch-all IMAP mail
3. longest `/f/a/` CTA → confirm.html
4. confirm double-encoded emailkey → ticket/userid
5. checkcode password accepted (`0` on first pass; later recheck can be `11318` Untrusted Device)

## Endpoints

- Register: `https://ptlogin.webnovel.com/login/doregister`
- Confirm: `https://ptlogin.webnovel.com/login/confirm`
- Login pre-check: `https://ptlogin.webnovel.com/login/checkcode` (`LoginV1.checkCode()` first)
- Reset probe: `https://ptlogin.webnovel.com/login/resetPwsMail`
- Runtime RSA: `https://www.yueimg.com/login/v2/js/login_v6.js`

## Password rules

```
/^(?!([a-zA-Z]+|\d+)$)[a-zA-Z\d]{6,18}$/
```

## Email / confirm quirks

- From: `service@webnovel.com`, subject like `Activate your Webnovel account`
- Gmail locale folder: `[Gmail]/Semua Email`
- CTA: `post.eu.spmailtechnol.com/f/a/...` (not `/q/` pixel GIF)
- Confirm `emailkey` must be **double-encoded** like jQuery
- Confirm success: code `0` or `4` with ticket+userId

## Bug fixes that mattered

1. **IMAP env precedence** — blank local `IMAP_PASS=` must not block fallback env files
2. **False success** — never save on register alone; require confirm + login password OK
3. **Catch-all IMAP poison** — never `UNSEEN FROM webnovel` alone
4. **Wrong CTA** — `/q/` beacon vs `/f/a/` activation
5. **Misleading wording** — `Registration submitted` until login proven

## Login / reset codes

| code | meaning |
|------|---------|
| 0 | login ok |
| 11313 | bad password / unusable |
| 11318 | password ok, untrusted device |
| 11401 + google/nextAction | password ok, captcha risk |
| 11314 (reset) | account missing |

## Evidence threshold

Complete only when register + correct-mail CTA + confirm ticket + login password accepted are all proven.
