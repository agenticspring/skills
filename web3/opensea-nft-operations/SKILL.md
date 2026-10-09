---
name: opensea-nft-operations
description: Use for OpenSea NFT operations.
version: 1.0.0
author: spring
license: MIT
metadata:
  hermes:
    tags: [opensea, nft, seaport, marketplace, mint, listing, sweep, multi-wallet]
    related_skills: [transactional-trade-safety, web3-freemint-batch-execution, web3-rpc-contract-audit]
---

# OpenSea NFT Operations

## Overview

Use this skill for OpenSea marketplace and primary-mint operations across multiple EVM wallets. It covers read-only discovery, collection and NFT pricing, wallet inventory, listing/selling, buying/sweeping, offers, transfers, and transaction verification.

OpenSea has two different surfaces:

1. **Primary mint:** a collection's drop or mint contract. Minting is governed by the collection's contract, allowlist, price, supply, phase, and mint transaction.
2. **Secondary marketplace:** listings, offers, fulfillment, cancellations, collection stats, and events through OpenSea API v2 / SDK and Seaport-compatible order flows.

Default mode is read-only. Listing, selling, buying, sweeping, approving, minting, transferring, and cancelling orders are financially consequential and require explicit confirmation at the final pre-broadcast boundary.

Official references:

- https://docs.opensea.io/
- https://docs.opensea.io/reference/api-overview
- https://docs.opensea.io/reference/opensea-js
- https://docs.opensea.io/docs/collection-offers-and-advanced-trading

## When to Use

Use when the user asks to:

- inspect NFT balances across wallets;
- check floor price, best listing, recent sales, volume, or collection stats;
- mint a primary NFT through a verified collection drop;
- list or sell NFTs on OpenSea;
- cancel listings or offers;
- buy NFTs or sweep the cheapest listings;
- manage multiple wallets and per-wallet inventory;
- calculate net proceeds, fees, gas, royalties, and break-even price;
- reconcile OpenSea orders against on-chain ownership and receipts.

Do not use this skill to guess a collection contract, blindly sign Seaport orders, paste private keys into scripts, or treat an indexer response as final proof of ownership or settlement.

## Phase 0: Secrets, wallet registry, and scope

1. Load credentials only from `~/.hermes/.env`, an approved secret manager, or an existing project-specific secret file. Never ask the user for a key before checking those locations.
2. Never print, copy, upload, or persist private keys, seed phrases, API keys, signatures, raw signed transactions, or secret wallet files in logs, chat, Obsidian, worker payloads, or repository files.
3. Maintain a non-secret wallet registry:

```json
{
  "walletId": "w01",
  "address": "0x...",
  "chain": "ethereum",
  "role": "mint|inventory|seller|buyer",
  "enabled": true
}
```

Private keys remain outside the registry. Checksum and independently verify every address.
4. Define exact scope before any write:
   - chain and collection contract;
   - token IDs or collection slug;
   - wallet IDs included;
   - operation: mint, list, sell, buy, sweep, transfer, cancel;
   - maximum unit price and total budget;
   - gas ceiling;
   - royalty/fee treatment;
   - destination wallet for transfers;
   - expiry and slippage constraints.
5. Multi-wallet operations are explicit batches. Never silently include the default wallet, every wallet on disk, or active wallet history.

Completion criterion: target addresses, collection identifiers, chain, budget, and operation type are explicit; secrets remain redacted.

## Wallet account registration (OpenSea SIWE)

OpenSea wallet registration is not an email/password signup. A wallet becomes an authenticated OpenSea account/profile through SIWE:

