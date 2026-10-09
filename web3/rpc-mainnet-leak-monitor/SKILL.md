---
name: rpc-mainnet-leak-monitor
description: Build and run a Go-based passive monitor that detects UNANNOUNCED blockchain RPC endpoints (pre-launch chain leaks — mainnet, testnet, OR devnet) by polling aggregators, probing seed RPCs, and scanning CT logs. Sends Discord webhook (embed) alerts on new chain IDs. No LLM dependency.
---

# RPC Chain Leak Monitor

Detect pre-announcement RPC leaks — chains live on RPC before official launch (e.g. Arc mainnet RPC was live before announcement). Covers mainnet, testnet, AND devnet.

## When to use
- User wants to monitor for new/unannounced blockchain chains (any type)
- User says "monitor rpc leak", "detect new chain rpc", "pre-launch chain detection", "tambahin semua chain"
- First-mover play: get RPC before announcement → deploy/snipe at launch

## User preference (embedded)
- **Pure Go, no LLM.** When Dez asks for monitoring/automation scripts ("Pake sc go aja. Tanpa llm"), build a standalone Go binary — no Python LLM calls, no agent dependency. Hardcode credentials (Discord webhook) or read from env; never call an LLM to decide alerts.
- **Discord webhook, NOT Telegram.** Dez explicitly said "Jangan pake bot tele 😡 / Itu ada yg pake" — do NOT use the Telegram bot for alerts. Use Discord webhook only. When he wants richer output he says "pake embed" → send a Discord rich embed (title + fields + color), not plain text.
- **Detect ALL chains.** When Dez says "tambahkan semua chain aja entah tesnet devnet mainet" → monitor must cover mainnet + testnet + devnet, not just mainnet. Baseline = full `known_chains.json` (chainid.network includes testnets).
- Keep it daemonizable: `screen -dmS` + interval loop, not a one-shot script.

