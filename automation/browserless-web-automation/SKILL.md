---
name: browserless-web-automation
description: "Automate web registration, login, and form submission — pick the lightest rung that works: pure HTTP (stdlib/curl-cffi), fetch() inside a browser page, or full Playwright. Covers CSRF acquisition (incl. JS-derived headers), RSA/PKCS1, JSONP APIs, IMAP verification, proxy rotation, and Playwright proxy/anti-bot setup."
platforms: [linux, macos, android]
prerequisites:
  commands: [python3]
---

# Browserless Web Automation

Automate web interactions — signup, login, email verification, form submission — by
picking the **lightest rung that actually works**. Works on VPS, laptop, and Termux
(Android).

## Pick the lightest rung

Cost rises fast as you go down. Always try rung 1, escalate only on evidence.

| rung | what it is | when it holds | cost |
|---|---|---|---|
| **1. Pure HTTP** | stdlib / `requests` / `curl_cffi` | older & passport-style auth: JSONP, RSA-encrypted passwords, cookie-CSRF | cheapest — no browser at all |
| **2. `fetch()` in a page** | `page.evaluate()` issuing the JSON calls from inside a real page | server binds CSRF/fingerprint to something only the page's JS provides | one browser, **zero rendering** — measured ~6× faster than driving the UI |
| **3. Full browser UI** | Playwright clicking the real interface | steps needing page-level crypto (card entry, wallet signing, CAPTCHA), or when 1–2 are blocked | most expensive |

Do not jump to rung 3 because rung 1 failed on the *first* call — check *why* it failed
first. A `403 csrfFailed` on call 2 usually means "go to rung 2", not "the site needs a
full browser". See `references/meta-muse-registration.md` for a worked case where rung 1
is hard-blocked, rung 2 solves the JSON half, and only the card step genuinely needs rung 3.

## Philosophy

Many sites (especially older/passport-based auth systems) don't need a browser at all. They use:

- **JSONP callbacks** instead of REST APIs
- **RSA PKCS1 v1.5** encryption for passwords (via JSEncrypt)
- **CSRF tokens** exchanged via cookies
- **IMAP** for email verification links

All of these can be handled with Python **stdlib only** — perfect for resource-constrained environments like Termux.

## Core Patterns

### 1. Lightweight HTTP Session with Cookie Jar

Use `http.cookiejar.CookieJar` + `urllib.request.build_opener` for cookie persistence across requests. No `requests`, no `httpx`:

```python
import http.cookiejar, urllib.request, ssl

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(cj),
    urllib.request.HTTPSHandler(context=ssl._create_unverified_context()),
)
```

For proxy support, add `urllib.request.ProxyHandler`.

### 2. RSA PKCS1 v1.5 Encryption (Zero Deps)

Replace `pycryptodome` with pure Python using `pow()`:

```python
import base64, random

def rsa_pkcs1_encrypt(password: str, n: int, e: int) -> str:
    pwd_bytes = password.encode("utf-8")
    k = (n.bit_length() + 7) // 8
    ps_len = k - 3 - len(pwd_bytes)
    if ps_len < 8:
        raise ValueError("Password too long")
    ps = bytes(random.randint(1, 255) for _ in range(ps_len))
    eb = b"\x00\x02" + ps + b"\x00" + pwd_bytes
    m = int.from_bytes(eb, "big")
    c = pow(m, e, n)
    return base64.b64encode(c.to_bytes(k, "big")).decode()
```

### 3. DER Decode RSA Public Key

Extract `n` and `e` from a SubjectPublicKeyInfo DER blob:

```python
def der_decode_rsa_pubkey(b64_pem: str) -> tuple[int, int]:
    der = base64.b64decode(b64_pem)
    def read_tlv(d, p):
        t=d[p]; l=d[p+1]; h=2
        if l & 0x80:
            nl = l & 0x7f
            l = int.from_bytes(d[p+2:p+2+nl], 'big')
            h = 2 + nl
        return t, l, p+h, p+h+l
    _, _, _, p = read_tlv(der, 0)
    _, _, _, p = read_tlv(der, p)
    _, _, vs, _ = read_tlv(der, p)
    _, _, rp, _ = read_tlv(der, vs+1)
    _, _, ns, ne = read_tlv(der, rp); n = int.from_bytes(der[ns:ne], 'big')
    _, _, es, ee = read_tlv(der, ne); e = int.from_bytes(der[es:ee], 'big')
    return n, e
```

