# Python Watchdog with X/Twitter Scrape + OCR (BUFOS-style)

Proven 2026-08-09 on `/root/bufos-watchdog` (asbryx/bufos-watchdog, Linux-ported).
Class: watch an X profile for invite-code posts (`BUFO-*`), validate against a
claim backend, submit a wallet pool FCFS. Combine with the Linux lock-port
pitfall in the main SKILL.md.

## Claim backend discovery: read the frontend HTML first

The "backend" is often embedded in the site's own frontend — do NOT assume a
custom endpoint is needed:

```bash
curl -sSL https://target.com/ -o /tmp/home.html
grep -bo "ENDPOINT" /tmp/home.html
```

thebufos.com inline JS had `const ENDPOINT = "https://script.google.com/macros/s/AKfy.../exec"`
(a Google Apps Script). Apps Script endpoints:
- Return **HTTP 302 → script.googleusercontent.com** — always follow redirects
  (`curl -sSL`; requests follows by default).
- Health: `GET` → `{"ok":true,...}`.
- Check: `POST {"action":"check","code":"X"}` → `{"ok":true,"remaining":N}` or
  `{"ok":false,"reason":"invalid|full|sold_out"}`.
- Claim: `POST {"action":"claim","code":"X","wallet":"0x..."}` → `{"ok":true,"number":N,"codename":"..."}`.
- Confirm the exact payload shape from the frontend JS (`post({action:"claim", code, wallet})`)
  instead of guessing — grep the page source for `action`.

## X timeline lazy-render (critical)

X renders tweets lazily: `article[data-testid="tweet"]` count is **0 until the
page is scrolled**, so a health check that counts articles before scrolling
reports a false "empty timeline / unhealthy" and skips scraping entirely.
Fix: scroll once before counting:

```python
await page.evaluate("window.scrollTo(0, 900)")
await page.locator('article[data-testid="tweet"]').first.wait_for(state="visible", timeout=8000)
await page.evaluate("window.scrollTo(0, 0)")
articles = await page.locator('article[data-testid="tweet"]').count()
```

## OCR for codes inside images (2 passes)

When tweet text has no code, OCR the media. Two passes because the code often
sits OUTSIDE the raw `tweetPhoto` media (styled corner, overlay, or composite
article layout):

1. **Pass 1**: download each `div[data-testid="tweetPhoto"] img[src*="twimg.com/media"]`
   full-res (replace `&name=small` with `&name=orig`), preprocess, tesseract.
2. **Pass 2**: screenshot the whole **article element** (`article.screenshot()`)
   and OCR that — catches codes the raw image misses. (BUFOS-SLEEP was only
   detectable via the article screenshot, not the raw image.)

Preprocessing that works (tesseract 5.x + Pillow):

```python
img = Image.open(path).convert("L")
if max(img.size) > 2000:            # cap huge screenshots for speed
    scale = 2000 / max(img.size)
    img = img.resize((int(img.width*scale), int(img.height*scale)), Image.LANCZOS)
elif max(img.size) < 1600:          # upscale small images
    img = img.resize((img.width*2, img.height*2), Image.LANCZOS)
img = ImageOps.autocontrast(img)
img = img.point(lambda p: 255 if p > 140 else 0)   # binarize
```

Try `--psm 3`, `--psm 6`, `--psm 11`; collect codes from ALL three — do NOT
break on first hit (one psm can return only a false positive).

Normalize OCR noise — tesseract reads the dash as `:`, spaces, `°`, `*`:

```python
norm = re.sub(r"(?i)\bBUFO\s*[^A-Za-z0-9]{1,4}\s*", "BUFO-", text)
```

## OCR caching — only scan NEW tweets (user expectation)

"OCR only when there's a NEW tweet; old tweets are never rescanned." Keep
`ocr_scan_ids` (list, cap ~500) in the state file:

```python
if not codes and status_ids:
    tweet_id = max(status_ids, key=int)
    if (tweet_id not in state["seen_tweet_ids"]        # had a text code
            and tweet_id not in state["ocr_scan_ids"]):  # already OCR'd
        codes = await ocr_codes_from_media(page, article)
        state["ocr_scan_ids"].append(tweet_id)
        save_state()
```

Without this, every poll re-OCRs every image article → cycles grow from 10-20s
to 30-60s. `seen_tweet_ids` alone is NOT enough — it only fills when a tweet
already produced a code.

## False positives are OK if the backend filters

Decorative text like "BUFO ISLAND FERRY CO" OCRs as `BUFO-ISLAND` — a false
code. Harmless when the backend answers `reason:"invalid"` and the bot records
it; do not over-engineer wordlists (worst case = one wasted check request).

## OCR timing budget (1085x1450 image)

- psm=3: ~1.6s (fast pass, often enough)
- psm=6: ~34s; psm=11: ~27s; worst case all three: ~60s per image.

## Temp files & hygiene

Watchdog writes `.ocr_*.img` / `.ocr_shot_*.png` in the repo — add `.ocr_*`
to `.gitignore`, clean leftovers after crashes. Wipe leftover temp files after
a crash before restarting the daemon.

## Telegram wiring quick facts

- Bot token + chat IDs live in the local config JSON (chmod 600, gitignored).
- Verify token first via `getMe`, send a test `sendMessage`, then restart the
  daemon — the heartbeat log shows `delivered=1` when the bot is read.
- `unset TELEGRAM_BOT_TOKEN` before running a bot that shares the Hermes
  gateway env (prevents 409/getUpdates conflicts).
