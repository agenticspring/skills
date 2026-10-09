# App-Router Auto-Relay vs CCTP Claimability

## Problem

Frontends advertise “mint on destination; you only sign once on source.” That can be true as **UI design** while the transfer is still **not claimable**.

## RobinLaunchpad Base→Arc (verified 2026-07-31)

Frontend:

```text
bridge/track on Base
→ poll /bridgeapi/status every ~5s
→ expect backend stage minting/done after off-chain relayer
→ no browser receiveMessage on Arc
```

Manual `receiveMessage(message, attestation)` existed for **Arc→Base** only.

Live incomplete status example:

```json
RobinLaunchpad: {"stage":"attesting"}
Iris: {"attestation":"PENDING","message":null,"status":"pending_confirmations"}
```

## Rules

1. Source burn success ≠ claimable.
2. Claim/relay needs Iris non-pending `message` + `attestation`, or destination already minted.
3. Do not invent a user claim path for Base→Arc if the app only auto-relays.
4. Bounded approve + bridge still means user signed on Base; “sign once” may omit approve.
5. App fee args (`maxFeeBps`) are not CCTP destination domains.

## Resume checklist after archive

```text
re-query Iris for burn tx
re-query app status if present
check destination receive/mint receipt
check recipient USDC balance delta
only then say delivered
```