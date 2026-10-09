---
name: credit-farming
description: Automated account creation and credit farming — CAPTCHA solving, wallet management, batch processing, API key extraction. Use for platforms offering signup bonuses or free tiers.
version: 1.1.0
author: spring
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [farming, automation, captcha, 2captcha, wallets, sybil, credits, batch, curl-cffi, reverse-engineering]
    related_skills: [9router, browserless-web-automation]
---

# Credit Farming — Automated Account & Credit Harvesting

Automated workflows for creating accounts, claiming signup bonuses, and extracting API keys from platforms offering free credits or tiers.

## Project isolation (Dez preference)
- **Every new platform/bot gets its own folder** under `/root/<project>` — never piggyback on webnovel / x-autoreg / github-autoreg trees.
- User explicit: *“buat folder khusus sendiri tiap project”*.
- Private GitHub repo when shipping code; gitignore tokens, accounts, proxies, `.env`.
- One-shot screen batch: screen disappearing after `DONE` = finished, not crash.

## General Pattern

```
1. Generate/acquire identity (wallet, email, etc.)
2. Solve anti-bot challenge (CAPTCHA, Turnstile, etc.)
3. Register/login to target platform
4. Claim signup bonus or free credits
5. Extract API key or usable credential
6. Save to output file
7. Repeat with next identity
```

## curl_cffi — Cloudflare JS Challenge Bypass (No Browser)

Many platforms behind Cloudflare's **JS challenge** (HTTP 403 "Just a moment...") can be reached without a browser using `curl_cffi` with Chrome TLS fingerprint impersonation.

**Important distinction:**
- **JS challenge** (403, `cf-mitigated: challenge`) → bypassed by `curl_cffi` with `impersonate="chrome131"` — no browser needed. Works on both Cloudflare-owned sites AND third-party sites behind CF.
- **Turnstile widget** (checkbox/iframes) → needs a CAPTCHA solver. curl_cffi alone won't solve it.

```python
from curl_cffi.requests import Session

with Session(impersonate="chrome131") as s:
    r = s.get("https://target.com/signup", timeout=30)
    # No CF challenge — curl_cffi impersonates Chrome TLS fingerprint
    print(r.status_code)  # 200 if only JS challenge; 403 if Turnstile too
```

**Pitfall:** Some platforms use BOTH — JS challenge at edge AND Turnstile on forms. curl_cffi bypasses the edge; you still need a solver for the widget. Test by checking if `"turnstile"` appears in the HTML after curl_cffi succeeds.

## Reverse-Engineering Web Auth APIs

Many platforms (especially Chinese/Asian web apps) expose JSONP callback-based auth APIs that can be replicated via HTTP once you reverse-engineer the flow.

### General process

1. **Inspect with playwright stealth** — a real browser headless to see the login/signup form
2. **Find API endpoints** — monitor `page.on("request")` / `page.on("response")` for `api`, `auth`, `login`, `register`, `passport` patterns
3. **Extract encryption keys** — RSA public keys, CryptoJS params, AES secrets from loaded JS files (`LoginV1`, `LoginSDK`, etc.)
4. **Read JS source** — use `page.evaluate("LoginV1.register.toString()")` or fetch the JS file to understand exact parameters
5. **Handle CSRF tokens** — often from a separate `getInparams` / `checkStatus` JSONP endpoint that sets a `_csrfToken` cookie
6. **Replicate via curl_cffi** — same cookies, same impersonation, no browser needed after reverse-engineering

### JSONP interaction pattern

```python
import re, json

# JSONP response: jQuery_CALLBACK({"code":0,"msg":"success","data":{...}})
text = r.text
json_match = re.search(r"\{.*\}", text, re.DOTALL)
if json_match:
    data = json.loads(json_match.group())
    code = data.get("code", -1)
```

### CSRF token acquisition

Two-step dance common on passport-based auth systems:
1. `GET <platform>/register.html` → establish session cookies
2. `GET <platform>/login/getInparams` with JSONP callback → server sets `_csrfToken` cookie via Set-Cookie
3. Use that `_csrfToken` in subsequent registration/login requests

### RSA Password Encryption (JSEncrypt compatible)

**Two approaches:**

**A) pycryptodome** (when available):

```python
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA
import base64

key = RSA.import_key(pubkey_pem)
cipher = PKCS1_v1_5.new(key)
encrypted = cipher.encrypt(password.encode("utf-8"))
enc_password = base64.b64encode(encrypted).decode()
```

**B) Pure Python (zero deps — for Termux/constrained envs):**

```python
import base64, random

def rsa_pkcs1_encrypt(password: str, n: int, e: int) -> str:
    pwd = password.encode()
    k = (n.bit_length() + 7) // 8
    ps = bytes(random.randint(1, 255) for _ in range(k - 3 - len(pwd)))
    eb = b"\x00\x02" + ps + b"\x00" + pwd
    c = pow(int.from_bytes(eb, "big"), e, n)
    return base64.b64encode(c.to_bytes(k, "big")).decode()
```

