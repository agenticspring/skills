---
name: transactional-trade-safety
description: Design and test fail-closed safety for automated swaps, orders, payments, and other irreversible external actions.
version: 1.0.0
author: Hermes
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [trading, payments, state-machine, concurrency, tdd, safety]
---

# Transactional Trade Safety

Use this skill when changing automated TP/SL, order execution, swaps, bridge submissions, payment dispatch, or any workflow where a duplicate or incorrectly accounted external action is dangerous.

## Core workflow

1. Identify the persisted domain record that owns execution.
2. Write one failing behavioral test per safety invariant before production changes.
3. Atomically claim ownership before invoking the irreversible adapter.
4. Release only when failure is proven to be pre-broadcast.
5. Reconcile domain accounting before sending success notifications.
6. Run focused race-enabled tests, then the canonical project gate if one exists.

## Required invariants

- Persisted execution data must fail closed. Unknown chain/network/venue/provider identifiers are quarantined and logged, never replaced with a default.
- For tracked asset sales, quote, slippage calculation, submission, and accounting use one bounded amount: `min(observed external balance, tracked inventory)`.
- Zero external balance means missing inventory, not a realized sale or realized loss. Record an explicit missing/quarantine state without fabricated proceeds.
- Claim transition is atomic (for example `open -> executing`). Exactly one concurrent claimant succeeds.
- Release (`executing -> open`) is allowed only before broadcast. Once broadcast may have happened, preserve state for reconciliation rather than risking duplicate execution.
- Accounting must understand the claimed state; otherwise a successful external action can be recorded with zero cost basis.
- Success notification happens only after accounting succeeds. On post-broadcast accounting failure, retain the transaction identifier in logs/state and suppress success messaging.
- A bridge-triggered destination action is eligible only after a composite proof: authoritative forwarding identifier, successful confirmed destination receipt, and a destination-recipient balance increase measured against a durable pre-action baseline. Route readiness, indexing, attestation readiness, pending confirmation labels, and a forwarding hash alone are never completion proof.
- Persist the recipient and its pre-bridge balance with the bridge record before submission. A missing baseline (including legacy records) fails closed for automated destination actions; do not infer it from a later balance.
- Bind an automated destination action to the recorded recipient wallet and explicit persisted targets only. Never fan out through active/default wallets or scan/watch history.
- After a bridge becomes completed, reload completed records on worker startup/ticks so an interruption between completion and dispatch is recoverable; durable per-target claims must suppress every repeat broadcast after submission.

## Batch execution and reporting

For batches of irreversible actions, separate preparation from broadcast. Preparation may run in parallel (discovery, validation, puzzle solving, and status checks); execution through one funded wallet must serialize nonce-bearing commit/reveal flows unless the protocol and nonce allocation have been explicitly tested. Before reporting progress, start with a fresh inspection of the current repository/files, runtime state, wallet registry, and approved credential locations; do not trust prior-session paths or assumptions. Verify real outputs: wallet balance, selected targets, prepared-input validity, and broadcast receipts/transaction hashes. Never say a batch has started or is underway when only a plan, delegation, scan, account form, or key-generation step has run. External success requires a verifiable receipt, account identifier, API-key presence check, or other authoritative result; otherwise report the exact blocker plainly.

### EVM claim preflight and race pitfalls

Treat ownership probes as tri-state: only the protocol-specific revert meaning "unclaimed" may be classified as available. `UNSUPPORTED_OPERATION`, missing revert data, rate limits, timeouts, and provider errors are unknown and must fail closed. Always instantiate read contracts with an explicit provider and verify the runner before scanning. A stale ownership scan is not a reservation; re-check immediately before broadcast.

Pin the exact answer-verification formula to the reference miner/contract. If a local corpus fingerprint is used to remove a redundant RPC call, verify the fingerprint against the on-chain fingerprint in the same run. If a candidate loses the race, continue with other already-verified candidates instead of terminating the batch.

Bound every batch runner. Avoid infinite retry loops and kill/restart only the specific process or screen session owned by the task. Emit progress before expensive scans and after each bounded wave. Keep solver preparation parallel, but serialize nonce-bearing commit/reveal broadcasts and reconcile uncertain sends before retrying.

For delegated preparation, pin each worker to the intended project directory and validate its first filesystem read before trusting results. A worker scanning a broad home directory or a different protocol is not evidence.

### EVM puzzle-claim race handling

For commit/reveal NFT claims, treat the ownership scan as a shortlist only: it is never a reservation. After a candidate's final answer is deterministically verified, minimize the pre-commit read path and serialize the funded wallet's commit. Do not perform a second long solver pass or redundant `ownerOf`/answer-hash calls between verification and commit unless the protocol requires it; each extra RPC round-trip widens the race window. Persist the complete answer, salt, commitment, candidate ID, and state before broadcast so an uncertain send can be reconciled without recomputing or changing the salt.