1. Create an isolated HTTP session and cookie jar per wallet.
2. `POST https://opensea.io/__api/auth/siwe/nonce`.
3. Build the exact SIWE message for `opensea.io`, URI `https://opensea.io/`, EVM/Ethereum, chain ID 1, the returned nonce, current `Issued At`, and the OpenSea Terms/Privacy statement.
4. Sign the exact message with the wallet's private key in memory. Never log the key, signature, or cookie.
5. `POST https://opensea.io/__api/auth/siwe/verify` with parsed message, signature, `chainArch: "EVM"`, and `connectorId: "injected"`.
6. Require HTTP 200 and a returned `user.userId` matching the wallet address. Persist only address, user ID, status, and timestamp.
7. Use a fresh session per wallet. Serialize or rate-limit the batch and checkpoint after each wallet.
8. Wallet-link endpoint `/__api/auth/accounts/wallets/siwx` is for linking an additional wallet to an already authenticated account; it is not the initial registration route.
9. Email is not required for basic wallet SIWE registration. The OpenSea instant API-key endpoint is separate and rate-limited (maximum two key creations per day); do not confuse API-key creation with wallet registration.

Verification fields:

```text
wallet address
OpenSea userId
authenticated address
HTTP status
checkpoint timestamp
```

## Phase 1: Verify collection and chain

1. Resolve the collection through official OpenSea data and canonical project links.
2. Verify NFT contract and chain from at least two sources, with on-chain code present.
3. Query `chainId`, collection name/symbol where available, supply, token standard, and ownership behavior.
4. Check proxy/upgradeability, pausing, blacklist, transfer restrictions, unusual mint authority, and unsupported token behavior.
5. For primary mints, inspect the actual mint ABI/bytecode and live phase: function, price, quantity, max-per-wallet, allowlist proof, payment token, refund behavior, deadline.
6. Verify OpenSea collection and contract are the same asset. A similar slug is not proof.

Completion criterion: chain ID, contract, token standard, collection identity, and operation-specific method are verified.

## Phase 2: Read-only inventory and balances

For every wallet in scope, collect:

- native balance and spendable balance after gas reserve;
- relevant ERC-20 balances;
- ERC-721 token IDs and ERC-1155 amounts;
- current approvals for Seaport and collection-specific operators;
- active listings/offers where available;
- recent transfers and sales.

Use both sources correctly:

- OpenSea API/indexer: discovery, metadata, listings, offers, events;
- direct RPC/contract reads: ownership, balances, approvals, receipt state.

If sources disagree, report `indexer_lag` or `chain/indexer_mismatch`; never fabricate a balance. For ERC-721, `balanceOf` alone does not identify token IDs. Use an indexer as a candidate list and verify `ownerOf` or logs directly.

Completion criterion: per-wallet inventory includes source, block/time, token IDs, balances, approvals, and mismatch flags.

## Phase 3: Pricing and profitability

Calculate separately:

- current floor listing;
- cheapest executable listing after filters;
- best offer;
- recent sale median and volume window;
- stale/invalid order flags;
- gas converted using a stated FX source;
- marketplace fee and creator royalty;
- payment-token cost;
- expected net proceeds and break-even price.

Never call a collection floor executable without checking token ID, traits, order validity, expiry, quantity, payment token decimals, conduit approval, fulfillment restrictions, current owner, and token approval.

Use cursor pagination and rate-limit backoff. Cache reads with timestamps, but refresh the selected order immediately before signing or fulfillment.

Completion criterion: price output states timestamp/block, payment token, fees, gas assumption, and whether it is indicative or executable.

## OpenSea operation matrix (verified against current API docs)

### A. Read inventory and balances

- OpenSea API inventory route: `GET /api/v2/chain/{chain}/account/{address}/nfts` with `limit` and cursor/`next` pagination.
- Use `collection` query filtering only as a discovery optimization.
- Direct RPC is authoritative for native/ERC-20 balances, ERC-721 `ownerOf`, ERC-721 `balanceOf`, ERC-1155 `balanceOf`/`balanceOfBatch`, approvals, receipts, and Transfer logs.
- For ERC-721, `balanceOf` gives a count but not token IDs. Combine indexer candidates with `ownerOf` or Transfer-event reconstruction.
- Record `chain`, block/time, source, pagination cursor, and `indexer_lag`/`chain_indexer_mismatch` flags.

