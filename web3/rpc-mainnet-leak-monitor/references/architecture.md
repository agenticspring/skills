# RPC Leak Monitor — v2 Discovery Architecture

## Why v1 was wrong (the circular verifier trap)
v1 probed a hardcoded `seedRPCs` list and alerted if the returned `chainId`
wasn't in the known baseline. That is **circular**: to detect a new chain you
must *already* know its RPC URL. Arc was only caught because `5042.rpc.thirdweb.com`
had been manually added to the seed. The monitor would never surface a chain
whose RPC lived on an un-monitored domain.

Real pre-launch leaks (e.g. Arc: `5042.rpc.thirdweb.com` + `poptyedev.com`)
come from **infrastructure exposure before the official announcement**. The
monitor must *discover* RPCs, not just *verify* known ones.

## v2 source-by-source

### 1. Baseline — `chainid.network/chains.json`
Full chain dump (2654 chains, mainnet+testnet+devnet) → cached to
`known_chains.json`. At runtime `announcedChains` is populated from this cache.
This is the "announced" reference set; anything NOT in it = leak.

### 2. chainlist.org diff — `https://chainlist.org/rpcs.json`
Fetched every cycle. Any `chainId` present here but not yet in `announcedChains`
is logged as "NEW chain listed on chainlist" and merged in. This catches chains
that just went public (e.g. BGGChain 3005, Bery 8379).

### 3. Seed RPCs (sync, report FIRST)
20 known RPC URLs probed with `verifyRPC` (eth_chainId + eth_blockNumber).
Runs synchronously; after `wg.Wait()` the results are passed to
`reportAndSave()` immediately so state is written and alerts can fire even if
the async parts (4 & 5) hang on network.

### 4. CT watchlist (ASYNC, best-effort)
For each provider in `watchlistDomains`, query `crt.sh/?q=%25.<domain>&output=json`.
A brand-new subdomain (e.g. `5043.rpc.thirdweb.com`) = a likely new chain RPC.
Each candidate hostname is turned into RPC URLs via `candidateURLs()` and probed.
Runs inside a `go func(){...}()` that does NOT share the main cycle `wg` — so a
crt.sh 429/timeout cannot stall the cycle. 429 → return silently.

### 5. JS-bundle scraper (ASYNC)
For each domain in `jsFrontends`, fetch the HTML, extract `<script src=...>`,
download each `.js`, and regex for `rpc`/`node`/`chain` URLs + `chainId`/`chain_id`
literals. RPC URLs found are verified; bare `chainId` hits (no resolvable RPC)
are still recorded as signals. Dedupe scanned domains in `state.KnownDomains`.

### 6. Leak detection
`reportAndSave(st, results)`: for each result, if `chainId` is not in
`announcedChains` AND `IsNew`, build the embed and `alertDiscord()`.

### 7. Loop
`time.NewTicker(20 * time.Minute)`; `runCycle` on each tick.

## Why "report before async" matters
crt.sh is heavily rate-limited (429/502, multi-second timeouts). In v2.1 the
CT goroutines shared the cycle's `wg.Wait()`, so the cycle blocked until all CT
queries timed out (up to ~10 domains × 60s). State was never saved mid-cycle.
Fix: `wg.Wait()` only over seed RPCs; CT+JS launch in a detached goroutine that
calls `reportAndSave` itself on completion.
