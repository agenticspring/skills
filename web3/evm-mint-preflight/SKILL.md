---
name: evm-mint-preflight
description: Use for EVM mint preflight and simulation.
version: 1.0.0
author: spring
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [evm, nft, mint, allowlist, merkle, eip712, simulation, burner-wallet]
    related_skills: [transactional-trade-safety, opensea-nft-operations, web3-rpc-contract-audit]
---

# EVM Mint Preflight

Use this class skill for primary NFT mint preparation across EVM chains: collection/contract verification, public/whitelist preflight, Merkle proofs, EIP-712 vouchers, OpenSea Drop preparation, gas/balance checks, and simulation-only transaction planning.

## When to Use

Use when preparing an EVM NFT mint or allowlist artifact before signing: verify a collection/contract, validate a Merkle proof or EIP-712 voucher, simulate exact calldata, estimate gas, or test fail-closed behavior with an unfunded burner wallet.

## Non-negotiable safety boundary

- Default mode is read-only and simulation-only.
- Do not sign, broadcast, fund, or submit a transaction in preflight.
- For smoke and integration checks, use an ephemeral burner wallet with zero native balance. Keep it in memory only; never print, persist, import into the production signer vault, or send it funds.
- A zero-balance burner failing at the balance-reserve gate is a successful fail-closed test result.
- Never call a signer adapter or broadcast adapter from this skill's test fixtures.
- OpenSea/indexer data is discovery and preparation input. RPC chain ID, bytecode, `eth_call`, gas estimation, receipts, and post-state are authority.

## Preflight sequence

1. Validate the OpenSea slug, requested chain, and requested contract agree. Similar slugs are not identity proof. If using the OSNM-Z Alchemy resolver, map the explicit chain alias to the documented Alchemy network slug before connecting.
2. Read `eth_chainId` and compare to the expected chain ID.
3. Read `eth_getCode`; reject empty bytecode. Record code hash and byte length. If a proxy is involved, resolve and bind the implementation/code hash before arming.
4. Validate token standard, mint function/calldata, phase, price, payment token, quantity limit, supply, pause state, deadline, recipient, and wallet-specific mint count where available.
5. Resolve allowlist artifacts using the contract's actual leaf formula. Never assume all Merkle projects use the same encoding or sorted-pair rule.
6. Bind proof/voucher cache keys to `chain + contract + stage + wallet + root/version + quantity`. A proof or voucher for wallet A must never be reused for wallet B.
7. For EIP-712 vouchers, validate domain, verifying contract, chain ID, recipient, quantity, price, nonce, expected signer, and expiry.
8. Run exact `eth_call` with the exact `from`, `to`, calldata, and value.
9. Run `eth_estimateGas`; enforce configured gas ceiling and compute `value + gasLimit * gasPrice` against spendable balance after reserve.
10. Produce a deterministic sanitized plan hash. The result must explicitly say `signed=false` and `broadcast=false`.

## JSON-RPC pitfall

For Geth-compatible endpoints, encode zero transaction value as `0x0`, not `0x00`. Some clients reject leading-zero hex quantities with errors such as `cannot unmarshal hex number with leading zero digits`.

## Status vocabulary

- `verified`: chain, address, and deployed bytecode evidence passed.
- `preflight_valid`: collection, phase, allowlist, policy, and balance gates passed locally.
- `simulated`: exact call and gas estimate passed; no signature exists.
- `failed_preflight`: simulation, gas, policy, allowlist, or balance gate failed.
- `signed`: a signer returned a signature; this is outside preflight.
- `broadcast`: a transaction hash was accepted; this is outside preflight.
- Never call a simulation “minted”, “broadcast”, or “successful mint”.

## TDD and verification

Write the failing test before implementation and verify the failure is caused by missing behavior. Then implement the smallest vertical slice, rerun the focused test, and run the full repository gate.

Minimum tests:

