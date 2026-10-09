# SniperX automation pattern

Use this pattern for a user-configured CCTP bridge followed by an optional destination buy.

## UX configuration
- Keep automation settings separate from normal manual bridge/trade settings:
  - source chain;
  - fixed bridge USDC amount;
  - fixed buy USDC amount **per target**;
  - explicit target list.
- Use one-click toggle labels with clear state: `🟢 ON` / `🔴 OFF`.
- A target list must be separate from generic scan/watch history.

## Durable state
- `Auto Bridge ON` creates a single persistent intent: source, amount, chat ID, `armed`.
- On observed forwarding-route availability, atomically transition `armed -> fired` before broadcast.
- `OFF` cancels only `armed`; it cannot reverse an already-submitted burn.
- Never implement a recurring `while enabled { bridge() }` loop.

## Completion gate for destination automation
Do **not** equate any of these with a complete bridge: route availability, Iris indexing, `pending_confirmations`, attestation availability, or a bare `forwardTxHash`.

Required proof chain:
1. Iris returns `forwardTxHash`.
2. Destination receipt is successful.
3. Receipt remains canonical after configured confirmations.
4. Recipient destination-USDC balance is greater than the baseline persisted immediately before the source burn.
5. Only then claim a durable `(burnTx, recipientWallet, target)` buy slot.

## Retry / idempotency
- Release an unsubmitted buy claim after a pre-broadcast metadata/quote/approval failure so a later tick may retry.
- Once RPC accepts a tx hash, persist it and never send a second buy for that identity.
- Scan completed bridge records after restart to recover the completion-to-buy handoff.

## Pending status examples
During a July 2026 check, user-supplied Base domain 6 and Avalanche domain 1 burns returned Iris `pending_confirmations`, with neither attestation nor `forwardTxHash`. Such records must remain inert.
