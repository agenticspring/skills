---
name: web3-rpc-contract-audit
description: Verify a chain or RPC is authentic, identify proxy implementations, and audit contracts on new/low-profile EVM chains with no verified source — RPC-only (registry checks, domain forensics, OP Stack fingerprint, L1↔L2 binding, L1 suite code audit via canonical bytecode hash, admin/upgrade-authority forensics, withdrawal liveness, bridged-ETH reconciliation, chain-wide token/DeFi discovery via topic census, liquidity proof, rug vectors, mint readiness, fund flow, and executing a buy on a fresh venue's DEX via router discovery from the app bundle, receipt-proven fills, honeypot sign census, and post-mortem drain forensics for a bait chain — escrow balance sampling, drain-vs-withdrawal discrimination, mixer tracing, receipt-derived loss accounting, and the DEX contract-size authenticity gate).
---

# Web3 RPC Contract Audit (no source available)

When a target contract on a new/low-profile chain (e.g. Arc, NOXA Fun launchpad) has **no verified source** on the explorer, slither can't run (it needs Solidity source, not bytecode). Fall back to **dynamic RPC analysis** — pure `cast` calls against the live RPC. This catches the main rug vectors without source.

## When to use
- User says "audit token X", "audit contract", "cek aman ga ini contract" on a chain where explorer has no source
- Target is a meme token, launch factory, or DEX router on a fresh chain
- Blockscout `/api/v2/smart-contracts/<addr>` returns 404 / "default backend - 404"
- **User hands over a chain ID + RPC URL and asks "is this real?"** — see the section below

## Is this CHAIN / RPC itself authentic?

Different job from auditing one contract: you are deciding whether a whole chain is genuine and
whether the endpoint you were given is the project's own. The two answers are independent — a
**real chain behind an unofficial endpoint** is a different verdict from a **fake chain**.

Fast route (all free, no API key):

1. `eth_chainId` / `net_version` match the claim; `web3_clientVersion` names the stack.
2. **Tx per block across many blocks** (`eth_getBlockTransactionCountByNumber`). Uniform 1
   tx/block on an OP Stack chain = only the system deposit = **zero users**. Block production
   is a heartbeat, never evidence of activity.
3. Registry: `ethereum-lists/chains` `_data/chains/eip155-<id>.json` — is `rpc` populated or
   `[]`? Check the file's commit history too: a chain ID reserved early by the project's own
   team is exactly what makes a copycat convincing. Then the OP Superchain registry, then the
   project's own docs network table.
4. Domain forensics on the endpoint host — `whois` creation date, apex `A` records (often
   zero on a proxy front), TLS `notBefore`, reverse-proxy headers.
5. Identify the contracts with EIP-1967 slots, then name the implementation through
   Blockscout's public `api/v2/addresses/<addr>` (`implementations`, `proxy_type`, `creator`).
6. **Bind the L1 suite to the L2** — matching `SystemConfig.gasLimit()` against the L2 block
   `gasLimit`, plus L1 `bridgeETHTo`/`depositTransaction` calls reappearing as L2 `0x7e`
   deposits. Without a binding you merely have "some OP Stack somewhere".
7. Attribute the users: first-inbound funder via `alchemy_getAssetTransfers`, then classify
   the funder (high nonce + thousands of tokens = exchange hot wallet).

Full recipe, the OP Stack fingerprint, the throttle-proof census pattern, and the verdict
discipline (including how to publicly revise an over-strong earlier call) live in
`references/chain-and-rpc-authenticity.md`.

Safety line that matters: read-only `curl` JSON-RPC is fund-safe, but **never add an
unverified network to a wallet that holds keys** — wallets auto-probe your accounts, so a
hostile RPC clusters every wallet you own and can feed fabricated state.

### The two checks that separate a real chain from a convincing fake

Canonical bytecode proves nothing — **`OPContractsManager` (`0x0000000aa232009084bd71a5797d089aa4edfad4`,
23,569 B) is PERMISSIONLESS**. Anyone can call it to deploy a full OP Stack chain whose contracts
are byte-identical to OP Mainnet's. Byte-identical code + verified source is available to the
attacker at zero cost, so it can only ever be evidence about the *contract*, never the *chain*.

Ask these two instead:

1. **`SuperchainConfig` membership.** Every genuine Superchain chain shares the **one** central
   `SuperchainConfig` `0x95703e0982140D16f8ebA6d158FccEde42f04a4C` (guardian
   `0x09f7150d8c019bef34450d6920f6b3608cefdaf2`). A chain carrying **its own** `SuperchainConfig`
   — worked case `0x00811e2b…`, guardian = its own 2-of-2 Safe — is **not a Superchain member**:
   it is a standalone permissionless deployment. Cross-check `ProtocolVersions`
   (`0x8062AbC286f5e7D9428a0Ccb9AbD71e50d93b935` on real chains) the same way.
2. **Who funds the admin.** Resolve ProxyAdmin → Safe → owners → funders. A 2-of-2 Safe whose two
   EOAs were funded from one address means **one person holds the instant-upgrade key** to the
   escrow, with no timelock. Real chains put this behind the OP Foundation / a distributed set.

Plus, always, the **provenance of the endpoint itself**: who told you the RPC? A URL handed over
by an unknown party, on a domain whose apex has no DNS, is the actual attack surface. The
dev's own summary in the worked case: *"it's not enough for an RPC to return the chain ID — you
must verify the Ethereum-side rollup contracts are genuine AND that the RPC comes from a trusted
source, such as the main domain or a partner."* Chain-ID echo, a live block heartbeat, exact
L1↔L2 reconciliation and canonical contracts are **all reproducible by an attacker**; operator
provenance and Superchain membership are not.

### Deployment non-standardness, concretely

When someone says "the rollup contracts show it is not a standard deployment", the checkable
content is: (a) own vs shared `SuperchainConfig`/`ProtocolVersions`, (b) admin Safe owner
diversity and funders, (c) which caller invoked OPCM (`eth_getBlockByNumber(<deployBlk>, true)` →
`input` selector on the OPCM address — worked case `0x1828e0e7…`), (d) whether the chain ever
appears in the project's own docs / the Superchain registry. None of these require the project's
cooperation, and together they turn a vibe into a finding.

## Steps
1. **Get RPC.** ChainList/aggregator often has it before announcement. For Arc: `https://5042.rpc.thirdweb.com` (or `https://real-pump-soon-trust-me-bro-again.poptyedev.com/`). Verify live: `cast chain-id --rpc-url <RPC>`.
2. **Resolve token/pool.** If you have a pool address, read `token0()`/`token1()` via `cast call <POOL> "token0()(address)" --rpc-url <RPC>`.
3. **Probe for rug functions** (each `cast call` that reverts = function absent = good):
   ```bash
   cast call <ADDR> "owner()(address)" --rpc-url <RPC>      # revert = no owner
   cast call <ADDR> "mint()(bool)" --rpc-url <RPC>          # revert = no mint
   cast call <ADDR> "blacklist(address)(bool)" --rpc-url <RPC>  # revert = no blacklist
   cast call <ADDR> "excludeFromFee(address)(bool)" --rpc-url <RPC>  # revert = no fee exclusion
   ```
4. **Check upgradeability.** Look for `delegatecall` in bytecode: `cast code <ADDR> --rpc-url <RPC>` → grep for `delegatecall` (0xf4) or proxy slots. Absence = not upgradeable.
5. **Read metadata.** `cast call <ADDR> "name()(string)"`, `"symbol()(string)"`, `"totalSupply()(uint256)"` — catches naming spoof (e.g. symbol "USDC" on a non-USDC contract).
6. **Liquidity lock check.** Read token + quote balances of the LaunchLocker/expected lock contract: `cast call <LOCKER> "balanceOf(address)(uint256)" <TOKEN> --rpc-url <RPC>`. Zero = LP not locked → rug risk if not graduated.
7. **Selector scan (optional).** Fetch bytecode, grep for known 4-byte selectors (`owner`=0x8da5cb5b, `mint`=0x40c10f19, `blacklist`=0x...). Confirms which functions exist without calling.

## Red-flag verdict logic
- NO `owner`/`mint`/`blacklist`/`excludeFromFee` + NOT upgradeable → **contract-safe** (technically)
- BUT naming spoof (symbol "USDC" on random token) = **impersonation risk** — verify against official source. A community meme token using joke branding is NOT a scam; a token impersonating a real brand to steal is.
- LP not in locker + active factory owner = **caution** (can pull liquidity / set fees)

## AMM NFT utilization: inventory is not mint status

When a market UI shows `AMM Utilization` as `NFTs in pool / total capacity`, verify the implementation before interpreting it as mint progress. In the Anvil/Clutch market UI reviewed in this session, the displayed fields are sourced from the AMM vault's `inventoryLength()` and the collection's `totalSupply()`/configured NFT capacity. Therefore:

- A high utilization percentage means NFT inventory remains in the AMM vault/pool.
- It does **not** mean that percentage is unminted.
- NFTs can be minted/genesis-created first and then seeded into the AMM vault.
- The remainder is inventory outside that vault; it may be acquired, loaned, staked, or otherwise transferred depending on the contracts.
- Confirm minting with collection `totalSupply()` and `Transfer` events from the zero address; confirm why inventory left with AMM purchase/loan/staking events and holder balances.

For a 3,333-capacity collection, 85% implies roughly 2,833 units in the pool and roughly 500 outside, but do not label the latter as sold without event-level verification.

## Mint-readiness check (is mint live?)

When the question is "udah bisa mint?" — site shows a MINT button but you must verify the contract, not the UI. A live frontend with a mint button does NOT mean mint is enabled on-chain; projects soft-launch the site before flipping the switch.

1. **Get the ABI.** For a VERIFIED contract, Blockscout v2 returns the full ABI:
   ```bash
   curl -s "https://<chain>.blockscout.com/api/v2/smart-contracts/<ADDR>" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('abi') or []))"
   ```
   Enumerate function names and look for mint-gating fns: `mintActive`, `mintStatus`, `mintFinished`, `price`, `maxSupply`, `maxPerWallet`, `totalMinted`, `mintsLeft`, `tokensPerNft`, `publicMinted`.
2. **Read state via cast:**
   ```bash
   cast call <ADDR> "mintActive()(bool)" --rpc-url <RPC>
   cast call <ADDR> "mintFinished()(bool)" --rpc-url <RPC>
   cast call <ADDR> "mintStatus()(uint256)" --rpc-url <RPC>
   cast call <ADDR> "price()(uint256)" --rpc-url <RPC>
   cast call <ADDR> "maxSupply()(uint256)" --rpc-url <RPC>
   cast call <ADDR> "maxPerWallet()(uint256)" --rpc-url <RPC>
   cast call <ADDR> "totalMinted()(uint256)" --rpc-url <RPC>
   cast call <ADDR> "tokensPerNft()(uint256)" --rpc-url <RPC>
   ```
3. **Verdict:** `mintActive()==false` (or `mintStatus()==0`) + `totalMinted()==0` → **mint locked**; warn user not to waste gas. `price()` + `maxSupply` + `maxPerWallet` configured but switch off = admin prepped the launch, waiting to call `setMintActive(true)`.
4. **Cross-check explorer:** NFT `token-transfers` count == 0 confirms no mints have happened yet.

To keep watching a pre-launch mint without burning tokens: a `no_agent=true` cron watchdog script that reads `mintActive()`/`totalMinted()` and alerts ONLY on transitions (open/close/sold-out) via state files. Full pattern: `references/mint-state-cron-watchdog.md`.

Full recipe + Robinhood Chain 4663 RPCs: `references/mint-readiness-check.md`.

## Verifying "official launch" claims (token deployed via project X's GitHub)

When a tweet/CT claims "this token is official — deployed with the address in project X's GitHub" (e.g. Uniswap's liquidity-launcher-sdk / pools.trade on Robinhood Chain), verify end-to-end instead of trusting the screenshot: fxtwitter API reads the tweet (no browser), tesseract OCRs the screenshots, raw GitHub fetch + commit-history grep checks whether the claimed address ever existed, Blockscout v2 `creator_address_hash` ties the token to the official factory, internal-tx decode shows the launch flow (EOA → launcher → factory create2 → token), and timeline triangulation validates "first launch" claims. Verdict logic: infra legit ≠ token endorsed — the factory is permissionless, so anyone can `createToken`; "deployed with addy in GitHub" means "created through the factory whose address is in GitHub", NOT "the team deployed this token". Full recipe: `references/official-launch-claim-verify.md`.

## Fund-flow tracing (where did the money go)

When mint is live/sold-out and the user asks "apakah dana di-hold / WD ke exchange / dev narik duit": decode the `withdrawTo`/`depositNative` logs via `cast receipt` — topics[1] = recipient, data = amount (never trust the tx `value` row, it's 0 for internal moves). Distinguish bridge contracts (`RelayDepository` = Robinhood bridge, not Binance) from exchanges; scan intermediary wallets' outbound txs; check `holderSink()` vs actual balances to answer held-vs-moved. Tracing past a bridge: `callRequests(id)(bool)`==false = processed (Relay settles on the DEST chain, so source-chain execute txs never match); cross-chain balance via keyless Blockscout (Etherscan V1 deprecated); Blockscout v2 paginates via `next_page_params`, NOT `?page=`; BSC nonce check proves the BNB pass-through path even at 0 balance; cross-reference X/web analysts when EVM tracing dead-ends (they often found the destination tx hash). Full recipe: `references/fund-flow-tracing.md`.

## Auditing an L1 contract suite — "apakah ada kode berbahaya?"

Once real funds sit in a bridge, the next question is whether the L1 contracts can steal them.
Auditing the *implementation* is not the first move: check whether the code is the **canonical
release**, then check **who can replace it** and **whether an exit path exists at all**.

In the worked case the implementations were byte-identical to the official OP Stack release and
the source was verified on-chain — and the verdict was still *do not enter*, because a 2-of-2
Safe whose two EOAs were funded from a single address held the upgrade key with no timelock,
and `DisputeGameFactory.gameCount() == 0` meant no withdrawal could ever be proven.
**Clean code + instant upgrade key + no exit path = do not enter.** Report both halves; a
bytecode match reported alone reads as a green light.

1. **Bytecode hash vs a canonical multi-chain baseline** — strongest cheap test, needs no
   source. Resolve each proxy's EIP-1967 impl slot, keccak256 the runtime bytecode, compare
   against the same contract's impl on known-good mainnet chains. Baseline addresses:
   `raw.githubusercontent.com/ethereum-optimism/superchain-registry/main/superchain/extra/addresses/addresses.json`
   (keyed by **L2 chain ID**; the `configs.json` path 404s — use `extra/addresses/`). An
   identical hash across official chains means the bytecode is unmodified: no injected
   functions, no backdoor, no extra selector, and no need to read source. A hash that differs
   from one chain but matches another is a **release-version difference, not a red flag**.
2. **Confirm the source is published** — `https://<explorer>/api/v2/smart-contracts/<impl>`
   (`is_verified`, `name`, `compiler_version`). Query the **impl**, not the proxy. Sourcify is
   keyless but has poor coverage on new chains; never call something unverified on a Sourcify
   miss alone.
3. **Find the real authority.** EIP-1967 admin slot → `ProxyAdmin.owner()` → Safe
   `getThreshold()` / `getOwners()` / `VERSION()`. Then trace the funders of **every** owner EOA
   with `alchemy_getAssetTransfers` (`toAddress:<owner>`). **Owners sharing one funder means an
   n-of-n Safe that is effectively a single key** — the threshold is theatre, and a ProxyAdmin
   with no timelock can `upgradeTo` arbitrary code and drain the escrow. Calibrate against
   official chains (OP Mainnet / Unichain / Soneium admin = the OP Foundation Safe; Zora 4-of-N;
   Worldchain 3-of-N).
4. **Check the exit path, not just the entrance.** `DisputeGameFactory.gameCount()`,
   `respectedGameType()`, `gameImpls(<type>)`, `OptimismPortal2.anchorStateRegistry()`,
   `paused()`, plus `WithdrawalProven` / `WithdrawalFinalized` log counts. `gameCount() == 0` =
   no state root was ever proposed = no withdrawal can be proven = **bridged funds are
   one-way** — no matter how canonical the contracts are. A guardian with `pause()` can halt
   both directions at will.
5. **Reconcile the bridged ETH to the wei.** Σ L2 `type 0x7e` deposit values vs the
   `OptimismPortal2` native balance on L1. An exact match is the strongest available proof the
   endpoint is not lying, since a dishonest node would have to fabricate sums matching escrow
   you read independently from L1.

Full recipe, the worked numbers and the verdict template: `references/l1-suite-code-audit.md`.
Re-runnable probe: `scripts/l1_suite_audit.py` (point `TARGETS` at a chain's L1 contracts; it
resolves impls, compares against the canonical baseline, unrolls admin/Safe/funder, and checks
withdrawal liveness).

## Executing the bridge IN — "coba bridge sedikit, gua udah siap hilang"

The recon verdict is **not** a refusal. Once the user has been told the funds are one-way and
explicitly accepts it, execute — state the risk **once** in the plan message, then work without
re-hedging every step. Repeated warnings after acceptance read as stalling.

Use a **fresh one-shot wallet per test** so the worst case equals what was sent to it, never the
user's main holdings. The parts that actually bite:

1. **Dry-run with no funds** — `eth_estimateGas` needs balance and `eth_call` accepts
   `stateOverrides`, so overrides are how you validate calldata on an empty wallet.
2. **Compute selectors, never recall them** — `cast sig "bridgeETHTo(address,uint32,bytes)"` →
   `0xe11013dd`; `cast 4byte-decode` confirms the arguments round-trip. A remembered selector that
   happens to be wrong is a silent misfire.
3. **`maxPriorityFeePerGas <= maxFeePerGas`** — a 1 gwei tip over a 0.12 gwei ceiling is rejected
   on every attempt with a cryptic `-32003`. Nothing is spent, but the retry loop hides the cause.
4. **`bridgeETHTo` costs ~621 k gas, not ~180 k.** Fund against a ~700 k ceiling.
5. **Find the L2 deposit tx by anomaly blocks** (`eth_getBlockTransactionCountByNumber > 1`), not
   by `to == recipient` — the bridge routes via `L2CrossDomainMessenger`, so `to` is
   `0x4200…0007`. Same sweep doubles as a new-activity census.
6. **Verify the full chain**, not the hash: L1 receipt → decoded `TransactionDeposited` → L2
   balance poll → L2 deposit tx → **portal balance delta vs Σ new L2 deposits**.
7. **Expect "why this contract and not that one?"** as soon as you name the target address. Do not
   answer with mechanics. Give the model (**bridge = pass-through front desk, portal = the vault**),
   *prove* it with three `eth_getBalance` reads (bridge `0`, messenger `0`, portal = everything),
   show the receipt log order, then close with the point that matters: **both sit behind the same
   admin, so the door choice changes nothing about safety — only gas.**

8. **Announce where the key lives before being asked.** Creating a fresh wallet invites the
   immediate question *"kau taruh mana PK nya?"* — pre-empt it in the same message that reports the
   address: absolute path, `chmod 600`, the file-mode string (`-rw-------`), the byte length,
   confirmation it is **not** in `.env`, git, or the notes vault, and the address re-derived from
   the stored key so the reader can see the two match. Never print the key, and state that the
   worst case is bounded by that wallet's balance because it is fresh and not connected to the
   user's other holdings. Offer `shred -u` once the test is over.

Fund-gated runs: ship a watcher that polls the balance and fires the broadcaster on arrival
(time-boxed, exits silently without sending if never funded) instead of polling by hand in chat.

Full recipe, encoding, fee math, the aliasing correction, the bridge-vs-portal explanation model,
endpoint quotas and the reporting template: `references/l1-to-l2-bridge-deposit-execution.md`.

## "Are there already tokens / any DeFi activity on this chain?"

A distinct job from auditing a contract you were handed: **enumerate what exists**. For a chain
with no token list and no working log index, the only reliable source is a **chain-wide log
census by topic, filtered client-side**. The worked case is the lesson — the explorer showed
**zero tokens** on a chain that actually held **3 ERC-20s plus a full Uniswap V3+V4 deployment**.

1. **Send `topics` only, never `address`.** Address-filtered `eth_getLogs` returned `[]` on a
   node that served the same address's logs fine under a topic-only scan. Chunk ~2000 blocks,
   split to ~250 on error, ~3 workers, retry with backoff. Re-runnable:
   `scripts/chain_topic_census.py` (supports `--preset tokens|defi|all`, client-side
   `--address`, and reports a genuine zero differently from an RPC failure).
2. **The topic menu** — `Transfer` finds every ERC-20/721; `Approval`, `Swap`, `Mint`,
   V3 `PoolCreated`, V4 `Initialize` each prove a different kind of DeFi activity. On the worked
   chain the entire ~20.5k-block history held **5 `Transfer` logs and zero of everything else**,
   so the whole activity surface was bounded rather than sampled.
3. **Prove liquidity by absence.** `factory.getPool(token, WETH, fee)` across **every fee tier**
   (500/3000/10000) returning `0x0` = no pool anywhere = not tradeable at any price. Add the
   DEX position-manager NFT `totalSupply()` — one call that shows whether *any* LP position was
   ever minted. "Token exists" and "token is tradeable" are separate claims; users conflate them.
4. **Attribute tokens via receipts, not `contractAddress`.** Receipt `contractAddress` reports
   only the outermost creation, so a token created by an intermediate contract shows `null` and
   looks deployer-less. Pull the token's earliest log → that block with `eth_getBlockByNumber`,
   then read `receipt.logs[].address` — a log emitted by the token inside tx *T* means *T*
   created it.
5. **Recognise "deploy via bridge".** A `type 0x7e` deposit carrying init code deploys a
   contract on an OP Stack L2 **without the L2 address ever holding gas** — which is why
   creators can show `nonce 1` / `balance 0` while having deployed. The mirror also explains how
   a deposited address gains a nonce with no signed L2 tx.
6. **Read mints correctly.** `Transfer(0x0→X,N)` then `Transfer(X→Y,N)` in one tx is **one mint
   plus one move**, not two mints — reconcile against `totalSupply()` before quoting supply.
7. **Interpret the pattern.** DEX + launchpad + test memecoins on an otherwise empty chain is a
   **launch rehearsal**, not random. Name the contracts by probing `factory()`, `WETH9()`,
   `poolManager()`, `permit2()`, `positionManager()`, `token()`, `owner()` and compare against
   the canonical Uniswap addresses — fresh addresses mean someone deployed their own copy, so
   the venue is not official. Then state the two consequences: expect launch-day meme season,
   and **any "project mainnet token" offered before the project's own announcement is not the
   project's** (no pool = no price).

8. **Enumerate every contract, then order by creation block**, for the follow-up asks "yang
   first deploy mana?" / "berikan seluruh CA". Build the set from **both** sources —
   `receipt.contractAddress` (outer creations) **and** every address reachable from
   `receipt.logs[]` (see the pitfall about topics below). A contract created *inside* another
   contract has no receipt `contractAddress`, so its creation block is the block of the
   enclosing tx; a contract that only *received* a value has no creation record at all and must
   be dated by its first appearance in any log. Exclude OP Stack predeploys from a
   "deployed by users" list, and keep 0-byte-code entries in the list labelled
   `self-destructed` rather than dropping them.
9. **Report deploy order as evidence, not as a wall.** Group by `(block, deployer)` and give the
   block timestamp (`eth_getBlockByNumber` → `timestamp`) so the reader sees the actual cadence —
   in the worked case three memecoins landed inside ~95 minutes, which is what identified the
   whole thing as one rehearsal. When the user then narrows the ask ("kasih CA meme aja"),
   answer with **only that subset, in deploy order, in one copy-paste block** — no re-explaining
   the audit.

Full recipe, topic menu and worked numbers: `references/chain-token-discovery.md`.

## Buying on a fresh chain's DEX — "beli token ini, cepat"

Once the recon says "there is a pool", the user will want in. This is the **write** counterpart to
the census work, and the whole job is *finding a call shape that has provably worked before*, then
proving the fill from the receipt. Do not hand-build calldata from memory, and do not trust the
DApp's own numbers.

0. **Gate on contract size before anything else.** `eth_getCode` the pool, factory and router and
   compare against real venues: a genuine Uniswap V3 pool is **20–25 KB**, factory ~20 KB, router
   ~30 KB. A "DEX" whose whole contract set is **under ~5 KB** is a set of stubs — the worked case
   had a **332-byte pool** and a 2,188-byte router, and the buy still executed and still emitted a
   token `Transfer`. A stub can take your ETH; it cannot give it back, because the sell path was
   never implemented. **Printed byte sizes are dispositive — treat them as a stop, not a
   curiosity.** See `references/bait-chain-rug-forensics.md`.

1. **Get the DEX addresses from the app's JS bundle, not its docs.** The token page is a thin
   client; the contract set is baked into the bundle as a config object. Fetch the page, pull
   `src="…/chunk-*.js"` tags, concatenate them, and grep for
   `swapRouter:b("0x…")`, `v3Factory:b("0x…")`, `positionManager:b("0x…")`, `quoter:b("0x…")`,
   `pairToken:b("0x…")`. In the worked case this revealed the venue ran **its own** V3 factory —
   `getPool()` against the chain's *other* factory returned `0x0` at every fee tier and would
   have concluded "no pool exists" one line before the buy. **A pool is scoped to a factory:**
   always ask the factory the DApp actually routes through.
2. **Read the fee tier off the factory, not off the UI.** Loop `getPool(token, WETH, fee)` over
   100/500/3000/10000 and take the non-zero result; a non-standard tier like `10000` is normal on
   a fresh venue.
3. **Copy the calldata shape from a real tx in the same pool.** Scan that pool's `Swap` events by
   topic, take a recent tx hash, and `eth_getTransactionByHash` → dump `input`. The selector and
   argument order you get this way are ground truth; a remembered ABI is a silent misfire.
   `cast 4byte-decode` the input to confirm the struct. (Worked selector:
   `0x414bf389` = the 8-field `exactInputSingle`.)
4. **Simulate, then set a slippage floor.** `eth_call` with `{from, to: router, data, value}` from
   the real buyer returns the quoted `amountOut` — that is your only price check. Rebuild the
   calldata with `amountOutMinimum = quote * 0.90` and **simulate again**; only then broadcast.
   The quote is not a promise: the worked buy received 96.8 % of quote in the same block, so the
   floor is what saves you, not the quote.
5. **Cross-check the UI's liquidity figure against on-chain balances.** `balanceOf(pool)` for the
   token **and** the WETH ERC-20 (`0x4200…0006`), plus native `eth_getBalance` — WETH sits in the
   WETH9 contract, so a native-ETH read of a WETH pool is legitimately `0` and means nothing. The
   site claimed `Liquidity $39.80K`; on-chain held 14.9 WETH ≈ $40 k. When they agree, the venue
   is real; when the site claims depth the pool does not have, walk away.
6. **Compute the price from `slot0().sqrtPriceX96`** — `price = (sqrtPriceX96 / 2**96)**2` gives
   token1-per-token0. Use it to (a) sanity-check the quote, (b) compare successive buys so you can
   tell the user what moved, and (c) size the market cap. Re-read it after each fill; all-buy
   pools drift upward fast (the worked token moved +37 % between two of the user's own buys).

### Honeypot check: census the pool's Swap signs

A pool that only ever absorbs buys has an **unproven exit**. Scan every `Swap` event for the pool
and classify by the sign of `amount0`:

- **`amount0 > 0` → the pool RECEIVED token0 → a BUY.**
- **`amount0 < 0` → the pool PAID OUT token0 → a SELL.**

(Getting this backwards is easy and was done in the worked session — sanity-check the sign against
the tx `value`, which is non-zero for a buy and often `0` for a sell.) Zero sells across a long
history means the sell path is **unverified, not proven broken**. State it that way and offer the
cheap experiment: sell a small slice and see if it clears. A sell test costs one gas fee and is the
highest-value information available once the user is holding.

### The trap: a successful trade reported as a failure

**Post-trade balance reads are not evidence.** Under load the balance `eth_call` returns `429`,
your helper collapses the failure to `None`, `None or 0` renders as `0`, and the script prints
*"DID NOT RECEIVE — FAILED"* on a trade that in fact succeeded. This happened twice in one session
and both times the tokens had arrived.

Verify a fill from the **receipt**, then confirm the balance separately:

1. `eth_getTransactionReceipt` → `status == 0x1`.
2. Walk `receipt.logs[]` for the token's `Transfer` topic and find the leg whose **destination is
   the buyer** — that is the delivery proof, and it exists independently of any balance query.
3. Only then read `balanceOf` with a real retry loop (`need()`-style: keep retrying until a
   non-empty result), and never let a failed read masquerade as a zero.

Generalise it: **any helper that maps an RPC failure to `0`/`None` will eventually report a false
negative on the most important number in the task.** Give critical reads a distinct failure sentinel
and print `FAILED`, so "the call broke" can never be mistaken for "the value is zero".

### When the user overrides the risk assessment

"Langsung beli, gua udah cek, dev legit, cepat" is a direct order, not a request for more analysis.
The recon is not a veto. **State the risk once, in the same message where you name the blockers, then
execute** — re-hedging after each step reads as stalling. What you may not skip is the part that is
load-bearing rather than advisory: you cannot construct a swap without the pool, fee tier and router,
so "just buy blind" is answered by doing that discovery *fast*, not by refusing.

Guards to keep even when the user says hurry: simulate before broadcasting, keep the
`amountOutMinimum` floor, spend from a **fresh throwaway wallet** so the worst case equals that
wallet's balance, and report the receipt-derived fill. Then flag the residual honestly and once —
unproven sell path, gas as a percentage of a small ticket (174 k gas ≈ 12 % of a 0.0037 ETH buy),
and funds being one-way if `DisputeGameFactory.gameCount() == 0`.

Full worked recipe — JS-bundle extraction, pool discovery across factories, exactInputSingle
encoding, sign census, receipt-verification script and the reporting template:
`references/onchain-dex-buy-execution.md`.

## Post-mortem: the venue was a bait chain — drain forensics

A chain can pass every contract-level check in this skill and still be a bait operation. Verified in
the worked case: canonical byte-identical L1 suite, verified source, zero upgrades, exact L1↔L2
reconciliation — and **~765 ETH (~$2.06 M) was still drained out of the escrow and laundered through
Tornado Cash.** The canonical portal is a *façade that collects ETH*; the theft happens at the
operator layer, not the code layer.

Run this when the endpoint dies, a balance looks wrong, or the user reports a loss.

1. **Sample the escrow balance at historical blocks** — `eth_getBalance(addr, <blockNumber>)`. This
   is the only trustworthy magnitude. A handful of samples either side of the event turns
   "something looks off" into an exact figure and block (worked: 766.19650981 ETH at blk 26067300 →
   1.24905000 ETH at 26067350 — a single **−764.947 ETH** move).
2. **Prove it is not a withdrawal** before calling it a drain: `gameCount() == 0` +
   `WithdrawalProven == 0` + `WithdrawalFinalized == 0` + unchanged impl + `paused() == 0` means no
   withdrawal *could* have been proven, so ETH leaving is not one.
3. **Trace the outflow** with `alchemy_getAssetTransfers({fromAddress: drainer})`. Mixer
   recognition: fixed **10 ETH / 1 ETH denominations** repeated in a minutes-long burst, confirmed
   by a public label (`api/v2/addresses/<addr>` → `name: "TornadoRouter"`) rather than an eyeballed
   address pattern. Router and pool addresses share long prefixes — always label, never
   pattern-match by eye.
4. **Never build a magnitude from `txlistinternal`.** Proxy `delegatecall` accounting invents rows
   with the *implementation* as counterparty; the worked listing claimed 721 transfers "totalling
   284 ETH" plus a 766 ETH row from a contract that never held more than ~19 ETH at that time.
5. **Report mechanism → laundering → exposure → next actions**, and record **which signal was
   missed** (here: printed 332-byte / 2 KB contract sizes). A post-mortem that only recites the
   operator's crimes teaches nothing reusable.
6. Tell the user that **a "recovery service" that DMs first is a second-stage scam aimed at
   victims**, to revoke approvals on any wallet that touched the DApp front-end, and that funds
   through a mixer are realistically unrecoverable.
7. **Quantify the loss from receipts, then reconcile it to zero.** *"Berapa ETH yang kita spent?"*
   is the standard follow-up, and it must come from receipts, never from the figure the user
   remembers or the DApp displayed.
   - **L1 side:** per bridge tx, `receipt.gasUsed × receipt.effectiveGasPrice` is the fee, and the
     tx `value` is what actually crossed. Sum both.
   - **L2 side:** the swap `value` plus the swap receipts' `gasUsed`. **Capture `gasUsed` at
     execution time and write it down** — the bait RPC dies at rug time, so L2 receipts become
     unreadable afterwards and an itemised L2 breakdown is only possible from notes taken while the
     endpoint was alive. Record it in the incident note the moment each swap lands.
   - **Self-check that makes the answer trustworthy:**
     `Σ bridged − Σ swap values − Σ swap gas == residual wallet balance`. In the worked case
     `0.02236000 − 0.02040000 − 0.00066349 = 0.00129651` against an observed `0.00129650` — tie-out
     to the wei, which is what lets you say "no ETH is unaccounted for". If it does **not** tie out,
     you have missed a transaction; find it before quoting a total.
   - **Report the loss in layers**, because they answer different questions: total out of pocket
     (bridged + L1 gas) → amount actually deployed into the venue → amount spent buying → residual
     stranded. The user cares most about the middle number ("how much did I burn on tokens") and
     will accept the outer one once the layers are separated.

**The containment that worked:** bridging and trading from a **fresh one-shot wallet** whose L1
history contains only plain transfers to the canonical bridge — no approvals — bounded the loss to
that wallet. Never let a wallet holding value connect to an unverified endpoint or DApp.

Full case study, byte-size table, drain timeline, laundering flow and the pre-buy checklist:
`references/bait-chain-rug-forensics.md`.

## Pitfalls
- **Blockscout API 404**: the `/api/v2/smart-contracts/<addr>` endpoint often returns "default backend - 404" for unverified contracts or wrong path. Don't waste time — go straight to `cast` RPC calls.
- **Wrong RPC**: never assume `llamarpc.com` or generic RPCs serve a specific new chain. Get the chain's actual RPC (often leaked before announcement — see rpc-mainnet-leak-monitor skill).
- **Symbol spoof ≠ scam**: a token named "FatCatBatRatWifHat" with symbol "USDC" on Arc is a community meme token, NOT Circle's USDC (`0x3600...0000` on Arc). Always compare contract address, not name/symbol.
- **cast needs `--rpc-url`**: omitting it defaults to ETH mainnet and gives wrong/empty results.
- **`cast codesize` > 0 = contract live**, but `cast code` returns full bytecode for selector analysis.
- **A zero you got from a FAILED call is the most dangerous wrong answer.** An unbounded
  `eth_getLogs` (`fromBlock:"0x0"` → `latest`) returns an **error**, not an empty list. A helper
  that collapses errors into `[]`/`0` will happily report "0 deposits", "0 upgrades", "0
  withdrawals" — and you will believe it and put it in a verdict. Make the RPC wrapper return a
  distinct error sentinel and print `FAILED` rather than a number; distinguish "no events" from
  "the call failed". Read logs from **tx receipts** or an Etherscan-compatible endpoint with a
  `&topic0=` filter instead.
- **Indexers are incomplete on brand-new chains — never treat them as evidence.** For one
  portal, Blockscout returned 11 of 14 `TransactionDeposited` logs and 13 of 14 txs, and one
  whole 0.05 ETH deposit was missing from both; `alchemy_getAssetTransfers` +
  `eth_getTransactionReceipt` found it. Verify amounts by receipt and reconcile totals — **a gap
  in the indexer must never be reported as a gap in the money.**
- **Two `Upgraded` events in ONE tx at the deploy block are not an upgrade.** That is the
  `OPContractsManagerV2` pattern (placeholder impl → real impl inside the same tx). Confirm
  `block == deploy block` and matching tx hashes before calling anything an upgrade. Also
  `L1ChugSplashProxy` emits **no** `Upgraded` on `setCode`, so 0 events there proves nothing.
- **Decode deposit `opaqueData` as ABI `bytes`** — `[0:32]` offset, `[32:64]` length, `[64:…]`
  payload. It is **not** packed; treating it as packed silently yields garbage mint/gasLimit.
- **A Safe threshold alone is not a safety signal.** Read the owners' funders. Two EOAs funded
  from one address control the upgrade of everything regardless of the threshold number.
- **Address-filtered `eth_getLogs` can silently return `[]`.** On self-hosted/leaked endpoints a
  query carrying an `address` key returned empty while the identical range with only a `topics`
  key returned that address's real logs. Never conclude "this contract emitted nothing" from an
  address-filtered call — rescan topic-only and filter in your own code. (Distinct from the
  unbounded-range error above: here the call *succeeds* and lies by omission.)
- **An explorer showing zero tokens is not evidence of zero tokens.** A chain with no token
  index and no registry lists nothing while real ERC-20s and a full DEX sit on it. Enumerate
  with a topic census, not a search endpoint.
- **`receipt.contractAddress == null` does not mean "nobody deployed."** It means the *outer*
  tx created nothing — an intermediate contract may have created the token. Attribute via
  `receipt.logs[].address` matched against the token's own emitted logs.
- **Collecting only `log.address` loses every contract that never emitted a log.** In the worked
  case the contract holding 100% of a token (a 9,481-byte bonding curve) appeared in no receipt
  `contractAddress` and emitted no log of its own — it was visible *only* as the `to` argument of
  a `Transfer` event. Harvest the `topics[1..]` participants alongside `log.address`, or you will
  silently ship an incomplete contract inventory and call it complete. Same applies to a
  deployer-supplied address list: cross-check it against the on-chain set before agreeing.
- **OP Stack predeploys are not "deployments".** `0x4200…0000`–`0x4200…0060` (plus `0x4200…0100`
  / `0x4200…0101`) carry code from genesis; many share one identical 2059-byte `Proxy` bytecode,
  which is normal and not a red flag. They also turn up inside a *user* tx's log set (a call to
  `L2CrossDomainMessenger` / `L2StandardBridge` pulls their addresses in), so filter them out
  before quoting a count of user-deployed contracts.
- **A protocol's own deployment addresses are the identity check.** Comparing a chain's DEX
  contracts against the canonical Uniswap deployment addresses shows whether it is the real
  venue or a fresh copy deployed by a third party — same source, different operator.
- **L1→L2 address aliasing inflates "unique user" counts.** When an **L1 contract** deposits, the
  L2-side sender in `TransactionDeposited` topic1 is `real_address + 0x1111…1111` (32 hex chars of
  the offset). Two addresses exactly that constant apart are **one actor**. In the worked case an
  alias of `L1CrossDomainMessenger` had been counted as a user wallet, making the census "11 users"
  when the truth was 10. Never count topic1 senders as distinct users without subtracting aliases —
  check `alias − candidate == 0x1111…1111`, and note `bridgeETHTo` always produces an alias.
- **An address-filtered `eth_getLogs` is not the only silent empty.** Alchemy's free tier **caps
  `eth_getLogs` to a 10-block range** and rejects wider queries with `-32600`, so a wide scan on a
  managed endpoint fails where the same scan works on a self-hosted node. For wide ranges use an
  Etherscan-compatible endpoint with `&topic0=`, or per-block
  `eth_getBlockTransactionCountByNumber` (a few bytes per call — thousands of blocks stay cheap).
- **`eth_estimateGas` checks balance and ignores `stateOverrides`.** On an unfunded wallet it fails
  `EVM error: OutOfFunds`; on Alchemy even passing overrides errors `Invalid params`. Use
  `eth_call` **with** `stateOverrides` to dry-run, and budget gas from a fixed ceiling instead of
  an estimate. Also: a deposit via `L1StandardBridge.bridgeETHTo` uses **~621 k gas**, roughly 3×
  a plain transfer.
- **`maxPriorityFeePerGas` must be `<=` `maxFeePerGas`.** A tip larger than the fee ceiling —
  e.g. `tip = 1 gwei` with `maxFee = baseFee * 2` ≈ 0.12 gwei on a quiet L1 — is rejected on every
  attempt with `-32003 max priority fee per gas higher than max fee per gas`. Set
  `maxFee = base*2 + tip`. Treat that error string as fatal, not transient: retrying cannot fix it.
- **A failed RPC read is not a zero — and you will report it as one.** A helper that collapses an
  error to `None`/`0` turns a `429` into *"balance 0"*, so a trade that succeeded gets reported as a
  failure. Give critical reads a distinct failure sentinel, print `FAILED`, and prove fills from
  `receipt.logs[]` (the token `Transfer` whose destination is the buyer) before consulting any
  balance. Two live trades were mis-reported this way in one session; both had filled.
- **A pool is scoped to one factory.** `getPool()/getPair()` against the chain's *other* factory
  returns `0x0` at every fee tier while the DApp happily routes through its own. Ask the factory the
  app actually uses — harvest the address set from its JS bundle — or you will conclude
  "no liquidity" one call before a successful buy.
- **`Swap.amount0` sign is easy to invert.** Positive = the pool *received* token0 = a **buy**;
  negative = the pool *paid out* token0 = a **sell**. Cross-check any census against the tx `value`
  (non-zero for a buy) before announcing "nobody has ever sold".
- **`eth_estimateGas * 2` is a balance bug in disguise.** Doubling an already-conservative estimate
  inflates the node's up-front reservation (`gasLimit * maxFeePerGas + value`) and the tx is rejected
  `insufficient funds for gas * price + value: have X want Y` on a wallet that holds plenty. Use a
  fixed ceiling from measurement; recover the real reservation from `want - value`.
- **DEX contract size is the cheapest authenticity test and it outranks every other check.** A
  **332-byte pool**, a 2 KB router and a 2 KB factory are stubs — real Uniswap V3 runs 20–30 KB.
  Stubs can accept ETH and emit a token `Transfer`; they cannot implement a sell. If you print the
  sizes and do not treat them as a stop, you have skipped the one check that would have saved the
  user. (A 1.4–1.9 KB bare ERC-20 and a 2,059-byte OP Stack predeploy `Proxy` are *normal* — do not
  flag those.)
- **Canonical bytecode on an unannounced chain is camouflage, not a guarantee.** Byte-identical OP
  Stack contracts, verified source, zero post-deploy upgrades and exact L1↔L2 reconciliation are all
  consistent with a bait operation: the canonical portal simply collects whatever is sent to it.
  When the chain was never announced by the project it names, a bytecode match is evidence about the
  *contract only* and must not raise the chain-level verdict.
- **An all-buy `Swap` history is the shape of the bait, not a neutral unknown.** Buys with zero
  sells across a long history mean the exit path was never implemented. Do not file it as "unproven
  — offer the user a sell test"; file it as **"assume you cannot exit."**
- **`txlistinternal` invents transfers for proxy contracts.** Blockscout listed 721 "outflows" from
  a portal to its own *implementation* address, totalling multiples of the escrow's real balance.
  Use per-block `eth_getBalance` sampling for magnitudes and a receipt for any single cited event.

## Verification (what we confirmed on Arc/NOXA Fun)
- NOAH token `0x0006ED5d37A9d6687d1ecc8B642Ff9C4760d9a16` (pool `0xefae...`): no owner/mint/blacklist, not upgradeable → SAFE. Symbol "USDC" = community meme joke, confirmed by user (not Circle).
- LaunchFactory `0xE7d4E64079FE467A21801B36Ccc6D9B3F66BD372`: has `owner()` + `maxTxAmount()` → active owner risk. Not upgradeable.
- V3Factory owner `0x33F26c...51E8` → can set fee tier.

## Responsible Bug-Bounty Workflow

When the user wants to audit a Web3 target for a bug-bounty submission (for example through Immunefi), do not jump straight to exploit testing:

1. Select a program with a manageable surface (vault/lending/accounting protocols are a reasonable first target; bridges and consensus systems are not beginner targets).
2. Read the live program information and scope pages before testing. Record in-scope addresses, chain IDs, source repositories, accepted impacts, severity/reward table, PoC requirements, KYC/payout requirements, exclusions, duplicate policy, and disclosure rules.
3. Verify deployed bytecode and source/address correspondence on every in-scope chain. Do not infer scope from a project name or website.
4. Model the attack path and protocol invariants first. A price drop, design trade-off, or generic centralization concern is not automatically a vulnerability.
5. Use local fork/testnet simulation only. Never send an exploit transaction to mainnet or alter third-party state.
6. Require a reproducible PoC with attacker capability, preconditions, measurable impact, and exact evidence. Falsify or downgrade theoretical candidates before reporting.
7. Draft a private report only after confirming the finding is in scope, novel, and mapped to an accepted impact. Do not publish details before triage.

For the first-pass study workflow, use `references/immunefi-bug-bounty-workflow.md` for the report checklist and target-selection notes.

## AMM NFT inventory verification

For questions about NFT AMM utilization versus minted/sold/dev-held supply, use `references/amm-nft-inventory-verification.md`. Resolve collection and AMM separately, query `totalSupply()`, `ownerOf()`, and AMM `inventoryLength()` on the official RPC, then classify outside-inventory holders without assuming they are sold or dev-owned.

## Tools needed
- `cast` (foundry, system-wide at `/usr/local/bin/cast`) — audited clean, no backdoor
- Live RPC URL for the chain
- Optional: `python3` for JSON parsing of `cast` output
- Optional but usually already present: `requests` + `pycryptodome` (compute any event topic or
  4-byte selector with `keccak`; used by `scripts/chain_topic_census.py` and
  `scripts/l1_suite_audit.py`). Never hardcode a topic0 from memory — compute it.
