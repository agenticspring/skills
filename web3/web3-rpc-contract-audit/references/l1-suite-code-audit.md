# Auditing an L1 contract suite: is there malicious code?

Companion to `chain-and-rpc-authenticity.md`. That file answers *"is this chain/RPC real?"*.
This one answers the question that comes right after, usually once real funds are already
bridged: **"is there dangerous code in the L1 contracts, and can my money come back?"**

The lesson that shapes the whole recipe: in the worked case the implementations were
**clean** — byte-identical to the official release — and the verdict was still *do not
enter*. Clean code is not the finding. The finding is **who can replace the code** and
**whether an exit path exists**.

## Order of operations (cheapest decisive test first)

1. Bytecode-hash comparison against a canonical multi-chain baseline
2. Source-verification status
3. Upgrade history (has the impl ever been swapped *after* deploy?)
4. Who holds the upgrade key, and do those keys belong to one entity?
5. Can funds leave at all (withdrawal liveness)?
6. Only then: read code

## 1. Bytecode hash vs canonical baseline (the strongest cheap test)

You do not need source to prove the code is unmodified. Compare the runtime bytecode hash of
each implementation against the same contract's implementation on known-good chains.

Baseline address source — note which path actually works:

```bash
# WORKS: keyed by L2 chain ID, 54 entries, includes L1 contract addrs per chain
curl -sL "https://raw.githubusercontent.com/ethereum-optimism/superchain-registry/main/superchain/extra/addresses/addresses.json"

# 404s — do not waste a round-trip on it
# .../superchain/configs/configs.json
```

Fields per chain: `L1StandardBridgeProxy`, `OptimismPortalProxy`, `SystemConfigProxy`,
`L1CrossDomainMessengerProxy`, `ProxyAdmin`, `SuperchainConfig`, `DisputeGameFactoryProxy`,
`AnchorStateRegistryProxy`, `DelayedWETHProxy`, `Guardian`, `Challenger`, `BatchSubmitter`.
Keys mix mainnet and testnet L2s, so filter to a whitelist of undisputed mainnet chain IDs
(`10` OP, `8453` Base, `7777777` Zora, `480` Worldchain, `130` Unichain, `1868` Soneium,
`57073` Ink, `34443` Mode, `1135` Lisk, `1750` Metal, `5330` Superseed …).

```python
IMPL_SLOT = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
impl = "0x" + rpc("eth_getStorageAt", [proxy, IMPL_SLOT, "latest"])[-40:]
code = rpc("eth_getCode", [impl, "latest"])          # runtime bytecode
h    = keccak256(bytes.fromhex(code[2:]))            # pycryptodome Crypto.Hash.keccak
```

Hash equality across chains is conclusive: one byte of difference changes the hash, so an
identical hash means **no injected functions, no backdoor, no extra selector**. This is why
you can skip reading the source entirely when the hash matches.

Worked result (chain 9134):

| contract | impl | runtime bytecode hash | matched |
|---|---|---|---|
| L1StandardBridge | `0xb37a11aadf167b2f0b8dd85372de4bc66cd4a891` | `0xc58661e10e86c9d2…f86f` | OP Mainnet, Zora, Worldchain, Unichain, Soneium, Ink, Mode, Metal, Superseed (9) |
| OptimismPortal2 | `0xe89f13c5ee4033b2d3cd76c9d6958efbfe26d3c2` | `0x8352c8b920e2d04c…ac14` | Zora, Worldchain, Mode, Metal, Superseed (5) |
| SystemConfig | `0x42ad0173051225ac784100e9acd43349707f4db9` | `0x32d957b22978b0c3…c92d` | (version-distinct elsewhere) |
| SuperchainConfig | `0xe4f9779ab53070a55db24dfaeff9af147c6ed550` | `0x955b803d6253862e…ad36` | — |

Note the portal hash differs on OP Mainnet / Unichain / Soneium (`0xf8600b3ce05e08eb…`) — that
is a **release-version difference, not a red flag**. Match on *any* official chain; report the
set you matched against rather than requiring the whole set.

Proxy bytecode is worth hashing too. `L1ChugSplashProxy` (bridge, ~2472 B), `Proxy`
(portal/config, ~2059 B), `ResolvedDelegateProxy` (messenger, ~799 B) are the stock OP Stack
proxy types — a **custom** proxy shape here is the thing to be suspicious of.

## 2. Source verification

```bash
curl -s "https://<explorer>/api/v2/smart-contracts/<impl>"
# -> is_verified, name, compiler_version, optimization_enabled, language
```

Query the **implementation**, not the proxy (the proxy just reports `Proxy` /
`L1ChugSplashProxy`). Sourcify (`sourcify.dev/server/v2/contract/<chainId>/<addr>`,
`repo.sourcify.dev/contracts/full_match/…`) is keyless but had **no coverage** for these
impls — use it as a bonus, never as the primary check, and do not report "unverified" from a
Sourcify miss alone.

## 3. Upgrade history — was the implementation swapped after deploy?

```python
UPG = topic("Upgraded(address)")   # compute; do NOT paste a literal you have not verified
```

Read the events from **receipts** or an Etherscan-compatible endpoint with a topic filter
(`…/api?module=logs&action=getLogs&address=<addr>&fromBlock=0&toBlock=latest&topic0=<UPG>`).
An unbounded `eth_getLogs` over the full range fails.

