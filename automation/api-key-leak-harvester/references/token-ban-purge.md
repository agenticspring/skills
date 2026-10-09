# Token ban purge (harvester)

## Goal
Drop dead/banned GitHub PATs from `/root/api-key-leak/data/tokens.txt` so harvester does not rotate corpses.

## Probe (per token)
```text
GET https://api.github.com/user
  Authorization: token ghp_…
GET https://api.github.com/rate_limit   # if user OK or rate-limited
```

## Classify
| Response | Action |
|---|---|
| 200 + login | KEEP |
| 403 + rate limit / secondary rate | KEEP (alive, temporarily limited) |
| 401 bad credentials | DROP |
| 403 suspended / disabled / blocked / abuse / spam | DROP (`banned/suspended`) |
| network error | do not drop blindly; retry once |

## Rewrite
- Write **alive only**, one `ghp_` per line, `chmod 600`
- Chat report: counts + `prefix…suffix` only
- No Hermes `GITHUB_TOKEN` / `GITHUB_TOKEN_2` in this file
- User “ga usah backup” → skip `.bak` unless they ask

## Empty inventory case
If every token is banned (session proof: **16/16** drop → `tokens.txt` empty):
1. Harvester must stay off / is useless until inject
2. Next: `github-account-registration` batch mint **or** user pastes new bots
3. After inject: restart `api-key-leak` and confirm `Loaded N GitHub token(s)`

## Note
Mass new-account PAT batches can later all land as suspended if GitHub farms them — treat purge as routine before any long harvest loop.
