---
name: web3-freemint-batch-execution
description: Use for puzzle-based NFT freemint batches and claim races.
version: 1.0.0
author: spring
metadata:
  hermes:
    tags: [web3, nft, freemint, batch, puzzle, transaction-safety]
---

# Web3 Free-Mint Batch Execution

Use for public free-mint collections where claiming requires solving a published puzzle, checking an on-chain answer hash, and racing other claimants.

## Workflow

1. Verify official repository, contract, chain ID, RPC, and corpus fingerprint.
2. Separate preparation from broadcast. Scan/solve/hash-check locally; serialize irreversible execution per funded wallet unless safe nonce management is explicitly tested.
3. Start with one funded wallet. Do not report 100 funded wallets because 100 key files exist. Gas distribution is a separate on-chain action.
4. Validate each final answer against the published hash before spending gas.
5. Check live ownership immediately before the official mint tool, but treat `ownerOf()` as race-prone, never as a reservation.
6. Prefer the project’s official miner. Do not rewrite commit/reveal, nonce, waiting, or receipt logic without tests.
7. Record every broadcast hash immediately. Confirm only after mined receipt and independent owner/token verification.
8. On a losing race, discard the candidate and continue with the next validated candidate; never blindly retry.

## Speed and safety

Parallelize local solving and bounded read-only ownership probes. Do not parallelize dependent puzzle trials or nonce-bearing broadcasts from one wallet. Public RPC views can lag; classify by receipt and re-read ownership from an authoritative endpoint.

## Reporting

Separate `prepared` (hash matched), `attempted` (TxHash obtained), `confirmed` (receipt plus owner verification), and `failed` (exact reason). Never claim a batch is underway when only a scanner/delegation/script ran. Never fabricate TxHashes.

## Pitfalls

- A valid answer does not reserve an NFT.
- `ownerOf()` becomes stale during races.
- Total minted changes during preparation.
- One funded wallet differs from 100 key files.
- Forwarding all balance can fail if transfer gas is not reserved.
- Pin commands to the verified project directory.
- Sub-agent claims never prove external side effects; verify directly.

## Verification checklist

Before final reporting, verify chain ID, contract, wallet balance, answer hash, TxHash, receipt, owner/balance, post-action balance, and confirmed mint count.

See `references/inference-angels.md` for the collection-specific puzzle schema and validated local checks.

## Global drip-timer mints (time-gated FCFS)

Some free mints (e.g. Fablings kiln items) drip **one global slot per interval** —
`lastFreeMintAt` resets when ANY wallet wins, so `mintFree()` reverts
`DripNotReady()` unless the tx lands inside the open window. This is a global
race, NOT a per-wallet cooldown. Strategy:

1. Read `lastFreeMintAt()` + `mintInterval()` on-chain; fire when
   `(last + interval) <= block.timestamp`; poll at ~150ms near the boundary.
2. On `DripNotReady` revert, retry immediately (next window, not backoff).
   Expect several REVERTED attempts per success (observed 21 attempts / 10 mints).
3. Track wallet cap via `freeMinted(wallet)` vs `FREE_PER_WALLET()`; stop cleanly
   at cap. `freeLeft(...)` may not exist — use `freeMinted` + constant.
4. Compute selectors from the ABI with keccak — do NOT hardcode guessed
   selectors (wrong `lastFreeMintAt` selector made the loop wait forever).

Worked run: `references/fablings-drip-race.md` (contract, selectors, race loop,
cascade funding, NFT consolidation, dust sweep).

## Multi-wallet cascade + consolidation (worked, 2026-08-19)

When farming one free mint across many wallets with a single funded source:

1. **Fund → mint → cascade**: Set1 sends ~0.001 ETH to Set2; Set2 mints its cap;
   Set2 sends its remaining balance (minus a gas reserve) to Set3; repeat. Keep
   `GAS_RESERVE ≈ 0.00005` so the transfer itself always has gas.
