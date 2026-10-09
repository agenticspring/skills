# Launchpad Data Verification — Event Scanning & Listing Truth

Session-tested recipes (2026-08) for verifying launchpad claims on Robinhood
Chain (chainId 4663). Complements the main SKILL.md procedure.

## 1. Enumerate EVERY token a launchpad created (TokenCreated / TokenLaunched)

The launch event signature and its indexed fields differ per platform. Get the
ABI first, never guess:

```python
from Crypto.Hash import keccak

def keccak256(sig):
    k = keccak.new(digest_bits=256); k.update(sig.encode())
    return "0x" + k.hexdigest()

# Uniswap LiquidityLauncher (pools.trade):
topic0 = keccak256("TokenCreated(address)")   # topics[1] = token
# SushiLaunchpad (pools.fun):
topic0 = keccak256("TokenLaunched(address,address,address,address,int24,string,string,uint16,uint256,uint64,uint16)")
# topics[1]=creator, topics[2]=token, topics[3]=pool  ← verify indexed flags in ABI
```

Pull ABI: `GET /api/v2/smart-contracts/<LAUNCHER>` → `abi` array; for each event
input check `indexed: true`. The first indexed field is frequently the creator
or pool, NOT the token.

## 2. eth_getLogs with the 10k-limit chunking

```python
def scan_launch_events(launcher, topic0, start_block, end_block):
    logs = []
    chunk = 1_000_000
    cur = start_block
    while cur < end_block:
        end = min(cur + chunk, end_block)
        res = rpc_call("eth_getLogs", [{
            "fromBlock": hex(cur), "toBlock": hex(end),
            "address": launcher, "topics": [topic0],
        }])
        if "exceeds limit" in str(res.get("error", "")):
            chunk = max(chunk // 2, 10_000)   # halve, retry same range
            continue
        logs.extend(res.get("result", []))
        cur = end + 1
        time.sleep(0.3)
    return logs
```

Find the launcher's deploy block via blockscout:
`/api/v2/addresses/<LAUNCHER>` → `creation_transaction_hash` →
`/api/v2/transactions/<HASH>` → `block_number`.

Decode token address: `"0x" + topics[N][-40:].lower()`.

## 3. Debunking "first launch" — worked example (FLAMINGO / SushiLaunchpad)

Claim: "$FLAMINGO first launch on pools.fun". On-chain:

- SushiLaunchpad deployed block 21,957,383 (28 Jul 22:39 UTC)
- FLAMINGO launch block 28,885,821 (05 Aug 23:35 UTC)
- `eth_getLogs` TokenLaunched in that range → **922 events**
- First launch block 21,966,938 ≈ 6h after deploy
- → FLAMINGO was launch #923, NOT first. Same pattern as pools.trade: the
  "first launch" narrative is marketing; launchers are permissionless and bots
  spam hundreds of tokens within hours.

pools.fun itself = Sushi's teaser site ("same pools, more fun. coming soon on
Sushi") hosted on Netlify, AWS Global Accelerator edge IP, GoDaddy domain
registered 05 Aug 2026 — same day as the SushiLaunchpad full-redeploy.

## 4. Why a token is missing from the frontend list (worked example: FROGE)

FROGE (0x1df1f09c4dd65c76746d53467361d536cdfdc719):

- Launched via official LiquidityLauncher FINAL (`0x0000FffF…`) 05 Aug 21:58
- `TokenDistributed` → strategy `0x05d552…` = **LBPStrategy** (deployed 10 Jul,
  old generation, still in GitHub addresses.ts)
- Frontend `cca.listAuctions` / `curve.listLaunches` returned 0 hits; token page
  `/t/<CA>` → 404
- Tokens that DID appear used **InstantLaunchStrategy** `0x23f820…` (deployed
  05 Aug 13:25, the post-redeploy generation) or were seeded legacy (FRONG, POOLS)

Later re-check: FROGE appeared in `cca.listAuctions` with full data
(status=graduated, raised $141K, 413 bidders, holderCount 3600) — the backend
had simply indexed the graduated auction late. Lesson: 404 ≠ banned; re-poll
after a delay; compare the distribution strategy, not just the launcher.

## 5. Home-page tRPC surface (pools.trade)

Home page fetches one batched tRPC call:
`/api/trpc/cca.listAuctions,curve.listLaunches,session.status,prices.getTokens?batch=1&input=…`

- `cca.listAuctions` body input: `{"1":{"sortBy":"volume"}}`
- `curve.listLaunches` takes NO explicit input key in the batch (omitted = no params)
- Token page uses `cca.getAuctionByAddress` / `curve.getLaunchByAddress`
  body: `{"0":{"tokenAddress":"<CA>"}}`
- `curve` item fields: `status` ("curveLive"), `createdAt`, `fdvUsd`,
  `holderCount`, `poolId`, `launchpadId` — note fdvUsd can be stale (clearing
  price × supply) while the rendered UI shows live price × total supply.

## 6. MC vs FDV — the three-number trap (worked example: FROGE)

| Source | Price used | Supply used | Result |
|--------|-----------|-------------|--------|
| pools.trade UI | live $0.0009408 | total 1B | FDV $940K |
| dexscreener | live $0.0009449 | circulating ~742M (74.2%) | MC $700K |
| pools.trade API `fdvUsd` | clearing $0.0005516 | total 1B | $551K (stale) |

Dexscreener `marketCap` and `fdv` fields are usually EQUAL on these pairs —
both computed from what it considers circulating. The launchpad UI calls its
live number "FDV" because it multiplies by full supply. For "what's the market
cap" answer with dexscreener's MC.

## 7. SushiLaunchpad quick facts (for comparison work)

- Contract verified, Solidity 0.8.36, functions: `launch`, `launchAndBuy`,
  `launchAndBuyNative`, `distributeFees`, `withdrawLaunchFees`, `sushiFeeBps`,
  `v3Factory`, `positionManager`
- Deployer `0x104Cf4b0…` (bridge-in wallet: RelayDepository/Symbiosis)
- 1,170 TokenLaunched events total; only ~300 tokens had live dexscreener pairs
  (~74% dead) — same permissionless-bot-farm pattern as pools.trade
- Top MC: MEOWSHI $598K, FLAMINGO $386K (vol leader $3.26M)
