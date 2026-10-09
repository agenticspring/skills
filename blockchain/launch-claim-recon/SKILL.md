---
name: launch-claim-recon
description: Verify token launch claims from tweets; profile deployer.
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Token Launch, Launcher, Sybil, Fund Trace, EVM, Robinhood Chain, Social Claims]
---

# Launch Claim Recon

Verify claims from social posts about a newly launched token or launch platform: "this is the official launch contract", "deployed with the addy in GitHub", "launched first", "this is the platform token". Separates what is REAL infra from what is team-endorsed, and detects whether the "insider deployer" is a human, a bot, or a sybil farm.

Complements `onchain-claim-verify` (which verifies a single tx claim) and `mint-fund-trace` (NFT fund flows). This skill is for the *token-launch narrative* class: is the platform real, is the token official, who launched it.

## When to Use

- Tweet claims a token is "the first launch" on some new launcher/pool platform
- "Deployed with addy in GitHub" / "this is [project]'s official contract"
- A launch platform frontend is being reconned (pools.trade, etc.) — is it real?
- Someone posts a token and calls the deployer an "insider" — is it a person or a bot farm?
- Deciding whether a new memecoin on a fresh launcher is a legit first-mover play or a sybil trap

## Prerequisites

- `cast` CLI (foundry) — `command -v cast || curl -L https://foundry.paradigm.xyz | bash`
- Public RPCs: Robinhood Chain (4663) `https://rpc.mainnet.chain.robinhood.com` (Cloudflare-fronted; ~200ms/call, rate-limits hard under burst — sleep between calls)
- Blockscout v2 API: `https://robinhoodchain.blockscout.com/api/v2/` (or `<chain>.blockscout.com`)
- DexScreener: `https://api.dexscreener.com/latest/dex/tokens/<addr>` and `https://api.dexscreener.com/tokens/v1/<chain>/<addr>`

## How to Run

Invoke probes through `terminal` (curl + cast) and `execute_code` (batched, rate-limited loops). Fetch tweet content via fxtwitter, verify GitHub addresses via raw.githubusercontent, verify on-chain via Blockscout/RPC.

## Quick Reference

```bash
# 1. Read the tweet (no X session needed)
curl -s "https://api.fxtwitter.com/i/status/<status_id>" | python3 -c "
import json,sys; d=json.load(sys.stdin)['tweet']
print(d['author']['screen_name'], d['author']['followers'], d['created_at'], d['text'])
for m in (d.get('media') or {}).get('all',[]): print(m.get('url'))"

# 2. Check GitHub file + commits for claimed addresses
curl -s "https://raw.githubusercontent.com/<org>/<repo>/<branch>/<path>" > /tmp/addr.ts
grep -i "<address>" /tmp/addr.ts          # is the address in the file?
curl -s "https://api.github.com/repos/<org>/<repo>/commits?path=<path>"  # is repo active?

# 3. Verify factory deployed the token (Blockscout)
curl -s "https://robinhoodchain.blockscout.com/api/v2/addresses/<token>" | python3 -c "
import json,sys; d=json.load(sys.stdin)
print(d.get('creator_address_hash'), d.get('is_verified'), d.get('creation_transaction_hash'))"

# 4. Token metadata via RPC
curl -s -X POST https://rpc.mainnet.chain.robinhood.com -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":"<token>","data":"0x06fdde03"},"latest"]}'

# 5. Bot/sybil tell: total tx count
curl -s "https://robinhoodchain.blockscout.com/api/v2/addresses/<wallet>/counters" | python3 -c "
import json,sys; d=json.load(sys.stdin); print(d.get('transactions_count'), d.get('token_transfers_count'))"
```

## Procedure

### A. Verify the platform/infra claim
1. **Read the tweet first** via fxtwitter (above). Note the claimed addresses, GitHub links, and screenshots. Download media at `?name=orig`.
2. **Fetch the exact GitHub file** from raw.githubusercontent. Grep for EVERY claimed address. A repo with commits dated today = active infra; no commits in months = stale.
3. **Check the token address itself in GitHub** AND in recent commit SHAs (`raw.githubusercontent.com/<org>/<repo>/<sha>/<path>`). 0 hits = the claim is about the *factory/launcher* address, not the token.
4. **Verify on-chain who created the token**: Blockscout `creator_address_hash` should equal the factory from GitHub. `is_verified: true` on the factory = source-verified.
5. **Get launch timeline**: token `creation_transaction_hash` → tx `timestamp` + `internal-transactions` (look for `create2 from: <factory> created: <token>`, and which strategy was called).
6. **Check the frontend** (if a platform site exists): DNS nameservers vs parent domain (matching Cloudflare NS = same operator), JS bundle `VITE_*` env leaks (`VITE_ENTRY_GATEWAY_URL` pointing at `*.api.<brand>.org` = real backend), CSP `connect-src` for RPC/API endpoints, WHOIS creation date, dev/staging subdomains via `dig`.

