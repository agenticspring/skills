---
name: nft-drop-launch
description: Use when creating or deploying your own NFT drop on OpenSea.
version: 1.0.0
author: spring
license: MIT
metadata:
  hermes:
    tags: [opensea, nft, seadrop, drop, deploy, allowlist, robinhood-chain]
    related_skills: [opensea-nft-operations, evm-wallet-set-management, web3-freemint-batch-execution]
---

# NFT Drop Launch (OpenSea programmatic)

## When to Use
- User wants to CREATE their own NFT collection/drop on OpenSea (not mint someone else's).
- Deploying a SeaDrop ERC721/ERC1155 contract on any OpenSea-supported chain.
- Configuring allowlist/GTD + public sale stages for a drop.
- Chain of interest includes Robinhood Chain (chainId 4663) — verified live 2026-08-24.

## The key endpoint: `POST /api/v2/drops/deploy`

OpenSea API v2 builds the ready-to-sign deployment transaction for you. No
Solidity, no forge needed:

```json
POST https://api.opensea.io/api/v2/drops/deploy
x-api-key: <key from developer-approved account>
{
  "chain": "robinhood",
  "contract_name": "...",
  "contract_symbol": "...",
  "drop_type": "seadrop_v1_erc721",
  "sender": "<deployer address>",
  "token_type": "erc721_standard"
}
```

Response 200: `{chain, data (creation bytecode), to ("0x000…0" = contract
creation), value}`. Sign `data` with the sender wallet and broadcast to chain.

- Valid `token_type`: `erc721_standard | erc721_clone | erc721_upgradeable |
  erc1155_standard | erc1155_clone | erc1155_upgradeable`. Bare `"erc721"` is
  rejected with the full list (useful discovery trick when docs are thin).
- Requires an API key from a developer-approved account
  (`isDeveloperAccountApproved` true — checkable via SIWE flow,
  see opensea-nft-operations).
- After broadcasting, configure stages and verify with `GET /api/v2/drops/{slug}`
  (stages, price, max_per_wallet, times). Existing RH drops use stage types
  `signed_presale` (GTD) and `public_sale`.

## Auth quirks that waste hours if unknown

1. **SIWE nonce/verify endpoints return JSON only with `accept: application/json`.**
   Reusing a page-fetch header builder with `accept: text/html` makes them return
   the Next.js HTML shell → `JSON.parse` crash. Keep a JSON-only header set for
   auth calls.
2. **Save the cookie jar immediately after verify** — access_token/refresh_token
   land in the verify response's Set-Cookie headers.
3. **Cookies do NOT carry into headless-browser sessions of opensea.io.** The
   studio web app reads auth from the Privy SDK's localStorage/IndexedDB state;
   cookie injection alone still shows "Connect Wallet". Don't burn time on it.
4. **gql.opensea.io uses Apollo persisted queries** — introspection returns
   empty (`mutationType.fields: []`). Studio mutations are only reachable via
   sha256Hash registry entries baked into their app bundles. The REST
   `/drops/deploy` route above is the supported programmatic path; use it
   instead of reverse-engineering GraphQL.
5. Studio UI route: `https://opensea.io/studio/create/collection` (requires the
   full browser Privy session). Manual fallback if API path breaks.

## Robinhood Chain facts

- chainId `0x1237` = **4663**. Alchemy:
  `https://robinhood-mainnet.g.alchemy.com/v2/<key>`.
- Public RPC: `https://rpc.mainnet.chain.robinhood.com`.
- OpenSea chain slug: `robinhood`; studio registry says
  `contractDeploymentEnabled: true`.
- Deploy gas observed: ~4.5M units, base fee ~20 gwei → ~0.0002 ETH. Keep
  ≥0.002 ETH in the deployer wallet for deploy + stage config.
- Existing drops pattern: seadrop_v1_erc721 with GTD presale then public sale,
  price in native ETH (`price_currency_address` = zero address).

## Launch sequence

1. Verify chain slug via `GET /api/v2/chains`.
2. Confirm deployer wallet funded (gas estimate × buffer).
3. `eth_estimateGas` the returned deploy payload before signing.
4. Sign + broadcast; persist TxHash; get contract address from receipt.
5. Configure drop stages (allowlist proofs/vouchers + public params).
6. Verify via `GET /api/v2/drops/{slug}`; only then wire up mint testing.
