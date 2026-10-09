---
name: captcha-service-apis
description: "Check captcha service API balances, IP block status, and test keys across 15 providers (2captcha, rucaptcha, anti-captcha, capmonster, capsolver, uCaptcha, Solvex, CaptchaAI, SolveCaptcha, NextCaptcha)."
version: 1.1.0
author: spring
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [captcha, 2captcha, anti-captcha, automation, api, balance-check, ucaptcha, solvecaptcha, nextcaptcha]
    related_skills: []
---

# Captcha Service APIs

Check captcha provider API key validity, balance, and IP block status. Useful for verifying harvested keys, monitoring spend, and rotating between providers.

## Supported Providers

| Provider | Auth Method | Balance Endpoint | Env Var |
|----------|------------|-----------------|---------|
| 2captcha | API key (query param) | GET `res.php?key=X&action=getbalance` | `TWOCAPTCHA_API_KEY` |
| rucaptcha | API key (query param) | Same as 2captcha (identical API) | `RUCAPTCHA_API_KEY` |
| anti-captcha | Client key (JSON body) | POST `api.anti-captcha.com/getBalance` | `ANTICAPTCHA_API_KEY` |
| capmonster | API key (JSON body) | POST `api.capmonster.cloud/getBalance` | `CAPMONSTER_API_KEY` |
| capsolver | API key (JSON body) | POST `api.capsolver.com/getBalance` | `CAPSOLVER_API_KEY` |
| uCaptcha | Client key (JSON body) | POST `api.ucaptcha.net/getBalance` | `UCAPTCHA_API_KEY` |
| Solvex | Client key (JSON body) | POST `api.solvex.run/getBalance` | `SOLVEX_API_KEY` |
| CaptchaAI | API key (query param) | GET `ocr.captchaai.com/res.php?key=X&action=getbalance&json=1` | `CAPTCHAAI_API_KEY` |
| SolveCaptcha | API key (query param) | GET `api.solvecaptcha.com/res.php?key=X&action=getbalance&json=1` | `SOLVECAPTCHA_API_KEY` |
| NextCaptcha | Client key (JSON body) | POST `api.nextcaptcha.com/getBalance` | `NEXTCAPTCHA_API_KEY` |

> Additional providers (NopeCHA, ImageTyperz, EndCaptcha) and official documentation links are in `references/additional-providers-leak-monitoring.md`.

## Quick Check — Single Key

### 2captcha

```bash
curl -s "https://2captcha.com/res.php?key=YOUR_KEY&action=getbalance"
# Returns: float (balance) or ERROR_* string
```

### anti-captcha

```bash
curl -s --max-time 15 -X POST "https://api.anti-captcha.com/getBalance" \
  -H "Content-Type: application/json" \
  -d '{"clientKey": "YOUR_KEY"}'
# Returns: {"balance": 1.23} or {"errorId": 1, "errorDescription": "..."}
```

### capmonster

```bash
curl -s --max-time 15 -X POST "https://api.capmonster.cloud/getBalance" \
  -H "Content-Type: application/json" \
  -d '{"clientKey": "YOUR_KEY"}'
```

### capsolver

```bash
curl -s --max-time 15 -X POST "https://api.capsolver.com/getBalance" \
  -H "Content-Type: application/json" \
  -d '{"clientKey": "YOUR_KEY"}'
```

### uCaptcha

```bash
curl -s --max-time 15 -X POST "https://api.ucaptcha.net/getBalance" \
  -H "Content-Type: application/json" \
  -d '{"clientKey": "YOUR_KEY"}'
```

### Solvex

```bash
curl -s --max-time 15 -X POST "https://api.solvex.run/getBalance" \
  -H "Content-Type: application/json" \
  -d '{"clientKey": "YOUR_KEY"}'
```

### CaptchaAI

```bash
curl -s "https://ocr.captchaai.com/res.php?key=YOUR_KEY&action=getbalance&json=1"
# Returns: {"status":1,"balance":1.23} or {"status":0}
```

### SolveCaptcha

```bash
curl -s "https://api.solvecaptcha.com/res.php?key=YOUR_KEY&action=getbalance&json=1"
# Returns: {"status":1,"balance":1.23} or {"status":0}
```

### NextCaptcha

```bash
curl -s --max-time 15 -X POST "https://api.nextcaptcha.com/getBalance" \
  -H "Content-Type: application/json" \
  -d '{"clientKey": "YOUR_KEY"}"
```

## IP Block Detection

> See `references/ip-block-detection.md` for detailed provider-by-provider patterns and timeout-vs-block diagnostics.

### 2captcha

If IP is blocked, balance check returns `ERROR_IP_NOT_ALLOWED` or `ERROR_IP_BLOCKED`. A valid response (even negative balance) means IP is NOT blocked.

