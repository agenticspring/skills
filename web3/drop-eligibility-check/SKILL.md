---
name: drop-eligibility-check
description: Check OpenSea and Scatter drop eligibility per wallet.
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [OpenSea, Scatter, Eligibility, SIWE, GraphQL, MultiWallet]
    related_skills: [osnm-z-mint, opensea-nft-operations, evm-mint-preflight]
---

# Drop Eligibility Check

Read-only per-wallet eligibility checks for NFT drops before minting. Covers
the installed `os-elig` CLI (OpenSea SIWE + GraphQL path and Scatter on-chain
path) and the manual fallback. Never signs or broadcasts anything; this is a
recon/preparation layer only.

## When to Use

- "Cek elig wallet mana" / "eligible di phrase/set mana" for a drop URL or slug.
- Decide whether a wallet set qualifies for a signed/whitelist stage.
- Pre-mint recon: identify which of the Hermes wallet sets (Set 1..100) can
  mint, at which stage, and at what price.
- Scatter.art collections (`scatter.art/c/<slug>`) where eligibility is
  on-chain list membership.

## Prerequisites

- Installed CLI: `/usr/local/bin/os-elig` (project at `/root/projects/os-elig-bot/`).
- `OPENSEA_API_KEY` in `/root/NFT-OPENSEA/opensea.env` (auto-loaded by the CLI).
- Wallet mnemonics at `/root/.hermes/.credintial/.springwallet` (Set 1..100);
  keys are derived in memory only.
- Python venv already provisioned: `/root/projects/os-elig-bot/.venv`.

## How to Run

Invoke through the `terminal` tool:

```bash
os-elig <opensea-slug-or-url>                # Set 1 default
os-elig <slug> 1-100                         # range of wallet sets
os-elig <slug> all                           # all 100 sets
os-elig <slug> 1-10 --json                   # JSON output
os-elig https://www.scatter.art/c/<slug> 1   # Scatter path (RH onchain, no SIWE)
```

For a slug-only string, `os-elig` treats it as an OpenSea slug; pass a full
`scatter.art/c/...` URL to select the Scatter path.

## Quick Reference

| Path | Auth | Source |
|---|---|---|
| OpenSea | SIWE login per wallet | GraphQL `DropEligibilityQuery` persisted hash `d893f026d731e8f14986921fa4229098e018289f6cc7683f8ee2dd83749dd95d` at `gql.opensea.io/graphql` |
| Scatter | none (public on-chain) | trpc `collection.getCollection` + RH RPC `invites(bytes32)`/`minted`/`balanceOf` |
| OpenSea REST drop stages | `x-api-key: $OPENSEA_API_KEY` | `GET /api/v2/drops/{slug}` |
| Claim-site whitelist verify | none (public POST) | site `/api/claim` re-submission semantics |
| SeaDrop on-chain (RH) | none | `cast call` on canonical SeaDrop + NFT contract |

Output labels: `ELIG` = signed/whitelist stage eligible; `PUB` = public stage
only; `NO` = none. SIWE sessions are cached 45 minutes (repeat checks skip
re-login).

## Stage Recon (fast, no SIWE)

Before any per-wallet check, pull the full drop stage table with the REST API
(invoke through the `terminal` tool):

```bash
source /root/NFT-OPENSEA/opensea.env
curl -s "https://api.opensea.io/api/v2/drops/<slug>" \
  -H "x-api-key: $OPENSEA_API_KEY" --max-time 15
```

`stages[]` gives per stage: `stage_type` (`public_sale`/`signed_presale`),
`label` (e.g. `GTD`, `WL`, `Team`), `price` (wei), `start_time`/`end_time`
(ISO UTC), `max_per_wallet`, `allowlist_wallet_count`. `active_stage` is null
until mint opens. This alone answers "which stage is our whitelist in and
when" without any wallet auth.

## Claim-Site Whitelist Verification