### 4. CSRF Token via JSONP

Many Chinese/auth systems use JSONP to distribute CSRF tokens. POST/GET to a JSONP endpoint, the cookie is set in response:

```python
# Flow:
# 1. Visit a page on the target domain (sets base cookies)
opener.open(register_url)
# 2. Call JSONP endpoint (sets _csrfToken cookie)
opener.open(get_inparams_url)
# 3. Read cookie from jar
csrf = next((c.value for c in cj if c.name == '_csrfToken'), '')
```

### 5. IMAP Email Verification (Stdlib)

```python
import imaplib, email

mail = imaplib.IMAP4_SSL(imap_host, imap_port)
mail.login(imap_user, imap_pass)
mail.select('"[Gmail]/All Mail"')
ok, msgs = mail.search(None, f'(TO "{email_addr}")')
for num in msgs[0].split():
    ok, data = mail.fetch(num, "(RFC822)")
    msg = email.message_from_bytes(data[0][1])
    # extract body, regex for verification link
mail.logout()
```

### 6. Fetching RSA Pubkey from JS Bundle

Some sites embed the pubkey in a JavaScript config file, not the HTML. Fetch the JS and extract:

```python
import re, urllib.request

resp = urllib.request.urlopen("https://cdn.example.com/login_v6.js")
js = resp.read().decode()
match = re.search(r"pubkey\s*=\s*'([^']+)'", js)
pubkey_pem = match.group(1).replace('\\n', '\n')
```

### 10. Reverse-Engineer a Signup from a HAR Capture

When a site's auth flow is opaque (wallet connect, multi-step, hidden signature
fields), the fastest path to a browserless script is a captured HAR:

1. **Ask the user for a HAR export** (DevTools → Network → Preserve log → do one
   manual signup → Export HAR). This is a first-class source, like pasted code.
2. **Parse `log.entries`** with `execute_code`; filter URLs matching
   `/account|auth|wallet|login|sign|verify|register/` and print request method,
   status, URL, and **full POST body** — signature/message fields hide after long
   tokens and only appear when you print the whole JSON.
3. **Verify signatures offline before scripting.** If the flow signs a message
   (SIWE-style), decode the captured signature BOTH ways (base64 AND base58) and
   check which one verifies against the captured public key with
   `nacl.signing.VerifyKey`. See `references/gmgn-registration.md` — the #1 bug
   there was sending base64 when the server wanted base58.
4. **Copy exact request headers** (UA, Origin, Referer, sec-fetch-*) from the HAR
   entry into the pure-HTTP client — Cloudflare-gated endpoints often 403 from
   bare curl but 200 with the app's headers.
5. **Timestamp fields may be validated.** If the signed message contains
   `Issued At`, use the step-1 request time, not the moment you send step 2.

## Camofox UI fallback for validated forms

When a legitimate one-off Google Form or similar form rejects fresh direct `formResponse` requests with HTTP 400/`data-validation-failed`, switch to a real Camofox UI session instead of blind retries. Install and invoke the pinned browser server through the `terminal` tool, open the form, use a fresh `camofox snapshot` for live refs, fill only truthful user-provided data, re-snapshot before one submit, and accept success only from the explicit confirmation page. Stop the server after verification. See `references/camofox-google-form-fallback.md` for the tested `camofox-browser@2.4.7` procedure and failure gates.

## Batch Google Form submissions (Camofox)

For a batch of distinct Google Form entries (each with its own payload), do not try raw `formResponse` POSTs — the same validation-failed gate hits every entry. Use the Camofox server with a fresh `open` per entry.

Key mechanics:

