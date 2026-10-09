---
name: hashwood-miner
description: "PoW mining on Robinhood Chain: keccak and SHA-256 drops."
---

# PoW Mining on Robinhood Chain — Hashwood (keccak) & HashBroker (SHA-256)

Fair-launch PoW mints on Robinhood Chain (4663). The keccak/EIP-918 protocol below is
Hashwood; the SHA-256 sibling and the general SHA-NI mining playbook are in
"Sibling drop: HashBroker" further down.

## Overview

**Token:** HASH (ERC-20)  \n**Chain:** Robinhood Chain (Chain ID 4663)  \n**Contracts:** `0xD69be8d7c6d0e8216Dc2C151834E4150313260Cc` (v1 — deprecated), `0x651F33574C092344E4257Fb6Bc353a5663c3e0cc` (v2 — active)  \n**RPC (public):** `https://rpc.mainnet.chain.robinhood.com`  \n**Algo:** keccak256 Proof-of-Work (EIP-918)  \n**Supply:** 21,000,000 HASH (5 seasons, halving every 11,000 mints)
**Chain:** Robinhood Chain (Chain ID 4663)  
**Contract:** `0xD69be8d7c6d0e8216Dc2C151834E4150313260Cc`  
**RPC (public):** `https://rpc.mainnet.chain.robinhood.com`  
**Algo:** keccak256 Proof-of-Work (EIP-918)  \n**Supply:** 21,000,000 HASH (5 seasons, halving every 11,000 mints)

## V2 Relaunch — July 2026

HashWood v1 had a flaw (immutable contract) → v2 relaunched with a new contract:

| Aspect | v1 (Deprecated) | v2 (Active) |
|--------|----------------|-------------|
| **Contract** | `0xD69be8d7c6d0e8216Dc2C151834E4150313260Cc` | `0x651F33574C092344E4257Fb6Bc353a5663c3e0cc` |
| **Snapshot** | All mined HASH credited 1:1 | ✅ Applied automatically |
| **Miner** | `miner.mjs` | `miner-simple.mjs` (secp256k1 signing) |
| **JS dep** | cast subprocess | secp256k1.mjs (direct signing) |
| **Functions** | Standard selectors | **Identical ABI** |

Function selectors verified identical between v1 and v2 (confirmed with `cast sig`).

**GPU miners migrated within minutes** — 231,088 HASH already minted by the time we detected the relaunch.

## Contract (v1 — deprecated)

Old contract address: `0xD69be8d7c6d0e8216Dc2C151834E4150313260Cc`

## Flow

```
keccak256(challenge(32) ‖ address(20) ‖ nonce(32)) ≤ miningTarget()
```

1. Read `challengeNumber()` + `miningTarget()` from contract (batch call)
2. Build 84-byte message: challenge(32) + yourAddress(20) + nonce(32)
3. Sweep nonces until keccak256 hash ≤ target
4. Call `mint(uint256 nonce, bytes32 digest)` with 0.00005 ETH

## Key Contract APIs

| Function | Selector | Gas |
|----------|----------|-----|
| `challengeNumber() → bytes32` | `0x8ae0368b` | Free (view) |
| `miningTarget() → uint256` | `0x8a769d35` | Free (view) |
| `checkMintSolution(uint256,address) → bool` | `0x9d7a7cc6` | Free (view) |
| `mint(uint256,bytes32)` | `0x1801fbe5` | 0.00005 ETH + gas |
| `balanceOf(address) → uint256` | `0x70a08231` | Free |

## Mining Strategies (tested)

### 1. JS Reference Miner (slowest)
~1-2 KHz. Pure JS keccak implementation, intentionally slow (reference only).

### 2. Python + pycryptodome (medium)
~75 KHz. Uses `Crypto.Hash.keccak` (C-accelerated). 6 threads via multiprocessing.  
Good for testing but the subprocess spawn overhead (0.5-1s per batch) costs the block race.

### 3. Go + go-ethereum (fastest)
~1M+ KHz. Compiled, goroutines, native keccak256. Direct TX signing + submission.  
Key deps: `golang.org/x/crypto/sha3`, `github.com/ethereum/go-ethereum`

## TX Submission Optimization

The bottleneck is **RPC latency** (~200ms per `eth_call` on the public RPC via Cloudflare).  
GPU miners running local nodes have <1ms RPC — they win every block race.

### Techniques tried (in order of impact):

