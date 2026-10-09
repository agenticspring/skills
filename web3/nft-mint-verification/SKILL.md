---
name: nft-mint-verification
description: Check if an NFT mint is really free on-chain.
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [NFT, Freemint, Verification, Onchain, Recon]
    related_skills: [free-mint-drip-race, osnm-z-mint, web3-freemint-batch-execution, token-launch-verify]
---

# NFT Mint Verification

Determine whether an NFT project is a real free mint by reading the contract
on-chain — never by trusting the site's labels. Handles the common Robinhood
Chain (4663) patterns seen in the wild: genuine free mint, paid mint, Dutch
auction house, burn-economy, and claim-gated (allowlist/TGE) mechanics. It
does NOT execute mints — it only classifies and reports.

## When to Use

- User drops an NFT mint site URL and asks "free mint?" / "cek freemint"
- Need to know price, supply, mint status, or who controls the project before
  deciding to mint
- Site says "FREE" but you need proof the transaction value is 0

## Prerequisites

- Alchemy RPC in `/root/.hermes/.env` (`ALCHEMY_API_KEY`)
- Robinhood Chain 4663 (most targets); any EVM RPC works
- `eth_utils` (via execute_code) for selector computation
- Blockscout: `https://robinhoodchain.blockscout.com` for verified ABI/source

## How to Run

1. Recon the site (fetch HTML + JS bundle, find contract addresses + ABI names)
2. Pull verified ABI/source from Blockscout
3. Read on-chain state via RPC probes
4. Classify the mint type and report

`scripts/check-mint-free.py <contract-address>` automates step 3's standard
probes against common function names.

## Quick Reference

| Read | Selector (compute via eth_utils.keccak) | What it tells you |
|------|------|---------|
| `PRICE()` / `mintPrice()` / `price()` | compute | 0 = free, else paid |
| `mintFree()` | compute | dedicated free-mint fn |
| `FREE_PER_WALLET()` | compute | free cap per wallet |
| `freeMintsRemaining(address)` | compute | unused free allowance |
| `mintCost(address,uint256)` | compute | per-wallet actual cost |
| `totalSupply()` | `0x18160ddd` | minted count |
| `MAX_SUPPLY()` / `maxSupply()` | compute | cap |
| `mintOpen()` / `mintActive()` / `phase()` | compute | window live? |
| `mintInterval()` | `0x0e726e6b` | drip interval (Fablings) |
| `lastFreeMintAt()` | `0xfca4b80e` | last global free mint |

## Procedure

1. **Recon the site.** Fetch the page and any JS bundle through `terminal`.
   Look for: `0x…40` addresses, `ld+json` metadata (chain, contracts, supply),
   and ABI names. Next.js apps often embed config in page chunks or
   `src/config.js`; Vite SPAs ship one obfuscated bundle — grep for addresses
   and known function names (`mintFree`, `PRICE`, `phase`, `reserved`).
2. **Resolve contracts.** Blockscout search (`/api/v2/search?q=<name>`) finds
   the contract by name; `/api/v2/smart-contracts/<addr>` returns verified
   ABI + name. `eth_getCode` length tells proxy vs full contract (45 bytes =
   minimal proxy).
3. **Read state on-chain.** Probe with computed selectors via RPC `eth_call`.
   Always read: price fn(s), totalSupply, MAX_SUPPLY, mintOpen/phase, and
   wallet-specific reads (`mintedBy`, `freeMintsRemaining`, `mintCost`) for the
   target wallet.
4. **Check sold-out.** `totalSupply >= MAX_SUPPLY` = done. Cross-check with the
   API/UI: `mintOpen:true` can be stale while supply is capped. If the last
   token IDs all share one owner, a bot swept the tail — free slots in the
   contract mapping are irrelevant.
5. **Classify the mechanic:**

| Signal in contract/site | Classification |
|---|---|
| `mintFree()` nonpayable, price 0, supply open | Genuine free mint |
| `PRICE() > 0`, payable `mint()` | Paid mint |
| `reservePrice`, `minimumNextBid`, `bid()` payable, "one at a time" | Dutch/English auction — must pay |
| `buy()` at fixed rate + `burnFrom` on mint | Burn economy — ETH to dev, token burned |
| `claim()` gated by NFT ownership / TGE | Claim reward, not free mint |
| `allowlist(address)`, `freemintOpen()`, `tailMinted` | Gated free window — check allowance |

6. **Identify the dev wallet.** `owner()` on the contract; a shared address
   across `treasury` and `owner` means one party controls price, phases, and
   funds. Check `setPrice`/`setPhase`/`sweep` functions to enumerate control.
7. **Report honestly.** State price wei→ETH, supply, mint status, mechanic,
   dev wallet, and whether a mint is actually free (transaction value 0).
   Never recommend a paid mint as free.

## Pitfalls

- **"FREE" label ≠ free tx**: Hoodilio advertised free at 0.00055 ETH; Market
  Arcana said "draw is free" while fulfill cost 0.0015 ETH; Robin Gorillas
  showed price 0 pre-launch then 0.0018 ETH live. The on-chain `mintCost` /
  calldata `value` is the only authority.
- **`mintOpen:true` is not proof of availability**: sold-out contracts keep
  phase 1 while `totalSupply==MAX_SUPPLY` (StonksWar 10k/10k). Always read
  both.
- **Config/JS numbers are aspirational**: minipengs `supply:1e4` in JS but
  on-chain maxSupply 3000 (Robies: JS said 10k, contract said 3k). Read the
  contract, not the frontend.
- **Proxy contracts**: 45-byte minimal proxies revert most probes — resolve
  implementation first (EIP-1967 slot `0x360894…`), or rely on Blockscout
  verified ABI + `eth_getStorageAt` for supply.
- **Rate limits**: Scatter API (429) and OpenSea drops API (403 without a
  browser User-Agent) throttle fast. Add a UA header; when throttled, go
  straight to Blockscout/RPC instead of retrying the site.
- **Auction ≠ mint**: "mint button" on an auction house is the bid button;
  winning requires paying. Doodads: reserve 0.0006 ETH, next bid 0.00945 ETH.
- **Burn economy = paid**: buying $ROBIE funds the dev treasury (fixed rate,
  no DEX pool), then mint burns the token permanently. No second-hand value.
- **Freemint window can be shut**: `freemintOpen()==0` means the reserved tail
  can't be claimed regardless of allowance.

## Verification

```bash
# proves the classification: 0 mintCost + supply open = free
python3 scripts/check-mint-free.py <contract-address>
# then confirm with the explorer URL for the contract on Blockscout
```
