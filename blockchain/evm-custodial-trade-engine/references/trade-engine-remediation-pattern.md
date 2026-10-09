# Custodial V3 Trade-Engine Remediation Pattern

## Audit order

1. Trace manual buy and sell from callback to receipt and DB write.
2. Trace TP/SL separately; automation often bypasses UI validation and sells a broader balance.
3. Enumerate every point after broadcast that can still return an error.
4. Search for ignored `AddBuy`, `RealizeSell`, journal-state, and notification errors.
5. Inspect persisted uniqueness assumptions versus actual database indexes.
6. Run race tests; nonce locks do not prove accounting or font/client/helper state is race-safe.

## High-value failure scenarios

### External inventory liquidation

```text
tracked: 100 tokens / cost 10
wallet receives 900 externally
engine values 1,000 against cost 10
TP fires and sells 1,000
```

Correct behavior: value and sell `min(balance, tracked)`. Imported inventory requires an explicit adopt/cost-basis flow.

### Mined but unaccounted

```text
broadcast accepted
receipt succeeds
post-receipt RPC or SQLite write fails
caller returns error / drops hash
position remains stale
```

Correct behavior: prepared hash exists before broadcast; submitted/mined states survive; received amount comes from receipt logs; reconciliation applies accounting idempotently.

### Crash during accounting

```text
journal → accounting
position mutation commits
process crashes before journal → accounted
```

Correct behavior: durable `open_tx`/`close_tx` or ledger proof causes restart to mark accounted without replay. If no proof exists, retry.

### Spot fallback weakens min-out

```text
Quoter reverts
attacker moves slot0
bot derives output from manipulated spot
minOut becomes weak
```

Correct behavior: fail closed. Display-only spot helpers must not silently become execution protection.

### Inventory drift false stop-loss

```text
tracked 100 / cost 100
wallet balance 60
quote 60 compared against full cost 100
false -40% loss
```

Correct behavior: compare sellable 60 against proportional cost 60.

## Durable journal fields

At minimum:

```text
user_id, wallet, chain, token, side
amount_in, min_out
operation_id / tx_hash(es)
state, received, failure
created_at, updated_at
```

Use unique `(chain, tx_hash)` or operation/hash child rows. Model RBF explicitly; never replace the journal's only hash without retaining prior candidates.

## Receipt event decoding

- ERC-20 output: sum valid `Transfer(address,address,uint256)` logs emitted by the expected token with recipient topic equal to the wallet.
- Native output via WETH unwrap: sum `Withdrawal(address,uint256)` emitted by the configured WETH contract for the router source.
- Validate topic count, emitter address, and 32-byte data.
- A missing expected output event after status-1 receipt is `mined_pending_reconciliation`, not “trade failed before broadcast.”

## Safe rollout sequence

1. Stop only the isolated dev worker if old TP/SL code can transact.
2. Add red tests for inventory scope and claims.
3. Add journal schema and migrate an isolated DB copy.
4. Wire manual trade journaling.
5. Wire TP/SL journaling and claim semantics.
6. Add startup reconciliation.
7. Remove executable spot fallback and unsafe slippage.
8. Replace unlimited approvals.
9. Correct cumulative/wallet-scoped accounting.
10. Run full race/vet/build and static searches for discarded accounting errors.
11. Start dev bot and verify actual schema/indexes.
12. Live chain validation only with explicit approval, verified parameters, bounded amount, and explorer confirmation.
