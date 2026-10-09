# Go Miner Architecture — Hashwood PoW

## Evolution
The Go miner went through 4 versions during a single session:

| Version | Key Change | Speed | Outcome |
|---------|-----------|-------|---------|
| v1 | goroutine + go-ethereum TX signing | ~200μs mining | All reverted (gas too low) |
| v2 | Gas saver with checkMintSolution + block detection | ~200μs | 0 gas wasted but no mints (check always returned false — bug) |
| v3 | Direct to sequencer (skip Alchemy), fire-and-forget TX | ~200μs | Gas drained by 50x boost + nonce desync |
| v4 | Block timing strategy — poll block every 80ms, mine on block change | ~200μs | Ready but out of ETH to test |
| v5 | Predictive timing + keep-alive + parallel RPC + cached nonce/gas | ~200μs | Lowest latency achieved; still lost to GPU competition |

## Code Structure
```
/root/hashwood-go/
├── go.mod
├── miner.go       # v1: basic goroutine miner with go-ethereum signing
├── miner_v2.go    # v2: gas saver + block detection
├── miner_v3.go    # v3: direct sequencer, fire-and-forget
├── miner_v4.go    # v4: block timing strategy
├── hashminer      # compiled binaries
├── hashminer_v2
├── hashminer_v3
└── hashminer_v4
```

## Key Components

### RPC Layer
```go
var httpClient = &http.Client{Timeout: 5 * time.Second}
func rpc(method string, params []interface{}) ([]byte, error) {
    // JSON-RPC over HTTP directly to RPC_SEQ
}
```

### Mining Loop (v4 — block timing)
```go
for {
    // Poll until block changes (someone minted)
    for {
        curBlock := getBlock()
        if curBlock > lastBlock { break }
        time.Sleep(80 * time.Millisecond)
    }
    // New block → challenge just rotated
    challenge, target := getWork()
    // Mine with goroutines
    // Submit solution
}
```

### TX Submission (v3/v4 — fire and forget)
```go
func sendMint(nonce, digest []byte, pk *ecdsa.PrivateKey) bool {
    // 1. Fetch nonce from chain (eth_getTransactionCount, "pending")
    // 2. Fetch gas price (eth_gasPrice)
    // 3. Build & sign TX using go-ethereum types
    // 4. eth_sendRawTransaction
    // 5. Poll receipt (5 attempts, 500ms each)
    // 6. Return receipt.Status == "0x1"
}
```

### Gas Caching (v2)
```go
var gpCacheHex string
var lastGasUpdate time.Time
var gpMu sync.Mutex
// Update gas price every 30s instead of every TX
```

## Optimizations Learned

### HTTP Keep-Alive (CRITICAL for latency)
Each RPC call creates a NEW TCP connection by default. This adds TLS handshake + TCP slow-start latency (~10-50ms). On a chain where blocks are 1-second windows, that overhead is significant.

```go
var httpClient = &http.Client{
    Timeout: 5 * time.Second,
    Transport: &http.Transport{
        MaxIdleConns:    100,
        IdleConnTimeout: 90 * time.Second,
    },
}
```

With keep-alive, subsequent RPCs reuse the same TCP connection → save ~10-50ms per call. For the 3-RPC pipeline (nonce → gas → send), this saves 30-150ms total.

### Parallel RPC Calls
`eth_getTransactionCount` and `eth_gasPrice` are independent — fetch them concurrently:

```go
ch := make(chan rpcResult, 1)
go func() {
    nonce := getNonce()
    gp := getGasPrice()
    ch <- rpcResult{nonce, gp}
}()
result := <-ch
```

### Pre-Sign TX
If you cache nonce and gas price, sign the TX once and keep it in memory. When the block opens, just `eth_sendRawTransaction` — 1 RPC call.

## Critical Bugs Found & Fixed

### 1. Nonce Byte Order (BROKEN → FIXED)
The 32-byte nonce field requires the 8-byte value at the END (bytes 76-83), not the start. The wrong layout was:
```go
msg[52:60] = nonce.to_bytes(8, 'big')  // WRONG
msg[60:84] = b'\x00' * 24
```

### 2. Function Selectors
Used wrong selectors in early versions:
- `challengeNumber()` is `0x8ae0368b`, NOT `0x21d06833`
- `miningTarget()` is `0x8a769d35`, NOT `0x61461954`  
- `checkMintSolution(uint256,address)` is `0x9d7a7cc6`, NOT `0x21e7b51d`

### 3. Gas Boost Explosion
50x gas boost on Robinhood Chain (base 10-50 gwei) = 500-2500 gwei. At 60K gas = 0.03-0.15 ETH per TX. Burned through 0.0016 ETH in 20+ reverts.

### 4. Nonce Caching Desync
Incrementing a local nonce counter on every `sendRawTransaction` causes desync when TXes are rejected. All subsequent TXes become invalid. Always fetch nonce from chain.

## Direct Sequencer Discovery
- DNS: `rpc.mainnet.chain.robinhood.com` → CNAME → `customer-origin.offchainlabs.com`
- Backend: Offchain Labs (Arbitrum) — centralized sequencer infrastructure
- Proxy: Cloudflare → Envoy/Istio → Sequencer
- VPS location: France (FR) — ~10ms latency to Amsterdam (where Cloudflare routes to)