Quick IP block test:
```bash
# This returns ERROR_WRONG_CAPTCHA_ID if IP is OK (just invalid ID)
# Returns ERROR_IP_* if IP is blocked
curl -s "https://2captcha.com/res.php?key=YOUR_KEY&action=reportbad&id=1"
```

### anti-captcha / capmonster / capsolver

Check `errorId` in response. If `errorId > 0`, read `errorDescription` for IP block clues.

## Batch Check Script

Use `execute_code` to check multiple keys efficiently:

```python
from hermes_tools import terminal
import json

providers = {
    "2captcha": {
        "keys": ["key1", "key2"],
        "check": lambda k: terminal(f'curl -s "https://2captcha.com/res.php?key={k}&action=getbalance"')
    },
    "anti-captcha": {
        "keys": ["key3"],
        "check": lambda k: terminal(f'curl -s --max-time 15 -X POST "https://api.anti-captcha.com/getBalance" -H "Content-Type: application/json" -d \'{{"clientKey": "{k}"}}\'')
    }
}

for name, cfg in providers.items():
    print(f"\n=== {name.upper()} ===")
    for key in cfg["keys"]:
        r = cfg["check"](key)
        raw = r.get("output", "").strip()
        # Parse based on provider
        print(f"  {key[:12]}... | Raw: {raw}")
```

## Operational workflow for leak-monitor integrations

1. Keep provider metadata separate from provider execution: each provider entry needs a documented format, query context, and validator contract.
2. Classify validator results explicitly as `active`, `valid_empty`, `invalid_or_revoked`, `rate_limited_or_blocked`, or `indeterminate`; a timeout must never be reported as a dead credential.
3. For public-leak monitoring, only run active validation when the credential is owned by the operator or the engagement explicitly authorizes testing. Otherwise emit a passive exposure alert with source, masked value, fingerprint, and `NOT_VALIDATED` status.
4. Discord alerts should distinguish `ACTIVE` from `PUBLIC_EXPOSURE_UNVERIFIED`; deduplicate by provider plus normalized key/fingerprint before writing `found/{provider}.txt` or sending a webhook.
5. When deploying the monitor, pass a dedicated token file with `--tokens`; explicitly unset inherited `GH_TOKEN`, `GITHUB_TOKEN`, and `GH_TOKENS`, and verify the child process environment. Never assume `gh auth token` is the intended bot credential.
6. A webhook URL is a secret. Load it into the screen/service environment without printing it, verify only presence and HTTP delivery status, and rotate it if it was pasted into a public/shared conversation.

Provider research and the passive-detection matrix are in `references/additional-providers-leak-monitoring.md`.

## Pitfalls

1. **anti-captcha/capmonster/capsolver may timeout** — These APIs use POST with JSON body. If `curl` times out (exit code 28), the server IP is likely blocked by the provider or the provider is down. From VPS/dedi IPs, anti-captcha is especially prone to timeouts. Always set `--max-time 15`. If all three timeout but 2captcha works, the server IP is likely blocked by those providers — use 2captcha/rucaptcha instead.

2. **2captcha returns negative balance** — Negative balance means the key is drained. Still valid (IP not blocked), just no funds. Exclude from usable keys.

3. **Commented-out .env lines** — When saving keys to `~/.hermes/.env`, check if the key line exists but is commented (`# KEY=...`). Use `grep -q` with both patterns:
   ```bash
   grep -q "^#\?TWOCAPTCHA_API_KEY=" ~/.hermes/.env && \
     sed -i 's|^#\?TWOCAPTCHA_API_KEY=.*|TWOCAPTCHA_API_KEY=newvalue|' ~/.hermes/.env || \
     echo "TWOCAPTCHA_API_KEY=newvalue" >> ~/.hermes/.env
   ```

4. **Rate limits** — 2captcha allows ~3 req/sec. Batch checks should include a small delay between keys if checking many.

5. **Key format differences** — 2captcha keys are 32-char hex. anti-captcha/capmonster/capsolver keys are also hex but may have different lengths. Don't assume a single format.

6. **capsolver `ERROR_KEY_DENIED_ACCESS` (Code 41)** — Response `{"errorCode":"ERROR_KEY_DENIED_ACCESS","errorDescription":"account authorization is invalid: Code(41)","errorId":1}` means the key is **revoked/expired/invalid**, not IP-blocked. Distinct from a valid-but-empty `{"balance":0.0,"errorId":0}`. Treat Code 41 as a dead key (exclude). A key returning `errorId:0` with a real balance is live even if the balance is $0.00.

7. **2captcha and rucaptcha share the same backend API** — both use `res.php?key=X&action=getbalance` and the same balance namespace. A key that works on `2captcha.com` will show the **same balance** on `rucaptcha.com` (and vice-versa) — they are the same account pool. Don't count them as two separate balances; check one, not both, to avoid double-counting. Negative balance (`-0.00043`) on either = drained.

