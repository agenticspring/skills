# Arc CCTP Mint-Burst Gate

Use this pattern when a CCTP fee route can remain advertised while attestation/forwarding is stalled, and Auto Bridge must avoid firing on route availability alone.

## Safety model

A destination burst is a probabilistic pre-burn timing signal, not a guarantee that the next source burn will be attested. Keep the individual post-burn completion gate unchanged.

```text
ARMED
→ verified global Arc CCTP mint burst
→ source route/finality/fee preflight
→ burst freshness recheck
→ atomic ARMED → FIRED
→ one bridge attempt
```

While only ARMED: no approval, burn, or transaction.

## Valid Arc mint observation

Monitor direct Arc RPC, not an explorer indexer, for:

- contract: `MessageTransmitterV2` at `0x81D40F21F12A8F0E3252Bccb954D722d4c464B64`;
- event topic: `MessageReceived`, `0xff48c13eda96b1cceacc6b9edeedc9e9db9d6226afbc30146b720c19d3addb1c`;
- transaction receipt status success;
- same receipt contains Arc USDC `Transfer(from=0x0, to=recipient, value)` from `0x3600000000000000000000000000000000000000`;
- unique transaction hash and CCTP nonce.

Do not count ordinary USDC transfers, approvals, swaps, failed receipts, removed logs, or historical logs loaded at startup.

The MessageReceived nonce is indexed topic 2 on the verified Arc event. Correlating the same successful receipt with a zero-address USDC mint prevents treating generic CCTP messages or ordinary token movement as a landing.

## Default and configurable policy

Default:

```text
30 unique valid mints
rolling 10 seconds
at least 5 unique recipients
latest mint age ≤2 seconds
```

Keep settings per user and bounded:

```text
threshold: 5–200
window: 2–60 seconds
min recipients: 2–threshold
latest age: 1–10 seconds and ≤window
```

Validate cross-field constraints before arming. Allow reset to safe defaults. A user's current policy may evaluate a shared global detector; source domain is not required for burst counting. Source chain remains mandatory for the actual RPC/contracts/balance/fee/burn preflight.

## Detector implementation invariants

1. First poll records the current confirmed block as a baseline and consumes no historical logs.
2. Serialize concurrent polls and count only after a small confirmation depth (current proven pattern: 2 Arc blocks).
3. Persist block number/hash and log index with each candidate. Require `receipt.BlockHash == log.BlockHash`, `receipt.BlockNumber == log.BlockNumber`, and `header.Hash() == log.BlockHash`.
4. Re-query a recent overlap (current proven pattern: 16 blocks), reconcile canonical events, and remove orphaned/reorged observations before evaluating readiness. `log.Removed` alone is insufficient for historical HTTP polling.
5. Keep a rolling buffer long enough for the maximum user window; deduplicate policy aggregation by tx hash and CCTP message by nonce.
6. On block, log, receipt, header, or canonical reconciliation failure, return an unhealthy poll. Never execute Auto Bridge using a stale ready snapshot.
7. Bound `eth_getLogs` requests to at most 1,000 blocks for Thirdweb compatibility; use direct Arc RPC, with explorers only as fallback/cross-check.
8. After the source-route HTTP check, re-evaluate burst freshness before claiming the intent.
9. Claim `ARMED → FIRED` with a conditional update and inspect `RowsAffected`; only the single caller with exactly one changed row may broadcast.
10. One burst may wake multiple users, but each durable intent fires at most once.

## UI requirements

Show both live progress and configured trigger:

```text
Arc Burst: 18/30 mints · 7 recipients · latest 0.8s ago
Trigger: 30 mints/10s · ≥5 recipients · latest ≤2s
```

Expose a Burst Trigger submenu for threshold, window, recipient diversity, freshness, and reset defaults. Be explicit that this is a timing signal, not guaranteed landing.

## Verification

Regression tests should cover:

- startup baseline does not replay history;
- successful MessageReceived + zero-mint correlation;
- missing zero mint rejected;
- failed receipt rejected;
- tx and nonce dedupe;
- recipient diversity;
- rolling-window expiry and stale latest event;
- per-user policies;
- invalid/cross-field setting rejection;
- route-only state cannot fire an intent.

Use a read-only live probe to establish a baseline, poll subsequent Arc blocks, and verify no historical count. Verify at least one real MessageReceived receipt contains the expected Arc USDC zero-mint event. Never send a canary or burn without explicit authorization.

## Operational pitfall

A successful mint burst cannot prove that a subsequent wallet will be selected by Iris, especially if processing is selective or extremely short-lived. Never report guaranteed landing. Auto Buy must still wait for that burn's Iris `forwardTxHash`, successful canonical Arc receipt, confirmations, and recipient USDC balance increase.
