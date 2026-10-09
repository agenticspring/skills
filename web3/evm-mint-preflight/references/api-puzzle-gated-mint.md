# API puzzle-gated mint flow (Alien Node pattern)

Mint where a project backend issues a puzzle and only provides a valid
`unsignedTx` after a correct answer; the contract accepts a backend
co-signed transaction. Verified live on Alien Node
(`https://www.aliennode.tech/skill.md`, contract
`0x51C69fDF457D1C0080c505CC210FCbfDDcCD8c85`, Robinhood 4663).

## Flow

```
1. GET  /api/info          → mintActive, supply, remaining, mintPrice, maxPerWallet, maxBatch
2. GET  /api/check/{wallet} → remaining slots, canMint
3. POST /api/puzzle {wallet} (optionally {"quantity":N}) → {puzzleId, question, expiresAt, agentHint}
4. POST /api/solve {wallet, puzzleId, answer} → {unsignedTx, mintPrice, quantity, totalCost, agentHint}
   unsignedTx = {to: contract, data: mint(quantity,nonce,signature), value: qty*price, chainId}
5. Sign LOCALLY (PK never leaves the machine), add gas + nonce, type 2:
   ethers: wallet.signTransaction({...unsignedTx, gasLimit, maxFeePerGas,
   maxPriorityFeePerGas, nonce, type:2})
6. POST /api/submit {signedTransaction} → {success, tokenId(s), hash, message, agentHint}
7. Verify receipt + ownerOf + balanceOf via RPC (never trust API success alone)
```

## Constraints (from skill.md + live runs)

- mintPrice 0.0005 ETH, max 20/wallet, batch max 5, puzzle expiry 5 min, 3
  attempts per puzzle, 413 = mint_limit_reached.
- First mint always single (quantity 1); offer batch only after first success.
- Every response has `agentHint` — read and follow it.
- Contract only mints with a valid backend co-signature over
  (minter, quantity, nonce, contract, chainId) — puzzle gate cannot be
  bypassed.
- ethers fallback: `node -e "require('ethers')"` fails → `npm install --prefix
  /tmp ethers` then run with `NODE_PATH=/tmp/node_modules`.
- Balance gate BEFORE requesting a puzzle: need `qty*price + gas`; the backend
  does not fund the minter.

## Local-signing runner (verified)

Reuse a single signer script that reads PK from a 0600 /dev/shm file and
unsignedTx JSON from disk, signs with live fee data + nonce, prints the raw
signed tx for /api/submit. Keep the PK file out of chat, logs, and the repo.

## Safety

- Never send the private key to the API or any remote service; sign locally.
- Check `/api/check/{wallet}` remaining slots before each mint.
- After submit, always confirm on-chain receipt status + Transfer log + owner.
