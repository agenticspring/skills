---
name: wallet-fund-sweep
description: Sweep wallet balances fully until none can tx.
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [Wallet, Sweep, Consolidate, Fund, Gas]
    related_skills: [evm-wallet-set-management, fifo-drip-sniper, free-mint-drip-race]
---

# Wallet Fund Sweep

Send wallet balances back to a hub wallet, down to the last wei that can still
pay for a transfer — no fixed buffer left behind. Built for the lesson learned
on BABIES: sweeping with a hard-coded `GAS_BUF` (0.00001) leaves ~$0.02 per
wallet across dozens of wallets, and cast's default max fee silently fails on
thin balances. Uses explicit low gas price so even 0.000007 ETH balances can
tx, and skips only balances below the actual transfer fee.

## When to Use

- User says "balikin dana ke set 1", "kirim semua saldo", "sweep semua wallet"
- Consolidating minted NFTs + ETH dust back to one wallet
- Cascade stops and leftover balances need recovery
- Any batch fund return where leftovers are not acceptable

## Prerequisites

- `cast` (Foundry) — `command -v cast || curl -L https://foundry.paradigm.xyz | bash`
- Alchemy RPC in `/root/.hermes/.env` (`ALCHEMY_API_KEY`)
- Wallet source: `/root/.hermes/.credintial/.springwallet` (mode 600)
- `eth_utils` for selector computation (or hardcode `0x2f745c59` tokenOfOwnerByIndex,
  `0x42842e0e` safeTransferFrom, `0x70a08231` balanceOf)

## How to Run

Invoke through the `terminal` tool:

```bash
# ETH dust sweep only
python3 scripts/dust-sweep.py <END> <START>

# NFT + ETH consolidate (transfer tokens then sweep)
python3 scripts/consolidate-nfts.py <END>
```

Both read balances live, derive keys ephemerally from `.springwallet`, and
verify receipts before reporting.

## Quick Reference

| Value | Meaning |
|---|---|
| `--gas-price 0x50000000` (~0.021 gwei) | explicit low gas price — cast default max fee fails on thin balances |
| `KEEP = 21000 * gas_price * 1.15` | only the real transfer fee, minimum 0.0000012 ETH |
| `MINBAL 0.00006` | sniper floor (60,000,000,000,000 wei) |
| skip rule | `balance <= KEEP` → cannot tx, keep (that IS "sampai ga bisa tx") |
| NFT transfer | `safeTransferFrom(owner, target, tokenId)` via `cast send --data` |

## Procedure

1. **Read balances for every wallet** 2..END via `eth_getBalance`; derive
   addresses ephemerally (never print PK/mnemonic).
2. **NFTs first** (when consolidating): for each wallet, list tokens with
   `tokenOfOwnerByIndex(address, i)` until it reverts; send
   `safeTransferFrom(owner, TARGET, id)` per token via `cast send --data`
   with explicit `--gas-price`.
3. **Sweep ETH**: `send = balance - KEEP` where
   `KEEP = 21000 * live_base_fee * 1.15` (min 0.0000012). Always pass
   `--gas-price` explicitly — without it cast estimates a max fee that
   reverts `insufficient funds for transfer` / `gas required exceeds
   allowance` on balances under ~0.00001 ETH.
4. **Skip only what truly can't tx**: `balance <= KEEP` → log and keep.
   That residual is the intended endpoint, not a bug.
5. **Verify**: re-read all balances; residual across N wallets should be
   `N * ~0.00000008 ETH` (atom dust below transfer fee) and hub balance
   increased by the swept sum.

## Pitfalls

- **Never use a fixed GAS_BUF** (e.g. 0.00001) per wallet when the instruction
  is "kirim tanpa sisa" — over 20+ wallets that silently leaves $0.02+ each.
- **cast default max fee fails on thin balances** — always pass explicit
  `--gas-price` (~0.021 gwei works on Robinhood where base is ~0.02 gwei).
  This also bites FUNDING transfers from a hub (e.g. 0.0017 ETH balance
  sending 0.00085 reverts "insufficient funds" without it).
- `gas required exceeds allowance (N)` where N < 21000 = balance can only
  cover part of the transfer; lower the gas price or accept the dust.
- After an NFT transfer, a wallet's residual ETH may drop below the sweep
  threshold — that's fine, the NFT moved (that's the priority).
- `tokensOfOwner` may not exist; use `tokenOfOwnerByIndex` (ERC721 enumerable).
- Blockscout fee values are reserved (gasLimit × maxFee), not actual; actual
  fee = `gasUsed × effectiveGasPrice` (observed ~0.00000057 ETH/revert on
  Robinhood).
- Nonce: use `eth_getTransactionCount(addr, 'pending')` per broadcast; the
  sniper/cascade may have left pending txs.
- Robinhood FCFS: base fee + 10% is enough; priority tip buys nothing.

## Verification

```bash
# residual should be atom dust only (~0.00000008 ETH/wallet, below 0.0000005 fee)
python3 - <<'PY'
import json, os, urllib.request, subprocess, tempfile
from pathlib import Path
# derive all addresses, sum eth_getBalance for Set2..END
# expect total < 0.000003 ETH and hub == previous + swept sum
PY
```