Interpretation — the trap:

- `OPContractsManagerV2` deploys the impl, then deploys the proxy, then `upgradeTo`s the real
  impl **inside the same transaction**. That emits `Upgraded` **twice in one tx at the deploy
  block** (placeholder `0x2476c911…` → real impl).
- So "N `Upgraded` events exist" is **not** an upgrade. Confirm `block == deploy block` and
  that the tx hashes are equal.
- `L1ChugSplashProxy` (the standard bridge proxy) emits **no** `Upgraded` on `setCode`, so 0
  events there proves nothing on its own.

Worked result: portal + SystemConfig each 2 `Upgraded`, both at block 26063331 in tx
`0x15146622…` = the deploy tx; SuperchainConfig 1 at its deploy block 26063317; bridge 0.
**Conclusion: zero post-deploy upgrades.**

## 4. Who holds the upgrade key — and is the multisig real?

```
EIP-1967 admin slot 0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103
  -> ProxyAdmin
ProxyAdmin.owner()          -> often a Gnosis Safe
Safe.getThreshold() / getOwners() / VERSION()
```

Then the step that actually produces the finding — **trace the funders of each owner EOA**:

```python
alchemy_getAssetTransfers {"toAddress": owner, "category": ["external","internal"],
                           "order": "asc", "maxCount": "0x19", "withMetadata": true}
```

**If every owner of an n-of-n Safe was funded from the same address, the multisig is
effectively a single key.** The threshold number is theatre. This is the real rug vector: a
ProxyAdmin with no timelock can `upgradeTo` arbitrary code and drain whatever the escrow
contract holds.

Calibrate against official chains rather than judging in a vacuum:

| chain | ProxyAdmin owner | threshold |
|---|---|---|
| OP Mainnet / Unichain / Soneium | OP Foundation `0x5a0aae59…` | 2 (independent signers) |
| Zora | `0x4a496227…` | 4 |
| Worldchain | `0xa4fb12d1…` | 3 |
| **audited chain 9134** | `0xccc2aecf…` | **2 of 2, both EOAs funded from one address (`0x016606ac…`) → single key, no timelock** |

Also record: `SystemConfig.owner()`, `SuperchainConfig.guardian()`, and whether
owner == guardian (normal for these chains, so not a finding by itself).

## 5. Withdrawal liveness — is the exit path real?

This is the question users actually care about and the one most audits skip.

```
DisputeGameFactory.gameCount()          -> how many fault dispute games have EVER been created
DisputeGameFactory.respectedGameType()  -> portal.respectedGameType()
DisputeGameFactory.gameImpls(<type>)    -> is an implementation even wired for that type?
OptimismPortal2.anchorStateRegistry()
OptimismPortal2.paused()
```

Plus event counts on the portal: `WithdrawalProven`, `WithdrawalFinalized`.

Rule: a withdrawal must reference a respected dispute game that was proven and resolved.
`gameCount() == 0` means **no state root was ever proposed**, therefore **no withdrawal can
ever be proven**, therefore bridged ETH is **one-way** regardless of how canonical the code
is. A fully-wired `gameImpls(1)` + `anchorStateRegistry` with 7 `InitBondUpdated` /
`ImplementationSet` events just means the contracts are *ready* — not that anyone is running
a proposer.

Worked result: `gameCount() = 0`, `respectedGameType = 1` with `gameImpls(1)` set to a 24 KB
`FaultDisputeGame`, `WithdrawalProven = 0`, `WithdrawalFinalized = 0` → **enter-only**.

Also: a guardian with `pause()` rights can halt both directions at will (not theft, but a
liveness/exit risk worth naming).

## 6. Reconcile the bridged ETH to the wei

The strongest available proof that the endpoint is not lying. Sum the L2 `type 0x7e` deposit
values and compare against the `OptimismPortal2` native balance on L1:

```
OptimismPortal2 balance (L1)      = 1.09139300 ETH
Σ L2 type 0x7e values (15 deposits) = 1.09139335 ETH
residue                            = 0.00000035 ETH  = 35 gwei, pure precision
```

An exact match is hard to fake: a dishonest node would have to produce sums matching escrow
you read independently from Ethereum mainnet. State the independent side explicitly (L1 escrow
read from mainnet) versus the single-source side (L2 state from the leaked RPC).

Decoding note: the `TransactionDeposited` `opaqueData` is **ABI-encoded `bytes`** —
`[0:32]` offset, `[32:64]` length, `[64:…]` payload. It is not packed. Treating it as packed
yields garbage mint/gasLimit values.

## Verdict template

| aspect | answer |
|---|---|
| malicious code in the implementation? | no — byte-identical to the official release on N chains |
| suspicious custom proxy / backdoor? | no — stock proxy types |
| hidden post-deploy upgrade? | no — all `Upgraded` events are in the deploy tx |
| funds really bridged? | yes — reconciled to the wei against L1 escrow |
| admin safe? | **no** — n-of-n Safe, single funder, no timelock |
| can funds leave? | **no** — `gameCount() == 0` |

Ship all six. "Clean code" and "do not enter" are not contradictory, and the user needs both
halves — otherwise they read the bytecode match as a green light.
