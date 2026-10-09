# Bait-chain rug forensics — the venue that passed recon and still drained everyone

Worked case: "GIWA chain 9134" / `giwa-mainnet.everblocks.io`. Investigated 2026-09-26/27 as a
suspected pre-launch OP-Stack chain behind a leaked RPC. The recon was **largely correct and still
insufficient**: the chain was real, the L1 suite was canonical, the deposits reconciled to the wei —
and it was a bait operation that drained **~765 ETH (~$2.06 M)** from every participant.

Read this reference when a chain/venue recon comes back "clean", and especially when the user
pushes to trade on it.

---

## 1. The one signal that would have stopped everything: contract size

| contract | observed | real Uniswap V3 |
|---|---|---|
| pool | **332 B** | ~22,000–25,000 B |
| factory | **2,188 B** | ~20,000 B |
| router | **2,188 B** | ~30,000 B |

The pool contract was **332 bytes**. That is a stub that can hold balances and answer a few
getters; it cannot implement concentrated-liquidity swap math. The sizes were printed on screen,
read, and not acted on. **That was the failure — not a missing check, a printed number that was not
treated as dispositive.**

Add this as a hard gate, before quoting or simulating anything:

```
router  :  2 KB  → stub            real: 20–30 KB
factory :  2 KB  → stub            real: ~20 KB
pool    :  0.3 KB → impossible     real: 20–25 KB
```

Sanity anchors (runtime code size, `eth_getCode`):

- ERC-20: 1.4–1.9 KB (this is *normal* for a bare token — do not flag it)
- OP Stack predeploy `Proxy`: 2,059 B (normal)
- Uniswap V3 pool / factory / router / position manager: 20 KB–30 KB
- A "DEX" whose entire contract set is under ~5 KB is a set of stubs

**A stub pool can still accept your ETH and emit a `Transfer` of a token it just invented.** It
cannot give you the ETH back, because the sell path was never real.

## 2. Second signal: an all-buy pool is not "unproven", it is the shape of the bait

The `Swap` census found 93 swaps, **all buys, zero sells**, across the pool's whole history. The
session recorded it as "sell path unverified, not proven broken" and offered a sell test. That
framing was too generous. On a venue whose contracts are stubs, an all-buy history means the exit
was never implemented — the correct reading is **"assume you cannot exit"**, and the burden is on
the venue to prove otherwise, not on you to test it after buying.

## 3. Third signal: canonical code is camouflage, not a guarantee

Everything the earlier sections teach was verified and true, and none of it helped:

- L1StandardBridge / OptimismPortal2 impl bytecode **byte-identical** to OP Mainnet, Zora,
  Worldchain, Unichain, Soneium, Ink, Mode, Metal, Superseed; source verified on Blockscout.
- Zero upgrades after the deploy block.
- `SystemConfig.gasLimit()` matched the L2 block gas limit; `L1Block` read real-time L1 height.
- L1→L2 deposits reconciled to the wei, repeatedly.

**Why it worked for the operator:** the canonical portal is a *façade that collects ETH*. It is
public, audited, and holds whatever is sent to it. Put one in front of a fake chain and every
technical check you can run on the contract passes, because the contract really is the real one.
The theft happens at the *operator* layer, not the *code* layer.

Consequence for verdicts: when the chain is **not officially announced by its named project**, the
bytecode match is evidence about the *contract*, and about nothing else. Do not let it pull the
chain-level verdict upward. The earlier section's line — *clean code + instant upgrade key + no
exit path = do not enter* — was written from this case and still understates it: **clean code +
unofficial chain + no exit path = assume bait.**

## 4. Post-mortem: how the drain actually looked

Ground truth is **native balance of the escrow sampled at historical blocks** — not an indexer.

```
eth_getBalance(PORTAL, <blockNumber>)   # Alchemy serves recent history fine
```

Worked timeline (blk → portal balance → delta):

```
26065430      4.45802111 ETH
26065580      4.52542111 ETH   +0.067
26065760      6.90692450 ETH   +2.382
26066118     18.66799182 ETH   +11.761     <- after our 4th bridge
26066354    234.47138774 ETH   +215.803    <- victim inflow begins
26066603    529.14940522 ETH   +141.657
26066900    706.36434839 ETH   +75.648
26067200    757.49334974 ETH   +27.922
26067300    766.19650981 ETH   +8.703      <- peak
26067350      1.24905000 ETH   -764.947    <- *** drained in one move ***
latest        1.39349499 ETH
```

**766.2 ETH accumulated → 764.95 ETH out in a single transaction.** Sampling a handful of blocks
either side of the suspected event turns "something looks off" into an exact figure and block.

### Distinguishing a drain from a legit withdrawal

Both reduce the escrow. The discriminator is the proof machinery, not the balance change:

```
DisputeGameFactory.gameCount() = 0     <- no game was EVER created
WithdrawalProven               = 0
WithdrawalFinalized            = 0
portal.paused()                = 0
impl unchanged (no upgrade)
```

