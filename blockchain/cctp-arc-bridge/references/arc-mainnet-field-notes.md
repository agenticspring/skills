# Arc Mainnet Field Notes

## Evidence hierarchy
1. Direct read-only RPC is authoritative for current chain state: `eth_chainId`, `eth_getCode`, `eth_call`, recent blocks.
2. Iris API is authoritative for CCTP route/fee/attestation status.
3. Explorer/indexer data is useful for indexed ecosystem snapshots, but can flap or disappear.
4. Public frontend JS proves application configuration/provenance only; individual addresses may be stale or wrong.
5. Search/social posts are leads, not verification.

## Current Arc facts
- EVM chain ID: `5042` (`0x13b2`); CCTP domain: `26`.
- Primary publicly corroborated RPC: `https://rpc.blockdaemon.mainnet.arc.io`.
- Arc USDC predeploy: `0x3600000000000000000000000000000000000000`.
- CCTP routes to destination domain 26 can return HTTP 200 and fee arrays even when no user transfer has been tested.
- Attestation status must be checked with `/v2/messages/{sourceDomain}?transactionHash=...`; `PENDING` means the specific burn is not ready, not that Iris is offline.

## Explorer behavior
`arc-mainnet.cloud.blockscout.com` has been observed both returning valid `/api/v2/*` data and later returning `404 default backend - 404`. Treat it as intermittent/flapping. `explorer.arc.io` has also redirected to Cloudflare Access. Never use explorer availability as proof that Arc or CCTP is down; fall back to RPC and Iris.

## Factory/token reconnaissance
- Token checks should compare contract address, not symbol. A community meme token can use symbol `USDC`; official Arc USDC is the `0x3600...0000` predeploy.
- For a factory deployment count, do not guess from a recent block window. First test historical `eth_getLogs`; if the RPC returns `pruned history unavailable`, exact historical counts require an archive RPC or a functioning indexer/subgraph.
- A zero-result log query over a readable recent range proves only that range has no matching logs; it does not prove the factory never deployed tokens.
- Factory `owner()` and pool registration are separate facts. A registered pool does not prove LP is locked or that the factory is trustless.

## Provenance example
DYORSwap's public JS bundle included Arc chain ID 5042 and `https://rpc.blockdaemon.mainnet.arc.io`, corroborating RPC provenance. The same frontend contained a stale/mismatched multicall address with no bytecode on current Arc. Validate every copied address with `eth_getCode`; do not copy a frontend chain config wholesale.

## Safe audit boundary
Use read-only calls only for reconnaissance. Do not broadcast transactions, call state-changing methods, or infer exploitability from raw bytecode substring hits (`delegatecall`, `selfdestruct`) without control-flow/source analysis.
