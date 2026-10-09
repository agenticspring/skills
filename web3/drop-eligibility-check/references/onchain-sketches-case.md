# Onchain Sketches Eligibility Case (2026-08-30)

Concrete worked example of whitelist verification for a claim-site + SeaDrop
drop on Robinhood Chain. Contract `0x882c098953e9b3c50c87f6fe0dd54b1efe951d9e`,
chain 4663, OpenSea slug `onchainsketches`.

## Drop schedule (from `GET /api/v2/drops/onchainsketches`)

| Stage | Type | Price | Window (UTC) | Max/wallet | allowlist_wallet_count |
|---|---|---|---|---|---|
| Team | signed_presale | 0 | 14:55–15:00 | 10 | 1 |
| GTD | signed_presale | 0.0002 ETH | 15:00–15:15 | 1 | 3,307 |
| WL | signed_presale | 0.0002 ETH | 15:15–15:30 | 2 | 33,912 |
| Public | public_sale | 0.0003 ETH | 15:30–17:30 | 3 | null |

`active_stage` was null before mint; `is_minting` false.

## Whitelist claim path (site, not OpenSea)

- Endpoint: `POST https://onchainsketches.xyz/api/claim`, JSON body
  `{"wallet":"0x...","route":"quests","x":"","giveaway":"","quests":"3 of 3","answers":"LINES / BERET / SHARPENER","when":"<ISO UTC>"}`.
- No signature / PoW / session. Validation is only address-format + rate limit.
- Quest answers are randomized per visitor (site stores question indices in
  localStorage keys `W1I`/`SWI`/`R3I`); answer pools: morse 16, sketchle 14
  (5-letter words), riddle 8 — see site HTML for current pools.
- Batch strategy that cleared 100/100: escalate cooldown 240s→300s→600s→900s→
  1800s and inter-request delay 7–12s→12–18s→20–30s→30–40s; retry failures
  only, keep going until failed list is empty.

## Verification results

- Before the path closed: re-submitting a previously-claimed wallet returns
  `{"ok":true,"updated":true}` = confirmed in DB. 11/100 spot-checked all
  returned `updated:true`.
- After the path closed: every submission (claimed or not) returns
  `{"ok":false,"error":"closed"}` — the site froze the list, and you can no
  longer distinguish membership this way. Verify before closure.
- `"too many tries"` mid-batch is IP rate limiting, not rejection.

## On-chain state at verification time

- `totalSupply()` = 0, `maxSupply()` = 3333, owner `0xc9cAC2...63d0`.
- `getPublicDrop(CA)` on canonical SeaDrop returned price 3e14, start
  1788103800, end 1788111000, maxPerWallet 3, feeBps 1000, restrict true.
- `getMintStats(addr)` on NFT contract returned (0, 0, 3333).
- `getSignedMintValidationParams` all zeros → signed stages not configured
  yet; `getAllowList(CA)` reverted → no merkle root yet. Eligibility for
  GTD/WL is only on-chain once the creator sets params near stage open.

## OpenSea GraphQL attempt

- SIWE auth works headlessly: `POST /__api/auth/siwe/nonce` → sign EIP-191
  message → `POST /__api/auth/siwe/verify` → cookies `access_token` +
  `refresh_token`.
- **KEY FIX (proven 100/100)**: also set cookie
  `connected-account-server-hint = <checksummed address>` on `opensea.io`.
  Then `dropBySlug` returns real `isEligible` per stage — the old "cannot
  answer headlessly" conclusion was wrong; the missing cookie was the cause.
- `dropBySlug` (not `drop`), stages typed `SIGNED_PRESALE` / `PUBLIC_SALE`;
  map to real labels (GTD/WL/Public) via API v2 `stages[].label` by index.
- Final result: 100/100 wallets `N/N/Y/Y` — quests route lands in WL stage
  (index 3), not GTD. Pattern `N/N/Y/Y` = Team ❌, GTD ❌, WL ✅, Public ✅.

