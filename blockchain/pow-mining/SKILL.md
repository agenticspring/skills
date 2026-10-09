---
name: pow-mining
description: "PoW mining and minting on EVM chains: keccak and SHA-256. Check winnability, build miners, deploy supervised."
version: 1.1.0
author: spring
license: MIT
platforms: [linux]
---

# PoW Mining — EIP-918 style (Hashwood, 0xBitcoin family)

## Goal
Mine a fair-launch ERC-20 token on an EVM chain using keccak256 proof-of-work.
Winning nonce is submitted as a `mint(uint256 nonce, bytes32 digest)` transaction.
The user's address is baked into the hash — nobody can steal your nonce.

## Contract pattern
```
challenge = contract.challengeNumber()  // bytes32, rotates per successful mint
target    = contract.miningTarget()      // uint256, difficulty target
input     = keccak256(challenge ‖ address ‖ nonce)  // 84 bytes total
```

Win condition: `uint256(input_hash) ≤ target`

## Pre-flight: is this PoW race winnable? (BEFORE building any miner)

Three cheap steps decide whether mining is worth doing at all. ~15 minutes, and they save
whole sessions of wasted CPU. Run them in order.

1. **Recover the exact preimage from the site's own miner.** The web UI *is* the spec:
   fetch the page, then `config.js` (contract address, chain id, supply, mint price) and
   `app.js` (function selectors, calldata assembly) and `miner.js` / worker (the hash layout).
   Selectors appear as literal hex in `app.js` — e.g. `mine: "0xe43e322c"`,
   `challenge: "0xd2ef7398"`, `currentDifficulty: "0x5c062d6c"`.
2. **Verify your reconstruction against REAL successful transactions.** Never trust your
   reading of obfuscated JS. Pull winning txs from the explorer, recompute the digest
   locally, and confirm it satisfies the contract's condition. 3/3 matches = formula nailed.
   This is how you reach 100% confidence on a contract that is **not verified** (no source,
   no ABI — bytecode only, which is the norm for these).
3. **Compute the implied network hashrate and compare it to yours.**

```
implied_network_H_s  =  2^difficulty / observed_seconds_between_wins
your_share           =  your_H_s / implied_network_H_s
expected_mints_to_win = 1 / your_share
```

Measure `observed_seconds_between_wins` as the **median gap between successful mints** in the
explorer tx list (exclude failed txs — they distort it). Read `difficulty` live, then sample it
at **historical blocks** (`eth_call` with a block-number param) to see the trend: rising
difficulty means the easy window has already closed.

**Also test for a precompute shortcut before concluding.** If the next challenge is derivable
from data you already hold, you can pre-mine proofs offline and submit instantly. Test the
obvious candidates (all-miss = fully unpredictable, hashrate is the only lever):

```
keccak/sha(blockhash) · (prevRandao) · (prevChallenge) · (previousNonce) · (sender)
keccak(prevChallenge ‖ blockhash) · keccak(blockhash ‖ prevChallenge) · keccak(ch ‖ nonce)
```

### Reading the verdict
- `your_share` ≥ ~5% → competitive, build the miner.
- `your_share` < ~1% → you lose every race while the big miners are active. Rent a GPU,
  monitor for a quiet window (difficulty *falls* when miners leave — sample over time), or skip.
- Check **which failure mode** the race is, because they need different fixes:
  a shared rotating challenge on a ~30 s cycle is a pure **hashrate** race; a 1-mint-per-1-second-block
  race is a **latency** race (public RPC ~100 ms loses to a local node every time, no matter your hashrate).
- Beware the sunk-cost trap: "gas is cheap so just keep trying" is false comfort when
  `your_share` is 0.1% — you are buying lottery tickets at 1000:1.

### Validate the submit path for FREE — you do not need to win first

Two `eth_call` tricks prove your calldata and your assumptions without spending a wei. Run
both before letting a bot loose, because they are the difference between "found a proof and
it reverted" and "found a proof and it minted".

1. **Replay a historical winning tx.** Take a known successful mint, rebuild its calldata,
   and call it at the block *just before* it was mined:

```bash
cast call $CA 0x<selector><nonce><challenge> --from <original_minter> --block <mint_block - 1> --rpc-url $RPC
# succeeds  → selector + argument encoding are exactly right
# same call at --latest reverts → correct: the challenge moved on
```

