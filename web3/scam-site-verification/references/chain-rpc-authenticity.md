# Chain / RPC authenticity — worked case: leaked "GIWA mainnet" RPC (2026-09-26)

Claimed by the user, verbatim:

```
Name     : GIWA
Chain ID : 9134
RPC      : https://giwa-mainnet.everblocks.io/rpc/exHgkb748URTmq3FBHi8fCWoJnsg9uWf
```

User context that matters: handed over as a **leaked** RPC ("Itu leaker rpc") from a
third party, and the user later instructed: *"Ga usah baca dokumentasi dulu apakah
benar Mainnet atau belum. Kau cek aja rpc nya apaka ada aktifitas tx dll atau infra yg
udh ada dari rpc yg kukasih tadi?"* — i.e. verify from the chain, not from docs.

## All probes, with observed values

### Chain / node basics

```bash
U="https://giwa-mainnet.everblocks.io/rpc/exHgkb748URTmq3FBHi8fCWoJnsg9uWf"
curl -s -X POST "$U" -H 'content-type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}'
```

| probe | observed | read |
|---|---|---|
| `eth_chainId` | `0x23ae` = 9134 | matches the claim |
| `net_version` | `9134` | consistent |
| `web3_clientVersion` | `reth/v2.3.0-9384bc5/x86_64-unknown-linux-gnu` | real op-reth |
| `eth_syncing` | `false` | |
| `net_peerCount` | **`0x0`** | zero peers — odd for a public network |
| `net_listening` | `true` | |
| `txpool_status` | **HTTP 403** | operator disabled it |
| `eth_gasPrice` | `0xf433b` | |
| HTTP headers | `405` on GET, `via: 1.1 Caddy`, `access-control-allow-origin: *`, `alt-svc: h3` | reverse-proxied |
| JSON-RPC batch | **batch 10 → 200; batch 25/50/100/200 → HTTP 400** | batch cap ≈ 10 |
| single request latency | ~0.12 s | fast individually, throttles under fan-out |

### Domain forensics — the decisive part

```bash
dig +short giwa-mainnet.everblocks.io A     # <REDACTED>
dig +short everblocks.io A                  # (empty)
dig +short explorer.everblocks.io A         # (empty)
dig +short rpc.everblocks.io A              # (empty)
dig +short everblocks.io NS                 # dns1/dns2.registrar-servers.com  (Namecheap)
whois everblocks.io | grep -iE "creation|registrar|registrant country"
#   Creation Date: 2026-09-26T19:52:18Z   <-- SAME DAY, ~3 h before the probe
#   Registrar: NameCheap, Inc.   Registrant Country: US
echo | openssl s_client -connect giwa-mainnet.everblocks.io:443 \
  -servername giwa-mainnet.everblocks.io 2>/dev/null | openssl x509 -noout -dates
#   notBefore=Sep 26 19:11:16 2026 GMT    <-- same afternoon
curl -s "https://ipinfo.io/<REDACTED>/json"
#   AS61272 UAB Bacloud, Šiauliai, LT — budget VPS, rDNS 34522-63693.bacloud.info
```

**Only the one RPC hostname exists; the apex has no `A` record at all.** A domain
registered hours earlier with no apex DNS is the whole tell.

### Chain age and the L1 anchor

```bash
# genesis
curl -s -X POST "$U" -H 'content-type: application/json' \
 -d '{"jsonrpc":"2.0","id":1,"method":"eth_getBlockByNumber","params":["0x0",false]}'
# block 0 timestamp = 1790446259 = 2026-09-26 18:10:59 UTC   <-- genesis ~5 h before probe

# OP Stack L1Block.number() -> which L1, and how fresh
curl -s -X POST "$U" -H 'content-type: application/json' \
 -d '{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":"0x4200000000000000000000000000000000000015","data":"0x8381f58a"},"latest"]}'
# 0x...018db7de = 26,064,862
# real Ethereum mainnet at that moment = 26,064,867  -> 5 blocks behind = LIVE L1 anchor
```

So the deployment is a genuine op-reth OP Stack chain reading **Ethereum mainnet** in real
time — a real chain, not a toy copy of the bytecode.

### Chain-ID registry provenance (the trap)

```bash
curl -s "https://raw.githubusercontent.com/ethereum-lists/chains/master/_data/chains/eip155-9134.json"
# {"name":"GIWA","chain":"ETH","rpc":[],"infoURL":"https://giwa.io",
#  "shortName":"giwa","chainId":9134,"networkId":9134,"status":"incubating"}
#                              ^^^^^^^  NO OFFICIAL RPC PUBLISHED

curl -s "https://raw.githubusercontent.com/ethereum-lists/chains/master/_data/chains/eip155-91342.json"
# {"name":"GIWA Sepolia Testnet","rpc":["https://sepolia-rpc.giwa.io"],
#  "faucets":["https://faucet.giwa.io"],"chainId":91342, ...explorers...}

curl -s "https://api.github.com/repos/ethereum-lists/chains/commits?path=_data/chains/eip155-9134.json&per_page=5"
# 2025-09-29  H.Chihoon (jerome)  "Add giwa testnet and mainnet (#7707)"
```

The 9134 entry was added by **GIWA's own team a year earlier** — so the chain ID is
legitimately theirs, which is exactly why the impersonator used it. `rpc: []` is the
discriminator: no official RPC exists for 9134.

