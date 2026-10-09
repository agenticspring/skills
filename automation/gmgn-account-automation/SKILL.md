---
name: gmgn-account-automation
description: "Create GMGN accounts browserlessly: reCAPTCHA + SIWE."
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [GMGN, Solana, SIWE, reCAPTCHA, Account-Automation]
---

# GMGN Account Automation (Browserless)

Creates GMGN (gmgn.ai) accounts with zero browser interaction, then optionally
auto-follows target wallets. The flow was reverse-engineered from a captured
WebInspector HAR (2026-08-06) and verified end-to-end — accounts created,
tokens validated via `/account/user_info`, wallet follows confirmed via the
follow list endpoint.

Working script lives at `/root/gmgn-bot/gmgn_autocreate.py` (repo
`agenticspring/gmgn-autocreate` — **public** since 2026-08; `.env` and
`accounts/` are gitignored, so no secrets are exposed).

## When to Use

- "Buat akun GMGN" / "bikin akun gmgn" / "create gmgn accounts"
- Need GMGN accounts at scale (farming, following wallets, API keys)
- User drops a `.txt` HAR captured from gmgn.ai and wants the auth flow replicated
- Follow target wallets automatically after account creation

## Prerequisites

- Python 3.10+, `pip install solders pynacl base58`
- 2captcha API key **with positive balance** in `~/.hermes/.env`
  (`TWOCAPTCHA_API_KEY`, `TWOCAPTCHA_API_KEY_2`, ...)
- No browser, no CF clearance needed on `/account/*` endpoints (unlike most of gmgn.ai)

## How to Run

```bash
# single account
python3 /root/gmgn-bot/gmgn_autocreate.py

# many accounts (5): loop it — 1 run = 1 new account
for i in $(seq 1 5); do python3 gmgn_autocreate.py; sleep 30; done

# OR use the shipped batch script (checks balance first, reports success/fail):
cd /root/gmgn-bot && ./batch.sh 5              # 5 accounts, 30s spacing
./batch.sh 10 --wait 60   # 10 accounts, 60s spacing
./batch.sh 3 --no-wait    # 3 accounts, no spacing
```

Each run generates a NEW Solana wallet + NEW GMGN account, then follows every
address in `FOLLOW_TARGETS`. Accounts append to `/root/gmgn-bot/accounts/gmgn_accounts.json`
(gitignored — contains private keys).

Batch pattern: keep runs spaced (`sleep 30-60`) to avoid GMGN flagging a burst of
fresh accounts; watch 2captcha balance (1 account ≈ $0.12–0.15 = 2 solves).
`install.sh` + `run.sh` are the user-facing entry points; `run.sh` loads `.env`
from the bot folder before executing. `batch.sh` validates args + 2captcha
balance before looping (arg test: `bash batch.sh 0` prints the positive-integer
error and exits cleanly).

## Verified Flow (from HAR)

1. **Solve reCAPTCHA v2 checkbox #1** — sitekey `6Lf3pucqAAAAADbq3czpqDHRAD8j3kC-hcwwDG_T` (page-level)
2. `POST /account/account/login_by_wallet`
   body: `{"address": <sol_pubkey>, "wallet_type": "Phantom", "chain": "sol", "captcha_token": <tokenA>}`
   → 200 `{session_id, step:1, require:["verify_wallet"], data:{nonce, captcha:{site_key: SITEKEY2, expected_action:"wallet_register"}}}`
3. **Solve reCAPTCHA v2 checkbox #2** — sitekey `6LcrYOcqAAAAAPESxsGqz4NyUR0_cJs3YfCzuGOd`, action `wallet_register`
4. **Build SIWE message**:
   ```
   gmgn.ai wants you to sign in with your Solana account:
   <address>

   wallet_sign_statement
   URI: https://gmgn.ai
   Version: 1
   Chain ID: 900
   Nonce: <nonce>
   Issued At: <step1 time ISO>
   Expiration Time: <step1 time + 300s ISO>
   ```
5. **Sign ed25519** with wallet seed (first 32 bytes of the 64-byte secret)
6. `POST /account/account/login_by_wallet`
   body: `{session_id, address, wallet_type, chain, captcha_token: <tokenB>, message, signature}`
   → 200 `{access_token, refresh_token}` = ACCOUNT CREATED
7. Optional: `POST /api/v1/follow/follow_wallet`
   body: `{"chain": "sol", "wallet_addresses": [<addr>], "remark_addresses": []}`
   → 200 `{"code":0}` ; verify with `GET /api/v1/follow/follow_wallet_page_multi_chain`
   body `{"chain":["sol","bsc"],"page_size":2000}` → list contains `following_address`

## Quick Reference

