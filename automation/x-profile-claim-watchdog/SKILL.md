---
name: x-profile-claim-watchdog
description: Watch X profiles for invite codes and auto-claim wallets.
version: 1.0.0
author: spring
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [x, twitter, playwright, watchdog, claim, whitelist, bufo, wallet]
    related_skills: [go-binary-daemon, web3-farmer-bot, obsidian]
---

# X Profile Claim Watchdog

Watch a public X profile for posts containing invite codes (`BUFO-*` style), validate each new code against a claim backend, and submit generated EVM wallet addresses first-come-first-served. Reference implementation: `asbryx/bufos-watchdog` at `/root/bufos-watchdog` (screen `bufos-watchdog`).

## Architecture

```
X profile (Playwright + auth_token/ct0 cookies)
  → random poll 10-20s → parse codes from tweets of target account
  → dedupe (seen/codes/pending_codes in state json)
  → check code on backend (sub-second retry while invalid)
  → claim pending wallets in parallel workers
  → persist claims atomically (skip already-successful wallets on restart)
  → screenshot ticket + optional Telegram notify
```

## Setup

```bash
git clone https://github.com/OWNER/REPO.git /root/REPO
cd /root/REPO
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
cp bufos_watchdog_config.example.json bufos_watchdog_config.json
cp profiles.example.json profiles.json
```

## Finding the claim backend without docs

Backend may be embedded in the site's frontend instead of documented:
- `curl -sSL <site>` → grep for `ENDPOINT` / `const ENDPOINT = "https://..."` / `fetch(`.
- thebufos.com served one inline `<script>` with `const ENDPOINT = "https://script.google.com/macros/s/.../exec"`.
- **Google Apps Script endpoints return HTTP 302 first** — always curl with `-L` to follow the redirect to `script.googleusercontent.com`.

Protocol the watchdog expects (verify with curl before wiring):
- `GET <endpoint>` → `{"ok": true}` (health)
- `POST {"action":"check","code":"BUFO-XXX"}` → `{"ok":true,"remaining":N}` or `{"ok":false,"reason":"invalid|full|sold_out"}`
- `POST {"action":"claim","code":"BUFO-XXX","wallet":"0x..."}` → `{"ok":true,"number":N,"codename":"..."}` or duplicate

## X session injection

Profile JSON needs `auth_token` + `ct0` (from browser cookies — the Netscape cookie file / DevTools). The bot injects them as Playwright cookies on `.x.com`:
```python
await context.add_cookies([
    {"name": "auth_token", "value": auth_token, "domain": ".x.com", "path": "/"},
    {"name": "ct0", "value": ct0, "domain": ".x.com", "path": "/"},
])
```
Only the monitor profile's cookies matter; other profiles just need wallets.

## X lazy-render pitfall (critical)

X renders timeline tweets **only after a scroll**. Counting `article[data-testid="tweet"]` right after `goto/reload` returns 0 → watchdog marks session "unhealthy" and skips parsing forever. Fix: before counting, scroll once + wait for first article visible, then scroll back to top:
```python
await page.evaluate("window.scrollTo(0, 900)")
await page.locator('article[data-testid="tweet"]').first.wait_for(state="visible", timeout=8000)
await page.evaluate("window.scrollTo(0, 0)")
```
Also bump post-reload wait (2.5s → ~4.5s initial).

## Wallet generation + secret hygiene

- `from eth_account import Account; acct = Account.create()` per wallet (pip install eth-account).
- Write addresses to `file.txt` (one per line, safe to share) and `{address, private_key}` to `wallet_keys.json` with `chmod 600`.
- Add BOTH to `.gitignore` — the default gitignore does NOT cover them. Never put private keys in the repo; the watchdog only needs addresses.

## Linux port (repo may be Windows-oriented)

- `SingleInstance` using `msvcrt` (Windows-only) → `ModuleNotFoundError: msvcrt` on start. Patch to: on `os.name == "nt"` use `msvcrt.locking`, else `fcntl.flock(fd, LOCK_EX | LOCK_NB)` (and `LOCK_UN` on exit).

## Run as daemon

```bash
# start.sh: exec .venv/bin/python bufos_watchdog.py 2>&1 | tee -a bufos_watchdog_console.log
screen -S bufos-watchdog -X quit 2>/dev/null; sleep 1
screen -dmS bufos-watchdog /root/REPO/start.sh
sleep 10 && screen -ls | grep bufos && tail -20 bufos_watchdog_console.log
```
Health check: `bufos_watchdog_state.json` → `twitter_health.status` should be `ok` with `article_count > 0`. Log lines "Poll OK: no new code" = healthy.

## Pitfalls

1. **"unhealthy" right after start is the lazy-render bug, not an expired cookie** — apply the scroll fix before suspecting the session.
2. **A code can be `full` before the watchdog detects it** — backend returns `{"ok":false,"reason":"full"}` and 0 claims is correct behavior, not a bug. Report honestly; never fabricate claims.
3. **Hermes lifecycle guard `embedded null byte`** — running `.venv/bin/python some_script.py` via the terminal tool can crash the guard. Run logic in `execute_code`, or via `start.sh` under screen. See `go-binary-daemon` pitfalls 7-8.
4. **Apps Script self-test subprocess may hang** on cold start — re-run the same asserts in-process via execute_code.
5. **Telegram optional** — empty bot token = local logs only; optionally wire bot + chat ID (`telegram_bot_token`, `telegram_chat_ids`) for heartbeat + ticket screenshots.

## Verification

- `curl -sSL <endpoint>` → `{"ok": true}`.
- `POST check` returns JSON (not HTML 302 — follow redirects).
- Self-test asserts: unique valid `0x[a-fA-F0-9]{40}` wallets, code regex, poll ranges.
- Live `--once` run: state json gains a `codes` entry with tweet_id + backend `last_result`.

## References

- `references/bufos-watchdog-verified.md` — verified instance: endpoint discovery transcript, Apps Script 302 quirk, lazy-render before/after, healthy state JSON shapes.

See also: `web3-farmer-bot` (SIWE/Turnstile farming patterns), `go-binary-daemon` (screen daemon lifecycle + Hermes guard workarounds).
