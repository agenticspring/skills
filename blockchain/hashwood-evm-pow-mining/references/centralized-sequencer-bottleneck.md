# Centralized Sequencer Bottleneck Analysis — Hashwood/Robinhood Chain

## The Problem
CPU miners can't compete with GPU miners on Hashwood (Robinhood Chain) despite having optimized Go miners that run at 1M+ KHz. The root cause is RPC latency to the Offchain Labs sequencer.

## Latency Breakdown (measured via HTTP pipelining + Server-Timing headers)

```
Server-Timing: cfEdge;dur=4, cfOrigin;dur=102
```

| Component | Time | Source |
|-----------|------|--------|
| VPS → Cloudflare edge (ping) | 1.2ms | ICMP from France VPS to AMS edge |
| Cloudflare edge processing | 4ms | Server-Timing cfEdge header |
| **CF edge → Origin (Offchain Labs) round-trip** | **102ms** | Server-Timing cfOrigin header |
| Origin processing (estimate) | ~52ms | Half of cfOrigin (other half = network) |
| **Total per eth_call** | **~107-120ms** | Measured with keep-alive connection |
| TLS handshake (first request) | ~93ms | Measured via curl timing |
| Total first request | ~200ms | TCP + TLS + server processing |

## Why This Matters

With a single-sequencer chain (no mempool), the first TX to reach the sequencer wins the block. Our TX path:

```
Block opens → detect (80ms poll) → getWork (110ms) → mine (200μs) → sendTX (110ms) → receipt (110ms) = ~410ms total
```

A GPU miner with a local node:
```
Block opens → detect (<1ms) → getWork (<1ms) → mine (1μs GPU) → sendTX (<1ms) = ~3ms total
```

The 400ms latency gap is insurmountable without a local node.

## Attempted Fixes (all failed to close the gap)

| Fix | Result | Latency saved |
|-----|--------|---------------|
| Go miner (compiled, 1M+ KHz) | ✅ Solutions in 100-500μs | ~0ms (not the bottleneck) |
| HTTP keep-alive | ✅ Reuses connection | ~93ms (TLS saved after first req) |
| Batch RPC | ✅ 2 eth_calls in 1 request | ~110ms |
| Cached nonce + gas price | ✅ Skip 2 RPC calls per cycle | ~220ms |
| Persistent TCP connection (raw tls.Conn) | ✅ No more `Connection: close` issues | ~15ms (TCP saved) |
| Predictive timing + pre-mine | ✅ Solution ready before block opens | ~50ms (poll delay saved) |
| Direct to origin (bypass DNS) | ✅ No change — origin is behind Cloudflare | 0ms |
| Cloudflare Workers | Not attempted — bottleneck is origin, not CF | N/A |

**Final conclusion: Without a local Arbitrum Nitro node, CPU mining against GPU miners on Hashwood v2 is mathematically unwinnable on 1-second blocks.**

## VPS Specs for a Local Node
- CPU: 6 cores ✅
- RAM: 11GB ✅ (Arbitrum Nitro recommends 8-16GB)
- Disk: 189GB free ❓ (depends on chain size — Orbit chains are smaller than L1)
- Network: 1.2ms to CF edge ✅

## What Would Need to Change for CPU to Win

1. **Block time increases** (3+ seconds instead of 1 second) — gives CPU TX time to arrive
2. **Difficulty drops significantly** (so all miners find solutions, not just GPU)
3. **Local node is set up** — removes the 100ms+ RPC bottleneck
4. **Competition decreases** (fewer GPU miners during off-peak hours)
