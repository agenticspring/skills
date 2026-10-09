# Token Scan Performance — RPC Waterfall Audit

Use this when a token card takes several seconds to appear.

## Measure before changing

Build a temporary harness that times, separately:

```text
RPC client/health selection
ReadTokenInfo / chain detection
ComputeTokenMetrics
wallet balances
external fiat price / gas estimate
Telegram send/edit
total card latency
```

Benchmark both cold process state and repeated warm scans. Remove the harness after recording results.

## Recurring bottlenecks

### Duplicate chain detection
A common UI bug is:

```text
tokenCardContent → detect chain + ReadTokenInfo
showTokenCard     → detect chain + ReadTokenInfo again for chain key
```

Return/reuse the detected chain, or reload the setting that the first detection persisted. Never rerun RPC discovery solely to obtain a cache key.

### Static metadata reread
Cache immutable/slow-moving `TokenInfo` globally by normalized `chain + CA` with a bounded TTL (for example 10 minutes): name, symbol, decimals, supply, pool, fee tier, quote, deployer/socials, limits, router/quoter context. Dynamic pool/wallet state must remain fresh.

### Direct-V3 factory waterfall
For tokens outside launcher ABIs, `getPool` across fee tiers and quote-liquidity probes are independent. Run tiers concurrently with a bounded group, then choose the pool with the greatest quote liquidity. Token metadata getters can also be parallelized or batched.

### Dynamic metrics waterfall
These reads are usually independent and should run concurrently or through Multicall3:

```text
slot0, token0, quote balance(pool), token balance(pool),
dead balance, zero balance, block number
```

Do not let optional reads fail the whole card unless the metric is essential.

### Card enrichment serialization
After TokenInfo is known, overlap dynamic metrics, wallet quote/token/native balances, gas price, and cached fiat price. External custom-emoji generation must always remain outside the initial-card critical path.

## Permanent observability

Log one structured event per card:

```text
token_scan chain=<key> token=<CA>
detect_ms=<n> metrics_ms=<n> wallet_ms=<n>
telegram_ms=<n> total_ms=<n> cache_hit=<bool> success=<bool>
```

This prevents future performance debugging from becoming guesswork.

## Verification targets

Choose targets from measured RPC latency. A practical baseline for a healthy EVM RPC is:

```text
cold card ≤ 3s
warm card ≤ 1s
```

Run `go test -race -shuffle=on -count=1 ./...`, `go vet ./...`, build, then benchmark cold and warm again. Preserve correctness: largest-liquidity pool selection, current metrics, and fresh wallet balances.