### B. Primary mint

OpenSea is not a universal mint authority. There are two valid routes:

1. **OpenSea Drop route:** `POST /api/v2/drops/{slug}/mint` with an API key. It returns ready-to-sign transaction data; the caller signs and broadcasts. The request minter address determines the recipient; the backend chooses the first eligible active stage. It can fail for inactive drop, allowlist, limit, balance, or exhausted supply.
2. **Direct official contract route:** inspect the verified drop/SeaDrop ABI and live phase, build the exact mint call locally, simulate, sign, broadcast, and verify Transfer events/ownership.

Required preflight: canonical slug + contract + chain, phase, price/payment token, quantity limits, allowlist proof, supply, recipient, gas, and wallet balance. Never guess a mint method from a button or slug.

### C. Create listing / list for sale

- Listing endpoint: `POST /api/v2/orders/{chain}/{protocol}/listings` with the current Seaport request schema.
- Prefer `@opensea/sdk`/current Seaport order builder over hand-built calldata.
- Verify owner/token/standard, collection, chain, protocol address, conduit, payment token, amount, start/end, fees, and order nonce.
- Collection approval is a separate on-chain write. A listing itself is normally an off-chain order signature; it is not a sale and does not move the NFT.
- Persist order hash, wallet ID, expiration, and signed/broadcast state without persisting private key or raw signed payload in logs.
- Confirm listing through OpenSea/indexer and re-check current owner. A listing can disappear because of expiry, cancellation, transfer, approval removal, or another sale.

### D. Sell / fulfill a buyer listing

- A buyer selects a current valid listing and calls the listing fulfillment-data endpoint: `POST /api/v2/listings/fulfillment_data` with `fulfiller` and `listing` (`chain`, `hash`, `protocol_address`), optional recipient/units.
- OpenSea returns ordered transaction data/signatures. The buyer simulates, signs, broadcasts, waits for receipt, and verifies NFT ownership plus payment spent.
- Never call a listing “sold” after the seller merely created it. Require fulfillment receipt, Transfer event, seller proceeds, and buyer ownership.

### E. Accept an offer

- Read the best/current offer for the exact NFT or collection, then revalidate owner, token ID/criteria, currency, amount, expiry, order hash, and offer status.
- Call `POST /api/v2/offers/fulfillment_data` with `fulfiller` and `offer` (`chain`, `hash`, `protocol_address`), optional units.
- For trait/collection offers with `identifierOrCriteria == 0`, let OpenSea validate the selected token against criteria; do not invent a Merkle proof.
- Ensure NFT approval to the supported Seaport conduit, simulate returned fulfillment transaction, then broadcast from the seller wallet.
- Verify receipt, NFT transfer away, payment-token balance increase, and fees/royalties. An offer visible in an indexer is not necessarily executable.

### F. Cancel listing/offer

- Off-chain cancel route: `POST /api/v2/orders/chain/{chain}/protocol/{protocol_address}/{order_hash}/cancel` for supported SignedZone orders.
- Some orders require on-chain cancellation. Determine the order type and current protocol behavior first.
- Reconcile order state after cancellation; never assume a failed HTTP response means the order remains active or a successful response means all cached listings are gone.

### G. Sweep/buy

- Fetch exact collection/chain listings, sort by effective cost, filter invalid/expired orders, revalidate selected orders immediately before fulfillment, and use listing fulfillment data.
- Scope max unit price, total budget, slippage, token IDs/traits, destination, and partial-failure policy.
- Serialize nonce-bearing execution per wallet, persist each order/TxHash, and stop on budget/contract/order changes.

### H. Multi-wallet rules

