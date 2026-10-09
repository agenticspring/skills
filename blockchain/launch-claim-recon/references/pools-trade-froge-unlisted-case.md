# pools.trade frontend listing: FROGE valid on-chain but absent from UI

Worked example (2026-08-06) of the "valid on-chain ≠ listed on launchpad frontend" class.

## Question
Dez held FROGE (`0x1df1f09c4dd65c76746d53467361d536cdfdc719`, 72.5 tokens, bought in
an auction earlier). FROGE showed $4.66M/24h volume on dexscreener — top volume on
Robinhood Chain — but did NOT appear on the pools.trade home trending list.
Question: "kenapa Dev hapus dari home?" — was it removed?

## Investigation path (what actually resolved it)

1. **Home page is live now** — `curl https://pools.trade/` returns
   `<title>Pools — create a token on Robinhood Chain</title>` (no longer teaser).
   HTML is an SPA shell; the token list renders via JS, so curl alone is not enough.

2. **Intercept the data API** — headless browser on `https://pools.trade/`,
   capture `request` events containing `/api/trpc/`:
   ```
   GET /api/trpc/cca.listAuctions,curve.listLaunches,session.status,prices.getTokens?batch=1&input=%7B%221%22...
   ```
   Decoded input: `{"1":{"sortBy":"volume"},"3":{"tokens":[...ETH quote tokens...]}}`.
   Key numbers = procedure positions in the URL; `curve.listLaunches` (position 2)
   takes no input and is simply omitted from the input map.

3. **Query each list for the token**:
   - `cca.listAuctions` → 24 items, FROGE absent
   - `curve.listLaunches` → 100 items, FROGE absent
   - Direct `https://pools.trade/token/0x1df1...` → body "404 Not Found"

4. **Root cause on-chain** — FROGE creation tx `0x8975ac02...` is `multicall`
   to LiquidityLauncher FINAL `0x0000FffF...`; then `TokenDistributed` event
   (topic0 = keccak256("TokenDistributed(address,address,uint256)")) shows it was
   distributed to strategy `0x05d552391067389ee44fec3924157ed33f976000` =
   **LBPStrategy** (verified, deployed 10 Jul by team wallet `0x32f4B2e6...`).

5. **Compare with tokens that ARE listed**:
   - PIGI (`0xcd1fC623C5...`) → strategy `0x23f8209572b4a1c2ad88a42749e830791fb027f1` =
     **InstantLaunchStrategy** (verified, deployed 05 Aug 13:25 by the SAME team wallet)
   - FRONG/POOLS (old legacy tokens) → seeded manually / via old launcher; shown in UI

6. **Conclusion**: not "removed". The backend tracks only current-generation
   strategies (InstantLaunchStrategy post-redeploy 05 Aug 15:02, commit
   `dd0ea30b`) plus seeded legacy tokens. FROGE launched via the OLD-generation
   LBPStrategy → no record in the backend → 404 on token page → absent from home.
   Still fully tradeable (dexscreener pool, $317K liquidity).

## Key reusable facts

- pools.trade home tRPC: `cca.listAuctions,curve.listLaunches,session.status,prices.getTokens` batch
- `curve.listLaunches` takes no input (omit its key from input map)
- Strategy-generation check: `smart-contracts/<strategy>` name + deployment date vs launcher redeploy date
- `TokenDistributed` event: topics[1]=token, topics[2]=strategy
- LiquidityLauncher FINAL `0x0000FffFBE8efE702c8703aE3477FF5dE3d319C0`
- Team CREATE2 deploy wallet `0x32f4B2e6...` deploys both old and new strategies

## Verdict phrasing used

"Bukan dihapus — FROGE gak pernah terdaftar di backend pools.trade. Launch via
LBPStrategy generasi lama yang backend sekarang gak track. Tetep valid on-chain,
tetep bisa jual — cuma gak dapet exposure listing resmi."
