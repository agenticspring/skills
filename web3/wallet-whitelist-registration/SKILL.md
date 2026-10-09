---
name: wallet-whitelist-registration
description: Batch register EVM wallets to NFT drop whitelists.
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [NFT, Whitelist, Wallet, Batch, Registration]
    related_skills: [browserless-web-automation, web3-freemint-batch-execution, evm-wallet-set-management]
---

# Wallet Whitelist Registration

Register many EVM wallets (Hermes spring wallet sets) to an NFT project's
whitelist. Handles the common patterns: plain JSON API, Next.js `/api`
endpoint, Google Forms (via Camofox), and TanStack server functions. It does
NOT mint, claim, or sign transactions — registration only.

## When to Use

- User says "isi whitelist semua wallet", "register all wallets", "daftarin ke whitelist"
- An NFT drop site has a whitelist/allowlist phase with a wallet input
- Batch of Hermes wallet sets (Set 1..N) needs whitelist spots

## Prerequisites

- Hermes wallet file: `/root/.hermes/.credintial/.springwallet` (mode 600)
- `cast` (Foundry) for mnemonic derivation
- For Google Forms: `camofox-browser@2.4.7` (see `browserless-web-automation`)
- Never print mnemonic/private key; derive addresses ephemerally

## How to Run

Invoke through the `terminal` tool:

```bash
python3 scripts/register-whitelist.py <api-url> [start-set] [end-set]
```

Example (Robillio-style Next.js API):

```bash
python3 scripts/register-whitelist.py https://robillio.xyz/api/whitelist 1 100
```

## Quick Reference

| Pattern | What to look for | Method |
|---------|-----------------|--------|
| Plain JSON API | `fetch("/api/whitelist", {method:"POST", body:{wallet}})` in JS | POST `{wallet}` |
| Google Form | `docs.google.com/forms` URL | Camofox batch (see browserless skill) |
| TanStack `/_serverFn` | chunk `*.functions-*.js`, export map | Camofox eval (see browserless skill) |
| Wallet-signing gate | sign-message challenge | local sign + submit (see bandit-list flow) |

## Procedure

1. **Recon the site.** Fetch the whitelist page through `web_extract`/`terminal`; find the submit endpoint and payload shape. Common: Next.js page chunk contains `fetch("/api/whitelist",{body:JSON.stringify({wallet:...})})`. Look for captcha/turnstile/signing requirements before batch.
2. **Test with Set 1 first.** POST one wallet; expect `{"success":true,"entry":{...}}` or an explicit error. This proves the endpoint, payload, and whether quota/duplicates are enforced.
3. **Batch.** Run `scripts/register-whitelist.py <api-url> 1 100`. The script derives addresses from the wallet file (ephemeral, never prints keys), POSTs each, records `success`/`id`/`error`, and sleeps between calls.
4. **Chunk long batches.** execute_code has a 300s timeout; ~2s/wallet means ~150 wallets max per run. Split 100+ wallets into two ranges (`1 56`, `57 100`) or run the script via `terminal(background=true)`.
5. **Verify.** Re-read the results file; confirm every set has `success:true`. Optionally re-POST one wallet and confirm the server returns "already registered" (not a new entry) to prove idempotency.

## Pitfalls

- **Duplicate entry IDs**: some servers mint sequential IDs and can return the same ID twice (observed `ROB-2609` for two different wallets). Success flag is the authority, not the ID.
- **"remainingSpots: 0" does not mean closed**: Robillio reported `remainingSpots:0` on the first entry yet accepted all 100. Only an explicit failure/error means closed.
- **IP logging**: server records the source IP for every entry. All wallets from one VPS IP look like one operator — acceptable for whitelist farming, but note it before blaming a failure on the wallet.
- **Rate limits**: add ~0.2s sleep between POSTs; if 429 appears, raise the delay, not concurrency.
- **Wallet source consistency**: derive from the same `.springwallet` used everywhere (Set index = valid mnemonic order, not raw line number — header lines can look like mnemonics).
- **Don't sign or broadcast**: registration endpoints usually don't need a signature. If a site demands wallet signing, it is the allowlist-claim pattern — see `browserless-web-automation` TanStack section, not this skill.

## Verification

```bash
python3 - <<'PY'
import json
r = json.load(open('/tmp/whitelist-results.json'))
print('ok', sum(1 for x in r if x['ok']), 'fail', sum(1 for x in r if not x['ok']))
PY
```