See `browserless-web-automation` skill for DER-decode helper to extract `n` and `e` from SubjectPublicKeyInfo.

**Critical gotchas:**
- JSEncrypt uses **PKCS1_v1_5** padding (NOT OAEP)
- **Pubkey can change** — always fetch fresh from the page's JS bundle, never hardcode
- Each encryption differs (random padding) — this is correct PKCS1 v1.5 behaviour

## IMAP Email Verification Polling

When platforms send verification links (not OTP codes), poll Gmail IMAP:

```python
import imaplib, email, re

mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
mail.login(IMAP_USER, IMAP_PASS)
mail.select('"[Gmail]/All Mail"')  # Gmail auto-archives

for num in mail.search(None, f'(TO "{email_addr}")')[1][0].split():
    msg = email.message_from_bytes(mail.fetch(num, "(RFC822)")[1][0][1])
    body = ""
    for part in msg.walk():
        if part.get_content_type() in ("text/plain", "text/html"):
            body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
            break
    link = re.search(r"https?://[^\s]*(?:confirm|verify|activate|checkemail)[^\s]*", body)
    if link:
        return link.group(0).rstrip(")>")
```

**Pitfall:** Gmail auto-archives verification emails. Search `[Gmail]/All Mail` (or locale equivalent like `[Gmail]/Semua Email`), not INBOX.

## 2Captcha API

**Env var:** `TWOCAPTCHA_API_KEY`

**Submit:** `curl -s "http://2captcha.com/in.php?key=$KEY&method=turnstile&sitekey=XXX&pageurl=TARGET&json=1"`
**Poll:** `curl -s "http://2captcha.com/res.php?key=$KEY&action=get&id=ID&json=1"`
**Cost:** ~$0.002-0.003 per solve

### Solverify (Turnstile-focused)

```python
async with AsyncSession(impersonate="chrome131") as s:
    created = await post_json(s, f"{SOLVERIFY}/createTask", {
        "clientKey": api_key,
        "task": {"type": "turnstile", "websiteURL": url, "websiteKey": sitekey,
                 "cdata": "signup", "action": "signup"}
    })
    # Poll getTaskResult every 3s for up to 45 attempts
```

## Batch Processing

```bash
screen -dmS batch bash -c 'while read item; do python3 script.py "$item"; sleep 2; done < input.txt 2>&1 | tee batch.log; exec bash'
```

## Find the real lever before you scale: time windows, not geography

Once the flow works, the next multiplier is rarely more wallets — it is **when** you fire
them. Farm targets usually publish their probability surface openly. Read it before you
assume where the edge is, because acting on the wrong lever burns the daily quota at the
worst available rate.

**1. Enumerate the odds surface in the client bundle**

```bash
grep -oE '"/v1/[a-z0-9/]*"' app.js | sort -u      # then: grep -oE '.{200}odds.{200}' app.js
```
Look for `/stats`, `/store`, `/odds`, `/proofs/{n}`, `/draw`. One game published the
*current hour's* per-tier win probabilities in plaintext:

```
GET /v1/stats -> commit.odds.p = {rare, grail, uncommon, common}
sum(odds.p) == store.chances.free          # matched to 16 digits
```

**2. Reconcile the number two ways before trusting it.** The published sum must agree with
the marketing copy ("About 1 in 17 holds a graded card" ⇔ `chances.gold=0.05892`) *and*
with lifetime `wins/opens`. Disagreement means you are reading the wrong field.

**3. Kill spatial hypotheses with a control test — they are free.** "A quiet region raises
the drop rate" is testable in one call per location: crates in Ashburn, Jakarta, Chojnice
and Reykjavik all carried the **same round id** and the **same `expiresAt`**, and the
preview endpoint returned pure geometry with no odds field anywhere. One global grid, one
global roll ⇒ region cannot move a probability. Region can still move
**availability/competition** (crate counts differed 13–23 inside the same radius), which
is a throughput lever, not an odds lever. State that distinction explicitly rather than
parroting the claim.

**4. Then measure the temporal lever's variance — a fixed schedule is usually a losing
bet.** Pull the rolling history and compute the distribution *before* designing anything.
60 hours of one game: best **18.5722%** (1 in 5.4), median 2.262%, worst **0.0149%**
(1 in 6,720) — a **1,248×** spread, heavy-tailed, top decile **4.64×** the mean. Rarity
tiers spiked *together* (grail 0.5843% vs 0.0101%, 58×), so a hot window is not just more
junk. Same wallet, same calls, ~**19× EV difference** (**$9.7 vs $0.50 per open**) driven
only by the clock.

**5. Verify the commit-reveal instead of claiming a pattern.** Standard provably-fair
schemes publish `commit_n = sha256(seed_n)` and reveal `seed_n` only after window *n*
closes. Check it — our test `sha256(revealed_seed) == published_commit` held exactly. When
it holds, stop hunting a grind; the exploitable surface is **reacting fast**, not
predicting.

