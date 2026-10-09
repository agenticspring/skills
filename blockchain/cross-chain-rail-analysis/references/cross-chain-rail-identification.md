# Cross-Chain Rail Identification Reference

## RobinLaunchpad example: CCTP

Public route: `https://robinlaunchpad.com/bridge`

Observed public bridge bundle (recorded 2026-07-31):

```text
router:             0x234502cf5fbea7eac5bc9fd812f6b7580d315d4e
Base USDC:          0x833589fcd6edb6e08f4c7c32d4f71b54bdA02913
Arc USDC config:    0x3600000000000000000000000000000000000000
Base chain ID:      8453
Arc chain ID:       5042
Base CCTP domain:   6
Arc CCTP domain:    26
feeBps:             200
TokenMessenger:     0x28b5a0e9c621a5badaa536219b3a228c8168cf5d
MessageTransmitter: 0x81d40f21f12a8f0e3252bccb954d722d4c464b64
Iris:               https://iris-api.circle.com/v2/messages
```

The relevant frontend function is `bridge(amount, arcRecipient, maxFeeBps)`. The value `200` is a fee bound/quote (`2%`), not a CCTP domain. The source receipt must still prove `MessageSent(bytes)` and the emitted CCTP header should be decoded for the actual destination domain.

Expected CCTP evidence:

```text
TokenMessenger/MessageTransmitter logs
→ MessageSent(bytes)
→ Iris message record
→ destination receiveMessage/forwarding receipt
→ recipient USDC balance delta
```

Base→Arc UI design (bundle-verified): user signs on Base; frontend tracks burn and polls `/bridgeapi/status`; no browser `receiveMessage` on Arc. Manual `receiveMessage` appears for **Arc→Base** claim only. Design ≠ delivery: Iris may remain `pending_confirmations` with `message=null`.

## CirqueDEX example: Circle Gateway

Public route: `https://cirquedex.xyz/bridge`

Observed bridge page and route bundle (recorded 2026-07-31):

```text
Gateway Wallet:    0x77777777Dcc4d5A8B6E418Fd04D8997ef11000eE
Arc GatewayMinter: 0x2222222d7164433c4C09B0b0D809a9b52C04C205
Base USDC:         0x833589fcd6edb6e08f4c7c32d4f71b54bdA02913
Arc USDC:          0x3600000000000000000000000000000000000000
Base domain:       6
Arc domain:        26
Fee wallet:        0x91bca5c3e880f215e22368bA348a57f0815342E
Platform fee:      2.5%
```

The page explicitly describes:

```text
Base USDC enters Circle Gateway
→ Cirque relays the Arc mint
```

The route bundle defines `GatewayWallet.deposit(token,value)`, a `TransferSpec`, a typed `BurnIntent`, Gateway API paths such as `/v1/estimate`, `/v1/balances`, `/v1/transfer/{id}`, and a separate `/api/relay`. It then checks the Gateway balance, signs the burn intent, and sends it to the Cirque relayer.

Expected Gateway evidence:

```text
USDC approve Gateway Wallet
→ Gateway Wallet deposit
→ Gateway balance/finalization
→ EIP-712 BurnIntent
→ Gateway Minter / relay result
→ destination receipt + recipient balance delta
```

Do not classify this as CCTP solely because it uses Circle, domains 6/26, native USDC, or a relayer. Gateway Wallet and Gateway Minter evidence is the distinguishing marker.

## Comparison

| Property | RobinLaunchpad | CirqueDEX |
|---|---|---|
| Application fee | 2% | 2.5% |
| Source app contract | Custom router | Gateway Wallet deposit path |
| Rail | CCTP burn-and-mint | Circle Gateway unified balance |
| Source marker | `MessageSent(bytes)`, CCTP Messenger | `GatewayWallet.deposit`, Gateway balance, BurnIntent |
| Circle API | Iris `/v2/messages/{domain}` | Gateway estimate/balance/transfer APIs |
| Destination execution | CCTP receive/relayer | Gateway Minter / relayer |

Both routes still require destination receipt and recipient balance proof before they can be labeled delivered.

## Hard pitfalls (live reviews 2026-07/08)

1. Chat “Robinhood” often means **RobinLaunchpad**, not Robinhood Chain.
2. Same wallet can hold **both** prior Gateway history and a later CCTP burn — classify **per tx**.
3. `maxFeeBps=200` is fee, never destination domain.
4. “Sign once on Base / relayer mints” is UI design; incomplete until Iris non-pending + destination mint proof.
5. Gateway mints need not 1:1 match each deposit amount (unified balance).
6. On user “gajadi / archive”: mark investigation ARCHIVED/PAUSED; no auto-claim/monitor; resume only with live re-check.

See also: `references/wallet-level-multi-rail-history.md`.

## Caveat

This reference records public configuration and method patterns, not an assertion that every historical or future route on either product uses the same deployment. Re-fetch the current bundle and verify each transaction's receipt.