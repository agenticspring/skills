# Critical side-effect safety test matrix

## Ownership state machine

Test these transitions independently:

| Given | When | Then |
|---|---|---|
| one open record | two workers claim concurrently | exactly one gets ownership |
| executing record, adapter fails before broadcast | release | record becomes open |
| executing record, broadcast may have happened | later step fails | record is not reopened automatically |
| executing record | accounting consumes result | tracked cost basis and proceeds are preserved |

An in-process mutex is insufficient: it does not coordinate multiple processes and does not survive restart. Use a conditional persisted update and assert affected-row count.

## Inventory bounds

Use the exact same effective amount through every stage:

`effective = min(on_chain_balance, tracked_tokens)`

Test:

1. on-chain balance below tracked amount;
2. tracked amount below on-chain balance;
3. either amount is zero;
4. malformed/missing tracked amount if legacy data permits it.

Zero effective inventory must enter `inventory_missing` or an equivalent quarantine state. Do not close the record with zero proceeds because that fabricates a realized loss.

## Routing failures

Persisted unknown chain/network/venue identifiers must:

- make no RPC or submission call;
- enter quarantine;
- log the record ID and unknown identifier;
- never resolve through a default venue.

Defaults may be valid at input-creation boundaries, but not while interpreting already-persisted execution records.

## Notification ordering

Use narrow seams to prove this order:

1. submit succeeds;
2. accounting is attempted;
3. only successful accounting permits success notification.

If accounting fails, assert notification count is zero and that diagnostic output includes the external transaction identifier.

## Manual-path interaction

Search for manual sell/execute handlers. If they do not claim the same persisted record, document the remaining race explicitly. Avoid broad UI edits when outside scope, but do not imply full race prevention until all execution paths share ownership semantics.

## Verification fallback

When no canonical project command is detectable:

1. Create an OS-safe temporary script using a `tempfile`-generated path with a `hermes-verify-` prefix.
2. Run focused tests with race detection and formatting/static checks for changed files.
3. Delete the script afterward.
4. Report the result as **ad-hoc targeted verification**, not “full suite green.”

Do not let unrelated pre-existing tests prevent a focused package/run-pattern check, but report that limitation clearly.
