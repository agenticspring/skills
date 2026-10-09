---
name: tencent-cloud-tokenhub
description: Register Tencent Cloud accounts and claim TokenHub free LLM trial (1M tokens) — browserless HTTP preferred, TCaptcha TenDI, IMAP catch-all, skip-CC free tier rules.
version: 1.0.0
---

# Tencent Cloud TokenHub (free trial / register)

Use when user asks about **Tencent Cloud TokenHub**, free 1M tokens, `tencentcloud.com/act/pro/tokenhub`, or automating Tencent intl account signup + model free trial claim.

## Project isolation (Dez default)
- **Own folder only:** `/root/tencent-tokenhub`
- Do **not** mix into webnovel / github / x trees
- Secrets: local `.env` gitignored; IMAP/DOMAIN from `/root/cf-tuyul/.env` + product envs
- Prefer **browserless** (like Webnovel/GitHub) when user says “tanpa browser”

## Product facts (docs + live)
| Item | Value |
|---|---|
| Promo | New **primary/root** account free trial package through **2026-12-31** |
| Quota | Often **1M tokens per language model**, **90 days** from claim |
| Claim | Model Gallery **New User Free Trial** or auto on first eligible API call |
| CC for free claim | **Not required** in official free-trial docs |
| After free | post-paid off → stop; post-paid on → pay-per-token |
| Email domain | Custom (`<REDACTED>`) accepted on form — not the main blocker |
| Password rules (live form) | 8–20; letter + number + special `!@#$%^&*`; no spaces; ≠ email |

Shared Webnovel `PASSWORD` may **fail** Tencent rules if no special char — generate compliant password for this product.

## Preferred architecture: browserless first
User preference: same class as Webnovel/GitHub (no Playwright unless stuck).

```text
curl_cffi session (chrome124)
  → GET /account/register (cookies)
  → checkAccountExistReg / checkBlackResource
  → 2captcha TencentTask + Webshare proxy → ticket/randstr
  → sendMailCode / sendMailCodeV2 (+ captcha fields)
  → IMAP OTP (cf-tuyul)
  → registerAccountV2 / completeRegisterV2
  → TokenHub claim (console session / gallery — still partial)
```

### Modules
| File | Role |
|---|---|
| `register_http.py` | **Browserless CLI** (preferred) |
| `tencent_captcha.py` | 2captcha proxy-first + CapMonster TenDI |
| `register_claim.py` | Playwright fallback |
| `proxy.txt` | Webshare-class proxies |
| `data/last_http_result.json` | last browserless result |

```bash
cd /root/tencent-tokenhub
.venv/bin/python register_http.py          # browserless
.venv/bin/python register_claim.py         # browser fallback
```

## Register AJAX map (intl)
Base: `POST https://www.tencentcloud.com/en/account/register/ajax?action=…`

| Action | Notes |
|---|---|
| `checkAccountExistReg` | `{email}` → `data.exist` |
| `checkBlackResource` | risk hit |
| `sendMailCode` / `sendMailCodeV2` | OTP send; needs captcha fields |
| `registerAccountV2` | create after OTP |
| `completeRegisterV2` / `completeUserInfoV2` | completion |
| `getRegisterStep` / `getUserRiskLevel` | state |

Captcha body fields seen in sibling login ajax:
`captchaAppId` / `appId`, `ticket`, `randstr`.

## Live E2E status (2026-07-21)
| Step | Browserless |
|---|---|
| Precheck exist/black | ✅ |
| Captcha solve (proxy) | ✅ intermittent |
| `sendMailCodeV2` | ⚠️ often **`code=51`** → OTP never arrives |
| IMAP | ❌ when send fails |
| Full account + TokenHub claim | ❌ not completed |

**`code=51`:** request accepted enough for JSON response, but mail not proven sent. Suspect incomplete payload and/or ticket not bound to same cookie session as solver worker. Do not claim free trial success.

## Ops status (Dez, 2026-07-22): **STOPPED / idle**
User conclusion: not a good bot-farm path — OTP/phone/card gates + flaky TCaptcha.
Keep `/root/tencent-tokenhub` as archive; **do not auto-resume** reverse/register/claim unless user explicitly restarts this project. Prefer other LLM credit sources when asked generically.

## Captcha rules (must)
1. appId **only** from captcha endpoints (`cap_union_prehandle?aid=188959458`)
2. Never parse rumt `aid=00110011-…` as appId
3. Prefer **`TencentTask` + proxy** over proxyless
4. Rank 2captcha keys by live balance; skip negative/zero
5. Solver input is **appId+URL**, not a user-built captcha token — see `captcha-manager/references/tencent-tcaptcha.md`
6. On user “salah kirim token?”: answer with the protocol table above

## Free trial claim (after real login)
1. Activate TokenHub console
2. Model Gallery → **New User Free Trial** → select models → Claim Now  
   **or** first API call auto-claims eligible models
3. Prefer claiming only models you will use within 90 days
4. Keep post-paid **off** until ready to spend

## Pitfalls
- Treating TokenHub as “no captcha free API key” — signup has **TCaptcha**
- Using Playwright forever after user asked browserless like Webnovel/GH
- Burning solvers before form fields/password rules are valid
- Assuming custom domain is blocked (Gmail/Outlook same gates on other products; here form accepts domain)
- Claiming trial without a completed root account
- Multi-account abuse may violate Tencent ToS — only automate when user owns the strategy
- Probe payload blasts can get session/tool blocked — prefer **narrow** payload experiments after captcha solve

## References
- `references/browserless-register.md` — HTTP flow, code=51, endpoints
- `references/free-trial-claim.md` — official free package rules
- Captcha deep dive: `captcha-manager` → `references/tencent-tcaptcha.md`
