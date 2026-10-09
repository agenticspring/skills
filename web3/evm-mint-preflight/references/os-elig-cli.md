# os-elig CLI — OpenSea/Scatter wallet eligibility checker

## Location

- Command: `/usr/local/bin/os-elig`
- Project: `/root/projects/os-elig-bot/` (`run-eligibility.py`, `src/` = audited
  Juuju1/Check-Opensea-Eligible-With-Telegram-Bot, `.venv/`)
- Source note: `<OBSIDIAN_VAULT_PATH_REDACTED>/Research/os-elig-bot.md`

## Usage

```bash
os-elig <slug-or-url>          # Set 1 default
os-elig <slug> 1-100           # range of wallet sets
os-elig <slug> all             # all 100 sets
os-elig <slug> 1-10 --json     # JSON output
```

Bare slug, OpenSea URL (`opensea.io/collection/<slug>`), or Scatter URL
(`scatter.art/c/<slug>`) all parse. Output tag per wallet:
`ELIG` (signed/whitelist stage), `PUB` (public stage only), `NO` (none),
plus `err=` on failure.

## How it works

- Reads `OPENSEA_API_KEY` from `/root/NFT-OPENSEA/opensea.env`.
- Derives private keys in memory from `/root/.hermes/.credintial/.springwallet`
  (Set 1..100), never persists PK, never needs `wallets.csv` or Telegram.
- OpenSea path: per-wallet SIWE login (`opensea.io/__api/auth/siwe/nonce` +
  `verify`, `eth-account` sign in memory) then GraphQL persisted query
  `DropEligibilityQuery` (sha256
  `d893f026d731e8f14986921fa4229098e018289f6cc7683f8ee2dd83749dd95d`) against
  `gql.opensea.io/graphql`; session cookies cached 45 min.
- Scatter path: `scatter.art/api/trpc` collection + RH RPC onchain
  `invites(bytes32)`, `minted(address,bytes32)`, `balanceOf(address)`; no SIWE.
  `404` = slug not found; `no stages` = collection exists but no onchain list.

## Verified behavior

- Mythborn (`mythborn-735638242`, `0x92ed183381e7ac64ad5e34222658fb788f369425`):
  Set 1 = `PUB` only (Public Mythborn 0.0002 ETH). Sets 1-15 sampled identical.
- Reproduces in ~5s for one wallet.

## Pitfalls

- Eligibility GraphQL needs per-wallet SIWE auth; it is NOT usable with just an
  API key. Batch runs are rate-limited — keep one-wallet default unless a range
  is explicitly requested.
- `active_stage` may be null before mint opens; GraphQL still returns the
  wallet's stage eligibility, which is the point of the tool.
- The tool is read-only discovery input — final mint authority remains RPC
  chain/contract/stage checks (see `evm-mint-preflight`).
