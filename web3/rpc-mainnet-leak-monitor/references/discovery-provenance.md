# Discovery Provenance

## Required record

For every RPC candidate, store:

- URL/hostname
- chain ID
- block number and timestamp
- discovery source
- verification source
- whether the URL was already present in a seed/reference database

## Source labels

- `seed/reference`: came from a hardcoded seed, prior skill, cache, or prior session.
- `chain-registry`: came from chainid.network/chains.json or equivalent registry.
- `chainlist-diff`: newly appeared in a registry diff.
- `ct-watchlist`: hostname discovered through Certificate Transparency logs.
- `js-bundle`: extracted from a public frontend bundle.
- `github/public-config`: found in public code/config/docs.
- `search-index`: found through public search indexing or indexed social posts.

## Discovery workflow

A screenshot is optional, never a prerequisite. For seed-independent discovery,
start with public observables: search queries combining project/chain name,
numeric chain ID, `RPC`, and `mainnet`; indexed social/provider references;
public GitHub/config/release artifacts; CT hostnames; public JS/config bundles;
or registry deltas. Then resolve and verify the candidate read-only.

## Verification

Use `eth_chainId`, `net_version`, and `eth_blockNumber`. Liveness identifies the
chain but does not prove official ownership, private disclosure, or authorization.
Record DNS, timestamp, source, query/discovery URL, and response values.

## Arc example

The Arc endpoints `https://5042.rpc.thirdweb.com` and the poptyedev hostname were
already present in prior reference/seed material. A later public search result can
be recorded as `search-index` rediscovery, but the first known provenance remains
`seed/reference`. A public search result also surfaced `rpc.blockdaemon.mainnet.arc.io`,
which was DNS-resolved and RPC-verified as chain 5042. The correct claim is
“public search-index candidate, then RPC-verified,” not “credential leak.”

## Negative-result rule

If no public observation supplies a hostname or URL, passive tooling cannot
determine which endpoint to test. Do not guess hostnames or scan private
infrastructure. Report the discovery boundary and request an authorized seed or
scope.

## Minimal evidence format

```text
candidate: https://example.invalid
source: ct-watchlist
observed_at: 2026-01-01T00:00:00Z
eth_chainId: 0x...
net_version: ...
eth_blockNumber: 0x...
official_status: unverified
```
