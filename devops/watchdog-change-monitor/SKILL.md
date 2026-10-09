---
name: watchdog-change-monitor
description: Silent poller that alerts only when a target changes.
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Monitoring, Watchdog, Cron, Automation, Alerts]
---

# Watchdog Change Monitor

Builds silent-unless-changed monitors for websites, GitHub files, and on-chain contracts. The script keeps last-seen state, prints NOTHING when nothing changed (so a `no_agent` cron delivers nothing), and prints a complete report only on a real diff. First run initializes baseline and stays quiet. This pattern avoids chat spam while still catching the exact moment something goes live.

Does NOT do LLM summarization per tick — pure script checks. For reasoned monitoring (e.g. "summarize what changed and whether it matters"), use an agent cron instead.

## When to Use

- "Monitor X every N minutes, kabarin kalau ada update"
- "Pasang monitor buat website/contract ini"
- Watching a launchpad/website for "Coming soon" → LIVE transition
- Watching a GitHub file for new contract addresses
- Watching an on-chain factory for newly deployed tokens
- Any recurring check where the user only wants to hear about CHANGES

## Prerequisites

- Python 3 stdlib only (`hashlib`, `json`, `re`, `urllib.request`, `os`)
- For Telegram delivery: `TELEGRAM_BOT_TOKEN` + `TELEGRAM_HOME_CHANNEL` in `~/.hermes/.env` (load via a small env parser — do NOT hardcode secrets)
- No other dependencies

## How to Run

- **Cron cadence (>= 1 min):** write the script under `~/.hermes/scripts/`, then `cronjob(action='create', no_agent=true, script='<name>.py', schedule='*/1 * * * *')`. Empty stdout = silent; non-empty stdout = delivered verbatim.
- **Sub-minute cadence (30s):** cron rejects seconds. Start a daemon with `terminal(background=true)` that loops `time.sleep(30)`, checks, and pushes to Telegram directly via `https://api.telegram.org/bot<TOKEN>/sendMessage` (urlencode `chat_id`, `text`, `disable_web_page_preview=true`).

## Quick Reference

```python
# state persistence — compare, don't refetch history
STATE = os.path.expanduser("~/.hermes/scripts/<name>_state.json")
state = json.load(open(STATE)) if os.path.exists(STATE) else {}
# ... compute new_hash / new_sha ...
if state.get("key") is not None and state.get("key") != new_val:
    changes.append("...")
state["key"] = new_val
json.dump(state, open(STATE, "w"))
```

## Procedure

1. **Decide cadence.** If the user said "setiap 30 detik", cron cannot do it — use the daemon pattern (`terminal(background=true)` + `time.sleep(30)` + direct TG send). If minutes are fine, use `no_agent` cron (simpler, self-healing, survives restarts).
2. **Write one check function per target** (site HTML, GitHub commit SHA, factory tx list). Each returns `(changes, new_state)`. Wrap each in try/except so one failing source doesn't kill the whole monitor — print the fetch failure to stderr, not stdout.
3. **First run initializes baseline silently.** Only store state; never alert on the first pass (there is no "previous" to compare against).
4. **Strip volatile tokens before hashing.** HTML pages with CSP emit a random `nonce="..."` per request — `re.sub(r'nonce="[^"]+"', 'NONCE', html)` BEFORE hashing, or every poll false-positives.
5. **Report CA/addresses directly.** For contract monitors, extract and print the new address verbatim (one per line) so the user can copy it. Full list, not a summary.
6. **Guard message length.** Telegram caps ~4096 chars. If a report can exceed that (e.g. listing 49 addresses), split into <4000-char blocks with `--- part 1/2 ---` markers so nothing truncates.
7. **Verify delivery.** After starting a daemon, send a test message via the same `tg_send` function and confirm `ok`. For cron, run the script once in `terminal` to confirm baseline + no output.
8. **Cleanup on "matikan semua".** Kill daemons with `process(action='kill', session_id=...)`, remove/pause crons with `cronjob`. Confirm with `process(action='list')` and `cronjob(action='list')`. Pause (not delete) unrelated jobs like other mint monitors unless told otherwise.

## Pitfalls

- **Hex calldata marker matching silently fails.** To detect bot-spam tokens, decode first: `bytes.fromhex(input[2:]).decode('latin1')` then match markers (`cli`, `automated`, `fast_`, `bot `, `deploy`). Matching against raw hex never hits because hex only contains `0-9a-f`.
- **Bot-farm deployer filter.** On launchpad factories, dozens of bot tokens deploy per day. Skip factory txs whose deployer `counters.transactions_count` > ~2000, and log the skip to stderr (visible in `process(action='log')`) so you can debug without spamming the user.
- **Watch pattern notifications are late duplicates.** A background daemon killed after firing `watch_patterns` may still emit a stale ALERT notification. Cross-check `process(action='list')` status before treating it as a new event.
- **Fetch errors must not corrupt state.** If a source fails, skip updating its state key — otherwise a transient failure becomes a permanent "changed" signal on the next successful run.
- **Don't re-invent state.** A fresh `json` state file per monitor beats grepping history. Keep it in `~/.hermes/scripts/`.

## Verification

```bash
# Baseline run must be silent; run twice and confirm only real diffs print:
python3 ~/.hermes/scripts/<name>.py && echo "silent (baseline ok)"
# Tamper a state value, re-run, confirm a report prints, then restore state:
cp ~/.hermes/scripts/<name>_state.json /tmp/state.bak
python3 -c "import json; s=json.load(open('..._state.json')); s['site_hash']='deadbeef'; json.dump(s, open('..._state.json','w'))"
python3 ~/.hermes/scripts/<name>.py   # expect a report
cp /tmp/state.bak ~/.hermes/scripts/<name>_state.json
```

A correct watchdog: silent on identical state, reports on diff, splits long messages, survives source failures, and cleans up when told.

## References

- `references/telegram-daemon-delivery.md` — tested Telegram bot-API delivery for sub-minute daemons: env loading, `tg_send`, daemon loop skeleton, bot-spam calldata filter, and the RPC-receipt fallback for finding a newly minted token CA when Blockscout 500s.
