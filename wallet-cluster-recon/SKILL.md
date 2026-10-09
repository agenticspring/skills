---
name: wallet-cluster-recon
description: Use when profiling EVM wallet clusters or Arkham links.
version: 1.0.0
author: spring (curator)
license: internal
metadata:
  hermes:
    tags: [web3, onchain, recon, tracing]
    related_skills: [onchain-claim-verify, evm-explorer-evidence, token-launch-claim-verify]
---

# Wallet Cluster Recon

## When to Use
- User shares an Arkham/visualizer link or a list of related EVM addresses and asks to analyze/trace the entity.
- Tracing fund flow across a cluster of wallets (who funds whom, what they trade).

Analyze a set of related wallets as one entity: who funds whom, what they trade, where funds flow.

## Workflow

1. **Arkham links are login-gated** (Cloudflare Turnstile + auth). Do not burn time extracting them; go straight to on-chain data. The URL itself still yields intel: the address list, and the `positions` query param names labeled nodes (`binance`, `stake-com`, `opensea`, `relay-link`, `0x000...000` mint node) that reveal the entity's context even without access.
2. **Primary data source: Blockscout v2 REST** (free, no key):
   - `GET https://eth.blockscout.com/api/v2/addresses/{addr}` — balance, is_contract, has_tokens
   - `.../counters` — tx_count, token_transfers_count (fast triage: skip dead wallets)
   - `.../transactions` — native txs
   - `.../token-transfers?type=ERC-20,ERC-721` — token/NFT history
3. **Triage first**: pull `/addresses` + `/counters` for all wallets in one pass, then deep-dive only active ones.
4. Profile each active wallet: recent transfers with direction (IN/OUT relative to target), symbol, method, counterparty. Summarize role per wallet (hub/funding, trader, collector, minter, disposal).
5. Report as a table: wallet short-form, balance, activity pattern; call out fresh/empty wallets (likely future use) and recently-active ones.
6. **Cross-chain check**: if the entity has activity on non-Ethereum chains (RH/Base/etc), probe those too — Blockscout instances exist per chain (e.g. `https://rpc.mainnet.chain.robinhood.com` for RH, no Blockscout but Alchemy works).

## Pitfalls

See `references/blockscout-v2-quirks.md` for exact API gotchas (filter syntax, JSON parsing, deprecated endpoints).

## References
- `references/blockscout-v2-quirks.md` — working curl patterns and parsing fixes.
