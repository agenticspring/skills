---
name: osnm-z-mint
description: Use OSNM-Z for gated OpenSea SeaDrop mint preparation.
version: 1.0.0
author: spring
license: Private
platforms: [linux]
metadata:
  hermes:
    tags: [nft, mint, opensea, osnm-z, seадrop, wallet-safety]
    related_skills: [evm-mint-preflight, opensea-nft-operations, transactional-trade-safety, secure-tool-install]
---

# OSNM-Z Mint

## When to Use

Use when the user asks to install, configure, validate, or run OSNM-Z (`zunmax/osnm-z`) for an OpenSea-hosted SeaDrop mint.

Use this skill whenever a mint request names `osnm-z`, `opensea-mint`, or the Hermes spring wallet source.

## Installed boundary

- Command: `/usr/local/bin/osnm-z` (preferred)
- Compatibility command: `/usr/local/bin/opensea-mint` or `/usr/local/bin/opensea-mint-spring`
- Installed source audit: `/opt/osnm-z-audit`
- Audited commit: `a078b67545f12d8b201fea955f596042b06a13c5`
- Installed binary SHA-256: `41523bd49bdf5aeeca918563d5c8e4e39837bdaa5e8a3896d2a1f6f9ce6e7472`
- Locked Rust test/build evidence: `cargo test --locked` 124 passed; release build passed.

If the binary is replaced or the upstream commit changes, re-run source audit, locked test/build, binary hash, `--version`/`--help` syscall smoke, and secret scan before use.

## Wallet source

The configured wallet source is exactly:

```text
/root/.hermes/.credintial/.springwallet
```

It contains mnemonic sets. Never print, copy, persist, upload, or place the file contents in a repository, note, `.env`, log, worker payload, or chat. It must remain mode `600`.

The `osnm-z` wrapper:

- Set selection is supported with `SPRING_OSNM_WALLET_SET=1` (1-based valid mnemonic set index). With `SPRING_OSNM_WALLET_SET=1`, only Set 1 is derived into the ephemeral manifest; without it, all valid sets are selected.

1. reads mnemonic sets at invocation;
2. derives private keys through `cast` into a `0700` ephemeral directory, preferably `/dev/shm`;
3. writes a `0600` private-key manifest only for that process;
4. runs OSNM-Z self-funded mode;
5. removes the manifest and temp directory in `finally`.

Do not point raw OSNM-Z at the mnemonic source. Do not create a persistent `wallets.json` from it. Do not use `wallets create` for these wallets.

## Required workflow

1. Confirm exact target: OpenSea slug/URL, collection contract if known, token standard, intended chain, wallet scope, quantity, and budget.
2. Require `SPRING_OSNM_RPC_URL` (preferred) or `RPC_URL`. If omitted, set `SPRING_OSNM_CHAIN` and the wrapper resolves an Alchemy HTTPS endpoint from the Hermes `ALCHEMY_API_KEY`, `ALCHEMY_API_KEY_2`, or `ALCHEMY_API_KEY_3` values. It must be HTTPS; only loopback HTTP is allowed for local test RPC. Never invent a chain or RPC.
3. Run validation only:

```bash
SPRING_OSNM_VALIDATE_ONLY=1 SPRING_OSNM_RPC_URL=<verified-rpc> osnm-z doctor
```

The success result only proves mnemonic parsing and ephemeral manifest creation. It does not prove eligibility, balance, calldata, simulation, or mint success.

4. Run read-only calldata acquisition:

```bash
SPRING_OSNM_RPC_URL=<verified-rpc> osnm-z calldata --collection <slug-or-url>
```

The wrapper owns the wallet input. Treat OpenSea private GraphQL/session data as acquisition-only, not settlement authority.

