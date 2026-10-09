---
name: hashwood-evm-pow-mining
description: PoW mining on EVM chains (EIP-918 style) — Hashwood (Robinhood Chain). Covers CPU mining in Python and Go, keccak256 message format, sequencer-direct TX submission, block-timing strategies, and gas optimization via checkMintSolution().
version: 1.0.0
author: spring
license: MIT
platforms: [linux]
---

# Hashwood EVM PoW Mining

## Goal
Mine HASH tokens on Robinhood Chain using keccak256 Proof-of-Work. Understand the protocol, build CPU miners, and compete against GPU miners using network-level advantages (sequencer proximity, block timing).

## Hashwood Protocol Spec
- Chain: Robinhood Chain (Chain ID 4663)
### V1 Contract (deprecated — immutable flaw, replaced)
- Address: `0xD69be8d7c6d0e8216Dc2C151834E4150313260Cc`
### V2 Contract (active)
- Address: `0x651F33574C092344E4257Fb6Bc353a5663c3e0cc`
- Relaunch reason: v1 had an immutable flaw, v2 snapshot credited 1:1
- V2 diff: Same function selectors, same mint price — starting target 4.417e71 (64x harder than v1's 2.826e73)
- New miner: `miner-simple.mjs` (hashwood.xyz) — secp256k1 signing natively, no cast subprocess
- RPC: `https://rpc.mainnet.chain.robinhood.com` (Cloudflare → Offchain Labs Envoy → Sequencer)
- Alchemy private RPC: `https://robinhood-mainnet.g.alchemy.com/v2/<key>`
- Algo: keccak256 (Ethereum variant, 0x01 padding — NOT SHA-3)
- Message: `challenge(32) ‖ address(20) ‖ nonce(32)` = 84 bytes total
- Win condition: `uint256(keccak256(message)) ≤ miningTarget()`
- Mint price: 0.00005 ETH (goes to locked Uniswap liquidity)

### Contract Functions
| Function | Selector | Description |
|---|---|---|
| `challengeNumber()` | `0x8ae0368b` | Current PoW challenge (bytes32) |
| `miningTarget()` | `0x8a769d35` | Target difficulty (uint256) |
| `MINT_PRICE()` | — | Mint fee (0.00005 ETH) |
| `checkMintSolution(uint256,address)` | `0x9d7a7cc6` | FREE — verify solution before submitting TX |
| `mint(uint256,bytes32)` | `0x1801fbe5` | Submit solution (payable: 0.00005 ETH) |
| `balanceOf(address)` | `0x70a08231` | HASH balance |

### Rewards (Season system — halves every 11,000 mints)
| Season | Reward/Mint | Supply % |
|--------|------------|----------|
| 1 | 1,100 HASH | ~50% |
| 2 | 550 HASH | ~25% |
| 3 | 275 HASH | ~12.5% |
| 4 | 137.5 HASH | ~6.25% |
| 5 | 68.75 HASH | ~3.125% |

## CRITICAL: keccak256 Message Format

The 84-byte message is: `challenge(32) + address(20) + nonce(32)`

The nonce (uint256) must be encoded as **big-endian, right-justified** (last 8 bytes = nonce value, first 24 bytes = zeros):

```
✅ CORRECT:
  msg[52:76] = zeros(24)   # padding
  msg[76:84] = nonce(8)    # big-endian

❌ WRONG (BROKEN — OLD CODE):
  msg[52:60] = nonce(8)    # at the start!
  msg[60:84] = zeros(24)   # right-padded
```

Putting the nonce at position 52 instead of 76 produces a completely different (invalid) hash. This was a bug found and fixed in the Python miner.

## Tools
### Python Miner (pycryptodome)
- Hashrate: ~75 KHz (6 threads)
- Deps: `pip install pycryptodome web3`
- Location reference: `/root/hashwood-miner/` on empero
- Uses multiprocessing for parallelism (heavy spawn overhead per batch)

### Go Miner (recommended)
- Hashrate: ~1M+ KHz (6 goroutines) — measured solutions in 100-500μs
- Deps: `go get golang.org/x/crypto/sha3 github.com/ethereum/go-ethereum/...`
- Location reference: `/root/hashwood-go/` on remote VPS
- Uses goroutines (lighter than Python multiprocessing)
- Direct RPC to sequencer (see references/go-miner-architecture.md)

### Reference JS Miner (Official — intentionally slow)
- Hashrate: ~1-2 KHz
- Files: `https://hashwood.xyz/miner/miner.mjs` + `keccak.mjs`
- Run: `RPC_URL=... PRIVATE_KEY=0x... CONTRACT=0x... node miner.mjs`

## Deployment
### VPS Setup (VPS <REDACTED> — France, near sequencer in Amsterdam)
```bash
# Install deps
curl -L https://foundry.paradigm.xyz | bash && foundryup
apt install golang-go python3-pip
pip3 install web3 pycryptodome --break-system-packages

# Miner files at:
#   /root/hashwood-miner/   (Python miner)
#   /root/hashwood-go/      (Go miner)
#   /root/hashwood-js/      (Reference JS miner)
```

### Run
```bash
# Go miner (fastest):
cd /root/hashwood-go && screen -dmS hashwood-go ./hashminer_v4

# Python miner:
cd /root/hashwood-miner && screen -dmS hashwood-py python3 -u run_v2.py

# JS reference:
cd /root/hashwood-js && screen -dmS hashwood-js bash run_js.sh
```

## Strategies for Winning Blocks

### Strategy 1: Gas Boost (limited effectiveness)
Pay higher gas price so validators prioritize your TX. Robinhood Chain uses base fee, so 2-5x boost may help, but 50x is wasteful.
- Gas boost 2x: negligible extra cost, slight priority
- Gas boost 50x: can drain wallet in 20 TX ($0.05-0.10 each on Robinhood Chain)

### Strategy 2: Block Timing (key insight from experienced miner)
Robinhood Chain has a SINGLE centralized sequencer (Offchain Labs). There is no mempool — the sequencer processes TX in submission order.

The winning strategy:
1. Poll `eth_blockNumber` every 50-80ms
2. When block number changes → someone minted → challenge rotated
3. IMMEDIATELY fetch new challenge + mine (takes ~200μs with Go)
4. Submit solution directly to the sequencer endpoint
5. With lowest latency to the sequencer, your TX arrives first

**CPU is competitive here:** GPU miners (on Vast.ai/RunPod) have variable network latency. A dedicated VPS near the sequencer (France VPS, sequencer in Amsterdam via Cloudflare) can beat GPU miners on network speed, even though GPUs hash faster.

### Strategy 3: Predict Next Block Window
Blocks are exactly 1-second windows. Predict when the NEXT block opens and pre-position your solution:
1. Record the current block's timestamp
2. Wait until ~950ms after it (50ms before next block)
3. Fetch the challenge (still the current one if no one minted)
4. Mine the solution (~200μs — completes by the 1-second mark)
5. Submit exactly when the next block timestamp arrives

### Strategy 4: Pre-check to Save Gas
Use `checkMintSolution(uint256,address)` (a FREE `eth_call`, no gas) before submitting a TX:
- If true → solution valid → submit TX (costs gas)
- If false → block taken → skip (0 gas loss)
Implemented in run_miner.py and available in the Go miner.

### Strategy 5: Persistent TCP Connection (v7)
Go's `http.Transport` doesn't reliably reuse connections when the server sends `Connection: close`. Fix: use a raw `tls.Conn` with manual HTTP/1.1 keep-alive:
- Open one TLS connection at startup
- Send all requests on that same connection
- Only reconnect when the connection drops
- Result: subsequent RPC calls skip TCP+TLS handshake (~100ms saved per call)
- Implemented in `/root/hashwood-go/miner_v7.go` on the VPS

### Strategy 6: Batch RPC Calls
Combine `challengeNumber()` + `miningTarget()` into a single batch JSON-RPC request. Saves 1 HTTP round-trip (~200ms) per getWork cycle.
Batch format: `[{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[...]},{"jsonrpc":"2.0","id":2,...}]`

## The Real Bottleneck: Sequencer Processing Time (NOT Network)

Using HTTP pipelining + Server-Timing headers, the exact latency breakdown is:
```
Server-Timing: cfEdge;dur=4, cfOrigin;dur=102
```
- VPS → Cloudflare edge: 1.2ms (ping)
- CF edge processing: 4ms
- **CF → Origin (Offchain Labs) round-trip: 102ms** ← BOTTLENECK
- Origin processing: ~52ms (half of the 102ms)
- Network from CF to origin: ~50ms (the other half)

**Without a local node, ~100ms per RPC call is the floor.** Every eth_call, eth_sendRawTransaction, eth_getTransactionCount takes ~100ms minimum. With 3 calls per cycle (getWork + sendRawTX + receipt check), the MINIMUM round-trip is ~300ms — too slow for 1-second blocks against GPU miners with local nodes (<1ms per call).

### The Only Real Solution: Run a Local Node
- A local Arbitrum Nitro node provides RPC with <1ms response time
- VPS <REDACTED> specs (6 CPU, 11GB RAM, 189GB free disk) are sufficient
- Without local node, CPU mining against GPUs is fundamentally uncompetitive on 1-second block chains
- Cloudflare Workers don't help — the bottleneck is origin processing, not the CF edge

### CPU vs GPU: What the Experienced Miner Said
The friend's advice was tested and partially validated:
| Suggestion | Result |
|---|---|
| "Send txn directly to sequencer" | ✅ Public RPC is the only option — no sequencer-direct endpoint found |
| "No hogs in between" | ❌ Cloudflare is unavoidable (CNAME → offchainlabs.com, all CF proxied) |
| "Co-locate with their sequencer" | ✅ France VPS, CF in Amsterdam — 1.2ms ping |
| "Figure out mint window" | ✅ Predictive timing + pre-mine implemented (v5) |
| "CPU better networking than GPU" | ✅ True on paper but not enough — GPU miners likely run local nodes for <1ms RPC |
| "CPU > GPU for low difficulty" | ❌ Even with 1M+ KHz, CPU can't win against 100ms+ RPC overhead |

## References
- `references/go-miner-architecture.md` — Go miner code structure, gas caching, nonce management
- `references/centralized-sequencer-strategy.md` — Detailed block timing and network strategy

## Pitfalls
- **Nonce byte-order bug**: The nonce field is 32 bytes (uint256) in big-endian. The 8-byte nonce value goes at the END of the 32-byte field (bytes 76-83), with 24 zero bytes padding at bytes 52-75. Misplacing this produces an invalid hash that `checkMintSolution()` rejects.
- **Function selectors are NOT intuitive**: `challengeNumber()` = `0x8ae0368b`, NOT `0x21d06833`. Always verify with `cast sig "functionName()"`.
- **Gas boost can drain wallet**: On Robinhood Chain with 10-50 gwei base fee, 50x boost means 500-2500 gwei. At 60K gas, that's 0.03-0.15 ETH per TX. A 1.5x boost is usually sufficient for priority.
- **Nonce caching desync**: If using local nonce caching (incrementing on each `sendRawTransaction`), rejected TXes cause nonce desync. All subsequent TXes become invalid. Always fetch nonce from chain with `eth_getTransactionCount(..., "pending")`.
- **Rate limiting on public RPC**: Polling `eth_blockNumber` every 50ms + `eth_call` + `eth_sendRawTransaction` can hit Alchemy's rate limit (HTTP 429). The public RPC (`rpc.mainnet.chain.robinhood.com`) is more forgiving but adds Cloudflare proxy latency.
- **CPU can beat GPU on centralized chains**: The friend's insight — "GPUs have bad networking, CPUs have better networking" — is real. On chains with a single sequencer, network latency matters more than hashrate. A dedicated VPS 10ms from the sequencer can out-compete a GPU miner on Vast.ai with 200ms RTT.
- **Browser miner (hashwood.xyz) is good for testing**: Zero setup, no gas risk for failed TXes. Run this first to understand the protocol before building custom miners.