2. **Probe the real difficulty floor.** Mine a deliberately easy low-bit proof, then
   `eth_call` it at the live challenge. A revert proves the advertised difficulty is enforced
   for *every* wallet (no fresh-wallet discount, no per-address allowance) — i.e. there is no
   shortcut and hashrate is genuinely the only lever.

Decode whichever revert you get; it names the failing check:

```
https://api.openchain.xyz/signature-database/v1/lookup?function=0x<selector>
```

Observed on HashBroker (contract unverified, so this was the only way to learn them):

| selector | error | meaning |
|---|---|---|
| `0xaa2bf635` | `StaleChallenge()` | challenge rotated — the proof is dead, resubmitting is pure gas burn |
| `0x09bde339` | `InvalidProof()` | not enough leading zero bits |

**Gate every submit on a free `eth_call` simulation first.** It converts a $0.03 revert into $0.

**Worked example — HashBroker (2026-09-12):** free-mint SHA-256 PoW NFT, Robinhood Chain.
Difficulty rose 35→38 with supply; median win gap ~27 s ⇒ implied ~2–9 GH/s (GPU rigs).
4-core VPS, no GPU, no SHA-NI ⇒ ~3 MH/s ⇒ share ~0.1% ⇒ **not viable**. Full transcript:
`references/hashbroker-sha256-pow-nft.md`.

## Non-keccak variant: SHA-256 PoW NFTs

Not every PoW mint is EIP-918 keccak. HashBroker-style contracts use SHA-256 over a
**different layout** — never assume the keccak template above:

```
msg = address(20) ‖ zeros(24) ‖ nonceHi(4 BE) ‖ nonceLo(4 BE) ‖ challenge[0:12] ‖ challenge[12:32]
win when sha256(msg) has >= difficulty LEADING ZERO BITS
```

Differences that matter:
- Address comes **first**, and is `msg.sender` (still bound to the minter — nobody can steal a proof).
- The nonce is split into **two big-endian u32 words, `nonceHi` then `nonceLo`**; the uint256 in
  calldata is `(nonceHi << 32) | nonceLo`.
- Difficulty is **leading zero bits**, not a numeric target — count them from the digest's MSB
  (`countLeadingZeros`), never by integer comparison.
- The **last SHA-256 block is constant per challenge** (padding + bit length are fixed), so only the
  first block varies — exploit that in a custom kernel.
- Loop over difficulty/supply history before mining: these schemes are usually **adaptive and rising**.
- The web miner may be a WebGPU compute shader — read the WGSL `digest()`/`setJob()` to recover
  the exact byte order rather than guessing.

## Stack selection (performance ladder)

| Stack | Hashrate (6-core VPS) | Setup complexity | Notes |
|---|---|---|---|
| Node.js (reference) | ~2 KHz | Zero (3 files) | "This is a correctness reference, not a performance miner" — from the dev |
| Python + pycryptodome | ~75 KHz | Low (pip install) | C-accelerated keccak256, multiprocessing. 35x over Node.js |
| **Go + go-ethereum** | **~800 KHz–1.5 MHz** | Medium (go build) | Compiled native, goroutines, single binary. **~500x over Node.js, ~10-20x over Python**. Direct RPC, no subprocess. Preferred for serious CPU mining. |
| C + OpenSSL | ~Mh+ range | Medium (compile) | Need working keccak256 EVP or custom kernel |
| CUDA (GPU) | GH/s range | High | RTX 4090/5090. Port inner loop to CUDA keccak kernel |

**Go is the sweet spot for serious CPU mining** — 1 MHz on 6 cores, single binary, persistent RPC, minimal TX latency (~200μs solution-to-TX-sent). Python is fine for initial testing.

### SHA-256 PoW: the hardware lever is SHA-NI, not core count

For SHA-256-based PoW (the non-keccak variant) the whole game is whether the CPU has the
**SHA extensions** (`sha_ni`), not how many cores it has. Same 84-byte / 2-block workload:

| CPU | cores | `sha_ni` | per core | total |
|---|---|---|---|---|
| Intel Xeon Gold 6138 (Skylake) | 4 | ❌ | 0.97 MH/s | 3.93 MH/s |
| AMD EPYC (Zen) | 6 | ✅ | 9.45–10.1 MH/s | **51–57 MH/s** |

≈8.3x per core. Going 4→6 cores on a non-SHA-NI CPU buys +50%, which changes no outcome;
one SHA-NI core buys +800%. **Check before renting/buying anything:**

```bash
grep -o sha_ni /proc/cpuinfo | head -1     # empty output = no SHA extensions
```

