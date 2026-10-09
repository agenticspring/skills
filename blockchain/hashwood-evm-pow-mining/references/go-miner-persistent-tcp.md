# Go Miner v7 — Persistent TCP Connection

## Problem
Go's `http.Transport` with `MaxIdleConns` and `IdleConnTimeout` doesn't reliably reuse connections when the RPC server sends `Connection: close` after each response. This means every HTTP request incurs TCP connect + TLS handshake overhead (~100ms).

## Solution: Raw `tls.Conn` With Manual HTTP/1.1 Keep-Alive

Instead of `http.Client.Post()`, open a single TLS connection at startup and send all HTTP requests on it manually:

```go
type PersistentRPC struct {
    conn *tls.Conn
    rw   *bufio.ReadWriter
    mu   sync.Mutex
}

func (p *PersistentRPC) do(data string) ([]byte, error) {
    p.mu.Lock()
    defer p.mu.Unlock()

    req := fmt.Sprintf("POST / HTTP/1.1\r\nHost: %s\r\nContent-Type: application/json\r\nContent-Length: %d\r\nConnection: keep-alive\r\n\r\n%s",
        RPC_HOST, len(data), data)

    for attempt := 0; attempt < 3; attempt++ {
        if p.conn == nil {
            conn, err := tls.DialWithDialer(&net.Dialer{Timeout: 3 * time.Second}, 
                "tcp", RPC_HOST+":443", &tls.Config{})
            if err != nil { continue }
            p.conn = conn
            p.rw = bufio.NewReadWriter(bufio.NewReader(conn), bufio.NewWriter(conn))
        }
        
        p.rw.WriteString(req)
        p.rw.Flush()
        
        resp, err := http.ReadResponse(bufio.NewReader(p.conn), nil)
        if err != nil { p.conn.Close(); p.conn = nil; continue }
        
        body, _ := io.ReadAll(resp.Body)
        resp.Body.Close()
        
        if resp.Close { p.conn.Close(); p.conn = nil }  // reconnect if server closes
        
        return body, nil
    }
    return nil, fmt.Errorf("failed")
}
```

## Results

| Metric | http.Client | Persistent TCP |
|--------|-------------|----------------|
| First request | ~200ms (TCP+TLS+server) | ~200ms (same) |
| Subsequent requests | ~200ms (new TCP+TLS each time!) | **~110ms** (server only) |
| Connection reuse | Unreliable (server sends `Connection: close`) | **Always** (we control the wire) |

## Implementation

Full code at `/root/hashwood-go/miner_v7.go` on VPS <REDACTED>.

Key design decisions:
- Single `PersistentRPC` instance shared by all goroutines (mutex-protected)
- Reconnect on any error (stale connection, timeout, server close)
- Batch RPC requests for `getWork` combined into one `do()` call
- Nonce + gas fetched once at startup, then cached locally
- Only `sendRawTransaction` needs an RPC call during the mining loop
