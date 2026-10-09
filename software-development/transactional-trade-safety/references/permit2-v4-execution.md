# Permit2 and Uniswap V4 Execution Safety

Use for protocol adapters that combine ERC20 approval, Permit2 allowance transfer, hooked V4 pools, Universal Router calldata, and receipt accounting.

## Permit2 boundaries

- Canonical allowance call order is `allowance(owner, token, spender)` and output is `(uint160 amount, uint48 expiration, uint48 nonce)`.
- Pack Permit2 approvals as `approve(token, spender,uint160,uint48)`; reject amount/expiration overflow before ABI packing.
- Bound expiration to an explicit short maximum lifetime. Never silently issue effectively unlimited time.
- ERC20 approval to Permit2 should be exact. If current allowance is nonzero and differs from the required amount, submit zero first, then the exact amount.
- Copy caller-owned `big.Int` values into plans/results; do not retain mutable aliases across goroutines.
- Native currency `address(0)` never takes ERC20 or Permit2 approval. WETH is an ERC20 and must use ERC20/Permit2 with `msg.value == 0`.

## Hooked V4 pools

- Address allowlisting alone is insufficient. Before quote and execution, fetch runtime code and compare `keccak256(runtimeCode)` with a chain-scoped pinned hash.
- Empty code, unknown hook, RPC failure, or hash mismatch fails closed.
- Keep quote/execution ABI encoding hook-aware; never clear the hook address merely to pass a generic safety validator.
- Pool identity is bytes32. If an older route interface exposes `Pool() address`, return an explicit non-identity sentinel and add `PoolID() common.Hash`; never truncate bytes32 into an address and call it canonical.

## Universal Router execution

- Use command `V4_SWAP (0x10)` without allow-revert for ordinary swaps.
- Pin router ABI by chain/deployment. Older Base direct tuples and newer routers with `minHopPriceX36` are not interchangeable.
- Preserve `SwapOpts` prepared/submitted/mined callbacks through the send seam.
- Only native input sets `TxOpts.Value = amountIn`; WETH routes set zero value.
- Never invent a native `PoolKey` to avoid wrapping. Use a PoolKey recovered from the canonical `Initialize` event and verify its PoolId. If the supplied direct pool takes WETH and atomic wrap+swap is not implemented, reject only that WETH-input route.
- Derive received ERC20 output from canonical `Transfer` logs to the signer. Native output must fail closed until the adapter has a chain/router-specific canonical payout event or balance-delta accounting contract.
- A dry run must not approve or submit.

## Fixture and integration evidence

- Treat token addresses, PoolIds, and PoolKeys as distinct evidence. A token address does not determine a unique PoolKey.
- For every supplied fixture, pin all five PoolKey fields plus an independently sourced expected PoolId; recomputing an ID from the same fixture without comparing to external evidence is circular.
- Read-only fixture acceptance requires an actual RPC quoter call or router simulation. A fake returning ABI-shaped bytes proves local decoding only.
- Wire the adapter into every active execution surface: manual buy, manual sell, TP/SL initial quote, TP/SL trigger re-quote, and TP/SL execution. Search for all engine constructors rather than patching one call site.
- Remove obsolete feature-disabled sentinels/tests once execution is enabled; contradictory blockers create false confidence.
- In concurrently edited workspaces, re-read a file immediately before each patch and avoid duplicating helpers introduced by another writer.

## Focused TDD matrix

1. Permit2 ABI round-trip and uint160/uint48 overflow.
2. Exact allowance zero-first behavior and mutable-input alias test.
3. Native-vs-WETH `msg.value` distinction.
4. Matching hook runtime succeeds; changed runtime fails under concurrent calls with `-race`.
5. Callback order and error propagation through the injected sender.
6. Canonical receipt output and missing-output failure.

## Verification fallback

When no canonical gate is detected, create an OS-safe temporary script with a `hermes-verify-` prefix outside the repository. Check formatting, run focused race tests, then broad regression tests. Report this explicitly as **ad-hoc verification**, not canonical CI evidence. Run verification separately from cleanup if cleanup approval could block or hide the test result.
