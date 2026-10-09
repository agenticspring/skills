# Captcha yield notes (api-key-leak)

## Snapshot before fix (2026-07-21)
- Harvester process: **off** (last log ~Jul 17, rate-limited tokens)
- `found/capsolver.txt`: **missing/empty**
- `found/2captcha.txt`: ~18 lines
- Capsolver keys in Webnovel bot `.env`: format **`CAP-…`** (len ~68)
- Old provider pattern: UUID `[A-Z0-9]{8}-…` → **never matched real Capsolver keys**

## Fixes shipped
1. Capsolver pattern → `CAP-[A-Za-z0-9]{20,100}`
2. High-signal queries for `CAP-` + `clientKey` + env names
3. `preserveKeyCase` in worker (keep `CAP-` prefix)
4. Primary scan: collect all queries → global URL set → `processURLsMultiProvider` once
5. `start.sh` → `/root/api-key-leak`, unset main GH tokens, captcha provider list

## Repo
- Push target: `https://github.com/<HANDLE_REDACTED>/api-key-leak.git`
- Commit example: `c3b8fbb` Boost captcha key harvest…

## Ops preference
- Stop harvester before architecture edits if it was running
- Leave webnovel sync/bot alone during harvester work
- After code change: `go build -o harvester .` + `go test ./...` + push if user wants remote updated
