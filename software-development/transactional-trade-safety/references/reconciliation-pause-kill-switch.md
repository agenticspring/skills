# Reconciliation, Pause, and Kill-Switch Reference

Use this reference for restart/incident work in EVM transaction systems.

## Decision matrix

| Situation | State | Retry | Notification |
|---|---|---|---|
| Crash before signing | pre-broadcast | allowed after fresh preflight | suppress |
| Signed but no persisted TxHash | quarantined | reconcile-only; never re-sign blindly | incident |
| Persisted TxHash / response lost | unknown | reconcile-only | incident |
| One RPC accepts, another says already-known | unknown | reconcile-only; compare/reconcile receipt | incident |
| Receipt reverted | terminal reverted | none | terminal |
| Transaction replaced | terminal replaced | none | terminal |
| Receipt/log removed by reorg | unknown | observe/reconcile only | incident |
| Indexer missing/lagging | unknown | observe-only; do not infer cancellation | incident or suppress |
| DB unavailable at trigger | blocked | retry only after durable control is restored; no claim/broadcast | incident |
| Kill switch while armed | blocked/disarmed | none until explicit clear and re-arm policy | incident |

## Durable control schema

Keep append-only reconciliation checkpoints with:

- chain and optional intent/wallet IDs;
- nonce and persisted TxHash when known;
- observed state and decision (`reconcile_only`, `observe_only`, `terminal`, `quarantine`);
- deterministic evidence hash;
- immutable creation time.

Keep incident/control audit rows separately. Store actor, reason, monotonic revision, and status (`running`, `paused`, `killed`). Restrict update/delete privileges; control identity and revision must not be operator-editable through generic CRUD.

## Pause/kill ordering

```text
load durable control
→ reject if paused/killed
→ load immutable plan
→ verify freshness/trigger
→ atomically claim journal
→ allocate nonce/sign
→ persist-before-broadcast
→ broadcast
```

The control check must occur before journal claim, signer invocation, nonce allocation, and RPC calls. A pause can be resumed explicitly. A kill switch must ignore ordinary resume and require a dedicated clear operation. Clearing the switch does not automatically re-arm stale plans.

## Chaos test shape

For each fault, assert final state, retry decision, notification behavior, nonce-lane effect, and signer/broadcaster call count. Minimum probes:

1. persisted TxHash causes zero signer/broadcaster calls;
2. signed-without-hash is quarantined;
3. chain/persisted nonce disagreement does not overwrite either value;
4. indexer missing is not `cancelled`;
5. reorg-removed evidence is not `confirmed`;
6. ownership missing is `unknown`, mismatch is `invalidated`;
7. pause blocks before journal claim and endpoint invocation;
8. kill switch remains blocked after ordinary resume;
9. every possible-send ambiguity is reconciliation-only;
10. success is not notified before exact receipt/log/post-state/accounting proof.

## Reporting vocabulary

- `reconcile_only`: inspect authoritative chain/durable evidence; no new signing or broadcast.
- `observe_only`: wait/re-read an external source; do not mutate financial state.
- `quarantine`: stop automated progression because state conflicts or proof is incomplete.
- `terminal`: no retry; report the exact confirmed failure/replacement/revert.
- `confirmed`: only after final receipt plus exact domain proof, never from an indexer label or TxHash alone.
