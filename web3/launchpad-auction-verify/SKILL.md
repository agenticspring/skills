---
name: launchpad-auction-verify
description: Verify bidder outcomes in CCA launchpad auctions.
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Web3, CCA, Auction, Launchpad, Bids, Verification]
---

# Launchpad Auction Verification

Verifies what actually happened to a bidder in a Continuous Clearing Auction (CCA) launchpad — the model used by Uniswap's Liquidity Launcher / pools.trade on Robinhood Chain. Users come with claims like "I bid $50, only $16 filled, but after the auction I got full tokens instead of a refund" — this skill traces their `submitBid` txs, reads the auction's on-chain state, and explains whether refund, full allocation, or creator-sweep is the real outcome. Also explains the mechanics to the user (partial fill / pro-rata, graduation gate, claim-based settlement).

Does NOT verify who launched the token (see `token-launch-verify`) and does NOT audit contract code. Passive lookups only.

## When to Use

- "Saya bid tapi tidak dapat refund / malah full token" — user bought on a CCA launchpad
- "Yang ke-fill cuma 20%, sisanya di-refund?" — explain fill/refund mechanics
- "Semakin sepi auction, dapat banyak?" — explain graduation dependence
- Verify a user's actual bid amounts, fill, and auction status on-chain
- Explaining how CCA launchpads differ from bonding-curve launchpads (Pump.fun)

## Prerequisites

- Robinhood Chain (4663): RPC `https://rpc.mainnet.chain.robinhood.com`, explorer `https://robinhoodchain.blockscout.com`
- `curl` + `python3` (stdlib) — no API keys

## How to Run

Invoke through the `terminal` / `execute_code` tools. Get the user's wallet address, trace `submitBid` txs to the auction contract, then RPC-read the auction state. Runnable probe: `scripts/read_cca_state.py` (stdlib, takes an auction address and prints all state fields). Full mechanics model (preset params, selectors, outcome model, launchpad comparison) in `references/cca-auction-mechanics.md`; the watchdog change-monitor pattern (CSP nonce strip, GitHub hash tracking, factory CA detection, bot-spam filter, Telegram delivery) in `references/launch-change-monitor.md`. Event-scanning recipes (enumerate every launched token, debunk "first launch", MC-vs-FDV trap, why tokens go missing from the frontend list, tRPC surface) in `references/launchpad-data-verification.md`.

## Quick Reference

```bash
# Sum a wallet's bids to an auction (blockscout tx list)
curl -s "https://robinhoodchain.blockscout.com/api/v2/addresses/<WALLET>/transactions" \
  | python3 -c "import json,sys; [print(t['timestamp'], t['value'], t['to']['hash']) for t in json.load(sys.stdin)['items'] if t.get('method')=='submitBid']"

# CCA auction state — RPC eth_call selectors (verified against Uniswap CCA ABI)
# endBlock()         0x083c6323
# isGraduated()      0x9e5f2602
# claimBlock()       0x37dfbc4b
# currencyRaised()   0x998ba4fc
# remainingSupply()  0xda0239a6
# sweepUnsoldTokensBlock() 0x8a76bfe4  (0 until creator sweeps; 1 = swept)
# tokensRecipient()  0x3c05e7bc      (the only address allowed to sweep)
curl -s -X POST "https://rpc.mainnet.chain.robinhood.com" -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":"<AUCTION>","data":"0x9e5f2602"},"latest"]}'
```

## Procedure