For drops that whitelist via a website claim endpoint (e.g.
`POST https://<site>/api/claim` with `{"wallet":"0x...","route":"quests",...}`)
and explicitly never ask for a wallet connection, verify membership by
re-submitting the SAME wallet with the SAME answers:

- `{"ok":true,"updated":true}` — wallet **already in their DB** (confirmed
  from a previous submission). `updated:true` is the positive proof.
- `{"ok":true,"updated":false}` — first-time entry created.
- `"too many tries, take a short break"` — **IP rate limit, not rejection**.
  Back off (cooldown escalates 240s→300s→600s→900s→1800s; add 7–40s jitter
  per request) and continue; verified wallets keep returning `updated:true`.
- `{"ok":false,"error":"closed",...}` — submission path locked before mint
  (they froze the list). At this point you CANNOT distinguish in-DB from
  not-in-DB; verify BEFORE the path closes, or rely on earlier runs.

## SeaDrop On-Chain Eligibility (Robinhood Chain)

When the drop is an ERC721SeaDrop on RH, the contract answers directly
(canonical SeaDrop `0x00005EA00Ac477B1030CE78506496e8C2dE24bf5`):

```bash
# full public drop config: price, start, end, maxPerWallet, feeBps, restrictFeeRecipients
cast call $SD 'getPublicDrop(address)(uint80,uint48,uint48,uint16,uint16,bool)' $NFT --rpc-url $RPC
# per-wallet mint stats (on the NFT contract): minted, maxByWallet, maxSupply
cast call $NFT 'getMintStats(address)(uint64,uint64,uint64)' $WALLET --rpc-url $RPC
# signed-presale signer params: all zeros = not configured yet
cast call $SD 'getSignedMintValidationParams(address,address)(uint80,uint24,uint40,uint40,uint40,uint16,uint16)' $NFT $SIGNER --rpc-url $RPC
# getAllowList(address) reverts when no merkle root is set — empty path, not an error
```

`signed_presale` stages (GTD/WL) are only answerable once the creator sets
signed validation params or a merkle root, usually right before the stage
opens. Until then eligibility is not on-chain — re-check at stage open time.

## OpenSea GraphQL Eligibility Query

With a working SIWE session the persisted query is:

```graphql
query GetDropEligibility($collectionSlug: String!) {
  dropBySlug(slug: $collectionSlug) {
    stages {
      stageIndex stageType isEligible eligibleMinterAddress
      eligibleMaxTotalMintableByWallet maxTotalMintableByWallet
      eligiblePrice { token { unit contractAddress } native { symbol unit } }
    }
  }
}
```

`isEligible` stays null unless OpenSea knows the **active address**. The fix
that makes headless SIWE fully work: after `siwe/verify`, ALSO set the cookie
`connected-account-server-hint` to the checksummed wallet address on the
`opensea.io` domain. That single cookie makes `dropBySlug` return real
`isEligible` booleans per stage (proven on Onchain Sketches, 100/100 wallets).
If you still see `"Active address was not provided"`, you missed this cookie —
do not treat null as "not eligible".

## Auto-Mint Handoff (watch-and-fire)

**Headless auto-mint WORKS for ALL stages (public AND signed_presale WL/GTD) via
the OpenSea backend mint endpoint** — do NOT conclude a signed stage is
unmintable because you lack the creator's signer key. OpenSea's backend signs
the voucher server-side when you call it with a wallet SIWE session.

Working flow (proven on Onchain Sketches, 2026-08-30):

1. SIWE-login the wallet (`siwe_login`) — this yields the `access_token` +
   `refresh_token` cookies.
2. Set the `connected-account-server-hint` cookie to the checksummed address
   (same fix as the GraphQL eligibility path).
3. `POST https://api.opensea.io/api/v2/drops/{slug}/mint` with body
   `{"minter": "<wallet>", "quantity": N}` and header `X-API-KEY: $OPENSEA_API_KEY`.
   OpenSea returns `{to, data, value, chain}` — a ready-to-broadcast calldata
   with the voucher already signed by their backend.
