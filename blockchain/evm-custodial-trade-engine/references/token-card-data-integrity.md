# Token-card data integrity: partial RPC failures and multi-version pools

## Failure signature

A trading card can look successfully scanned while being internally invalid:

```text
name/symbol = ?
market cap = $0
liquidity = $0
DEX label = a hardcoded protocol
buy buttons remain enabled
```

A common chain of failure is:

1. An ERC-20 `name()` call succeeds but `symbol()`, `decimals()`, or `totalSupply()` is rate-limited.
2. A best-effort view helper converts errors to `nil`, `?`, zero, or default decimals.
3. The partial `TokenInfo` is cached for minutes.
4. Pool discovery chooses V3 whenever any V3 pool exists, ignoring a deeper V2 pool.
5. Metrics call V3 `slot0` regardless of the selected protocol and swallow errors into zero.
6. The card renders `$0` as measured data and leaves trade controls active.

## Reproduction recipe

For each reported token:

1. Call ERC-20 `name`, `symbol`, `decimals`, and `totalSupply` independently via `eth_call`; record partial rate-limit behavior.
2. Discover all configured V2 pairs and V3 fee-tier pools against the quote asset. Include safe V4 candidates when supported.
3. Compare on-chain quote-side liquidity and executable quote output per amount.
4. Run the application's actual `ReadTokenInfo` and `ComputeTokenMetrics`, not only standalone RPC probes.
5. Inspect runtime logs for `success=true` scans that produced placeholder metadata—this indicates validity was defined too weakly.
6. Restart/invalidate caches after fixing non-caching rules.

## Correctness rules

### Required metadata

A cacheable identity requires:

```text
non-empty non-placeholder name
non-empty non-placeholder symbol
decimals successfully decoded
totalSupply successfully decoded and positive when policy requires it
```

Retry idempotent reads with a small bound. Use multiple independently operated RPC endpoints; a successful `eth_chainId` probe does not guarantee that subsequent `eth_call`s will avoid rate limits. Do not cache partial objects.

### Pool selection

Do not use `if V3 exists, choose V3`. One token can have simultaneous V2/V3/V4 pools. For a display pool, compare reliable on-chain quote-side liquidity. For execution, compare amount-aware executable quotes and gas where convertible.

For V2, derive reserve ordering from token addresses or `token0/token1`. For V3, probe relevant fee tiers and require valid `slot0`. Keep display selection and execution selection explicit if they optimize different goals.

### Protocol-aware metrics

- V2: `getReserves`, correct token ordering, `price = quoteReserve/tokenReserve`, approximate direct-pair liquidity `2 × quoteReserve`.
- V3: required `slot0`, token ordering, and pool balances/StateView as appropriate. A failed call is unavailable—not zero.
- V4: use verified PoolKey/PoolId and StateView/route semantics; PoolId stays bytes32.

Market cap is unavailable if required price or supply is unavailable. Never infer `$0` from an RPC error.

### Card behavior

- DEX label comes from selected protocol.
- Missing values render `Tidak tersedia` (or locale equivalent) with a warning.
- Buy controls are withheld when token identity or required execution metrics are incomplete.
- A zero configured priority fee renders `Auto` if the transaction engine estimates it dynamically.

## Required tests

- first metadata read rate-limited, second succeeds;
- incomplete metadata is not cached;
- cached complete metadata remains stable;
- a dominant V2 pool beats a smaller V3 pool;
- V2 reserve ordering and liquidity math;
- V3 `slot0`/balance failure returns error, not zero metrics;
- card DEX label for V2/V3/V4;
- missing metric renders unavailable;
- incomplete card has no buy callbacks;
- zero fee configuration renders `Auto`.

## Verification evidence shape

Report:

```text
address
resolved name/symbol/decimals
selected protocol and pool/poolId
raw quote-side liquidity
computed price/market cap/liquidity
metric error, if any
cache invalidation/restart status
full race/vet/build result
```

Never use an external indexer as the final source of truth. It can help identify candidate pools, but verify metadata, pool identity, reserves/StateView, and executable quotes on-chain.
