# Webnovel Login Flow Notes

Derived from reverse-inspecting `passport.webnovel.com/emaillogin.html` and `login_v6.js`.

## Entry page
- URL: `https://passport.webnovel.com/emaillogin.html?appid=900&areaid=1&target=iframe&returnurl=https://www.webnovel.com/`
- Submit button calls `LoginV1.checkCode()`, not a separate public `login()` helper on this page.

## checkcode (password gate)
1. Build base data (`_csrfToken` from cookie)
2. `username`, `password = LoginV1.rsa_encryption(password)` (JSEncrypt / PKCS1 v1.5)
3. `sessionkey`, `logintype=22`, `method=LoginV1.checkCodeCallback`
4. GET JSONP `https://ptlogin.webnovel.com/login/checkcode`

### Observed codes
| code | msg / meaning | next |
|------|---------------|------|
| 0 | ok + returnurl/ticket | full login |
| 11313 | Email or password incorrect | fail |
| 11318 | Untrusted Device + `encry`/`sessionKey` | trust flow |
| 11401 | risk / google code (`nextAction=1`) | captcha (password often already OK) |

## Device trust after 11318
See `references/device-trust-11318.md`.

Summary:
- `sendTrustEmail` with `encry`
- IMAP Guard code (alphanumeric, e.g. `BRAAOz`)
- `checkTrust` with `encry` + `trustcode` + `sessionKey`
- success `code=0` then jump returnurl

## Practical policy
- Registration `doregister code=0` alone is not usable-account proof.
- Require confirm ticket + password acceptance (`0` / completed trust / captcha-after-password `11401`).
- Prefer aiming for full `checkcode/checkTrust code=0` when automating.
