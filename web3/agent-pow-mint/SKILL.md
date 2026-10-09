---
name: agent-pow-mint
description: "Automate agent PoW NFT mints: API puzzles or keccak grind."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [PoW, NFT, Mint, Robinhood, Keccak, Puzzle, LocalSigning]
    related_skills: [hashwood-miner, osnm-z-mint, evm-mint-preflight, drop-eligibility-check]
---

# Agent PoW NFT Mint

Mint NFTs whose gate is proof-of-work solved by an AI agent, on Robinhood
Chain (4663) or similar EVM chains. Two proven protocol families:

1. **API-puzzle style** (AlienNode): backend issues an arithmetic puzzle, you
   solve it, get an unsigned tx, sign LOCALLY, submit the signature.
2. **On-chain keccak grind** (MINECAT): grind `keccak256(seed‖addr‖nonce)` until
   `uint256(hash) < ticketTarget`, submit the nonce, then claim.

What this does NOT do: buy mints, bypass co-signatures, or move private keys
off the local machine. Keys always sign locally.

## When to Use

- Site is "agentic PoW", "proof-of-luck", "mine your NFT", or ships a
  `skill.md` describing puzzle→solve→sign→submit.
- User says "mint harus ikut mining dulu", "free mint tapi claim bayar",
  "auto mint pas buka", or pastes a mint site with a mining phase.
- Any Robinhood 4663 NFT whose contract exposes `submitWork` / `claim`
  instead of a plain `mint()`.

## Prerequisites

- `cast` (Foundry) for RPC calls and broadcast.
- `python3` + `pycryptodome` (`Crypto.Hash.keccak`) for keccak grinding.
- `node` + `ethers` for local signing (install with
  `npm install --prefix /tmp ethers` if missing; run with
  `NODE_PATH=/tmp/node_modules`).
- Wallet mnemonic file `/root/.hermes/.credintial/.springwallet`; derive the
  selected Set key into `/dev/shm` (mode 600), never persist.
- Alchemy key in `/root/.hermes/.env` (`ALCHEMY_API_KEY`).

## How to Run

Read the contract/site first (see Procedure), then pick the path:

```bash
# API-puzzle (AlienNode example)
curl -X POST https://<site>/api/puzzle -H "Content-Type: application/json" -d '{"wallet":"0x…"}'
# solve -> unsignedTx -> sign locally with ethers -> POST /api/submit

# On-chain grind (MINECAT)
python3 scripts/minecat-auto.py --max-mints 3   # run via `terminal` background
```

## Quick Reference

| Protocol | Free part | Paid part | Wallet cap |
|---|---|---|---|
| API puzzle | puzzle+solve+sign | submit broadcast | per site (20) |
| On-chain round PoW | `submitWork(uint64)` (0 value) | `claim()` = mintPriceWei | per contract (5) |

Common contract views: `ticketTarget()`, `luckyTarget()`, `diffTicket()`,
`luckyDivisor()`, `currentRound()`, `roundSeed(uint256)`,
`mintedBy(address)`, `voucher(address)`, `ticketFromRound(address)`,
`mintPriceWei()`.

## Procedure

1. Recon the site: fetch homepage + `skill.md`; extract contract address,
   chain, endpoints, mint price. Verify contract on Blockscout
   (`/api/v2/smart-contracts/<addr>`) — verified source is a strong green flag;
   read `submitWork`/`claim`/puzzle-gate source before signing anything.
2. Confirm the economics BEFORE grinding: "free mint" on the page often means
   mining is free but `claim()` still pays `mintPriceWei`. Compare wallet
   balance against price + gas; abort if short (tell user, don't guess).
3. API-puzzle path: POST `/puzzle` → solve exactly → POST `/solve` → get
   `unsignedTx` → sign locally with ethers (add gas, nonce, type 2) → POST
   `/submit` → verify receipt + `ownerOf`/`balanceOf`.
4. On-chain grind path: read `currentRound()` + `roundSeed(r)` (must be
   non-zero; call `openRound()` if zero — free, mirrors site button). Grind
   `keccak256(seed(32) ‖ addr(20) ‖ nonce(8 BE))` < `ticketTarget()` with
   multiprocessing workers. On hit, re-verify the round did NOT roll before
   submitting the nonce (stale nonce reverts `hash above target`).
5. After a successful `submitWork`: if hash < `luckyTarget()` (and
   `roundMinted < ROUND_CAP`) you hold a voucher → claimable immediately; else
   you hold a ticket claimable from next round (`currentRound >=
   ticketFromRound`). Claim via `claim()` with `value = mintPriceWei`.
6. Stop at the contract wallet cap. Auto-claim only after explicit user
   approval of the paid claim (price shown), or after the user pre-approved
   the flow ("ok mulai").

## Pitfalls

- **Stale nonce across rounds**: a solution found for round N is invalid for
  round N+1 (`hash above target`). Always re-check `currentRound()` before
  `submitWork`.
- **Solution replay**: the same nonce submitted twice reverts
  `solution replayed` (wasted gas). Break the grind loop after one successful
  submit and re-read wallet state.
- **Round open race**: `openRound()` reverts `already open` when another
  miner opened it first — treat as success, read the seed.
- **Don't keep grinding while holding a ticket/voucher**: the deliverable is
  the claim; grind only to earn the next one.
- **"Free mint" is a label, not a price**: always read `mintPriceWei` /
  active stage price on-chain before broadcasting.
- **claim() with wrong value reverts `wrong price`**; read the exact wei.
- Never send the private key to the site API; sign locally only.
- `eth_getLogs` on Alchemy free tier is capped at 10-block ranges — use
  Blockscout `/api/v2` for history instead.

## Verification

```bash
cast call <contract> 'mintedBy(address)(uint256)' <addr> --rpc-url <rpc>
cast call <contract> 'balanceOf(address)(uint256)' <addr> --rpc-url <rpc>
```

Report `confirmed` only with receipt status 1 + owner/balance match.

## References

- `references/aliennode-api-mint.md` — API-puzzle protocol walkthrough
  (endpoints, payloads, local ethers signing, verified mint).
- `references/minecat-round-pow.md` — on-chain round PoW contract mechanics,
  ticket/voucher logic, mining script behavior, verified mints.
- `scripts/minecat-auto.py` — reusable round-PoW miner + claimer (edit
  CONTRACT/ADDR/PK_FILE/RPC per target; invoke through the `terminal` tool).
