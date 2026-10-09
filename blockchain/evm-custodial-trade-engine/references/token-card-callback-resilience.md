# Token-card callback resilience

## Trigger

A known live token intermittently appears as either:

```text
Gagal baca metrik pool
Token tak terbaca / pool tidak ada
```

while direct read-only RPC checks show valid token metadata, pool, and metrics.

## Root cause

Telegram callback/edit contexts can be cancelled before UI rendering finishes. If only metadata/metrics are detached but balance or formatting reads retain the original context, the card can still render misleading zero balances/holdings or omit Sell controls.

## Safe pattern

1. Create exactly one render budget:

```go
cardCtx, cancel := context.WithTimeout(context.WithoutCancel(parent), 12*time.Second)
defer cancel()
```

2. Use `cardCtx` for every read-only operation in the render:
   - chain detection and `ReadTokenInfo`;
   - pool metrics;
   - quote/token/native balances;
   - holdings quote and PnL display quote;
   - USD conversion, gas tiers, and estimated costs.
3. For metrics retry, derive independent child attempts from `cardCtx`:

```text
attempt 1: ≤4 seconds
attempt 2: ≤4 seconds
```

4. Keep all writes on the original operation context. Never apply this to approval, signing, swap, bridge, or journal writes.
5. On exhaustion, report a retryable verification/RPC message—not that the CA or pool is missing.

## Robinhood V3 evidence

Token `0x01637b14B7378B99dE75A64d50656d98488D9a4d` (`MARIAN`) was verified read-only on Robinhood:

```text
pool: 0xFE331fD29b54bCE09D52988FA691e3B18B0A4081
protocol: Uniswap V3
fee: 10000
metrics: valid
```

Therefore intermittent UI failure was a render-context issue, not a missing CA/pool.

## Verification

- reproduce direct `ReadTokenInfo` + `ComputeTokenMetrics` against the reported chain;
- test cancelled parent context does not cancel the card read context;
- test read failures do not render numeric zero as real data;
- run focused race tests, then full race/vet/build;
- restart isolated dev worker and confirm actual token-card render before reporting success.