1. **Get the auction address.** Blockscout `/api/v2/addresses/<WALLET>/transactions` on the user's EOA — `submitBid` txs point at the auction contract (`to`). Note: some auctions use a proxy/router; collect the full `to` hashes.
2. **Sum the bids.** For each `submitBid` to that auction, `value` is wei ETH. Sum = total committed. Multiple small bids over minutes = user testing/front-running; a single bid = one-shot.
3. **Read auction state** via RPC selectors (Quick Reference). Critical fields: `isGraduated`, `endBlock`, `claimBlock`, `currencyRaised`, `remainingSupply`.
4. **Classify the outcome** (see `references/cca-auction-mechanics.md` for the full model):
   - `isGraduated() == true` → bids settle to FULL token allocation at clearing price. **No ETH refund** — this is the "why did I get full tokens" answer.
   - `isGraduated() == false` and past `endBlock` → failed auction; creator can `sweepUnsoldTokens()` (full deposited supply on failure). Bidder recovery is claim-based, not automatic.
   - `claimBlock` in future → bids locked until claims open.
5. **Check the user's token balance** — `/api/v2/addresses/<WALLET>/token-balances` (returns a bare LIST, not `{items}`) to confirm how much they actually received.
6. **Explain in user terms.** Partial fill ≠ refund: the "fill %" shown in UI is clearing-price progress, not a refund split. Graduated = full token; failed = refund must be claimed (and creator sweep competes). Don't promise "automatic refund" — settlement is claim-based.

## Monitoring a Launchpad for Changes (watchdog pattern)

Proven pattern for watching website + GitHub + on-chain factory for real
changes, with no false positives. Working reference deployments:
`/root/.hermes/scripts/pools_webgh.py` (cron-safe) and
`/root/.hermes/scripts/pools_daemon.py` (30s background daemon that sends
Telegram alerts directly). State kept in a JSON file; first run baselines and
stays silent; subsequent runs alert only on diffs.

Checks that matter (mirror the pools.trade monitor):
1. **Website HTML**: hash the stripped HTML; on change, re-read title/desc and
   extract any `0x[a-fA-F0-9]{40}` CAs rendered on the page (a live site that
   shows a CA is the strongest official-token signal).
2. **GitHub**: track latest commit SHA for the addresses file + raw content
   hash — a new commit like "register the ... full-redeploy generation" or a
   re-mined vanity launcher means the team deployed a fresh generation.
3. **On-chain factory**: poll `explorer/api/v2/addresses/<FACTORY>/transactions?filter=to`
   for new `createToken` txs; extract the created CA from the receipt logs
   (Transfer from 0x0 event) or internal `create2`.

## Pitfalls

- **CSP nonces break naive HTML hashing.** `nonce="..."` changes on EVERY
  request. Strip it (`re.sub(r'nonce="[^"]+"', 'NONCE', html)`) before hashing,
  or every poll reports a "change" (false positive).
- **Bot-spam filter: match markers on DECODED calldata, not the hex string.**
  Hex only contains 0-9a-f, so `"cli" in hex` never matches. Decode
  `bytes.fromhex(input[2:]).decode('latin1')` first, then test
  `cli|automated|fast_|deploy|bot `. Also check deployer `/counters`
  `transactions_count` — >2000 txs = bot farm, skip.
- **Cron minimum is 1 minute.** For 30-second polling, use a background daemon
  loop that sends Telegram directly (bot token + home channel from
  `~/.hermes/.env`), not cron. Cron `no_agent` watchdog prints only on change;
  empty stdout = silent.
- **Telegram 4096-char limit**: split long reports into `<4000`-char blocks
  with a `--- part N/M ---` marker so nothing truncates.
