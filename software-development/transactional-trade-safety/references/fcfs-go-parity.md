# Go/TypeScript FCFS parity reference

Use this checklist when introducing a Go fast path beside the TypeScript FCFS reference executor.

## Shared fixture

Keep one sanitized JSON fixture containing:

- immutable armed plan: plan hash, wallet ID/address, chain ID, campaign/stage versions, expected/observed code hash, expiry, trigger, and an exact non-secret payload sentinel;
- evidence: timestamp/block/log/state plus freshness and kill-switch fields where relevant;
- expected status and hash sentinel.

Do not use 64-hex strings in fixture values: repository secret scanners commonly classify them as keys/signatures. Use labels such as `tx-fixture-hash-v1`.

Both implementations must consume the same fixture and agree on status, payload, and hash semantics. The fixture is an equivalence test, not proof of a real broadcast.

## Go implementation gates

1. Load only an armed immutable plan through an injected store.
2. Reject disabled mode, kill switch, expired plan, chain mismatch, code-hash mismatch, and stage-version mismatch.
3. Evaluate timestamp, block, exact log address/topics, and named state triggers.
4. Claim `(plan_hash, trigger_key)` atomically before calling an endpoint.
5. Serialize by `(chain_id, wallet_address)`; allow different wallet lanes to overlap.
6. Send the identical payload to each approved endpoint.
7. Require one consistent TxHash. All failures, ambiguous timeouts, and mismatched hashes become `unknown_needs_reconciliation`; never auto-retry.
8. Keep the CLI hard-disabled by default and smoke the compiled binary for sanitized `mode=disabled` output.

## Verification commands

```bash
go test ./cmd/fcfs-executor/...
go test -race ./cmd/fcfs-executor/internal/fcfs
go vet ./...
go test ./...
go test ./cmd/fcfs-executor/internal/fcfs -bench='BenchmarkTrigger' -benchmem -count=1
go build -o bin/spring-nft-executor ./cmd/fcfs-executor
./bin/spring-nft-executor
```

Record benchmark numbers as CPU trigger-evaluation baselines only. They are not network, signing, or end-to-end FCFS latency.

## Honest quality reporting

If the aggregate project quality wrapper is blocked before execution by a tool timeout or approval guard, do not call it green. Run the component gates separately—TypeScript test/typecheck/build, secret scan, Go test/vet/race/build—and report the blocked wrapper plus the verified component outputs.