1. Install the pinned server: `npm install -g camofox-browser@2.4.7` (through the `terminal` tool), start `camofox-browser` in the background, wait for `/health` (`curl -fsS <CAMOFOX_URL_REDACTED>/health`) to return `"running":true`.
2. Prepare a mapping JSON file with one object per entry: `{"set": N, "handle": "...", "address": "0x..."}` and an optional per-entry reasons JSON keyed by `set`/index. Keep both mode 600.
3. Use `scripts/camofox-google-form-batch.py` — it opens the form, snapshots, fills fields, ticks checkboxes/radios, submits, and verifies the confirmation page for each entry. Adjust `FORM_URL` and the ref-label matcher to the actual form.
4. **Pitfall: Camofox limits tabs per session.** `camofox open` starts failing with `Error: Maximum tabs per session reached` after a handful of opens. Always run `camofox close` (ignore errors) before each new `open`.
5. Confirm success only on the explicit recorded-response page, e.g. `Twoja odpowiedź została zapisana.` / `Your response has been recorded.` Treat anything else (`data-validation-failed`, error text, unknown page) as failed — no blind retries. Stop on first failure and keep partial results.
6. Camofox refs (`[eN]`) change per snapshot; parse the snapshot text for label→ref each iteration (regex `(textbox|checkbox|radio|button|link) "label" [eN]`), never hardcode refs.

See `references/camofox-google-form-batch.md` for the tested run, exact ref-label matcher for the HypzList form, and resume-from-index usage.

## TanStack Start server-functions (/_serverFn)

Modern TanStack Start apps (e.g. Lovable-built sites like `playbandits.xyz/claim`)
call backend functions through `/_serverFn/<sha256-hash>` endpoints instead of
plain REST. The hash identifies a compiled server function; the wire format is
NOT plain JSON.

Key mechanics (verified on playbandits.xyz Bandit List claim):

1. **Endpoint discovery.** The main JS bundle lists chunks like
   `claim.functions-<hash>.js`. Fetch that chunk and read its tail — server
   functions are registered as
   `h({method:"POST"}).handler(e("<sha256>"))` and re-exported with minified
   names (`export{k as a, ...}`). Each export maps to a `/_serverFn/<sha256>`
   call.
2. **Required headers.** Calls need `x-tsr-serverFn: true`, `accept:
   application/json`, `Origin` and `Referer` matching the site, plus cookies
   from a prior page load. Without them you get `403 Forbidden`.
3. **Body format.** The client sends `{"data": {...}}` where `data` is the
   serialized argument object (e.g. `{address, purpose}`). Plain JSON works
   for some functions but POST handlers can reject with
   `Seroval Error (step: 3)` — the client serializes args with the Seroval
   wire format before sending.
4. **Reliable invocation from Camofox.** When raw curl fights the wire
   format, run the function through the page context so the framework
   serializes for you:
   ```js
   import('/assets/claim.functions-<hash>.js')
     .then(m => m.<exportName>({data: {address: '0x...', purpose: 'claim'}}))
     .then(r => JSON.stringify(r))
   ```
   Do this with `camofox eval <expression>` after opening the site. This
   bypasses all manual Seroval encoding.
5. **Allowlist claim flow.** A check function returns a sign-message
   (`"The Bandit List\n\nSign to prove you control this wallet...Nonce: ..."`)
   when the wallet might be eligible. Sign it locally (ethers
   `wallet.signMessage`, NOT `cast wallet sign`), then call the claim
   function with `{data: {message, signature}}`. Response statuses:
   `not_eligible`, `already_claimed`, `claimed`, `closed`.
6. Read the returned object — TanStack returns Seroval-tagged JSON
   (`{"t":..., "p":{"k":["result"],"v":[...]}}`); `JSON.stringify` the
   resolved promise in the eval to get readable values.

See `references/tanstack-start-serverfn.md` for the full worked Bandit List
run: function-hash map, minified export mapping, exact eval expressions, and
the sign → submit sequence.

## Common Password Validation Rules

When registering, the client-side validation regex reveals server rules. Common patterns:

- **Alphanumeric only**: `^[a-zA-Z\d]{6,18}$`
- **Mix of letters and digits**: `^(?!([a-zA-Z]+|\d+)$)[a-zA-Z\d]{6,18}$`
- **At least one uppercase, one lowercase, one digit**: `^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$`

Always extract the regex from the page/JS rather than guessing.

### 7. Proxy Rotation with Ban Tracking

When a site bans IPs (code 11401, -11051, -11055), rotate proxies and mark dead ones:

```python
class ProxyPool:
    def __init__(self, path: Path):
        self.proxies: list[str] = []
        self.dead: set[int] = set()
        self.idx = 0
        if path.exists():
            for line in path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(":")
                if len(parts) == 4:
                    self.proxies.append(f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}")
                elif len(parts) == 2:
                    self.proxies.append(f"http://{line}")

    def mark_dead(self, proxy_url: str) -> None:
        try:
            self.dead.add(self.proxies.index(proxy_url))
        except ValueError:
            pass

    def random(self) -> str | None:
        alive = [p for i, p in enumerate(self.proxies) if i not in self.dead]
        return random.choice(alive) if alive else None

    @property
    def alive_count(self) -> int:
        return len(self.proxies) - len(self.dead)
```

### 8. Batch Account Registration Loop

For mass signups, structure the loop with retry-on-ban logic:

```python
success = 0
for i in range(count):
    email, password = gen_identity()
    proxy = proxy_pool.random()

    code, msg = register(email, password, proxy, rsa_n, rsa_e)

    if code == 0:
        save_account(email, password)
        success += 1
        poll_email(email)  # verify if needed
    elif code in BAN_CODES:
        proxy_pool.mark_dead(proxy)
        proxy2 = proxy_pool.random()
        if proxy2:
            code2, msg2 = register(email, password, proxy2, rsa_n, rsa_e)
            if code2 == 0:
                save_account(email, password)
                success += 1
        # else: skip, no more proxies
    else:
        failed += 1
```

### 9. Random Identity Generation

Avoid detection by using region-specific name pools for email generation:

```python
NAMES = {
    "usa": {"first": ["James","Mary","Robert",...], "last": ["Smith","Johnson",...]},
    "asia": {"first": ["Wei","Yuto","Minjun",...], "last": ["Wang","Sato","Kim",...]},
    "europe": {"first": ["Liam","Emma","Lukas",...], "last": ["Mueller","Martin",...]},
}

def gen_identity(domain: str) -> tuple[str, str]:
    region = random.choice(list(NAMES.keys()))
    pool = NAMES[region]
    first = random.choice(pool["first"])
    last = random.choice(pool["last"])
    num = random.randint(10, 999)
    email = f"{first.lower()}.{last.lower()}{num}@{domain}"
    return email, region
```

## Pitfalls

- **Pubkey can change between page loads** — always fetch it fresh from the JS bundle or page, never hardcode
- **Base64 `+` in URL query strings** — `urllib.parse.urlencode` encodes `+` as `%2B` automatically, but if you build URLs manually, `+` gets decoded as space
- **IMAP folder names** — Gmail auto-archives some emails; search `[Gmail]/All Mail` not `INBOX`
- **JSONP with `$.ajax`** — jQuery adds `callback=?` automatically; your manual call needs an explicit `callback` param
- **Password must pass BOTH client and server validation** — server may be stricter than client regex
- **Proxy format**: `host:port:user:pass` lines in proxy.txt need to be parsed into `http://user:pass@host:port` URLs for urllib
- **Playwright needs those SAME credentials split apart — a URL-embedded `user:pass@host:port` fails.** `new_context(proxy={"server": "http://user:pass@host:port"})` produces `net::ERR_TUNNEL_CONNECTION_FAILED` on hosts that `curl -x` and `requests` reach fine through that exact proxy. Pass them as separate keys instead:
  ```python
  {"server": f"http://{host}:{port}", "username": user, "password": pw}
  ```
  Diagnostic that isolates this in one step: if `curl -x <proxy>` works but the browser times out, it is the *browser's* proxy layer, not the proxy. Normalise `host:port:user:pass` → the split dict before handing it to Playwright.
- **Chromium exhausts a rotating proxy's concurrent-session cap.** Through a proxy that curl handles instantly, chromium still times out on every page: it opens many parallel connections per host (preconnect, background networking, HTTP/2 multiplexing) and trips the provider's session limit. Launch with connection pressure reduced:
  `--disable-http2 --disable-background-networking --disable-preconnect --disable-dns-prefetch --disable-features=NetworkPrediction,PreconnectToSearch,SpeculativePreconnect`.
  Optionally abort `image`/`media`/`font` via `context.route()` — never `stylesheet`, or element-visibility waits start lying.