4. Broadcast: `cast send <to> --data <data> --value <value> --private-key <pk>
   --rpc-url <rpc> --gas-limit 300000`.
5. Repeat per wallet — SIWE logins are independent, so run them PARALLEL
   (`ThreadPoolExecutor`, 4-5 workers): 10 wallets ≈ 30 s instead of 3 min.

**Mint endpoint error semantics** (parse these, they are the scheduler state):

| HTTP | Body | Meaning |
|---|---|---|
| 200 | `{to,data,value,chain}` | drop active, tx built — broadcast now |
| 401 | `Missing an API Key...` | add `X-API-KEY` header |
| 409 | `Drop is not currently active for minting` | not open yet — keep polling |
| 422 | `Drop is fully minted out` | supply exhausted — stop, no point retrying |
| 400 | `...` | bad wallet/quantity — fix input |

**Watch-mode probe must be stage-specific.** `GET /api/v2/drops/{slug}`
returns `active_stage` — but a multi-stage drop opens GTD before WL, and if the
scheduler fires on the FIRST active stage it mints at the wrong stage and
fails. Check the requested stage window by epoch FIRST
(`WL_START <= now <= WL_END`), and only fall back to `active_stage.label`
when it matches the requested stage family (`wl`/`whitelist` vs `public`).
Probe with the cheap REST endpoint (no SIWE needed) every 10 s; SIWE only at
fire time.

**Supply math before arming**: if `allowlist_wallet_count` (from the stage
table) is far above `maxSupply`, the drop is oversubscribed and will sell out
in seconds at open — a 10 s poll interval WILL miss it. Either poll at 1-2 s,
or arm at `stage_start - small offset`, or accept that high-demand drops
require an off-chain pre-signed voucher ahead of time.

**Timezone trap when computing epochs**: server local time may be WIB (UTC+7),
so `datetime(2026,8,30,15,15).timestamp()` silently returns UTC+7-naive epochs
(off by 7 h). Build stage epochs with explicit `tzinfo=datetime.timezone.utc`,
and verify against OpenSea API times before arming.

When building an auto-mint scheduler for a drop:

1. Read the real stage windows from OpenSea API v2 `GET /api/v2/drops/{slug}` —
   do NOT trust hardcoded epochs; creators shift times.
2. Poll the cheap REST probe every 10 s; fire when the REQUESTED stage window
   is open (epoch check first, API label as fallback).
3. At fire time re-check per-wallet eligibility (wallets can lose eligibility
   between arming and opening).
4. Parallel SIWE + backend-mint per wallet; 1-2 s spacing on broadcast; retry
   broadcast once after 2 s on transient errors; skip fired wallets on retry.

## Batch Eligibility Check (mnemonic sets → PK → SIWE per wallet)

For the Hermes wallet sets, derive PK from the mnemonic file and SIWE-login per
wallet (each wallet is its own OpenSea account). Full working script:
`scripts/batch_ocs_elig.py` (invoke through the `terminal` tool). Core flow:

1. Parse `/root/.hermes/.credintial/.springwallet` (`Set N` header + mnemonic).
2. Derive account: `eth_account.Account.from_mnemonic(m)` — requires
   `Account.enable_unaudited_hdwallet_features()` first.
3. Verify derived address == expected address from the manifest before SIWE.
4. `siwe_login(addr, pk)` → `client.cookies.set("connected-account-server-hint",
   checksummed, domain="opensea.io")` → GraphQL persisted query
   `d893f026d731e8f14986921fa4229098e018289f6cc7683f8ee2dd83749dd95d` with
   variables `{"address": wallet, "collectionSlug": slug}`.
5. `time.sleep(3)` between wallets (GraphQL 429s if faster).
6. Save structured JSON to disk; print per-wallet stage booleans.

Runtime ≈ 15 s/wallet (SIWE nonce→verify round trip dominates) → ~25 min for
100 wallets. Run in background with `terminal(background=true)`.

