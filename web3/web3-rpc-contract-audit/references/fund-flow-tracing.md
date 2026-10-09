# Fund-Flow Tracing + Post-Mint Intel (real case: A-NONYM, 2026-08-03)

After verifying mint is live/sold-out, users ask "where did the money go" / "apakah dana di-hold atau dikirim keluar" / "apakah dev WD ke Binance". This is the recipe that worked.

## 1. Enumerate the owner wallet

Owner from the NFT contract: `cast call $NFT "owner()(address)" --rpc-url $RPC`. Then pull the full tx list from Blockscout v2:

```bash
curl -s "https://robinhoodchain.blockscout.com/api/v2/addresses/$OWNER/transactions" \
  | python3 -c "import sys,json; [print(t.get('hash',''), '|', t.get('method',''), '| to:', ((t.get('to') or {}).get('hash','') if isinstance(t.get('to'),dict) else ''), '| val:', float(t.get('value','0') or 0)/1e18) for t in (json.load(sys.stdin).get('items') or [])]"
```

Signals: repeated `withdrawTo` calls to the NFT contract = dev pulling mint revenue. `None` method rows = contract creations (deployer wallet).

## 2. Decode withdrawTo logs (the critical step)

`cast receipt` shows the log **topics[1] = recipient address**, **data = amount in wei**:

```bash
cast receipt $TX --rpc-url $RPC
# logs: [{address: <NFT>, topics: [eventSig, 0x000...RECIPIENT], data: 0x000...AMOUNT}]
```

Decode data: `python3 -c "print(int('0x0429d069189e0000',16)/1e18)"` → 0.3 ETH.

**Don't trust `value` on the tx row** — `withdrawTo` rows show `val: 0.0` because the ETH moves inside the contract call; the actual amount is in the emitted event. Same for `depositNative`/bridge txs.

## 3. Identify destination wallets (bridge vs exchange)

- Get `cast receipt` logs → recipient addresses.
- Check each recipient's role via Blockscout address metadata:
  ```bash
  curl -s "https://robinhoodchain.blockscout.com/api/v2/addresses/$DEST" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('name'), d.get('is_contract'), d.get('is_verified'))"
  ```
- `RelayDepository` (e.g. `0x4cD00E387622C35bDDB9b4c962C136462338BC31`) = **Robinhood Chain bridge contract**, NOT an exchange. `depositNative` into it = cross-chain move (typically to L1 before cashing out). `swapEth` to a router = small swap.
- Scan outbound tx of the intermediary wallet: `.../api/v2/addresses/$INTERMEDIARY/transactions`. Intermediary balance near zero + bridge deposit = funds already moved out of the ecosystem.
- Binance check: compare destinations against known Binance hot-wallet prefixes (`0x28c6c0...`, `0xdfd529...`, `0x56eddb...`, `0x5a52e9...`, `0xf97781...`, `0x9f8f72...`, `0x21a31e...`) — zero matches + only bridge/router destinations = no exchange WD.

## 4. Where did mint revenue go? (vault vs dev)

```bash
cast call $NFT "holderSink()(address)" --rpc-url $RPC   # where mint ETH is designed to flow
cast balance $VAULT --rpc-url $RPC                      # 0 = rewards not started
cast balance $NFT --rpc-url $RPC                        # 0 = contract drained
```

If holderSink = RewardsVault but vault balance is 0 while dev `withdrawTo`-ed the ETH → mint proceeds went to dev-side wallets, not the rewards vault. That's the honest answer to "is the money held or moved".

## 5. Floor price for a fresh chain collection (OpenSea)

OpenSea API needs an API key for `/listings` but these work keyless:

```bash
# Resolve collection by contract:
curl -s "https://api.opensea.io/api/v2/chain/robinhood/contract/$NFT"   # -> collection slug
# Collection stats:
curl -s "https://api.opensea.io/api/v2/collections/<slug>" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('total_supply'), d.get('floor_price'))"
```

Keyless `/collections` often returns `floor_price: None` even when listings exist — use `browser_navigate` on `https://opensea.io/collection/<slug>` instead; the page title embeds floor (`"A Nonym 0.0024 ETH - Collection | OpenSea"`) and the snapshot shows FLOOR PRICE, TOP OFFER, 24H VOLUME, and the cheapest listed items with "Buy now" prices.

## 6. Tracing past a Relay bridge (RelayDepository)

When funds land in a bridge contract, the money is NOT at its final destination yet. Relay (relay.link) is intent-based: deposit locks collateral on the source chain, the relayer pays out on the destination chain. So do NOT expect a matching `execute` tx on the source chain.

