# EVM trade incident repair: receipt, PnL, and RPC failover

## When a successful sell is shown as unresolved

1. Fetch the exact transaction receipt read-only from a known-good chain RPC and validate `status == 1`.
2. Do not infer output from the position database. Decode expected receipt events using the configured token/router addresses.
3. For native-token sells using known `exactInputSingle(... recipient=router)` followed by `unwrapWETH9`, accepted output evidence is:
   - standard WETH `Withdrawal(router, amount)`; or
   - chain-specific WETH `Transfer(router, address(0), amount)` burn during unwrap.
   Require WETH emitter, router as sender/source, zero-address burn target, positive amount. Do not accept arbitrary transfers.
4. Reconcile the existing durable journal idempotently. A successful receipt plus valid output proof may move `unresolved -> mined -> accounted`; do not send another transaction.
5. Gate PnL cards while any journal for the same user/chain/token is `prepared`, `submitted`, `unresolved`, `mined`, or `accounting`. Never render a numeric fallback as realized PnL.
6. On successful accounting, clear obsolete parser failure text so an `accounted` journal is not misleading.

## RPC / fee-estimation incident procedure

Before changing code, consult official protocol docs and reproduce read-only against the real chain:

- Confirm router sequence and semantics from official Uniswap docs (`exactInputSingle`, `unwrapWETH9`).
- Query `eth_chainId`, latest block, `eth_maxPriorityFeePerGas`, `eth_gasPrice`, token balance, allowance, and then exact calldata with `eth_estimateGas`.
- `eth_estimateGas` is read-only. If it reaches the router and returns `STF`, inspect on-chain token balance and allowance. Do not attribute an inventory-zero/stale-position issue to gas.

### Failover rule

`eth_chainId` alone is not a sufficient health check: an edge service may answer it while returning Cloudflare HTML or blocking fee/read methods. A send-capable RPC probe must successfully complete:

```text
eth_chainId
eth_getBlockByNumber(latest)
eth_maxPriorityFeePerGas
```

For a fund-moving path, bypass cached health once and freshly probe every candidate before signing/broadcast. **Verify that returned `eth_chainId` equals the expected configured chain ID**; a responsive foreign EIP-1559 endpoint is never eligible. Keep multiple independently operated endpoints in the configured list. If a provider returns HTTP 403/Cloudflare HTML, fail closed before signing and show a short sanitized error; never send raw HTML to Telegram.

## UX rule

A failed read-only token card must not be described as proof that the token/pool is absent unless that conclusion is established. Prefer a transient-verification message that asks the user to refresh when RPC availability is ambiguous.
