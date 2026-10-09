# GMGN (gmgn.ai) — Browserless Wallet Registration

Reverse-engineered 2026-08-06 from a captured HAR file. GMGN is a multi-chain meme
trading terminal (Solana/BSC/Base). Account creation = wallet login; there is NO
email/password path. The full flow works with pure HTTP — no browser needed.

## Flow (verified working)

Two reCAPTCHA solves + one SIWE wallet signature:

```
1. Generate fresh Solana keypair (solders.Keypair) — wallet_type "Phantom", chain "sol"
2. Solve reCAPTCHA v2 checkbox (sitekey SITEKEY_PAGE)        -> token A
3. POST /account/account/login_by_wallet
     {address, wallet_type:"Phantom", chain:"sol", captcha_token: tokenA}
   Response: {code:0, data:{session_id, step:1, require:["verify_wallet"],
              data:{nonce, captcha:{site_key: SITEKEY_REGISTER, expected_action:"wallet_register"}}}}
4. Solve reCAPTCHA v2 checkbox (sitekey SITEKEY_REGISTER, action="wallet_register") -> token B
5. Build SIWE message (exact format below)
6. Sign message with ed25519 (first 32 bytes of 64-byte secret = seed),
   ENCODE SIGNATURE AS BASE58 (NOT base64 — see pitfall)
7. POST /account/account/login_by_wallet
     {session_id, address, wallet_type, chain, captcha_token: tokenB, message, signature}
   Response: {code:0, data:{data:{access_token:{token,expire_at}, refresh_token:{token,expire_at}}}}
```

## Exact constants (2026-08-06)

```
SITEKEY_PAGE      = "6Lf3pucqAAAAADbq3czpqDHRAD8j3kC-hcwwDG_T"   # page-level checkbox
SITEKEY_REGISTER  = "6LcrYOcqAAAAAPESxsGqz4NyUR0_cJs3YfCzuGOd"   # wallet_register action
API_BASE          = https://gmgn.ai
LOGIN_PATH        = /account/account/login_by_wallet
DEVICE_ID         = b59c3d76-5766-4fe1-b576-738fe500ece7         # reusable from HAR
UA                = Mozilla/5.0 (Linux; Android 10; K) ... Chrome/148 Mobile Safari
```

## SIWE message (exact — every newline matters)

```
gmgn.ai wants you to sign in with your Solana account:
<address>

wallet_sign_statement
URI: https://gmgn.ai
Version: 1
Chain ID: 900
Nonce: <nonce-from-step1>
Issued At: <step1-time ISO with milliseconds, e.g. 2026-08-06T04:10:07.927Z>
Expiration Time: <step1-time + 300s>
```

Key details:
- `Issued At` must be the STEP-1 request time (not step-2 time) — capture it before calling step 1.
- Milliseconds in the ISO timestamp are fine (the captured HAR used `.927Z`).
- `Chain ID: 900` is GMGN's Solana SIWE chain id — do not "fix" it to 101.

## Pitfalls (each cost real debugging time)

1. **Signature encoding is BASE58, not base64.** The server returns
   `{"code":-100016,"message":"invalid login message"}` if you send base64. Verify
   before scripting: decode the captured signature both ways and check the ed25519
   signature verifies with the captured public key:
   `base58.b58decode(sig)` -> 64 bytes -> `nacl.signing.VerifyKey(pub).verify(message, sig)`.
2. **2captcha primary key can be zero/negative balance.** Auto-scan the sequential
   `TWOCAPTCHA_API_KEY[_N]` vars from `~/.hermes/.env`, check `getbalance` on each,
   use the first with `float(balance) > 0`. Do not hardcode the first key.
3. **Two different reCAPTCHA sitekeys.** The page-level checkbox and the
   wallet_register checkbox use different keys. Solving only one fails at step 4/7.
4. **Cloudflare**: the page itself loads fine in a headless browser, but raw `curl`
   to `/account/*` returns 403 without the app's headers. The pure-HTTP flow works
   with the Android UA + Origin/Referer/sec-fetch headers copied from the HAR.
5. **HAR capture is the blueprint**: user opens DevTools → Network → (check Preserve
   log) → performs one manual login → exports HAR. Parse `log.entries`, filter
   `/account|wallet|auth|sign|login|verify/`, then inspect full POST bodies —
   the step-2 body has `message` + `signature` fields that look like they're missing
   until you print the full JSON (they sit after the long captcha_token).

## Working implementation

`/root/.hermes/scripts/gmgn_autocreate.py` — runnable, saves each account to
`/root/gmgn_accounts.json` (address, secret b58, access/refresh tokens, expiry).
Deps: `solders`, `PyNaCl`, `base58`, `requests`/urllib.

## Verify an account after creation

- `POST /account/user_info` with `Authorization: Bearer <access_token>` and `{}`
  body → HTTP 200 `code:0` = token valid, account real (returns `user_id`,
  `create_time`, bot addresses). 404 = wrong method (needs POST, not GET).
- `GET /api/v1/user_vip_level` with Bearer → 200 `vip_level:0` for fresh accounts.
- `GET /tapi/v1/wallet/list?chain=sol` → `40101600 GMGN_TRADE_UNAUTHORIZED` is
  EXPECTED until the wallet is imported for trading — it is NOT an auth failure
  and does not mean the account is broken.
