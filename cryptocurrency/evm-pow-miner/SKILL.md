---
name: evm-pow-miner
description: Set up, optimize, and run a keccak256 Proof-of-Work miner for EIP-918 style tokens on EVM chains (e.g. Hashwood, 0xBitcoin family). Covers VPS prep, Node.js reference miner, Python C-accelerated miner, and screen management.
version: 1.0.0
---

# EVM PoW Miner Setup

## Goal
Deploy a keccak256 PoW miner on a VPS to mine EIP-918 style tokens (e.g. HASH on Robinhood Chain).

## Quick comparison

| Miner | Hashrate | Notes |
|-------|----------|-------|
| JS reference (Node.js) | ~2 KHz | Pure JS, intentionally slow |
| Python + pycryptodome | ~75 KHz (6 cores) | C-accelerated keccak via pycryptodome |
| GPU (CUDA) | MHz–GHz | Needs dedicated GPU, not tested here |

## Setup steps

### 1. Install dependencies
```bash
# Node.js 20+
curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt install -y nodejs

# Foundry (cast for TX submission)
curl -L https://foundry.paradigm.xyz | bash && source ~/.bashrc && foundryup

# Python keccak (C-accelerated)
pip3 install pycryptodome --break-system-packages
```

### 2. Download reference miner
```bash
mkdir /root/hashwood-miner && cd /root/hashwood-miner
curl -O https://hashwood.xyz/miner/miner.mjs
curl -O https://hashwood.xyz/miner/keccak.mjs
```

### 3. Create `.env` with burner private key
```bash
echo -n "0x<your-private-key>" > .env
chmod 600 .env
```

### 4. Deploy Python C-accelerated miner
Place `hashminer.py` (reference below) and `run_miner.py` from `references/` into the miner directory.

### 5. Start in screen
```bash
screen -dmS hashwood python3 run_miner.py
```

### 6. Monitor
```bash
screen -S hashwood -X hardcopy /tmp/out.txt && cat /tmp/out.txt   # last output
tail -f miner.log                                                     # if logging
cast balance <address> --rpc-url <RPC>                                # check ETH
cast call <contract> "balanceOf(address)(uint256)" <addr> --rpc-url <RPC>  # check token
```

## Reversing an UNKNOWN PoW mint (before writing any miner)

PoW mints are often free (0 ETH) with an **unverified** contract, so the algorithm
is not in an ABI — but the web frontend ships it in plain JS. Recover it, then
prove your implementation against real on-chain wins before mining a single nonce.

1. **Get the config + kernel from the site.** Fetch the page, then the JS it loads.
   Look for a `config.js` (contract address, chain id, RPC, selectors) and a
   `miner.js`/worker (the hash kernel).
2. **Extract selectors** from the frontend constant table, e.g. `totalSupply`,
   `mintPrice`, `challenge`, `currentDifficulty`, `mine`. Confirm the mint
   signature with `cast 4byte <selector>` or `cast sig "mine(uint256,bytes32)"`.
3. **Read the kernel to get the exact preimage.** Note byte offsets, endianness,
   and which fields are fixed vs iterated (usually only the nonce).
4. **Verify against real transactions — mandatory.** Pull the contract's tx list
   from the explorer API and take a few **status=ok** mints. Recompute the hash
   from (sender, submitted nonce, submitted challenge) and check it meets the
   target. If your formula reproduces the winners, the reversal is confirmed.
5. **Cross-check a failed tx.** A tx that reverted with an otherwise-valid nonce
   usually submitted a **stale challenge** (the challenge is global and rotates on
   every mint) — not a weak hash. Don't "fix" your formula over it.
6. **Benchmark your own hashrate, then do the feasibility math** (see below).

### Feasibility math (do this instead of guessing)

```
expected_hashes_per_proof = 2^difficulty_bits
your_time_per_proof       = 2^difficulty / your_hashrate
win_chance_per_challenge  = window_seconds / your_time_per_proof
expected_total_wins       ≈ your_hashrate * total_remaining_seconds / 2^difficulty
```

