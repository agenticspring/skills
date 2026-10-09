# Native unwrap receipt and PnL publication gate

## Observed integration pattern

A successful Robinhood-chain native sell routed through a trusted SwapRouter emitted:

```text
Token Transfer(wallet → pool)
WETH Transfer(pool → router)
Swap event
WETH Transfer(router → address(0))
```

No WETH `Withdrawal(router, amount)` event was emitted. The wallet's native balance increase, after adding receipt gas cost back, matched the router-to-zero WETH burn.

## Decoder rule

For a configured wrapped-native quote asset, consider native output receipt-derived when either event exists on the configured WETH contract:

1. `Withdrawal(router, amount)`; or
2. `Transfer(router, address(0), amount)`.

Require the configured trusted router as indexed sender. Do not treat arbitrary WETH burns, transfers to a third party, or a wallet-wide balance delta as output proof.

## Recovery rule

A status-1 receipt with an unknown/missing decoder result remains unresolved. After decoder support is added, the normal reconciler must reread the canonical receipt and apply the existing journal idempotently:

```text
unresolved → mined(received) → accounting → accounted
```

Verify the durable position mutation and receipt-derived proceeds before declaring a PnL value.

## PnL rule

Do not offer or render a PnL card while any journal for the same user/chain/token is in:

```text
prepared, submitted, unresolved, mined, accounting
```

A zero percent card during unsettled accounting is misleading. Show a clear pending message instead.
