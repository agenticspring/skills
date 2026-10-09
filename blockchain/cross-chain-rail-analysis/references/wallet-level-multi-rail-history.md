# Wallet-Level Multi-Rail History

Use when a user asks whether “this wallet already bridged via Cirque / Robin / Gateway / CCTP.”

## Rule

```text
Classify each source transaction’s rail independently.
Wallet habit is corroboration, not proof for a new hash.
```

## Confirmed pattern (wallet 0x5b86…ff3c2, 2026-07-29 → 07-31)

### Cirque / Circle Gateway (destination-confirmed history)

Base deposits into Gateway Wallet `0x77777777Dcc4d5A8B6E418Fd04D8997ef11000eE` with paired ~2.5% fee transfers to Cirque fee wallet, then Arc `gatewayMint` on Minter `0x2222222d7164433c4C09B0b0D809a9b52C04C205`.

Markers:

```text
method: deposit (Base USDC → GatewayWallet)
method: gatewayMint(bytes,bytes) (Arc)
TransferSpec: sourceDomain 6, destDomain 26, same depositor/recipient
```

Do **not** require deposit amount == mint amount. Gateway is a unified balance.

### RobinLaunchpad / CCTP (separate later tx)

```text
approve USDC for router 0x234502…5d4e
→ bridge(amount, recipient, maxFeeBps=200)
→ 2% router fee
→ TokenMessenger/MessageTransmitter burn + MessageSent
→ Iris /v2/messages/6?transactionHash=...
```

Last live incomplete status observed:

```text
RobinLaunchpad /bridgeapi/status: stage=attesting
Iris: attestation=PENDING, status=pending_confirmations, message=null
```

Label: `source-confirmed/destination-pending` until Iris non-pending + Arc mint receipt + balance delta.

## Quick decision table

| Question | Answer from evidence |
|---|---|
| Did wallet ever use Cirque Gateway? | Look for GatewayWallet deposits + Arc gatewayMint |
| Is the current RobinLaunchpad hash Gateway? | No if TokenMessenger/MessageSent/Iris path present |
| Can user claim CCTP mint now? | Only if Iris returns non-pending message+attestation (or destination already minted) |
| Does “sign once on Base” mean funds landed? | No — only means Base→Arc UI does not ask for Arc signature |

## Archive resume checklist

When user says “gajadi / archive / nanti aja”:

1. Mark investigation note ARCHIVED/PAUSED with date.
2. Store last Iris/app status and hashes.
3. No monitor, claim, relay, or broadcast.
4. On resume: re-query Iris + destination live; never trust cached pending status as final.