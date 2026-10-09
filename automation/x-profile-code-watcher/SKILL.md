---
name: x-profile-code-watcher
description: "Use when building an X profile code watcher with image OCR."
version: 1.0.0
author: spring
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [twitter, x, playwright, ocr, tesseract, watchdog, claim, invite-code]
    related_skills: [go-binary-daemon, web3-farmer-bot]
---

# X/Twitter Profile Code Watcher

Watch an X profile for invite/claim codes (`BUFO-*` style) posted as tweet text **or inside images**, validate against a claim backend, and submit wallet addresses first-come-first-served. Verified with `asbryx/bufos-watchdog` (THEBUFOS whitelist) 2026-08-09.

## Architecture

```
Playwright + X session cookies (auth_token + ct0)
        → poll profile page every 10-20s
        → lazy-render scroll fix
        → scrape article texts → extract codes (text path, cheap)
        → if no text code: OCR tweet images (once per NEW tweet)
        → check code against backend
        → claim pending wallets in parallel (ThreadPoolExecutor)
        → screenshot ticket + Telegram notify
        → persist state (never re-submit successful wallets)
```

## Core steps

### 1. Session cookies

Watchdog only needs `auth_token` + `ct0` (never the password/private key). Inject via Playwright:
```python
await context.add_cookies([
    {"name": "auth_token", "value": auth_token, "domain": ".x.com", "path": "/"},
    {"name": "ct0", "value": ct0, "domain": ".x.com", "path": "/"},
])
```
`twitter.username` is only for logs — not used for auth.

### 2. Lazy-render fix (critical)

X does NOT render `article[data-testid="tweet"]` immediately after `domcontentloaded`. Counting articles without scrolling returns 0 → health check marks session `unhealthy` → scraper never runs. Fix:
```python
await page.evaluate("window.scrollTo(0, 900)")
await page.locator('article[data-testid="tweet"]').first.wait_for(state="visible", timeout=8000)
await page.evaluate("window.scrollTo(0, 0)")
```

### 3. Text code extraction

```python
CODE_RE = re.compile(r"(?<![A-Z0-9])BUFO[-‐‑‒–—_][A-Z0-9][A-Z0-9_-]{1,31}(?![A-Z0-9])", re.I)
```
Normalize dash variants (en/em dash, underscore) to `-` before matching. Only accept codes from status URLs belonging to the target account (`/<target>/status/<id>`).

### 4. Image OCR (tesseract) — only when text yields nothing

Two-pass:
1. **Download full-res media**: `div[data-testid="tweetPhoto"] img` → replace `&name=small` → `&name=orig` → fetch via `page.request.get()`.
2. **Screenshot the whole `article` element** and OCR it — codes often sit OUTSIDE `tweetPhoto` (overlay, corner, composite). Raw-image OCR missed `BUFO-SLEEP`; article screenshot found it.

Preprocessing (PIL): grayscale → autocontrast → binarize `>140` → try psm `3`, `6`, `11` in order. Cap images `>2000px` down to 2000 (2x upscale on large images makes tesseract timeout >60s); upscale only when `<1600px`.

OCR noise normalization — dash misread as `:`, spaces, `°`, `*`:
```python
norm = re.sub(r"(?i)\bBUFO\s*[^A-Za-z0-9]{1,4}\s*", "BUFO-", text)
```

### 5. Per-tweet OCR cache (performance)

OCR is expensive (psm=3 ~1.6s, psm=6 ~34s, psm=11 ~27s on a 1085x1450 image). Run it ONCE per new tweet_id:
- `seen_tweet_ids` — tweets that already produced a text code (handled upstream)
- `ocr_scan_ids` — tweets already OCR-checked; append + `save_state()` immediately after OCR
- Skip OCR when tweet_id is in either list; cap lists to ~500 entries.
Without this, polls degrade from 10-20s to 30-40s.

### 6. Backend discovery

The claim endpoint is often embedded in the site's frontend HTML:
```bash
grep -oE '.{120}ENDPOINT.{200}' page.html
```
Google Apps Script endpoints return **HTTP 302** on GET — must follow redirect (`curl -sSL` / requests default). Protocol:
- `GET` → `{"ok":true}`
- `POST {"action":"check","code":"X"}` → `{"ok":true,"remaining":N}` | `{"ok":false,"reason":"invalid|full|sold_out"}`
- `POST {"action":"claim","code":"X","wallet":"0x..."}` → `{"ok":true,"number":N,"codename":"..."}` or `duplicate`
- Submit only `min(pending_wallets, remaining)` — not all wallets.

### 7. Run as daemon

See `go-binary-daemon` skill: `start.sh` + `screen -S <name>`, fcntl lock-port for Windows-only single-instance code, and the Hermes terminal-guard workaround (run referenced `.py` via `execute_code`'s terminal helper or the screen wrapper).

## Pitfalls

1. **Lazy-render** — counting articles before scroll always returns 0; false "unhealthy", scraper never runs.
2. **Raw image vs rendered article** — codes can be outside `tweetPhoto`; always add the full-article screenshot pass.
3. **OCR per poll is a silent perf killer** — cache per tweet_id.
4. **Upscale cap** — 2x on >1600px images → tesseract timeout; cap down, upscale only small.
5. **False positives harmless** — e.g. `BUFO-ISLAND` from "BUFO ISLAND FERRY CO" ticket text: backend answers `invalid`, bot records and moves on. Don't over-filter.
6. **EPIPE crash** — `Error: write EPIPE` from Playwright node transport when the browser is killed mid-OCR (timeout). Wrap OCR in try/except; the daemon restart loop recovers.
7. **`--self-test` subprocess hang** on Apps Script cold start + subprocess timeout — validate the same asserts in-process via `execute_code` instead.
8. **Never store wallet private keys in the repo** — addresses live in `profiles.json` (gitignored), private keys in a separate chmod-600 file, never committed.

## Verification checklist

- [ ] Health check sees `article_count > 0` after lazy-render fix (log shows `Poll OK`, not `unhealthy`)
- [ ] Text-code tweet: code extracted without OCR
- [ ] Image-code tweet: OCR finds code (watch for `OCR image N found codes:` log)
- [ ] Backend check returns valid/invalid/full correctly
- [ ] Claim submits `min(pending, remaining)` wallets in parallel
- [ ] Second poll does NOT re-OCR the same tweet (cache working)
- [ ] Telegram heartbeat `delivered=1`

See `references/bufos-x-watchdog-ocr.md` for the full verified session detail (endpoints, tweet IDs, timing, exact fixes).