### B. Official vs permissionless
- **A permissionless factory (`createToken`/`create2`) means ANYONE can launch through it.** "Deployed via the official factory" ≠ "made by the team". This is the classic Pump.fun/launcher trap: infra is legit, token is not endorsed.
- "First token through the launcher" is a real but weak narrative: anyone can be first, and bots race for it.
- Team endorsement requires more: an official announcement naming the token, a token with the same name as the platform AND launched by the team's own deploy wallet — not just the factory.

### C. Profile the deployer (person vs bot vs sybil)
1. **Total tx count**: `addresses/<w>/counters` — 100K+ txs and millions of token transfers = automated bot. A dev wallet has hundreds.
2. **Vanity address pairs**: two EOAs sharing a long substring (e.g. 32 of 40 chars identical, like `...97812CB96acDF810712Aa562db8dfA3...`) are deliberately generated by the same entity. Loop-compare 6-char substrings against known cluster wallets to confirm.
3. **Funding path**: `addresses/<deployer>/transactions?filter=to` — same funder across multiple token deployers, funding 1–2.5h BEFORE each launch = coordinated operator.
4. **L1/L2 pair**: a high-tx L2 funder receiving 50–112 ETH chunks from a vanity-paired L1 wallet via `submitRetryable` (Arbitrum bridge) = one operator bridging under multiple addresses.
5. **Fee-revenue tell**: deployer calling `collectFees` on the official fee splitter after launch = configured as beneficiary/creator (consistent with being the launch creator, NOT proof of team membership).

### D. Verify "first launch" claims with event scanning
1. **Fetch the launcher's verified ABI** from Blockscout: `/api/v2/smart-contracts/<LAUNCHER>` → `abi` — find the launch event (`TokenLaunched(...)`, `TokenCreated(address)`, etc.) and note which inputs are `indexed`.
2. **Compute topic0** = keccak256 of the full event signature (e.g. `TokenLaunched(address,address,address,address,int24,string,string,uint16,uint256,uint64,uint16)`). `from Crypto.Hash import keccak`.
3. **Scan `eth_getLogs`** from the launcher's deployment block to the token's creation block, filtering `address: LAUNCHER, topics: [topic0]`. Zero events before the token = genuinely first. **Decode indexed addresses carefully**: for `TokenLaunched(creator, token, pool, ...)` all three are indexed → topics[1]=creator, **topics[2]=token**, topics[3]=pool. Don't assume topics[1] is the token — check the ABI.
4. **Pitfall: eth_getLogs 10K-log limit.** `{"error":{"code":-32000,"message":"logs matched by query exceeds limit of 10000"}}` — halve the block range chunk (100K blocks works on Robinhood) and re-query in a loop.
5. **Count all launches ever**: paginate chunks from deploy block to latest. This session: FLAMINGO on SushiLaunchpad claimed "first" but was #923 of 1,170 total — deploy 28 Jul, first launch hours later, FLAMINGO at 05 Aug 23:35.
6. **Batch market-cap/volume ranking**: `GET https://api.dexscreener.com/latest/dex/tokens/<a>,<b>,...` (comma-joined, ~25-30 per call) with ThreadPoolExecutor (8-10 workers). Pick best pair per token by liquidity. Expect a long tail: pools.trade 22,875 tokens → only ~576 (2.5%) still had pairs; SushiLaunchpad 1,170 → ~300.

### E. Check frontend listing (token valid on-chain ≠ token shown on the launchpad UI)

A token can be fully valid on-chain (launched through the official launcher, verified contracts, real pool with volume) yet completely absent from the launchpad's own frontend — because the backend only tracks current-generation strategies. Do NOT report "deleted/removed/hidden" without proving it was ever listed.

