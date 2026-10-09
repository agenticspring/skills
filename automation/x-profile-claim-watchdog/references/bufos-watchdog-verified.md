# bufos-watchdog verified instance (2026-08-09)

Live evidence from the reference implementation at `/root/bufos-watchdog`.

## Endpoint discovery (thebufos.com)

The claim backend was NOT documented — it was embedded in the site frontend:

```bash
curl -sS -m 20 -o home.html -L https://thebufos.com/
grep -oE '.{120}ENDPOINT.{200}' home.html
# const ENDPOINT = "https://script.google.com/macros/s/AKfycbwmOPq-9jKPDXRYVojieY5Nd7VXkoLI788yZgn4vOrWjHUqARilEqP8pQIgaArccEw-2g/exec";
```

Site title: `THE BUFOS — Whitelist Mint`. One inline `<script>` block; no external JS.

## Google Apps Script redirect quirk

`curl <endpoint>` (no -L) returns **HTTP 302** with HTML body (`Moved Temporarily` + `script.googleusercontent.com/macros/echo?...`). The actual JSON only appears after following the redirect:

```
GET (with -L)  → {"ok":true,"message":"Bufos whitelist back end is live."}  200
POST check BUFO-TEST1 → {"ok":false,"reason":"invalid"}  200
POST check BUFO-FAKE  → {"ok":false,"reason":"invalid"}  200
POST check BUFO-LEGEN → {"ok":false,"reason":"full"}  200
```

Frontend claim flow confirmed: `{action:"check", code}` then `{action:"claim", code, wallet}`;
response on success `{ok:true, number:N, codename:"..."}`; duplicate returns same with `reason:"duplicate"`.

## Lazy-render diagnosis transcript

Pre-fix: `articles: 0`, `login inputs: 0`, URL `https://x.com/THEBUFOS`, title OK. Body nav rendered but tweets absent → watchdog falsely "unhealthy", `scrape_events` never called.

Post-fix (scroll + `wait_for` visible): `article_count: 4`, `own_status_links: 1`, health `ok`, log `Poll OK: no new @THEBUFOS code` every cycle.

## State health shape (healthy daemon)

```json
"twitter_health": {
  "status": "ok",
  "reason": "timeline_readable",
  "consecutive_empty_polls": 0,
  "last_ok_at": 1786262048,
  "article_count": 4,
  "own_status_links": 1
}
```

## Codes state shape (detected code)

```json
"codes": {
  "BUFO-LEGEN": {
    "tweet_id": "2086332276644962574",
    "source_url": "https://x.com/THEBUFOS/status/2086332276644962574",
    "tweet_text": "...",
    "first_seen": 1786261523,
    "attempts": 1,
    "status": "full",
    "last_result": {"ok": false, "reason": "full"}
  }
}
```

## Key numbers

- 100 generated wallets: `file.txt` (addresses) + `wallet_keys.json` (chmod 600).
- Default config: poll 10–20s random, claim_workers 12, screenshot_workers 3, invalid_retry 0.3s, invalid_code_retry_seconds 600.
- `--once` = one live polling cycle then exit (useful smoke test).
