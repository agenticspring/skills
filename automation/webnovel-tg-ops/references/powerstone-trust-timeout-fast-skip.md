# Powerstone trust-timeout fast skip

## Symptom
Telegram progress appears stuck on a line like:

```text
⚡ Powerstone 3/10
→ vote: alessandrorossi81 (ledger sisa 1)
Delay: 0s · ▶️ running
```

Live logs show repeated trust polling:

```text
🔐 Untrusted device — requesting trust email...
📧 Trust email sent, waiting OTP...
[trust] polling OTP email...
timeout
```

## Root cause
A cold/rebound account entered Webnovel trust-email gate (`11318`). The old Powerstone path used the normal session recovery trust timeout (~120s) and could retry/rotate, so one account could hold the whole Powerstone job for minutes while the UI still displayed the same `vote:` account.

This is not proxy 407, not CF/no-csrf, and not a Telegram crash.

## Correct behavior for Powerstone
Powerstone is a fast ledger-driven operation. It should not spend minutes on one cold account.

Recommended behavior:
1. Use short `trust_timeout` for `vote_power` (~20s).
2. If `11318` remains after short wait, raise/skip this account.
3. Continue to the next `daily_power.remaining_power > 0` candidate.
4. Keep longer trust handling for `/sync` or explicit relogin flows where recovery is the task.

## Verification pattern
- Check `action_log` latest `power` row for `success/requested/acted/stopped`.
- If DB has no final row but Telegram shows running, inspect `logs/bot-screen.log` for `Untrusted device` / `[trust] polling OTP`.
- After patch, a trust-gated account should consume ~20s, not 2–6 minutes.