1. **Read the frontend's data API** (pools.trade uses tRPC): open the home page in a headless browser and intercept `* /api/trpc/*` requests, or replay the exact batched call:
   ```
   GET /api/trpc/cca.listAuctions,curve.listLaunches,session.status,prices.getTokens?batch=1&input=<urlencoded JSON>
   ```
   Input shape is `{"1": {procs args}, "3": {tokens:[...]}}` — the key numbers are procedure positions, and a procedure that takes no input (e.g. `curve.listLaunches`) is simply OMITTED from the input map. Decode with `urllib.parse.unquote`.
2. **Check the token page directly**: `https://pools.trade/token/<CA>` → "404 Not Found" body means the backend has NO record of the token (never listed, not merely filtered from home).
3. **Check the strategy generation on-chain** — this is the root cause discriminator. For each token, find the `TokenDistributed(address,address,uint256)` event from the launcher → `topics[2]` = strategy contract → `/api/v2/smart-contracts/<strategy>` name. Generation matters:
   - Old LBPStrategy (deployed weeks earlier) → backend may not track it after a full-redeploy
   - New InstantLaunchStrategy (deployed same day as redeploy) → tracked
   - Both can be deployed by the SAME official team wallet — "official strategy" ≠ "frontend-tracked strategy".
4. **Verify the token is still tradeable**: dexscreener pool + liquidity — a high-volume token absent from the UI is real but unlisted, not a scam. Report both facts: "valid on-chain, trading X/24h, but not featured/listed on the platform frontend".

### F. Deliver the verdict
State separately: (1) infra is real or fake, (2) token is team-endorsed or just launched-through, (3) deployer is human/bot/sybil with evidence. Never conflate "real factory" with "official token".

## Pitfalls

- **Blockscout v2 pagination is NOT `?page=N`** (returns 422) and **prefix/truncated hashes return 422** — use `next_page_params` from the response or fetch full hashes from the address tx list first.
- **Blockscout rate limits hard** — sleep 2s between calls; re-fetch once if empty.
- **RPC 403 under burst** — the Robinhood public RPC rate-limits fast; use `execute_code` with sleeps or switch to `https://robinhood-rpc.publicnode.com`.
- **DexScreener pair age ≠ token creation** — `pairCreatedAt` is the first pool; token may predate it. Use Blockscout `creation_transaction_hash` for true birth.
- **"Verified" on explorer ≠ team ownership** — `is_verified` only means source code was uploaded.
- **Vision model may be unavailable** — OCR screenshots with tesseract: `ffmpeg -ss <t> -i vid.mp4 -frames:v 1 f.jpg`, then `ImageOps.autocontrast` + `ImageEnhance.Contrast(3.0)` before `tesseract --psm 6`. Bottom strips often contain recording timestamps.
- **fxtwitter 404 = deleted/private tweet** — don't conclude "never existed"; check web archives if timeline matters.

## Verification

A single command proving the core claim resolved:

```bash
curl -s "https://robinhoodchain.blockscout.com/api/v2/addresses/<token>" | python3 -c "
import json,sys; d=json.load(sys.stdin)
print('creator:', d.get('creator_address_hash'), '| verified:', d.get('is_verified'))" \
&& curl -s "https://api.dexscreener.com/latest/dex/tokens/<token>" | python3 -c "
import json,sys; p=(json.load(sys.stdin).get('pairs') or [{}])[0]
print('chain:', p.get('chainId'), '| dex:', p.get('dexId'), '| vol24h:', (p.get('volume') or {}).get('h24'))"
```

If the creator matches the GitHub factory and the tweet's claim matches the on-chain timeline, the infra claim is verified — then apply Section C before calling the token "official".

## References

- `references/pools-trade-unifrog-case.md` — worked example: pools.trade/Uniswap Robinhood launcher, UNIFROG/POOLS/FORK/FRONG, sybil funder trace.
- `references/pools-fun-sushi-flamingo-case.md` — worked example: pools.fun (Sushi) teaser recon, SushiLaunchpad verification, FLAMINGO "first launch" debunked via TokenLaunched event scan (#923 of 1,170), batch volume ranking across 22,875 pools.trade tokens.
- `references/pools-trade-froge-unlisted-case.md` — worked example: FROGE valid on-chain ($4.66M vol) but absent from pools.trade home — root cause = old-generation LBPStrategy not tracked by backend, not "removed by dev". Includes the tRPC batch-input recipe.