- ✅ AMD EPYC / Ryzen (every generation), Intel Ice Lake and newer (Xeon Scalable gen 3+)
- ❌ Xeon Scalable gen 1–2 (Skylake/Cascade Lake) — this is the common trap on cheap VPS

Two ways to reach the SHA-NI path. SHA-NI already runs at ~86–92% of the theoretical
ceiling, so there is almost no headroom to chase — pick the simpler one:

1. `openssl/sha.h` `SHA256_Init/Update/Final` — trivial, but per-call overhead costs ~20%
   (`openssl speed -seconds 3 sha256` at 64 B is a good proxy for the ceiling).
2. **`SHA256_Transform`** — one block per call, no Init/Final overhead ⇒ ~25% faster
   (10.11 MH/s/core measured). Link `-lcrypto`, compile `-DOPENSSL_SUPPRESS_DEPRECATED`,
   feed both blocks yourself and reset `ctx.h` to the IV on every candidate.

Working, verified kernel: `templates/sha256_pow_sa_miner.c` — its digest was checked against
an independently computed hash on a real winning nonce before it was trusted.

## Setup on a fresh VPS

```bash
# 1. Install deps
apt update && apt install -y python3-pip
pip3 install pycryptodome --break-system-packages

# 2. Install Foundry (cast for RPC)
curl -L https://foundry.paradigm.xyz | bash && foundryup
export PATH="$HOME/.foundry/bin:$PATH"

# 3. Create miner dir + scripts
mkdir /root/miner
# See templates/ for the Python miner code
```

## Wallet requirements
- **Burner wallet only.** Never use a wallet that guards real funds — the miner needs the private key.
- Fund with ETH on the mining chain for:
  - Mint price (Hashwood: 0.00005 ETH per mint)
  - Gas fees (~few cents per TX)
  - Recommended: 0.01-0.05 ETH to start
- For Robinhood Chain: bridge ETH from mainnet or use a CEX that supports it.

## Full flow (fetch → mine → submit → loop)
1. `cast call` → `challengeNumber()` + `miningTarget()`
2. Build 84-byte input: challenge(32) + address(20) + nonce(32)
3. Hash with keccak256 until hash ≤ target
4. Pre-check: `cast call` → `checkMintSolution(nonce, address)` — saves gas if challenge rotated
5. Submit: `cast send contract "mint(uint256,bytes32)" nonce 0xdigest --value MINT_PRICE --private-key PK`
6. If `BlockAlreadyMined` → challenge changed → fetch new work and restart

## Go miner setup

Go combines near-GPU hashrate with simple deployment. The single binary has no runtime deps.

```bash
# On the VPS:
mkdir /root/hashwood-go && cd /root/hashwood-go
go mod init pow-miner
go get golang.org/x/crypto/sha3
go get github.com/ethereum/go-ethereum/common
go get github.com/ethereum/go-ethereum/core/types
go get github.com/ethereum/go-ethereum/crypto
go get github.com/ethereum/go-ethereum/rlp

# Write .env with private key
echo -n "0xYOUR_PRIVATE_KEY" > .env
chmod 600 .env

# Build
go build -o powminer miner.go
# Start
screen -dmS miner ./powminer
```

**See `templates/go_miner_v2.go` for the full working Go miner.**

### Critical Go deployment notes
- The Go binary reads `.env` from `/root/hashwood-js/.env` by default (change path in source).
- Private RPC URL is hardcoded — edit the `RPC_URL` const before building.
- Gas boost is hardcoded as `2` (2x base gas price). Change via the `sendMint` call argument.
- Block number polling is throttled to once per 500ms to avoid Alchemy rate limits.
- Nonce is fetched from chain every TX (never cache locally — nonce desync silently breaks all subsequent TXes).

## Gas boost strategy (competing with GPU miners)

CPU miners can't beat GPU miners on hashrate, but they CAN win by paying higher gas fees.
When both a CPU TX and a GPU TX are in the same mempool, validators pick the one with
higher gas price. Strategy:

1. **Start with 2x gas boost** (multiply base gas price by 2)
2. Base gas on Robinhood Chain is usually 1-50 gwei
3. At 2x boost with 50k gas: ~0.0001-0.005 ETH per TX attempt
4. **Never use 50x boost** — tested this, it drained 0.0014 ETH in 20s (all reverts)
5. Realistically, even with high gas, CPU miners rarely win against GPUs because the GPU's TX lands in the mempool first