Use the contract's live `commitMinBlocks()` and `commitMaxBlocks()` values rather than hardcoding a delay. After commit confirmation, wait for the minimum age, then run `mint.staticCall(tokenId, answerBytes, salt)` against the same route used for broadcast. Broadcast reveal only after simulation passes, and verify the receipt plus `ownerOf` before reporting success. A reveal transaction exposes the answer and salt in calldata; this is expected, and the security boundary is that competitors still need their own prior commit.

For contracts whose `ownerOf` signals availability by revert, classify only the known protocol selector as `unclaimed`; rate limits, missing revert data, transport failures, and unsupported runners remain `unknown` and fail closed. Keep protocol-specific selectors in a reference file, not scattered through batch runners. See `references/evm-puzzle-claim.md` for the state machine, ABI checks, and race-focused probes.

When solving finite puzzle spaces, brute-force only after parsing the exact puzzle shape and filtering constraints. Support variable word counts and rule-step counts; never route a 5-word construct into a 4-word helper, and never treat a prefix hit as a verified answer until the next sealed trial or final contract hash validates it. Remote workers must receive the complete corpus, wordlist, dependency tree, and a configurable root path; verify the first filesystem read and runtime path before trusting results. A faster worker with an incomplete corpus is not evidence.

When a user requests N wallets, treat that as an explicit artifact requirement: create and index exactly N wallets, verify the count on disk and each address, then separately verify funding coverage. A funded source wallet does not fund newly-created wallets automatically. Do not report the wallet batch as ready until target wallets have balance, or explicitly report them as unfunded. Do not create multiple wallets when one wallet is sufficient unless the user specifically wants ownership distributed across addresses; explain the extra funding and nonce costs.

For delegated preparation, pin each worker to the intended project directory and validate its first filesystem read before trusting results. A worker scanning a broad home directory or a different protocol is not evidence. Review outputs for scope, side effects, and concrete artifacts before reporting progress.

Use strict status vocabulary: `prepared` means local inputs validated; `funded` means exact execution wallets have balance; `broadcast` means a transaction hash exists; `confirmed` means the receipt succeeded and target state was re-read. Never use “minting,” “underway,” or “started” for preparation-only work. When the user asks to obtain NFTs or maximize claims, preparation is not the deliverable: continue through final-hash verification, commit broadcast, reveal simulation, reveal broadcast, and owner verification, or report a concrete verified blocker. Keep a bounded candidate queue ready while one wallet's commit/reveal remains serialized.

## Scope discipline

Prefer the smallest domain-specific state transition that establishes ownership. Do not introduce a generic transaction journal unless recovery/reconciliation requirements actually demand one. Keep unrelated UI layers unchanged, but inspect and document any manual execution path that bypasses the same claim protocol.

### Protocol-neutral route refactors

When extracting discovery, quoting, optimization, or swap execution behind protocol-neutral interfaces:

- Pin the current production route as a compatibility adapter first; route existing public buy/sell and quote entry points through it without changing their signatures.
- Carry transaction lifecycle hooks as part of the execution request/options boundary. Add a compile-time or behavioral test proving prepared/submitted/mined hooks survive adapter selection.
- Keep native wrap/unwrap, approval, dry-run, receipt accounting, deadline, and nonce-lock behavior in the existing production adapter. A route abstraction must not silently bypass these hardened branches.
- Model candidate comparison separately from execution. A minimal optimizer may compare `amountOut` and optionally subtract a caller-supplied gas cost expressed in output-token units; do not compare raw gas units directly with token output.
- Protocol identifiers and interfaces may declare future support, but do not add discovery, calldata, or live-transaction internals unless explicitly in scope.
- In a shared workspace, inspect unexpected new files before modifying them: they may be concurrent-agent work. Do not overwrite or claim those changes; verify the combined tree and distinguish ownership in the report.

See `references/protocol-neutral-routing.md` for the compatibility and TDD checklist.

## EVM transaction journaling and restart reconciliation

For signer-driven EVM writes, derive the TxHash from the exact signed raw transaction and persist the TxHash, plan hash, nonce, and a raw-transaction checksum **before** the first broadcast call. Do not persist raw signed transaction bytes in ordinary database rows or logs. Validate the signed envelope against the confirmed plan—sender, chain ID, target, value, calldata, gas policy, and nonce—before journaling.

If a broadcast call times out, returns a mismatched hash, or may have reached the network, transition to an explicit unknown/reconciliation state. Never auto-sign or auto-broadcast again. On restart, any intent with a persisted TxHash is reconciliation-only; inject signer/broadcaster dependencies if required by the worker interface, but assert their call counts remain zero.

