# Daily Powerstone ledger (no mandatory /sync)

## Product rule (Webnovel)

> You will get a fixed amount of Power Stones daily at **0:00 (UTC+8)** based on your user level.

## User requirement

Dez: bot must show remaining PS **without requiring `/sync`** first.

## Design

Timezone for day key: **Asia/Shanghai (UTC+8)** — matches Webnovel grant clock (not Jakarta for ledger day).

### Tables

`daily_power(email, day, total_power, used_power, remaining_power, updated_at)`  
`account_meta(email, last_total_power, last_level, updated_at)` — remembers last known daily grant

### Auto-seed

On `pool_remaining(emails)` / status / novel card:

1. For each account missing today's row, insert:
   - `total = last_total_power or 1` (new accounts typically get 1)
   - `used = 0`
   - `remaining = total`
2. Sum remaining/total for UI

### Consume

On successful power vote: `add_used(email, n)` decreases remaining for today.  
If row missing, seed then consume.

### Create

After successful `/create`, `seed_new_account(email, total=1)`.

### `/sync` role

Optional live re-check via `userInfoAjax` / `getRewardVotingPopup`.  
Updates ledger with real `availablePower` / totals.  
Do **not** block card UX on full live probe.

## Pitfalls

- Do not use `Asia/Jakarta` for the **day key** if matching Webnovel grant; use UTC+8.
- Auto ledger can drift if Webnovel grant amount changes by level — `/sync` corrects.
- Never invent remaining from account count alone without per-email used tracking.

## Files

- `/root/webnovel-tg-bot/db.py` — `power_today()`, `ensure_daily_for_accounts`, `seed_new_account`
- `/root/webnovel-tg-bot/bot/main.py` — `pool_snapshot()`
