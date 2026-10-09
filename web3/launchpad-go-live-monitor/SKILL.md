---
name: launchpad-go-live-monitor
description: Watch launchpads and contract files for go-live changes.
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Web3, Monitoring, Cron, Launchpad, Recon]
---

# Launchpad Go-Live Monitor

Silent watchdog for a pre-launch crypto platform (website + GitHub contract files) that alerts the user the moment something changes — teaser → live, new launcher/strategy/factory registered, new commit pushed. Built on the `cronjob` no_agent watchdog pattern: the script prints ONLY on change, so empty stdout = silent and non-empty stdout is delivered verbatim.

Does NOT trade, does NOT parse every on-chain event. It watches three static surfaces: site HTML, GitHub commit SHA, raw contract file hash. For deep token-officiality analysis, pair with `token-launch-verify`.

## When to Use

- "Kalo live kabarin ya" / "monitor tiap 10 menit" / "kabarin kalau ada update"
- A pre-launch platform has a "Coming Soon" page and contract deployments are visible on-chain
- Need to catch the moment a site flips live or an official contract CA appears without babysitting
- User wants a recurring silent check that only pings on real change

## Prerequisites

- Python 3 (stdlib only: `hashlib`, `json`, `os`, `re`, `urllib.request`)
- `cronjob` tool available (Hermes scheduler)
- No API keys — public endpoints only (site, GitHub API, raw.githubusercontent)

## How to Run

Write the script via `write_file` to `~/.hermes/scripts/<name>.py` (template: `scripts/launchpad_monitor.py`), run it once through `terminal` to initialize the baseline, then register with `cronjob`:

```
cronjob(action='create', schedule='every 10m', no_agent=true, script='<name>.py', deliver='origin')
```

no_agent=true is the whole point: the scheduler runs the script and delivers stdout verbatim; empty stdout = silence.

## Quick Reference

```bash
# Initialize baseline (first run is silent by design)
python3 ~/.hermes/scripts/<name>.py

# State file (baseline hashes live here)
cat ~/.hermes/scripts/<name>_state.json

# Manual re-check
python3 ~/.hermes/scripts/<name>.py
```

## Procedure

1. **Clone the template.** Copy `scripts/launchpad_monitor.py` and set `SITE_URL`, `GH_REPO`, `GH_PATH` (the contracts file, e.g. `sdks/liquidity-launcher-sdk/src/addresses.ts`), and a unique `STATE` path.
2. **Strip CSP nonces before hashing site HTML.** React-Router/Remix pages put a random `nonce="..."` on every tag — hashing raw HTML fires false changes on every poll. `re.sub(r'nonce="[^"]+"', 'NONCE', html)` first (this bit us live: pools.trade alerted on every run until fixed).
3. **Run once to seed the baseline.** First run stores hashes and exits silent — never let the first run alert.
4. **Register the cron job.** `cronjob(action='create', schedule='every 10m', no_agent=true, script='<name>.py', deliver='origin')`. Confirm `next_run_at` looks right.
5. **Interpret signals on alert:**
   - JS/CSS bundle hashes changed but title/teaser unchanged → team pushing pre-launch builds (prep, not live).
   - Teaser text / description changed → likely live flip; verify by fetching the page.
   - GitHub commit registers a new contract (e.g. "full-redeploy generation") → final infra confirmed; re-fetch the raw file for the new addresses.
6. **Verify after any alert.** Fetch the site and the raw file yourself before telling the user "it's live" — the watchdog only flags, it doesn't confirm.

## Pitfalls

- **CSP nonce = false positive factory.** Strip nonces before hashing or every poll reports a change. Also strip other per-request random fields if the site has them.
- **Bundle-name change ≠ live.** `root-*.js` / `entry.client-*.js` / manifest version bump with unchanged title = build deploys, not go-live.
- **GitHub moves mid-watch.** The contracts file can be updated between baseline and alert; always re-fetch raw + latest commit on alert before concluding.
- **Silent on fetch failure is deliberate.** If the site 500s or the network drops, the script should stay quiet (no error spam) — the next successful poll will catch a real change.
- **First run must be silent.** If you test after seeding and it reports the baseline as a "change", the nonce strip is missing.
- **Public endpoints rate-limit.** GitHub API unauthenticated allows ~60 req/hr; a 10-min poll cadence is fine, but don't poll sub-minute.

## Verification

```bash
# Run twice; the second run must print nothing (state unchanged):
python3 ~/.hermes/scripts/<name>.py && echo "second run output: [$(python3 ~/.hermes/scripts/<name>.py)]"
```

A correct setup prints `second run output: []` — confirming baseline is stable and only real changes will alert. Then touch the state file's `raw_hash` to a wrong value and re-run: it should print an alert line (change detection works).
