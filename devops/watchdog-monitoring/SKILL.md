---
name: watchdog-monitoring
description: Silent change monitors via cron or background daemon.
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Monitoring, Cron, Watchdog, Telegram, Alerting]
---

# Watchdog Monitoring (silent-until-change)

Build recurring monitors that stay SILENT when nothing changed and print a self-contained alert only on a real diff. Default delivery: cron `no_agent=True` with a script whose empty stdout = silent, non-empty stdout = delivered verbatim. For sub-minute intervals, use a background daemon that posts directly to Telegram.

Does NOT babysit jobs: it codifies the state-file diff pattern, the false-positive traps (CSP nonces, deploy manifests), and the sub-minute daemon escape hatch.

## When to Use

- "Cek tiap X menit" / "monitor ini" / "kabarin kalau ada update"
- Watch a website teaser → live transition, a GitHub file, or an on-chain contract/factory
- Any recurring alert job where you must NOT spam when nothing changed
- Polling faster than cron supports (cron floor = 1 minute)

## Prerequisites

- `~/.hermes/scripts/` for scripts + JSON state files (cron `script=` resolves relative paths there)
- For Telegram direct send: `TELEGRAM_BOT_TOKEN` + `TELEGRAM_HOME_CHANNEL` in `~/.hermes/.env` (load via a tiny env parser; never hardcode)
- `cronjob` tool for schedules; `terminal(background=true)` for daemons

## Quick Reference

```bash
# cron: silent watchdog (empty stdout = no delivery, non-empty = delivered)
cronjob action=create no_agent=true script=watch.py schedule="*/1 * * * *" deliver=origin

# state file: ~/.hermes/scripts/<name>_state.json — JSON of last-seen values

# Telegram direct send (daemon mode)
curl -s "https://api.telegram.org/bot<TOKEN>/sendMessage" \
  -d "chat_id=<CHAT>&text=<MSG>&disable_web_page_preview=true"

# strip per-request noise before hashing (React/Remix CSP nonce)
html2 = re.sub(r'nonce="[^"]+"', 'NONCE', html)
```

## Procedure

1. **Write the watchdog script** in `~/.hermes/scripts/<name>.py`:
   - Load state JSON if it exists; else start empty.
   - Fetch target(s), normalize, hash or store a key value.
   - Compare with stored state; if different, append a human-readable change line.
   - Save the new state (even on first run).
   - Print the full report only if changes exist; otherwise print nothing.
2. **Baseline first run**: run once manually so the state file is written and the first cron tick doesn't alert on the initial snapshot.
3. **Create the cron job**: `no_agent=true` (stdout IS the message), `schedule` cron-expression or `every Nm`, `deliver=origin` to return to the requesting chat. Interval floor is 1 minute.
4. **Sub-minute (e.g. every 30s)**: cron rejects `"30s"`. Start a background daemon: `terminal(background=true)` running a loop with `time.sleep(30)` + `tg_send()` via the bot API. Kill the old daemon session BEFORE starting a new one (restart leaks duplicate alerters). Use `process(action=list)` to confirm only one runs.
5. **Anti-truncation**: Telegram hard-caps ~4096 chars. Split long reports into `--- part N/M ---` blocks of ≤4000 chars; the daemon/cron delivers each block.
6. **Filter spam sources** (e.g. on-chain factory monitors): skip alerts whose subject matches a known bot pattern — decode calldata and match markers on the DECODED text (never on the hex string: hex only contains 0-9a-f, so ASCII markers like `cli`/`fast_` never match), and check the deployer's `counters.transactions_count` (>~2000 = bot farm, skip).

## Pitfalls

