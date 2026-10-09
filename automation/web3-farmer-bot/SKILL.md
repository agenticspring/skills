---
name: web3-farmer-bot
description: Patterns for building Web3 airdrop/bonus farmer bots — SIWE auth, Turnstile solving, CryptoJS encryption, session management, batch processing. Reference for building similar bots to b.ai farmer.
version: 1.0.0
author: spring
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Web3, Farmer, Bot, SIWE, Turnstile, 2Captcha, Airdrop, Automation]
    related_skills: [9router]
---

# Web3 Farmer Bot Patterns

## Core Architecture

Every Web3 farmer bot follows this pattern:

```
1. Session Setup (cookies, CSRF, headers)
2. Captcha Solving (Turnstile/reCAPTCHA/hCaptcha)
3. Authentication (SIWE, OAuth, wallet connect)
4. Validation Check (already claimed? eligible?)
5. Action Execution (claim, mint, register)
6. Key/Asset Extraction (API key, NFT, token)
7. Output Storage (file, database, webhook)
```

## Key Components

### 1. Session Management

```python
import requests

s = requests.Session()
s.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
})

# Get CSRF token from cookies
s.get(f"{BASE}/chat")
csrf_cookie = s.cookies.get("__Host-authjs.csrf-token", "")
csrf_token = csrf_cookie.split("%7C")[0] if "%7C" in csrf_cookie else csrf_cookie
```

**Pitfalls:**
- Always use `requests.Session()` for cookie persistence
- CSRF tokens often have format `token|hash` — split on `%7C`
- Some sites use `__Host-` prefix cookies (secure, same-origin only)

### 2. Cloudflare Turnstile Solving

```python
TWOCAPTCHA_KEY = "your_key"
TURNSTILE_SITEKEY = "0x4AAAAAADKhTSXIozuHjOoF"  # from page source
PAGE_URL = "https://target.com/page"

def solve_turnstile():
    # Submit to 2Captcha
    r = requests.get("http://2captcha.com/in.php", params={
        "key": TWOCAPTCHA_KEY, "method": "turnstile",
        "sitekey": TURNSTILE_SITEKEY, "pageurl": PAGE_URL, "json": 1,
    })
    data = r.json()
    if data.get("status") != 1:
        return None
    req_id = data["request"]
    
    # Poll for result (max 90 seconds)
    for i in range(30):
        time.sleep(3)
        r2 = requests.get("http://2captcha.com/res.php", params={
            "key": TWOCAPTCHA_KEY, "action": "get", "id": req_id, "json": 1,
        })
        d2 = r2.json()
        if d2.get("status") == 1:
            return d2["request"]  # token
        elif d2.get("request") == "CAPCHA_NOT_READY":
            continue
        else:
            return None
    return None
```

**How to find sitekey:**
- Search page source for `turnstile` or `sitekey`
- Look for `data-sitekey` attribute on `<div class="cf-turnstile">`
- Or in JavaScript: `new turnstile.Widget("0x4AAAAA...")`
- Or in network requests to `challenges.cloudflare.com`

**Cost:** ~$0.002 per solve

### 3. SIWE (Sign In With Ethereum)

```python
from eth_account import Account
from eth_account.messages import encode_defunct
import datetime

def sign_siwe_message(pk_hex, addr):
    """Generate SIWE message + signature."""
    nonce = "RANDOM" + str(int(time.time() * 1000))
    expires = (datetime.datetime.now(datetime.timezone.utc) + 
               datetime.timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    
    msg = f"""Welcome to App!
https://app.com wants you to sign in with your account:
{addr}

Chain ID: 0x1
Expiration Time: {expires}
Nonce: {nonce}"""
    
    sig = "0x" + Account.sign_message(
        encode_defunct(text=msg), pk_hex
    ).signature.hex()
    
    return msg, sig
```

**SIWE Message Format:**
```
{domain} wants you to sign in with your Ethereum account:
{address}

{statement}

URI: {uri}
Version: 1
Chain ID: {chain_id}
Nonce: {nonce}
Issued At: {issued_at}
Expiration Time: {expires}
```

**Pitfalls:**
- Message format varies per app — check actual login request
- Some apps use EIP-4361 strict format, others are custom
- Chain ID can be 0x1 (ETH), 0x38 (BSC), 0x89 (Polygon), etc.
- Nonce format varies — some use timestamp, some random, some prefixed

### 4. CryptoJS AES Encryption (OpenSSL Compatible)