- **Probe proxies at LOW concurrency or you will mark live ones dead.** The same list measured at 20 workers reported 4 alive; at **2 workers with ~0.8 s spacing** it reported **21 alive**. High concurrency looks identical to a dead proxy list. Always re-test failures serially before concluding a pool is exhausted, and record the per-proxy exit country from the response body — an "alive" proxy in the wrong country is useless for geo-gated targets.
- **Browserless is the wrong default for some modern signups:** Outlook/Microsoft Fluent multi-step needs a browser for form + fingerprint; late gate is often **HUMAN/PerimeterX press-and-hold**, not a simple token POST. Capsolver/2captcha/Anti-Captcha balances used for Webnovel reCAPTCHA/CF **do not** map 1:1. Spike live page → name captcha vendor (Arkose vs HUMAN vs reCAPTCHA vs CF) → only then pick solver. See `captcha-manager` → `references/outlook-human-perimeterx.md`.
- **curl_cffi helps TLS, not HUMAN:** Outlook CheckAvailable can succeed and CreateAccount returns **`1059` / `field=humanCaptcha`** (or **`1347`** incomplete). Retry with riskAssessmentDetails from 1059 still fails without PX clearance. Hybrid: browserless for canary/availability diagnostics + browser for HUMAN. Toolkit: `/root/outlook-autoreg` (`microsoft-account-registration`).
- **App-JS-derived CSRF defeats cookie+token replay.** Some auth services bind CSRF to a
  value the page's own JS computes, so replaying a harvested cookie jar gets
  `403 {"type":"csrfFailed"}` no matter how complete the headers are. On Meta's native
  auth the header is `x-hatch-csrf-token`, and its value is **only the part of the
  `hatch_native_auth_csrf` cookie before the dot** — a value the server hands back in the
  `/restart` response body. Replaying the full cookie set + that token + client hints +
  `x-hatch-waterfall-id` through `curl_cffi` still 403s. Recognise the shape early:
  `{"type":"csrfFailed"}` or `"Request blocked"` on the *second* call of a flow, while
  the first call succeeds, means the binding is in JS, not in the cookie. See
  `references/meta-muse-registration.md`.
- **Middle rung: run the API through `fetch()` inside a browser page.** Before giving up
  on "browserless" and driving the whole UI, try issuing the JSON calls from the page
  context — `page.evaluate()` with `fetch(path, {credentials:'include'})`. The browser
  supplies whatever the server binds to, so CSRF/fingerprint problems vanish, yet you
  skip every page render and UI click. Measured on Meta: ~20 s for six onboarding steps
  that took ~130 s through the UI — **~6× faster and far less CPU**. Two traps: (a) return
  the *parsed JSON* out of the JS, not the raw body — a big response silently pushes your
  field past any `slice()` cap; (b) the first `restart`→`send-otp` pair intermittently
  403s, so retry the pair ~4×. Caveat: this covers the JSON steps only — any step that
  needs page-level crypto (card entry, wallet signing) still needs the real UI.
- **Rate limits look exactly like a code bug.** When verification codes stop arriving
  across repeated polls after a batch of signups, suspect per-IP OTP/registration
  throttling before re-debugging the mail fetcher. Rotate proxies or wait; do not keep
  hammering (it extends the block).
- **Rotate proxies by ACCOUNT IDENTITY, not by loop index.** `px = proxies[i % len(proxies)]`
  with `i` the inner loop counter looks correct and is a silent disaster: every
  single-account invocation (`--count 1`, which is how you test) and every retry
  re-selects `proxies[0]`. One IP absorbs the entire batch, trips the per-IP
  OTP/registration throttle, and the rest of the pool sits unused — so you debug a
  "broken flow" that is really one exhausted IP. Key the choice on something stable
  across runs (account serial / email / a persisted counter): `proxies[n % len(proxies)]`.
  Diagnostic: log the proxy per account and check whether the SAME exit IP repeats when
  you expect rotation.
- **A step returning success does not mean the SPA is at rest.** After a multi-step
  onboarding (disclosure → verification → app) the next screen's panels are populated
  from server state **asynchronously**, and a single `reload()` is often not enough — you
  get a rendered shell with the control you need simply absent, forever, no error. This
  presented as 8 consecutive redeem failures; the tell was that accounts which skipped
  onboarding (already-settled) succeeded on the *first* poll while every account that had
  just finished onboarding failed every retry round. Fix: re-load and wait before driving
  state-dependent UI — e.g. `for _ in range(3): reload(); wait(13s)` plus a ~7 s wait after
  opening any panel. Budget for it up front in batch loops.
