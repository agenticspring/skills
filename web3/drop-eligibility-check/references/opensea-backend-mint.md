# OpenSea Backend Mint Flow (proven 2026-08-30, Onchain Sketches)

Headless auto-mint of ANY OpenSea drop stage — public AND signed_presale
(GTD/WL) — without the creator's signer key. OpenSea's backend signs the
voucher when you call the drop mint endpoint with a wallet SIWE session.

## Endpoint

```
POST https://api.opensea.io/api/v2/drops/{slug}/mint
Headers: X-API-KEY: <OPENSEA_API_KEY>
Body:    {"minter": "<wallet_address>", "quantity": N}
```

Requires an authenticated SIWE session (cookies) for the SAME wallet being
minted. Response 200:

```json
{ "to": "0x...", "data": "0x...", "value": "0x...", "chain": "robinhood" }
```

Broadcast with cast:
```
cast send <to> --data <data> --value <value> --private-key <pk> \
  --rpc-url <rpc> --gas-limit 300000
```

## Error semantics (these are scheduler state, not bugs)

| HTTP | Body | Meaning / action |
|---|---|---|
| 200 | `{to,data,value,chain}` | drop active — broadcast now |
| 401 | `Missing an API Key...` | add `X-API-KEY` header |
| 409 | `Drop is not currently active for minting` | not open — keep polling |
| 422 | `Drop is fully minted out` | supply exhausted — stop entirely |
| 400 | `...` | bad wallet/quantity — fix input |

## SIWE session requirements

1. `siwe_login(addr, pk)` (httpx client with cookie jar) → access_token +
   refresh_token cookies.
2. **Set `connected-account-server-hint` cookie to checksummed address** on
   domain `opensea.io` — same fix as GraphQL eligibility; without it the
   backend may treat the session as having no active wallet.
3. Fresh session per wallet; never reuse one wallet's cookies for another.

## Parallel batch pattern

SIWE round-trip dominates (~15 s/wallet sequential). Wallets are independent →
parallelize:

```python
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=5) as ex:
    futures = {ex.submit(mint_one, n): n for n in targets}
    for fut in as_completed(futures):
        results.append(fut.result())
```

10 wallets ≈ 30 s with 5 workers (vs ~3 min sequential).

## Stage-specific probe (critical)

`GET /api/v2/drops/{slug}` returns `active_stage`, but multi-stage drops open
GTD before WL. A scheduler firing on the first active stage mints at the wrong
stage and fails. Rules:

1. Check the requested stage window by epoch FIRST:
   `WL_START <= now <= WL_END` → fire (WL case).
2. Fall back to `active_stage.label` ONLY when it matches the requested family
   (`'wl' in label or 'whitelist' in label` for WL; `'public' in label or
   'sale' in stage_type` for public).
3. Cheap REST probe (no SIWE) every 10 s; SIWE only at fire time.

## Supply math before arming

If `allowlist_wallet_count` (stage table) >> `maxSupply`, the drop is
oversubscribed and sells out in seconds. A 10 s poll WILL miss it. Options:
poll at 1-2 s, arm at `stage_start - offset`, or get pre-signed vouchers
ahead of time. Real case: Onchain Sketches — 3333 supply, 33,912 WL wallets
(10x oversubscribed), sold out fully in < 8 s of WL open; even a parallel
backend-mint at 15:15:08 returned 422 for all 10 wallets.

## Broadcast verification

- Anchor the success regex on `transactionHash` ONLY:
  `grep -oE 'transactionHash\s+0x[0-9a-fA-F]{64}' | grep -oE '0x[0-9a-fA-F]{64}'`
  A `(transactionHash|blockHash)[:\s]+0x{64}` regex false-matches
  `blobGasUsed`/`gasUsedForL1` fields and can report success on a failed tx.
- Verify one receipt after the batch: `cast receipt <hash> | grep -E 'from|to|status'`
  — `to` must be the intended destination, not the sender (self-send bug).

## Fund sweep-back lessons (returning dust to hub)

- ONE tx per wallet: read balance → `GP = gas-price * 1.5` →
  `GAS_COST = 21000 * GP` → `SEND = BAL - GAS_COST` → `cast send "$DEST"`.
  Refreshing gas each loop iteration creates a runaway loop (95 txs for
  0.0006 ETH observed). Residual `GAS_COST` is the intended dust endpoint.
- `cast send "$SRC"` sends funds to the wallet ITSELF — tx confirms status 1
  while balances never move. Always `cast send "$DEST"` and verify `to`.
- RH base fee moves during mint windows; add 30-50% margin over
  `cast gas-price`, else `max fee per gas less than block base fee`.
- Robinhood is legacy fee model — do NOT pass `--priority-fee`
  (errors `unexpected argument`).