`gameCount() == 0` means no state root was ever proposed, therefore **no withdrawal can be proven or
finalized**. ETH leaving an escrow under those conditions is not a withdrawal. Check this trio
*before* describing an outflow, and note that `paused() == 0` and an unchanged impl rule out the
other "legitimate-looking" explanations.

### The laundering trace

```python
alchemy_getAssetTransfers({"fromAddress": drainer, "category": ["external","internal"],
                           "order": "asc", "withMetadata": True})
```

Worked flow:

```
0x04a9c8d8fee491411bda28b68ad80f0122fc4134   EOA, nonce 16, 197.24 ETH   <- drain receiver
   ├─► 0x8c563fc543f6ecc2c8c09eb09d82798f7a7f3da4   EOA, 251 ETH, 0 outbound (parked)
   ├─► 0xec160acd00d95ebbbe0394161101eb577ca96b60   EOA, nonce 15, 200.96 ETH
   │      └─► many 10 ETH + several 1 ETH  ──► 0xd90e2f925da726b50c4ed8d0fb90ad053324f31b
   └─► 10 ETH × 3        ──────────────────────► same address
```

**Tornado Cash recognition:**

- Denominations **10 ETH and 1 ETH** (also 0.1 / 100) repeated in a burst — that is the mixer's
  fixed-denomination pool structure, not organic payments.
- Timestamps cluster in minutes (here 08:19–08:29 UTC), i.e. scripted.
- Confirm the label rather than trusting the address: Blockscout `api/v2/addresses/<addr>` returned
  `name = "TornadoRouter"`. Registry/deployer-side labelling is stronger than eyeballing.
- Do not over-trust an address that merely *resembles* a known one — the key routers/pools share
  long prefixes. Pass the address through a public labeler, don't pattern-match by eye.

### `/txlistinternal` mis-attributes proxy delegatecalls

Blockscout's internal-tx listing for the portal reported transfers such as
`from: portal → 0xe89f13c5…` (the **implementation** address) — 721 of them, "totalling 284 ETH",
plus a 766 ETH row — while the escrow never held more than ~19 ETH at the time. Proxy
`delegatecall` accounting produces phantom rows with the implementation as the counterparty.

**Never build a drain figure from `txlistinternal`.** Use `eth_getBalance(addr, blockNumber)`
sampling for magnitudes, and pull the actual outflow transaction + receipt for any single event you
want to cite.

## 5. Exposure containment (what went right)

The one thing that limited the damage was having bridged and traded from a **fresh one-shot
wallet**:

- Its L1 history contains only plain transfers to the **canonical** `L1StandardBridge` — no
  approvals, no `setApprovalForAll`, nothing a hostile contract can reuse.
- The user's main holdings were never connected to the chain or the DApp.
- Loss is bounded by what was sent to that wallet.

Therefore: **when the endpoint is unverified, never let the user connect a wallet holding value.**
Sign locally, broadcast through the endpoint, keep the key on disk, and treat the wallet as
expendable.

Still flag for the user: **any other wallet that connected to the DApp front-end and signed an
approval** must have approvals revoked (revoke.cash / explorer token-approvals). The front-end
(`dyorv3.org`) is part of the operation, not just the chain.

## 6. Reporting a loss without softening it

State the mechanism, the figures, and the exit path in that order, then the containment:

1. **Mechanism** — X ETH accumulated at the escrow and Y ETH left in one move at block N; the
   withdrawal-proof counters are all zero, so it was not a withdrawal.
2. **Laundering** — destination addresses and the mixer label with the denomination pattern.
3. **Exposure** — which wallet was affected, which was not, and the exact outlay
   (bridges + L1 gas + L2 gas + now-worthless balances).
4. **Next actions** — do not send more; **a "recovery service" that DMs first is a second-stage
   scam targetting victims**; revoke approvals; keep the evidence; and state plainly that funds
   through a mixer are realistically unrecoverable.

Also record **which signal was missed and why** — in this case the printed byte sizes. A post-mortem
that only lists the operator's crimes teaches nothing reusable.

## 7. Checklist to run BEFORE quoting a buy on an unfamiliar venue

- [ ] `eth_getCode` size of pool / factory / router — stubs (< 5 KB) = stop
- [ ] Pool found on the factory the **app actually routes through** (JS bundle), not the chain's other one
- [ ] `Swap` sign census — buys only ⇒ assume the exit is not implemented
- [ ] Pool token + WETH `balanceOf` match the site's advertised liquidity
- [ ] Venue contracts are **not** the canonical protocol addresses ⇒ third-party deployment
- [ ] Chain is **officially announced by the project it names** — if not, no bytecode result raises the chain verdict
- [ ] Exit path: `gameCount()`, `WithdrawalFinalized` count, `paused()`
- [ ] Funds are spendable-if-lost; wallet is fresh and holds nothing else
