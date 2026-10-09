---
name: fifo-drip-sniper
description: Win FIFO drip free-mint races with tuned timing.
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [NFT, Freemint, Drip, Sniper, FIFO, Robinhood]
    related_skills: [free-mint-drip-race, nft-mint-verification, evm-mint-preflight]
---

# FIFO Drip Sniper

Race global-drip free mints on Arbitrum Nitro Orbit chains (Robinhood 4663)
where the sequencer is FIFO by arrival — priority fees buy nothing and the
winner is the first eligible tx in the first block of the boundary second.
Uses timing brackets around the predicted boundary plus an auto-tuner that
walks the centre from where shots actually landed. Proven on RWA FLYWHEEL
BABIES: 284 free NFTs in one run, and a 1-wallet Set 1 win in this session
(fired -120ms, landed sec +0). Does NOT bid gas and does NOT need a mempool
(Arbitrum has no public one).

## When to Use

- A drip mint with `mintFree()` + global `lastFreeMintAt() + mintInterval()`
  is contested and naive poll-then-fire keeps losing
- Need the best shot timing on a FIFO sequencer
- Multi-wallet free-mint farming where each wallet mints once forever
- `free-mint-drip-race` basic loop is not winning

## Prerequisites

- `python3` + `pip install eth-account`
- Funding wallet with RH-Chain ETH (0.0003/wallet is comfortable; burn was
  ~0.00002/wallet, rest sweeps back)
- `~/babies/` working dir; `wallets.json` is `[{address, private_key}]` mode 600
- The contract's selectors (compute or reuse known): `mintFree` `0x8ab53447`,
  `lastFreeMintAt` `0xfca4b80e`, `mintInterval` `0x0e726e6b`, `mintOpen`
  `0x24bbd049`, `remaining` `0x55234ec0`, `freeMinted(address)` `0x389fcf06`

## How to Run

Invoke through the `terminal` tool:

```bash
mkdir -p ~/babies && cp scripts/babies_*.py ~/babies/ && cd ~/babies
python3 babies_gen.py 100                 # or point wallets.json at your sets
# write hub.json with funding key (only key that stays on the machine)
python3 babies_fund.py --go               # fund wallets
BABIES_TARGET=1 python3 babies_sniper.py  # run until 1 win
python3 babies_sweep.py --go              # pull leftover gas to hub
```

## Quick Reference

| Env | Default | Meaning |
|-----|---------|---------|
| `BABIES_RPC` | public RH RPC | own endpoint; paid is steadier not faster |
| `BABIES_ACTIVE` | 4 | wallets firing per window |
| `BABIES_SPREAD` | `-80,-40,0,40` | bracket offsets ms around centre |
| `BABIES_CENTRE` | `-210` | starting centre ms before boundary second |
| `BABIES_TARGET` | 100 | stop after N wins |
| `BABIES_MAXFEE` | 0.05 gwei | keep low; base is ~0.020 |
| `BABIES_MINBAL` | 0.00006 ETH | floor; must stay > 4 × gasLimit × maxFee |
| `BABIES_PER` | — | funding per wallet in ETH |

## Procedure

1. **Read the mechanic on-chain first.** Confirm `mintFree()` value 0,
   `freeMinted(address)` cap (usually 1/wallet forever), `mintOpen`,
   `remaining`, and the live `lastFreeMintAt`/`mintInterval`. Wallet count =
   NFT ceiling: 100 wallets = 100 free NFTs max.
2. **Prepare wallets.** `babies_gen.py N` or reuse existing sets — write
   `wallets.json` with `{address, private_key}` (mode 600). Fund via
   `babies_fund.py --go` (idempotent: skips already-funded and already-minted).
3. **Set gas knobs for thin wallets.** Admission reserves
   `gasLimit × maxFeePerGas` per pending tx, so `BABIES_MINBAL` must exceed
   `4 × 250000 × BABIES_MAXFEE`. On thin wallets use
   `BABIES_MAXFEE=30000000 BABIES_MINBAL=30000000000000`.
4. **Run the sniper.** It fires a bracket of shots around `centre` before each
   boundary second, reads where they landed (block ts vs boundary second),
   and walks `centre` (too early → later; too late → earlier). Don't set
   `BABIES_TUNE=0` — the tuner is what wins.
5. **Verify wins on-chain, not from the log.** The log can over-count (a win
   credited by both receipt check and periodic sync). The real number is
   `balanceOf` / `freeMinted` on the contract.
6. **Sweep leftover gas** back to the hub with `babies_sweep.py --go`.

## Pitfalls

- **Do NOT bid gas.** FIFO sequencer: in a 9s sample, 596 attempts produced 3
  winners, all at 0.001 gwei, while a 1.0-gwei spam army reverted. Tip = waste.
- **No public mempool** on Arbitrum Nitro Orbit — don't look for one.
- **Send BEFORE the boundary, not at it.** Write admission is ~340ms and the
  tx lands 4-5 blocks after head at send time; reads are ~30ms. A perfect
  clock firing on the boundary is permanently ~400ms late and never wins.
- **Block timing:** blocks ~100ms; the first block of chain second `B` appears
  at wall `B+0.35s`. Default centre −210ms; real runs settle around −110ms
  (our Set 1 win fired −120ms).
- **Never fire-and-forget.** An earlier version wrote pre-signed payloads to
  persistent sockets and never read replies; keep-alive closes made `sendall()`
  succeed locally while ~97% of shots went nowhere. Every shot must do a real
  request/response on its own connection, and reconcile against chain nonce,
  never a local counter.
- **The boundary moves every win.** `lastFreeMintAt` is re-read every round —
  never precompute from the clock.
- **`freeMinted` is the ceiling** — a wallet that already won is done forever.
- `BABIES_MINBAL` too high vs `BABIES_MAXFEE` makes wallets idle with most of
  their balance unusable (happened on the real run).

## Verification

```bash
# after a win: freeMinted(wallet) == 1 and balanceOf(wallet) == 1 on-chain
cast call <CA> "freeMinted(address)(uint256)" <wallet> --rpc-url <RPC>
cast call <CA> "balanceOf(address)(uint256)" <wallet> --rpc-url <RPC>
```