```python
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import hashlib, os, base64

def crypto_js_encrypt(data, passphrase):
    """Replicate CryptoJS.AES.encrypt(data, passphrase).toString()
    
    Format: base64("Salted__" + salt + ciphertext)
    Key derivation: EVP_BytesToKey (MD5-based)
    """
    salt = os.urandom(8)
    
    # EVP_BytesToKey key derivation
    key_material = passphrase.encode() + salt
    hashed = hashlib.md5(key_material).digest()
    key = hashed
    while len(key) < 48:
        hashed = hashlib.md5(hashed + passphrase.encode() + salt).digest()
        key += hashed
    
    aes_key = key[:32]  # 256-bit key
    iv = key[32:48]     # 128-bit IV
    
    cipher = AES.new(aes_key, AES.MODE_CBC, iv)
    ciphertext = cipher.encrypt(pad(data.encode(), AES.block_size))
    
    result = b"Salted__" + salt + ciphertext
    return base64.b64encode(result).decode()
```

**Why this is needed:**
- Many Web3 apps use CryptoJS on frontend
- CryptoJS uses OpenSSL-compatible format: `Salted__` + 8-byte salt + ciphertext
- Key derivation: `EVP_BytesToKey` (repeated MD5)
- Algorithm: AES-256-CBC with PKCS7 padding

### 5. Wallet Generation & Management

```python
from eth_account import Account

# Generate new wallet
acct = Account.create()
private_key = acct.key.hex()
address = acct.address

# Load from private key
acct = Account.from_key("0x" + private_key_hex)
address = acct.address

# Sign message
from eth_account.messages import encode_defunct
msg = encode_defunct(text="Hello")
sig = Account.sign_message(msg, private_key)
```

### 6. Batch Processing Pattern

```python
def process_wallets(wallet_file, output_file, captcha_key):
    """Process multiple wallets with dedup and progress tracking."""
    wallets = read_wallets(wallet_file)
    results = {"success": 0, "failed": 0, "skipped": 0}
    
    for i, pk in enumerate(wallets):
        addr = get_address(pk)
        
        # Dedup: skip if already processed
        if addr in get_processed_addresses(output_file):
            results["skipped"] += 1
            continue
        
        # Process
        try:
            result = farm(pk, captcha_key)
            if result and result.get("api_key"):
                save_result(output_file, result)
                results["success"] += 1
            else:
                results["failed"] += 1
        except Exception as e:
            print(f"Error: {e}")
            results["failed"] += 1
        
        # Progress update
        if (i + 1) % 10 == 0:
            print(f"Progress: {i+1}/{len(wallets)} {results}")
        
        # Rate limit delay
        time.sleep(2)
```

## Common Anti-Bot Bypasses

### Turnstile (Cloudflare)
- Use 2Captcha/AntiCaptcha with `method: "turnstile"`
- Need `sitekey` + `pageurl`
- Cost: ~$0.002/solve
- Alternative: `hcaptcha` method for hCaptcha

### reCAPTCHA v2/v3
- 2Captcha: `method: "userrecaptcha"` + `googlekey` + `pageurl`
- v3 needs `action` + `min_score` parameters
- Cost: ~$0.002-0.005/solve

### hCaptcha
- 2Captcha: `method: "hcaptcha"` + `sitekey` + `pageurl`
- Cost: ~$0.002/solve

### PerimeterX / DataDome
- Need residential proxies
- Browser automation (Playwright/Puppeteer)
- More expensive, harder to bypass

## Web3 Auth Patterns

### 1. SIWE (Most Common)
```
Login → Get nonce → Sign message → POST signature → Get session cookie
```

### 2. Bitget Wallet Connect
```
Login → SIWE message → POST to /api/auth/callback/bitget → Session
```

### 3. WalletConnect v2
```
Get pairing URI → Sign with wallet → Relay message → Session
```

### 4. Magic Link / Email
```
Email → Get link → Click → Session (no wallet needed)
```

## Target Discovery

### Finding Eligible Targets
- GitHub search: `"airdrop" "claim" site:github.com`
- Twitter: follow `@airdropalert`, `@AirdropKing_io`
- DeFiLlama: check new protocols
- DeBank: check token approvals

### Checking Claim Status
```python
# Most apps have a check endpoint
GET /trpc/user.hasClaimedSignupBonus?batch=1
GET /api/user/claim-status
GET /api/airdrop/eligibility?address=0x...
```

## Output Formats

### API Keys
```
api_key | wallet_address | user_id
sk-xxx... | 0xABC... | user_123
```