- **Poll for the target control before clicking any parent nav item.** Clicking a
  container/nav entry to "get to" a pane frequently *toggles it closed* when the pane was
  already the default view, and accessible-name matching is unreliable on icon-only nav
  (Playwright reports empty `inner_text`). Order that works: open the container → verify
  it opened (look for a known label) → poll for the exact control
  (`[data-pel-click='…']`, or a stable attribute) while scrolling → only on failure click
  a nav item, matched on its own stable attribute plus exact text. Treat "the control is
  missing right after I clicked a nav item" as evidence *you* closed it, not that the
  feature is absent.
- **An attribute-only locator silently misses controls that render without the attribute.**
  Targeting `[data-pel-click='…']` (or any framework test-id) is the right default, but the
  same screen can render the control with an *empty* attribute — a live dump showed
  `{'p': '', 't': 'Confirm'}` where the element was visible and clickable yet carried no
  test-id at all. Back every such locator with a **text/role fallback**
  (`get_by_role("button", name=re.compile(r"^(Confirm|Confirm age|Continue|Get started)$", re.I))`):
  poll the attribute first, the text second, and log which one matched. This removed the
  majority of one screen's failures and is far cheaper than raising timeouts.
- **Batch runs need three resource guards, not just per-account retries.**
  (1) *Pre-flight*: probe every proxy/resource before account #1 and **abort** the run
  (loud message + webhook notice) if none are alive — a silently dead pool otherwise burns
  the whole batch at ~1 s/account on transport errors.
  (2) *Mid-run*: when an account dies with a transport error
  (`ERR_TUNNEL_CONNECTION_FAILED`, `ERR_PROXY`, `ERR_CONNECTION`, `ERR_TIMED_OUT`,
  `ERR_EMPTY_RESPONSE`), retry that same account on the *next* proxy
  (`proxies[(n + try) % len]`, ≤3) before marking it failed. Accounts failing in ~0-1 s
  with an identical transport error = pool problem, not a logic regression.
  (3) *Terminal resource*: when what you're farming has a finite budget (invite code, promo
  quota, credits) and the API answers a terminal reason such as `{"reason":"used_up"}`,
  **stop the entire run** and ask for a fresh one — do not grind the remaining accounts
  against a dead resource, and do not silently retry (it looks identical to a bot bug).
- **Report success only when the SERVER confirms it, and keep the receipt.** A bare "done"
  off an unexamined response is a claim, not a result. Gate the success branch on explicit
  server truth (`json.success is True`, `redemptionStatus == "redeemed"`), retry transient
  errors before falling through to the slow path, and append
  `email|http_status|raw_response|timestamp` to a proof file so "did it actually go
  through" stays answerable after the run. Corollary: verify against the **mutating call's
  own response**, not a neighbouring read endpoint — a sibling status read returned
  `ELIGIBLE` both before *and* after a successful redeem, so a post-check built on it looks
  like a failure.
- **When a WORKING flow goes 100% fail right after an environment swap, the environment is
  the suspect — revert the swapped variable before touching code.** A batch that had been
  redeeming fine turned into universal `403 {"error":"Forbidden"}` the moment the proxy set
  was replaced. `403` on the JSON calls while the HTML pages, OTP delivery and signup all
  still worked was read as "onboarding step missing" and patched around for ~40 minutes —
  it was the proxies. The discipline that would have settled it in two runs: change one
  variable → run ONE account → if it breaks, **restore the previous value and run one more
  account** → only then start editing code. Recognise the shape: identical failure for every
  account, starting exactly at a known config change, with the failure confined to one tier
  of the stack (API 403 but HTML fine). That is never a code regression you introduced by
  editing a *different* step. Cost of getting this wrong is worse than wasted time: the user
  sees a system that worked stop working and asks *"kenapa kok jadi ga bisa Running?"*.
- **A blocked IP *range* is not a dead proxy — check the tier before discarding the pool.**
  Some provider ranges are WAF-blocked by the target for `XHR`/API traffic while normal
  document loads pass. Symptom set, all at once: proxy passes liveness (HTTP 200 on the
  homepage), OTP arrives, the account is created, and then **every** JSON call returns
  `403 {"error":"Forbidden"}` / the site's own forbidden error. Do not re-debug CSRF for
  this — a *missing/rotated* CSRF token gives the site's CSRF-specific error, whereas a
  range block gives a generic `Forbidden` and hits endpoints that need no CSRF at all.
  Confirmation test: keep everything else fixed and swap to a different **range** (not just
  a different IP in the same /16). Record the working and blocked ranges in the project
  reference so the next run starts from a known-good one.