Measure the network rate from the mint cadence: `network_H/s ≈ 2^difficulty / median_gap_seconds`.
If your share is far below ~1%, say so plainly and price out a GPU instead of
burning days of CPU.

### SHA-256 family vs keccak family

Not every PoW mint is EIP-918/keccak. Some (e.g. HashBroker on Robinhood Chain)
use **single SHA-256 over a custom address-bound preimage** with a
leading-zero-**bits** target. Differences that matter:

| | keccak / EIP-918 | SHA-256 custom |
|---|---|---|
| Hash | `Crypto.Hash.keccak`, never `hashlib.sha3_256` | `hashlib.sha256` is correct |
| Preimage | `challenge ‖ address ‖ nonce` | as recovered — often `address ‖ zeros ‖ nonce ‖ challenge` |
| Binding | varies | may bind `msg.sender` (so **each wallet mines its own proof**) |
| Target | `hash <= miningTarget()` | often `leading_zero_bits >= currentDifficulty` |
| Difficulty | usually fixed per era | may **rise with supply** — the early window is the cheap one |

See `references/sha256-pow-mint-recon.md` for a fully worked case, and
`scripts/verify_pow_formula.py` to reproduce/validate a formula from on-chain txs.

## Pitfalls

- **Burner wallet only** — miner needs private key to sign. Never use a real wallet.
- **One mint per block** — second TX in same block reverts. Challenge rotates ~3s.
- **CPU mining is NOT competitive vs GPU** — expect 1-2 mints max before GPU miners dominate.
- **PYTHON HASHER**: The keccak256 used by Ethereum is NOT SHA3-256 (different padding). Use `Crypto.Hash.keccak` from pycryptodome, NOT `hashlib.sha3_256`.
- **RPC rate limits** — public RPCs (`rpc.mainnet.chain.robinhood.com`) can time out under load. Add private RPC fallback.
- **cast send timing** — `cast send` can be slow. The gap between finding a solution and submitting TX lets GPU miners win the block.
- **cast output has `[scientific]` suffix** — target returned as `"2826... [2.826e73]"` — must `.split()[0]`.
- **`.env` newlines** — read `.env` with `.strip()` or `tr -d '\n\r'` to avoid corrupted PK/address in cast calls.
- **Global challenge rotates on every mint** — a proof is only valid for the challenge
  that was live when you found it. Submit immediately or you burn gas on a revert.
- **`challenge` is usually NOT predictable** — test `keccak(blockhash)`, `prevRandao`,
  `prevChallenge`, `nonce`, `sender` before believing in a pre-mine attack. If none
  match, there is no precompute shortcut; raw hashrate is the only lever.
- **CPU benchmark reality check** — a cloud vCPU without SHA-NI does ~1 MH/s per core
  for single SHA-256 (~4 MH/s on 4 cores). A GPU does GH/s. If the implied network
  rate is GH/s, a CPU miner will not win regardless of tuning — report the number
  instead of running it for days.
- **Always self-check the miner against a known winning tx** before a long run — one
  wrong byte offset silently produces zero wins and looks like "bad luck".

## Resources
- `references/hashminer.py` — standalone Python miner (takes challenge, address, target, threads)
- `references/run_miner.py` — full wrapper: fetch work → mine → submit → loop
- `references/sha256-pow-mint-recon.md` — worked SHA-256 PoW case: reversal, on-chain validation, benchmark & feasibility
- `scripts/verify_pow_formula.py` — reproduce/validate a PoW hash layout against real explorer txs
- `templates/c_sha256_pow_miner.c` — multithreaded C SHA-256 miner with precomputed schedule + self-check
- Contract: `0xD69be8d7c6d0e8216Dc2C151834E4150313260Cc` (Robinhood Chain, chain ID 4663)
- RPC: `https://rpc.mainnet.chain.robinhood.com`
- Explorer: `https://robinhoodchain.blockscout.com`
