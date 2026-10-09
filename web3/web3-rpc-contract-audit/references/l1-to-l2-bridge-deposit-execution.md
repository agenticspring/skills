# Bridging funds INTO a pre-launch / leaked OP Stack L2 — execution + end-to-end proof

Companion to the recon half. Recon answers "is this chain real, can I get out?"; this file covers
what happens when the user says **"bridge a little, I know it's gone"** and you actually execute.

Worked case: chain 9134 (leaked RPC, pre-launch), 0.00056 ETH deposited from Ethereum mainnet via
`L1StandardBridge.bridgeETHTo`, landed on L2 ~40 s later, portal escrow delta reconciled to the wei.

---

## 0. Gate before you accept the order

Do the recon checks **once**, state the two blocking facts **once**, then stop re-litigating:

- `DisputeGameFactory.gameCount() == 0` → no state root ever proposed → **no withdrawal can be
  proven** → inbound funds are one-way.
- ProxyAdmin → Safe → owners' funders → **can the upgrade key be replaced without a timelock?**

When the user has explicitly accepted total loss ("gua udh siap hilang duitnya"), **execute**. Do not
re-hedge mid-flight, do not add safety lectures to every progress message. One line of risk in the
plan message, then work. Repeated warnings after acceptance read as stalling.

Size the loss ceiling explicitly: a **fresh one-shot wallet per test** means worst case equals what
was sent to that wallet, never the user's main holdings.

## 1. Fresh one-shot wallet + key hygiene

```python
from eth_account import Account
ac = Account.create()                      # address only in chat
open("/root/<proj>/pk.txt","w").write(ac.key.hex()); os.chmod(path, 0o600)
```

Then *prove* the key is not leaking, and report the audit rather than asserting it:

```bash
stat -c 'perms=%A owner=%U size=%s' pk.txt          # want -rw------- root root 64 bytes
git -C <dir> rev-parse --is-inside-work-tree        # want "not a repository"
grep -rl "$(head -c 8 pk.txt)" ~/.hermes/obsidian-vault/   # want no hits
```

Never echo the key. Print `first6…last4` only if the user asks to identify it. Offer
`shred -u` as the cleanup path when the test is done.

## 2. Dry-run the deposit with NO funds on hand

`eth_estimateGas` checks balance, so it fails `EVM error: OutOfFunds` on an empty wallet — and
Alchemy's `eth_estimateGas` **does not accept `stateOverrides`** (it errors `Invalid params`).
Use `eth_call` **with state overrides** to validate calldata + contract acceptance for free:

```python
OVR = {ADDR: {"balance": hex(1 * 10**18)}}     # virtual 1 ETH, nothing real
rpc("eth_call", [{"from":ADDR,"to":BRIDGE,"data":data,"value":hex(amt)}, "latest", OVR])
# -> not a dict/error  ==  deposit valid
```

Budget gas from a **fixed ceiling** (see §4) instead of an estimate.

## 3. Calldata — compute the selector, never recall it

```bash
cast sig "bridgeETHTo(address,uint32,bytes)"          # 0xe11013dd
cast 4byte-decode 0xe11013dd…                          # confirm args decode back
```

`cast 4byte 0xe11013dd` confirms the 4byte directory agrees. (Recall produced a wrong selector in
the first attempt — this is exactly why the parent skill says compute, never hardcode.)

Encoding for `bridgeETHTo(to, minGasLimit, extraData)` — `extraData` empty:
`sel | to (32B) | minGasLimit 200000 (32B) | offset 0x60 (32B) | length 0 (32B)`.

Alternative single-call path: `OptimismPortal2.depositTransaction(address,uint256,uint64,bool,bytes)`
= `0xe9e05c42`. Both verified accepted by `eth_call` in the worked case.

## 3b. "Why did you use THIS contract and not THAT one?" — the explanation model