| Technique | Impact |
|-----------|--------|
| **Batch RPC** — merge multiple `eth_call` into 1 HTTP POST | Saves ~200ms per getWork cycle |
| **Persistent HTTP connection** — reuse TCP+TLS | Saves ~100ms/call after first |
| **Cached nonce** — track locally, skip `eth_getTransactionCount` | Saves 1 RPC call per TX |
| **Cached gas price** — update every 30s | Saves 1 RPC call per TX |
| **Pre-sign TX** — sign before block opens, submit immediately | Saves signing time in the race window |
| **Parallel goroutines** — fetch work + nonce concurrently | Saves ~100ms per cycle |
| **Predictive block timing** — pre-mine before block opens | 0 impact (GPU miners use same technique) |
| **Gas boost (50x)** — pay higher gas for priority | **DANGER** — drained wallet with no wins |
| **Direct RPC** (skip Alchemy) | Marginal (Alchemy adds ~50ms) |

## Diagnosing RPC Bottlenecks (Server-Timing header)

The RPC behind Cloudflare exposes `Server-Timing` response headers that break down latency:

```bash
# Use -v to see response headers
curl -s -o /dev/null -w '\n' -v \
  -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":"0x651F33574C092344E4257Fb6Bc353a5663c3e0cc","data":"0x8ae0368b"},"latest"]}' \
  "https://rpc.mainnet.chain.robinhood.com" 2>&1 | grep -i 'Server-Timing\|cf-Ray'
```

Expected output:
```
Server-Timing: cfCacheStatus;desc="DYNAMIC"
Server-Timing: cfEdge;dur=4,cfOrigin;dur=102
CF-RAY: a18b3e54d99efba5-AMS
```

The breakdown:
| Component | Typical | Meaning |
|-----------|---------|---------|
| **cfEdge** | 4ms | Cloudflare edge processing time |
| **cfOrigin** | 102ms | **Round-trip to Offchain Labs origin server** = real bottleneck |
| **CF-RAY AMS** | Amsterdam | Cloudflare data center location (AMS = Amsterdam) |

This shows the bottleneck is the **origin server processing** (~52ms minimum), not network latency. Running the miner from a VPS in France (1.2ms ping to CF) vs Netherlands (1.2ms) made no difference — the 100+ms is server-side processing at Offchain Labs.

**`eth_getStorageAt` is no faster than `eth_call`** — both take ~200ms on this RPC endpoint. Not a viable bypass.

## Infrastructure Facts

- **DNS**: `rpc.mainnet.chain.robinhood.com` CNAME → `customer-origin.offchainlabs.com`
- **Provider**: Offchain Labs (Arbitrum) manages the sequencer infrastructure
- **Path**: Client → Cloudflare → Envoy (Istio) → Sequencer
- **No direct sequencer endpoint found**: All paths through Cloudflare return 301/404 for non-RPC paths; WebSocket returns 400
- **VPS from Netherlands (NL) and France (FR)**: Both have 1.2ms ping to Cloudflare edge — negligible difference

## Contract Interface (v1 and v2 — identical ABI)
- Gas boost (all revert anyway — 1 mint per block, 1 second blocks)
- Predictive timing (GPU miners are too numerous)
- WebSocket (not supported on public RPC — returns 400)

## Critical Bug: Nonce Byte-Order

The nonce must be encoded as **uint256 big-endian, right-justified**:

```python
# WRONG — nonce at start of 32-byte field:
msg[52:60] = nonce.to_bytes(8, 'big')   # placed at beginning
msg[60:84] = b'\x00' * 24               # zeros after

# CORRECT — nonce at END of 32-byte field:
msg[76:84] = nonce.to_bytes(8, 'big')   # last 8 bytes
msg[52:76] = b'\x00' * 24              # zero pad before
```

## Practical Conclusion: Without a Local Node, You Lose

After 7 iterations of the Go miner with escalating optimizations:

| Version | Technique | Result |
|---------|-----------|--------|
| v1 (Python) | pycryptodome keccak, 6 threads | ❌ All revert |
| v2 (Go) | goroutines, direct RPC | ❌ All revert |
| v3 (Go) | checkMintSolution before TX (gas saver) | ❌ checkValid always false |
| v4 (Go) | Block timing — poll 80ms for new blocks | ❌ 47 revert |
| v5 (Go) | Predictive timing + pre-mine | ❌ 30+ revert |
| v6 (Go) | Batch RPC + parallel goroutines + cached nonce/gas | ❌ 20 revert |
| v7 (Go) | **Persistent raw TCP connection** (bypass Go http.Transport) | ❌ 20 revert |
| **Total** | **60+ TX submitted, 0 wins** | **Waste of ETH** |

**Root cause:** The public RPC goes through Cloudflare → Envoy → Offchain Labs sequencer, adding ~102ms per call (cfOrigin header). GPU miners running local Arbitrum Nitro nodes have <1ms RPC. In a 1-second block window with 1-mint-per-block, they win every time.

