# Receipt and Value Reconciliation Checklist

Use this for any bridge hash review. It is deliberately read-only.

## 1. Source transaction

Record:

```text
chain ID
block / timestamp
from / to
selector and decoded arguments
status / gas used / execution + L1 fee
```

Never treat a successful outer transaction as proof of destination delivery.

## 2. Token flow

Build a receipt-derived table:

```text
from wallet → application/router or Gateway Wallet
application/router → service/fee recipient
application/router/Gateway → canonical bridge contract
canonical burn/deposit amount
remaining allowance
```

For ERC-20 logs, verify `Transfer` topic and raw units before converting decimals.

## 3. Rail-specific evidence

### CCTP

```text
TokenMessenger or MessageTransmitter address
MessageSent(bytes)
message header source/destination domains
burn token / amount / mint recipient
Iris status + attestation/message
```

`destinationDomain` in the CCTP message is the authoritative domain. An outer app parameter named `destination`, `route`, or a number such as `200` may be an application ID or fee bound.

### Gateway

```text
Gateway Wallet address
GatewayWallet.deposit(token,value)
Gateway balance after finality
TransferSpec fields
BurnIntent maxBlockHeight/maxFee
EIP-712 signature
Gateway Minter / relay transfer result
```

Do not substitute CCTP `MessageSent`/Iris fields for Gateway balance/intent evidence.

## 4. Destination completion

Require all available evidence:

```text
non-pending protocol/API status
→ destination transaction hash
→ destination receipt status = success
→ expected destination contract/event
→ recipient balance increase by expected amount
```

Classify as `source-confirmed/destination-pending` when the source is final but one of these is missing.

## 5. Fee math

Keep distinct:

```text
platform/service fee
Circle protocol/forwarding fee
source-chain gas
L1 data fee
destination relayer gas
```

Use a script or arbitrary-precision decimal math. Do not round raw token units early. Confirm that the observed fee equals the contract's fee configuration at the transaction block, not only the current value.

## 6. Trust boundaries

Record owner/admin, fee recipient, signer, rescue function, upgrade/proxy slots, and destination relayer separately. A centralized relayer or configurable fee is a trust boundary; it is not automatically a vulnerability.

## 7. Report language

Use precise labels:

- `CCTP source burn confirmed; destination pending`
- `Gateway deposit/intent confirmed; destination relay pending`
- `destination confirmed`
- `rail unresolved`

Never report “bridged successfully,” “minted,” or a destination tx hash without direct evidence.