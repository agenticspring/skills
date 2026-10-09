# Webnovel Signup — Session-Specific Detail

## Endpoints

| Step | URL | Method | Notes |
|------|-----|--------|-------|
| Register page | `https://passport.webnovel.com/register.html?appid=900&areaid=1&target=iframe` | GET | No CF JS challenge on this subdomain |
| getInparams | `https://ptlogin.webnovel.com/login/getInparams` | JSONP GET | Returns `_csrfToken` cookie via Set-Cookie header |
| doregister | `https://ptlogin.webnovel.com/login/doregister` | JSONP GET | Password must be RSA PKCS1 v1.5 encrypted |
| email confirm | `https://ptlogin.webnovel.com/login/confirm` | GET | Click the emailkey link |
| resendRegEmail | `https://ptlogin.webnovel.com/login/resendRegEmail` | JSONP GET | Resend verification email |

## Parameters

- `appid=900` — Webnovel app ID
- `areaid=1` — Global region
- `accountType=102` — Email-based account
- `format=jsonp` — All API calls use JSONP
- `method=LoginV1.registerCallback` — Callback function name

## Error Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success | Proceed to email verification |
| 11302 | Invalid password | Use 6-18 alphanumeric only (no symbols/spaces) |
| 11401 | IP suspended | Wait 30+ min or use residential proxy |
| -11051 | IP banned from login | Use different proxy/network |
| -11055 | IP banned from registration | Use different proxy/network |

## RSA Public Key

```
-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDOf5B7Sg/EsfK+29BhFn1SUgoX
gcLP9Dl1Sf3g3PgwRTEkqMwhFVpIYoNVo1TV1q6Y6dRYZ1BExt/tqQqJcLvQhCKc
b4JuINKdftwG5le+Q2n6S/Ioyx7euYZgkmm3LSQ5VW7y+VGpMvBi70CTNFAcIM4j
4J1YzLN/RRpFysAxBQIDAQAB
-----END PUBLIC KEY-----
```

1024-bit RSA key, PKCS1 v1.5 padding, base64-encoded ciphertext.

## IP Ban Behavior

- Webnovel tracks IP for registration attempts
- After ~1-3 attempts from the same IP, it returns code 11401 (IP suspended)
- Suspension lasts ~30-60 minutes
- Residential proxies work; datacenter proxies from old Proxyscrape lists were already flagged
- No CAPTCHA/Turnstile is required on the registration page

## Original Session Context

Built during investigation of Webnovel signup automation. The key insight was that `passport.webnovel.com` and `ptlogin.webnovel.com` subdomains don't have Cloudflare JS challenge (only `www.webnovel.com` does), so `curl_cffi` impersonation isn't needed — pure stdlib `urllib.request` works. The template script at `templates/webnovel-signup.py` is a compact working implementation.