**The gas-vs-hashrate tradeoff:** With Go at 1 MHz, finding a solution takes ~200μs. But the real bottleneck is TX propagation (~200-500ms RPC round-trip). By the time our TX reaches validators, the GPU's TX (submitted 50ms earlier) is already in a block. Gas boost helps but doesn't overcome this latency gap.

## RPC rate limiting (Alchemy/QuickNode)

Aggressive mining triggers rate limits fast:

```python
# Too aggressive — 3000+ requests/second:
for:  getWork() → mine() → submit()  # repeats every 200μs

# Fixed — throttle to 2-20 req/s:
for:
  if time_since_last_block_check > 500ms:  poll eth_blockNumber
  getWork() → mine() → submit()
```

**Symptoms of rate limiting:**
- `HTTP 429 Too Many Requests`
- `eth_call` returns empty or stale data (zombie challenges)
- `eth_sendRawTransaction` returns errors or silently drops TXes
- checkMintSolution() returns false for valid solutions

**Fix:** Space out RPC calls. Cache gas price (update every 30s). Don't poll block number more than twice per second. Use a private RPC endpoint (Alchemy/QuickNode — public RPCs are stricter).

## Nonce management — never cache locally

The most expensive mistake: caching the TX nonce locally and incrementing it per TX attempt.

```go
// DANGEROUS — silently breaks:
nonce := getNonceFromChain()  // nonce = 62
for {
    tx = buildTx(nonce)
    send(tx)
    nonce++  // now nonce = 63, 64, 65...
    // If TX at nonce 62 never mined (revert), ALL subsequent TXes are invalid
}
```

**The fix:** Always fetch nonce from chain with `eth_getTransactionCount(address, "pending")`.
This adds ~50ms per TX but prevents the "infinite loop of invalid TXes" where every TX
fails because the local nonce is ahead of the chain nonce.

## Fire-and-forget vs receipt waiting

| Strategy | Speed | Certainty | Gas wasted |
|---|---|---|---|
| Submit + wait for receipt | ~2s per TX | Know if it minted or reverted | Know exactly |
| Fire-and-forget | ~50ms per TX | Don't know until balance check | Wild guess |

**When to use fire-and-forget:** When mining at high speed (Go, 1 MHz+), waiting 2s per receipt
is 40x slower than the solution time. Better to fire-and-forget and check HASH balance periodically.

**When to wait:** When ETH is limited and every TX cost matters. The receipt confirms success or
revert, so you can adjust strategy (skip TX if challenge changed).

## Block detection strategy

Poll `eth_blockNumber` to detect when someone minted (challenge rotated):

```go
// Throttled to once per 500ms
if time.Since(lastBlockCheck) > 500*time.Millisecond {
    blockNum = eth_blockNumber()
    if blockNum > lastBlock {
        // Challenge changed — mining current work is worthless
        refreshChallenge()
    }
    lastBlock = blockNum
}
```

This prevents mining a stale challenge for more than 500ms. Without it, the miner
might hash against an already-taken block for 1000x more hashes than needed.
When the user provides SSH creds (IP, root, password), use `sshpass` to set up mining remotely:

```bash
# Test connection
sshpass -p 'PASSWORD' ssh -o StrictHostKeyChecking=no root@IP "uname -a"

# Install + Foundry + scripts in one go
sshpass -p 'PASSWORD' ssh ... "apt install -y nodejs python3-pip; pip3 install pycryptodome --break-system-packages; ..."

# Start miner in screen
screen -dmS <name> python3 run_miner.py
```

After setup: verify the miner is running (`screen -ls`), check that it found solutions
in the output, then verify HASH balance via `cast call balanceOf(address)(uint256)`.

## Running the miner as a long-haul supervised job (remote VPS)

A PoW race is won in hours, not minutes, so the deliverable is a job that survives
disconnects — not a foreground loop. Shape that worked on HashBroker:

```
/root/.hb/
  hb_mine            # C kernel: hb_mine <addr> <challenge> <diff> <threads> <seconds>
                     #            stdout "FOUND <nonce_hex> <bits>" (exit 0) | exit 2 on timeout
                     #            stderr "STAT <hashes> <bestbits> <MH/s>" every ~3 s
  hb_bot.py          # supervisor: read challenge/difficulty -> mine a chunk -> re-check -> submit
  hb_ctl.sh          # start | stop | status | watchdog
  pk                 # chmod 600, burner wallet only
  bot.log, state.json
```

