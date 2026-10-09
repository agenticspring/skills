# Uniswap V2/V3/V4 Multi-Version Routing

Use this reference when expanding a custodial EVM engine from one Uniswap generation to automatic V2/V3/V4 routing.

## Core model

A token is not intrinsically “V2”, “V3”, or “V4”. The same token can have pools in multiple generations and quote assets. Discover and quote routes **for each exact input amount**, then select an executable route.

```go
type Protocol string
const (
    ProtocolV2 Protocol = "uniswap-v2"
    ProtocolV3 Protocol = "uniswap-v3"
    ProtocolV4 Protocol = "uniswap-v4"
)

type RouteCandidate struct {
    Protocol    Protocol
    Hops        []Hop
    AmountOut   *big.Int
    GasEstimate uint64
}
```

Do not select only by TVL. Compare amount-aware output and, when gas can be expressed in the output asset, net output:

```text
netOut = quotedOut - estimatedGasInOutputAsset
```

If gas conversion is unavailable or unreliable, rank by executable output and expose gas separately rather than inventing a conversion.

## Deployment discovery

Use canonical machine-readable deployment mappings, not search snippets or old explorer labels:

- Uniswap deployments: `https://github.com/Uniswap/contracts/tree/main/deployments/json`
- Chain file: `<chainId>.json`

Pin both address and deployed ABI/commit. Universal Router tuple layouts can differ across deployments. Historical routers may remain indexed after being orphaned.

At startup, verify code exists at every configured factory/router/quoter/PoolManager address. For specially allowlisted hooks, verify runtime bytecode hash as well as chain ID and address.

## Capability and active-path acceptance

Do not infer end-to-end support from adapter tests or a green build. Track each protocol through explicit capability states:

```text
adapter-only → read-only quote → calldata-ready → active execution
```

Before declaring active execution, prove the production-shaped call path:

```text
token discovery → amount-aware selection → manual buy/sell
→ journal hooks → canonical receipt → accounting/reconciliation
→ TP/SL fresh route selection and execution
```

Search callers for direct legacy quote/swap methods that bypass the route engine. Keep the executable dev worker stopped during migration if stale code can transact. Add representative fixture tests and source-level/caller-injection tests so a compatibility wrapper cannot silently remain active.

## V2 adapter

Discovery:

```text
factory.getPair(token, quote)
pair.token0/token1
pair.getReserves
```

Executable quote:

```text
router.getAmountsOut(amountIn, path)
```

For native/WETH routes, the usual Router02 methods are:

```text
swapExactETHForTokensSupportingFeeOnTransferTokens
swapExactTokensForETHSupportingFeeOnTransferTokens
```

Fee-on-transfer supporting methods do not return a trustworthy amount array. Decode actual output from canonical receipt events. Keep deadline and nonzero slippage-derived min-out.

For native sells, verify who actually calls `WETH.withdraw`. In canonical Router02 flow, the pair transfers WETH to the router and the **router** performs the withdrawal, so `Withdrawal(src, amount)` should be attributed to the configured router rather than assumed to originate from the pair. Encode this as a receipt fixture; do not generalize balance-flow intuition across router versions.

## V3 adapter

Discovery:

```text
factory.getPool(tokenA, tokenB, fee)
```

Probe configured/common fee tiers in parallel. For each exact amount, quote with QuoterV2 rather than choosing permanently by raw pool balance. Execution remains SwapRouter02 `exactInputSingle` or packed-path `exactInput`.

Never revive raw `slot0` as executable quote fallback.

## V4 PoolKey and PoolId

V4 has no pair contract address. A pool is identified by:

```solidity
PoolKey {
  Currency currency0;
  Currency currency1;
  uint24 fee;
  int24 tickSpacing;
  IHooks hooks;
}
```

Recover PoolKey from the PoolManager `Initialize` event:

```solidity
Initialize(
  bytes32 indexed id,
  address indexed currency0,
  address indexed currency1,
  uint24 fee,
  int24 tickSpacing,
  address hooks,
  uint160 sqrtPriceX96,
  int24 tick
)
```

Topic0:

```text
0xdd466e674ea557f56295e2d0218a125ea4b4f0f6f3307b95f85e6110838d6438
```

Always recompute and compare:

```text
PoolId = keccak256(abi.encode(currency0,currency1,fee,tickSpacing,hooks))
```

`address(0)` is native currency, not WETH. A PoolId is a one-way hash; StateView cannot recover its preimage. Use initialization logs or a trusted indexed copy.

Keep PoolId as a full `bytes32`/hash throughout the model. Never truncate it into a 20-byte address merely to satisfy a legacy route interface; expose a separate `PoolID()` and use a zero pool address if compatibility requires one.

When a token's configured quote is WETH but a safe direct V4 pool uses native `address(0)`, discovery may treat native as the executable counterpart only when the chain explicitly marks the quote as wrapped-native. Do not globally equate native and WETH.

For native-output reconciliation, decode the canonical PoolManager `Swap` event for the exact PoolId and use the negative output-currency delta. This avoids relying on WETH `Withdrawal` events that do not exist for direct native V4 pools.

For RPCs that limit `eth_getLogs` ranges, find an approximate creation block from an indexed timestamp and query a narrow range, or scan deployment-to-head in bounded chunks with caching.

## V4 quote and execution

