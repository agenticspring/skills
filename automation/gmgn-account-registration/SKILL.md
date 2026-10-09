---
name: gmgn-account-registration
description: GMGN browserless account creation via wallet + reCAPTCHA.
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [GMGN, Solana, Registration, Browserless, Captcha]
---

# GMGN Account Registration (Browserless)

Creates GMGN (gmgn.ai) accounts without a browser — pure HTTP, wallet signing, and
reCAPTCHA solving. Reverse-engineered from a captured HAR file (2026-08-06); the
flow was validated end-to-end (account created, `user_info` returns 200). Also covers
follow-wallet and invite-code operations on the same API surface.

Does NOT do browser automation — GMGN's login modal will not render in headless
Chromium, so the API path is the only reliable browserless route.

## When to Use

- "Buat akun GMGN" / "create GMGN account" (one or many)
- "Follow wallet ini di GMGN" — follow_wallet API
- Submitting GMGN invite codes / referral farming
- Applying for GMGN API keys (flow starts from a logged-in account)

## Prerequisites

- Python 3.10+, packages: `pip install solders pynacl base58`
- 2captcha API key with positive balance in `~/.hermes/.env` (`TWOCAPTCHA_API_KEY[_N]`)
  OR in `/root/gmgn-bot/.env` (script auto-loads its own `.env` first, then falls back).
- Working bot: `/root/gmgn-bot/` (repo `agenticspring/gmgn-autocreate` — **public**
  since 2026-08; `.env` and `accounts/` are gitignored so no secrets exposed).
  **NOTE (2026-08): bot moved OUT of `~/.hermes/scripts/` into its own folder.**
  Layout: `gmgn_autocreate.py`, `install.sh`, `run.sh`, `batch.sh`, `.env.example`,
  `README.md`, `accounts/gmgn_accounts.json` (gitignored — private keys).

## Quick Reference

```bash
# Run one creation (new wallet each run, appends to accounts/gmgn_accounts.json)
python3 /root/gmgn-bot/gmgn_autocreate.py

# Batch (N accounts) — 1 run = 1 account, space runs out:
for i in $(seq 1 5); do python3 /root/gmgn-bot/gmgn_autocreate.py; sleep 30; done
# ~$0.12-0.15 captcha per account; sleep avoids a fresh-account burst flag.

# OR the shipped batch script (validates args + balance, spaces runs itself):
cd /root/gmgn-bot && ./batch.sh 5            # 5 accounts
./batch.sh 10 --wait 60   # 10 accounts, 60s spacing
./batch.sh 3 --no-wait    # 3 accounts, no spacing
```

```text
Endpoint: POST https://gmgn.ai/account/account/login_by_wallet
Sitekey page-level (reCAPTCHA v2 checkbox): 6Lf3pucqAAAAADbq3czpqDHRAD8j3kC-hcwwDG_T
Sitekey wallet_register (returned by step 1): 6LcrYOcqAAAAAPESxsGqz4NyUR0_cJs3YfCzuGOd
Follow: POST /api/v1/follow/follow_wallet   {chain:"sol", wallet_addresses:[...]}
Invite: POST /defi/quotation/v1/invite/add_tg_invite_info  {invite_code, chain, type}
```

## Procedure

1. **Generate a Solana wallet** — `solders.Keypair()`; keep the 64-byte secret for signing.
2. **Solve page-level reCAPTCHA** (sitekey `6Lf3pucq...`) via 2captcha `userrecaptcha` → token A.
3. **Step 1 — initiate:**
   `POST /account/account/login_by_wallet` body `{address, wallet_type:"Phantom", chain:"sol", captcha_token: A}`
   → `{session_id, step:1, require:["verify_wallet"], data:{nonce, captcha:{site_key: 6LcrYOcq..., expected_action:"wallet_register"}}}`
4. **Solve register reCAPTCHA** (sitekey `6LcrYOcq...`, action=`wallet_register`) → token B.
5. **Build SIWE message** (exact format):
   `gmgn.ai wants you to sign in with your Solana account:\n<address>\n\nwallet_sign_statement\nURI: https://gmgn.ai\nVersion: 1\nChain ID: 900\nNonce: <nonce>\nIssued At: <step1 time>\nExpiration Time: <step1 time + 300s>`
6. **Sign ed25519** with the wallet seed (first 32 bytes of secret), then **encode base58**.
7. **Step 2 — verify + login:**
   `POST login_by_wallet` body `{session_id, address, wallet_type, chain, captcha_token: B, message, signature}`
   → `{access_token, refresh_token}` = account created.
8. **Verify** with `POST /account/user_info` (Bearer access_token) → `code:0` + `user_id`.
9. **Follow wallets / submit invites** using the same Bearer token (endpoints above).

## Pitfalls

- **Signature encoding is base58, NOT base64.** This is the classic failure — step 2 returns
  `-100016 invalid login message` when the signature is base64. Verified against a captured
  signature: ed25519 64-byte sig, `base58.b58encode`.
- **SIWE `issued_at` must be step-1 request time**, not the time of step 2 (which happens after
  the second captcha solve). Compute it right after the step-1 call.
- **2captcha primary key is often drained.** Auto-scan `TWOCAPTCHA_API_KEY*` for the first
  positive balance before solving (the script does this). `ERROR_ZERO_BALANCE` = key empty, try next.
- **URL format for GMGN address/invite links:** `https://gmgn.ai/sol/address/<invite>_<wallet>`
  — the part before `_` is an invite code, after `_` is the real base58 wallet address.
  Feeding the whole thing to the API returns `invalid wallet address`.
- **Follow requires the account's own group or no group.** Reusing a group id from a different
  account returns `Invalid group`. Omit `group_ids` and it succeeds with `code:0`.
- **GMGN login modal does NOT render in headless Chromium** (anti-bot). Don't burn time on
  Playwright UI clicking; go straight to the API.
- **No Cloudflare clearance needed on `/account/*` POSTs** — browser-ish headers
  (Android Chrome UA, Origin/Referer gmgn.ai) suffice.
- **HAR files are gold for this class of work** — a captured browser session reveals the full
  auth flow, exact payloads, and response shapes; parse with `json` and diff request sequences.

## Verification

```bash
# After creation, this must return 200 with code:0 and a user_id:
curl -s -X POST "https://gmgn.ai/account/user_info?device_id=<id>&fp_did=unknown&client_id=gmgn_web_20260806-2992-8990b78&from_app=gmgn&app_ver=20260806-2992-8990b78&tz_name=Asia/Jakarta" \
  -H "Authorization: Bearer <access_token>" -H "Content-Type: application/json" -d '{}'
```
