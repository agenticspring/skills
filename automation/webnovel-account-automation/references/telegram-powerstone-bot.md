# Webnovel Telegram Powerstone Bot

Private admin-only bot for novel link → info → Powerstone vote + library bookmark.

## Canonical paths
- Code: `/root/webnovel-tg-bot` (private `<HANDLE_REDACTED>/webnovel-tg-bot`)
- Reuses accounts/proxy/IMAP from `/root/webnovel-autoreg`
- Bot: `@webnovelpowerbot` (token in `/root/webnovel-tg-bot/.env` only)
- Admin TG id: `<TELEGRAM_ALLOWED_USERS_REDACTED>`
- Screen: `webnovel-tg`
- Run: `cd /root/webnovel-tg-bot && unset TELEGRAM_BOT_TOKEN TELEGRAM_TOKEN; ./run.sh`

## Why `unset TELEGRAM_BOT_TOKEN`
Hermes agent often exports a different `TELEGRAM_BOT_TOKEN` into the shell.  
If project `config.py` does not **override** with local `.env`, the bot starts as the wrong identity.  
Pattern: load project `.env` with `override=True`; start screen with `unset TELEGRAM_BOT_TOKEN`.

## Commands (setMyCommands on boot)
| Cmd | Purpose |
|-----|---------|
| `/start` `/help` | intro |
| `/status` | pool PS remaining from SQLite ledger |
| `/sync` | live-refresh `availablePower` all accounts |
| `/create [n]` | run `webnovel-autoreg/signup.py N` (max 5) |
| `/accounts` | list pool emails |
| (text link) | parse bookId → detail card + inline buttons |

## Inline UX
1. Card: Powerstone | Bookmark | Refresh | Re-fetch
2. Powerstone → amount (1/2/3/5/10/Max)
3. Bookmark → primary | ALL
4. Then **delay antar akun** (not start-delay):
   - Presets: Now, 1m, 5m, 15m, 30m, 1h, 3h, 6h, 12h
   - Custom: free text `45s` / `10m` / `2h` / `90m`

## Delay semantics (critical — user-corrected)
User-selected delay is **spacing BETWEEN accounts**:

```
akun1 action
  → sleep(delay)
akun2 action
  → sleep(delay)
…
```

- `now` / `0` = no sleep between accounts
- No sleep before the first account
- Progress message updates between accounts
- **Wrong:** wait once, then blast all accounts back-to-back (first implementation; corrected)

## Spend algorithm
1. Lazy or `/sync` balances into `daily_power` ledger (timezone `Asia/Jakarta`)
2. Prefer accounts with remaining > 0
3. When delaying: **1 PS per account step** (natural with inter-account spacing)
4. Endpoint: `POST /go/pcm/powerStone/vote` with `novelType=0`
5. Bookmark: `POST /go/pcm/library/addLibraryItemsAjax` with `bookIds` + `novelType=0`

## Create accounts from TG
`/create` shells:
```bash
/root/webnovel-autoreg/.venv/bin/python signup.py N
```
cwd = autoreg; timeout ~15m; parse Done! success/failed + new emails from accounts.txt delta.

## Device isolation
Reuse autoreg sticky profiles (`device_profiles.py` / `device_profiles.json`).  
Same email → same proxy + desktop UA + mobile UA/impersonate. Never random hop per action.

## Pitfalls
- Admin-only on **messages and callbacks** (not just /commands)
- Never print passwords/OTP/tokens in TG replies
- Partial vote success is OK — report N/M and remaining
- PCM actions need same mobile session as avatar (`login/login`+csrf, chrome120/124)
- Do not invent bot success without API `code=0`
- Inter-account delay ≠ scheduled start delay
