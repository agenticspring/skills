---
name: launchpad-token-census
description: "Scan launchpad tokens on-chain and rank by volume/MC."
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Launchpad, Token-Census, eth_getLogs, Dexscreener, Listing-Diagnosis]
---

# Launchpad Token Census & Listing Diagnosis

Census every token a launchpad contract ever created, rank them by volume or
market cap, and diagnose why a specific token is (or isn't) listed on the
launchpad's own UI. Works for any EVM chain with an RPC + Blockscout — verified
on Robinhood Chain (4663) against SushiLaunchpad (1,170 tokens) and Uniswap
LiquidityLauncher (22,875 tokens).

Does NOT do browser scraping of DEX aggregators, social verification of
individual tokens, or explain launchpad mechanisms (see `token-launch-verify`
and `launchpad-mechanics` for those).

## When to Use

- "Token apa volume/mcap tertinggi di launchpad X?"
- "Berapa total token yang launch di platform ini?"
- "Kenapa token ini gak muncul di home/listing launchpad?"
- Comparing two launchpads on the same chain (Sushi vs Uniswap on RH 4663)
- Checking whether a token you hold is actually indexed by the platform UI

## Prerequisites

- Python 3.10+, `pip install pycryptodome` (keccak256 for event topic0)
- RPC for the target chain (Robinhood: `https://rpc.mainnet.chain.robinhood.com`,
  chainId 4663) — may 403/rate-limit; retry with browser UA + backoff
- Blockscout v2 API (`https://robinhoodchain.blockscout.com/api/v2`) for ABI,
  decoded tx input, and contract names
- Dexscreener public API (no key): `https://api.dexscreener.com/latest/dex/tokens/{a},{b},{c}`

## How to Run

1. Get the launcher contract ABI → find the launch event + which topic is the token:
   `GET /api/v2/smart-contracts/{launcher}` → `abi` array (note `indexed` flags).
2. Compute event topic0 with keccak256 and scan `eth_getLogs` in chunks
   (script below does all of it).
3. Batch-query dexscreener for the collected addresses, rank by volume/MC.

Full scanner: `scripts/scan_launchpad.py` (chunked eth_getLogs + topic decode +
concurrent dexscreener batch + ranking). Run it via the `terminal` tool.

## Quick Reference

```bash
# Blocklscout ABI (indexed flags tell you which topic = token)
curl -s "https://robinhoodchain.blockscout.com/api/v2/smart-contracts/0x104F1Ab42674565EC3DF0BFEbCcC4186f72fA7ED" | jq .abi

# Known launch events (verified 2026-08):
# Uniswap LiquidityLauncher: TokenCreated(address indexed tokenAddress)  -> topic1 = token
# SushiLaunchpad: TokenLaunched(address indexed creator, address indexed token,
#   address indexed pool, address quoteToken, int24 startTick, string name,
#   string symbol, uint16 reserveBps, uint256 reserveAmount, uint64 reserveUnlockAt,
#   uint16 initialSushiFeeBps)                                          -> topic2 = token!
```

## Procedure

1. **Fetch launcher ABI** via Blockscout `smart-contracts/{addr}`. Read every
   event's `indexed` flags — the token address is NOT always topic1. Sushi's
   `TokenLaunched` has creator=topic1, **token=topic2**, pool=topic3; Uniswap's
   `TokenCreated` has token=topic1. Wrong index = you collect creator/launcher
   addresses and the census is garbage.
2. **Find the launcher's deploy block** — `addresses/{addr}` →
   `creation_transaction_hash` → `transactions/{hash}` → `block_number`.
3. **Scan events with `eth_getLogs`** in ~1M-block chunks (or smaller). If the
   response is `"logs matched by query exceeds limit of 10000"`, halve the chunk
   and retry. Collect token addresses from the correct topic, dedupe.
4. **Rank with dexscreener batches**: 25-30 addresses per URL, 8-10 concurrent
   workers. Pick the best pair per token by liquidity (not first returned).
   Sort by `volume.h24` or `marketCap`.
5. **List vs on-chain gap**: to explain a missing token, query the launchpad's
   own tRPC list endpoints (pools.trade: `cca.listAuctions` + `curve.listLaunches`)
   and the token page `/t/{addr}` — if both 404/absent, the token is not indexed
   even though the contract is valid.

## Pitfalls

- **RPC 403 from datacenter IPs.** Robinhood RPC returns 403 intermittently —
  retry 3-4× with `Mozilla/5.0` UA + 2-3s backoff before declaring failure.
- **Blockscout `transactions/{hash}` returns `block_number`, not `block`.** Use
  `block_number` for eth_getLogs range math.
- **`logs exceeds limit of 10000`** is normal for busy launchers (LiquidityLauncher
  FINAL emitted 22K+ TokenCreated). Never scan the whole range in one call;
  adaptive chunk halving is mandatory.
- **Launchpad UI listing ≠ on-chain validity.** FROGE (RH) launched via
  `LiquidityLauncher` + `LBPStrategy`, was valid on-chain but the pools.trade
  backend did NOT index it (token page 404, absent from listAuctions). Later it
  appeared after backend reindexed post-graduation. A token can be 100% real
  and still invisible on the platform UI — that's indexing, not a rug.
- **Strategy generation matters.** pools.trade backend tracks the post-redeploy
  `InstantLaunchStrategy` generation + manually seeded legacy tokens; tokens
  distributed to the older `LBPStrategy` singleton may be missing until reindexed.
  Check the `TokenDistributed(token, strategy, amount)` event to see which
  strategy a token went to, then compare against what the backend lists.
- **MC vs FDV mismatch across sources is supply-basis, not price.**
  - pools.trade token UI shows **FDV = live price × total supply** (1B).
  - dexscreener shows **MC = live price × circulating supply** (~74% for CCA
    tokens because 50% is LP-locked).
  - Raw API field `fdvUsd` may be **stale** (clearing price at graduation).
  Same price, different numbers — answer "which is right" by asking whether the
  question is about circulating value (MC) or fully-diluted value (FDV).
- **Home-page virtual list**: `document.body.innerText` from headless Chromium
  renders the digit-font glyphs character-by-character (numbers split on every
  line). Grep the text for the symbol (`'froge' in txt.lower()`) instead of
  trying to read the rendered numbers.

## Verification

```bash
# Census sanity: sum of unique tokens should match a manual count on one chunk
python3 scripts/scan_launchpad.py 0x104F1Ab42674565EC3DF0BFEbCcC4186f72fA7ED 21957383 \
  "TokenLaunched(address,address,address,address,int24,string,string,uint16,uint256,uint64,uint16)" 2
# expect: ~1170 tokens for SushiLaunchpad as of 2026-08-07
```
