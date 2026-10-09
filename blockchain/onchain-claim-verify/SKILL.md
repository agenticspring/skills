---
name: onchain-claim-verify
description: Verify onchain claims from social posts and trace funds.
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Verification, Fund Trace, Binance, Social Claims, EVM]
---

# Onchain Claim Verification

Verify whether a claim from social media (X/Twitter, Telegram, forums) about onchain activity is TRUE by pulling the actual transactions from the chain. Typical claim: "NFT mint funds were bridged to BNB and sent to a Binance wallet" with links to explorers. This skill resolves shortened links, extracts the full tx hash, verifies it via RPC, identifies exchange hot wallets, and cross-checks the claimed amounts against on-chain values.

Does NOT judge whether the activity is legal or good — it produces verified evidence and a pass/fail verdict on the claim.

## When to Use

- "Cek tx nya apakah benar" (verify this tx is real)
- Someone posts an analysis with explorer links — confirm it
- "Apakah dana masuk Binance" / "is this really a Binance wallet"
- Cross-check a bridge/withdraw story shared in a tweet
- Verifying any truncated hash or shortened URL from social media

## Prerequisites

- `cast` CLI (foundry) — `command -v cast || curl -L https://foundry.paradigm.xyz | bash`
- Public RPC endpoints per chain:
  - BSC: `https://bsc-dataseed.binance.org`
  - Base: `https://mainnet.base.org`
  - Arbitrum: `https://arb1.arbitrum.io/rpc`
  - Optimism: `https://mainnet.optimism.io`
  - Robinhood Chain (4663): `https://robinhood-rpc.publicnode.com`
- Optional Etherscan V2 key for L1 explorer APIs

## How to Run

Invoke probes through the `terminal` tool. Resolve shortlinks first, then verify with RPC `eth_getTransactionByHash` — this works even when block explorers (BSCScan) block bots with Cloudflare.

## Quick Reference

```bash
# Resolve shortened link to full URL (t.co, etc.)
curl -s -L -o /dev/null -w "%{url_effective}\n" "https://t.co/<shortcode>"
# or HEAD for Location header
curl -s -I "https://t.co/<shortcode>" | grep -i location

# Verify a tx exists on-chain (works under CF-blocked explorers)
curl -s -X POST https://bsc-dataseed.binance.org -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"eth_getTransactionByHash","params":["0x<fullhash>"],"id":1}'

# Wallet balance + nonce (nonce is the exchange-wallet tell)
curl -s -X POST https://bsc-dataseed.binance.org -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"eth_getBalance","params":["0x<addr>","latest"],"id":1}'
curl -s -X POST https://bsc-dataseed.binance.org -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"eth_getTransactionCount","params":["0x<addr>","latest"],"id":1}'

# Verify with cast
cast receipt 0x<fullhash> --rpc-url <RPC>
```

## Procedure

1. **Extract all links from the claim.** `web_search` for the post, or `browser_navigate` to it and read the linked URLs. Social platforms show truncated hashes (`0xc6702a72e…`) but keep the full `t.co` shortcode in the DOM/href.
2. **Resolve every shortlink.** `curl -s -L -o /dev/null -w "%{url_effective}\n" "https://t.co/<code>"` or read the `Location:` header. This reveals the full tx hash and explorer path. Do this for ALL shortlinks, not just the first.
3. **Verify each tx exists on-chain.** POST `eth_getTransactionByHash` to the chain's public RPC with the FULL hash. A valid response returns `from`, `to`, `value`, `nonce`, `blockNumber`. `result: null` = tx doesn't exist on that chain.
4. **Convert values.** `value` is hex wei; divide by 1e18. Compare to the claimed amount (e.g. claim says ~16.98 BNB, tx value = 16.976 → match).
5. **Identify exchange wallets by balance + nonce.** Binance hot wallets have huge balances AND enormous nonce (55M+ tx). `eth_getBalance` showing 100k+ BNB + `eth_getTransactionCount` showing tens of millions = exchange hot wallet, not a personal EOA. A personal wallet has low nonce (< a few thousand).
6. **Check sender profile.** The `from` may differ from the wallet you traced earlier (e.g. an intermediate relay wallet with near-zero balance and nonce 1). Trace its own history to connect the dots.
7. **Cross-check the full chain.** Merge the verified BSC tx with earlier on-chain tracing (NFT contract withdraw → bridge deposit → BSC) into one flow diagram. State which parts are verified vs inferred.
8. **Deliver verdict.** "Claim TRUE/VERIFIED" with the exact on-chain values, or "claim FALSE" with what actually happened.

## Pitfalls

- **Explorers block bots.** BSCScan shows a Cloudflare "Just a moment..." page to `browser_navigate` and curl. Do NOT conclude the tx is fake — verify via RPC `eth_getTransactionByHash` instead, which explorers can't block.
- **Truncated hashes are useless for RPC.** You need the full 0x64-char hash. Resolve the shortlink — the full hash is in the redirect target. Never guess the missing characters.
- **t.co links work without login.** `curl -s -L -o /dev/null -w "%{url_effective}"` resolves them; no X session needed.
- **`from` may not be the wallet you expect.** The bridge/intermediate wallet sends from a different address (e.g. relay payout wallet). Verify the value matches the claim, then trace the sender's own history.
- **Nonce is the exchange tell, not balance alone.** A 102k-BNB wallet with nonce 55,286,710 is Binance; a 100k-BNB cold wallet with low nonce could be anything. Check both.
- **Etherscan V1 APIs are deprecated** (`NOTOK ... switch to V2`). Use `https://api.etherscan.io/v2/api?chainid=<id>&...` or skip the API and use public RPC.
- **BSC RPC rate limits on block scans.** Scanning thousands of blocks via `eth_getBlockByNumber` times out; find the tx by hash instead, or use an explorer API.
- **Shortener flags.** Security scanners flag `t.co` as a shortened URL — that's expected, the redirect target is the real data.
- **Value is hex.** `int("0x...", 16) / 1e18` — a single missed conversion makes the claim look wrong.

## Verification

A single command that proves the claim's core tx is real:

```bash
curl -s -X POST https://bsc-dataseed.binance.org -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"eth_getTransactionByHash","params":["0x<fullhash-from-resolved-link>"],"id":1}' \
  | python3 -c "import sys,json; r=json.load(sys.stdin)['result']; print('FOUND', r['from'][:10], '->', r['to'][:10], int(r['value'],16)/1e18, 'BNB') if r else print('NOT FOUND')"
```

If this prints FOUND with a value matching the claim and the destination wallet shows exchange-level balance+nonce, the claim is verified. If NOT FOUND, the claim cites a tx that doesn't exist on that chain — report that.