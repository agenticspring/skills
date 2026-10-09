# b.ai Technical Reference

## Target

- **URL:** https://chat.b.ai
- **Platform:** AI chat service with 1M signup credits
- **Auth:** SIWE (Sign In With Ethereum) via Bitget wallet

## Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/chat` | GET | Get CSRF token |
| `/api/auth/callback/bitget` | POST | Login with SIWE |
| `/api/auth/session` | GET | Check login status |
| `/trpc/lambda/user.hasClaimedSignupBonus?batch=1` | GET | Check if already claimed |
| `/trpc/lambda/user.claimSignupBonus?batch=1` | POST | Claim 1M credits |
| `/trpc/lambda/apiKey.createApiKey` | POST | Create API key |

## Constants

```
TURNSTILE_SITEKEY = "0x4AAAAAADKhTSXIozuHjOoF"
ENCRYPT_KEY = "1wT1r7z8bZxDHVmZKAs6VFYSXOxmyh0lLByiw5TmF0="
```

## SIWE Message Format

```
Welcome to BAI !
https://chat.b.ai wants you to sign in with your account:
{ADDRESS}

Chain ID: 0x1
Expiration Time: {ISO_DATETIME_24H_FROM_NOW}
Nonce: 1PSFBM{TIMESTAMP_MS}
```

## Claim Message Format

```
BAI welcome gift-claim
Account:
{ADDRESS}
Chain ID: 0x1
Nonce: TV00G8{TIMESTAMP_MS}
```

## Encrypted Token

CryptoJS AES-CBC format:
- Input: `"BAI welcome gift-claim|{TIMESTAMP_MS}"`
- Key: `ENCRYPT_KEY` (base64)
- Output: Base64 of `Salted__` + 8-byte salt + ciphertext

## Login Payload

```json
{
  "chain": "eth",
  "message": "{SIWE_MESSAGE}",
  "signature": "{ETH_SIGNATURE}",
  "turnstileToken": "{TURNSTILE_SOLUTION}",
  "version": "2",
  "csrfToken": "{CSRF_TOKEN}",
  "callbackUrl": "https://chat.b.ai/chat"
}
```

## Claim Payload

```json
{
  "0": {
    "json": {
      "address": "{ADDRESS}",
      "chain": "eth",
      "encryptedToken": "{AES_ENCRYPTED_TOKEN}",
      "message": "{CLAIM_MESSAGE}",
      "signature": "{CLAIM_SIGNATURE}",
      "turnstileToken": "{TURNSTILE_SOLUTION}",
      "type": "wallet",
      "version": "2"
    }
  }
}
```

## API Key Creation

```json
{
  "json": {
    "group": "default",
    "name": "auto-{ADDR_PREFIX}"
  }
}
```

## Critical Requirements

1. **Wallet MUST hold native tokens** (ETH, BNB, or POL)
   - Error without: "Your EVM addresses do not hold any native tokens"
   - Minimum: ~0.0001 ETH equivalent
2. **Two Turnstile solves per account** (login + claim)
3. **CSRF token required** from initial page load

## Cost Analysis

| Item | Cost |
|------|------|
| 2Captcha (2 solves) | ~$0.004 |
| Gas for wallet funding | ~$0.001-0.01 |
| Credits earned | 1,000,000 |
| **Net ROI** | Very high |

## Dependencies

```bash
pip install requests eth_account pycryptodome
```