- Miner as a **subprocess that exits on hit or timeout** keeps the supervisor trivial: no
  shared memory, no signal plumbing, and a dead child is visible in the logs.
- **Chunk the search** (5 s) and re-read `challenge()` between chunks. On a rotating shared
  challenge a proof for a stale challenge is worthless; the ~1 s of RPC between chunks still
  leaves ~98% duty cycle, so there is nothing to gain from longer chunks.
- `state.json` written every ~60 s (hashes, best bits, wins, supply, difficulty) makes
  `hb_ctl.sh status` a one-liner and gives the user something to look at.
- Install a **cron watchdog** (`*/5 * * * * hb_ctl.sh watchdog`) so the job self-heals.

### Pitfalls that cost real time

- **`pkill -f <script>.py` over SSH kills your own SSH session.** The remote shell's cmdline
  contains the pattern, so it self-matches and dies *before* the restart in the same command
  runs — leaving the bot down. Use the bracket trick: `pkill -f "[h]b_bot.py"`, and wrap it in
  the ctl script so it is never typed raw.
- **"Turn it off" means three things**: stop the process, **delete the watchdog cron entry**,
  then verify zero processes. Skip the cron and the watchdog resurrects the bot within one
  interval. Also remove any out-of-band notifier job you created.
- **Verify "stopped" with a pattern that cannot self-match** (`pgrep -cf "[h]b_bot.py"`). A bare
  `pgrep -f hb_bot` over SSH matches the SSH command itself and reports a phantom process —
  and load average lags by a minute, so check both.
- **Don't redirect the supervisor's stdout into the file it already logs to** — every line
  lands twice. Run under `> /dev/null` and let the script own its logfile.
- **Keys in `/dev/shm` do not survive a reboot** (tmpfs). Re-derive from the mnemonic instead
  of assuming the file is still there; derive-on-demand costs a second.
- The mining wallet needs **gas only**, and only on a win. Measure it from a real receipt
  (`gasUsed` × `effectiveGasPrice`) rather than guessing; fund enough for a few wins, not for
  the whole session.

### Reporting an honest result

State the expected wait up front (`2^difficulty / your_H_s`) so the user knows what "nothing
yet" means. Then: **a correct miner with 0 wins is the expected outcome, not a bug to paper
over.** A useful sanity check to prove the kernel is really working: best-of-run leading-zero
bits should track `log2(total_hashes)` — 104 billion hashes ⇒ expect a best around 36–38 bits.
If best bits are far below that, the kernel is broken; if they match, the miner is fine and the
race simply wasn't won. Report the no-win run as a no-win run.

## Troubleshooting
- **BlockAlreadyMined**: Normal. Someone else mined the same block. Miner auto-retries with new challenge.
- **Insufficient funds**: ETH ran out for mint price + gas. Replenish the burner wallet.
- **cast: command not found**: PATH doesn't include `~/.foundry/bin`. Always `export PATH="$HOME/.foundry/bin:$PATH"` before running cast.
- **keccak mismatch**: Ensure Ethereum keccak256 (0x01 padding), NOT SHA3-256 (0x06 padding). They produce different hashes for the same input.

## Templates
- **`templates/sha256_pow_sa_miner.c`** — SHA-256 PoW kernel for the non-keccak variant: multi-threaded, uses OpenSSL `SHA256_Transform` (SHA-NI path), sweeps the 64-bit nonce, prints `FOUND <nonce> <bits>` / `STAT <hashes> <best> <MH/s>`. Verified correct against a real winning nonce. ~10 MH/s per SHA-NI core.
- `templates/hashminer.py` — Python pycryptodome PoW core (standalone miner)
- `templates/run_miner.py` — Full loop wrapper using cast subprocess (basic)
- `templates/run_v2.py` — Optimized wrapper with web3.py + private RPC (`pip install web3`)
- **`templates/go_miner_v2.go`** — Full Go miner: compiled (~1 MHz), persistent RPC, gas boost, block detection, fire-and-forget TX. Zero runtime deps. Read `resources/` for setup instructions.

## Critical bugs found + fixed (learn from these)

### 1. Nonce byte order (CRITICAL — silent wrong hashes)
The 32-byte uint256 nonce field must be RIGHT-JUSTIFIED. The 8-byte nonce value goes
in the LAST 8 bytes (offset 76-83), with 24 leading zero bytes (offset 52-75):

