---
name: nft-economy-recon
description: Verify NFT mint economics on-chain before minting.
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [NFT, Recon, Economy, Burn, Contract, Treasury]
    related_skills: [free-mint-drip-race, osnm-z-mint, evm-mint-preflight]
---

# NFT Economy Recon

Before minting or buying into any NFT project, verify the actual on-chain
economics: which contract is the NFT vs the token, whether "burn" really
destroys tokens, whether "buy token" is a DEX or a fixed-rate dev counter,
and where the ETH actually lands. Read-only RPC + verified source analysis;
never broadcast. This is the pre-mint sanity gate for both free-mint and
paid-mint farming.

## When to Use

- User links a mint site and asks "cek CA", "apakah free mint", "beneran burn?", "buy di DEX atau di minting"
- Before minting/whitelisting/farming any new NFT project
- Suspicion that a project is a dev cash-out (buy token → burn token → ETH to dev)

## Prerequisites

- Alchemy RPC in `/root/.hermes/.env` (`ALCHEMY_API_KEY`)
- `eth_utils` for selectors, Blockscout explorer per chain
- Robinhood: `https://robinhoodchain.blockscout.com`

## How to Run

Invoke through the `terminal` tool: fetch site JS + config, then RPC-probe the
candidate contracts and read verified source. No single command; the procedure
below is the workflow.

## Quick Reference

| Question | Probe | Decides |
|----------|-------|---------|
| Which address is the NFT? | `ownerOf(1)`, `decimals()`, `MAX_SUPPLY()` | ERC-721 vs ERC-20 |
| Free or paid? | `mintPrice()`, `FREE_PER_WALLET()`, `mintCost(addr,1)` | value == 0 |
| Sold out? | `totalSupply()` vs `MAX_SUPPLY()`, `ownerOf(lastId)` | cap reached / sweep |
| Real burn? | verified source `mint()` + `totalSupply` drift | `burnFrom` vs `transfer` |
| DEX or counter? | `robiesPerEth`, `shut`, `quote()`, shelf balance | fixed rate = dev counter |
| Where does ETH go? | `treasury()` vs NFT `owner()` | same addr = dev controls all |

## Procedure

1. **Collect candidates.** Fetch the site HTML/JS bundle; grab every
   `0x...` address and any config object (Next.js chunks often carry
   `addresses:{items, treasury, exchange}`). Also fetch `abi/*.json`
   artifacts when present.
2. **Classify on-chain — never trust config labels.** Configs mislabel
   (Robies config named the ERC-20 "token" and the ERC-721 "robies").
   For each address probe:
   - `ownerOf(1)` returns an address → ERC-721 NFT
   - `decimals()` returns 18 → ERC-20 token
   - `totalSupply()` huge with decimals → token; small count → NFT minted
3. **Read mint state.** On the NFT contract: `mintPrice()`,
   `FREE_PER_WALLET()`, `freeMinted(addr)`, `totalSupply()`,
   `MAX_SUPPLY()`, `mintOpen()`/`phase()`, `walletLimit()`.
4. **Verify burn vs transfer.** Fetch verified source from Blockscout
   (`/api?module=contract&action=getsourcecode&address=<addr>`), grep the
   `mint()` function. Real burn = `token.burnFrom(msg.sender, qty * price)`.
   Cross-check token `totalSupply` drifts DOWN. `transfer` to the contract =
   not burned, supply unchanged.
5. **Trace the money.** If there's a token buy step: read `shut`,
   `robiesPerEth`/rate, `quote(wei)`, `balanceOf(exchange)` (shelf), and
   `treasury()`. Compare treasury with NFT `owner()`. Same wallet = dev has
   full control (rate, phase, prices, freemint, reservedMint, sweep) and all
   ETH is a sunk cost.
6. **Report honestly.** Distinguish: real free mint / paid / burn economy /
   auction (settle-bid) / fixed-rate counter. Flag dev-controlled sinks.

## Pitfalls

- **Config labels lie** (Robies: token vs robies swapped). Always classify by
  on-chain probes, not the site's names.
- **`name()`/`symbol()` may return empty on verified contracts** — use
  `ownerOf`/`decimals` instead.
- **UI "FREEMINT" ≠ free** — a `freemintOpen:false` window is closed; a
  "reserved 300" tail is owner-gated, not public.
- **Site config `maxSupply` can differ from on-chain** (Robies JS said 10000,
  contract said 3000). Contract wins.
- **"Buy token" is often NOT a DEX** — no pool/AMM/slippage/second-hand
  value; fixed rate + shelf + treasury sweep = dev cash-out structure.
- **Treasury == NFT owner** is the red flag: same wallet controls rate,
  mint phase, freemint window, reserved mint, and sweeps ETH to itself.
- **Burn ≠ destruction** — verify `burnFrom` in source; `transfer` to
  contract keeps supply flat.
- **Check `mintInterval()` drift before blaming latency.** Drip-mint
  intervals are dev-controlled and swing wildly (BABIES: 3s → 5s → 60s →
  600s → 2s in one session). A long losing streak with normal block timing
  means the slot rate collapsed (1 win/10min), not that the bot is slow.
- **Blockscout fee display is misleading** — it shows the reserved fee
  (gasLimit × maxFeePerGas), up to 100x actual. Real cost = `gasUsed ×
  effectiveGasPrice` from the receipt; reverted-mint fees on RH were
  ~0.0000006 ETH each, tiny.

## Verification

```bash
# Prove the classification: NFT vs token
cast call <nft> 'ownerOf(uint256)(address)' 1 --rpc-url $RPC   # returns addr
cast call <token> 'decimals()(uint8)' --rpc-url $RPC           # returns 18
# Prove the treasury link
cast call <exchange> 'treasury()(address)' --rpc-url $RPC
cast call <nft> 'owner()(address)' --rpc-url $RPC              # same?
```

## References

- `references/robies-burn-economy.md` — full worked case: mislabeled config,
  real `burnFrom` mint, fixed-rate counter vs DEX, treasury == owner.