## Architecture (v2 — DISCOVERY MODE)
1. **Baseline**: `chainid.network/chains.json` (2654 chains) → `known_chains.json`
2. **chainlist.org diff**: new listed chains auto-added to baseline (logged)
3. **Seed probe**: verify `eth_chainId`+`eth_blockNumber` on 20 known RPCs (sync, report+saves FIRST — fast cycle)
4. **CT watchlist**: monitor subdomains on RPC/dev-infra providers (thirdweb, poptyedev, quicknode, publicnode, drpc, blastapi, llamarpc, allthatnode) via crt.sh → NEW RPC subdomain = leak. Runs ASYNC (best-effort, doesn't block cycle). crt.sh 429 → skip silently.
5. **JS bundle scraper**: crawl `jsFrontends` domains → extract `chainId` + RPC URLs from `.js` bundles (async)
6. **Leak detect**: `chainId` NOT in baseline → 🚨 Discord embed alert
7. **Loop**: every 20 min

## Build
```bash
export PATH="/usr/local/go/bin:$PATH"
cd /opt/crypto-tools/rpc-monitor
go mod init rpc-monitor  # if first time
go build -o rpc-monitor .
```

## Run (daemon)
```bash
screen -dmS rpc-mon bash -c 'export PATH="/usr/local/go/bin:$PATH"; cd /opt/crypto-tools/rpc-monitor; ./rpc-monitor'
```

## Key code sections (main.go)
- `announcedChains` — **empty at init**, populated from `known_chains.json` (2654 chains incl testnet/devnet) at runtime in `runCycle`. Do NOT hardcode a subset.
- `seedRPCs` — RPC URLs to always probe (mainnet + testnet + devnet + leaked). Add new ones here.
- `fetchAggregatorChains(url)` — parses chainid.network / chainlist format
- `fetchCRT(query)` — crt.sh with 3x retry, 20s timeout, 429=skip
- `verifyRPC(url)` — JSON-RPC `eth_chainId` + `eth_blockNumber`
- `scrapeJSPool(domain)` — crawl frontend, extract chainId+RPC from `.js`
- `candidateURLs(host)` — build RPC URLs from a hostname
- `alertDiscord(msg)` — Discord webhook send with **embed** (red card: Chain ID, Block, Source, RPC, Host)
- `reportAndSave(st, results)` — leak check + alert + save state
- `runCycle(st)` — orchestrates (seed sync, CT/JS async)

## Pitfalls
- **No Telegram, ever.** Dez: "Jangan pake bot tele 😡 / Itu ada yg pake". Alerts go to Discord webhook ONLY. `alertTG` was deleted from code — do not re-add it.
- **Discord embeds, not plain text.** When Dez says "pake embed", build a rich embed: `{"embeds":[{"title","color":15158332,"fields":[...],"footer","timestamp":RFC3339}]}`. Parse chain ID/RPC/block from the msg string → embed fields. Plain `content` text is NOT what he wants.
- **All chains mode (default).** `announcedChains` is empty at init, populated from `known_chains.json` (2654 chains incl testnet/devnet) at runtime. Detects ANY new chain ID — mainnet, testnet, OR devnet. Do not restrict to mainnet.
- **Discovery ≠ verifier (the core lesson).** A monitor that only probes a hardcoded `seedRPCs` list and alerts on unknown `chainId` is CIRCULAR — it can only catch chains you already know the RPC for. Real pre-launch leaks surface from infra exposure: (a) CT-log subdomain watch on RPC/dev providers (`%25.thirdweb.com`, `%25.poptyedev.com`...), (b) JS-bundle scraping of frontend domains for `chainId`+RPC URLs, (c) chainlist.org diff for newly-listed chains. Build the monitor around those passive-discovery sources; keep seed RPCs only as a sanity baseline. See `references/architecture.md`.
- **Provenance is mandatory.** Every candidate must record `source`: `chain-registry`, `chainlist-diff`, `ct-watchlist`, `js-bundle`, `github/public-config`, `search-index`, or `seed/reference`. RPC liveness verification does not prove how the URL was discovered. Never call a seed/reference result a fresh discovery.
- **Passive-source ladder.** Without seed/reference data, use official/public docs and bundles, public registries/diffs, public GitHub/config search, CT logs, and search/social indexing as leads; then verify read-only with `eth_chainId` and `eth_blockNumber`.
- **No-observation boundary.** If no public hostname, registry entry, code/config reference, CT name, or indexed lead exists, there is no URL to test passively. Do not guess hostnames, enumerate private infrastructure, port-scan, or probe random endpoints; state that discovery is underdetermined.
- **Arc lesson.** `5042.rpc.thirdweb.com` and the poptyedev endpoint were present in prior seed/reference material. Their later search-index rediscovery should be labeled `search-index verified`, while the original result remains `seed/reference verified`, not a zero-knowledge discovery. A screenshot is only a lead, never a prerequisite: search by project name + numeric chain ID + `RPC`/`mainnet`, then inspect indexed social posts, provider references, and public code. See `references/discovery-provenance.md`.
- **crt.sh query shape.** Per-watchlist-domain: `fetchCRT("%25." + domain)` → e.g. `%25.thirdweb.com` returns that provider's subdomains. Filter: keep only entries where `nv` contains the domain AND is not the bare domain AND contains a dot. The OLD `%25.rpc.%25` wildcard returns non-crypto infra like `*.rpc.net` (Microsoft RPC) — too noisy, do not use.
- **Report + save seed results BEFORE launching async CT/JS.** Call `reportAndSave(st, seedResults)` immediately after the seed `wg.Wait()`. Then run CT-watchlist + JS-scrape inside a `go func(){ ... }()` that does NOT share the main `wg`. If you block the cycle on crt.sh (`wg.Wait()` over CT goroutines), the monitor stalls 3+ min per domain when crt.sh is rate-limited (429/502) — state never saves, alerts never fire. crt.sh 429 → `return` silently; 20s timeout, 3 retries.
- **Unit-test the alert path without spamming or false negatives.** To verify `alertDiscord` (embed) without a real leak: write a standalone `main.go` in `/tmp/<x>/` that re-declares just `alertDiscord` + its imports and sends a fake chain (e.g. 999999) → expect HTTP 204. Do NOT inject a fake RPC into the running binary's `seedRPCs` to force a leak — `chainlist.org/rpcs.json` is fetched every cycle and will silently re-add the "removed" chain to the baseline, defeating the test. See `references/ct-watchlist-domains.md`.
- **chainid.network slow / down**: falls back to `known_chains.json` cache. Pre-populate if API is down:
  ```bash
  curl -s --max-time 60 "https://chainid.network/chains.json" -o /tmp/c.json
  python3 -c "import json; d=json.load(open('/tmp/c.json')); m={e['chainId']:e['name'] for e in d if e.get('chainId')}; json.dump(m, open('known_chains.json','w'), indent=2); print(len(m))"
  ```
- **Multiple instances**: `pkill -9 -f rpc-monitor` before restart, or you'll get duplicate cycles + duplicate Discord alerts.
- **Orphan screen sessions**: after `pkill`, run `screen -wipe` (dead sessions leave stale markers like "153221.rpc-mon (Dead ???)"); restart with a fresh `screen -dmS rpc-mon`. Verify with `screen -ls | grep rpc-mon`. (Alternatively use `terminal(background=true)` for a tracked session_id.)
- **RPC timeout**: verifyRPC uses 25s timeout. Public RPCs can be slower — increase if needed.
- **Alert dedup**: alert only fires on `IsNew` (first time seen). Wipe `state.json` to re-test.
- **Loop-var capture in goroutines**: when spawning `go func()` inside a `for` loop that reads loop vars (e.g. `nv`, `url`), pass them as params `(url, nv)` — Go <1.22 captures by reference and breaks dedupe/values.

## Verification
- Discord embed alert verified: direct POST with embed payload → HTTP 204.
- Detects (tested): Arc (5042), ETH (1), OP (10), Arbitrum (42161), Base (8453), Blast (81457), Scroll (534352), Sepolia (11155111, testnet), Arc Testnet (5042002), Monad Testnet (10143), Arc Network devnet (`api.arc.network/rpc`).
- 0 false positives on known chains.

## Reference files (in this skill dir)
- `references/architecture.md` — full v2 discovery architecture, the circular-verifier explanation, and why "report seed results before async CT/JS" is required.
- `references/ct-watchlist-domains.md` — the curated provider list, query shape, and filtering rules.

## Test the alert path (dev only)
Write a standalone `main.go` in `/tmp/<x>/` that re-declares `alertDiscord` + its
imports and sends a fake chain (999999) → expect HTTP 204. Do NOT inject a fake
RPC into the running binary's `seedRPCs` to force a leak — `chainlist.org/rpcs.json`
is fetched every cycle and silently re-adds the "removed" chain to the baseline,
so the test never fires.

## Files
- `/opt/crypto-tools/rpc-monitor/main.go` — source
- `/opt/crypto-tools/rpc-monitor/rpc-monitor` — binary
- `/opt/crypto-tools/rpc-monitor/monitor.log` — logs
- `/opt/crypto-tools/rpc-monitor/state.json` — known RPCs (dedupe)
- `/opt/crypto-tools/rpc-monitor/known_chains.json` — full chain cache (2654, incl testnet/devnet)
- `/opt/crypto-tools/rpc-monitor/README.md` — run docs