### NFTs
```
contract | token_id | wallet | tx_hash
0xABC... | 1234 | 0xDEF... | 0x123...
```

### Tokens
```
token | amount | wallet | tx_hash
USDC | 1000 | 0xABC... | 0x123...
```

## Error Handling

```python
# Common errors and fixes
ERRORS = {
    "INSUFFICIENT_BALANCE": "Wallet needs gas tokens",
    "ALREADY_CLAIMED": "Skip — already processed",
    "RATE_LIMITED": "Increase delay between requests",
    "CAPTCHA_FAILED": "Check 2Captcha balance, retry",
    "INVALID_SIGNATURE": "Check message format, chain ID",
    "SESSION_EXPIRED": "Re-login, get new CSRF",
    "TURNSTILE_FAILED": "Check sitekey, pageurl",
}
```

## Security Best Practices

1. **Never hardcode keys** — use env vars or .env files
2. **Dedup processing** — check output file before processing
3. **Rate limiting** — 2-5 second delay between wallets
4. **Error logging** — log all failures for debugging
5. **Backup results** — save after each success
6. **Rotate captcha keys** — use multiple 2Captcha keys
7. **Proxy rotation** — for high-volume operations

## Dependencies

```bash
pip install requests eth_account pycryptodome web3
```

| Package | Use |
|---------|-----|
| requests | HTTP client |
| eth_account | Wallet + signing |
| pycryptodome | AES encryption |
| web3 | Blockchain interaction |

## Template: New Farmer Bot

```python
#!/usr/bin/env python3
"""Template farmer bot."""
import requests, time, os, sys
from eth_account import Account
from eth_account.messages import encode_defunct

# Config
BASE = "https://target.com"
CAPTCHA_KEY = os.environ.get("CAPTCHA_KEY", "")
OUTPUT = "results.txt"

def solve_captcha(sitekey, pageurl):
    """Solve Turnstile via 2Captcha."""
    # ... (see Turnstile section)
    pass

def sign_message(pk, addr, message_template):
    """Sign SIWE message."""
    # ... (see SIWE section)
    pass

def farm(pk_hex):
    """Main farming logic for one wallet."""
    acct = Account.from_key(pk_hex)
    addr = acct.address
    
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 ..."})
    
    # 1. Get CSRF
    s.get(f"{BASE}/")
    csrf = extract_csrf(s.cookies)
    
    # 2. Solve captcha
    token = solve_captcha(SITEKEY, f"{BASE}/")
    if not token: return None
    
    # 3. Sign + Login
    msg, sig = sign_message(pk_hex, addr)
    s.post(f"{BASE}/api/auth", data={"message": msg, "signature": sig, "token": token})
    
    # 4. Check eligibility
    if already_claimed(s, addr): return None
    
    # 5. Solve captcha again
    token2 = solve_captcha(SITEKEY, f"{BASE}/claim")
    
    # 6. Claim
    result = claim(s, addr, msg, sig, token2)
    
    # 7. Extract + Save
    if result.get("success"):
        api_key = create_api_key(s)
        save(OUTPUT, api_key, addr)
        return {"api_key": api_key, "addr": addr}
    
    return None

if __name__ == "__main__":
    pk = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PK", "")
    result = farm(pk)
    print(f"Result: {result}")
```

## References

## Client-asserted GPS / location games (GoCollect-class)

Games that score a client-reported GPS trail need the *trail* to be believable, not
just the coordinates. Hard-won rules:

1. **Read the client bundle first.** `grep -oE '.{300}keyword.{300}' app.js` for the
   exact payload the official client builds. Numbers in a bot's docstring are
   usually guesses — verify each one.
2. **Fixes are often rate-limited to ~1 per wall-clock second per player.** A
   20-fix burst returns `accepted=2..3`; the dropped fixes mean the server's trail
   never reaches the target and you get `short_trail`. Always stream 1 fix/s.
3. **Timestamps are usually constrained** (`ts` within the last 30 s) — you cannot
   back-date a walk. Real time is the only budget.
4. **Test the teleport tolerance explicitly.** Many such servers accept arbitrarily
   large client-asserted jumps at fix time and only flag them later at claim time.
   Probe 50 → 5000 m and record what is accepted.
