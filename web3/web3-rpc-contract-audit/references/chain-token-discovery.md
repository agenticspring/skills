# Chain-wide token & DeFi discovery (no indexer, no explorer)

Use when the question is **"are there already tokens on this chain?"**, "any DeFi activity?",
or "who deployed what here?" on a new/low-profile chain whose explorer has no token list, no
verified sources, and no working log index.

The only trustworthy source is a **chain-wide log census by topic**, filtered client-side.

## Why you cannot just ask the explorer

On the worked chain (OP Stack, ~20.5k blocks, ~5 hours old) the explorer returned **0 tokens**.
A topic-only census found **3 ERC-20s and a full Uniswap V3+V4 deployment**. The explorer was
not malicious — it simply had not indexed and had no token registry. Never conclude "no tokens"
from an explorer's token list or a search endpoint.

## Step 1 — the census primitive

`eth_getLogs` **with an `address` filter returned empty (`[]`) on this node**, while the same
call with only a `topics` filter returned real logs for that very address. Treat
address-filtered `eth_getLogs` as unreliable on self-hosted/leaked endpoints:

- Scan with `{"fromBlock":…, "toBlock":…, "topics": [<topic0>]}` — **no `address` key**.
- Filter by address **in your own code** afterwards.
- Chunk the range (~2000 blocks) and fall back to ~250-block sub-chunks when a chunk errors.
- Keep concurrency ~3 and retry with backoff — these endpoints throttle hard.
- Reuse the resumable/gentle pattern from `chain-and-rpc-authenticity.md` Step 10.

Re-runnable: `scripts/chain_topic_census.py`.

## Step 2 — the topic menu

Compute each topic0 as `keccak256(signature)`. Each answers a different question:

| topic0 signature | answers |
|---|---|
| `Transfer(address,address,uint256)` | **which ERC-20s/ERC-721s exist** — every mint/transfer |
| `Approval(address,address,uint256)` | did anyone ever approve a token (DeFi intent) |
| `PoolCreated(address,address,uint24,int24,address)` | Uniswap **V3** pools created |
| `Initialize(bytes32,address,uint24,int24,address,uint160,int24)` | Uniswap **V4** pools created |
| `Swap(address,address,int256,int256,uint160,uint128,int24)` | real trading |
| `Mint(address,address,int24,int24,uint128,uint256,uint256)` | V3 liquidity added |

On the worked chain the whole chain held **5 `Transfer` logs and zero of everything else** —
so "activity" was fully bounded and provable, not sampled.

## Step 3 — liquidity is proven by absence, not inferred

Three independent checks, all cheap:

1. **DEX factory lookup** — for each token, ask the factory directly across every fee tier:
   ```
   factory.getPool(token, WETH, 500) / (…,3000) / (…,10000)
   ```
   All `0x0000…0000` = **no pool exists anywhere** = not tradeable at any price.
2. **Chain-wide `Swap` / `Mint` censuses** = 0 → nothing was ever traded or seeded.
3. **Position-manager NFT `totalSupply()`** — one call that proves whether *any* LP position
   was ever minted on that DEX. `0` = the venue exists but has never been used.

Report these together. "Token exists" and "token is tradeable" are different claims and users
conflate them.

## Step 4 — attribute each token to its creator

`eth_getTransactionReceipt().contractAddress` only reports the **outermost** creation of that
tx. If a token was created by an intermediate contract, the receipt is `null` and you will
wrongly conclude the token has no deployer.

Robust method: from the token's own earliest log get its **block**, pull that block with
`eth_getBlockByNumber(block, true)`, and read `receipt.logs[].address` for each tx in it. A log
emitted by the token inside tx *T* means tx *T* created it — whatever `to` on that tx says.

This is also how you spot the **launcher/factory → token** relationship and the bonding-curve
contract that holds the supply.

## Step 5 — recognise "deploy via bridge" (no L2 gas needed)

A contract can be created on an OP Stack L2 by a **`type 0x7e` deposit carrying init code**.
The L1 sender pays; the L2 address never needs native gas. On the worked chain all three
memecoins were born this way, which is why their creators show `nonce 1`, `balance 0` on L2.

Practical consequences to state for the user:

- A deployer can be **completely empty on L2** and still have deployed contracts there.
- Consequently, an EOA appearing in the organic-tx list as `from` with `to=null` is a **deployer
  via bridge**, not a user transferring value.
- The mirror trick matters for the reverse question too: a user can *fund* an L2 address by
  bridging, which is why deposit txs increment the L2 nonce without any signed L2 tx.

## Step 6 — read mint events correctly

Mint-to-then-forward shows as **two `Transfer` logs in the same tx**:
`Transfer(0x0 → launcher, N)` then `Transfer(launcher → holder, N)`. That is **one mint plus one
move**, not two mints. Always reconcile against `totalSupply()` before quoting a supply number.

Also: `totalSupply() == 0` on an NFT is a strong statement (nothing minted), while a bare
`owner()` revert means only "not `Ownable`" — it says nothing about safety. Enumerate holders by
summing `Transfer` deltas, then confirm each with a live `balanceOf(address)` call; supply split
across two addresses (e.g. 50M to the deployer + 950M to a fresh `nonce 0` wallet) is the normal
shape of a pre-launch meme, not evidence of a sale.

## Step 7 — interpret the pattern, and say what it implies

An empty chain carrying *DEX + launchpad + test memecoins* is not random. Reconstruct the whole
picture: identify each contract by probing well-known getters (`factory()`, `WETH9()`,
`poolManager()`, `permit2()`, `positionManager()`, `token()`, `owner()`) and compare the
addresses against the canonical Uniswap deployment addresses (V3 NFPM
`0xC36442b4a4522E871399CD717aBDD847Ab11FE88`, V4 PoolManager
`0x000000000004444c5dc75cB358380D2e3dE08A90`) — **fresh addresses mean someone deployed their
own copy, not that the venue is official.**

Two conclusions worth delivering:

- **This is a launch rehearsal.** A team is dry-running its full stack so tokens can fire the
  moment mainnet goes live. Say so, and set the expectation of meme season at launch.
- **Nothing here is buyable or endorsed.** No pool = no price. Explicitly warn that any
  "project mainnet token" offered *before* the project's own announcement is not the project's.

## Worked result (OP Stack L2, chain 9134, ~20.5k blocks)

```
Transfer logs, whole chain          = 5
Approval / V3 PoolCreated / V3 Swap
  / V3 Mint / V4 Initialize         = 0 each
tokens found                        = 3 ERC-20, 1e27 supply each, decimals 18, no owner()
pools for any of them               = 0x0 at fee 500 / 3000 / 10000
Uniswap V3+V4 stack deployed by     = 1 EOA, 22 contracts in a 75 s burst
```

Verdict delivered: three memecoins exist, **zero liquidity, zero pools, zero trading**; the
chain is a rehearsal venue, and no token on it is buyable or endorsed.