- wrong chain ID rejected;
- empty bytecode rejected;
- code-hash mismatch rejected;
- collection slug/chain/contract mismatch rejected;
- Merkle root/proof mismatch rejected;
- voucher recipient/signer/expiry mismatch rejected;
- proof cache is wallet-specific;
- simulation revert rejected;
- gas ceiling rejected;
- zero-balance burner fails at balance reserve;
- deterministic plan hash is stable;
- result is always `signed=false`, `broadcast=false`.

## Unified campaign and adapter boundary

For multi-route mint support, do not let each adapter implement its own simulation or execution policy. Every route must produce a typed `PreparedMintCall` with an explicit adapter kind, target, calldata, value, quantity, artifact hash, and optional expiry. A single campaign finalizer then enforces:

1. adapter kind matches campaign kind;
2. wallet identity and wallet ID are bound to the artifact;
3. campaign window, stage, quantity, value, target, and gas ceilings are valid;
4. chain ID, deployed bytecode, and expected code hashes match;
5. exact `eth_call`, `eth_estimateGas`, gas-price, native-balance, and block evidence pass;
6. deterministic campaign/artifact/plan hashes are produced;
7. replay reservation succeeds atomically before the plan is accepted.

Campaign/stage/root-or-artifact-version/code-hash changes invalidate an existing plan. Keep replay reservation durable across restarts and workers; a duplicate artifact must fail closed rather than silently rebuild a new plan.

### OpenSea Drop acquisition

Use the official routes, but keep them as acquisition-only boundaries:

```text
GET  /api/v2/drops/{slug}/eligibility  # wallet-scoped session/JWT
POST /api/v2/drops/{slug}/mint         # API key; body: minter + quantity
→ validate returned to/data/value/chain
→ run the same on-chain finalizer
→ signed=false, broadcast=false
```

An API key is application authentication, not wallet identity. Eligibility must use the matching wallet-scoped session. Never expose the JWT/session, proof, voucher signature, or calldata in a Telegram preview or ordinary logs. If the live API returns 401/403, report the unverified live state and do not fall back to an unverified endpoint or claim discovery succeeded.

See `references/mint-campaign-adapters.md` for the normalized adapter contract, replay key rules, OpenSea route details, and validated error/reporting vocabulary.

## OpenSea eligibility reference audit

A standalone eligibility checker can be useful as a read-only reconnaissance source, but its results are not mint authority. Normalize its stage labels and on-chain observations into the campaign model, then rerun the canonical finalizer: wallet binding, chain/code-hash checks, exact calldata, `eth_call`, gas, balance reserve, and replay reservation. Never copy a raw-private-key CLI, hardcoded RPC/selector, stale persisted GraphQL hash, or raw session flow into the bot.

Use `references/opensea-eligibility-checker-audit.md` for the reviewed reference patterns, official route details, and known GraphQL/API quirks.

## OSNM-Z integration (audited local mint CLI)

When the user asks to use OSNM-Z (`zunmax/osnm-z`) for OpenSea-hosted SeaDrop mints, use the audited wrapper installed as `osnm-z`/`opensea-mint-spring`, not the raw binary directly.

### Credential boundary

- The configured source is the Hermes credential file `${HERMES_HOME:-~/.hermes}/.credintial/.springwallet` (override with `SPRING_WALLET_FILE`).
- The source contains mnemonic sets. Treat it as signer material: require mode `600`, never print/read it into chat, never put it in `.env`, a repo, logs, Obsidian, or a persistent OSNM-Z `wallets.json`.
- The wrapper derives private keys only in a `0700` temporary directory (prefer `/dev/shm`), writes an ephemeral `0600` manifest, invokes OSNM-Z, and removes the directory in `finally`. If cleanup or source permissions fail, stop.
- OSNM-Z itself expects `WALLET_KEY` or a private-key `WALLETS_FILE`; do not point it at the mnemonic source directly and do not manually convert the file into a persistent manifest.
- The wrapper never enables sponsored mode and strips conflicting `WALLET_KEY`, `WALLETS_FILE`, `SPONSOR_KEY`, `PRIVATE_KEY`, `MNEMONIC`, and `SEED_PHRASE` variables from the child environment.

