# Robinhood Single-Wallet Operation Evidence

Use this reference for a one-wallet mint or ERC-721 transfer on Robinhood Chain (chain ID 4663). It captures the validated sequence from a live OSNM-Z/Alchemy workflow without storing wallet secrets or session-specific credentials.

## Mint sequence

1. Resolve the OpenSea slug and supplied contract together. Query official drop metadata and verify `contract_address`, `chain`, `drop_type`, `is_minting`, `active_stage`, `price`, and `max_per_wallet`.
2. Scope to one wallet and one quantity, for example `SPRING_OSNM_WALLET_SET=1`, `SPRING_OSNM_QUANTITY=1`, and the same wallet as `SPRING_OSNM_RECIPIENT_ADDRESS`.
3. Run `osnm-z doctor`, then wallet-specific `osnm-z calldata --collection <contract-or-slug> --token-id 0` through the `terminal` tool.
4. Require exactly one active stage, authenticated/eligible wallet, intended target, and exact value. A zero-price stage still requires native gas. Do not infer “free” from UI copy if the active stage price is nonzero.
5. Only after explicit mint/broadcast instruction run interactive `osnm-z mint`.
6. Capture the full hash from the CLI. It must match `^0x[0-9A-Fa-f]{64}$`.
7. Verify with Alchemy RPC: receipt status, block number, sender, destination, gas used, effective gas price, value, and ERC-721 `Transfer` logs.
8. Decode the token ID from the Transfer topic and re-read `ownerOf(tokenId)` and `balanceOf(wallet)`. Report `confirmed` only when receipt and post-state agree.

## Transfer sequence

For moving a token from Set 1 to Set 2:

1. Derive the two public addresses ephemerally; never print or persist mnemonic/private-key material.
2. Verify chain ID 4663, `ownerOf(tokenId) == Set1`, and `balanceOf(Set2) == 0` or the intended destination state.
3. Estimate `safeTransferFrom(address,address,uint256)` with `--from Set1` via `terminal`.
4. Broadcast only after explicit transfer instruction.
5. Verify receipt status, Transfer topics, `ownerOf(tokenId) == Set2`, `balanceOf(Set1) == 0`, and `balanceOf(Set2) == 1`.

## Explorer fallback

RPC remains authoritative. For a full valid hash, test the exact URL before reporting:

```text
https://robinhoodchain.blockscout.com/tx/<full-64-hex-txhash>
```

A stale explorer host, DNS failure, HTTP 404, or malformed hash is an explorer problem, not evidence that the transaction failed. Never manually shorten/copy a hash; one missing character causes a misleading invalid-request page.

## Failure corrections

- `calldata inspection requires exactly one active stage`: stop; do not guess a stage or selector.
- `OpenSea reported insufficient wallet funds`: compare exact native wei balance against active stage price plus gas reserve.
- Explorer “invalid request”: validate hash length and query direct RPC receipt before retrying the URL.
- Do not expand a single Set request to all manifest wallets.