5. Apply canonical preflight from `evm-mint-preflight`: collection/contract/chain identity, `eth_chainId`, deployed bytecode/code hash, SeaDrop stage, wallet-specific eligibility, exact `eth_call`, `eth_estimateGas`, gas ceiling, balance after reserve, and deterministic plan hash.
6. `mint` is a write-capable command. Ask for explicit final confirmation immediately before it. Show chain, contract, wallet count, quantities, max mint value, gas ceiling, recipient, and self-funded mode.
7. After any broadcast, persist/capture real TxHash, wait for receipt, verify Transfer events and owner/balance post-state, and report `confirmed` only with all evidence. Timeout/possible-send becomes reconciliation-only; never rederive and re-sign automatically.

## Live mint workflow

Use this exact sequence for a single-wallet test mint after the user names the target and explicitly asks to mint:

1. Resolve the target from both the supplied OpenSea URL/slug and contract address when available. Query the official OpenSea drop metadata through the `terminal` tool; verify `contract_address`, `chain`, `drop_type`, `is_minting`, `active_stage`, `price`, and `max_per_wallet`. Never trust the slug alone.
2. Lock the execution scope to one wallet and one quantity:

```bash
SPRING_OSNM_CHAIN=robinhood
SPRING_OSNM_WALLET_SET=1
SPRING_OSNM_QUANTITY=1
SPRING_OSNM_RECIPIENT_ADDRESS=<same-set-1-address>
```

3. Run the read-only gate through the `terminal` tool:

```bash
SPRING_OSNM_VALIDATE_ONLY=1 SPRING_OSNM_CHAIN=robinhood SPRING_OSNM_WALLET_SET=1 osnm-z doctor
SPRING_OSNM_CHAIN=robinhood SPRING_OSNM_WALLET_SET=1 SPRING_OSNM_RECIPIENT_ADDRESS=<set-1-address> SPRING_OSNM_QUANTITY=1 osnm-z calldata --collection <contract-or-slug> --token-id 0
```

4. Require the calldata result to show the intended chain, exactly one active stage, wallet authentication/eligibility, target/data/value, and `value=0` for a freemint. If OpenSea reports `insufficient wallet funds`, inspect the authoritative drop `price` before retrying; a supposedly free page may have a paid active stage or still require gas reserve.
5. Run `mint` only after the user explicitly says to send/broadcast/mint now. The command is interactive; answer only the expected final confirmation and keep the scope at Set 1/quantity 1. Never silently increase quantity or include all 50 sets.
6. Capture the full transaction hash from the command output, then use the `terminal` tool/RPC to verify receipt status, block, sender, destination, gas, value, and Transfer logs. Keep the hash as `0x` plus exactly 64 hexadecimal characters.
7. Decode the minted token ID from the `Transfer` log and re-read `ownerOf(tokenId)` plus `balanceOf(set1)` directly through RPC. Report `confirmed` only when receipt status is 1 and post-state matches.
8. Validate an explorer URL only after RPC verification. Use the full hash, test the exact URL through the `terminal` tool, and discard any host that returns DNS failure, 404, or malformed-hash errors. Explorer UI is presentation only; RPC receipt/log/state remains authoritative.

## Live mint pitfalls

- A collection URL can resolve to a different or stale collection than the contract address. Bind both before minting.
- “Freemint” can still fail from insufficient native gas, or the active drop stage can have a nonzero price. Read the drop metadata and exact calldata value.
- `calldata inspection requires exactly one active stage` is a fail-closed stage ambiguity, not a reason to guess a phase or selector.
- `OpenSea reported insufficient wallet funds` is not proof that the wallet has zero balance; compare exact wei balance against the active stage price plus gas reserve.
- Do not copy a shortened or manually typed TxHash into an explorer URL. Validate the 64-hex invariant first; one missing character produces a misleading explorer error.
- An explorer can be down or behind the chain. Never downgrade a confirmed RPC receipt because an explorer page fails.
- On timeout or possible-send, reconcile the nonce/hash/receipt before retrying. Never automatically rederive and re-sign.

## Short-window FCFS free mints

