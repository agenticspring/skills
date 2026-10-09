# Webnovel Registration — Full Flow

## Domain Map

| Domain | Purpose |
|--------|---------|
| `passport.webnovel.com` | Login/signup iframe pages |
| `ptlogin.webnovel.com` | JSONP API endpoints (login, register, checkStatus) |
| `www.yueimg.com` | Static assets (JS, CSS, images) |
| `www.webnovel.com` | Main site |

## Registration Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/register.html` | GET | Registration page (sets base cookies) |
| `/login/getInparams` | GET (JSONP) | Returns CSRF token (via Set-Cookie) and config data |
| `/login/doregister` | GET (JSONP) | Submit registration |

## Required Parameters for doregister

```
_csrfToken    — from cookie (set by getInparams)
method        — 'LoginV1.registerCallback'
format        — 'jsonp'
callback      — 'jq' (or any jQuery-style name)
appid         — '900'
areaid        — '1'
accountType   — '102'
target        — 'iframe'
backUrl       — 'https://www.webnovel.com/'
account       — email
email         — email
password      — RSA-encrypted (PKCS1 v1.5)
validateCode  — '' (empty, unless CAPTCHA triggered)
nextAction    — '0'
fromuid       — '0'
returnurl     — 'https://www.webnovel.com/'
```

## JSONP Response Format

```
LoginV1.registerCallback({"code":0,"msg":"ok","data":{"emailkey":"...","email":"..."}})
```

## Error Codes

| Code | Meaning | Action |
|------|---------|--------|
| `0` | Success | emailkey returned; save account |
| `11302` | Password format error | Must be 6-18 alphanumeric, mix of letters+digits |
| `11401` | IP suspended (nextAction=2) | Rotate proxy or wait |
| `-11051` | IP/IMEI banned from login | Rotate proxy |
| `-11055` | IP banned from registration | Rotate proxy |
| `-11053` | Browser banned | Rotate proxy |
| `-11052` | Account banned | Different credentials |

## Password Rules

Regex from client JS: `/^(?!([a-zA-Z]+|\d+)$)[a-zA-Z\d]{6,18}$/`

- 6-18 characters
- Alphanumeric only (no special chars)
- Must contain BOTH letters AND digits (cannot be all-letters or all-digits)

## RSA Pubkey Location

Fetch from: `https://www.yueimg.com/login/v2/js/login_v6.js`

Extract: `re.search(r"pubkey\s*=\s*'([^']+)'", js_content)`

Pubkey changes periodically — always fetch fresh. The page HTML (Next.js SSR) does NOT contain it; it's only in the JS bundle.

## Full Registration Flow

```
1. GET login_v6.js              → extract RSA pubkey (n, e)
2. GET register.html            → set base cookies
3. GET getInparams?callback=... → sets _csrfToken cookie
4. Read _csrfToken from cookie jar
5. RSA-encrypt password with n, e
6. GET doregister?params...     → submit registration
7. Check response code == 0
8. Poll IMAP [Gmail]/All Mail   → extract verification URL
9. GET verification URL         → confirm account
```

## Email Verification

- Webnovel sends email with a confirmation link
- Link format: `https://ptlogin.webnovel.com/login/confirm?emailkey=...`
- IMAP polling should search `[Gmail]/All Mail` folder (not INBOX)
- Filter by recipient email address using `TO` search

## Proxy Rotation

When IP is banned (code 11401 / -11051 / -11055):
1. Mark current proxy as dead
2. Pick next proxy from pool
3. Retry the same email with new proxy
4. If no proxies left, stop

Proxy file format: `host:port:user:pass` (one per line)
Parsed to: `http://user:pass@host:port` for urllib

## Batch Registration Strategy

1. Fetch RSA pubkey once (shared across all accounts)
2. For each account:
   a. Generate random identity (region-appropriate name)
   b. Pick proxy from pool
   c. Register with proxy
   d. On success → save to accounts.txt, poll IMAP
   e. On ban → mark proxy dead, retry with different proxy
   f. On other error → skip
3. Summary report at end

## Identity Pools

Names should be region-diverse to avoid detection:
- USA: English first/last names
- Asia: Chinese, Japanese, Korean, Indian names
- Europe: German, French, Italian, Dutch, Nordic names

Email format: `firstname.lastnameNN@domain`
