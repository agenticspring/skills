---
name: evm-custodial-trade-engine
description: Design, audit, harden, and verify custodial EVM swap engines with durable transaction state, safe quoting, inventory-scoped automation, and idempotent accounting.
version: 1.0.0
author: spring
license: Private
platforms: [linux]
metadata:
  hermes:
    tags: [evm, trading, uniswap-v3, transaction-safety, accounting, reconciliation]
---

# EVM Custodial Trade Engine

Use this skill for fund-sensitive EVM buy/sell systems, Telegram trading bots, automated TP/SL engines, swap execution services, and position-accounting audits.

## Operating rule

Treat chain execution and database accounting as one recoverable state machine, even though they cannot be one atomic transaction. Never infer safety from a green unit suite alone. Audit the complete path:

```text
user intent → amount parsing → quote → minOut → claim → sign
→ persist prepared hash → broadcast → receipt → confirmation
→ decode outcome → accounting → notification → restart reconciliation
```

No live transaction during an audit. For implementation, test each invariant red→green before wiring callers.

## Fund-safety invariants

1. **Automation owns only tracked inventory.** TP/SL sell amount and trigger valuation must use `min(on-chain balance, tracked quantity)`. External transfers, airdrops, and purchases from other apps are not implicitly owned by the bot.
2. **Inventory drift changes cost basis proportionally.** If sellable quantity is below tracked quantity, compare its quote against proportional tracked cost—not the whole position cost.
3. **Zero balance is not automatically a realized loss.** Quarantine as `inventory_missing`; require reconciliation or explicit user disposition.
4. **Unknown chain data fails closed.** Never silently substitute a default chain for persisted positions.
5. **Claim before irreversible work.** Atomically transition `open → executing`; release only if failure is definitely pre-broadcast. Manual and background sells must share the same claim protocol.
6. **Re-check automated triggers after claiming.** Price may have crossed back while waiting. Prefer a final quote close to transaction construction.

## Durable transaction lifecycle

Persist a transaction journal with states such as:

```text
prepared → submitted → unresolved → mined → accounting → accounted
                                  ↘ failed
```

Requirements:

- Persist signed TxHash **before** broadcast. Persistence failure means no broadcast.
- After RPC acceptance, mark submitted.
- A timeout after broadcast is `unresolved`, never an ordinary failure.
- Reconcile unresolved rows immediately at startup and periodically.
- Distinguish mined from confirmed/final; re-fetch the receipt and verify canonical block hash after configured depth.
- Store one operation identity and all candidate hashes if using RBF. If the journal cannot represent replacements safely, disable RBF for journaled swaps rather than losing identity.
- Never drop database errors after a successful chain transaction or send a definitive success notification before accounting succeeds.

## Crash-safe idempotent accounting

Use unique operation/TxHash constraints. Position writes must preserve proof (`open_tx` / `close_tx` or a dedicated ledger row).

Crash cases:

```text
crash before position write
→ journal says accounting, no matching TxHash proof
→ retry accounting

crash after position write but before journal accounted
→ matching durable TxHash proof exists
→ mark accounted without replay
```

For true multi-process safety, prefer applying position mutation and accounting marker in one database transaction. If callbacks span separate transactions, explicitly test both crash windows and concurrent reconcilers. In a single-process SQLite/WAL engine, serialize the full claim→callback→marker region; a journal CAS alone can replay while the first callback is still running. Store an immutable TxHash accounting proof in the same transaction as the position mutation, and perform immediate proof lookup through the writer connection rather than a pooled WAL reader that may retain an older snapshot. See `references/sqlite-accounting-concurrency.md` for the deterministic race reproduction and crash-recovery test.

## Quotes and slippage

- Executable min-out must come from an amount-aware quoter/simulation.
- Do not use raw V3 `slot0` spot price as an automatic executable fallback. It ignores amount impact/tick traversal and is manipulation-sensitive.
- Quoter failure should fail closed unless a manipulation-resistant fallback is formally designed (TWAP, liquidity threshold, deviation guard, impact model).
- Validate slippage at both UI and execution boundaries: finite, positive, and capped by policy. Never turn 100% slippage into `minOut=1`.
- Parse user token/native amounts from decimal strings directly into integer subunits. Avoid `string → float64 → string → units` for 18-decimal assets.

