# Chain & RPC authenticity verification (pure RPC, no source, no docs trust)

Use when someone hands over a chain ID + RPC endpoint and asks *"is this real?"* — the
classic shape is a "friend sent me this network", a brand-new chain reusing a well-known
project's name, or a mainnet endpoint for a project that has not announced a mainnet.

## Step 0 — split the question into three, they have different answers

1. **Is the CHAIN a genuine deployment?** (real client, real L1 anchor, real contracts)
2. **Is this ENDPOINT the project's official RPC?** (or a republisher / leak / copycat)
3. **Is the project's mainnet even launched?**

> A real chain behind an unofficial endpoint is a completely different verdict from a fake
> chain. Answering #2 and calling it #1 is the mistake to avoid.

## Step 1 — RPC basics

```
eth_chainId / net_version      must match the handover claim
web3_clientVersion             the stack (e.g. reth/v2.3.0 = op-reth)
net_peerCount, net_listening   this endpoint reported 0x0 peers
txpool_status                  HTTP 403 = operator deliberately disabled it
eth_syncing, eth_gasPrice
```

## Step 2 — freshness and liveness

- Genesis: `eth_getBlockByNumber("0x0")` → `timestamp`. A "mainnet" whose genesis is hours
  old is a deployment, not a network.
- Heartbeat: sample `eth_blockNumber` twice ~20 s apart (this one: ~1 block/s).
- **The decisive test — tx per block across MANY blocks**:
  `eth_getBlockTransactionCountByNumber` for every block. On an OP Stack chain the normal
  block holds **exactly one** system deposit, so uniform 1 tx/block means **nobody uses the
  chain**. Real census output to recognise: `{0: 1, 1: 9665, 2: 20, 4: 1}` = genesis + a
  handful of real txs in 20k blocks.
- **Block production is a heartbeat, not activity.** Never report "the chain is producing
  blocks" as evidence of a live product.

## Step 3 — fingerprint the stack without docs

OP Stack (Optimism-style) tells:

- `miner` == `0x4200000000000000000000000000000000000011` (SequencerFeeVault)
- the per-block tx: `from 0xdeaddeaddeaddeaddeaddeaddeaddeaddead0001` →
  `to 0x4200000000000000000000000000000000000015` (L1Block), `type 0x7e`, ~46k gas
- predeploys exist at `0x4200…0000`–`0x4200…00FF` (WETH9 `…06`, L2CrossDomainMessenger `…07`,
  L2StandardBridge `…10`, SequencerFeeVault `…11`, L2ToL1MessagePasser `…16`, EAS `…21`)
- `eth_call` to `0x4200…0015` with `number()` (`0x8381f58a`) returns the **L1 height this
  chain reads** — compare it against a real L1 RPC to prove which L1 it is anchored to

**Ignore these as evidence:** Multicall3, Permit2, Create2Deployer, EIP-4788 beacon-roots,
EIP-2935 history. They are canonical deterministic deployments present on almost every EVM
chain, so "they're deployed here" proves nothing. Chain-specific contracts being **absent**
is the informative signal.

## Step 4 — registry checks (authoritative and free)

| source | what to read |
|---|---|
| `raw.githubusercontent.com/ethereum-lists/chains/master/_data/chains/eip155-<id>.json` | is `rpc` populated or `[]`? what `status`? |
| GitHub commits API for that same path | **who added the ID and when** — a chain ID reserved by the project's own team (a year early, via their own PR) is exactly what makes a copycat convincing |
| OP Superchain registry | `contents/superchain/configs/mainnet` (one folder per chain) and `chainList.json` — absent = not registered |
| the project's own docs network table | read it yourself; never trust a domain the docs never mention |

## Step 5 — domain forensics on the endpoint host

```bash
whois <host>            # Creation Date hours old = the whole tell
dig +short <host> A     # and the apex: often ZERO records when it is a proxy front
echo | openssl s_client -connect <host>:443 -servername <host> | openssl x509 -noout -dates
curl -sI <url>          # Caddy/nginx reverse proxy, CORS *, 405 on GET (JSON-RPC is POST-only)
```

A **leaked-RPC republisher** (someone fronting the real node behind their own fresh domain,
with no apex DNS) looks identical to a **fake endpoint** on these signals alone. Say which
one you can actually distinguish, and which you cannot.

## Step 6 — identify a contract with no verified source (EIP-1967)

```
storage slots:  impl 0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc
                admin 0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103
                beacon 0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50
```

Then **name the implementation using Blockscout's public v2 API — no API key needed**:

```bash
curl -s "https://eth.blockscout.com/api/v2/addresses/<ADDR>"
# -> name, is_contract, is_verified, proxy_type, creator_address_hash,
#    creation_status, implementations:[{address_hash,name}], public_tags
```

That single call identified a proxy as `L1StandardBridge` and told us the proxy type was
`eip1967`. Probe the implementation for `version()`/`VERSION()` (`0x54fd4d50`) — OP Stack
contracts return their release version string (2.8.2 / 5.6.1 / 3.14.2 …).

**Compute any selector** instead of guessing (pycryptodome is usually already installed):