```bash
# 2captcha solve
curl -s "https://2captcha.com/in.php?key=KEY&method=userrecaptcha&googlekey=SITEKEY&pageurl=https://gmgn.ai/?chain=sol&json=1"
curl -s "https://2captcha.com/res.php?key=KEY&action=get&id=TASK_ID&json=1"

# verify token works
curl -s "https://gmgn.ai/account/user_info?device_id=...&fp_did=unknown&client_id=...&from_app=gmgn&app_ver=...&tz_name=Asia/Jakarta" \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{}'

# follow wallet
curl -s -X POST "https://gmgn.ai/api/v1/follow/follow_wallet?device_id=...&from_app=gmgn..." \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"chain":"sol","wallet_addresses":["<addr>"],"remark_addresses":[]}'
```

## Pitfalls

- **Solana SIWE signature is base58, NOT base64.** The most common failure:
  server returns `{"code":-100016,"message":"invalid login message"}`. Encode the
  64-byte ed25519 signature with `base58.b58encode()`. Verified against a captured
  HAR signature with `nacl.signing.VerifyKey(pubkey).verify(message, sig)`.
- **`issued_at` must be the step-1 request time**, not the time you finish solving
  captcha #2 (5-minute solve window makes this fail otherwise).
- **2captcha primary key can be $0/negative.** Auto-scan sequential
  `TWOCAPTCHA_API_KEY[_N]` for the first positive balance before solving.
- **Biggest-balance 2captcha key can fail while a small key works.** A key with
  $1.50 balance may return `ERROR_CAPTCHA_UNSOLVABLE` repeatedly while a $0.09
  key solves fine. Do NOT return on first key's failure — try ALL positive-balance
  keys in balance-descending order until one returns a token (script:
  `_solve_2captcha` loops `_solve_2captcha_with_key` per key; current working
  balance is `54081d9b559e…` not the $1.50 key). Dedupe keys first — several
  `TWOCAPTCHA_API_KEY_N` vars can hold the SAME value, and without dedupe the
  same failing key is tried 3×.
- **Capsolver fallback: pick the key with the LARGEST balance, not the first
  positive.** A key with $0.0001 balance gets selected by "first > 0" and then
  fails `HTTP Error 400`. Track `best_balance` across keys (current winner
  `CAP-BD487656…` ≈ $38).
- **Capsolver keys must be loaded from `~/.hermes/.env` too.** `load_env()` used to
  fall back only `TWOCAPTCHA_API_KEY*` vars; CAPSOLVER keys were missing → "Capsolver
  key tidak ada di .env — skip". The fallback loop must include both
  `TWOCAPTCHA_API_KEY*` and `CAPSOLVER_API_KEY*` prefixes.
- **Local `.env` shadowing.** The bot reads `.env` in its own folder first and
  falls back to `~/.hermes/.env` for missing vars. `install.sh` creates a blank
  `.env` — if you test after a fresh install without filling it, `batch.sh` fails
  with "TWOCAPTCHA_API_KEY kosong" even though the key exists in `~/.hermes/.env`.
  Fill the local `.env` (or remove it) when the bot folder is the working copy.
- **GMGN reCAPTCHA is v2 checkbox, NOT enterprise.** Adding `enterprise=1` to
  2captcha or using `ReCaptchaV2EnterpriseTaskProxyLess` on Capsolver makes
  workers fail with `ERROR_CAPTCHA_UNSOLVABLE` — even for keys that worked
  before. Use plain `userrecaptcha` / `ReCaptchaV2TaskProxyLess`. The
  `recaptcha/enterprise` URLs in the HAR are just the page loading the standard
  checkbox widget — don't be fooled.
- **Provider fallback chain (current design):** all 2captcha keys (balance desc,
  deduped) → Capsolver (largest balance) → retry whole chain (3 attempts).
  This is what makes a batch survive a flaky provider day.

> Full debugging transcript, key/balance table, and the enterprise trap timeline:
> `references/captcha-provider-debug.md`
- **GMGN invite URL format** is `invitecode_walletaddress` (e.g.
  `yO1att5f_GV6UUmNxz2RpKxmNA...`). Split on `_`: left = invite code (used in
  `POST /defi/quotation/v1/invite/add_tg_invite_info`), right = real Solana address.
  A raw paste of that URL is NOT a valid base58 address by itself.
- **follow_wallet without `group_ids` works** (auto default group). Passing another
  account's group id → `Invalid group`.
- **`wallet/list` (trade API) returns 401** after login — separate authorization
  domain, not a login failure. Verify with `user_info` / `user_vip_level` instead.
- **HAR files from Telegram are `.txt` but JSON** — `json.load()` directly, then
  scan `log.entries` for auth paths (`login_by_wallet`, `verify_wallet_signature`,
  `follow_wallet`) and read `request.postData.text` + `response.content.text`.

## Verification

```bash
# Account truly exists + token valid:
curl -s ".../account/user_info" -H "Authorization: Bearer <token>" -d '{}'
# expect: {"code":0,"data":{"data":{"user_id":"..."}}}
```