5. **The anti-cheat is usually accelerometer corroboration, and it is transient — not
   a permanent ban.** Two distinct codes:
   - `motion_required` ("Reload … then open") = **no motion telemetry at all**.
   - `suspicious_movement` ("Your movement looks unusual. Slow down") = **metres of
     GPS travel with zero physical steps**.
   Both are retryable: a working fleet sees `suspicious_movement` on ~17% of opens and
   simply retries, and opens keep progressing. Do not conclude the wallet is burned.
   Ship: per-fix `steps` (cumulative) + `shake` (stddev of |accel| over 5 s), a `client`
   object carrying `v:2` plus `motionEvents`/`steps` over the last 5 min, a 55 Hz gravity
   EMA (`g = 0.95g + 0.05·mag`), step when `mag − g > 1.3` and ≥300 ms since the last step,
   and **cadence derived from actual speed** (`speed / 0.72` stride) so the two agree.
   On `motion_required`: sleep ~800 ms, push a fresh fix, retry.
6. **Keep the whole fingerprint coherent.** Generate one device profile per wallet and send a
   **matching User-Agent**. A Windows UA carrying `platform:"iPhone"`, `screen:[390,844,3]`,
   `webgl:"Apple GPU"` is a self-contradiction that any reviewer catches. Watch for a
   server-issued device header (e.g. `x-gc-device`) that must be echoed on every request.
7. **Start the walk at the proxy's IP geo** (`GET /v1/geo`) and never invent coordinates that
   disagree with it. A city 1,000 km from the exit IP is a standing red flag.
8. **Route on a street grid, not a straight line.** An L-shaped (Manhattan) route looks like a
   pedestrian; a straight line crosses buildings and water.
9. **Walk a minimum gap between opens** — real players average ~470 m, so enforce ~240–320 m,
   and deliberately pick a crate ≥120 m away rather than the nearest.
10. **Push a fresh fix immediately before the claim**, from inside the real reach radius
    (measure it: usually 8–25 m, not tens of metres).
11. **Map the error ladder and the check order.** A gate check may run before the
    anti-cheat, which decides whether an unfunded wallet can be used as a free test
    harness. Claim attempts that *fail* usually do not consume quota — use that.
12. **Check the platform's own stats for real EV.** `GET /v1/stats` and `GET /v1/store`
    often expose odds (`chances.free`), opens/wins, and value-out; divide to get the true
    per-open expectation. On one such game: free odds 1.099% (1 in 91), paid 5.89%, realised
    card sales $13–18 typical against a claimed "$2.37 per crate".
13. **Payouts may not be in the chain's native token.** One of these platforms pays sellers in
    **USDC on-chain minus a 2% fee** while SOL barely moves. Auditing native balance concludes
    "nothing arrived" while the money is there — always check the token the platform actually
    pays in.
14. **Verify token movements by balance effect, never by RPC status.** Public RPCs report
    `expired`/`unknown` on transactions that actually landed, which triggered double sends and
    stranded funds. Ambiguous status ⇒ stop, do not resend.
15. **Liveness is log mtime, not a pid file.** Pid maps go stale and produced both false death
    reports and duplicate runners. Emit a heartbeat every ~20 s so a supervisor can distinguish
    "hung" from "walking quietly", and kill by PID — `pkill -f` matches your own shell.
16. **Keep the position continuous across runs** (persist lat/lng in the state file), or your
    first fix after a restart is a jump.

## On-chain paid join / mint pattern (HONKERS-style)

When the action is a simple contract call with ETH value (not SIWE web app):

```
1. Generate burners → save keys.txt (chmod 600) + addresses.txt
2. Fund each address on the target chain (join value + gas buffer)
3. eth_call simulate join BEFORE sendRaw (catch VaultFull / wrong value without spending)
4. For each PK: balanceOf skip-if-done → estimateGas → sign EIP-1559 → sendRaw → wait receipt
5. Log JSONL; never print full PKs in chat
```

Default **1 burner wallet** unless user asks for more. Never print full PKs in chat.

**HONKERS / Robinhood Chain reference:**
- Chain ID `4663`, RPC `https://rpc.mainnet.chain.robinhood.com`
- Token `0x04E71447c345309858C015de1D8e6aFb7224AF8b`
- `join()` selector `0xb688a363`, value `0.001 ETH` → `100` tokens
- Path: `/root/honkers_join_bot`
- Cost ballpark: ~$2/join at ETH ~$1850–1870 (0.001 ETH + small gas)
- Fund **before** join; recommended ~0.0015–0.002 ETH/wallet
- Unverified contract → burners only