For NFT transfers, confirmation requires all of: exact transaction input/from/to, successful final receipt with no removed logs, exactly matching `Transfer` or `TransferSingle` evidence, and destination post-state. For ERC-1155, retain the destination's pre-transfer balance and prove the quantity delta; `balance > 0` is insufficient. A successful receipt with incomplete transaction/log/post-state proof remains unknown, not confirmed.

See `references/evm-nft-transfer-safety.md` for the preparation, journal, restart, and reconciliation test matrix.

## Reference FCFS executor pattern

For trigger-driven EVM mint/claim execution, keep the reference executor behind a hard-disabled default. Model the armed plan as an immutable snapshot containing plan hash, campaign version, chain ID, wallet identity, trigger, expiry, and exact prepared payload. Never rebuild mutable calldata at trigger time.

Supported trigger evidence should be explicit and typed: timestamp, block number, exact log address/topics, or named state predicate. Evaluate the trigger first, then atomically claim `(plan_hash, trigger_key)` before any irreversible adapter call. A duplicate claim returns `duplicate` and must not retry.

Serialize all nonce-bearing work by `(chain_id, wallet_address)`; permit different wallet lanes to overlap. If broadcasting to multiple approved RPC endpoints, send the identical exact raw payload and require one consistent TxHash. Zero accepted responses, mismatched hashes, or ambiguous timeout states become `UNKNOWN_NEEDS_RECONCILIATION`; never auto-sign or auto-broadcast again.

Benchmark trigger evaluation separately from network/signing latency. A 1,000-iteration p50/p95/p99 report is useful as a local CPU baseline only, not as FCFS end-to-end latency. Preserve fault-injection tests for hard-disable, duplicate claims, same-wallet serialization, different-wallet parallelism, RPC mismatch, and possible-send timeout.

### Cross-language FCFS parity

When adding a Go fast path, do not create a second interpretation of the executor. Define one sanitized JSON fixture containing the immutable armed plan, trigger evidence, exact non-secret payload sentinel, expected status, and expected hash sentinel; run both TypeScript and Go against it. Keep the Go CLI hard-disabled unless explicitly enabled, and require parity for TTL, chain/code/stage freshness, kill switch, trigger evaluation, `(chain,wallet)` lane serialization, atomic claim, identical endpoint fan-out, mismatched-hash quarantine, and ambiguous-send reconciliation. Run `go test -race` on the Go lane/journal tests and a compiled-binary smoke that proves the default mode is disabled. Use non-secret sentinel hashes in fixtures rather than 64-hex strings that look like credentials to repository secret scanners.

Do not claim the aggregate quality wrapper is green if a tool timeout or approval guard prevented it from starting. Run and report the component gates separately—TypeScript test/typecheck/build, secret scan, Go test/vet/race/build—and preserve the blocked wrapper status honestly.

See `references/fcfs-go-parity.md` for the shared-fixture shape, parity matrix, race/benchmark commands, and reporting vocabulary.

## NFT marketplace fulfillment and sweep safety

For OpenSea/Seaport buys, sweeps, and offer acceptance, treat indexer/API data as discovery or transaction-data acquisition, never as final settlement proof. Revalidate the exact persisted order immediately before preparation: order hash, chain, protocol address, seller, NFT contract, token/criteria, quantity, payment currency, consideration, and expiry. Bind OpenSea fulfillment requests to the exact fulfiller wallet, order hash, and protocol address; validate `fulfillment_data.transaction.to/data/value` before simulation. If `identifierOrCriteria == 0`, require an explicit supported criteria-validation boundary and fail closed when it is missing.

Keep sweep preparation all-or-nothing by default. When partial execution is explicitly enabled, record each item as selected or rejected with a reason, enforce the aggregate budget item-by-item, and stop on stale, expired, or invalid orders. Confirmation is composite: successful receipt, matching TxHash, exact transfer event, destination ownership, and expected payment delta. Preparation and Telegram previews must remain `signed=false` and `broadcast=false`; acquisition data such as calldata or signatures is never shown in chat.

See `references/nft-marketplace-fulfillment.md` for the boundary contract and test matrix.

### Production-wiring audit for marketplace actions

When auditing BUY, SWEEP, ACCEPT OFFER, or similar marketplace paths, distinguish exported helpers from a live execution path. Trace actual call sites from the user callback/command to the runtime entrypoint, not merely `index.ts` exports or passing unit tests. Treat these as separate boundaries: discovery/API acquisition → immutable plan/preflight → durable intent and confirmation → worker claim/nonce lane → signer/broadcaster → journal-before-broadcast → receipt, exact transfer, ownership, payment, and accounting reconciliation. Production wiring is absent until every boundary is connected.

