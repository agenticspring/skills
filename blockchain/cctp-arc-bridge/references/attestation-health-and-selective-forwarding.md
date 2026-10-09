# Attestation Health and Selective Forwarding

Use this when deciding whether an automated CCTP burn is safe to start while Iris/forwarding appears degraded.

## Distinguish the signals

- Source transaction confirmed: the burn/message exists on the source chain. It says nothing about destination delivery.
- Iris fee route available: Circle advertises a source→destination fee/finality option. It does not prove the attestation signer or forwarding worker is processing new messages.
- Circle status component operational: useful coarse telemetry, not message-level proof.
- Iris `pending_confirmations`: the message is indexed but not complete; never treat it as readiness.
- Arc landing: only proves that specific burn completed.

Circle status telemetry is available from `https://status.circle.com/api/v2/components.json`, including the CCTP group, Attestation Service, ARC, and source-chain minting/burning components. Iris itself has no preflight endpoint equivalent to `canAttest(wallet, route)` or a reservation for the next message.

## Selective/random forwarding caveat

A successful witness does **not** necessarily prove that the next wallet/message will be attested. If Iris temporarily completes only selected messages or opens for millisecond-scale windows:

```text
message A lands on Arc
≠ pipeline globally healthy
≠ message B burned immediately afterward will land
```

Therefore, never implement `one landing in the last N minutes → auto-burn every armed intent` as a hard safety guarantee. Even multiple recent landings are only probabilistic telemetry when completion is selective.

## Safe policy

Default to a fail-closed mode:

```text
Auto Bridge ON → durable ARMED intent
route/status/landing telemetry → display and notify only
no automatic approval or burn while attestation acceptance is unproven
```

If product requirements permit risk-taking, expose a separate explicit aggressive/manual-confirm mode with clear wording that the next burn may remain pending. Do not silently downgrade safe mode.

A canary burn is also a real irreversible burn and can become stuck; require explicit user approval and a bounded amount. It still cannot guarantee the next message will pass.

## Community explorer telemetry

The community Arc explorer at `https://megaeth-pump-ok-moon.poptyedev.com/` is a Blockscout frontend, not a JSON-RPC endpoint. Its same-origin API responds under paths such as:

- `/api/v2/stats`
- `/api/v2/blocks`
- transaction/address/token-transfer endpoints from Blockscout API v2

Use it to observe Arc blocks, receipts, and USDC transfers after landing. Correlate a landing with Iris `forwardTxHash`, successful canonical Arc receipt, recipient, and USDC amount. A generic USDC transfer is not a CCTP witness.

## Completion remains strict

For a burn that already exists, downstream automation still requires:

```text
Iris forwardTxHash
→ successful canonical Arc receipt
→ required confirmations
→ recipient USDC balance increased from the pre-burn snapshot
```

This completion gate protects Auto Buy; it does not solve pre-burn attestation prediction.
