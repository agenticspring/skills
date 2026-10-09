# Forwarding Completion Gate

Use this when bridge completion triggers any downstream automation (buy, transfer, notification marked final).

## Never treat these as completion

- forwarding route/fee endpoint is live;
- source burn transaction exists;
- Iris has indexed the source transaction;
- Iris status is `pending_confirmations`;
- an attestation exists or is ready;
- a `forwardTxHash` exists by itself.

## Required completion proof

```text
Iris forwardTxHash present
→ destination Arc receipt exists and has status=success
→ required destination confirmations reached
→ canonical receipt still matches
→ recipient Arc USDC balance is greater than the pre-burn snapshot
→ downstream action eligible
```

Use the full 32-byte burn hash, recipient wallet, and target token as a durable idempotency key. Persist a pre-broadcast claim before an automated buy; persist the destination buy hash after RPC acceptance; never retry a claimed operation after a submitted hash without reconciliation.

## SniperX policy

- Auto Bridge is a durable, one-shot bridge intent; never implement it as a repeating balance-draining timer.
- Auto Buy is independent: it only operates for explicit user-added targets after the completion proof above.
- If Auto Buy is enabled after a bridge completed, reload completed burns and safely process only unclaimed target jobs.
- Temporary quote/RPC failure before broadcast may release the claim for retry. Once a transaction is submitted, retain the claim and reconcile it.

## Iris diagnostics observed

`GET /v2/messages/{sourceDomain}?transactionHash={burnTx}` returns `pending_confirmations` before Iris can issue an attestation or forwarding transaction. In the observed samples, Base used source domain 6 and Avalanche used domain 1. This status must remain pending with no bridge-complete or auto-buy notification.

## Rate limiting

Circle documentation warns that the attestation service has request limits. Use bounded polling with backoff and do not fan out unbounded per-user requests.