## Receipt-derived results

After a successful receipt, do not make success depend on another balance RPC.

Prefer:

- ERC-20 `Transfer` logs to the recipient for token output.
- WETH `Withdrawal` logs for native unwrap output.
- Some WETH implementations burn during unwrap without emitting `Withdrawal`; accept `Transfer(router, address(0), amount)` **only** when emitted by the configured WETH token and the sender is the configured trusted router. Treat it as a chain/router-specific receipt decoder with fixtures from a real receipt; never accept arbitrary token burns or ordinary router transfers.
- Canonical receipt logs or router return data over wallet-wide `after-before` deltas.

Balance deltas can include unrelated transfers and post-receipt RPC failures can otherwise turn a mined trade into a false application error.

### PnL publication gate

A PnL card is a financial statement, not a best-effort UI decoration. Before rendering, query the durable journal for the same user/chain/token. If any row is `prepared`, `submitted`, `unresolved`, `mined`, or `accounting`, block the card and state that receipt/accounting is pending. After a sell UI action, offer the card only when every submitted sell has become fully accounted; otherwise show a locked/pending message. This prevents a misleading `+0.0%` card when a mined trade has not yet been reconciled.

When a decoder repair lets a historical unresolved receipt reconcile, verify: journal is `accounted`, received amount is receipt-derived, position is closed/updated, and clear the obsolete decoder-failure text only after successful accounting.

## Allowances and RPCs

- Prefer exact or tightly bounded approvals, not `uint256 max`.
- Support zero-first tokens: insufficient nonzero allowance → approve zero → approve exact.
- Validate router addresses/code at startup when practical.
- Send-client selection must return `(client, error)`, health-check private RPCs, and never pass nil into signing/broadcast paths.
- Idempotent reads may retry across RPCs. Broadcast policy must handle `already known` and pending-pool disagreement carefully.

## Position accounting

- Store all amounts as arbitrary-precision integer subunits.
- Reject malformed, zero, or negative persisted quantities; never coerce invalid text to zero.
- DCA aggregation must be transactional and scoped by user/wallet/chain/token.
- Partial sells allocate cost proportionally and preserve rounding residue in the remainder.
- If actual sold quantity exceeds tracked inventory, either reject accounting or attribute proceeds proportionally to tracked quantity.
- Token PnL should aggregate lifecycle realized proceeds plus current open value—not only the latest closed slice.
- Wallet-filtered holdings must use wallet-filtered cost basis.

## Automation and observability

Log structured phases with position/user/wallet/chain/token, quote block, min-out, TxHash, state, attempt, duration, and error. Notify users when automation is quarantined or a submitted trade is unresolved. Do not advertise an auto-snipe feature as active when discovery/liquidity/dedupe are scaffolds.

Use bounded worker concurrency, per-position timeouts, panic isolation, and metadata single-flight. Persist claims and transaction state; process-local nonce locks alone do not protect restarts or multiple processes.

## Telegram long-poll runtime safety

A running process is not proof that a Telegram bot is consuming updates.

- Telegram allows one active `getUpdates` long poll per bot token. A manual diagnostic `getUpdates` request can terminate the real poll and create the same 409 conflict being investigated. Prefer `getMe`, `getWebhookInfo`, logs, process/socket inspection, and a harmless `sendMessage` health check. If direct polling is unavoidable, stop the bot first.
- Compare bot-token fingerprints rather than printing secrets when checking whether dev and production use the same Telegram identity.
- Optional startup calls such as `SetMyCommands` must run best-effort with a short timeout and must not delay polling. Otherwise the process can look healthy while `/start` remains queued.
- Clean restart sequence: stop the old instance, allow the previous long-poll request to expire, start exactly one replacement, then monitor for 409 conflicts over at least one poll cycle.
- Interpret `pending_update_count` cautiously: it is supporting evidence, not proof by itself that polling is dead. Correlate it with post-start logs and an established Telegram TLS socket.
- When validating recovery, send a non-sensitive health message to the affected chat and ask the user to issue a fresh command. Avoid repeatedly probing `getUpdates`, which perturbs the system under test.

