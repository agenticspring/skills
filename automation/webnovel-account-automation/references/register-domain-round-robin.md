# Register domain round-robin

## Active domains (2026-07-22+)
- `<REDACTED>`
- `<REDACTED>`
- `<REDACTED>`

Legacy `<REDACTED>` is **retired for new creates**. Existing accounts in `accounts.txt` keep their old domain; do not mass-rewrite.

## Config
```env
DOMAIN=<REDACTED>
DOMAINS=<REDACTED>,<REDACTED>,<REDACTED>
```

Set in:
- `/root/webnovel-autoreg/.env`
- `/root/webnovel-tg-bot/.env`
- `/root/cf-tuyul/.env` (IMAP shared source)

## Code
- `signup.py`: parse `DOMAINS` (or fallback `DOMAIN`), drop `<REDACTED>` when multi-domain present
- `next_domain()` via `itertools.count` round-robin
- `gen_identity()` → `{local}@{next_domain()}`
- `wn/create_accounts.py` injects `DOMAIN`/`DOMAINS` into `/create` child and hard-replaces legacy-only values
- Domain-only env changes: **no bot restart** required (`/create` spawns fresh child)

## IMAP
Gmail catch-all must accept mail for **all three** active domains. If only one domain is forwarded, ~1/3 of creates will hang on OTP.

## Product split vs ProxyScrape
Webnovel RR includes `<REDACTED>`.
ProxyScrape free trial should still prefer **`<REDACTED>`** — `<DOMAIN_REDACTED>` often marked disposable (verify OK, trial denied).

## Verify
```bash
cd /root/webnovel-autoreg
python3 - <<'PY'
from signup import DOMAINS, gen_identity
assert "<REDACTED>" not in DOMAINS
assert set(DOMAINS) == {"<REDACTED>", "<REDACTED>", "<REDACTED>"}
print([gen_identity()[0].split("@")[1] for _ in range(9)])
PY
```
