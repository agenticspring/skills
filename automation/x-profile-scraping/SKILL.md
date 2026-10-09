---
name: x-profile-scraping
description: "Scrape X profiles via Playwright; OCR images for codes."
version: 1.0.0
author: spring
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [x, twitter, playwright, scraping, ocr, tesseract, watchdog, invite-codes]
    related_skills: [go-binary-daemon, web3-farmer-bot, agentx]
---

# X Profile Scraping & Code Extraction (Playwright + OCR)

Monitor an X profile for invite-code posts (e.g. `BUFO-*`), extract codes from tweet text AND images, and submit them to a claim backend. Built and verified on the BUFOS Watchdog (see `references/bufos-watchdog.md`).

## 1. Session Setup (X cookies)

X requires a logged-in web session. Use `auth_token` + `ct0` cookies (never passwords).

```python
from playwright.async_api import async_playwright

browser = await p.chromium.launch(headless=True)
ctx = await browser.new_context(viewport={"width": 1280, "height": 900})
await ctx.add_cookies([
    {"name": "auth_token", "value": auth_token, "domain": ".x.com", "path": "/"},
    {"name": "ct0", "value": ct0, "domain": ".x.com", "path": "/"},
])
page = await ctx.new_page()
await page.goto(f"https://x.com/{target}", wait_until="domcontentloaded", timeout=30000)
```

Pitfalls:
- Cookies must be added for `.x.com` domain (not `twitter.com`).
- `ct0` is long (~160 hex chars); auth_token ~40 chars. Don't confuse them.
- Session expiry detection: URL contains `/i/flow/login`, `/login`, `/account/access`, or login inputs (`input[autocomplete="username"]`) → session invalid.

## 2. CRITICAL: Lazy-render timeline

X renders tweets lazily. **`article[data-testid="tweet"]` count is 0 immediately after load** — a health check that counts articles before any scroll falsely reports "empty/unhealthy" and skips scraping.

Fix — scroll once to trigger render, then wait for the first article:

```python
await page.evaluate("window.scrollTo(0, 900)")
await page.locator('article[data-testid="tweet"]').first.wait_for(state="visible", timeout=8000)
await page.evaluate("window.scrollTo(0, 0)")
articles = await page.locator('article[data-testid="tweet"]').count()
```

Also give generous post-load wait: 4.5–7s after `domcontentloaded`, and 2.5s+ after reload.

## 3. Extract codes from tweet text

- Each tweet = `article[data-testid="tweet"]`.
- Codes via regex on `article.inner_text()`: `(?<![A-Z0-9])BUFO[-‐‑‒–—_][A-Z0-9][A-Z0-9_-]{1,31}(?![A-Z0-9])` (handles Unicode dash variants).
- Only accept codes whose tweet has a status link matching `/{target}/status/(\d+)` — this filters replies/quotes from other accounts.
- Normalize code: `value.translate(DASHES).upper().strip(".,:;!?()[]{}<>'\"")`.

## 4. OCR: codes hidden inside images

Many posts put the code in an image, not text. Tesseract pipeline (system binary + PIL preprocessing):

Two passes — image download AND article screenshot (code often sits OUTSIDE the raw media, in overlay/styled corner):

1. **Pass 1**: download media full-res: `div[data-testid="tweetPhoto"] img` → `src` has `&name=small`, replace with `&name=orig`. Fetch via `page.request.get(full)`.
2. **Pass 2**: screenshot the whole `article` element (`article.screenshot()`) — this caught codes the raw image missed.

Preprocessing that works (stylized fonts):
```python
img = Image.open(tmp).convert("L")
if max(img.size) < 1600:
    img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)   # upscale small
elif max(img.size) > 2000:
    img = img.resize((img.width * scale, ...))                          # cap huge shots
img = ImageOps.autocontrast(img)
img = img.point(lambda p: 255 if p > 140 else 0)                        # binarize
# tesseract with psm 3, 6, AND 11; aggregate codes from all psms (don't break on first hit)
```

OCR noise normalization — tesseract reads `-` as `:`, spaces, `°`, `*`:
```python
norm = re.sub(r"(?i)\bBUFO\s*[^A-Za-z0-9]{1,4}\s*", "BUFO-", text)
```

Pitfalls:
- **False positives are OK** if backend validates: OCR reads "BUFO ISLAND FERRY CO" as `BUFO-ISLAND` → backend answers `invalid`, harmless. Don't over-filter; let the backend reject.
- Aggregate across psms; a code found only by psm=6 gets missed if you break at the first psm that returns something.
- `tesseract` must exist (`which tesseract`); `pillow` must be installed. Timeout each tesseract call (45–60s).

## 5. Claim backend integration

Verify the endpoint protocol BEFORE wiring:
- `GET <endpoint>` → `{"ok": true}` (health).
- `POST {"action":"check","code":"X"}` → `{"ok":true,"remaining":N}` or `{"ok":false,"reason":"invalid|full|sold_out"}`.
- `POST {"action":"claim","code":"X","wallet":"0x..."}` → `{"ok":true,"number":N,"codename":"..."}` or `reason:"duplicate"`.

Pitfalls:
- **Google Apps Script endpoints return HTTP 302 first** (redirect to `script.googleusercontent.com`) — curl needs `-L` / requests `allow_redirects=True`. A bare `curl` showing `Moved Temporarily` is normal, not a failure.
- Apps Script has **cold-start latency** (seconds) — set generous timeouts (30–45s) and expect first-call slowness.
- Apps Script has **concurrency quotas** — don't fire 100 parallel claims; keep worker pools ~12–30.
- Watchdog's `--self-test` can hang in subprocess if the endpoint is slow — validate the same asserts in-process instead.

## 6. Run as daemon

Follow `go-binary-daemon` for screen/tmux pattern: `start.sh` wrapping the python binary, `screen -dmS name /path/start.sh`, verify with `tail` + `pgrep`. Linux port: replace `msvcrt` file-lock with `fcntl.flock` (see go-binary-daemon pitfalls).

## References

- `references/bufos-watchdog.md` — full BUFOS watchdog case: Apps Script endpoint discovery, Linux port, fixes, config layout.
