# SQLite journal accounting concurrency

Use this note when a single-process EVM trade engine stores its journal and positions in SQLite/WAL with separate writer and pooled reader handles.

## Confirmed replay race

A journal state machine alone does not make an out-of-transaction accounting callback exactly-once:

```text
reconciler A: mined -> accounting -> enters callback
reconciler B: reads accounting before A writes durable proof
reconciler B: sees no proof, resets accounting -> mined
reconciler B: enters callback too
```

This can duplicate DCA aggregation or sell realization and corrupt inventory, cost basis, and PnL.

## Minimal single-process mitigation

Serialize the complete `read journal -> claim -> callback -> accounted marker` region with a store-level mutex. Locking only the state UPDATE is insufficient because the callback and durable proof must remain inside the critical section.

This is intentionally a **single-process** guarantee. For multiple bot processes, use a database-native claim plus accounting mutation/proof in one transaction, or otherwise design a lease/fencing protocol.

## Durable proof requirements

Do not infer application from mutable position rows alone. DCA and partial sells can aggregate, rewrite, or delete `open_tx`/`close_tx`. Record an immutable `(chain, tx_hash)` accounting proof in the same SQLite transaction as the position mutation.

When checking that proof immediately after a write, query through the serialized writer connection. A pooled WAL reader may retain an older snapshot and report the proof absent, causing replay. The safe sequence is:

```text
position mutation + immutable proof COMMIT
-> writer-connection proof lookup
-> journal accounted
```

## Deterministic regression test

Use two goroutines and channels, not sleeps, to overlap callbacks:

1. First callback increments an atomic counter, signals entry, and blocks on a channel.
2. Start the second `AccountTrade` only after the first entered.
3. Detect whether the second callback enters before releasing the first.
4. Release, join both calls, and require callback count exactly one.
5. Run with `go test -race -count=1`.

Also retain a crash-window test:

```text
journal = accounting
position mutation + immutable proof already committed
AccountTrade invoked again
=> callback must not run; journal becomes accounted
```

If this test flakes between replay/no-replay, inspect whether proof lookup uses a pooled WAL reader rather than the writer handle.

## Verification reporting

When an orchestration environment does not recognize the repository's canonical gate, create an OS-safe temporary script with a `hermes-verify-` prefix, run the focused race tests, and remove it with an exit trap. Report this explicitly as **ad-hoc focused verification**, not full-suite green.