- **Deposit event ABI** (verified on `RelayDepository` Robinhood Chain): `RelayNativeDeposit(from, amount, id)` — 3 slots: address, uint, bytes32 requestId. Decode `cast receipt` data the same way as withdrawTo.
- **Is the request still pending?** `cast call $RELAY "callRequests(bytes32)(bool)" $REQID` — `false` = request already processed/consumed; `true` = pending. (Trying to decode the tuple form with the wrong return type gives "buffer overrun" — the actual return is just `bool`.)
- **Relay API status check** (`https://api.relay.link/intents/status/v3?requestId=...`) returns `{"status":"unknown"}` for these deposits without an API key — not a useful signal.
- **Don't waste time scanning execute txs** for the requestId on the source chain: 39+ execute txs had zero match in calldata or logs because settlement happens on the destination chain. `callRequests(id)==false` + `RelayDepository` balance holding = funds still locked as bridge collateral.
- **Cross-chain balance check** (is the same wallet funded on L1?): Etherscan V1 API is deprecated (returns NOTOK). Two verified options (2026-08-03):
  - **Etherscan V2 with API key** — `curl -s "https://api.etherscan.io/v2/api?chainid=1&module=account&action=balance&address=$WALLET&tag=latest&apikey=$KEY"`. Confirmed working chains on free tier: **Ethereum (1), Arbitrum (42161), Polygon (137)**. **NOT supported free: Base (8453), Optimism (10), BSC (56)** — those return "Free API access is not supported for this chain" / NOTOK.
  - **Keyless RPC fallback for unsupported chains** — `curl -s -X POST https://mainnet.base.org -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","method":"eth_getBalance","params":["$WALLET","latest"],"id":1}'` (also `arb1.arbitrum.io/rpc`, `mainnet.optimism.io`, `bsc-dataseed.binance.org`, `mainnet.base.org`). Parse `result` hex /1e18.
  - Zero on every EVM chain + no matching execute on source = funds still in bridge, settled to a non-EVM chain (Relay supports Solana/Tron via custom IDs), or moved to an unknown destination wallet. Honest answer: "cannot confirm final wallet from EVM side alone".

## 6b. BSC nonce check — prove the BNB path when balance is 0

A wallet that bridged to BNB shows 0 balance but a **non-zero nonce** on BSC. This is the cheapest proof that funds passed through BSC even when the explorer APIs are blocked (BSCScan Cloudflare, Etherscan free tier):

```bash
curl -s -X POST https://bsc-dataseed.binance.org -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"eth_getTransactionCount","params":["0x2d5c...ba0c","latest"],"id":1}'
# result: 0x2  → 2 txs on BSC. Combined with 0 balance = received then forwarded (pass-through).
```

Same trick works on any EVM chain: nonce > 0 + balance ≈ 0 = the wallet acted as a transit hop. Pair with `eth_getBalance` for the full picture.

## 6c. Cross-reference public analysts when EVM tracing dead-ends

When your own trace hits a wall (funds left the chain via bridge, no destination wallet found), **search X/web for analysts who already did the work** — this is legitimate corroboration, not a shortcut:

```bash
web_search: "<project> mint fund gone"
web_search: "<project> bridge binance transfer"
```

Real case (A-NONYM 2026-08-03): after EVM-side tracing dead-ended, a tweet by @CrypSaf contained the exact missing pieces — the bridge txn hash (`0xde8605df4e...`, which matched our deposit tx), the **Binance Transfer BSC tx hash** (`0xc6702a72e...`), and the summary "bridged into ~16.98 BNB (~$10k) → sent to a Binance wallet → NOT into the $ANON LP". Read the tweet via `browser_navigate` (the snapshot shows the post text + quoted links). Use it to verify your own flow diagram, then re-check the destination tx via RPC/explorer to confirm rather than trusting the tweet alone. Tweet-embedded tx hashes are often truncated (`0xc6702a72e…`) — treat them as search seeds, match by wallet nonce/count or pull the full hash from an explorer search.

## 7. Blockscout v2 API pagination gotcha

`?page=N` is INVALID on Blockscout v2 (`{"errors":[{"title":"Invalid value","source":{"pointer":"/page"}}]}`). Paginate with the `next_page_params` object from each response, replayed as query params:

```python
import urllib.parse
qs='&'.join(f'{k}={urllib.parse.quote(str(v))}' for k,v in npp.items())
curl -s ".../transactions?{qs}"
```

Also: rate limits return empty bodies (0 bytes) — retry after 2-3s with `-H 'Accept: application/json'`; `cast receipt` needs the FULL 66-char hash (truncated 14-char hashes from print statements fail).

## Verdict phrasing for the user (Indonesian)

- Funds NOT held: state balances (NFT=0, VAULT=0, intermediary≈0) + where they went (bridge/owner).
- "WD ke Binance?" → "tidak ada bukti" if no exchange destination found; name the actual destinations (bridge contract, own wallet).
- Flag as watch-item when rewards vault is still 0 after sold-out — rewards round may never open.