### Required invocation gate

1. Set `SPRING_OSNM_RPC_URL` (or `RPC_URL`) to an HTTPS RPC for the intended chain. Loopback HTTP is allowed only for local tests. Missing/HTTP-public RPC fails closed.
2. Run `SPRING_OSNM_VALIDATE_ONLY=1 osnm-z doctor` first. A successful validation proves only that the mnemonic sets were parsed and an ephemeral manifest was built; it is not an eligibility, balance, simulation, or mint proof.
3. For read-only acquisition use `osnm-z calldata --collection <slug-or-url> --wallets <ignored-by-wrapper>`; the wrapper replaces the wallet path and the returned action must still pass chain/target/data/value validation.
4. Before any `mint`, run the canonical preflight: collection/contract/chain identity, `eth_chainId`, bytecode/code hash, live SeaDrop stage, wallet-specific eligibility, exact `eth_call`, gas estimate, fee ceiling, native balance after reserve, and deterministic plan hash.
5. `mint` is a broadcast-capable command. Never invoke it from a generic read-only question. It requires explicit user confirmation at the final boundary showing chain, contract, wallet count, per-wallet quantity, maximum value/gas, recipient, and whether OSNM-Z self-funded or sponsored mode is selected. Default wrapper mode is self-funded; sponsored/EIP-7702 remains disabled unless a separate audited configuration and user instruction explicitly enable it.
6. After broadcast, capture the real TxHash, receipt, Transfer events, owner/balance post-state, and per-wallet result. Possible-send/timeout states become reconciliation-only; never auto-retry by re-deriving or re-signing.

### OSNM-Z correction rules

- If `RPC_URL` is missing, do not invent a chain/RPC or run `mint`; report the exact missing configuration.
- If the mnemonic file cannot be parsed, has wrong permissions, has an unsupported word count, or derivation produces no keys, stop; do not create replacement wallets.
- If OpenSea returns 401/403/private GraphQL drift, do not bypass with undocumented endpoints or reuse another wallet session. Report `unknown`/`failed_preflight`.
- If OSNM-Z reports multiple active stages, stale calldata, stage drift, recipient mismatch, chain mismatch, invalid selector/target, insufficient balance, or executor/runtime mismatch, reject the plan.
- Never use `wallets create`, `--fund`, `--withdraw`, `--undelegate`, `deploy-executor`, `SPONSORED=true`, `SPONSOR_KEY`, or a persistent manifest unless the user explicitly scopes that separate write operation and the same on-chain preflight passes.
- Never call a successful `doctor`, `calldata`, or local wrapper validation `minted`, `broadcast`, or `confirmed`.

### Installed-tool evidence

The audited source is pinned to the upstream commit used during installation. Keep the installed binary hash in the local audit log; if the binary is replaced, re-run source audit, `cargo test --locked`, `cargo build --release --locked`, version/help runtime checks, and the secret/runtime syscall audit before promotion.

## Related references

See `references/mint-preflight-and-burner-fixtures.md` for tested burner-wallet fixture rules, exact gate order, the zero-value RPC pitfall, and reporting vocabulary.

See `references/api-puzzle-gated-mint.md` for the backend-puzzle mint flow (Alien Node pattern): puzzle → solve → local sign → submit, with balance gate, ethers fallback, and on-chain verification rules.

See `references/os-elig-cli.md` for the installed `os-elig` CLI (OpenSea SIWE/GraphQL + Scatter onchain eligibility checks across wallet sets).

## Custom (non-SeaDrop) contract free-mint verification