Quote only through `eth_call`; V4Quoter methods are intentionally not Solidity `view`.

Direct quote:

```text
quoteExactInputSingle(((address,address,uint24,int24,address),bool,uint128,bytes))
selector 0xaa9d21cb
```

Multi-hop quote:

```text
quoteExactInput((address,(address,uint24,int24,address,bytes)[],uint128))
selector 0xca253dc9
```

Universal Router deadline overload:

```text
execute(bytes,bytes[],uint256)
selector 0x3593564c
```

Outer command:

```text
V4_SWAP = 0x10
```

Inner actions:

```text
Direct:    SWAP_EXACT_IN_SINGLE + SETTLE_ALL + TAKE_ALL = 0x060c0f
Multi-hop: SWAP_EXACT_IN        + SETTLE_ALL + TAKE_ALL = 0x070c0f
```

Do not use `V4_SWAP | ALLOW_REVERT` (`0x90`) for ordinary swaps. Enforce uint128 bounds before encoding. Use a short deadline and nonzero amountOutMinimum.

Pin the router ABI per deployment. Newer routers can add fields such as `minHopPriceX36`; encoding the wrong tuple silently produces reverts.

## Hook policy

Unknown hooks fail closed. Do not assume `hookData=0x` works because a pool is visible in an indexer.

Allow a hooked route only after all of the following:

1. Recover and verify its PoolKey/PoolId.
2. Inspect verified hook source and declared permissions.
3. Determine whether hookData is optional and its exact ABI.
4. Check dynamic-fee behavior.
5. Pin chain ID + hook address + runtime bytecode hash.
6. Re-check code hash at startup and before a sensitive rollout.
7. Add executable quote and calldata simulation tests.

Upgradeable hooks remain changeable even when their address is stable. A code-hash mismatch must disable the route until reviewed.

A useful pattern for optional referral hooks is verified source proving:

```solidity
hookData.length == 0 ? address(0) : abi.decode(hookData, (address))
```

Only then may empty hookData represent “no referral.” Never generalize this behavior to other hooks.

Dynamic fee (`fee & 0x800000 != 0`) requires explicit support; otherwise reject it.

## Permit2 and approval

V4 Universal Router ERC-20 input commonly requires two bounded permissions:

```text
token allowance → Permit2
Permit2 allowance/permit → Universal Router
```

Do not substitute unlimited, non-expiring approvals. Bound amount and expiration, support zero-first ERC-20s, and journal approval/swap outcomes distinctly. Native input does not use ERC-20 approval.

Treat approval capability as an explicit execution dependency. An ERC-20 V4 route with no approval backend must fail **before transaction construction/signing/broadcast**; add a test whose send callback fails if reached. Keep both approvals and the swap under the same per-wallet nonce lock. Re-read token and Permit2 allowances, approve the exact intended amount, and give the router a short expiry rather than a permanent grant.

## Optimizer and discovery safety

Candidate discovery should be bounded and chain-aware:

- configured V2 factory and direct quote asset;
- configured V3 factory and allowlisted fee tiers;
- V4 Initialize logs cached by chain/token;
- allowlisted intermediates only for multi-hop (for example WETH, canonical USDC, protocol-specific backing currency);
- maximum hops and maximum candidate count;
- parallel executable quotes with per-call timeout;
- reject unknown hooks, changed bytecode, dynamic fees, zero quote, and ABI mismatch.

External DEX/indexer APIs may seed candidate discovery, but execution must verify every pool and quote on-chain. Never trust labels such as `v4` as sufficient execution metadata.

## Integration with hardened trade state

All adapters must feed the same state machine:

```text
intent → exact units → executable quote → slippage/minOut
→ position claim → signed hash persisted → broadcast
→ canonical receipt → receipt-derived output
→ idempotent accounting → notification/reconciliation
```

Persist enough route identity to reconcile after restart: protocol, router, input/output currencies, pool/pool IDs, fee/tick spacing/hooks, path, and candidate transaction hash. Receipt decoding must use the expected final output token and recipient, not adapter-specific balance deltas.

TP/SL must discover and quote a fresh route for the sellable tracked quantity, then re-check the trigger after claim. Do not persist a route forever as market liquidity can migrate between V2/V3/V4.

## Required tests

- one token with simultaneous V2/V3/V4 pools; best route changes by amount
- V2 fee-on-transfer native buy/sell calldata and receipt output
- V3 fee-tier comparison and Quoter failure
- V4 PoolKey log decode and PoolId recomputation
- zero-hook direct and multi-hop quote vectors
- wrong-chain hook and runtime-code-hash mismatch rejection
- dynamic-fee rejection unless explicitly supported
- old/new Universal Router ABI tuple vectors
- uint128 overflow rejection
- native address(0) versus WETH distinction
- bounded Permit2 approval and expiration
- optimizer gas/no-gas ranking
- restart reconciliation with persisted multi-hop route identity
- manual sell and TP/SL through every supported protocol
- read-only fixture quotes followed by transaction simulation, never a live broadcast without explicit confirmation

For native payable simulations, use a funded public address as the `from` account for `eth_estimateGas`; an unfunded arbitrary address can return `OutOfFunds` before exercising router logic. This is read-only and does not require that address's key. Record quote output, PoolId, quoter gas, estimated execution gas, and simulation error separately.
