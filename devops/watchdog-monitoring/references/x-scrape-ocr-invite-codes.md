# X/Twitter Scrape + OCR Invite-Code Extraction (BUFOS-style)

Proven 2026-08-09 while porting `asbryx/bufos-watchdog` to Linux. Class of task: watch an X account for invite-code posts (text OR image), validate against a claim backend, claim wallet spots FCFS.

## 1. X lazy-render pitfall (CRITICAL)

X timeline tweets render **lazily on scroll**. `page.locator('article[data-testid="tweet"]').count()` returns **0** right after `goto`/`reload` even when the account HAS posts, because the browser hasn't scrolled to trigger render. A health check that counts articles before scrolling reports false "unhealthy" (`timeline_has_no_tweet_articles`) and skips the scrape step entirely — real code posts get missed.

Fix — scroll before counting:

```python
await page.evaluate("window.scrollTo(0, 900)")
await page.locator('article[data-testid="tweet"]').first.wait_for(state="visible", timeout=8000)
await page.evaluate("window.scrollTo(0, 0)")
articles = await page.locator('article[data-testid="tweet"]').count()
```

Verified: after patch, health flips to `ok` (article_count=4), continuous "Poll OK" cycles. The `scrape_events` function already scrolled — the bug was only the health check that gates it.

## 2. OCR: extract code from tweet image

Codes are often **inside the tweet image** (stylized font), not the text body.

1. Media container: `div[data-testid="tweetPhoto"]` (NOT `article[data-testid="tweetPhoto"]` — that compound selector misses).
2. Get image src: `img` inside tweetPhoto, src like `https://pbs.twimg.com/media/XXXX?format=jpg&name=small`. Fetch full-res with `&name=orig` via `page.request.get(src)` (Playwright APIRequestContext — avoids CORS).
3. Preprocess + OCR (tesseract 5.x + Pillow):
   - grayscale → `ImageOps.autocontrast` → 2x upscale (LANCZOS) → binary threshold ~140 (`point(lambda p: 255 if p > 140 else 0)`)
   - `tesseract <img> stdout --psm 6` (fallbacks: 11, 3)
4. **Normalize OCR output before regex**: stylized fonts make tesseract read hyphens as `:` or spaces — `BUFO: SLEEP` / `BUFO- SLEEP` instead of `BUFOS-SLEEP`. Regex that worked: `\bBUFO[A-Z0-9_\-:\.']*\b` then normalize `:`/space → `-`, or strip hyphens/spaces/colons before comparing.
5. Upscaling 2x on a large image can make tesseract exceed 60s — OCR the raw image first, only upscale if nothing found.

Verified: `BUFO-LEGEN` (text post) detected → backend said `full` (correct). `BUFOS-SLEEP` (image-only) OCR'd as `BUFO: SLEEP` → detected after normalization. Ticket screenshots (boarding-pass style) OCR'd as text, no code.

## 3. Google Apps Script backend discovery (from frontend HTML)

Mint/whitelist sites are often vanilla HTML+JS with an Apps Script backend. The endpoint URL is embedded in the frontend:

```html
const ENDPOINT = "https://script.google.com/macros/s/AKfycbw.../exec";
```

- Grep the HTML for `ENDPOINT` / `const ENDPOINT`.
- **Apps Script returns HTTP 302 first** (redirect to `script.googleusercontent.com/macros/echo?...`) — always follow redirects (`curl -sSL`). A 302 without following looks like a dead endpoint.
- Health: `GET <endpoint>` → `{"ok": true, ...}`.
- Protocol:
  - check: `{"action":"check","code":"BUFO-XXX"}` → `{"ok":true,"remaining":N}` | `{"ok":false,"reason":"invalid|full|sold_out"}`
  - claim: `{"action":"claim","code":"BUFO-XXX","wallet":"0x..."}` → `{"ok":true,"number":N,"codename":"..."}` | `{"ok":false,"reason":"duplicate"}` (duplicate = success, backend already recorded it)

## 4. Self-test validation via execute_code

The binary's `--self-test` subprocess can hang (Apps Script cold start + subprocess timeout). Equivalent evidence without subprocess: run the same asserts in-process via `execute_code` — wallet regex `0x[a-fA-F0-9]{40}` uniqueness, poll-range uniformity, `extract_codes` behavior, endpoint GET. Manual validation of the same checks is a valid replacement for the self-test gate.

## 5. Telegram wiring verification

- Validate token: `GET https://api.telegram.org/bot<TOKEN>/getMe` → `{"ok":true}`.
- Test send: `sendMessage` to chat_id before restarting the daemon.
- Confirm wiring after restart: log line `Telegram heartbeat delivered=1` (delivered=0 = chat_ids not discovered yet, wait for next 60s heartbeat).
- Store token + chat_ids in config JSON chmod 600, gitignored.

## Session artifacts

- Repo: `/root/bufos-watchdog` (screen `bufos-watchdog`, start.sh → `.venv/bin/python bufos_watchdog.py`)
- Obsidian: `Operations/BUFOS Watchdog Setup.md`
- Config: `bufos_watchdog_config.json`, `profiles.json` (100 wallet profiles + X auth_token/ct0), `wallet_keys.json` (chmod 600) — all gitignored
