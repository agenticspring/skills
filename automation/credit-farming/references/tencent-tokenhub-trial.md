# Tencent Cloud TokenHub free trial (2026-07)

Project folder (mandatory isolation): **`/root/tencent-tokenhub`**  
Do not dump this into webnovel/x/github trees.

## Product
- TokenHub = multi-model LLM gateway (DeepSeek/GLM/Kimi/MiniMax/Hunyuan)
- OpenAI-compatible style API after account + API key
- Promo landing: `https://www.tencentcloud.com/act/pro/tokenhub`
- Docs claim path: `https://www.tencentcloud.com/document/product/1300/80423`

## Free trial rules (official)
- **Root/primary account**, first TokenHub activation
- **~1M free tokens per language model**, **90 days** from claim
- Claim once per account per model; non-transferable
- Claim methods:
  1. Model Gallery → **New User Free Trial** → select models → Claim Now
  2. Auto-claim on **first API call** to eligible model
- After free exhausted: service **stops** unless post-paid enabled
- **CC not required** in free-trial docs to claim; payment needed only for post-paid continuity
- Campaign noted through **2026-12-31** (verify page)

## Register form (intl live)
- URL: `https://www.tencentcloud.com/account/register`
- Choose **Individual** (not Enterprise)
- Country sets tax/region (sticky after pick)
- Password rules:
  - 8–20 chars
  - letter + number + special `!@#$%^&*`
  - no spaces; not identical to email
- Shared Webnovel `PASSWORD` often **fails** (no special char) → generate compliant password
- Custom email domain (e.g. `@<REDACTED>`) accepted in form if IMAP can receive mail
- Send code triggers **Tencent Safety Check** image captcha (e.g. “Select the image that best matches ‘Fish’”)
- Captcha stack: `captchaapi.tencentcloudcs.com`, app id seen **`188959458`**, `TCaptcha-global.js`

## Proven attempt notes
- Playwright scaffold: `/root/tencent-tokenhub/register_claim.py`
- IMAP from `/root/cf-tuyul/.env` (same as other bots)
- E2E blocked at captcha → OTP never sent → claim not reached
- Next: solve image captcha (headed/manual or specialized solver), then IMAP OTP, then TokenHub claim

## Ops checklist
1. Work only under `/root/tencent-tokenhub`
2. Load env: local `.env` + cf-tuyul IMAP + hermes captcha keys
3. Use compliant password generator
4. Individual + terms + DOB if asked
5. Expect captcha on Send code before mail
6. After login: console TokenHub models → claim free trial
7. Keep post-paid OFF until intentional spend

## Do not
- Mix accounts/tokens into webnovel or api-key-leak trees
- Claim “trial claimed” without logged-in TokenHub evidence
- Assume free trial needs CC (docs say otherwise)