- `solve/read/prepare` can be parallel; signing and nonce-bearing writes are serialized per wallet.
- Isolate cookies/session and signer per wallet.
- Never reuse one wallet's SIWE/session, nonce, approval, allowlist proof, or order nonce for another wallet.
- Maintain per-wallet state: `prepared`, `simulated`, `signed`, `broadcast`, `confirmed`, `unknown_needs_reconciliation`.

### I. Fees and net proceeds

For every sale/offer acceptance compute:

```text
gross consideration
- creator royalty
- marketplace fee
- payment-token transfer cost
- approval/gas cost
= estimated net proceeds
```

Use actual payment-token decimals and current order consideration, not the displayed floor alone. Record whether the quote is indicative or executable and its freshness.

## Phase 4: Primary mint flow

1. Resolve and verify official drop contract and phase.
2. Read live price, max quantity, remaining supply, wallet limit, start/end, allowlist status, and payment token.
3. Dry-run exact mint call with `staticCall` and `estimateGas`.
4. Calculate safe quantity from wallet limit, supply, balance, and gas reserve.
5. Prepare wallets in parallel but serialize transactions per wallet/nonce. Do not reuse one wallet's proof or nonce.
6. At the final confirmation boundary, show wallet, quantity, price, gas ceiling, and maximum spend.
7. Broadcast only after explicit confirmation. Persist TxHash immediately.
8. Wait for receipt, parse token IDs from transfer logs, and verify ownership/balance directly.
9. If a mint fails after broadcast, reconcile receipt and payment/refund before retrying.

Do not promise OpenSea itself can mint an arbitrary collection. If the drop contract or official mint route is unavailable, report the blocker.

## Phase 5: Listing and selling

A listing is an order-signing action even if no transaction is broadcast immediately.

1. Verify owner, token ID, token standard, chain, and collection.
2. Verify order type, marketplace contract/conduit, payment token, quantity, start/end, and expiry.
3. Calculate gross price, marketplace fee, creator fee, gas/approval cost, and net proceeds.
4. Verify approval. Treat an approval transaction as a separate confirmation and write.
5. Use the current OpenSea SDK/Seaport order builder rather than hand-assembling calldata unless the exact protocol version is verified.
6. Show before signing:

```text
wallet, chain, contract, token ID, quantity,
price/payment token, fees, expiry, conduit/operator,
minimum net proceeds, order nonce reference
```

7. Sign only after final confirmation. Persist order hash, expiration, and wallet ID without storing secrets.
8. Verify listing through OpenSea and order validation/read calls where available.
9. For a sale, require fulfillment receipt, proceeds increase, and ownership transfer.

Never list at a guessed currency or unit. `listing created` is not `sold`.

## Phase 6: Buying and sweeping

Separate:

- **Marketplace sweep:** buy multiple cheapest executable listings.
- **Wallet sweep:** consolidate NFTs from source wallets to a destination.

Marketplace sweep:

1. Fetch paginated listings for exact collection/chain.
2. Sort by effective total cost, not displayed floor alone.
3. Apply max unit price, total budget, quantity, trait/ID filters, and slippage.
4. Revalidate each selected order immediately before fulfillment.
5. Simulate each fulfillment. A batch fails closed if any item is invalid unless partial execution is explicitly allowed.
6. Estimate gas for the full batch and reserve gas in each wallet.
7. Execute serially per wallet/nonce or use tested durable nonce allocation.
8. After every receipt, verify ownership and payment spent. Stop if budget, floor, contract, or order validity changes.

Wallet sweep:

1. Build explicit source-wallet/token list from direct ownership checks.
2. Set destination and per-wallet transfer policy explicitly.
3. Verify destination chain and token contract.
4. Estimate gas and leave native balance for the transfer. All-balance means `balance - gas reserve`, never blind full balance.
5. Use correct ERC-721 or ERC-1155 `safeTransferFrom`; simulate first.
6. Broadcast serialized transfers per wallet, persist TxHashes, wait receipts, verify destination balances.
7. Do not sweep listed, escrowed, locked, or held NFTs without explicit inclusion.

