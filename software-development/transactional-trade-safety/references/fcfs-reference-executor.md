# TypeScript FCFS Reference Executor

Use this reference for trigger-driven EVM mint/claim execution before considering a Go fast path.

## Required model

```text
immutable armed plan
→ typed trigger evidence
→ atomic `(plan_hash, trigger_key)` claim
→ per-chain/per-wallet serialized lane
→ identical payload to approved RPCs
→ consistent TxHash proof
→ durable broadcast/reconciliation state
```

## Trigger types

- timestamp: `now >= atSeconds` and still before plan expiry;
- block: current block reaches the armed threshold;
- log: exact contract address plus ordered topic prefix;
- state: named state key equals expected value.

## Failure semantics

| Condition | Result | Retry |
|---|---|---|
| executor disabled | `disabled` | no |
| trigger not reached | `trigger_not_satisfied` | wait for fresh evidence |
| duplicate claim | `duplicate` | no |
| all RPCs fail/timeout | `unknown_needs_reconciliation` | no auto-retry |
| RPCs return different hashes | `unknown_needs_reconciliation` | no auto-retry |
| consistent hash | `broadcast` | reconcile receipt/post-state |

## Benchmark rule

Benchmark only pure trigger evaluation in 1,000 iterations and emit p50/p95/p99. Do not present that number as network, signing, or broadcast latency. The benchmark is a CPU baseline for comparing TypeScript with a potential Go implementation.

## Minimum tests

1. hard-disabled by default;
2. immutable plan/trigger snapshot;
3. timestamp/block/log/state trigger behavior;
4. one concurrent claimant;
5. same-wallet serialization;
6. different-wallet overlap;
7. identical raw payload fan-out;
8. mismatched RPC hash quarantine;
9. possible-send timeout quarantine;
10. no retry after ambiguous broadcast.
