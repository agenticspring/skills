# DYORSwap Arc Mainnet provenance

## Source chain
- X post: `https://x.com/i/status/2065439940377477253`
- Redirect target: `https://dyorswap.org/?chainId=5042`
- Public bundle: `/_next/static/chunks/pages/_app-86699f06d0fc1d15.js`

## Extracted Arc configuration
```text
chain ID: 5042
RPC: https://rpc.blockdaemon.mainnet.arc.io
Explorer: https://explorer.arc.io/
native currency: USDC, 18 display decimals
frontend multicall entry: 0x942Bd5BFdc5317C5507e326f8EB4BB6058AB5C10
```

## Read-only verification
The RPC answered `eth_chainId = 0x13b2` and served live blocks. The configured multicall address returned empty code (`0x`) when checked with `eth_getCode` on the same RPC. Treat the frontend entry as stale or mismatched; do not use it without a fresh deployment check.

## Evidence classification
- RPC URL provenance: `public-JS-config` corroborated by public social post and live JSON-RPC.
- Official Arc/Circle endorsement: not established.
- Contract config correctness: partially disproved by the empty multicall code result.

## Reusable lesson
A public frontend is a useful source for discovering an endpoint, but it is not an authoritative chain registry. Extract the chain config, then independently verify chain ID, latest block, every configured contract's bytecode, and explorer/API behavior.
