---
name: free-mint-drip-race
description: Mint drip-rate free NFTs across wallet sets.
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [NFT, FreeMint, Drip, Race, Wallet, Cascade]
    related_skills: [osnm-z-mint, web3-freemint-batch-execution, evm-mint-preflight, wallet-whitelist-registration]
---

# Free Mint Drip Race

Mint "drip" NFTs that release one free mint per global time interval (not per
wallet), across Hermes wallet sets, then consolidate all NFTs and dust back to
Set 1. Covers on-chain free-mint verification, the global-drip race loop,
wallet cascading, NFT consolidation, and minimum-gas dust sweeps. It does NOT
mint paid lanes and does NOT handle OpenSea SeaDrop mints (see `osnm-z-mint`).

## When to Use

- A mint site's JS shows `mintFree()` / `mintInterval` / `lastFreeMintAt`
- "mint gratis tiap X detik", "drip mint", "free hatch"
- User asks: check if free, mint max on wallet sets, consolidate NFTs, sweep dust
- Contract ABI exposes `FREE_PER_WALLET`, `freeMinted(address)`, `mintFree()`

## Prerequisites

- `/root/.hermes/.credintial/.springwallet` — `Set 1..N` labeled mnemonics
- `cast` (Foundry), `eth_utils` for selectors
- Alchemy RPC in `/root/.hermes/.env` (`ALCHEMY_API_KEY`)
- Robinhood Chain 4663: gas price ~0.02 gwei, FCFS sequencing (no priority tip)
- PKs staged ephemerally under `/dev/shm/fab-pk-<n>` (mode 600), never printed

## How to Run

Invoke through the `terminal` tool:

```bash
python3 scripts/drip-race-mint.py 2 10      # cascade mint Set2..10
python3 scripts/consolidate-nfts.py 2 10    # move all NFTs to Set 1
python3 scripts/dust-sweep.py 2 10          # sweep remaining ETH to Set 1
```

## Quick Reference

| Check | Selector (via eth_utils keccak) | Meaning |
|-------|------|---------|
| `FREE_PER_WALLET()` | compute | free cap per wallet |
| `freeMinted(address)` | compute | used free count |
| `mintFree()` | compute | 0-value mint, nonpayable |
| `lastFreeMintAt()` | `0xfca4b80e` | last global free mint ts |
| `mintInterval()` | `0x0e726e6b` | seconds between free mints |
| `mintOpen()` | `0x24bbd049` | mint phase live |
| `totalSupply()` | `0x18160ddd` | minted so far |
| `MAX_SUPPLY()` | compute | cap |

Common custom errors: `DripNotReady` `0x5273678a`, `FreeWalletCapReached`
`0x53353903`, `MintNotOpen` `0x951b974f`, `ERC721IncorrectOwner` `0x177e802f`.

## Procedure

### 1. Verify it's really free (on-chain, never trust UI)

1. Fetch the site's JS bundle and `abi/*.json` artifact; extract the items
   contract address + ABI (site `src/config.js` often has
   `addresses.items`).
2. Read state via RPC: `mintPrice()`, `FREE_PER_WALLET()`,
   `freeMinted(addr)`, `totalSupply()`, `MAX_SUPPLY()`, `mintOpen()`.
3. Free is proven by `mintPrice()==0` (or a `mintFree()` nonpayable fn) AND
   `totalSupply() < MAX_SUPPLY()`. `mintCost(addr,1)==0` confirms per-wallet.
4. UI/API `mintOpen:true` is NOT proof — sold-out contracts keep phase 1 while
   `totalSupply==MAX_SUPPLY` (StonksWar 10k/10k case). Check `ownerOf(lastId)`:
   one wallet owning the tail ids = bot sweep already happened.

### 2. Race the global drip

A global drip has ONE free slot per `mintInterval` reset by whoever wins;
`mintFree()` reverts `DripNotReady` if you miss. Loop:

```text
poll lastFreeMintAt() + mintInterval() until (last + iv) <= blockTime
fire cast send mintFree() with explicit nonce
on DripNotReady -> retry immediately (lost race)
on FreeWalletCapReached -> stop (cap hit)
wait receipt before next
```

Use `scripts/drip-race-mint.py` — it derives PKs, races to the cap, and
tracks per-wallet balance for cascading.

### 3. Cascade wallets

```text
Set1 -> 0.0010 ETH -> Set2 -> mint cap (10) -> remaining -> Set3 -> ...
```

Keep `GAS_RESERVE` (~0.00005) in the sender before the transfer so the
transfer tx itself has gas; `--value` hex needs `0x` prefix
(`format(int(amt*1e18),'#x')`).

### 4. Consolidate NFTs to Set 1

`safeTransferFrom(from, to, tokenId)` calldata is
`0x42842e0e + from + to + tokenId`. **Argument order matters**: `from` is the
OWNER wallet (Set N), `to` is Set 1 — reversed args revert
`ERC721IncorrectOwner`. Fund gas into each owner wallet first (~0.00005 ETH
covers 10 transfers), then sweep the remainder.

### 5. Dust sweep at minimum gas

Robinhood is FCFS — set gas price to pending `baseFeePerGas * 1.10`, no tip.
Fee for plain ETH transfer = `21000 * gasPrice`. Send `balance - fee` exactly.
Re-read base fee and retry on `max fee per gas less than block base fee`.

## Pitfalls

- **Header lines in the wallet file**: skip lines starting `#` or `Set ` —
  a 12-word comment line looks like a mnemonic and breaks `cast` derivation.
- **Selector typos**: compute selectors with `eth_utils.keccak`, never hardcode
  from memory; a wrong selector returns empty/Revert and hangs `wait_ready`.
- **Global drip ≠ per-wallet cooldown**: `lastFreeMintAt` is shared; expect
  ~1 revert per win on a contested drip. Not an error.
- **`freeRemaining` in JS is a client-side guess**: the site may show a free
  slot while the contract is sold out or the mapping is stale.
- **Never use site `--value` without `0x`**: `cast send` rejects
  `38d7ea4c68000` style hex without the prefix.
- **Gas price races**: reading `eth_gasPrice` then submitting can hit a base
  fee bump; always take pending baseFee +10% and retry.
- **safeTransferFrom approval not needed** for owner→anyone; only non-owner
  transfers need approval.

## Verification

```bash
python3 - <<'PY'
import json, os, urllib.request
# after a run: check Set1 balanceOf == 10*wallet_count and other sets == 0
# balanceOf(Set1) == total minted confirms consolidation
PY
```

Confirm `balanceOf(Set1) == 10 × (wallets minted)`, `freeMinted` caps at 10/10
per wallet, Set 2-N NFT balance == 0, and Set1 ETH balance grew by the sweep.
