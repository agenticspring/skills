# Powerstone ledger-first vote (2026-07-21)

## User signal
Power amount small (e.g. 3) but TG job waits a long time.  
Ask: “kenapa harus coba 1–1? skip yang sudah power hari ini.”

## Bug shape
`execute_power` used to:
1. Iterate **all** pool accounts
2. Call live `get_power_balance` (session restore/login + userInfoAjax) each
3. Then vote on those with `available_power > 0`

With ledger roughly `used=100, remaining_accounts≈13`, amount=3 still paid login/CF cost on many zeros.

## Fix shape
1. `pool_snapshot()` for remaining/total (ledger, Asia/Shanghai day)
2. `accounts_with_remaining(emails)` → only `remaining_power > 0`
3. Vote only that ordered list (`use=1` per account typically)
4. Success → `add_used`
5. Live fail / no PS → `mark_empty` so next skip
6. Full live refresh **only** if ledger remaining ≤ 0

## Code
- `/root/webnovel-tg-bot/db.py` — `accounts_with_remaining`, `mark_empty`
- `/root/webnovel-tg-bot/bot/main.py` — `execute_power` ledger-first

## Verify
```bash
cd /root/webnovel-tg-bot && .venv/bin/python - <<'PY'
from db import Store
from wn.client import load_accounts
store=Store()
accs=load_accounts()
c=store.accounts_with_remaining([a.email for a in accs])
print(len(accs), 'pool', len(c), 'candidates', c[:5])
PY
```

After restart single `webnovel-tg`, amount=3 should attempt ~3 votes, not scan whole pool first.
