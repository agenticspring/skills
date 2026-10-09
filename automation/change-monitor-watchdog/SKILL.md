---
name: change-monitor-watchdog
description: Silent stateful monitors that alert only on change.
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Monitoring, Cron, Watchdog, Telegram, Web3]
---

# Change Monitor Watchdog

Builds silent stateful monitors that poll websites, GitHub files, and on-chain
contracts, and only notify the user when something actually changed. The
"watchdog" pattern: empty output = nothing to report (no spam); non-empty output
is delivered verbatim to the chat.

Used for teaser→live site transitions ("coming soon" → launched), contract
address file updates, new-token deploys, mint counts, price thresholds — any
recurring "tell me when X changes" request.

## When to Use

- "Monitor situs ini, kabarin kalau ada update" / "cek tiap N menit"
- Tracking a staged launchpad/website until it goes live
- Watching a GitHub repo file (addresses.ts, config) for new commits/content
- Watching a factory/contract for new deployments
- Any recurring polling the user wants delivered to Telegram/Discord without noise

## How to Run

1. Write a Python watchdog script into `~/.hermes/scripts/<name>.py` via
   `write_file`.
2. Create a cron job with `cronjob` — `no_agent=true`, `script=<name>.py`,
   `deliver=origin`, `schedule` like `*/1 * * * *` or `every 10m`.
3. First run initializes the baseline state file and stays silent. Later runs
   print a report ONLY when a watched value differs from state.

## Quick Reference

```python
STATE = os.path.expanduser("~/.hermes/scripts/<name>_state.json")

def check(state):
    changes = []
    new_state = {}
    # ... poll each source, compare to state, append to changes ...
    return changes, new_state

def main():
    state = load(STATE)           # {} if missing
    changes, new_state = check(state)
    save(STATE, new_state)
    if changes:                   # silent when nothing changed
        print("🔔 <NAME> — update terdeteksi:")
        for c in changes:
            print("•", c)
```

## Procedure

1. **Decide sources** — pick from: homepage HTML, GitHub commit SHA, raw file
   content hash, on-chain factory transactions. Each is one probe block with its
   own try/except (a fetch failure must NOT kill the other probes).
2. **Hash HTML with nonces stripped.** Next.js/Cloudflare pages rotate
   `nonce="..."` on EVERY request — without stripping, every poll is a false
   "changed". `html = re.sub(r'nonce="[^"]+"', 'NONCE', html)` then sha256.
3. **GitHub**: `https://api.github.com/repos/<org>/<repo>/commits?path=<file>&per_page=1`
   → compare `sha`. Raw content: hash
   `https://raw.githubusercontent.com/<org>/<repo>/main/<file>`.
4. **On-chain new deploy**: blockscout
   `/api/v2/addresses/<FACTORY>/transactions?filter=to` → newest tx hash → if
   differs from state, fetch `/api/v2/transactions/<HASH>/internal-transactions`
   → `created_contract.hash` = the new CA. Report the CA directly.
5. **Bot-spam filter (token factories)**: decode calldata strings for CLI/auto
   markers (`cli`, `automated`, `bot`, `fast_`, `deploy`) and check the deployer's
   `/counters` `transactions_count` — >2000 txs = bot farm, skip. Prevents alert
   spam from front-run bots.
6. **Long-message safety**: Telegram caps at 4096 chars. Split output at ~4000
   with a `--- part 1/2 ---` marker so nothing truncates.
7. **Cron cadence**: `*/1 * * * *` is the minimum; cron cannot express seconds.
   For sub-minute, run a background daemon (`terminal` `background=true`) with
   `time.sleep(30)` that posts via `api.telegram.org/bot<TOKEN>/sendMessage`
   (token + `TELEGRAM_HOME_CHANNEL` from `~/.hermes/.env`).

## Pitfalls

- **Never alert on the first run** — that's a baseline, not a change.
- **CSP nonce rotation** — the #1 false-positive source for Next.js/Cloudflare sites.
- **Fetch failures must be silent** — a transient network error is not "site changed"; let the next tick retry.
- **Stop/cleanup**: `cronjob` remove + `process` kill for daemons. Kill daemons by session_id, never broad `pkill`.
- **Watch for overlap with existing monitors** — list cron jobs (`cronjob` action=list) before creating a duplicate.

## Verification

```bash
python3 ~/.hermes/scripts/<name>.py   # exit 0, no output on first run (baseline)
python3 ~/.hermes/scripts/<name>.py   # still silent if nothing changed
cat ~/.hermes/scripts/<name>_state.json  # state file written with current values
```
