# Create delay + concurrent ops with Powerstone

## Create delay (same UX as Powerstone)

User requirement: delay antar akun on `/create`, not a fixed cap and not start-then-burst.

Flow:
```
/create N
→ delay keyboard (Now / 1m / 5m / … / Custom)
→ start_create_job(n, delay_s, delay_tok)
→ create_accounts(..., delay_s=...)
→ env CREATE_DELAY_S=delay_s into signup.py
→ after each account: print delay, sleep 1s chunks (Stop-friendly)
→ next account
```

Semantics:
```
akun1 selesai → nunggu delay → akun2 → …
```
No sleep before first account. No sleep after last.

## Soft timeout
Approx `min(8h, max(15m, N * (240 + delay_s)))` seconds.

## Concurrent create + other bot actions

Allowed:
- create running + Powerstone / bookmark / `/sync` / `/status`

Why safe enough:
- create = background `asyncio.create_task` + child `signup.py`
- bot has `concurrent_updates=True`
- PS/bookmark use sticky sessions per email

Blocked:
- second concurrent create job

Risks (not crashes, quality):
- denser proxy / IMAP / captcha load
- higher CF chance if both mass-run without delay
- progress message edits can compete

Recommendation when both heavy:
- keep delay on create
- keep inter-account delay on PS
- avoid dual mass bursts

## Progress UI looks "stuck" after Registration submitted

Common false alarm after `/create`:

```
✅ Registration submitted
… UI freezes on that line for a long time …
[imap] polling................. timeout
❌ Not counted as success because confirm/login finalization failed
⏳ Delay Ns before next account…
```

Meaning:
1. Register **did** succeed
2. Process is **IMAP-waiting** for activation mail (default ~120s) — low CPU, PID alive
3. IMAP progress is often printed as **same-line dots** without newlines → TG stream (line-based) does not refresh
4. On timeout, account is **not** success-saved; then inter-account delay still applies (including after fail)

Do **not** diagnose this as freeze/crash if signup PID is alive.

Improvements when touching create UX:
- print IMAP status with newlines every few seconds (`waiting email 30/120s`)
- distinguish statuses: register → waiting email → confirm → avatar
- optional: only apply delay after success (if user wants)

## Soft timeout note
When delay is large (e.g. 300s) and N is large, total runtime ≈ N*(register+IMAP+avatar+delay). Expect multi-hour batches.