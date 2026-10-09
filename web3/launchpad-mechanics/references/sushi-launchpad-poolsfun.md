# SushiLaunchpad / pools.fun — recon (2026-08-06)

Second launchpad to go live on Robinhood Chain (4663), directly competing with
Uniswap's pools.trade. Recon findings from a teaser-site + on-chain investigation.

## Teaser site: pools.fun

- Title/slogan: "same pools, more fun." — maskot flamingo pink (favicon 🦩),
  "coming soon on Sushi" (sushi.svg = real Sushi logo, Adobe Illustrator source).
- Hosting: Netlify (server header, Netlify Edge cache, x-nf-request-id).
  DNS fronted by AWS Global Accelerator IP 75.2.60.5 (anycast, Seattle).
- Registrar: GoDaddy + domaincontrol NS (default). Domain created 2026-08-05 —
  SAME DAY as pools.trade go-live window.
- Frontend: Vite + React SPA, assets index-*.js / index-*.css, fonts
  InterTight-Bold + GeistMono-Regular. JS is only modulepreload + video
  autoplay — pure teaser, no API surface, no subdomains (app/api/dev = 000),
  all routes 404 except `/`. Assets: teaser.mp4 (15s, 720p h264), poster.jpg,
  share.jpg (1280x720 og:image).
- Narrative (from tweet @cfm_sol /2085259607497469970): Sushi + BNKR vs Uniswap
  "launchpad wars" — callbacks to Sushi's 2020 vampire attack on Uniswap.
  Sushi's Alex and BNKR deployer both posted "would be funny if the launchpad
  wars got sushi'd" shortly before pools.fun appeared.

## On-chain: $FLAMINGO (first token on SushiLaunchpad)

- CA: `0x09fd8577a5d4a7202d41aa3040f4247df4ea2d98` (Robinhood Chain 4663)
- Supply 1,000,000,000 (18 dec); ~2,056 holders, 37,613 transfers;
  vol 24h ~$3M (SushiSwap pair, 2026-08-06); MC ~$765K; 30 pairs total.
- Creation tx `0xb8b50100...` 2026-08-05 23:35:28Z, method `launchAndBuyNative`,
  value 0.21 ETH initial buy, caller EOA 0xD9088c9C... (fresh, bridge-in funded).
- **KEY: creation tx `to` = `0x104F1Ab42674565EC3DF0BFEbCcC4186f72fA7ED`** →
  blockscout `/api/v2/smart-contracts/<addr>` → name **`SushiLaunchpad`**,
  verified, Solidity 0.8.36 (optimized).

## SushiLaunchpad contract surface (from verified ABI)

- Launch entrypoints: `launch(tokenConfig, quoteToken, deadline)`,
  `launchAndBuy(...)`, `launchAndBuyNative(tokenConfig, deadline, initialBuy)`.
- State reads: `INITIAL_FDV_USD`, `calculateStartTick(address)`,
  `defaultSushiFeeBps`, `sushiFeeBps(address)`, `launchFee`,
  `protocolReserveBps`, `protocolRecipient`, `quoteTokenPriceFeed(address)`,
  `v3Factory`, `positionManager`, `owner`.
- Events: `TokenLaunched(...)`, `PositionCreated(...)`, `FeesDistributed(...)`,
  `InitialBuyExecuted(...)`, `LaunchFeesWithdrawn(...)`,
  `ProtocolReserveWithdrawn(...)`, `SushiFeeBpsUpdated(...)`,
  `DefaultSushiFeeBpsUpdated`, `LaunchFeeUpdated`, `CreatorTransferred`.
- Design parallels Uniswap Liquidity Launcher: one-call launch + initial buy,
  start-tick pricing (INITIAL_FDV_USD → calculateStartTick), fee splitter
  (Sushi fee + protocol reserve), positions migrated to Sushi v3
  (SushiV3Factory found on-chain: 0xAC707D8B... and 0x7737D250...).
- Launchpad deployer `0x104Cf4b0...` funded via bridging
  (RelayDepository / Symbiosis `swapAndStartBridgeTokensViaSymbiosis`),
  consistent with a team treasury bridging into RH.

## Reusable technique: identify WHICH launchpad launched a token

1. Fetch token creation tx (`/api/v2/addresses/<TOKEN>` → creation_transaction_hash,
   then `/api/v2/transactions/<HASH>`).
2. Read `method` + `to` — `to` is the launcher/launchpad contract.
3. `GET /api/v2/smart-contracts/<launcher>` → `name` + full verified ABI.
   Function/event names immediately reveal mechanism (launch* vs multicall CCA,
   fee splitter events, position manager, v3 vs v4).
4. `GET /api/v2/search?q=<Name>` finds contracts by name (e.g. SushiV3Factory).
5. Cross-check: launcher deploy date vs token creation vs domain registration —
   all three line up here (28 Jul launcher deploy, 05 Aug domain + token).

## Status read

- Infra = official (verified SushiLaunchpad, real Sushi logo, matching narrative).
- Token = FIRST on the launchpad but deployer was a fresh bridge-in EOA — same
  "infra official ≠ token endorsed" caveat as pools.trade bots. Vol driven by
  launchpad-wars hype.
- pools.fun = pure teaser (no product yet); launchpad itself is already live.