## Procedure

1. Resolve the drop: `os-elig <target>` with the target from the user (slug,
   OpenSea URL, or Scatter URL).
2. Read the header output: collection, contract address, stage list, price,
   and `is_minting`/supply where shown.
3. Interpret per wallet:
   - `ELIG` labels = the wallet passed a signed/whitelist stage check.
   - `PUB` only = the wallet is not whitelisted but can mint in the public
     stage (usually open to all, often paid or free depending on stage).
   - `NO` = not eligible anywhere checked.
4. Verify the active stage price directly (OpenSea drop API
   `active_stage.price` or contract `PRICE()` selector) before any mint —
   "FREE MINT" in a stage label does not make it free, and signed presales are
   frequently the paid or restricted stage.
5. Report a table of eligible sets and which stage(s). For a follow-up mint,
   hand off to `osnm-z-mint` workflow with the exact stage, price, and wallet
   set.

## Pitfalls

- `signed_presale`/partner stages require proofs or partner-collection
  ownership; `PUB` on the same drop means only the public stage is open.
- A drop with no active stage yet returns `calldata inspection requires
  exactly one active stage` style errors or empty eligibility — re-check at
  the actual open time; OpenSea shifts stage end times.
- If `os-elig` is missing, reinstall from `/root/projects/os-elig-bot`
  (venv + symlink `/usr/local/bin/os-elig`), or fall back to manual
  `siwe_login` + `check_eligibility_graphql` from the module.
- Never paste private keys or mnemonic content into command lines; the CLI
  reads the wallet file itself.
- Scatter 404 = slug does not exist; `no stages` = collection exists but no
  on-chain list detected.
- RH public RPC `rpc.mainnet.chain.robinhood.com` can return stale `eth_getCode`
  (0x for a deployed contract); use Alchemy
  `https://robinhood-mainnet.g.alchemy.com/v2/$ALCHEMY_API_KEY` for read calls
  against RH contracts. Alchemy free tier caps `eth_getLogs` to 10-block
  ranges — scan logs in small windows, don't span thousands of blocks.
- `eth_account.Account.from_mnemonic` throws until you call
  `Account.enable_unaudited_hdwallet_features()` once.
- SIWE + GraphQL per-wallet ≈ 15 s each (nonce→verify dominates). For 100
  wallets run as a background `terminal` job; keep 3 s between GraphQL calls
  or you hit 429.
- If GraphQL returns `PersistedQueryNotFound`, the persisted hash
  `d893f026...` expired — refresh it from a browser network trace of the
  drop page (`DropEligibilityQuery` request body `sha256Hash`).

## Verification

```bash
os-elig <slug> 1
```

A healthy run prints one line per wallet with `ELIG`/`PUB`/`NO` plus
`DONE ok=N eligible=M err=0`.

## References

- `references/os-elig-verified-notes.md` — audited bot module summary, Mythborn
  verified case (stages/prices/results), Scatter path behavior, module function
  map for manual fallback, and rate-limit notes.
- `references/onchain-sketches-case.md` — worked claim-site + SeaDrop example
  with the `connected-account-server-hint` cookie fix and 100/100 `N/N/Y/Y`
  result.
- `scripts/batch_ocs_elig.py` — batch eligibility checker: derive PK from
  `.springwallet` mnemonics → SIWE per wallet → GraphQL → JSON results.
- `scripts/ocs_auto_mint.py` — watch-and-fire auto-mint scheduler (OpenSea
  backend mint endpoint, NOT direct `mintPublic`): polls `GET /drops/{slug}`
  stage-specifically, SIWE-logins in parallel, POSTs `/drops/{slug}/mint`,
  broadcasts returned calldata, retries once. Works for public AND WL/GTD.
- `references/opensea-backend-mint.md` — full backend-mint flow writeup:
  endpoint, headers, error semantics (200/401/409/422), stage-specific probe,
  parallel SIWE pattern, supply-math rule, sweep-back lessons.