The only viable path to competitive mining: run a local Robinhood Chain (Arbitrum Nitro) node on the VPS.

## Miner Go Code (v7 — most optimized, still loses without local node)

```go
// PersistentRPC: raw TLS connection reused across all RPC calls
// Key optimizations (all baked into v7):
// 1. Persistent TCP + TLS connection (no reconnect per call)
// 2. Batch RPC (2 eth_calls in 1 HTTP request)
// 3. Cached nonce + gas (1 RPC call per TX: sendRawTransaction only)
// 4. Parallel goroutines for work + nonce fetching
// 5. Pre-signed TX (sign before block opens)
// Location: /root/hashwood-go/miner_v7.go on VPS <REDACTED>
```

## Sibling drop: HashBroker — SHA-256 PoW on the same chain (2026-09)

`hashbroker.fun` is a second Robinhood-Chain fair-launch PoW mint — **SHA-256
leading-zero-bits, not keccak**. Contract `0x4272D6f51771839F596082eF48fa84D35239Bab3`
(unverified; reverse from the site's `miner.js` + real on-chain txs). Full detail,
worked numbers and the deploy recipe: `references/hashbroker-sha256-pow.md`.
Ready-to-compile SHA-NI miner: `scripts/hb_mine.c`.

Verified preimage — matched **3/3** successful on-chain mints:

```
sha256( address(20B) ‖ 24 zero bytes ‖ nonceHi(4B BE) ‖ nonceLo(4B BE)
        ‖ challenge[0:12] ‖ challenge[12:32] )   → leading zero BITS ≥ currentDifficulty
```

- `mine(uint256 nonce, bytes32 challenge)` selector `0xe43e322c`
- nonce arg = uint64 right-aligned in a 32-byte word (`nonceHi` high 32 bits first)
- the address comes from **`msg.sender`, not calldata** → every wallet must mine its own
  proof; work is not shareable across wallets (splitting hashrate across wallets does not
  change the total win probability, so concentrate on one funded wallet)
- also present: `totalSupply() 0x18160ddd`, `mintPrice() 0x6817c76c`,
  `challenge() 0xd2ef7398`, `currentDifficulty() 0x5c062d6c`

### Race shape decides whether you can win — check this before comparing to Hashwood

| | Hashwood | HashBroker |
|---|---|---|
| Algo | keccak256 | SHA-256 |
| Race | **per-block** (1 mint / 1s block) → latency decides | **global challenge** (~30s–3min per find) → **hashrate decides** |
| What kills you | 102ms public-RPC latency vs local-node GPU miners | raw MH/s vs GPU rigs |

The "without a local node you lose" conclusion above is a **per-block-race** conclusion.
On a global-challenge race like HashBroker, ~30s of slack means RPC latency is nearly
irrelevant — the only lever is hashrate. Don't carry the wrong lesson across.

### SHA-NI is the entire game for SHA-256 PoW

| CPU | SHA-NI | 1 core | 6 cores |
|---|---|---|---|
| Xeon Gold 6138 (Skylake-SP) | ❌ | 0.97 MH/s | ~3.9 MH/s |
| **AMD EPYC** | ✅ | **9.45 MH/s** | **~55 MH/s** |

**Check the target before committing any time to it:**
```bash
grep -o sha_ni /proc/cpuinfo | head -1     # present = hardware SHA
openssl speed -seconds 3 sha256            # 64-byte col: ~52 MB/s = no SHA-NI, ~180 MB/s = SHA-NI
```
AMD EPYC and Ryzen (all gens) and Intel Ice Lake+ have it; Skylake-SP Xeons do **not**.
Adding cores without SHA-NI buys almost nothing (~1.5x for 4→6 cores) — hashrate is
dominated by the per-core SHA-NI factor, so one SHA-NI box beats a pile of old Xeons.

### Mining loop implementation

- Use OpenSSL **`SHA256_Transform()`** (2 calls per 64-byte block), **not**
  Init/Update/Final — measured 25% faster (10.11 vs 8.05 MH/s/core) and lands ~90% of the
  SHA-NI hardware ceiling. Reset `ctx.h[]` to the IV by hand each iteration.
- Self-check the miner against a **known-successful on-chain proof** before trusting it
  (address + challenge + nonce → expected digest). Cheap and decisive.
- No partial-precompute shortcut is available: the nonce sits **inside** block 1, so the
  first block's compression cannot be precomputed and reused across nonces. Only the
  message schedule for the fixed words (W[0..10]) is reusable, and that is a minor win.
  Don't spend time hunting for a "skip half the hash" trick — there isn't one.

### Validate the calldata for free before spending gas

`eth_call` the exact mint calldata **at the block immediately before a known-successful
mint** — it returns success. The same call at `latest` reverts once the challenge rotates
(observed revert selector `0xaa2bf635` = challenge/proof mismatch). This proves your
selector and argument encoding end-to-end without broadcasting, and it exercises the same
revert path a stale proof will hit.

### Supervisor + watchdog pattern (any long PoW race)

- C miner does one chunk per process invocation: `FOUND <nonce> <bits>` on stdout + exit 0;
  `TIMEOUT <hashes> best <bits> bits` on stderr + exit 2. Supervisor re-reads the challenge
  between chunks and abandons stale work.
- Supervisor **simulates (`eth_call`) before broadcasting** → never burns gas on a proof for
  a rotated challenge.
- cron `*/5 * * * * /root/.hb/hb_ctl.sh watchdog` restarts a dead `screen` session.

## Pitfalls

1. **Verifying selectors**: Always use `cast sig <functionSignature>` — don't assume keccak hash
2. **Nonce byte-order**: Right-justified uint256 big-endian (see bug section above)
3. **checkMintSolution() is FREE**: Use it before submitting TX to save gas on expired solutions
4. **Keep-alive doesn't work on Cloudflare**: Server sends `Connection: close` — use persistent raw TCP (like v7) not Go's http.Transport
5. ⚠️ **Gas boost is DANGEROUS**: A 50x boost drained 0.0016 ETH ($4) in <20 TX with 0 wins — never boost above 2x
6. **Robinhood Chain behind Cloudflare + Envoy**: No way to bypass — the 102ms RPC latency includes server processing (~52ms), not just network
7. **WebSocket not available**: public RPC returns 400 for WS upgrade
8. **`eth_getStorageAt` is same speed as `eth_call`**: ~200ms — no advantage
9. **Server-Timing header**: Use `curl -v` and check `cfEdge;dur=X,cfOrigin;dur=Y` to diagnose where latency lives
10. **Robinhood Chain = Offchain Labs infrastructure**: DNS CNAME is `customer-origin.offchainlabs.com` — the sequencer is managed by Offchain Labs, not self-hosted by Robinhood
11. **`pkill -f <script>.py` over SSH kills your own SSH session** — the pattern matches the remote command line that contains it, so the run dies half-way and you get an empty result. Use the bracket trick `pkill -f "[h]b_bot.py"`, or put stop/start inside a controller script (`hb_ctl.sh`). Same failure class as the general "never `pkill -f` a broad pattern" rule.
12. **`/dev/shm/*.pk` does not survive a reboot** (tmpfs). Never assume the shm key file is still there — re-derive the key from the mnemonic file and confirm the derived address matches before using it.
13. **Don't redirect a bot's stdout to the same file the bot already logs to** — every line lands twice and the log doubles in size. Either let the bot own its log file and send stdout to `/dev/null`, or vice versa.
14. **Difficulty on these drops ratchets up with supply, it doesn't reset** — HashBroker went 35 → 41 bits while supply went ~1 → 67. Expected yield degrades the longer you wait, and a rising difficulty can outrun a fixed hashrate. Sample `currentDifficulty()` at several historical blocks (`eth_call` with a block number) to get the curve before deciding, and start early if you're going to start at all.

## Miner File Structure (on VPS <REDACTED>)

```bash
/root/hashwood-js/      # JS reference miner (miner.mjs + keccak.mjs)
/root/hashwood-miner/   # Python miner (hashminer.py + run_miner.py + run_v2.py)
/root/hashwood-go/      # Go miners (v1-v6, escalating optimizations)
/root/.hb/              # HashBroker bot (hb_mine + hb_bot.py + hb_ctl.sh + cron watchdog)
```

Host note: `<REDACTED>` is an **AMD EPYC 6-core with SHA-NI** — the SHA-NI box, use it
for SHA-256 PoW. The other box (`empero`, 82.39.206.183) is a Xeon Gold 6138 **without**
SHA-NI and is ~14x slower on SHA-256; don't put SHA-256 mining there.

## References

- `references/hashwood-contract-abi.md` — full ABI and function selectors
- `references/hashbroker-sha256-pow.md` — HashBroker (SHA-256 sibling drop): verified
  preimage, selectors, contract, measured hashrates, deploy layout, and expectation math
- `scripts/hb_mine.c` — SHA-NI multithreaded miner for the leading-zero-bits family of PoW
  (`gcc -O3 -march=native -pthread -o hb_mine hb_mine.c -lcrypto`, then
  `./hb_mine <addr_hex> <challenge_hex> <difficulty> <threads> <max_seconds>`)