```python
# WRONG — produces hashes that ALMOST match but contract rejects:
msg[52:60] = nonce.to_bytes(8, 'big')     # nonce first
msg[60:84] = b'\x00' * 24                 # zeros after

# CORRECT — matches contract's verification:
msg[76:84] = nonce.to_bytes(8, 'big')     # nonce last (right-justified)
msg[52:76] = b'\x00' * 24                 # zeros before
```

The wrong ordering produces hashes that look valid but fail `checkMintSolution()`.
The error is silent — hashminer thinks it found a solution but the contract disagrees.
**Always test a known solution with `cast call checkMintSolution()` before assuming
the miner is correct.**

### 2. Function selectors (must match contract)
Don't guess the selectors — always verify:
```bash
cast sig 'challengeNumber()'              # → 0x8ae0368b (NOT 0x21d06833)
cast sig 'miningTarget()'                 # → 0x8a769d35 (NOT 0x61461954)
cast sig 'checkMintSolution(uint256,address)'  # → 0x9d7a7cc6
cast sig 'mint(uint256,bytes32)'          # → 0x1801fbe5
```

Wrong selectors cause silent "execution reverted" errors in web3 eth_call.

### 3. Gas pricing — don't assume mainnet rates
Robinhood Chain gas is cheap (~1-10 gwei). The first attempt failed with
`insufficient funds for gas * price + value` because maxFeePerGas was set to
50 gwei (fine on mainnet, overpriced for RH Chain). Use 10 gwei max, 0.1 gwei
priority. Robinhood Chain doesn't need EIP-1559 priority to be competitive.

### 4. TX receipt — don't trust send_raw_transaction return
`send_raw_transaction` returns a TX hash immediately (before mining). The TX
can be mined and REVERT silently. Always `wait_for_transaction_receipt` and
check `receipt['status'] == 1`. A "MINT SUCCESS" without receipt verification
is a false positive — you burned gas + mint fee for nothing.

### 5. cast stderr — don't ignore it
`cast send` puts errors on stderr and nothing on stdout. If the wrapper only
reads stdout, failed TXs look like "TX: ..." (empty). Always capture and log
stderr when using subprocess cast.

### 6. RPC rate limiting (Alchemy/QuickNode)
Mining at Go speed (~200μs per cycle) triggers 3000+ RPC requests/second. Alchemy free tier
limits to ~100-300 req/s. Symptom: `HTTP 429`, stale challenges from cached responses,
`checkMintSolution()` returning false for valid solutions since the RPC returns stale data.

**Fix:** Throttle block number polling to once per 500ms. Cache gas price (update every 30s).
Use a single persistent HTTP connection (not one per call). If rate-limited, add exponential backoff
(not a mandatory fix — the polling throttle is usually sufficient).

### 7. Gas boost — 2x is reasonable, 50x is a trap
50x gas boost on Robinhood Chain at base 10 gwei = 500 gwei. At 60k gas: 0.03 ETH per TX.
After 20 reverts (1 minute): 0.6 ETH drained. The balance evaporates before a single TX lands.

**Fix:** Start with 1.5-2x boost. Monitor ETH balance. Don't boost higher than 5x unless you
have a confirmed win condition (e.g., you're the only miner). 2x gives enough priority on
Robinhood Chain without draining the wallet.

### 8. Nonce caching = silent death
Caching the TX nonce locally and incrementing per TX attempt works UNTIL a TX reverts.
After the first revert, EVERY subsequent cached-nonce TX is invalid (the chain nonce hasn't
moved). The miner keeps "sending" TXes that never land — sometimes for hours — while the
balance drains.

**Fix:** Always call `eth_getTransactionCount(address, "pending")` before building every TX.
The `"pending"` parameter is critical — it includes pending TXes in the mempool so consecutive
TXes from the same miner get sequential nonces without waiting for confirmation.

- **"Insufficient funds for gas * price + value"**: Total = mint_price + gas_limit × gas_price. For Robinhood Chain at 10 gwei with 50k gas: 0.00005 + (50000 × 0.00000001) = 0.00055 ETH per TX attempt (reverted TXs also burn gas!).
- **Python spawn overhead**: Each call to `hashminer.py` via subprocess spawns 6 Python processes. This takes 0.5-1s. To reduce this, run the miner loop continuously with pre-spawned processes (not re-spawning each batch).
- **Private RPC matters**: Public RPCs add 1-3s latency per call. A private Alchemy/QuickNode RPC cuts round-trips to ~100ms. Combined with web3.py persistent connection (no subprocess), total TX submit time drops from ~5s to ~1s.
