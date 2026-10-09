# Go Miner v7 — Persistent TCP + All Optimizations

This is the final (most optimized) iteration of the Hashwood Go miner. It was the 7th version and included every optimization tried.

## Architecture

```
main loop (every ~1s)
  │
  ├── goroutine 1: getWork() — batch RPC (challenge + target in 1 HTTP POST)
  │
  ├── goroutine 2: getNonceAndGas() — batch RPC (nonce + gasPrice in 1 HTTP POST)
  │                (caches after first call for subsequent cycles)
  │
  └── after both complete:
      ├── spawn 6 goroutines → mine 1M nonces (takes ~200μs)
      └── if solution found → sendMint():
          ├── sign TX locally (no RPC)
          └── eth_sendRawTransaction (1 RPC call)
          └── poll receipt (up to 5 × 500ms)
```

## Key Component: PersistentRPC

```go
type PersistentRPC struct {
    conn *tls.Conn
    rw   *bufio.ReadWriter
    mu   sync.Mutex
}

func (p *PersistentRPC) do(data string) ([]byte, error) {
    // Reuses the SAME TLS connection across ALL RPC calls
    // Only reconnects if the server drops the connection
    // Builds raw HTTP/1.1 request with keep-alive header
    // Uses bufio.ReadWriter for efficient I/O
}
```

## Latency Budget (measured via Server-Timing header)

```
eth_call via batch RPC:
  ┌────────────────────────────┐
  │ TLS dial (first call only) │  0ms (amortized)
  │ HTTP request serialization │  <1ms
  │ Network → CF Edge          │  1.2ms
  │ CF Edge processing         │  4ms (cfEdge)
  │ CF → Origin round-trip     │  102ms (cfOrigin)
  │ Response parsing           │  <1ms
  ├────────────────────────────┤
  │ Total per eth_call         │  ~110ms
  │ Total per cycle (v7)       │  ~210ms (batch + sendRawTX)
  └────────────────────────────┘
```

## What Didn't Reduce Latency

| Attempt | Result |
|---------|--------|
| Bypass Cloudflare (--connect-to origin IP) | Same latency (still CF) |
| eth_getStorageAt vs eth_call | Same (~200ms) |
| HTTP/1.1 pipelining | Same (origin processing is bottleneck) |
| WebSocket upgrade | Returns 400 |
| Gas boost (50x) | Drained wallet, 0 wins |
| Predictive timing / pre-mine | 60+ reverts, 0 wins |

## The One Thing That WOULD Work

Run a local Arbitrum Nitro node synced to Robinhood Chain. This gives:
- <1ms RPC (local, no network)
- No Cloudflare overhead
- No rate limiting
- Can `eth_sendRawTransaction` directly to the sequencer from the node

## Deploy

```bash
# On VPS with go installed:
cd /root/hashwood-go
# miner_v7.go is at /root/hashwood-go/miner_v7.go on VPS <REDACTED>
go build -o hashminer_v7 miner_v7.go
# Rebuild on the VPS (go 1.25):
cd /root/hashwood-go && go build -o hashminer_v7 miner_v7.go
screen -dmS hashwood-go ./hashminer_v7
```
