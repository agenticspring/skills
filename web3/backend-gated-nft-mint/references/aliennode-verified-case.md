# AlienNode verified case (2026-08-17)

Full verified run of the backend-gated mint pattern on
https://www.aliennode.tech/ (Robinhood Chain 4663).

## Project metadata (from site /skill.md)

- Contract: `0x51C69fDF457D1C0080c505CC210FCbfDDcCD8c85` (Alien Node, ERC-721)
- Supply: 3,333; mint price `0.0005 ETH`; max 20/wallet; batch up to 5
- Chain: robinhood, chain_id 4663
- API base: `https://aliennode.tech/api`
- Gate: arithmetic puzzle (add/sub/mul/div/mod/squares/half/double/
  three-number sum/decimal conversions), 5-min expiry, 3 attempts
- Backend co-signs `(minter, quantity, nonce, contract, chainId)`; puzzle
  gate cannot be bypassed on-chain

## API contract (verified live)

| Endpoint | Method | Notes |
|---|---|---|
| `/api/info` | GET | minted, supply, remaining, mintActive, mintPrice, maxPerWallet, maxBatch |
| `/api/check/{wallet}` | GET | remaining, maxPerWallet, canMint |
| `/api/puzzle` | POST | body `{"wallet": ...}` (optional `"quantity":N`) → `{puzzleId, question, quantity, expiresAt, agentHint}` |
| `/api/solve` | POST | body `{wallet, puzzleId, answer}` → `{unsignedTx{to,data,value,chainId}, mintPrice, quantity, totalCost, agentHint}` |
| `/api/submit` | POST | body `{signedTransaction:"0x..."}` → `{success, tokenId, tokenIds, quantity, hash, message}` |

## Mint 1 (success)

- Balance before: `0.000839577783577879` ETH
- Puzzle: `What is 31 + 7 + 40?` → answer `78`
- unsignedTx: to contract, data `0x9ab475b5...` (mint(quantity,nonce,sig)),
  value `0x1c6bf52634000` (0.0005 ETH), chainId 4663
- Signed locally with ethers (gasLimit 250000, maxFeePerGas 2x,
  maxPriorityFeePerGas 10000000, nonce from provider)
- TxHash: `0x14fc3cf6b2cef279d6a1445728197820d81f4dce4a0648d01055082d4aaf67e8`
- Token ID: 284; receipt status 1; gas used 132509; ownerOf(284)=Set1;
  balanceOf=1; final balance `0.000336917797911879`

## Mint 2 (success)

- Balance after top-up: `0.000863933346520804` ETH
- Puzzle: `What is 21 + 33 + 6?` → answer `60`
- TxHash: `0xbf154a21ef64a94ae3ab68cdec238529caf6ccea3167e0a7ee1a10bb2f3acb57`
- Token ID: 1630; receipt status 1; gas used 98133; ownerOf(1630)=Set1;
  balanceOf=2; final balance `0.000361920246158804`

## Security notes

- Private key derived in memory from `.springwallet`, staged at
  `/dev/shm/alien-pk` (0600), never sent to the API.
- Signing scripts: `/tmp/alien-sign.js` (reads `/dev/shm/alien-pk` +
  `/tmp/alien-unsigned.json`, writes signed tx to stdout).
- No tx broadcast by us directly — the backend submits; we verify receipt
  and ownership via Alchemy RPC afterwards.

## Lessons

- `cast wallet sign --data <hex>` failed for the plain-message case; the
  site uses `personal_sign` semantics → ethers `wallet.signMessage` is the
  correct primitive for message signing; `wallet.signTransaction` for the
  unsigned tx.
- The unsigned tx from the backend has NO gas/nonce — the client must fill
  them. Without that, signing produces an invalid tx.
- Each mint is a fresh puzzle; token IDs are NOT sequential per wallet.
