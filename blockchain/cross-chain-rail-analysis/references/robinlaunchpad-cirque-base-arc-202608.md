# RobinLaunchpad vs CirqueDEX (Base → Arc) — evidence notes

Session-derived comparison. Read-only. Not a live exploit guide.

## Product → rail

| Product | Settlement rail | Source markers | Completion markers |
|---|---|---|---|
| RobinLaunchpad `robinlaunchpad.com/bridge` | Circle **CCTP V2** | Router `bridge` → USDC burn; `TokenMessengerV2` `0x28b5…cf5d`; `MessageTransmitterV2` `0x81d4…4b64`; Iris `/v2/messages/6?transactionHash=` | Iris non-pending message+attestation; destination `receiveMessage`/forwarding receipt; recipient USDC delta |
| CirqueDEX `cirquedex.xyz/bridge` | Circle **Gateway** | `GatewayWallet` `0x7777…00eE` deposit; EIP-712 BurnIntent; Arc `gatewayMint` on `0x2222…C205` | Gateway balance change; destination gatewayMint receipt; recipient USDC delta |

## RobinLaunchpad call shape (observed)

```text
approve USDC (bounded) → bridge(amount, arcRecipient, maxFeeBps)
maxFeeBps example: 200 = 2%
wallet debit = amount
router fee = amount * feeBps / 10000  (observed 2%)
CCTP burn = amount - fee
```

Do **not** decode `maxFeeBps` as a destination domain.

## Completion honesty

```text
Base burn success + Iris PENDING = source-confirmed / destination-pending
Not claimable until attestation + message exist
Auto-relayer copy is design intent for Base→Arc, not proof of mint
```

## Wallet multi-rail

Same EOA can show:

1. earlier Cirque fee+deposit sequences on Base + Arc `gatewayMint`s
2. later RobinLaunchpad CCTP burn still attesting

Classify **per transaction**, not per wallet brand.

## Useful endpoints (public)

```text
Iris: https://iris-api.circle.com/v2/messages/{sourceDomain}?transactionHash=
Robin status (if up): https://robinlaunchpad.com/bridgeapi/status?txHash=
Cirque gateway balances (product API shape may change): POST /api/gateway/v1/balances
Base RPC + Arc RPC for receipts/balances
```