- **Blockscout token-balances returns a LIST** (`[...]`), not `{"items": [...]}` — iterate directly or you hit `AttributeError: 'list' object has no attribute 'get'`.
- **`submitBid` can target a proxy/router**, not the raw auction — collect full `to` hashes from the tx list before reading state.
- **"Fill 20%" does NOT mean 80% is refunded.** In a graduated CCA, the whole bid converts to tokens at the clearing price. UI fill indicators are pricing, not refund accounting.
- **Failed auction ≠ automatic refund.** `sweepUnsoldTokens` is creator-called and one-shot (`sweepUnsoldTokensBlock() == 0` gate); bidder recovery requires explicit claim. In bot-launched tokens, the creator often sweeps first — user funds can be stranded.
- **RPC rate-limits on bursts** (HTTP 403). Space `eth_call`s; retry after a pause.
- **Robustness over guesswork.** If you cannot confirm the outcome (auction state ambiguous), say so and show the raw numbers — don't invent a refund path that doesn't exist in the ABI.
- **MC vs FDV is a three-number trap on launchpads.** For the SAME token at the SAME price you can legitimately see: (1) frontend UI shows FDV = live price × TOTAL supply (e.g. pools.trade UI showed FROGE $940K = $0.00094 × 1B); (2) dexscreener shows MC = live price × CIRCULATING supply (~74% — rest is LP-locked) = $700K; (3) the platform API's raw `fdvUsd` field may be STALE = auction clearing price × supply (FROGE API said $551K long after price moved). Always identify which supply AND which price each number uses. Standard answer to "what's the MC" = dexscreener MC (circulating).
- **404 token page ≠ delisted/banned.** Frontends index graduated auctions LATE. FROGE 404'd on pools.trade for hours, then appeared fully in `cca.listAuctions` with complete data (raised $141K, 413 bidders). Before concluding "removed from home", re-check the API after a delay and compare listing status over time.
- **Frontend listing depends on strategy GENERATION, not just official launcher.** A token launched via the official launcher but distributed to an OLD strategy generation (FROGE → LBPStrategy deployed 10 Jul) did not appear in the pools.trade list, while tokens on the NEW generation (InstantLaunchStrategy deployed 05 Aug, re-deploy commit) did. Both strategies were deployed by the SAME Uniswap team wallet (`0x32f4B2e6…`) and both are in the GitHub addresses.ts — the frontend just only tracks the newer one (plus seeded legacy tokens). Verify which strategy the token was distributed to via `TokenDistributed(address token, address strategy, uint256 amount)` (strategy = topics[2]).
- **Debunk "first launch" claims by scanning launch EVENTS, not tweets.** FLAMINGO's tweet said "first" but it was launch #923 on SushiLaunchpad. Recipe: keccak256 the launch event signature → topic0; `eth_getLogs` from launcher deploy block to token creation block with `topics:[topic0]` + `address:<launcher>`; count events. >0 before the token = NOT first. See `references/launchpad-data-verification.md` for the full recipe.
- **Multi-address event topics: topics[1] is NOT always the token.** For `TokenLaunched(address creator, address token, address pool, address quoteToken, …)` only the first three addresses are indexed: topics[1]=creator, topics[2]=token, topics[3]=pool. Decoding topic[1] as the token yields the deployer's address. ALWAYS pull the ABI (`/api/v2/smart-contracts/<LAUNCHER>` → `abi`) and check `indexed: true` before decoding topics.
- **`eth_getLogs` has a 10,000-log-per-query limit.** "logs matched by query exceeds limit of 10000" → halve the block-range chunk (start ~1M blocks, fall to ~100K). Robinhood public RPC accepts `eth_getLogs` with browser UA + retries even when `eth_call` bursts 403.
- **Dexscreener batch endpoint: up to ~30 addresses per call.** `GET /latest/dex/tokens/<a1>,<a2>,…` returns all their pairs. For 1,000+ tokens: 25-30 per batch + ThreadPoolExecutor (8-10 workers) — 1170 individual queries timed out at 300s, 47 batched calls finished in seconds. Response is a flattened `pairs` array — group by `baseToken.address`, keep best-liquidity pair per token.

## Verification

```bash
# Proves auction graduated and how much was raised (the core outcome):
curl -s -X POST "https://rpc.mainnet.chain.robinhood.com" -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":"<AUCTION>","data":"0x9e5f2602"},"latest"]}' \
  -d '{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":"<AUCTION>","data":"0x998ba4fc"},"latest"]}'
```

Real result: `isGraduated` true + `currencyRaised` > 0 → bids became tokens (no refund). Pairs with the user's summed bids to deliver the verdict.