## Token metadata, pool metrics, and card safety

Treat token identity and pool metrics as required typed data, not best-effort decoration:

- distinguish RPC errors from empty/reverting ERC-20 views;
- retry idempotent metadata reads in a bounded way and across independently health-checked RPC endpoints;
- require valid `name`, `symbol`, `decimals`, and `totalSupply` before caching;
- never cache placeholders such as `?`, default decimals produced by a failed call, or partial metadata;
- compare simultaneous V2/V3/V4 candidates instead of permanently preferring a protocol merely because its pool exists;
- for display-pool selection, use reliable on-chain quote-side liquidity or executable amount-aware quotes; a tiny V3 pool must not hide a dominant V2 pool;
- calculate metrics with the selected protocol's model: V2 reserves/token ordering, V3 `slot0` plus required pool balances, V4 StateView/verified route semantics;
- required metric-call failures must return unavailable/error, never silently become numeric zero;
- derive the displayed DEX/version from the selected route rather than a hardcoded label;
- render missing market cap/liquidity as `Tidak tersedia` or equivalent, not `$0`;
- withhold buy controls when identity or required metrics are incomplete;
- display zero priority-fee configuration as `Auto` when zero means provider estimation, not literal zero gas.

After fixing partial-data caching, restart the worker or explicitly invalidate bad cache entries before UI verification. Token-card reads are UI-adjacent but must not inherit short-lived Telegram callback/edit cancellation: create **one bounded card-read context** with `context.WithTimeout(context.WithoutCancel(parent), budget)` and pass it to every read-only dependency of that render—not only chain detection and pool metrics, but also token/quote/native balances, holdings quotes, USD conversion, gas tiers, and estimated costs. A partially detached card can otherwise render valid metrics with zero balances and missing Sell controls.

Metrics may use child per-attempt timeouts derived from that same card context. Give each retry its own bounded deadline (for example `4s + 4s` inside a `12s` card budget); do not claim a retry exists if both attempts share one deadline that a hung first call can exhaust. Do not detach cancellation for signing, approvals, swaps, or any write. A cancelled callback must never be rendered as “token/pool does not exist”; log the real metrics error and return a retryable verification message. Test a first-call failure followed by recovery, callback cancellation isolation across the **whole card**, incomplete-data non-caching, cross-version pool selection, protocol-aware metrics, and fail-closed card controls.

See `references/token-card-callback-resilience.md` for the Robinhood V3 MARIAN reproduction and rollout checks.

See `references/token-card-data-integrity.md` for a concrete reproduction and verification recipe.

## Production audit reference

See `references/custodial-bot-production-audit.md` for durable patterns covering immutable accounting proofs, burn-time automation snapshots, private-chat boundaries, SQLite sidecar permissions, isolated single-instance launchers, and gas-mode propagation.

## Verification checklist

- DCA hash proof survives aggregate `open_tx` overwrite
- partial-sell proof survives position-row reconstruction
- historical completed bridge cannot gain newly configured automation targets
- overlapping reconcilers run accounting once
- duplicate launcher is rejected before polling/worker startup
- private-key generation/reveal uses durable auto-delete in private chat only
- tracked-vs-external inventory TP/SL test
- balance-below-tracked proportional cost test
- manual sell vs TP/SL atomic claim test
- timeout then later-mined reconciliation test
- crash before/after accounting marker tests
- duplicate TxHash replay test
- receipt status 0 and reorg/canonicality test
- invalid/NaN/100% slippage tests
- Quoter failure fails closed
- exact and zero-first approval tests
- receipt event decoding tests
- malformed accounting input tests
- cumulative multi-partial-sale PnL test
- wallet-filtered cost test
- schema migration against an isolated copy of a real database
- full race suite, vet, build

