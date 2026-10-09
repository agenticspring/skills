# Centralized Sequencer Strategy — Beating GPU Miners on Single-Sequencer Chains

## Core Insight (from an experienced miner)
> "Centralized chains with one sequencer have no hogs in between. Co-locate with their sequencer. Figure out when the new mint window opens. The networking between GPUs is not very good compared to CPUs. When the challenge is easy like this, it's better to go with CPU."

## Why CPU Can Beat GPU on Single-Sequencer Chains

On Ethereum (decentralized mempool), GPU wins because hashrate dominates — thousands of validators compete, and finding the solution FIRST is everything.

On centralized chains (Robinhood Chain, many L2s):
- **One sequencer** processes TX in submission order
- **No mempool competition** — no MEV, no gas wars
- **Network latency matters more than hashrate** — first TX to reach the sequencer wins
- **GPU miners are on cloud GPUs** (Vast.ai, RunPod, Lambda) with shared/variable network
- **Dedicated VPS** has more consistent, lower-latency networking

## The Strategy

### Phase 1: Find the Sequencer
```bash
# DNS resolution shows the backend
dig rpc.mainnet.chain.robinhood.com +short
# → customer-origin.offchainlabs.com (Offchain Labs = Arbitrum infra)
```

### Phase 2: Co-locate
- Check where the sequencer infrastructure is:
  - Cloudflare Ray headers show the serving region
  - tcpdump/traceroute can reveal latency
- Rent VPS in the same region (France VPS for Amsterdam-based sequencer = ~10ms)

### Phase 3: Block Timing
```go
lastBlock := getBlock()
for {
    // Poll aggressively — detect new block immediately
    curBlock := getBlock()
    if curBlock > lastBlock {
        lastBlock = curBlock
        // NEW BLOCK — challenge just rotated!
        // IMMEDIATELY fetch challenge + mine + submit
        break
    }
    time.Sleep(80 * time.Millisecond)
}
```

### Phase 4: Submit Directly
- **DO NOT use Alchemy/Infura** — they add a proxy hop
- Submit TX directly to the chain's public RPC endpoint
- The RPC goes Cloudflare → Envoy → Sequencer
- Cloudflare's anycast finds the closest PoP (Amsterdam for EU VPS)

### Phase 5: Optimize the Pipeline
```go
// Faster than the block time:
// Go miner: mine in ~200μs
// Fetch nonce + gas: ~50ms  (parallel with goroutines)
// Build + sign TX: ~1ms
// Send raw TX: ~50ms
// Total: ~100ms from block detection to TX sent
// Block window: 1 second → 10x headroom
```

### Phase 6: HTTP Keep-Alive
"Send TXN directly, no hogs in between" doesn't just mean skip Alchemy — it also means reuse TCP connections. Without keep-alive, every RPC call does a fresh DNS + TLS + TCP handshake (~10-50ms per call). On a 4-call pipeline (block poll + challenge fetch + nonce/gas + send), that's 40-200ms of wasted latency.

```go
httpClient = &http.Client{
    Transport: &http.Transport{
        MaxIdleConns:    100,
        IdleConnTimeout: 90 * time.Second,
    },
}
```

## Gas Strategy
On centralized sequencers, **gas price does not affect ordering** — the sequencer processes in submission order, not by gas price. Gas boost only matters for:
- Replacing stuck/pending TXes
- Ensuring the TX is processed when the sequencer batches

**Recommendation:** No boost (base gas price). Save ETH for mint fees (0.00005 ETH per mint + gas).

## Key Metrics (from actual runs)
| Metric | Value |
|--------|-------|
| Block time | ~1 second (variable) |
| Solution find time (Go) | 100-500μs |
| TX submission time | ~50-100ms |
| Pipeline total | ~100-200ms |
| Success rate | Low — highly competitive (GPU miners active 24/7) |
| ETH cost per attempt | ~0.00005 ETH mint + ~0.00001 ETH gas |

## When This Strategy Works Best
- **Low difficulty** — CPU can find solutions within the block window
- **Quiet hours** — fewer GPU miners competing
- **New coin launches** — first few blocks have fewer miners
- **Your VPS is geographically close to sequencer** — sub-10ms latency
