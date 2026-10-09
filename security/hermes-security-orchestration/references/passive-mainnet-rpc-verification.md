# Passive Mainnet/RPC Verification

Use this checklist when a user asks whether a Web3 project has launched mainnet or leaked a mainnet RPC.

## Evidence order

1. Read the project's official chain documentation and landing page.
2. Check the official node/deployment repository or release notes.
3. Extract explicit network status, chain ID, and RPC URLs from public docs.
4. Verify only documented public RPCs with a harmless JSON-RPC read such as `eth_chainId`.
5. Compare the returned chain ID against the documented network name.
6. Label the endpoint as **documented public testnet/mainnet RPC**, never “leaked,” unless there is direct evidence it was private and unintentionally exposed.

## Proof standard

- “Mainnet under development” in official docs plus matching node-repo status is strong evidence that no public mainnet has launched.
- A testnet RPC responding successfully does not prove mainnet availability.
- Chain ID is necessary but not sufficient: also check network name, explorer, genesis/deployment docs, and official status.
- Search results are discovery data, not authoritative proof; cite the underlying official page.
- Do not enumerate guessed subdomains, scan private infrastructure, or test admin/debug methods.

## Reporting format

```text
Mainnet status: confirmed / not confirmed / unclear
Documented network: name + chain ID
Documented RPCs: URLs
Live harmless check: method + returned chain ID
RPC classification: documented public / possibly private / unknown
Limitations: what was not tested
```

## Example disposition

If official docs say “Mainnet is currently under development,” the node repository says “coming soon,” and the only live endpoints return a documented testnet chain ID, report: **no evidence of mainnet launch; no mainnet RPC leak found; documented testnet RPCs verified**.
