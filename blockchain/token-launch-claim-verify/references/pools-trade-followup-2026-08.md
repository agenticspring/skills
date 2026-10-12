# pools.trade Follow-up — Multi-Tweet Cross-Check + Official Platform Attribution (2026-08-05)

Same-day continuation of the $UNIFROG case. Adds: a second shill tweet that got the ordering wrong, a research-question tweet that was more accurate, the "fees strategy" decode, and full attribution of pools.trade as the official Uniswap token-issuance platform on Robinhood Chain.

## The three tweets

| Tweet | Author | Claim | Accuracy |
|-------|--------|-------|----------|
| T1 07:46 UTC | @0xDawggy (1.8K, verified) | UNIFROG first, "addy in GitHub" | ✅ infra claims true, token not in repo |
| T2 09:14 UTC | @cryptovenusrcr (806, unverified) | "UNIFROG first fees coin... $FRONG with fees" | ⚠️ FRONG named as #2 — WRONG (FORK was #2) |
| T3 08:40 UTC | @Xiaoyao_LI_0 (2K, verified, 赢麻了) | Research question: is this the official pools.trade contract? Lists UNIFROG #1, $FORK #2, router dev 0x32f4... | ✅ Fully accurate — best tweet of the three |

## True on-chain launch order (the only truth)

```
01:16 UTC  $UNIFROG 0xe702a01968800d6249522771fcc3f970f6a25403  (first)   vol $207K
06:05 UTC  $FORK    0x404a032297205d437dbafb39dab82474f18b95f0  (second)  vol $378K ← bigger than UNIFROG!
08:21 UTC  $FRONG   0x4c136180005a3c2659cd0151fa63ebcba37cc097  (third)   vol $12K
16:00 UTC  pools.trade go-live (4 PM)
```

$FORK: creator UERC20Factory, launch tx `0xbb504dfd39a5bdcf8681f29e2203f408537c97ea2cb119757fdf2cd5000d855f` via launcher `0x7A6C...768e` multicall from `0x2CF8e5b175aa29C1fDf0e9fe572735C78eacCE43`. Discovered ONLY via T3 — the T2 shill omitted it entirely.

## "Fees coin" decode

- NO fee/tax/owner functions on UNIFROG or FRONG (probed fee(), feeBps(), transferFee(), buyFee(), sellFee(), tax(), owner() — all 0/absent).
- Meaning: the LAUNCH STRATEGY had fees enabled. GitHub `addresses.ts` lines 291-306 list pairs:
  - `INSTANT_LAUNCH_STRATEGY_FEES_ON_ROBINHOOD_V311 = 0x3f556B542105D5EFBBefe7C766a4919C76B960Fb` (line 298) ← used in UNIFROG internal trace
  - `INSTANT_LAUNCH_STRATEGY_FEES_OFF_ROBINHOOD_V311 = 0x36bdB859518C89F764337cd5C24762d2Aa650f3C` (line 299)
  - FeeSplitters: `INSTANT_LAUNCH_FEE_SPLITTER_FEES_ON_ROBINHOOD_V311 = 0x6CC1b74Fc1BE1ff373Fa07f3381856f38103e653` — FRONG deployer 0x44122F... calls collectFees() on it.
- UNIFROG internal trace shows `0x3f556B...` staticcall → FEES_ON v3.1.1 strategy. So "first fees coin" = first launch through the new fees-on strategy, not a taxed token.

## pools.trade site attribution (official = VERIFIED)

Signals, in order of weight:

1. **Nameservers match uniswap.org**: `dig +short pools.trade NS` → `gemma.ns.cloudflare.com`, `damian.ns.cloudflare.com` — IDENTICAL to uniswap.org. Strong ownership signal.
2. **Backend under org domain**: root JS bundle leaks `VITE_ENTRY_GATEWAY_URL: https://entry-gateway.backend-prod.api.uniswap.org`, `VITE_WEBSOCKET_URL: wss://entry-gateway.backend-prod.api.uniswap.org/ws`. Gateway `/health` returns `ok` (200); `/ws` returns 401 (auth-gated).
3. **CSP connect-src enumerates chains**: `https://rpc.mainnet.chain.robinhood.com`, `https://eth.drpc.org`, `https://eth-mainnet.public.blastapi.io`, `https://mainnet.unichain.org`, `https://mainnet.base.org` → Robinhood + Ethereum + Unichain + Base.
4. **Dev/staging infra exists**: `dev.pools.trade` and `staging.pools.trade` resolve to separate ELBs (`rh-cca-lb-*us-east-2.elb.amazonaws.com`) but time out on HTTP — restricted. Their existence confirms real engineering infra.
5. **Production config**: Datadog RUM enabled (env `prod`, app `d9fb6f67-612a-44ea-80f9-df6a4ab10b06`, client token `pub2a38...`), WalletConnect project id `9b352e684c…c860`, `VITE_TEASER_MODE: true`, `VITE_APP_VERSION: 4cc33d5`.
6. **Registrar (mild flag, NOT decisive)**: GoDaddy + Domains By Proxy privacy, created 2026-07-17. Uniswap main domain uses Cloudflare registrar — the GoDaddy stealth registration is consistent with a pre-launch teaser domain, and signals 1-3 outweigh it.
7. **Hosting**: AWS ELB us-east-2 (Columbus) → S3 + CloudFront (`d29c45bs0h4ffe.cloudfront.net`), Amazon RSA cert, `rh-cca-*` ELB naming (Robin Hood Chain CCA = Continuous Clearing Auction).

## frong.mp4 teaser leak

- Homepage embeds `https://d29c45bs0h4ffe.cloudfront.net/rh-cca/frong.mp4` (11.7MB, 24s, 1280x720 h264, no audio).
- `last-modified: 2026-07-28T23:20:43Z` — a week BEFORE any token launch. Video frames carry screen-recording timestamp `07-28-2026 02:15:04`.
- Named **frong**, not unifrog → the showcase/demo token was FRONG, while UNIFROG launched first. Mismatch is the finding: demo naming ≠ launch order. Sibling paths (`unifrog.mp4` etc.) return 403 (only frong.mp4 exists).

## Reusable specifics

- Screenshot OCR with contrast boost for faint UI text: `tesseract` + PIL `ImageOps.autocontrast` + `ImageEnhance.Contrast(3-5x)`; crop bottom strip for timestamps.
- RPC rate limits (403) after bursts — pace `eth_call` probes or route through Blockscout.
- Blockscout API: `https://robinhoodchain.blockscout.com/api/v2/addresses/<addr>` gives `creator_address_hash`; tx endpoint needs FULL 0x-hash (truncated → 422).
- CSP headers from `curl -s -I https://<site>` are a free chain/service inventory for any DeFi frontend.
- Root JS bundle (`/assets/root-*.js`) is a free config dump: grep `VITE_[A-Z_]+` — exposes gateway URLs, RUM ids, project ids, feature flags.

## Verdict

pools.trade = official Uniswap token-issuance platform on Robinhood Chain (pre-launch teaser, go-live 4 PM UTC Aug 5). UNIFROG/FORK/FRONG = permissionless first launches on its new fees-on launcher. None is an "official Uniswap token" — the infra is official, the tokens are user launches. T3 (the research-question tweet) was the most accurate source; account size and verification badge did not predict accuracy.