2. **Consolidate NFTs after minting**: `safeTransferFrom(from,to,id)` calldata
   is `0x42842e0e + from + to + id` — **from = the wallet that owns the token
   (Set N), to = Set 1**. Swapping from/to reverts `ERC721IncorrectOwner`.
   Fund ~0.00005 ETH gas into each source wallet before transferring its 10
   tokens, then sweep the dust back.
3. **Dust sweep at minimum fee**: Robinhood is FCFS-sequenced, so no priority
   tip is needed — use `--gas-price = pending baseFee * 1.10` and retry on
   `max fee per gas less than block base fee` (base fee drifts between read and
   submit; bump and re-send, up to 3 attempts). A plain ETH transfer uses 21,000
   gas; send `balance - fee`, keep nothing.
4. **Wallet file parsing**: `.springwallet` contains `#` header comment lines
   that are exactly 12 words and look like mnemonics, plus `Set N` label lines.
   Filter: skip lines starting with `#` or `Set` before treating a line as a
   mnemonic — otherwise you derive the wrong key or empty PK.
5. **`cast send --value`** needs a hex literal with `0x` prefix
   (`format(amount,'#x')`), not bare hex — bare hex errors out in the CLI.

Detail + txs: `references/fablings-drip-race.md`.

## FIFO drip sniper (timing-tuned FCFS, worked 2026-08-21)

For contested global-drip mints where naive poll-then-fire loses (RWA FLYWHEEL
BABIES: `mintFree` `0x8ab53447`, 1 free/wallet forever, `lastFreeMintAt` +
`mintInterval` global gate, Arbitrum Nitro Orbit FIFO sequencer):

1. **Fee = waste**: FIFO by arrival — winners paid 0.001 gwei while a 1.0-gwei
   spam army reverted. No public mempool exists on Arbitrum; don't bid gas.
2. **Send BEFORE the boundary, not at it**: `eth_sendRawTransaction` admission
   ~340ms, tx lands 4-5 blocks after head at send time (reads ~30ms). A
   perfect clock firing *on* the boundary is permanently ~400ms late.
3. **Bracket + auto-tuner**: fire 4 shots around `centre` (default −210ms),
   read where they landed (block ts vs boundary second), walk centre. Real
   runs settle ≈ −110ms (Set 1 win fired −120ms, landed sec +0). First block
   of chain second B appears at wall B+0.35s.
4. **Never fire-and-forget**: each shot needs a real request/response on its
   own connection; keep-alive closes made `sendall()` succeed locally while
   ~97% of shots went nowhere. Reconcile against chain nonce, never a local
   counter. Win log over-counts — verify `freeMinted`/`balanceOf` on-chain.
5. **Gas reservation**: admission reserves `gasLimit × maxFeePerGas` per
   pending tx, so `MINBAL` must exceed `4 × 250000 × maxFee`. Thin-wallet
   recipe: `MAXFEE=30000000 MINBAL=30000000000000`.
6. **Cascade gas math**: ~0.00002 ETH/win + ~0.0000005 ETH/transfer hop.
   0.00085 ETH funds ~40-45 wallets; a full 100-wallet run needs ~0.0025 ETH
   total gas. Re-runs are idempotent — skip wallets with `freeMinted == 1`.

## Pitfalls

- **Public Robinhood RPC can 403 from a VPS** (`rpc.mainnet.chain.robinhood.com`).
  Use the Alchemy endpoint (`ALCHEMY_API_KEY` from `/root/.hermes/.env`),
  send a browser `user-agent` header, and retry 403s once or twice.

## Verifying an arbitrary site is a REAL free mint

Before paying gas, prove "free" = `0 wei` on-chain, never trust the page label
(Hoodilio, Market Arcana, Robin Gorillas all lied). Recipe:
`references/free-mint-site-verification.md`.

## Signed whitelist-seat claims (personal_sign + /join)

Some free-mint drops gate their whitelist behind a signature-verified Cloudflare
Worker collector: build the site's exact message, `personal_sign` locally,
POST `{message, signature}` to `<endpoint>/join`. Check `<endpoint>/count`
first — the cap (e.g. 500 seats) fills fast and later wallets 409 mid-batch.
Worked run: `references/signed-whitelist-seat-claim.md`.
