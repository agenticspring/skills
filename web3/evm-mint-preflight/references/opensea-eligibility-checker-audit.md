# OpenSea Eligibility Checker Audit

Reviewed reference: `krisnrzky/opensea-eligibility-checker`

- Commit inspected: `37d48f0fdbd681c39771f5256980ef7d1d6bfafa`
- Scope: read-only eligibility reconnaissance for OpenSea Drops
- Upstream verification: Python files compile; CLI `--help` runs; no automated upstream tests found

## Useful patterns

The checker separates three evidence surfaces:

1. **SeaDrop on-chain:** `getMintStats`, `getPublicDrop`, and allowlist-root reads for supply, wallet cap, stage window, price, and root presence.
2. **OpenSea API v2:** `GET /api/v2/drops/{slug}` for stage labels, timing, price, and wallet limits.
3. **OpenSea wallet-auth GraphQL:** `GET /api/v2/drops/{slug}/eligibility` is the official typed SDK route for wallet-scoped eligibility; older standalone flows use SIWE plus GraphQL `DropEligibilityQuery` and read `dropBySlug`.

Useful normalization rules:

- API/GraphQL stage labels are not interchangeable. API v2 can expose `GTD`, `WL`, `FCFS`, and `Public`; GraphQL may expose generic `SIGNED_PRESALE`/`PUBLIC_SALE`.
- Public stages do not require a wallet eligibility proof, but they still require live contract/window/supply checks before a mint plan is valid.
- `/drops/{slug}` provides stage data; `/collections/{slug}` provides collection/social metadata. Do not merge them as if one endpoint were authoritative for both.
- GraphQL persisted-query hashes can expire. Treat a stale hash as an unavailable source, never as permission to guess or use an unverified replacement.

## Official acquisition routes used by the bot

From the official OpenSea SDK/API source:

```text
GET  /api/v2/drops/{slug}/eligibility
POST /api/v2/drops/{slug}/mint
```

The mint body is:

```json
{"minter":"0x...","quantity":1}
```

The response is ready-to-sign transaction data:

```text
to
 data
 value
 chain
```

The acquisition client must validate those fields and hand them to the same EVM campaign finalizer as direct SeaDrop/Merkle/voucher routes. It must not sign or broadcast.

## Security exclusions

Do not copy these patterns into production:

- CLI `--private-key` / `--api-key` values;
- raw SIWE signatures, cookies, JWTs, or session tokens in output;
- hardcoded RPC URLs or contract selectors as a source of truth;
- fixed persisted GraphQL hashes without freshness/version control;
- eligibility output treated as executable mint permission;
- direct fallback from an API 401/403 to an undocumented endpoint.

## Required finalizer sequence

```text
normalize discovery data
→ bind wallet ID + checksummed address
→ bind campaign/stage/artifact version
→ verify chain ID and target/NFT code hashes
→ validate exact target/value/calldata
→ eth_call
→ eth_estimateGas + gas ceiling
→ native balance + reserve
→ observe block
→ atomic replay reservation
→ signed=false, broadcast=false
```

A live API 401/403 is an honest unverified result. Report it, preserve the read-only boundary, and do not claim eligibility or discovery succeeded.
