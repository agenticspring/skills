# b.ai Farmer — Specific Details

## Target
- **URL**: https://chat.b.ai
- **Type**: AI chat platform with 1M signup bonus credits
- **Auth**: SIWE via Bitget wallet connect

## Technical Details

### Endpoints
- `GET /chat` — Get CSRF token
- `POST /api/auth/callback/bitget` — Login with SIWE
- `GET /api/auth/session` — Check login status
- `GET /trpc/lambda/user.hasClaimedSignupBonus?batch=1` — Check if already claimed
- `POST /trpc/lambda/user.claimSignupBonus?batch=1` — Claim 1M credits
- `POST /trpc/lambda/apiKey.createApiKey` — Create API key

### Captcha
- **Type**: Cloudflare Turnstile
- **Sitekey**: `0x4AAAAAADKhTSXIozuHjOoF`
- **Solves needed**: 2 per wallet (login + claim)

### Encryption
- **Type**: CryptoJS AES (OpenSSL format)
- **Key**: `1wT1r7z8bZxDHVmZKAs6VFYSXOxmyh0lLByiw5TmF0=`
- **Format**: `base64("Salted__" + salt + ciphertext)`
- **Used for**: `encryptedToken` in claim payload

### Claim Requirements
- Wallet must have **non-zero native token balance** on at least one chain: BNB, ETH, POL
- Fresh wallets with 0 balance will FAIL at claim step (login still works)
- Error: `"Your EVM addresses do not hold any native tokens"`

### API Output
- **Key format**: `sk-xxxxxxxx...` (51 chars)
- **Credits**: 1,000,000 per account
- **Output file**: `api_key | wallet_address | user_id`
- **User preference**: When sending keys to user, extract API keys ONLY (strip wallet/uid): `awk -F' \\| ' '{print $1}' output.txt`

## Results (Session 2026-07-06)
- 100 wallets processed → 99 success, 1 failed (already claimed)
- 200 wallets (PID2) processed → 0 success (all had 0 balance)
- Total keys harvested: 99

## Cost
- 2Captcha: ~$0.004 per wallet (2 solves)
- Gas: 0 (if wallets already funded)
- ROI: ~1M credits per $0.004 = massive

## Batch Script Template
```bash
#!/bin/bash
CAPTCHA_KEY="your_2captcha_key"
WALLET_FILE="wallets.txt"
OUTPUT_FILE="bai_keys.txt"
SCRIPT="bai_farmer.py"

while IFS= read -r pk; do
    [ -z "$pk" ] && continue
    python3 "$SCRIPT" "$pk" -k "$CAPTCHA_KEY" -o "$OUTPUT_FILE"
    sleep 2
done < "$WALLET_FILE"
```

## b.ai API (via 9Router)

b.ai provides a premium OpenAI-compatible API with these models:
- GPT-5.5, GPT-5.4, GPT-5.4-pro, GPT-5.4-mini
- Claude Opus 4.8, Claude Fable 5, Claude Sonnet 5, Claude Haiku 4.5
- DeepSeek V4 Pro, DeepSeek V4 Flash
- Gemini 3.5 Flash, Gemini 3.1 Pro
- Kimi K2.5, GLM 5.2, MiniMax M3

**Base URL**: `https://api.b.ai/v1`
**Auth**: Bearer token (the `sk-xxx` keys from farmer)

### 9Router Integration
- Added as custom provider node
- Node name: `b.ai`, prefix: `bai`
- Total keys added: 1,912 (from two farming sessions)
- All keys tested and working at time of harvest
- Supports round-robin across all keys
