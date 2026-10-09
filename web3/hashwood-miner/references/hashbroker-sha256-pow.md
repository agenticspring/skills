# HashBroker — SHA-256 PoW drop on Robinhood Chain (2026-09-12)

Sibling to Hashwood: same chain, same "fair-launch PoW mint" shape, **different hash**.
Free mint (`mintPrice() = 0`), supply 4444, 100% on-chain SVG. Site: `hashbroker.fun`.

## Contract surface

| Item | Value |
|---|---|
| Mining/NFT | `0x4272D6f51771839F596082eF48fa84D35239Bab3` (NOT verified — no ABI/source; 7753 bytes) |
| Staking | `0xE2828077B67aAff31816281e1A64d0453959e94` |
| `totalSupply()` | `0x18160ddd` |
| `mintPrice()` | `0x6817c76c` |
| `challenge()` | `0xd2ef7398` (bytes32, global — one value for everyone) |
| `currentDifficulty()` | `0x5c062d6c` (leading-zero **bits** required) |
| `mine(uint256,bytes32)` | `0xe43e322c` |
| calldata layout | selector + nonce as 32-byte BE word + challenge 32 bytes |
| observed mint gas | 124,060 gas, effectiveGasPrice ~0.0956 gwei (~$0.03–0.05) |

Site config (`/config.js`) also exposes: `CHAIN_ID 4663`, `STAKE_ACTIVATION_SUPPLY 1000`,
MAX_SUPPLY 4444, and a reward-token list (MANCER/PONS/NVDA/AMZN/AAPL/STONKBROKER/ZZZ/CASHCAT,
all still `0x0` at recon time).

## Verified preimage (3/3 successful mints matched)

```
msg = addr(20) ‖ 0x00*24 ‖ nonceHi(4, BE) ‖ nonceLo(4, BE) ‖ challenge[0:12] ‖ challenge[12:32]
accept iff leading_zero_bits(sha256(msg)) >= currentDifficulty
```

- Total 84 bytes = exactly 2 SHA-256 blocks; **block 2 is constant** for a given challenge
  (challenge[12:32] + `0x80` pad + 672-bit length).
- `addr` is `msg.sender` — not supplied in calldata. Proofs are wallet-bound.
- `nonceHi` is written **first** in the byte stream (high 32 bits at offset 44).
- Cross-check in Python before trusting a C implementation:
  `sha256` over that layout for a real (addr, challenge, nonce) triple must reproduce the
  on-chain winner's digest.

Reverse path that produced this: read the site's `miner.js` (WGSL/WebGPU kernel) for the
digest layout, then confirm against real successful `mine` transactions pulled from the
explorer API. Correctness is provable — don't ship a miner without that check.

## Measured performance

| Machine | CPU | SHA-NI | 1 core | 6 cores |
|---|---|---|---|---|
| `empero` (82.39.206.183) | Xeon Gold 6138, 4c | ❌ | 0.97 MH/s | 3.93 MH/s |
| `vmi3236372` (<REDACTED>) | AMD EPYC, 6c | ✅ | 9.45 MH/s | **~55 MH/s** |

- `openssl speed sha256` 64-byte column: 52.5 MB/s (no SHA-NI) vs 179 MB/s (SHA-NI).
- `SHA256_Transform` loop: 10.11 MH/s/core vs 8.05 via Init/Update/Final (25% better).
- 55 MH/s ≈ 1.21 GB/s of SHA-256 block throughput ≈ 86% of that CPU's measured SHA-NI
  bulk rate (1.4 GB/s) — near ceiling, little headroom left by hand-tuning.

## Expectation math (use this shape, not a guess)

```
our hashes per win   = 2^difficulty
our seconds per win  = 2^difficulty / our_hashrate
our share            = our_hashrate / (2^difficulty / mint_interval)
expected wins        = our_share * remaining_supply
```

Observed at recon (difficulty 41, supply 67, ~40s–2.5min mint interval, 55 MH/s):
our ~11h per proof → share ≈ 0.1–0.4% → **~5–20 mints over the remaining run**.
State plainly that difficulty ratchets up with supply, so this degrades over time.

## Deployed bot layout (VPS <REDACTED>)

```bash
/root/.hb/
  hb_mine      # C SHA-NI miner (6 threads, ~55 MH/s)
  hb_mine.c    # source
  hb_bot.py    # supervisor: read challenge/difficulty -> mine chunks -> simulate -> submit
  hb_ctl.sh    # start | stop | status | watchdog
  pk           # wallet private key, chmod 600   (never print)
  bot.log      # bot's own log (run stdout to /dev/null)
  state.json   # rolling stats: chunks, hashes, best_bits, wins, submits, errors
  watchdog.log
```

- cron: `*/5 * * * * /root/.hb/hb_ctl.sh watchdog` (restarts the `screen` session if dead)
- monitor: `ssh root@<REDACTED> '/root/.hb/hb_ctl.sh status'`
- mining chunk is short (5s) so the supervisor notices challenge rotation quickly; duty
  cycle stayed ~98% at that size, so don't lengthen it without measuring.

## Free validation of the submit path

```bash
# the exact mint calldata of a real successful mint, replayed one block earlier:
cast call $CA 0xe43e322c<nonce32><challenge32> --from <minter> --block <mint_block-1> --rpc-url $RPC
#   -> SUCCEEDS  => selector + argument encoding are correct
cast call $CA <same> --from <minter> --rpc-url $RPC
#   -> reverts "execution reverted, data: 0xaa2bf635" once the challenge rotated
```

Do this before running any live submitter. It costs nothing and catches encoding errors
that would otherwise only surface as a failed mint hours later.

## Pitfalls hit during this build

1. `/dev/shm/*.pk` was gone (tmpfs cleared on reboot) → re-derived the key from
   `/root/.hermes/.credintial/.springwallet` and verified the address matched.
2. `pkill -f hb_bot.py` issued over SSH **matched its own remote command line** and killed
   the session mid-command (empty output, bot left stopped). Fixed with the bracket trick
   `pkill -f "[h]b_bot.py"` and by wrapping control in `hb_ctl.sh`.
3. Bot logged to its own file *and* had stdout redirected there → every line duplicated.
4. A failed proof submission showed up as 37 leading-zero bits and still reverted — the
   discriminator is the challenge, not the bit count. Always re-read `challenge()`
   immediately before sending and skip if it moved.
5. Wallet needs only gas: the mint is free, so a wrong/failed submit costs gas, not price.
   Fund ~$1–5 of RH ETH before starting (124k gas ≈ $0.03–0.05 per mint; $1 ≈ ~21 mints).
