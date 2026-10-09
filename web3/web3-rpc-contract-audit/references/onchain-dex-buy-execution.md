# Executing a swap on a fresh chain's DEX

Write-side counterpart to the read-only census work. Worked end-to-end on a leaked OP Stack L2
(chain 9134, 2026-09-27): 3 buys filled, 0 failed, ~0.0182 ETH deployed.

The governing rule: **find a call shape that has provably worked before, then prove your own fill
from the receipt.** Everything below exists to satisfy those two clauses.

---

## 1. Harvest the DEX contract set from the app's JS bundle

The token page is a thin client. Its config object carries the whole contract set.

```python
r  = requests.get(f"https://<app>/token/{TOKEN}?chain=<slug>", headers={"User-Agent": "Mozilla/5.0"})
js = re.findall(r'src="([^"]+\.js[^"]*)"', r.text)
blob = "".join(requests.get(u if u.startswith("http") else base + u).text for u in js)
# then grep the minified config:
#   swapRouter:b("0x1F79…"), v3Factory:b("0x245e…"), positionManager:b("0x8280…"),
#   quoter:b("0x2B6e…"), pairToken:b("0x4200…0006"), multicall:b("0xca11…")
```

Also grab the site's own API host from the HTML (`giwa-api-production-*.up.railway.app`) and try
`/api/tokens` — an empty array there is a signal the front end is decorative and the chain is the
only truth.

