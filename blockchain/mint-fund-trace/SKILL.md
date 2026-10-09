---
name: mint-fund-trace
description: Trace NFT mint revenue from contract to final destination.
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [NFT, Fund Tracing, EVM, Bridge, Rugpull, Blockchain]
---

# Mint Fund Trace

Trace where an NFT collection's mint revenue actually goes: from the collection contract through withdraws, intermediary wallets, and bridges to the final destination (exchange, LP, rewards vault, or another wallet). The goal is answering "did the dev pull funds out / is this a rug-pull risk" with on-chain evidence, not speculation. Read-only — no transactions are sent.

Does NOT judge tokenomics or legality; it produces the fund-flow evidence and flags red-flag patterns (revenue to exchange instead of the promised rewards vault).

## When to Use

- "Apakah dana mint masih di-hold atau dikirim ke wallet lain"
- "Apakah dev WD ke binance"
- "Lacak dana hasil mint ke mana"
- "Cek apakah ini rug pull" / "funds gone from contract"
- Checking any newly launched NFT: where did the mint money go

## Prerequisites

- `cast` CLI (foundry): `command -v cast || curl -L https://foundry.paradigm.xyz | bash`
- RPC for the collection's chain (e.g. Robinhood Chain `https://robinhood-rpc.publicnode.com`, chain id `0x1237` = 4663)
- Blockscout v2 API: `https://<chain>.blockscout.com/api/v2/` (rate-limited — sleep 2s between calls)
- Optional: Etherscan V2 API key in `~/.hermes/.env` as `ETHERSCAN_API_KEY` for L1 destination checks (`https://api.etherscan.io/v2/api?chainid=1&...`)

## How to Run

Invoke all probes through the `terminal` tool. Use `cast call` with full signatures (never raw selectors) for contract reads; use Blockscout v2 JSON for tx lists; use `cast receipt`/`cast tx` for individual transaction decode.

## Quick Reference

```bash
RPC="https://robinhood-rpc.publicnode.com"
NFT=0x...   # collection contract

cast call $NFT "owner()(address)" --rpc-url $RPC
cast call $NFT "mintActive()(bool)" --rpc-url $RPC
cast call $NFT "totalMinted()(uint256)" --rpc-url $RPC
cast call $NFT "holderSink()(address)" --rpc-url $RPC
cast balance $NFT --rpc-url $RPC

curl -s "https://robinhoodchain.blockscout.com/api/v2/addresses/$NFT/transactions" -H 'Accept: application/json'
curl -s "https://robinhoodchain.blockscout.com/api/v2/addresses/$WALLET/coin-transfers" -H 'Accept: application/json'
cast receipt 0x<txhash> --rpc-url $RPC   # decode logs: topics[1]=recipient, data=amount (wei)
cast tx 0x<txhash> --rpc-url $RPC        # input data / from / to
```

## Procedure

