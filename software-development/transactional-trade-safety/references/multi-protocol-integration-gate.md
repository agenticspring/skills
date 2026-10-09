# Multi-protocol integration completion gate

Use this when integrating V2/V3/V4 routing into an existing journaled trading bot.

## Inspect before editing

A shared or restored workspace may already contain route models and protocol packages with changed APIs. Read the current registry, route types, discovery, quote, swap, journal, position schema, manual execution, TP/SL, reconciliation, and UI selector before adding code. A directory without `.git` still requires filesystem inspection; do not infer ownership or reset files.

## End-to-end completion matrix

Do not describe a registry-only or policy-only patch as end-to-end. Require evidence for every requested layer:

1. Canonical per-chain V2/V3/V4 deployment registry.
2. Generic ERC20 metadata reading independent of launcher-specific views.
3. Route discovery across all enabled protocols.
4. Amount-aware quote comparison for the actual input amount.
5. Allowlisted intermediate-token multihop construction.
6. Hook address plus runtime-bytecode hash validation before quote and execution; unknown or changed code fails closed.
7. Protocol-specific execution preserving prepared/submitted/mined hooks.
8. Exact bounded ERC20 and Permit2 allowances, including reset-to-zero compatibility where needed.
9. Receipt-derived realized output rather than quote/router return assumptions.
10. Manual buy/sell and TP/SL using the selected persisted route.
11. Route metadata sufficient for restart reconciliation and fail-closed decoding.
12. UI chain exposure through the canonical registry.

## Hook policy

Treat address allowlisting and runtime-bytecode verification as separate requirements. An address-only helper is insufficient. Fetch runtime code through the chain RPC, hash the exact bytes, compare against a chain-scoped pinned hash, and perform this check at the RPC-facing discovery/execution boundary. Zero hooks may be accepted explicitly. Hook data must remain empty only when verified source semantics permit it.

## Fixture evidence

For each supplied fixture, produce read-only evidence where technically possible:

- token metadata and decimals;
- discovered protocol/pool or verified PoolKey/PoolId;
- quote for a stated amount;
- `eth_call` simulation of execution calldata from a non-broadcasting caller;
- selected route and competing route outputs;
- hook runtime hash for hooked V4 pools.

Never turn a simulation into a transaction. If public RPC limitations, missing full PoolIds, or unavailable archive logs block evidence, identify the exact missing datum or RPC response.

## Verification when no canonical gate is detectable

Create a unique script with `mktemp /tmp/hermes-verify-XXXXXX` (or an equivalent OS-safe tempfile API), not a fixed filename. The script should check formatting, focused race tests for changed and directly dependent packages, `go vet ./...`, and `go build ./...`. Execute it, preserve the real output, and remove it afterward. Label this **ad-hoc focused verification**, never canonical suite green.

A passing gate proves only the implemented tree is internally healthy. It does not prove omitted integration layers are complete. Report implemented files, evidence, and remaining blockers separately.
