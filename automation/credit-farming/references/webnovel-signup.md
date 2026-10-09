# Webnovel Signup — Full Reverse-Engineering Record

Target: `https://www.webnovel.com/` (passport-based auth, JSONP API, no CAPTCHA)

## Platform Profile

- **Domain**: webnovel.com (Cloudflare protected — JS challenge, NOT Turnstile)
- **Auth subdomain**: `passport.webnovel.com` (register/login forms)
- **API subdomain**: `ptlogin.webnovel.com` (JSONP endpoints)
- **CAPTCHA**: NONE on registration form
- **Email verification**: Link-based (not OTP)
- **Password**: RSA-encrypted (PKCS1 v1.5) before sending
- **CSRF**: Token from `getInparams` endpoint, stored as cookie

## curl_cffi Accessibility

`curl_cffi` with `impersonate="chrome131"` bypasses the Cloudflare JS challenge on `passport.webnovel.com` and `ptlogin.webnovel.com`. The main site (`www.webnovel.com`) has a stricter CF config that still needs a browser.

## Registration API

**Endpoint**: `GET https://ptlogin.webnovel.com/login/doregister`  
**Format**: JSONP (wraps JSON in `CallbackName({...})`)  
**Auth tokens**: `_csrfToken` cookie (from `getInparams`)

### Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| `_csrfToken` | from cookie | Required |
| `method` | `LoginV1.registerCallback` | Callback function name |
| `format` | `jsonp` | Server always returns JSONP |
| `callback` | `jQueryXxx` | Can be anything |
| `appid` | `900` | Webnovel's app ID |
| `areaid` | `1` | Region |
| `accountType` | `102` | Email account type |
| `target` | `iframe` | Iframe mode |
| `backUrl` | `https://www.webnovel.com/` | Post-registration redirect |
| `account` | email | Same as email param |
| `email` | email | The email address |
| `password` | RSA-encrypted | PKCS1 v1.5 + base64 |
| `validateCode` | `""` | Empty = no CAPTCHA |
| `nextAction` | `0` | No next action |
| `fromuid` | `0` | No referring user |

### Response Codes

| Code | Meaning |
|------|---------|
| `0` | Success — `data.emailkey` set |
| `11401` | IP suspended (`nextAction: 2` = CAPTCHA required after ban) |
| `11302` | Password format invalid (6-18 alphanumeric only — NO special chars) |
| `-11051` | IP/IMEI banned |
| `-11055` | IP/IMEI banned from registration |
| `-11052` | Account banned |
| `-10085` | Verification failed (CAPTCHA/anti-fraud) |

### Password Rules
- 6-18 characters
- Alphanumeric only (no spaces, no special characters like `!@#$%`)
- Case sensitive

## RSA Public Key

```
-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDOf5B7Sg/EsfK+29BhFn1SUgoX
gcLP9Dl1Sf3g3PgwRTEkqMwhFVpIYoNVo1TV1q6Y6dRYZ1BExt/tqQqJcLvQhCKc
b4JuINKdftwG5le+Q2n6S/Ioyx7euYZgkmm3LSQ5VW7y+VGpMvBi70CTNFAcIM4j
4J1YzLN/RRpFysAxBQIDAQAB
-----END PUBLIC KEY-----
```

**Important**: JSEncrypt uses PKCS1_v1_5 padding (NOT OAEP). Verify encrypt matches by running a test: `JSEncrypt.encrypt("test")` in browser console → `b64encode(RSA-PKCS1_v1_5.encrypt(b"test"))` in Python should match.

## CSRF Token Flow

1. `GET passport.webnovel.com/register.html` → establishes session
2. `GET ptlogin.webnovel.com/login/getInparams` with callback → server sends `Set-Cookie: _csrfToken=xxx`
3. Use `_csrfToken` in subsequent `doregister` call

## IMAP Verification

- **Sender**: Webnovel (from email/webnovel.com)
- **Subject**: Account activation / email confirmation
- **Link pattern**: URL containing `confirm`, `verify`, `activate`, `checkemail`, or `emailkey`
- **Gmail folder**: `[Gmail]/All Mail` (or `[Gmail]/Semua Email` for Indonesian locale)
- **Poll interval**: 8 seconds, timeout after 300 seconds

## Verification Email Content

The email contains a "Akun Aktif" (Active Account) button with a confirmation link. Extract the URL from the email body and click it via HTTP to activate the account.

## Script Location

`/root/webnovel_signup.py` — PEP 723 script (single file, `uv run`)

Usage:
```bash
uv run webnovel_signup.py <email> <password> [proxy_url]
uv run webnovel_signup.py user@<REDACTED> Pass123
uv run webnovel_signup.py user@<REDACTED> Pass123 http://user:pass@1.2.3.4:8080
```