- **CSP nonces cause false positives.** React/Remix pages put a random `nonce=` on every element per request. Hash AFTER stripping nonces, or every poll reports a "change".
- **Hash changes can be deploy noise.** New hashed JS/CSS bundle names (`root-<hash>.js`) or a bumped `manifest-<hash>.js` version mean a REAL deploy — treat as signal, but strip per-request nonces first. Also `react-router` stream chunks are identical after nonce-strip.
- **Match markers on decoded text, not hex.** `bytes.fromhex(input[2:]).decode('latin1')` then search — searching the hex itself for `"cli"` always misses.
- **Cron interval floor is 1 minute.** `"30s"` → error. Use the daemon path for faster polling.
- **Daemon restart leaks duplicates.** Kill the old `session_id` via `process(action=kill)` before relaunching; verify with `process(action=list)`.
- **State write ordering.** Save state AFTER deciding to alert, and keep the save in both branches (alert + silent) so the next tick compares against the latest snapshot.
- **GitHub API rate limits.** Unauthenticated commits polling = 60 req/hr. Polling `commits?path=...` every minute will 403 eventually — consider caching or longer intervals.
- **Blockscout/explorer flakiness.** Tx-detail endpoints can 500 on fresh txs (retry/backoff); pagination often 422 — use `filter=to`/`filter=from` and `counters` instead of `?page=N`.
- **Fetch failures should stay silent.** Wrap each fetch in try/except and skip on error — a transient network blip shouldn't page the user.

## Verification

Run the script twice with a tampered state (e.g. set `site_hash` to a dummy value) — the first run after tampering must print a diff, and a second run (state now current) must print nothing. That proves baseline + diff + silence all work.

## Event feeds vs silent watchdogs (choose deliberately)

Silent-until-change is the right default for price/status monitors. It is **wrong** when the
user is validating a pipeline and wants to watch it run. When the user says
"kasih notif **tiap** <event>" ("notify me on every …"), build a per-event feed — do not impose
silence. Silence is a choice the user makes, not a default you assume on their behalf.

Per-event feed shape (proven on a long-running bot fleet):

- **Tail the producer's own log** instead of re-deriving state. Keep a byte `offset` per log file
  in the state JSON, read only the new chunk, and split on `[\r\n]+` — progress writers often
  emit bare `\r` and produce one giant line. Regex the events out of the split tokens.
- **Dedupe on a hash of the matched line**, appended to a capped `seen` list (last ~800).
  Survives monitor restarts with zero replay. Handle rotation: if `size < offset`, reset the
  offset to 0.