8. **New provider timeouts (uCaptcha, Solvex, NextCaptcha)** — These use POST with JSON body from Russian/EU infrastructure. From US VPS IPs they may timeout (exit code 28). Treat as IP-blocked, not a dead key. CaptchaAI and SolveCaptcha use the same GET-param format as 2captcha and are usually more reliable from any IP.

8. **New provider timeouts (uCaptcha, Solvex, NextCaptcha)** — Same as anti-captcha/capmonster: these use POST with JSON body from Russian/EU infrastructure. From US VPS IPs they may timeout (exit code 28). Treat as IP-blocked, not dead key. CaptchaAI and SolveCaptcha use the same GET-param format as 2captcha and are usually more reliable from any IP.

## Environment Variables

Store active keys in `~/.hermes/.env`:
```
TWOCAPTCHA_API_KEY=your_key_here
ANTICAPTCHA_API_KEY=your_key_here
CAPMONSTER_API_KEY=your_key_here
CAPSOLVER_API_KEY=your_key_here
UCAPTCHA_API_KEY=your_key_here
SOLVEX_API_KEY=your_key_here
CAPTCHAAI_API_KEY=your_key_here
SOLVECAPTCHA_API_KEY=your_key_here
NEXTCAPTCHA_API_KEY=your_key_here
```

## Verification

After saving a key, always verify:
```bash
source ~/.hermes/.env
curl -s "https://2captcha.com/res.php?key=$TWOCAPTCHA_API_KEY&action=getbalance"
```

## Reporting a key inventory — and proving it is live

The common ask is not "check one key" but *"which of our keys still have balance, and show me the
key and provider."* Two things go wrong: double-counting, and reporting numbers the user has no
reason to believe.

### Dedupe by key VALUE, never by env-var name

A batch of keys is usually stored as a numbered family (`TWOCAPTCHA_KEY_1..14`,
`TWOCAPTCHA_API_KEY_1..N`, `CAPSOLVER_API_KEY[_2/_3]`). The same key is routinely saved under more
than one name — in the worked case `TWOCAPTCHA_KEY_4` and `TWOCAPTCHA_API_KEY_2` were both
`54081d9b…`. Keep a `seen = set()` of the **key string** and skip repeats, or the total is inflated
and the user is told they hold the same money twice.

### Prove liveness when challenged — do not re-assert the number

*"Itu beneran kau hit ke API pas cek balance nya gak?"* is a fair challenge. It is not answered
with prose. Re-run and show evidence:

1. **Raw `curl` output, unparsed** — the provider's own body, not your formatted table:
   `{"errorId":0,"balance":98.26203}` or `4.97841`.
2. **HTTP response headers** — `server:` and `date:` from the provider prove the response is theirs
   and current, not cached or hardcoded:
   ```
   HTTP/2 200
   server: nginx/1.18.0 (Ubuntu)
   date: Wed, 30 Sep 2026 06:57:08 GMT
   ```
3. **Show the number MOVE across samples.** The strongest proof is a value that changes while you
   watch. In the worked case anti-captcha read `98.26603 → 98.26203 → 98.26003` over ~40 s. Say it
   plainly: a memorised figure cannot drift.
4. Always print the **timestamp of the check** next to the results.

### Balance drift is a finding, not noise

Sampling the same key a few times is a free spend-monitor. In the worked case several keys fell
together (anti-captcha `-0.004`, two 2captcha keys `-0.00145` each — about the cost of one
reCAPTCHA solve), which means **something is consuming credit right now**. Before blaming the
user's own host, check `crontab -l`, `systemctl --user list-units`,
`ps aux | grep -iE "captcha|solve"` and `screen -ls`. If nothing local is solving, say so and name
the real candidates: the keys are **shared or resold** (numbered key families are commonly bought in
bulk), or the provider is settling pending charges. Recommend IP-whitelisting the key to the VPS so
an external holder cannot drain it.

### Output shape to give

When asked for "list aja — api, balance, provider", answer with a flat, copy-pasteable block — one
row per key, no table, no commentary. Funded keys first, drained keys in a clearly separated tail,
then one line with the deduped total and any duplicate-key note:

```
# api_key | balance | provider   (live 2026-09-30 07:00:16 UTC)

<TWOCAPTCHA_KEY_5_REDACTED> | $4.97841  | 2captcha
<ANTICAPTCHA_API_KEY_REDACTED> | $98.25803 | anti-captcha
<CAPSOLVER_API_KEY_3_REDACTED> | $8.231 | capsolver

# habis / kosong
<TWOCAPTCHA_API_KEY_REDACTED> | $-0.00126 | 2captcha
```

Re-runnable: `scripts/captcha_balance_report.sh` (prints exactly that shape from `~/.hermes/.env`).

### Inventory pitfalls