- **A client-side guard is not the security boundary — probe the server directly.**
  Reading the SPA bundle shows the intended gate (e.g. `if (!xConnected) { hint = "Connect
  your X account…"; return }`), but that only proves what the *page* enforces. To answer
  "can this be done without X?", fetch the endpoint yourself with the prerequisite absent
  and read the server's own error: `POST /api/whitelist/address` → `401
  {"error":"x_login_required"}` settles it as server-enforced, whereas a 200 would mean the
  guard is cosmetic. Cheap, single-request, and it is the difference between a real answer
  and a guess. Finding the endpoint in the first place: fetch `/assets/index-*.js` and grep
  `"/api/[a-zA-Z0-9_/\-]*"` plus the `fetch(`/`axios(` call sites — SPAs name their own
  routes. Also read the flow's OAuth parameters (scope, PKCE, redirect) before proposing
  automation; a PKCE + state-validated OAuth callback cannot be forged, so the only honest
  route is a real account.

## Working style on long reverse-engineering runs

These runs are inherently multi-hour and full of dead ends. Two habits, both learned the
hard way:

1. **Report each blocker as you hit it — do not iterate silently.** The failure mode is
   running 10+ exploratory tool calls in a row while the user sees only "still working",
   then being asked *"jelaskan kenapa kamu lama sekali"*. Send a short status the moment a
   hypothesis dies or a new one appears (what broke, what you're trying next). A user who
   can see the search is fine with a long search; a silent one reads as being stuck.
2. **Prove feasibility before building.** When asked "can this be done without X?", run
   the smallest empirical test that settles it (one captured request, one replay attempt)
   and answer with the evidence — do not build the whole thing and discover the blocker at
   the end.

Also: when the user reports a loss, outage, or that something "got hacked", verify against
the primary source before agreeing or disagreeing. Trace the actual artifact (on-chain
state, live response body, the account's own API) and report what the evidence shows —
including confirming the user when they are right.

## References

- `references/tanstack-start-serverfn.md` — TanStack Start `/_serverFn` reverse-engineering: function-hash map, minified export mapping, Camofox eval invocation, sign → submit sequence (Bandit List worked run)
- `references/meta-muse-registration.md` — **Meta ecosystem (muse.ai) signup**: the working Playwright UI flow + full `data-pel-click` selector map, sr-only OTP input, two form variants, age-verification card popup ($1 auth, new tab), the Meta native-auth JSON API, the JS-derived CSRF header that blocks pure HTTP, **and the deterministic redeem API (§4b) plus the finite invite-code budget (`reason: "used_up"`)**. Verdict: UI flow, API fase 1, and redeem API all verified; **card step settled as not realistically browserless (§6)** — do not re-investigate. **§7 = proxy IP-range block producing `403 {"error":"Forbidden"}` on JSON while HTML/OTP still pass (LA ✅ vs Ashburn ❌), with the three-403 disambiguation table; §8 = unfinished `/access/disclosure` ⇒ app API 403, plus the working end-to-end ordering.**
- `references/rsa-pkcs1-pure-python.md` — Deep dive on RSA PKCS1 v1.5 padding and pure Python implementation
- `references/webnovel-registration.md` — Full reverse-engineered Webnovel signup flow
- `references/gmgn-registration.md` — GMGN wallet-login flow: 2x reCAPTCHA + SIWE message, base58 signature (worked example of HAR reverse-engineering)
- `references/stripe-checkout-session-2step.md` — Stripe Checkout Session API: 2-step create+address pattern, SEPA PaymentMethod creation, pricing lookup
- `templates/mass-signup-skeleton.py` — Runnable skeleton for batch registration with proxy rotation
- `scripts/proxy-preflight.py` — **Run before account #1 of any batch.** Low-concurrency proxy liveness probe (default 2 workers, ~0.8s spacing) that exists because a parallel sweep reported 4/100 alive where a gentle probe found 21/100; exits non-zero when zero are alive so the caller aborts instead of burning the batch on a dead pool.
- Skill `microsoft-account-registration` + `references/outlook-custom-toolkit.md` — Outlook 1059/HUMAN capture path