Expect this question the moment you name a target address (worked case: *"Kenapa kamu bridge pake
contract ini? Tapi bukan yg ini? Jelaskan dong"*). The user is not asking for the mechanics — they
are checking whether you picked a worse or less official door. Answer with **one model, then
on-chain proof**.

**The model:** the two contracts are one system, at two layers.

```
L1StandardBridge   = the front desk   — takes your ETH, passes it on, KEEPS NOTHING
L1CrossDomainMessenger = the courier  — relays a message so the L2 side auto-delivers
OptimismPortal2    = the vault        — emits TransactionDeposited and HOLDS ALL THE ETH
```

**Prove it with balances, don't assert it.** Three reads settle the whole question:

```python
eth_getBalance(L1StandardBridge)        # 0.000000000  -> pass-through, holds nothing
eth_getBalance(L1CrossDomainMessenger)  # 0.000000000  -> ditto
eth_getBalance(OptimismPortal2)         # 4.518021112  -> every wei lives HERE
```

So "I bridged via the bridge" and "the money is in the portal" are simultaneously true. Then walk
the **receipt log order** to show the path visibly:

```
log#0,1  emitter L1StandardBridge       ETHBridgeInitiated
log#2    emitter OptimismPortal2        TransactionDeposited   <- escrow lands here
log#3,4  emitter L1CrossDomainMessenger SentMessage
```

**Then give the honest comparison** (see §3/§4 for the measured numbers):

| | `L1StandardBridge.bridgeETHTo` | `OptimismPortal2.depositTransaction` |
|---|---|---|
| gas (measured) | 620,976 | ~150–250 k |
| L2 delivery | automatic via messenger | manual; you own the `_data` call |
| L2 deposit tx `to` | `0x4200…0007` | the recipient |
| who uses it | official OP Stack wallets & UIs | contract integrators, power users |

Prefer the portal directly when gas matters at scale, or when you want the deposit to *also* call a
contract on L2 via `_data`.

**The sentence that actually answers the worry:** both contracts sit behind the **same EIP-1967
admin** — same `ProxyAdmin` → same Safe → same upgrade key. Verify it (read the admin slot on both)
and say so explicitly:

> Choosing the bridge over the portal changes nothing about safety. Same admin, same upgrade
> authority, same vault. The only real cost difference is gas.

That reframes a nervous "which one did you use?" into the real risk, which is never the door. Report
the admin comparison rather than letting a mechanics explanation imply the choice was material.

## 4. Fee policy — the bug that cost four failed broadcasts

**`maxPriorityFeePerGas` MUST be `<= maxFeePerGas`.** Setting `prio = 1 gwei` with
`maxFee = baseFee * 2` (≈0.12 gwei on a quiet mainnet) is rejected every time with:

```
-32003  max priority fee per gas higher than max fee per gas
```

Correct construction:

```python
prio   = max(1, int(0.01e9))    # 0.01 gwei tip on a quiet L1
maxfee = base * 2 + prio        # ceiling INCLUDES the tip
```

Nothing was spent during the failures (nonce stayed 0) — but the retry loop burned four attempts
before surfacing it. Fail fast on this error string; it is never transient.

**Gas reality:** `bridgeETHTo` consumed **620,976 gas**, not the ~180–200 k you would guess from a
plain value transfer. Fund against a **~700 k ceiling**. At baseFee 0.07 gwei that is ~0.000043 ETH;
at 30 gwei it is ~0.021 ETH — never leave the wallet near-empty relative to the ceiling.

## 5. Fund-gated auto-execution (the watcher pattern)

When the user must fund first, do not poll by hand in chat. Ship a watcher that fires on arrival:

```
loop every 20 s:
    bal  = eth_getBalance(addr)
    need = amount + 700_000 * max(base*2, 1) + dust
    if bal >= need:  run broadcaster  ->  print output  ->  exit 0
time-box it (e.g. 3 h); on timeout exit 0 WITHOUT sending anything and say so
```

Launch it as a background process with completion notification so the result re-enters the
conversation on its own. Print a balance line only when the balance **changes**, not every tick.
Guard the broadcaster too: recompute `need` with live baseFee and refuse with an explicit
"isi dulu" message rather than broadcasting into a shortfall.

## 6. Verification — a hash is not a result

Report the whole chain of evidence, in this order:

1. **L1 receipt** — `status == 0x1`, block, `gasUsed`, `effectiveGasPrice`, gas cost.
2. **The `TransactionDeposited` log** decoded from the receipt (`opaqueData` as ABI `bytes`:
   offset `[0:32]`, length `[32:64]`, payload `[64:…]` — never packed) → mint / value / gasLimit.
3. **L2 balance poll** for a few minutes — it appeared after ~40 s in the worked case. Print a
   timestamped poll line so "landed at 40 s" is visible.
4. **The L2 deposit tx itself** — see §7.
5. **L1 portal balance delta** — see §8.

`"submitted"` is never the answer. Neither is the L1 hash alone.

## 7. Finding the L2 deposit tx — do NOT filter by `to`

`bridgeETHTo` routes through `L1CrossDomainMessenger` → `L2CrossDomainMessenger`, so the L2 deposit
tx has **`to = 0x4200000000000000000000000000000000000007`**, not the recipient. A search for
`to == recipient` finds nothing while the money is demonstrably there.

Reliable method — the chain is one system tx per block, so **scan for anomaly blocks**:

```python
cnt = rpc("eth_getBlockTransactionCountByNumber", [hex(bn)])   # cheap, tiny response
# tx count > 1  =>  organic activity; fetch that block and print the non-0xdead…0001 txs
```

Parallelise with ~4–8 workers over a few thousand blocks. This also doubles as a **new-activity
census** (see §8) at almost no cost.

## 8. Address aliasing — correct a naive sender count

When an **L1 contract** (the messenger, the bridge) is the depositor, the L2-side sender in
`TransactionDeposited` topic1 is the contract address **plus the alias offset**:

```
alias = l1_address + 0x1111000000000000000000000000000000001111
```

Two addresses exactly that constant apart are **the same actor**. In the worked case
`0xf5d62377b88ce93f89703b9427e67bb0f4c2f0e4` was the alias of `L1CrossDomainMessenger`
`0xe4c52377b88ce93f89703b9427e67bb0f4c2dfd3` — and had been miscounted as a *user wallet* in an
earlier census. **Unique-user counts that read topic1 are overcounts; subtract the aliases.**
Sanity check: alias − real must equal the constant exactly.

## 9. Multi-party reconciliation

`OptimismPortal2` balance delta on L1 must equal Σ of the new L2 `0x7e` deposit values. In the
worked case the delta was `4.518021112 − 1.091393348 = 3.426627764` ETH against `3.42662776` ETH
summed from L2 — an exact match covering the test deposit *and* seven unrelated depositors.

This is the strongest available honesty check on a single-source endpoint, and it scales from
"my one tx" to "everyone's traffic". Run it after every bridge, not just the first.

## 10. Endpoint / tooling quirks hit along the way

- **Alchemy free tier caps `eth_getLogs` to a 10-block range.** A 3,000-block query is rejected
  `-32600`. For wide ranges use the Etherscan-compatible surface
  (`https://<explorer>/api?module=logs&action=getLogs&address=…&topic0=…`) or per-block scans.
- **Explorer log API is incomplete on brand-new suites** — it returned 11 of 14 deposit logs and
  missed one deposit entirely. Reconcile from receipts; an indexer gap is not a money gap.
- **Per-block `eth_getBlockTransactionCountByNumber` beats per-block `eth_getBlockByNumber`** for
  sweeps: a few bytes per call instead of a full block, so thousands of blocks stay within budget.

## 11. Reporting template

```
L1 tx hash + explorer URL + block + status + gasUsed + gas cost
TransactionDeposited value (decoded from the receipt, not from a log index)
L2 deposit tx: block, type 0x7e, value
L2 balance: before -> after
Remaining balance left in the one-shot wallet
Full cost table: bridged / gas / leftover
```

Then offer the leftovers decision explicitly — sweep back, deposit more, leave it, or shred the
key. State plainly that a second deposit is equally one-way.