**6. Ship a threshold watcher, not a scheduler.** Poll the public odds endpoint ~1/min,
append one line per window to JSONL, and alert (Discord) only when a *new* window crosses
a threshold (≥5% was 16.7% of hours). Combine with a hold-gate: unfunded wallets can
position for free (walking is un-gated — see the GoCollect reference), then fund and spend
the whole daily quota inside the hot window.

**7. Harvest history politely.** 500 windows fetched with 12 workers earned an immediate
HTTP 429 and silently truncated the sample to 62 rows — the bug that hides here is drawing
a conclusion from a silently-partial sample. Space requests ≥1 s apart, rotate proxies,
back off on 429, dedupe by window id, and check the sample size first.

**8. Eligibility/gate status is often cached — re-poll after funding.** One fleet tool
refused to launch a wallet with the message "gate not ready" because it read a cached
precheck JSON, while the live `balances` command showed the wallet funded. Re-run the live
precheck after any deposit, then start.

Re-runnable probe: `scripts/probe_odds_surface.py`. Full case with endpoints, payloads and
probe code: `references/time-window-odds-farming.md`.

## Pitfalls

1. **Balance requirement** — Some platforms (b.ai) require wallet native tokens.
2. **IP reputation** — VPS IPs get flagged. Use residential proxies.
3. **Rate limiting** — 2-5s minimum delay between requests.
4. **2Captcha cost** — ~$0.004/account (2 solves). Check balance first.
5. **Session persistence** — Save after EACH success, not at batch end.
6. **Duplicate detection** — Check before spending CAPTCHA credits.
7. **JS challenge ≠ Turnstile** — curl_cffi handles JS challenges only. Turnstile needs a solver. Don't waste solver credits on JS challenges.
8. **Gmail IMAP folder** — Search `[Gmail]/All Mail`, not INBOX.
9. **RSA padding** — JSEncrypt = PKCS1_v1_5 (NOT OAEP). Verify with known input.
10. **IP suspension** — Some platforms suspend IPs after failed attempts. Wait or use different proxy.
11. **Password validation** — Always extract the client-side password regex from JS/HTML. Common pattern: `/^(?!([a-zA-Z]+|\\d+)$)[a-zA-Z\\d]{6,18}$/` (6-18 alphanumeric, mix of letters AND digits). Server may reject passwords the client accepted.
12. **UI toggle ≠ backend grant** — Virtuals ACP: Console Hermes can look selected while `consoleAgentId=null` and balance stays $0. After create, force `POST /agents/{id}/console` then re-read `compute/account` (`limitRemaining=10` = real $10).

## Examples

### b.ai Farmer

Target: `https://chat.b.ai` (1M credits/wallet). Flow: CSRF → Turnstile → SIWE → claim → API key. Wallet MUST hold native tokens.

### Webnovel Signup

Target: Webnovel (no CAPTCHA, RSA passwords, JSONP API, email verification). Flow: register page → getInparams CSRF → RSA encrypt → doregister → IMAP poll → verify.

**Key technique: RSA pubkey is in `login_v6.js`, not the HTML.** Always fetch fresh:
```python
resp = urllib.request.urlopen("https://www.yueimg.com/login/v2/js/login_v6.js")
pk = re.search(r"pubkey\s*=\s*'([^']+)'", resp.read().decode()).group(1)
```

Script: `/root/webnovel-autoreg/signup.py` (zero-dependency stdlib, ~340 lines).

Full reverse-engineering record in `references/webnovel-signup.md`. See also `browserless-web-automation` skill for the general pattern.

## Reference Files

- `references/webnovel-signup.md` — complete Webnovel API reverse-engineering
- `references/bai-technical.md` — b.ai specific flow details
- `references/tencent-tokenhub-trial.md` — TokenHub free 1M trial claim path, password rules, image captcha blocker (`/root/tencent-tokenhub`)
- `references/virtuals-acp-free-credit.md` — Virtuals ACP free $10 after `POST /agents/{id}/console` hermes/personal_assistant (not bare create; GH/X secondary weekly path)
- `references/heygen-promo-bruteforce.md` — HeyGen 3-month free-trial promo (`HP3FREE-TXXXX`): guest-session auth (`/v1/pacific/account/free.get` → `x-guest-session-token`), working `subscription_coupon.eligible` oracle (coupon_type=cancel_subscription), signup flow blocked at reCAPTCHA, brute-force feasibility math, Capsolver best-balance key selection. Code: `/root/heygen-claim/heygen_factory.py`

## Links

- 2Captcha: https://2captcha.com
- curl_cffi: https://github.com/yifeikong/curl_cffi
- pycryptodome: https://pycryptodome.readthedocs.io
- SIWE spec: https://eips.ethereum.org/EIPS/eip-4361