Live check of the real testnet endpoint (works, and matches the documented ID):

```bash
curl -s -X POST https://sepolia-rpc.giwa.io/ -H 'content-type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}'
# {"result":"0x164ce"} = 91342  ✅
```

### Full census — is anyone using it?

`eth_getBlockTransactionCountByNumber` batched (10 per request, 24 workers) over all
blocks. Result: **3,876 of 20,166 blocks answered** before throttling.

```
distribusi tx/blok : {0: 1, 1: 3868, 2: 7}   # block 0 = genesis, 7 blocks with 2 txs
total tx di chain  : 3,882
blok dgn tx != 1   : 8   [0, 1899, 3024, 11214, 11219, 11224, 11229, 19123]
```

Merged with an earlier partial pass (22 anomalies) → **19 non-system transactions** across
~20k blocks. Every normal block = 1 tx = the system deposit:

```
from=0xdeaddeaddeaddeaddeaddeaddeaddeaddead0001
to  =0x4200000000000000000000000000000000000015   type=0x7e   gasUsed=46,230/60,000,000
```

The 19 real ones:

```
blk    508 18:19:27  0xc1abf6cf90… -> DEPLOY(18,210 B)  0x7e   -> 0x6a2ca1cec1573dd1a476a1d7e951e81dcfbd7a5a (329 B proxy)
blk    519 18:19:38  3× self-transfer 0.1814 / 0.1473 / 0.0713 ETH   0x7e
blk   1402 18:34:21  self-transfer 0.0100 ETH   0x7e
blk   1899 18:42:38  self-transfer 0.1550 ETH   0x7e
blk   2698 18:55:57  self-transfer 0.1714 ETH   0x7e
blk   3024 19:01:23  self-transfer 0.0900 ETH   0x7e
blk   4734 19:29:53  0xf7d3f436e9… -> DEPLOY(2,868 B) -> 0x44435d71d27bb23233f09c9171969f0c80b9e738  (code now 0 B)
blk   6219 19:54:38  0x5bea742bd6… -> DEPLOY(1,845 B) -> 0xcd4a6b33e41fc25dc24c45af87efe555e34306da  (code now 0 B)
blk   7163 20:10:22  self-transfer 0.1040 ETH   0x7e
blk   7777 20:20:36  self-transfer 0.0500 ETH   0x7e
blk  11104 21:16:03  0xf5d62377b8… -> L2CrossDomainMessenger (0x4200…0007) 0.001 ETH, sel 0xd764ad0b
blk  11154 21:16:53  0x44c4ec4f63… -> DEPLOY(24,939 B) type 0x2 -> 0x69ac9b0362f38f4e1b46972302f84dd322e677d2 (24,535 B)
blk  11214 21:17:53  0x44c4ec4f63… -> DEPLOY(25,013 B) type 0x2 -> 0x7d711d4a1da22f8ddc26a2f91df0cf4abc16d3c2 (24,497 B)
blk  11219 21:17:58  0x44c4ec4f63… -> DEPLOY(15,783 B) type 0x2 -> 0xa50d16aaef156415cb32cef55703255494eb2693 (15,365 B)
blk  11224 21:18:03  0x44c4ec4f63… -> call into 0x69ac9b03…  type 0x2
blk  11229 21:18:08  0x44c4ec4f63… -> DEPLOY(24,226 B) type 0x2 -> 0xa143443113fb31bbbb2445ee3c1fadece48f9d61 (24,009 B)
blk  19123 23:29:42  0x937933e11a… -> self-transfer 0.0100 ETH   0x7e
```

11 distinct senders. Note the pattern: type `0x7e` = **deposit txs that originated on L1**
(someone used the bridge), while the 21:16–21:18 burst used ordinary type-`0x2` L2 txs —
one sender deployed **four contracts totalling ~88 KB in 75 seconds**. That is a staged
deployment, not user traffic. No ERC-20 transfers, no swap selectors anywhere.

`eth_getCode` sweep: standard OP Stack predeploys present (WETH9 2,846 B, L2CrossDomainMessenger,
L2StandardBridge, SequencerFeeVault, L1Block, EAS 2,059 B) plus the canonical universal
deployments (Multicall3 3,808 B, Permit2 9,152 B, Create2Deployer 1,584 B, EIP-4788, EIP-2935).
Nothing GIWA-specific.

## Verdict wording that worked

- Not an official RPC. The official registry publishes **no** RPC for 9134, and the endpoint's
  domain is hours old with no apex DNS.
- The chain is **real and live** (op-reth, mainnet-anchored) but **essentially empty** — 19
  non-system txs, all deployment/bridge-test work.
- Read-only `curl` probing is safe for funds; **never add it to a wallet with keys**.
- Chain data alone cannot distinguish "leaked real staging node" from "copycat wearing the
  reserved chain ID" — say that rather than picking one.

## Reusable scripts (this session)

- `giwa_deep.py` — basics + full scan + gas sampling + infra sweep + system-tx decode
- `giwa_scan.py` — chunked tx-count census → `giwa_anomalies.json`
- `giwa_infra.py` — anomaly → activity/deployment inventory → `giwa_activity.json`
- `giwa_blocks.py` — dump specific blocks with full tx classification (SELECTORS map)

Port these rather than rewriting: the batch-cap handling (`CHUNK = 10` + parallel small
batches), the system-sender filter (`0xdead…0001`), and `to == null` deployment detection are
the parts that took the time.
