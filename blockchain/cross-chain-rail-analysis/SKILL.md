---
name: cross-chain-rail-analysis
description: Use when identifying a bridge's actual settlement rail.
version: 1.1.0
author: spring
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [web3, bridges, CCTP, Gateway, receipts, provenance]
    related_skills: [web3-public-disclosure-corpus, cctp-bridge, web3-rpc-contract-audit]
---

# Cross-Chain Settlement Rail Analysis

## Purpose

Identify what actually moves value behind a bridge product: CCTP burn-and-mint, Circle Gateway unified balance, LayerZero/Stargate, a liquidity bridge, or a custom relay. Separate the product/frontend layer from the settlement rail. This is a read-only, evidence-first workflow for transaction review, integration audits, and defensive bug-bounty research.

Do not infer the rail from branding, a page title, a generic “bridge” label, or a chain name. Do not connect a wallet, sign, approve, broadcast, relay, or execute a historical exploit while performing this analysis.

## Core distinction

```text
application / frontend
    → application router or coordinator
        → underlying settlement rail
            → destination execution / mint
```

A platform can charge its own fee and use a separate router while the underlying rail remains Circle CCTP or Circle Gateway. Record these independently:

- application/platform and router;
- source token and source-chain transaction;
- settlement rail and canonical contracts;
- platform fee, Circle fee, source gas, and destination-relay gas;
- destination completion proof.

## Evidence-first workflow

1. **Pin the target and scope.** Record URL, source chain, destination chain, hashes, timestamp, and whether the analysis is read-only. Never assume a chain ID is the same as a protocol domain ID.
2. **Fetch raw transaction and receipt from at least one independent RPC.** Record `chainId`, `from`, `to`, calldata, status, block, logs, and all token transfer events. If an explorer is bot-gated, use RPC as the primary evidence and note the explorer limitation.
3. **Decode the outer call.** Resolve the selector using ABI/source or a signature registry, but treat a registry hit as a hint. Read the target bytecode and public views where available. Distinguish fee/route parameters from destination-domain parameters.
4. **Follow the internal value flow.** For ERC-20 routes, reconcile sender debit, platform fee, router balance, canonical bridge deposit/burn, and any residual allowance. Check exact decimal math.
5. **Classify the settlement rail using canonical evidence.** Use the CCTP and Gateway gates below. If neither gate passes, classify as `unknown/custom` and keep the candidate unresolved.
6. **Validate destination completion separately.** A successful source transaction or an API `200` does not prove delivery. Require a non-pending protocol status, destination receipt, and recipient balance delta on the expected destination network.
7. **Inspect the public frontend only as corroboration.** Download the exact route chunk, store its URL and SHA-256, and extract configured addresses, domains, fee fields, API endpoints, and completion logic. Do not treat frontend configuration as stronger than on-chain receipt evidence.
8. **Report uncertainty explicitly.** Use `confirmed`, `source-confirmed/destination-pending`, `destination-confirmed`, or `unresolved`. Never fabricate a destination tx hash or attestation.

## Rail gates

### CCTP burn-and-mint

Count CCTP as confirmed when source evidence shows most or all of:

- Circle TokenMessenger/MessageTransmitter address or verified deployment;
- `depositForBurn`, `depositForBurnWithHook`, or a router that demonstrably calls that flow;
- `MessageSent(bytes)` from MessageTransmitter;
- message bytes decode to source domain, destination domain, burn amount, and mint recipient;
- Circle Iris `/v2/messages/{sourceDomain}?transactionHash=...` returns the matching message record.

CCTP destination completion requires:

```text
non-pending attestation/message
→ destination receiveMessage or forwarding receipt
→ recipient native-USDC balance increase
```

A platform router argument such as `200` must not be called a CCTP destination domain until the emitted CCTP message header confirms the domain. CCTP domain IDs are not EVM chain IDs.

### Circle Gateway

Count Gateway as confirmed when source evidence shows most or all of:

- Gateway Wallet contract `deposit(token,value)` or the documented Gateway Wallet interface;
- Gateway balance/estimate/transfer API interaction;
- typed `BurnIntent`/EIP-712 signing with a `TransferSpec` containing source/destination domains, contracts, tokens, depositor, recipient, salt, and fee bounds;
- destination Gateway Minter or a documented Gateway transfer/relay result;
- Gateway transfer status and destination receipt/balance evidence.

Gateway is not a CCTP source burn merely because it uses Circle, USDC, domains, or a relayer. Keep Gateway Wallet balance accounting separate from CCTP Iris/MessageTransmitter evidence.

### Other or custom rails

For LayerZero, Stargate, Wormhole, Across, liquidity bridges, and custom coordinators, require their own canonical event/function/API markers. Do not force a CCTP/Gateway classification because the app routes to Arc or because a UI says “native USDC.”

## Frontend bundle extraction

When source code is not published:

- fetch the page HTML and route-specific JavaScript chunk;
- save URL, acquisition timestamp, byte length, and SHA-256;
- extract contract addresses, chain IDs, protocol domains, fee constants, API paths, and status transitions;
- compare the configured values to the transaction receipt;
- treat stale or contradictory bundle values as a finding for integration review, not proof of theft.

Useful pattern search terms:

```text
TokenMessenger MessageTransmitter MessageSent depositForBurn
GatewayWallet GatewayMinter deposit BurnIntent TransferSpec
attestation pending_confirmations receiveMessage mint relayer
```

## Value and fee reconciliation

For each transfer, produce a table like:

```text
wallet debit
- platform/service fee
= canonical deposit/burn or Gateway deposit
- protocol/destination fee where applicable
= expected recipient amount
```

Keep Base/ETH gas, L1 data fee, platform fee, Circle fee, forwarding fee, and destination gas as separate rows. Verify units and token decimals before calculating.

## Completion labels

| Label | Meaning |
|---|---|
| `source-confirmed/destination-pending` | Source debit/deposit/burn is proven; no destination mint/receipt yet. |
| `destination-confirmed` | Destination receipt and recipient balance delta are independently proven. |
| `unresolved` | Rail or value flow cannot be established from available public evidence. |
| `historical/unknown` | Old or conflicting configuration; current liveness not established. |

## Safety and reporting

- Read-only RPC, HTTP, source inspection, and public API calls are allowed.
- Do not approve tokens, sign typed data, submit `receiveMessage`, or broadcast a relay transaction during analysis.
- Do not call an app router a drainer without proving unauthorized control, asset impact, and attacker capability.
- A missing destination receipt is a settlement-status issue, not automatically a vulnerability.
- A configurable fee or rescue function is an administrative trust boundary; it is not automatically a bug.
- When the user says archive / gajadi / nanti aja: mark the investigation ARCHIVED/PAUSED with last live statuses, stop monitoring/claim/relay, and on resume re-query Iris/app/destination live — never treat a cached `pending` as final.

## Naming traps

- Chat “Robinhood bridge” often means **RobinLaunchpad** (`robinlaunchpad.com/bridge`), not Robinhood Chain.
- Same wallet can have prior **Gateway** history and a later **CCTP** burn. Classify **per transaction**, not by wallet habit.

## References

- `references/cross-chain-rail-identification.md` — condensed CCTP vs Gateway evidence patterns and the RobinLaunchpad/CirqueDEX comparison.
- `references/wallet-level-multi-rail-history.md` — same-wallet multi-rail history, Gateway vs CCTP markers, archive/resume checklist.
- `references/receipt-value-reconciliation.md` — reusable receipt/log/fee reconciliation checklist.