- **`NextCaptcha` returns a generic message for unknown keys.** `getBalance` answered
  `"your account balance is insufficient to complete this task"` for **every** key tested, including
  keys verified live elsewhere. That is a catch-all, not a validity signal — never report a
  NextCaptcha key as "valid but empty" on that string alone. Mark it `indeterminate` and say so.
- **An empty body is a block, not a zero.** `capmonster` returned nothing at all from the worked VPS
  IP. Report `timeout/blocked`, never `$0.00`.
- **Negative ≠ broken.** `-0.00067`…`-0.00146` on 2captcha means the key is live but drained (which
  also proves the IP is not blocked). Classify as `valid_empty`, distinct from `invalid_or_revoked`,
  and offer them for `.env` cleanup rather than calling them dead.
- **Keys printed into a chat log are exposed.** After displaying a key in a shared or persistent
  channel, say so once and recommend rotating the ones holding meaningful balance.

Full worked transcript, provider-by-provider responses and the drift measurements:
`references/key-inventory-and-balance-reporting.md`.

## Identifying Unknown Keys

When you have a key of unknown provider, test all providers in parallel. Most captcha keys are 32-char hex, so format alone doesn't identify the provider. Use `execute_code` to test each:

```python
from hermes_tools import terminal
import json

unknown_key = "your_key_here"

# Test 2captcha/rucaptcha (same API)
r1 = terminal(f'curl -s "https://2captcha.com/res.php?key={unknown_key}&action=getbalance"')
raw1 = r1["output"].strip()
if "ERROR" not in raw1:
    print(f"→ 2captcha/rucaptcha | Balance: ${raw1}")

# Test anti-captcha
r2 = terminal(f'curl -s --max-time 15 -X POST "https://api.anti-captcha.com/getBalance" -H "Content-Type: application/json" -d \'{{"clientKey": "{unknown_key}"}}\'')
try:
    d2 = json.loads(r2["output"])
    if d2.get("errorId", 1) == 0:
        print(f"→ anti-captcha | Balance: ${d2['balance']}")
except: pass

# Test capmonster
r3 = terminal(f'curl -s --max-time 15 -X POST "https://api.capmonster.cloud/getBalance" -H "Content-Type: application/json" -d \'{{"clientKey": "{unknown_key}"}}\'')
try:
    d3 = json.loads(r3["output"])
    if d3.get("errorId", 1) == 0:
        print(f"→ capmonster | Balance: ${d3['balance']}")
except: pass

# Test capsolver
r4 = terminal(f'curl -s --max-time 15 -X POST "https://api.capsolver.com/getBalance" -H "Content-Type: application/json" -d \'{{"clientKey": "{unknown_key}"}}\'')
try:
    d4 = json.loads(r4["output"])
    if d4.get("errorId", 1) == 0:
        print(f"→ capsolver | Balance: ${d4['balance']}")
except: pass

# Test uCaptcha
r5 = terminal(f'curl -s --max-time 15 -X POST "https://api.ucaptcha.net/getBalance" -H "Content-Type: application/json" -d \'{{"clientKey": "{unknown_key}"}}\'')
try:
    d5 = json.loads(r5["output"])
    if d5.get("errorId", 1) == 0:
        print(f"→ uCaptcha | Balance: ${d5['balance']}")
except: pass

# Test Solvex
r6 = terminal(f'curl -s --max-time 15 -X POST "https://api.solvex.run/getBalance" -H "Content-Type: application/json" -d \'{{"clientKey": "{unknown_key}"}}\'')
try:
    d6 = json.loads(r6["output"])
    if d6.get("errorId", 1) == 0:
        print(f"→ Solvex | Balance: ${d6['balance']}")
except: pass

# Test CaptchaAI
r7 = terminal(f'curl -s "https://ocr.captchaai.com/res.php?key={unknown_key}&action=getbalance&json=1"')
try:
    d7 = json.loads(r7["output"])
    if d7.get("status") == 1:
        print(f"→ CaptchaAI | Balance: ${d7.get('balance', 0)}")
except: pass

# Test SolveCaptcha
r8 = terminal(f'curl -s "https://api.solvecaptcha.com/res.php?key={unknown_key}&action=getbalance&json=1"')
try:
    d8 = json.loads(r8["output"])
    if d8.get("status") == 1:
        print(f"→ SolveCaptcha | Balance: ${d8.get('balance', 0)}")
except: pass

# Test NextCaptcha
r9 = terminal(f'curl -s --max-time 15 -X POST "https://api.nextcaptcha.com/getBalance" -H "Content-Type: application/json" -d \'{{"clientKey": "{unknown_key}"}}\'')
try:
    d9 = json.loads(r9["output"])
    if d9.get("errorId", 1) == 0:
        print(f"→ NextCaptcha | Balance: ${d9['balance']}")
except: pass
```