```python
from Crypto.Hash import keccak
def sel(sig):
    k = keccak.new(digest_bits=256); k.update(sig.encode()); return "0x" + k.hexdigest()[:8]
```

A 160-bit-looking result that resolves to an address with code is an address return; ABI
strings need the offset+length decode. Distinguish before labelling.

## Step 7 — walk the application graph, never stop at one contract

```
bridge.messenger()            -> L1CrossDomainMessenger
portal.systemConfig()         -> SystemConfig        (same address from bridge + portal = consistent)
systemConfig.owner() / .guardian()
```

Recognise a **Gnosis Safe**: `proxy_type: master_copy`, implementation named `GnosisSafe`
(v1.3.0 singleton `0xd9Db270c1B5E3Bd161E8c8503c55cEABeE709552`), and `getThreshold()` returning
a small n. A Safe as owner+guardian is a real operational multisig — that is a legitimacy
signal, opposite of a throwaway EOA. Owner == guardian is normal for these chains.

## Step 8 — BIND the L1 suite to the L2 (the step people skip)

Three independent bindings, use at least two:

1. **Config equality** — `SystemConfig.gasLimit()` vs the `gasLimit` of the L2 blocks. Equal
   (here `0x3938700` = 60,000,000) means the L1 config and that L2 are one deployment.
2. **Bridge call ↔ deposit** — find the L1 tx of an address that deposited. Blockscout
   `/api/v2/addresses/<a>/transactions` shows `method` (`bridgeETHTo`, `depositTransaction`,
   `OPContractsManagerV2` `deploy`) and `created_contract`. This is how the L1StandardBridge
   and the OptimismPortal were identified as the entry points used by the deployers.
3. **L2 reappearance** — the deposit must appear on the L2 as a `type 0x7e` transaction from
   that same address.

Without a binding you have *"some OP Stack somewhere"*, not *"the L1 suite of this chain"*.

## Step 9 — attribution: who is actually using it

- Blockscout `/addresses/<a>/transactions` → method names + `created_contract` per row
- **First-inbound funder** (the strongest single attribution move):

```
alchemy_getAssetTransfers
  {fromBlock:"0x0", toAddress:<addr>, category:["external","internal"],
   order:"asc", maxCount:"0x3", withMetadata:true}
```

Two actors sharing one funder = **one person/team**. Then profile the funder: nonce, native
balance, and token count (`api.ethplorer.io/getAddressInfo/<a>?apiKey=freekey`).

| funder shape | read |
|---|---|
| nonce 100k–1M, thousands of tokens | exchange hot wallet (users withdrew from it) |
| nonce ≤ 3, small balance | fresh throwaway |
| nonce ~50–100k, one chain, 20–30 ETH | active personal / distribution wallet |

Verdict shape that actually helps: *"N distinct senders, M contracts deployed, all funded from
exchange-grade wallets, no organic traffic"* — not adjectives.

## Step 10 — a census the endpoint will actually let you finish

- Some endpoints **cap JSON-RPC batches** (measured: batch 10 → 200, batch 25 → **HTTP 400**)
  and throttle hard: 24 workers over 20k blocks left ~80% unanswered. Gentle mode — small
  batches, **4 workers**, retries with backoff, and **persist progress to a state file** so the
  run is resumable; freeze the chain height at start so new blocks do not move the goalposts.
- Single requests were ~0.12 s, so a patient full scan is minutes, not hours.
- Prefer `eth_getBlockTransactionCountByNumber` (tiny responses) for the first pass; only pull
  full blocks for the outliers.

## Verdict discipline (the expensive lesson)

- **State which of the three questions you answered.** "Not the official endpoint" is not
  "fake chain". Say so explicitly.
- **Quote the numbers**, and mark the ones you approximated.
- **Revise loudly when evidence contradicts you.** In the worked case an early "looks fake"
  call was too strong: the chain turned out to sit behind a canonical `OPContractsManagerV2`
  deployment, a verified `OptimismPortal2`, a Gnosis Safe (2-of-N) admin, a canonical shared
  `SuperchainConfig`, and a `SystemConfig.gasLimit()` matching the L2 blocks — i.e. a properly
  deployed OP Stack chain — while *still* not being the project's official RPC and *still*
  absent from the Superchain registry. Both halves must survive into the answer.
- **Never let "no label" become "no owner".** Absence of a public name tag is not evidence of
  fraud, and presence of official-looking contracts is not proof of endorsement either.
- **Hand over the tamper-proof signal**: the two things that change when a project really
  launches are the docs network table and the registry `rpc` array. Offer to watch those
  instead of polling a leaked endpoint.

## Safety framing to give the user

- **Read-only `curl` JSON-RPC is fund-safe** — no keys, no signing, no approvals.
- **Never add an unverified network to a wallet holding keys.** Wallets auto-probe
  `eth_accounts` / `eth_getBalance` / `eth_getCode` across your accounts, so a hostile RPC
  instantly clusters every wallet you own and can serve fabricated balances/tokens to bait an
  approval.
- Curl from a throwaway IP if you intend to keep watching; the endpoint operator sees your IP
  and your query pattern.
- Bridging real assets into an endpoint you cannot attribute is irrecoverable, and if it
  anchors to Ethereum mainnet then even a "test" deposit is real money.