Use concrete evidence: a bot callback must create or load a durable intent; a worker must claim it and serialize `(wallet, chain)`; the signer must receive validated target/data/value and wallet policy; the journal must persist the locally derived TxHash before broadcast; and reconciliation must be reachable from the same operation type. Formatter-only commands, plans permanently typed `signed=false`/`broadcast=false`, unused OpenSea fulfillment builders, transfer-only execution jobs, or a deployment entrypoint that runs `doctor` do not constitute marketplace execution. For SWEEP, require per-item identity/status and explicit all-or-nothing or partial policy; for BUY/OFFER, require exact order revalidation and fulfillment-data binding immediately before signing. Record the exact file/function gap for each missing edge and keep the UI preview-only until the full chain is implemented and gated.

## Observation-only alerts and explainable recommendations

For market/mint monitoring, keep alerting and recommendation generation strictly outside signer/executor boundaries. Store the last source observation, a deterministic value fingerprint, and last alert time. Emit only on a material change; suppress identical observations as `duplicate` and changed observations inside cooldown as `cooldown`. Preserve the latest observation even when it is unusable.

Missing observations and observations older than the configured freshness window must return `INSUFFICIENT_DATA`, never a recommendation. Recommendations must expose source inputs, observed/checked timestamps, age/max-age, confidence, rationale, and explicit invalidation criteria. Price/budget failures should be explicit `NOT_ACTIONABLE` reasons, not silent drops. Keep recommendation actions empty and test that no `sign`, `execute`, `broadcast`, signer import, or executor dependency is reachable from alert/recommendation modules.

Use observation-only worker adapters for market and mint feeds, and sanitized bot formatters that show freshness/reasoning without calldata, signatures, or execution buttons. Test first observation, duplicate suppression, cooldown, material change after cooldown, missing/stale data, threshold/budget decisions, and absence of side-effect surfaces. See `references/observation-alerts.md` for the class-level contract and test matrix. For restart/incident decisions, use `references/reconciliation-pause-kill-switch.md`.

## Restart reconciliation, pause, and kill switch

For restart and incident handling, treat persisted execution records as the authority for what may happen next. A persisted TxHash always enters reconciliation-only handling; it must never trigger a fresh sign or broadcast. A signed record without a persisted TxHash is ambiguous and must be quarantined rather than re-signed. Terminal states (`confirmed`, `reverted`, `replaced`, `dropped`) are not retryable.

Reconcile nonce state against the chain before reopening a wallet lane. Any disagreement between chain pending nonce and persisted next nonce is a quarantine decision, not an invitation to guess or overwrite state. For orders, indexer absence is lag, not cancellation; reorg-removed receipt/log evidence is unknown until re-observed; chain state outranks an indexer label. Ownership reads are tri-state: exact match confirms, mismatch invalidates, missing/error remains unknown.

Model pause and kill control as durable, audited state. Pause blocks new claims and broadcasts but may be resumed explicitly. A kill switch is stronger: resume must not clear it; only an explicit, separately authorized clear operation can return execution to running. Put the control check before journal claim, signer, nonce allocation, and RPC calls. Include the control revision/reason in incident records so an operator can reconstruct why a plan was blocked.

Keep a bounded fault matrix with a decision for every crash/uncertainty path: retry only when failure is proven pre-broadcast; otherwise use `UNKNOWN_NEEDS_RECONCILIATION` with `reconcile_only`. Receipt revert/replacement is terminal, while response loss, already-known ambiguity, reorg removal, indexer lag, DB unavailability, and kill-switch activation must never silently retry or report success. Suppress success notifications until receipt, exact logs, post-state, and accounting are reconciled.

See `references/reconciliation-pause-kill-switch.md` for the state matrix, durable schema constraints, and focused chaos test cases.

## Testing strategy

Create vertical red-green slices for concurrency, release semantics, quarantine behavior, bounded inventory, claimed-state accounting, and notification ordering. Prefer pure functions for amount selection and narrow seams/fakes around quote, submit, accounting, and notification adapters. Run concurrency tests with the race detector.

See `references/critical-side-effect-safety.md` for a reusable test matrix and verification fallback.

For DEX/router adapter implementation details—exact approvals, fee-on-transfer receipt accounting, journal-hook boundaries, chain-registry evidence rules, strict vertical TDD slices, and ad-hoc focused race verification—use `references/protocol-adapter-safety.md`.

For full V2/V3/V4 integrations, use `references/multi-protocol-integration-gate.md`. It prevents registry-only work from being mistaken for end-to-end completion and covers runtime hook-code verification, route persistence/reconciliation, fixture simulation evidence, and unique-tempfile verification when no canonical gate is detectable.

For Permit2 plus hooked Uniswap V4 execution primitives, use `references/permit2-v4-execution.md`. It covers exact zero-first approval, bounded uint160/uint48 values, native-vs-WETH value handling, runtime code-hash checks, chain-specific router ABIs, independently verified PoolIds, full manual/TP-SL wiring, read-only fixture simulation, focused race tests, and ad-hoc verification evidence.
