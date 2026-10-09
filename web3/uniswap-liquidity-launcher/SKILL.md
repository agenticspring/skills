---
name: uniswap-liquidity-launcher
description: "Understand Uniswap Liquidity Launcher / pools.trade."
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Uniswap, Robinhood-Chain, Liquidity-Launcher, CCA, pools.trade]
---

# Uniswap Liquidity Launcher / pools.trade Mechanics

Reference knowledge for the Uniswap token-issuance stack on Robinhood Chain
(chain 4663) behind `pools.trade` — contracts, launch flow, quick-launch
preset, CCA auction behavior, fees, and the bot-farm signature seen on every
launch. Use when analyzing tokens launched via this stack, explaining the
mechanics to Dez, or deciding whether a launch will graduate.

## Key contracts (chain 4663, post-2026-08-05 full redeploy)

```
LIQUIDITY_LAUNCHER_ROBINHOOD (FINAL, vanity-mined) = 0x0000FffFBE8efE702c8703aE3477FF5dE3d319C0
  - superseded 0x7A6C474b... (v3.1.1) and 0x00004c4c... (old)
UERC20_FACTORY                                     = 0x000000e200088D55C39a11F609E5F667729ad49b
  - token factory; ANYONE can call createToken — permissionless
USUPERC20_FACTORY                                  = 0xeEeeEEE204Afb6BABb1287ffed52cCD6BA0b0fb2
POSITION_MANAGER_ROBINHOOD                         = 0x58daec3116aae6D93017bAAea7749052E8a04fA7
INSTANT_LAUNCH_STRATEGY_FEES_ON_ROBINHOOD_20260805 = 0x23f8209572b4a1C2AD88A42749E830791Fb027f1
INSTANT_LAUNCH_STRATEGY_FEES_OFF_ROBINHOOD_20260805= 0xAD44D55E7f8337C3cE113fBb591486E85be104b2
INSTANT_LAUNCH_FEE_SPLITTER_FEES_ON_20260805       = 0xeFF166AAf189323c58dc27eD1206EB2C37FaACDf
UERC20_BENEFICIARY_VAULT_ROBINHOOD                 = 0xd35E9CA72F64C7F93BE30fad67524323396B36D7
```

Canonical CREATE2 deployer: `0x4e59b44847b379578588920cA78FbF26c0B4956C`.
Uniswap's own deployer EOA (seen deploying launcher/strategies): `0x32f4B2e6...`.

## Launch flow (one LiquidityLauncher.multicall)

1. `createToken(uerc20Factory, name, symbol, 18, 1e27, launcher, tokenData)`
   — mints fixed 1B supply to the launcher (or `depositToken` for existing tokens)
2. `distributeToken(token, { strategy, amount, configData }, salt)`
   — strategy pulls supply, initializes the hookless native-ETH v4 pool
   (LP_FEE 2500 = 0.25%, TICK_SPACING 25 after redeploy), optionally registers
   `feeBeneficiary`
3. CCA (Continuous Clearing Auction) runs; on graduation, `migrate()` moves
   proceeds + reserved supply into the v4 pool

## Quick Launch preset (quickLaunch.ts)

```
QUICK_LAUNCH_TOTAL_SUPPLY           = 1_000_000_000 (1B, 18 decimals = 1e27 raw)
QUICK_LAUNCH_SUPPLY_AUCTIONED_PCT   = 50   (500M auctioned)
QUICK_LAUNCH_RESERVED_FOR_LP_RAW    = 5e26 (500M + 100% of raised proceeds seed LP)
QUICK_LAUNCH_DURATION_SECONDS       = 14_400 (4h)
QUICK_LAUNCH_FLOOR_FDV_USD          = 1_000
QUICK_LAUNCH_GRADUATION_FDV_USD     = 10_000 (~$5K raise at 50% sold)
QUICK_LAUNCH_LP_FEE                 = 2_500 (0.25%)
QUICK_LAUNCH_POOL_TICK_SPACING      = 25 (post-2026-08-05; older = 50)
QUICK_LAUNCH_LOCK_MODE              = buybackBurn
QUICK_LAUNCH_LP_RANGE               = CONCENTRATED_FULL_RANGE
```
"Quick launch" is NOT a separate contract — it is a CCA with these fixed params.
The classifier is explicitly "not a trust signal"; anyone can reproduce the preset.

## CCA behavior that matters to buyers

- Bids are committed ETH; tokens settle at clearing price per cycle — **not
  instant swap**. "Fill %" is pro-rata across a batch when oversubscribed.
- Partial fill → excess bid is refunded **only via claim/settle**, not auto.
  `claimBlock()` tells when winning bids become claimable.
- Failed (non-graduated) auction: creator can `sweepUnsoldTokens()` (one-shot,
  returns full deposited supply). Funds left unclaimed stay stuck in the auction.
- `sweepCurrencyBlock()`, `currencyRaised()`, `remainingSupply()`,
  `tokensRecipient()`, `endBlock()` are the state views (CCA_ABI in abis.ts).

## Fee structure

- FeeSplitter splits creator share → UERC20BeneficiaryVault → autocompound.
- FEES_ON vs FEES_OFF strategies: creator fees enabled = different strategy
  instance. MPS_TOTAL = 10_000_000 (milli-percent denominator).
- MIN_LP_ALLOCATION_PERCENT = 25 per bracket.
- Lock modes: timelock / feesForwarder / buybackBurn; "permanent" modes
  (burn, creatorFees) use timelock horizon >= 1000 years.

## Bot-farm signature (observed on every launch)

- Tokens appear <= 30s after a contract deploy (front-run).
- Deployer EOAs are funded by high-volume bot wallets (114K–652K txs).
- Vanity address pairs share long common substrings (e.g. 32 of 40 chars) —
  deliberately crafted by one operator.
- Even with official infra, a token created by a bot is NOT the official token.
  Separate "infra is official" from "token is official" — that is the whole point.

## Pitfalls

- **"First launch" claims are worthless** — bots front-run every redeploy;
  verify the deployer's funding path and tx counts before believing a narrative.
- **A 200 HTTP / verified contract ≠ endorsement** — factory is permissionless.
- **Don't predict graduation from bid size alone** — graduation needs ~$5K raise;
  a single small bidder does not graduate the auction and funds may require
  manual claim.
- **Website teaser changes are real signals** — JS/CSS bundle hashes and
  `addresses.ts` commits track pre-launch prep; monitor them with hashed
  watchers that strip random CSP nonces (`nonce="..."`) before diffing.
