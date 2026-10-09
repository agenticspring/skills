# ProxyScrape signup — live notes (2026-07-22)

## Reverse sources
- Page: `https://dashboard.proxyscrape.com/v2/sign-up`
- Chunk: `pages/sign-up-*.js` → `X.signUp({email,password,cf_turnstile_token})`
- App: `signUpEndpoint:"/v2/v4/account/auth/register"`
- Turnstile sitekey: `0x4AAAAAAAFWUVCKyusT9T8r`

## Register body
```
email=<addr>
password=<policy>
cf_turnstile_token=<turnstile>
```
`Content-Type: application/x-www-form-urlencoded`

Success sample fields:
- `access_token`, `token_type=bearer`, `expires_in`
- `userData.EmailVerified` starts `false`
- `userData.emailId`, `associatedSubaccounts` may be empty until trial

## Verify body (proven)
```
verificationCode=<from email>
```
+ `Authorization: Bearer <access_token>`

Wrong fields (`code`, `otp`, `token`) → `400 Verification code is not set.`  
Right field → `200 Verification successfully completed`

Email body pattern:
```
Here is your email verification code: 5bc88e2bf7
```
(hex/alnum, not only 6-digit)

## Resend
`POST /v2/v4/account/reset-verification-code` with Bearer  
→ `New verification code has been sent`

## Domain matrix (Dez catch-all)
| Domain | Deliverability | Trial |
|---|---|---|
| <REDACTED> | OK (resend helped ~45s) | Premium trial subaccount created |
| <REDACTED> | No verification mail in 3+ min | N/A |
| <REDACTED> | OK | Rejected: “email may be disposable” / Trial not created |

User: **do not use <REDACTED>** for ProxyScrape after mark.

## Proven good account shape
```
email: casey_kim18@<REDACTED>
EmailVerified: true
associatedSubaccounts: [{
  AccountType: datacenter_shared,
  label: Account 1 (Premium trial)
}]
```

## Project path
`/root/proxyscrape-autoreg/register.py`