When the target is a custom mint site with no OpenSea drop record (drops
endpoint empty/404) — game sites, project dashboards, `stonkswar.com`,
`niulai.cx` — verify free-ness at the CONTRACT level, never from page copy or
the site's own API:

1. Pull the ABI: sites usually expose `/abi/<Contract>.json` (foundry
   artifact) or the contract is verified on Blockscout. Grep the JS bundle
   first for `0x` addresses and `function X() view` ABI strings.
2. Read ABI surface for free-mint signals:
   - `FREE_PER_WALLET()`, `freeMintsRemaining(address)`, `mintCost(address,uint256)` — genuine per-wallet free allowance.
   - `TEAM_FREE_MINT()` + `teamFreeMinted()` — a free allocation FOR THE TEAM, not public. If `teamFreeMinted == TEAM_FREE_MINT` the team quota is spent; its existence is NOT a public free mint (NiuFactory: 10/10 spent).
   - `mintPrice()`/`MINT_PRICE()` non-zero ⇒ paid regardless of "free" copy.
3. Read on-chain state with `eth_call` (4-byte selectors from `keccak(text=...)`): `mintOpen()`, `mintPhase()`, `totalSupply()`, `MAX_SUPPLY()`, plus wallet reads `mintedBy(wallet)`, `freeMintsRemaining(wallet)`, `mintCost(wallet,1)`.
4. **Sold-out beats free**: if `totalSupply() == MAX_SUPPLY()`, `mint()` reverts even when `freeMintsRemaining(wallet) > 0` and even when the site API reports `mintOpen:true` (Stonks War: `/api/mint-status` said open, chain said 10,000/10,000 owned). On-chain `totalSupply` is authority; site APIs can be stale mirrors of phase.
5. Probe `ownerOf()` for the LAST few token IDs. One wallet owning the tail range (e.g. 9990-10000) = whale/bot sweep; the free/cheap window closed.
6. Website-gated EIP-712 mints (`mint(qty, nonce, deadline, sig)` with `trustedSigner`, signature issued by `/api/mint-auth`) cannot be broadcast directly — the site flow owns the signature. `mintCost==0` still means free, but without the signature there is no valid broadcast path.
7. Broadcast only when `mintCost(wallet,1)==0` AND `totalSupply < MAX_SUPPLY` AND a valid signature path (or direct-callable contract) exists.

### Identify NFT vs ERC-20 before reading state (labels lie)

When the site config lists multiple `0x` addresses (`token`, `exchange`, `art`,
`robies`, ...), NEVER trust the key names to tell which contract is the NFT.
Robies And Co. mapped `robies` → NFT collection and `token` → $ROBIE ERC-20 —
the exact opposite of what the names suggest. Prove type on-chain:

- **ERC-721 (NFT)**: `ownerOf(1)` returns an address (selector `0x6352211e`),
  `maxSupply()` (`0xd5abeb01`) returns a small integer, no `decimals()`.
- **ERC-20 (token)**: `decimals()` (`0x313ce567`) returns `18`; `totalSupply()`
  magnitude carries 18 decimals (e.g. 999,452,320 × 10^18).
- Read `name()`/`symbol()` too — but note they can return empty/revert on
  custom contracts, so ownerOf/decimals is the authoritative probe.

### Auction houses are not free mints

If the site copy says "one at a time" / "mint button in the Bidding Box" and
the ABI has a payable `bid()`, the collection is auction-gated (Doodads:
`reservePrice` 0.0006 ETH, `minimumNextBid` 0.0094 ETH, clock arrival 780s →
first close 30s → extension 15s → hard close 75s). Views to check:
`reservePrice()`, `minimumNextBid()`, `currentAuction()`. Nonzero reserve/next
bid = paid bidding path only; there is no free mint. Skip unless the operator
explicitly wants to bid.

See `references/custom-contract-free-mint-verification.md` for the worked
Stonks War / NiuFactory checks with exact selectors and RPC reads.