1. **Read contract state.** `mintActive()`, `totalMinted()`, `price()`, `maxSupply()`, `maxPerWallet()`, `owner()`, `holderSink()`. Compare UI claims vs on-chain truth (UI may show "mint now" while `mintActive()` is still false).
2. **List contract transactions** via Blockscout v2 `addresses/<NFT>/transactions`. Find fund-moving methods: `withdrawTo`, `withdraw`, `setHolderSink`, `setToken`. Ignore admin setup (`setPrice`, `setDefaultRoyalty`, `approve`, `setName`).
3. **Decode each withdrawal.** `cast receipt <tx>` — in logs, `topics[1]` = recipient address (padded), `data` = amount in wei (hex). Convert: `python3 -c "print(int('0x...',16)/1e18)"`.
4. **Check rewards vault.** Read `holderSink()` address, then `cast balance` it. A vault that stays 0 after sold-out = promised rewards not funded (red flag if rewards were promised).
5. **Trace intermediary wallets.** For each withdrawal recipient: full tx list + `cast balance`. A wallet that receives then immediately forwards to a bridge/exchange = pass-through.
6. **Identify bridge contracts.** Look for `depositNative`/`depositErc20` calls. E.g. `RelayDepository` = relay.link bridge. Get its ABI from Blockscout `smart-contracts/<addr>`; events like `RelayNativeDeposit(from, amount, id)` reveal the request id.
7. **Check bridge state.** `cast call <bridge> "callRequests(bytes32)(bool)" 0x<requestId>` — `false` = request already processed. Also scan relay `execute` txs (`cast tx` input data) for the request id.
8. **Check destination chains.** Use the Etherscan V2 API with `chainid` param, or RPC `eth_getBalance` per chain (Base `https://mainnet.base.org`, BSC `https://bsc-dataseed.binance.org`, Arbitrum `https://arb1.arbitrum.io/rpc`, Optimism `https://mainnet.optimism.io`). Also check BSC `eth_getTransactionCount` — a nonce > 0 proves activity even at 0 balance (BNB path).
9. **Cross-reference public analysts.** `web_search` for `<project> mint fund` / check X posts — analysts often already found the missing tx hash or Binance transfer link. Use `browser_navigate` to read the tweet if web search shows a link.
10. **Write the flow diagram** (contract → withdraws → intermediaries → bridge → destination) and flag patterns: revenue to exchange instead of LP/vault = red flag; revenue still locked in bridge = unresolved.

## Pitfalls

- **Blockscout v2 pagination is NOT `?page=N`** — that returns `{"errors":[{"title":"Invalid value"...}]}`. Use the `next_page_params` object from the response and pass it as query string.
- **Blockscout rate limits** — rapid calls return empty/404. Always `sleep 2` between API calls; re-fetch once if empty.
- **Etherscan V1 endpoints are deprecated** (`NOTOK ... switch to V2`). Use `https://api.etherscan.io/v2/api?chainid=<id>&module=account&action=balance&address=<w>&tag=latest&apikey=<KEY>`. Free tier does NOT support Base/BSC/Optimism — use public RPCs for those.
- **BSCScan blocks bots with Cloudflare** ("Just a moment..."). Use `browser_navigate` may also fail; fall back to RPC (`eth_getBalance`/`eth_getTransactionCount`) or the tweet-provided hash.
- **`callRequests(id)=false` means processed, not pending** — don't interpret as "not found".
- **Zero balance on EVM chains ≠ funds vanished** — bridges route to BNB/Solana etc. Relay supports Solana (`chainid 792703809`); the same wallet address exists on BSC with nonce > 0 even when balance is 0.
- **Relay API `intents/status/v3` returns `{"status":"unknown"}`** without a Relay API key — it does NOT prove the request never existed.
- **Same address on another chain ≠ same contract.** `RelayDepository` exists on Robinhood Chain; the identical address on Ethereum mainnet returned "No data found" (balance 0, no contract).
- **Hash in tweets/links may be truncated** (e.g. `0xc6702a72e…`). Match by nonce/count on the wallet or ask for the full hash; don't fabricate the missing characters.
- **`cast` may need full tx hash** — truncated hashes error out; pull the full hash from the Blockscout list first.

## Verification

A single command proving the trace resolved the destination:

```bash
cast call <NFT> "owner()(address)" --rpc-url $RPC && \
  curl -s "https://<chain>.blockscout.com/api/v2/addresses/<NFT>/transactions" -H 'Accept: application/json' | python3 -c "import sys,json; [print(t.get('method',''), t.get('hash','')[:16], float(t.get('value','0') or 0)/1e18) for t in json.load(sys.stdin).get('items',[]) if float(t.get('value','0') or 0)/1e18>0.1]"
```

If this shows the revenue-sized withdrawal(s) and the follow-up `cast balance`/nonce check identifies where they went, the trace worked. If every value is 0, you're looking at the wrong list — check the contract's internal/coin transfers instead.