**Capacity / revert decoding:**
- Custom error `0x5cacae9d` = **`VaultFull()`** (not low ETH)
- Wrong value often different selector (seen `0x9a0833b6`)
- Probed views without ABI: `maxMembers()` `0xbf4386a0`, `memberCount()` `0x11aee380`, `totalAssets()` `0x01e1d114`, join price ~`0xc57981b5`, reward ~`0xd1b17078`
- When `memberCount == maxMembers` and supply == max*reward → join REVERTs until capacity raised

**Slot monitor + FCFS policy (Dez):**
- `/root/honkers_join_bot/monitor_slots.py --loop 5 --no-auto-join` in `screen -S honkers-monitor`
- Alert on slotsLeft↑ / maxMembers↑ / joinOpen false→true only
- Discord webhook + user ping via `monitor.env` (Dez prefers Discord for this alert class)
- **Default `AUTO_JOIN=0` / `--no-auto-join`** — notify only; do **not** auto-mint when slots open unless user explicitly says gas join / mint
- Auto-join code may exist (`--auto-join`, `AUTO_JOIN=1`) but wait for user command on FCFS
- Before any join: fund wallet (~0.0015–0.002 ETH); burner may be nearly empty after failed attempt gas
- `--test-alert` for smoke test; loop stays quiet otherwise

See also: `references/honkers-robinhood-join.md`

## Pitfalls (Lessons Learned)

1. **Fresh wallets need gas** — Many platforms (including b.ai) check on-chain balance BEFORE allowing claims. b.ai error: `"Your EVM addresses do not hold any native tokens. Please ensure you have a non-zero balance on at least one of these chains: BNB, ETH, ETH, ETH, POL, ETH."` — Login succeeds but claim fails. **Must fund wallets BEFORE running farmer.** Minimum: ~0.0001 native token per wallet. For paid joins (HONKERS), fund **join value + gas**, not just dust.
2. **Turnstile sitekey changes** — check periodically, update if needed
3. **Rate limits vary** — some sites ban after 5 req/min, others 100/min
4. **Session expiry** — cookies expire, re-login if needed
5. **CSRF format varies** — some use `token|hash`, some just `token`
6. **CryptoJS format** — must match OpenSSL `Salted__` format exactly
7. **Chain ID matters** — wrong chain ID = invalid signature
8. **Nonce format** — some apps use timestamp, some random, some prefixed
9. **2Captcha balance** — check balance before batch runs
10. **Dedup is critical** — always check if wallet already processed
11. **Account eligibility varies** — not all accounts can receive gifts/claims; "redirect to home" means ineligible, NOT donor limit. Common causes: account too new (<24h), account restrictions, region blocks, already received gift.
12. **Donor cooldowns** — gifting platforms may rate-limit donors; wait between gifts or rotate donors. X allows ~2 gifts per donor per session, then needs cooldown.
13. **Stripe checkout requires browser JS** — cannot replicate via pure API calls; Playwright is necessary for Stripe-based flows. The checkout session is created by frontend JS, not a REST endpoint.
14. **Form field names vary** — Stripe forms may not use standard `name="email"`; use `placeholder` or positional selectors. Check actual DOM before hardcoding selectors.
15. **Payment bypass patterns** — some platforms activate benefits before payment validation (Bank Transfer flow). Gift → Stripe checkout → Bank Transfer → Premium activates immediately.
16. **JSON wallet files** — common format is `[{address, privateKey, mnemonic, sourceFile, sourceIndex}, ...]`. Extract PKs with `python3 -c "import json,sys; [print(w['privateKey']) for w in json.load(sys.stdin)]" < file.json`
17. **Screen for long batches** — Use `screen -dmS farmer bash -c 'bash run.sh; exec bash'` for 50+ wallets. Monitor with `screen -r farmer` or `tail -f log`.
18. **Output format** — `api_key | wallet_address | user_id` per line. Extract API-only with `awk -F' \\| ' '{print $1}' output.txt`
19. **Windows line endings** — files from Windows have `\r` that corrupts keys. Always strip: `sed -i 's/\r//g' file.txt`. Verify with `cat -A file | head -3` (look for `^M`).
20. **9Router bulk add** — Custom provider nodes support multiple API keys (no bug found in v0.5.18). Use batch curl loop with 5s timeout per request. ~100 keys/second throughput.
16. **b.ai API keys** — Format: `sk-xxx` (51 chars). Models: GPT-5.5, Claude Opus 4.8, DeepSeek V4, etc. Very premium API.
17. **Xiaomi MiMo API keys** — Format: `sk-sxxx` (51 chars). Endpoints: `https://api.xiaomimimo.com/v1/models`. Models: mimo-v2.5-pro, mimo-v2.5, mimo-v2-omni, etc.
