# Mint-Readiness Check — Recipe + Robinhood Chain 4663

## Real case (2026-08-03, A-NONYM @ anonymhood.xyz)

Site was LIVE with a "CONNECT WALLET TO MINT" button, supply 0/10,000, price 0.00055 ETH — but on-chain `mintActive()` was `false`. Mint locked; any attempt would revert and waste gas. Frontend ≠ contract state.

## Robinhood Chain (Chain ID 4663)

Verified working RPCs (all return chain id `0x1237`):

```bash
RPC="https://robinhood-rpc.publicnode.com"
# also: https://rpc.mainnet.chain.robinhood.com
#       https://robinhood.rpc.blxrbdn.com
```

Dead/no response RPCs (do not waste time):
- `https://rpc.robinhoodchain.com`
- `https://mainnet-rpc.robinhoodchain.com`
- `https://rpc.rhchain.io`
- `https://robinhoodchain.drpc.org` (404)
- `https://robinhoodchain-mainnet.rpc.chainstack.com`

Chainlist discovery: `chainid.network/chains/4663.json` was HTML-blocked; the chainlist.org page grep for `https://` gave the live RPCs above.

Explorer: `https://robinhoodchain.blockscout.com` (Blockscout v2 API works for verified contracts).

## Full sequence

```bash
# 1. Verify RPC
cast chain-id --rpc-url $RPC                      # 4663 (0x1237)

# 2. Contract + ABI (verified contracts only)
curl -s "https://robinhoodchain.blockscout.com/api/v2/smart-contracts/$ADDR" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('verified:',d.get('is_verified'),'abi_fns:', sorted(set(a.get('name') for a in (d.get('abi') or []) if a.get('type')=='function')))"

# 3. Read mint state
cast call $NFT "mintActive()(bool)" --rpc-url $RPC          # false = LOCKED
cast call $NFT "mintFinished()(bool)" --rpc-url $RPC
cast call $NFT "mintStatus()(uint256)" --rpc-url $RPC       # 0 = closed
cast call $NFT "price()(uint256)" --rpc-url $RPC
cast call $NFT "maxSupply()(uint256)" --rpc-url $RPC
cast call $NFT "maxPerWallet()(uint256)" --rpc-url $RPC
cast call $NFT "totalMinted()(uint256)" --rpc-url $RPC
cast call $NFT "tokensPerNft()(uint256)" --rpc-url $RPC     # e.g. 1e20 = 100 tokens/NFT
cast call $NFT "owner()(address)" --rpc-url $RPC

# 4. Cross-check transfers
curl -s "https://robinhoodchain.blockscout.com/api/v2/addresses/$NFT/token-transfers" \
  | python3 -c "import sys,json; print('transfer_events:', len(json.load(sys.stdin).get('items',[])))"
```

## Verdict rules

| State | Meaning |
|---|---|
| `mintActive()==false` + `totalMinted()==0` | Mint locked — site is front-running the launch; warn user, do not send tx |
| `mintActive()==true` + `totalMinted()>0` | Mint live and already minting |
| `mintFinished()==true` | Mint ended (sold out / closed) |
| `mintStatus()==0` | Closed/uninitialized gate |

Admin-only setters seen in the wild: `setMintActive`, `setPrice`, `setMaxSupply`, `setMaxPerWallet`, `setToken`, `setHolderSink`, `setNamingConfig` — prepped-but-locked launch = price/supply configured, switch still off.

## Pitfalls

- `mintsLeft()` can revert (`execution reverted`) on some contracts even when mint is simply locked — don't treat that as a bug, use `totalMinted()`/`maxSupply()` instead.
- `cast call` without `--rpc-url` defaults to ETH mainnet → wrong results.
- The `/api/v2/smart-contracts/<addr>` ABI endpoint works only for verified contracts; unverified returns 404 → fall back to selector probing (see umbrella SKILL.md).