- **One message per event**, carrying the identifiers a human needs (counter, id, result, the
  producer's own numbers) — not a digest.
- **Layer exception alerts on top of the feed**: transport errors, denials, process death, and a
  run-complete summary.
- **Cooldown repetitive classes.** A retry loop can emit hundreds of identical events; keep one
  alert per error code per ~5 min with the timestamp in state, or you train the user to ignore
  the channel.
- Also verify the notification actually left: log the send result (`discord sent` / `SENT FAILED`)
  and grep it, rather than assuming the message arrived.

### Discord webhook as an alert rail

The user may hand you a webhook URL instead of a bot token. It is the simpler rail — use it.

```bash
curl -s -o /dev/null -w '%{http_code}' -m 25 -X POST "$WEBHOOK" \
  -H 'Content-Type: application/json' -d '{"content":"...","username":"..."}'
```

- **`204` = accepted.** Any other code is a failure; log it.
- Message cap is 2000 chars — slice to ~1900.
- Build the JSON body with the language's JSON encoder, not string concatenation, so embedded
  quotes/newlines can't break the payload.
- Store the webhook in the shared secrets file (`~/.hermes/.env`) as its own key and read it from
  there; never inline it in the script or in a note.

## Supervising long-running workers

- **Spawn each worker as its own transient unit, not as a child of the supervisor** (e.g.
  `systemd-run --user --unit <name>`). Otherwise restarting the supervisor kills every worker it
  launched — a `start_new_session`/process-group detach is **not** enough (cgroup inheritance).
- **Liveness = log mtime + a real `ps` match on the identity flag** (keyfile/config path), never a
  stored pid alone. Stale pid files produce false death reports *and* duplicate workers.
- **Require a heartbeat** from the worker (~every 20 s) before letting a supervisor judge
  staleness. Quiet phases longer than the staleness window are normal for workers that walk,
  wait, or sleep — a naive threshold kills healthy processes. Heartbeat first, threshold second.
- **Never restart or reconfigure a worker that is mid-flight.** A worker that rebuilds its
  position/session from an exit IP or a server-side cursor will jump or lose progress on
  restart; swapping its proxy mid-run can move it to another city. Restart only on proven death
  and extend the pool by adding *idle* workers instead.
- **Mark work complete only after verified success**, never before execution — pre-marking a
  money-move as "handled" while it was still in dry-run silently stranded capital and dropped a
  fleet from 10 workers to 9. On failure: mark, alert loudly, and do **not** auto-retry money.
- **Kill by PID.** `pkill -f <script>` matches the supervising shell's own command line and kills
  it too.
- After restarting a supervisor, confirm the new code is live by reading *its* log — an exit code
  of 0 does not prove the new code path ran.
- **Long-lived monitors and guards belong under a service manager, not `screen`.** Observed: a
  `screen`-hosted notifier and a `screen`-hosted guard both vanished silently — no traceback, no
  OOM in `dmesg`, no reboot (uptime 26 days), empty redirect logs — and nothing detected it for
  ~19 minutes while the worker kept running unprotected. Promote them to `systemd --user` units
  with `Restart=always` + `RestartSec=15`, `StandardOutput/StandardError=append:<repo>/logs/…`,
  and `loginctl enable-linger <user>` so the user manager survives logout/reboot. `screen` is for
  a live debug session, not for the process that has to be alive at 03:00. Verify with
  `is-active` **and** `is-enabled` **and** a PID listing.
- **Template units scale per identity for free.** Use `<proj>-guard@.service` with
  `ExecStart=… --slot %i …`; onboarding a new slot becomes
  `systemctl --user enable --now <proj>-guard@4` instead of a bespoke unit file each time.
- **Two supervisors with opposite goals must never be armed together.** An auto-restart watchdog
  will resurrect the worker that a kill-guard just terminated for an anti-cheat/validation
  rejection — straight back into the same rejection, burning quota or rate limit for nothing.
  Choose deliberately: **kill-guard ON + watchdog OFF** when the failure is a hard contradiction
  that retry cannot fix; **watchdog ON, no guard** when failures are crashes/network deaths.
  Tell-tale that a *watchdog* restarted a worker rather than a human: the command line shows
  **default** flags where you had tuned yours — so read the running process's argv, not the
  launcher script, to find out which supervisor is actually live.
- **Stopping order is guard-first, then worker.** Kill the thing that can restart the worker
  before killing the worker, then verify across every layer — service manager, PID-exact process
  listing, session list, cron/unit list. A single check is not a stop.
- **A monitor that only notifies cannot also be the thing that heals.** When both duties are
  wanted, run them as separate units and make the notify-only one explicitly non-restarting
  (a config flag such as `*_WATCHDOG=0`), so the pair cannot fight.

Canonical detail for the two sections above lives with the worker-side skill, so keep them in
sync instead of re-deriving the recipe here: `go-binary-daemon` →
`references/per-item-notification-feed.md` (result-line regex with a negative-case sanity test,
hash dedupe, proof-by-grepping the send log, escalation glyphs, per-error cooldown, Discord
`204` transport) and `references/vendor-operator-package-port.md` (fleet layout, one identity
per IP, capital rotation, zero-output triage order). This skill owns the *monitor* framing;
that one owns the worker/fleet framing.

## X-scrape + OCR invite-code watchdogs

For watchers that scrape an X/Twitter account for invite-code posts (text or image), validate against a claim backend, and claim wallet spots FCFS — see `references/x-scrape-ocr-invite-codes.md`. Key traps it covers: X lazy-renders tweets until scroll (health check must scroll before counting `article[data-testid="tweet"]`), codes embedded in images need tesseract OCR + `:`/space→`-` normalization, and mint/whitelist claim backends are often Google Apps Script endpoints embedded as `const ENDPOINT = "https://script.google.com/macros/s/.../exec"` in the frontend HTML (always follow the 302).
