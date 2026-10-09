# CT Watchlist Domains (RPC / dev-infra providers)

Monitored via `crt.sh/?q=%25.<domain>&output=json` to catch NEW subdomains that
signal a pre-launch chain RPC. A fresh subdomain on one of these = likely new
chain (the way Arc leaked via `5042.rpc.thirdweb.com` + `poptyedev.com`).

## Current list (in `watchlistDomains`)
- `thirdweb.com` — launchpad infra; Arc leaked here (`5042.rpc.thirdweb.com`)
- `poptyedev.com` — Arc dev infra (`real-pump-soon-trust-me-bro-again.poptyedev.com`)
- `quicknode.com` — major RPC provider
- `publicnode.com` — public RPC (Base, Scroll, OP, Sepolia RPCs used as seeds)
- `drpc.org` — RPC aggregator
- `blastapi.io` — RPC provider
- `llamarpc.com` — public RPC (eth.llamarpc.com is a seed)
- `allthatnode.com` — multi-chain RPC

## Query shape
Per domain: `fetchCRT("%25." + domain)` → URL-encoded `%.thirdweb.com`.
Returns all certs whose NameValue contains a subdomain of that provider.

## Filtering (critical)
After fetching, for each `nv` in `NameValue` (split by `\n`):
- strip leading `*.`
- skip if `nv` does NOT contain the watchlist domain
- skip if `nv == domain` (bare) or has no dot
- otherwise build RPC candidate URLs via `candidateURLs(nv)` and `verifyRPC()`

## Do NOT use
- `%25.rpc.%25` wildcard — returns non-crypto infra like `*.rpc.net` (Microsoft
  RPC / network gear), massive false-positive noise.

## To extend
Add more providers as they gain traction (e.g. `onfinality.io`, `ankr.com`,
`getblock.io`, `alchemy.com`). More domains = broader leak coverage, but each
adds crt.sh load (rate-limited) — keep the async/best-effort pattern.
