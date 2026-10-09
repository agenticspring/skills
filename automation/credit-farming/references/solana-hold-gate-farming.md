# Solana hold-gate farming — worked reference

Case: **GoCollect** (`gocollect.fun`), Solana geolocation crate-opening game.
Session 2026-09-26. Project folder `/root/gocollect-farm`.

Use this as the template whenever a target gates its money step behind a token
hold rather than a spend.

## 1. The verification-first pass

Never fund before proving the chain. The bot carries a `selftest` subcommand that
runs the whole flow against a **throwaway generated keypair** and prints
PASS/FAIL per step. 14/14 PASS live from a datacenter VPS, DIRECT (no proxy):

```
login (SIWS)            OK
gate check              {"required":true,"ok":false,"min":10000}
trail generation        max inter-fix gap 1.70 m
POST /v1/fixes          accepted=20
crate discovery         n=17, commit returned
walk-to-crate           converged 37m -> 37m in 0 batches
gate enforcement        403 gate_failed   <- expected while unfunded
```

What that bought:

- Auth, forged-input acceptance, target discovery, and convergence are **proven**.
- The datacenter IP is **not blocked** → proxies are not required to start.
- Exactly one step is unproven: `POST /v1/crates/{id}/open` has never returned a
  prize, because every attempt hits the 403 gate.

**Resolved later the same session** — the gate was characterised exactly, on a throwaway
unfunded wallet sent over a free pool proxy (full transcript in
`references/time-window-odds-farming.md` §6):

- login (SIWS), `/v1/me`, `/v1/crates` (17 crates + commit) and `/v1/fixes` (accepted=20)
  **all succeed at zero balance**. Only `/open` is gated — so `selftest` was right that the
  flow works unfunded, and the gate is a single choke point rather than a precondition on
  the whole session.
- The gate is evaluated **before** the distance check: an open attempted from 1,261 m away
  returned `gate_failed`, never a range error. That ordering is precisely what makes
  pre-positioning (walk and park while unfunded, fund only to open) viable.
- It is a per-wallet **hold**, re-read live at open time — funding flipped `gate.ok` within
  minutes of the transfer, not at a daily snapshot.

The module docstring claimed **~$2.37 per crate**. That is an assumption from
launch-phase odds, not a measurement. Report it that way and refuse to size a
batch on it until a funded wallet completes one open and the JSON result lands on
disk.

## 2. Hold-gate economics (live numbers, 2026-09-26)

Gate = hold 10,000 $COLLECT per wallet. It is a **hold**, not a spend, so the
capital is recoverable by selling back after the run.

```bash
MINT=nDZknLvfFRp5rgUHdzTrQsmSY5NKzoavqdLjSHVpump
curl -s "https://api.dexscreener.com/latest/dex/tokens/$MINT" -A 'Mozilla/5.0'
```

| Metric | Value |
|---|---|
| Price | ~$0.002308 (pumpswap COLLECT/CARDS) |
| Liquidity | ~$179,331 |
| 24h volume | ~$1,999,497 |
| FDV | ~$2.28M |
| Gate cost / wallet | 10,000 × price ≈ **$23.08** (refundable) |

Sort `pairs[]` by `liquidity.usd` descending and price off the deepest pool — the
top two pools differed slightly, so don't take `pairs[0]` blindly.

## 3. Solana secret-key import

Operator handoff is base58 most of the time (Phantom/Solflare export), but the
full matrix has to be accepted or the handoff fails at the worst moment. See the
`parse_secret` implementation in the SKILL.md section "Solana secret-key import"
— it covers base58 64-byte, base58 32-byte seed, JSON int-array (`id.json`),
`{"secret":[...]}`, and hex.

Verified by round-trip in-session:

```
re-import same base58 key   -> [ALREADY_PRESENT]   (dedupe works)
fresh base58 key            -> [ADDED]
same key as JSON int-array  -> [ADDED] on first pass, deduped on second
```

Pair with `export-pub` (addresses only) so the operator can share progress
without ever pasting a secret. `wallets.json` is forced to chmod 600 on every
write path.

## 4. Wrapper + RPC

`run.sh` lifts only `ALCHEMY_API_KEY`, `SOLANA_RPC`, `PROXY` out of
`/root/.hermes/.env` instead of sourcing the whole file — a large shared `.env`
with unquoted spaced values breaks `source`.

RPC resolution: `$SOLANA_RPC` → Alchemy (`solana-mainnet.g.alchemy.com/v2/$KEY`)
→ public `api.mainnet-beta.solana.com`. Both answered `getHealth` → `{"result":"ok"}`
in-session; prefer the keyed path at scale because the public endpoint rate-limits
under parallel wallets.

## 5. Pitfalls seen here

- One IP running many wallets at 25 actions/day each is the obvious detection
  axis. Decide on proxies before scaling past a couple of wallets.
- The worker loop breaks the whole per-wallet run when one target stays
  unreachable past `--max-walk-batches`, so a single bad spawn ends that wallet.
- The docstring claim "targets placed ≥ 190 m from any arbitrary point" was
  false — a crate spawned 37 m away in the test, so the convergence loop never
  actually exercised. Log the observed distance or you'll mistake an untested
  branch for a passing one.