Free-mint drops with a public stage can sell out in minutes. Do not run a
single slow preflight loop and wait manually — the stage times on OpenSea
drops shift (extensions get pushed, e.g. a 15:15Z presale that keeps being
moved to 16:00Z, then 16:18Z, then 18:15Z) and supply can go from 1.2k to
5,555/5,555 (sold out) before the public stage ever opens.

Rules learned from the Feline Brokers miss:

1. Check the **drops endpoint**, not the collection endpoint, for contract +
   stage data:
   `GET https://api.opensea.io/api/v2/drops/<slug>` with `x-api-key`.
   The collection endpoint often returns `contract_address: null`.
2. Read `active_stage.stage_type`, `price`, `end_time`, `max_per_wallet`,
   `total_supply`, `max_supply`, `is_minting`. A `signed_presale`/partner
   stage means Set 1 is not eligible without the partner collection.
3. The active stage reported by OpenSea is the authority; `end_time` moves.
   Never assume a stage opens at the time you first read — re-read at target
   time and expect extension.
4. If OSNM-Z calldata returns `no wallet remains eligible and valid for the
   selected stage`, that is an eligibility gate, not a wallet/balance error.
5. If `is_minting: false` or `total_supply >= max_supply`, the drop is done —
   stop, do not retry.
6. For a target stage, run `scripts/watch-drop-stage.py` in the background
   (through the `terminal` tool) with a tight `--interval` (5-10s) and a
   `--timeout` covering the expected open time. It exits 0 exactly when the
   target stage is live, 1 on sold-out, 3 on timeout. Fire `osnm-z calldata`
   + the mint immediately on exit 0; there is no time for a second full
   preflight.
7. With short windows, pre-authenticate and have the exact calldata prepared
   before the stage opens when possible; a full doctor -> calldata -> simulate
   -> confirm cycle will miss the window.

## Hard corrections

- No RPC/chain: stop with missing configuration. Do not default to Ethereum or an unconfigured public RPC. Supported Alchemy aliases currently include Ethereum, Polygon, Arbitrum, Optimism, Base, zkSync, Linea, Scroll, Blast, Polygon zkEVM, Shape, Frax, Zora, World Chain, Unichain, Ink, and Robinhood Chain; the wrapper maps the alias to its Alchemy mainnet slug and selects one of the configured Hermes Alchemy projects without exposing the key.
- Bad mnemonic file, unsupported word count, wrong permissions, or derivation failure: stop. Do not generate replacement wallets.
- OpenSea HTTP 401/403, GraphQL drift, stale/ambiguous stage, chain mismatch, target/data/value mismatch, insufficient balance, invalid calldata, or executor mismatch: fail closed.
- Keep sponsored/EIP-7702 disabled. Do not use `SPONSORED=true`, `SPONSOR_KEY`, `deploy-executor`, `--fund`, `--withdraw`, or `--undelegate` without a separately scoped user request and fresh on-chain preflight.
- Never call doctor, calldata, local validation, or a prepared plan `minted`, `broadcast`, or `confirmed`.
- Never put mnemonic/private key/signature/raw transaction in output.

## Reporting vocabulary

- `validated`: source and ephemeral manifest passed local checks;
- `verified`: chain/contract/bytecode/eligibility evidence passed;
- `simulated`: exact call and gas estimate passed, no signature exists;
- `signed`: signer produced a signature;
- `broadcast`: TxHash accepted;
- `confirmed`: successful receipt plus Transfer and owner/balance post-state;
- `unknown_needs_reconciliation`: a send may have reached the network.

## Verification commands

```bash
command -v osnm-z
osnm-z --version
SPRING_OSNM_VALIDATE_ONLY=1 SPRING_OSNM_RPC_URL=<verified-rpc> osnm-z doctor
stat -c '%a %n' /root/.hermes/.credintial/.springwallet
```

No transaction is allowed from this skill without explicit user confirmation at the final pre-broadcast boundary.
