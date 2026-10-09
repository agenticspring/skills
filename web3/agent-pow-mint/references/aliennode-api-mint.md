# AlienNode API-puzzle mint — verified walkthrough (2026-08-17)

Site: `https://www.aliennode.tech` (skill.md at `/skill.md`).
Collection: 3,333 "Alien Node" on Robinhood 4663. Mint price `0.0005 ETH`
(+gas ~0.00002). Max 20/wallet, batch max 5 per tx.

## Protocol

```
puzzle → solve → sign locally → submit
```

Endpoints:

| Method | Endpoint | Body |
|---|---|---|
| GET | `/api/info` | — |
| GET | `/api/check/{wallet}` | — |
| POST | `/api/puzzle` | `{"wallet":"0x…"}` (optional `"quantity":N` ≤5) |
| POST | `/api/solve` | `{"wallet":"0x…","puzzleId":"pzl_…","answer":"78"}` |
| POST | `/api/submit` | `{"signedTransaction":"0x02f8…"}` |

## Verified run (Set 1, token #284)

1. `POST /api/info` → `minted:249, supply:3333, mintActive:true,
   mintPrice:"0.0005", maxPerWallet:20, maxBatch:5`.
2. `POST /api/puzzle` → `{"puzzleId":"pzl_…","question":"What is 31+7+40?",
   quantity:1, expiresAt, agentHint}`.
3. Solve → `POST /api/solve` with answer `78` → `unsignedTx`:
   `{to:0x51C6…C85, data:0x9ab475b5…, value:0x1c6bf52634000 (=0.0005 ETH),
   chainId:4663}`. Data selector `0x9ab475b5` = `mint(uint256,bytes32)`
   carrying a backend co-signature.
4. Sign locally with ethers:
   ```js
   const signed = await wallet.signTransaction({...unsigned, gasLimit:250000,
     maxFeePerGas:(fee.maxFeePerGas ?? fee.gasPrice)*2n,
     maxPriorityFeePerGas:fee.maxPriorityFeePerGas ?? 10000000n,
     nonce: await provider.getTransactionCount(wallet.address), type:2});
   ```
   ethers install if missing: `npm install --prefix /tmp ethers`, run with
   `NODE_PATH=/tmp/node_modules`.
5. `POST /api/submit` `{"signedTransaction":"0x02f8…"}` →
   `{success:true, tokenId:"284", hash:"0x14fc…", message:"Successfully minted
   1 Alien Node: #284."}`.
6. Verify: `cast receipt` status 1 (block 38859891, gasUsed 132509),
   `ownerOf(284)` = Set 1, `balanceOf` = 1.

## Notes / pitfalls

- First mint is always single (`quantity:1`); batch offered after first
  success (up to min(remaining,5)).
- Puzzle expiry 5 min, 3 attempts per puzzle.
- HTTP 413 `mint_limit_reached` = 20/wallet cap — use a different wallet.
- Read `agentHint` in every response; the backend re-issues hints per step.
- Private key never leaves local env; only the signed tx string is posted.
- The contract mint function is gated by a backend co-signature over
  `(minter, quantity, nonce, contract, chainId)` — puzzle gate is not
  bypassable on-chain.