Worked set (venue ran **its own** V3 stack, not the chain's earlier Uniswap deployment):

| role | address |
|---|---|
| v3Factory | `0x245e264705A457a1d79DE41573479627018a2120` |
| swapRouter | `0x1F7904e0379b2179D1716651dBc2EA7bf866fb21` |
| positionManager | `0x82804a2abCD91a288483E9175D1C9a215d9AD0aE` |
| pairToken (WETH) | `0x4200000000000000000000000000000000000006` |
| multicall3 | `0xcA11bde05977b3631167028862bE2a173976CA11` |

Cross-check each against `eth_getCode` — and note the chain had a **second, unrelated factory**
earlier in its history. Only this one had the pool.

## 2. Find the pool, and read it

```python
for fee in (100, 500, 3000, 10000):
    p = call(FACTORY, "getPool(address,address,uint24)", pad(TOKEN) + pad(WETH) + enc(fee))
```

One non-zero hit at fee `10000`. Then:

```
pool.token0()      -> 0x4200…0006 (WETH)
pool.token1()      -> <TOKEN>
pool.liquidity()   -> 57742791865701158097912
pool.slot0()       -> sqrtPriceX96 = 252909857272233766773933940668740
WETH.balanceOf(pool)  -> 14906772978245592403   (14.91 WETH ≈ $40k)
TOKEN.balanceOf(pool) -> 184380691565639061047503009
eth_getBalance(pool)  -> 0.0      # correct: WETH lives in the WETH9 erc-20, not as native ETH
```

**The native-balance read being `0` for a WETH pool is expected and must not be reported as
"no liquidity".** Read the WETH9 ERC-20 balance.

Liquidity sanity check: the site advertised `Liquidity $39.80K`; on-chain 14.91 WETH matched. When a
UI claim and the chain disagree, the chain wins.

Price: `price = (sqrtPriceX96 / 2**96)**2` → token1 per token0 → `1 ETH ≈ 10,189,957 TOKEN`.
Track it across fills — an all-buy pool drifts: this one moved from 10,079,891 → 7,295,237 TOKEN/ETH
(**+37 %**) between two of the user's own buys.

## 3. Copy the calldata from a real tx

Scan the pool's `Swap` topic, take a recent tx, dump its `input`:

```python
SWAP = topic("Swap(address,address,int256,int256,uint160,uint128,int24)")
logs = getLogs(fromBlock=0, toBlock=head, topics=[SWAP])           # topic-only!
pool_logs = [l for l in logs if l["address"].lower() == POOL.lower()]
tx = eth_getTransactionByHash(pool_logs[-1]["transactionHash"])
print(len(tx["input"])//2-1, tx["input"][:200])
```

Result: **260 bytes**, selector `0x414bf389` — the 8-field `exactInputSingle`. So the venue is
Uniswap-V3-compatible at the router boundary even though its own factory/pool are custom.

```
exactInputSingle((address tokenIn, address tokenOut, uint24 fee, address recipient,
                  uint256 deadline, uint256 amountIn, uint256 amountOutMinimum,
                  uint160 sqrtPriceLimitX96))       selector 0x414bf389
```

Encode (paying **ETH**, router auto-wraps to WETH):

```
selector
+ tokenIn  = WETH 0x4200…0006
+ tokenOut = TOKEN
+ fee      = 10000
+ recipient= buyer
+ deadline = now + 1200
+ amountIn = wei
+ amountOutMinimum = floor
+ sqrtPriceLimitX96 = 0
```

`cast 4byte-decode <input>` on a captured tx confirms the argument order before you commit.

## 4. Simulate, floor, re-simulate

```python
q = eth_call({"from": ME, "to": ROUTER, "data": data_min0, "value": hex(IN_WEI)})
quote = int(q, 16)                       # 37,318.2550 TOKEN for 0.0037 ETH
data  = rebuild(min_out=int(quote * 0.90))
sim   = eth_call({... "data": data ...}) # MUST still succeed before broadcasting
```

The quote is not a promise. One fill received **96.8 %** of quote in the same block (price moved
during inclusion); the 90 % floor is what protects the buyer. A floor of `0` removes the only
protection a thin pool offers.

Gas: `estimateGas` ≈ 188–206 k, limit = estimate × 1.3 ≈ 245–268 k. **Never** double the estimate
(see the pitfalls in SKILL.md — it becomes an `insufficient funds` rejection).

## 5. Honeypot: census the Swap signs

```python
for l in pool_logs:
    a0 = int(l["data"][2:66], 16)          # int256, two's complement
    buy  += a0 > 0                          # pool RECEIVED token0
    sell += a0 < 0                          # pool PAID OUT token0
```

Worked result: **91 swaps, 91 buys, 0 sells.** Verdict language matters — the sell path is
**unverified, not proven broken**. Cross-check the sign against tx `value` (buys carry ETH, sells
often `0`) before publishing the count; inverting this produced a wrong first answer.

Once the user is holding, offer the sell test: it costs one gas fee and is the only way to convert
"unverified" into an answer.

## 6. Verify the fill — from the receipt, never from a balance read

```python
rc = eth_getTransactionReceipt(H)
assert rc["status"] == "0x1"
TR = topic("Transfer(address,address,uint256)")
for lg in rc["logs"]:
    if lg["topics"][0].lower() == TR.lower():
        f, t = topic_address(lg["topics"][1]), topic_address(lg["topics"][2])
        v = int(lg["data"], 16) / 1e18
        if t.lower() == ME.lower():
            print("DELIVERED", v, "from", f)
```

Worked receipt for a 0.0037 ETH buy — 4 logs:

```
Transfer <TOKEN>   37,318.2550   pool -> buyer        <<< delivery proof
log @0x4200…0006   (Deposit — WETH wrap)
Transfer <WETH>     0.0037       router -> pool
log @<pool>        (Swap)
```

Then read the balance **with a retry loop**, and only for confirmation — never as the primary
evidence.

### Why this ordering is mandatory

The naive version of this script printed:

```
TILE sebelum : 0.0000
TILE sekarang: 0.0000
DAPAT        : 0.0000 TILE  (❌ nggak dapat)
kepakai      : 0.00387469 ETH
```

i.e. *"spent the ETH, received nothing"* — on a transaction that had delivered 37,318 tokens. Cause:
the post-trade `balanceOf` `eth_call` returned `429`, the helper returned `None`, and `None or 0`
rendered as `0`. It happened **twice**, and the user was told a successful trade had failed both
times.

Rules that fall out of it:

- Critical reads get a `need()` wrapper that retries until it gets a non-empty result.
- Never `value or 0` on a read that can fail — print `FAILED` instead.
- Receipt logs are the evidence; balances are corroboration.

## 7. Reporting template

```
tx hash / block / status / gasUsed
fill       : <amount> TOKEN   (receipt Transfer, pool -> buyer)
wallet     : TOKEN before -> after ; ETH before -> after
cost       : swap value + gas, and gas as a % of the ticket
price      : implied fill price + current pool price, and the drift since the last buy
venue      : token CA, pool, fee tier, router, function selector
provenance : UI liquidity claim vs on-chain WETH+token balances
risk       : unproven sell path (n sells in a m-buy history), one-way chain if
             gameCount() == 0, fresh throwaway wallet bounding the worst case
```

Worked end state: 3 buys, 163,705.63 TOKEN held, cost 0.01868884 ETH, marks 0.02228508 ETH.
On a fresh chain **mark ≠ money** until a sell has actually cleared — say so in the same breath as
the profit figure.