Completion criterion: every acquired or transferred token has a confirmed receipt and direct ownership proof at destination.

## Phase 7: Offers, cancellations, and approvals

Treat offers, cancellations, approvals, and conduit changes as write-capable:

- verify order hash, token/collection scope, price, expiry, and counterparty;
- use current SDK/protocol methods;
- distinguish off-chain cancellation from on-chain cancellation;
- track approval scope and expiry; prefer smallest required approval;
- never approve unknown operators from untrusted metadata;
- verify cancellation through the authoritative route.

## Multi-wallet execution architecture

Start with one app, one durable database, and one worker queue:

```text
OpenSea API/RPC readers
        ↓
normalized inventory + order cache
        ↓
validated operation queue
        ↓
per-wallet nonce/side-effect lock
        ↓
signer adapter
        ↓
receipt reconciler
        ↓
confirmed inventory/proceeds ledger
```

Persist:

```text
prepared → simulated → awaiting_confirmation → signed → broadcast → confirmed
                                           ↘ failed_pre_broadcast
broadcast → unknown_needs_reconciliation
```

Exactly one worker owns a wallet/nonce lane. On restart, reload `signed`, `broadcast`, and `unknown_needs_reconciliation`; reconcile before retrying.

## Common pitfalls

1. OpenSea slug used as contract identity: verify contract and chain on-chain.
2. Indexer inventory treated as final: re-read ownership/balance directly.
3. Floor treated as executable: revalidate the specific order.
4. Listing treated as sale: require fulfillment receipt and proceeds/ownership proof.
5. Private key in wallet JSON or worker: keep secrets in approved storage.
6. All wallets implicitly included: use explicit wallet registry and scope.
7. Approval to unknown conduit: verify operator against current protocol.
8. Sweep with no gas reserve: calculate spendable balance first.
9. Batch nonce collision: serialize per wallet or use tested durable allocation.
10. Retry after uncertain broadcast: reconcile nonce, TxHash, receipt, and balances first.
11. Price decimals/royalty omitted: state token decimals and net proceeds.
12. Primary mint confused with marketplace purchase: inspect drop contract and phase.
13. API key/rate limit guessed: load env, paginate/backoff, report errors. Current API routes tested accept `limit` up to 100; using 200 returns HTTP 400.
14. API key only in `opensea.env`; never put it in notes, manifests, or logs.
15. One API key can serve read requests for many wallet addresses. API keys under the same OpenSea account share one rate-limit bucket, so creating 99 extra keys does not multiply capacity.
16. Separate application authentication from wallet identity: wallet-specific REST operations require the API key plus that wallet's wallet JWT/session; on-chain listing/mint/fulfillment still requires the corresponding wallet signer and approval/nonce handling. Do not reuse one wallet JWT as another wallet's identity.
17. Bulk operation partially executes silently: persist per-item result and stop/fail closed according to scope.
18. Transfer destination mistyped: checksum and display it before confirmation.

## Verification checklist

Before read-only reporting:

- [ ] API/RPC source and timestamp recorded.
- [ ] Chain and contract verified.
- [ ] Inventory reconciled against direct on-chain reads.
- [ ] Prices state payment token, decimals, fee assumptions, and freshness.

Before any signature or broadcast:

- [ ] Exact wallets and token IDs scoped.
- [ ] Contract, chain, method, recipient/conduit, amount, and expiry verified.
- [ ] Static call and gas estimate pass.
- [ ] Gas reserve and total budget safe.
- [ ] Human-readable summary shown and explicit confirmation obtained.
- [ ] No secret appears in logs/output.

After any write:

- [ ] TxHash or order hash persisted immediately.
- [ ] Receipt status confirmed.
- [ ] Ownership, balance, proceeds, or order state re-read independently.
- [ ] Partial failures and uncertain broadcasts reconciled.
- [ ] Report distinguishes prepared, signed, broadcast, and confirmed.