## Multi-version Uniswap routing

When supporting Uniswap V2, V3, and V4, never classify a token permanently by protocol version. One token may have simultaneous pools across generations and quote assets. Discover and executable-quote candidates for each exact input amount, then select the best safe route.

### Integration acceptance rule

Adapter tests and a green build do **not** prove that the bot supports a protocol. Before reporting support, trace and verify the active production-shaped path:

```text
token discovery → executable candidate quote → selected adapter
→ manual buy/sell → journal hooks → receipt decode → accounting
→ TP/SL fresh discovery and execution → restart reconciliation
```

Search active callers for legacy direct methods such as V3-only min-out and swap helpers. A protocol is not integrated while manual trade, automation, or reconciliation bypasses the route abstraction. Require fixture acceptance tests proving representative V2/V3/V4 selection and caller-level tests showing manual trade and TP/SL use the multi-route engine.

Describe capability precisely:

```text
adapter-only → read-only quote → calldata-ready → active execution
```

Never collapse these states into “supported.” During migration, keep the executable dev worker stopped if an old path can still transact. Do not restart merely because package tests compile.

### Cross-adapter receipt review

Receipt assumptions must be reviewed against the actual caller for each router generation. Example: Router02 receives WETH from the pair and calls `WETH.withdraw` itself, so the expected `Withdrawal(src, amount)` source is the **router**, not the pair. Validate emitter, indexed source, recipient semantics, and amount with protocol-specific receipt fixtures before wiring accounting.

Requirements:

- implement V2/V3/V4 behind a protocol-neutral route interface;
- use canonical machine-readable deployment mappings and pin deployment ABI/commit;
- recover V4 PoolKeys from PoolManager `Initialize` logs and re-hash them to PoolId;
- preserve V4 PoolId as the full `bytes32`; never truncate it to a 20-byte address to satisfy a legacy route interface;
- keep native `address(0)` distinct from WETH;
- fail closed on unknown hooks, changed hook bytecode, dynamic fees, or router ABI mismatch;
- support a hook only after verified-source analysis plus chain/address/runtime-code-hash allowlisting;
- require an explicit approval backend before any ERC-20 V4 route can construct or broadcast a swap; missing approval support must fail before `SendTx`;
- bound both Universal Router approval layers: exact ERC-20 allowance to Permit2 and amount-limited, expiring Permit2 allowance to the router;
- decode native V4 proceeds from the canonical PoolManager `Swap` event using the matching full PoolId and signed currency delta—not wallet balance changes;
- persist sufficient route identity for restart reconciliation, or use a deterministic verified decoder keyed by chain/token/full PoolId; discover a fresh route for every new trade and TP/SL evaluation;
- route every adapter through the same journal, canonical receipt, receipt-derived output, and idempotent accounting pipeline;
- prove fixture routes with read-only executable quotes and `eth_estimateGas` from a currently funded address. Treat `OutOfFunds` as a simulation-caller problem, not proof that calldata is invalid.

See `references/uniswap-multiversion-routing.md` for deployment discovery, V2/V3/V4 encoding, hook policy, Permit2, optimizer rules, and required tests.

## References

- See `references/trade-engine-remediation-pattern.md` for a concrete V3 custodial-bot audit/remediation checklist and failure scenarios.
- See `references/native-unwrap-pnl-gate.md` for WETH burn-style unwrap decoding, historical receipt reconciliation, and preventing premature PnL cards.
- See `references/rpc-receipt-pnl-repair.md` for real-chain receipt repair, Cloudflare/RPC failover probes, and sanitized user errors.
- See `references/uniswap-multiversion-routing.md` for class-level V2/V3/V4 adapter architecture and safety patterns.
- See `references/telegram-long-poll-runtime.md` for safe diagnosis of alive-but-unresponsive Telegram workers, 409 conflicts, and clean restart verification.
