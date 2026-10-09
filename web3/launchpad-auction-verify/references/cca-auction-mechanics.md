# CCA Auction Mechanics — Uniswap Liquidity Launcher / pools.trade

Model distilled from the Uniswap `liquidity-launcher-sdk` source (repo `Uniswap/sdks`,
path `sdks/liquidity-launcher-sdk/`) and verified on-chain on Robinhood Chain (4663).

## The Launch Flow

A launch is ONE `LiquidityLauncher.multicall([...])`:
1. `createToken(uerc20Factory, name, symbol, 18, 1e27, launcher, tokenData)` — mints fixed 1B supply to the launcher (or `depositToken` for an existing token).
2. `distributeToken(token, { strategy, amount: 1e27, configData }, salt)` — strategy pulls the full supply, initializes the hookless native-ETH v4 pool, registers `feeBeneficiary`.

Token address is CREATE2-predictable (`predictTokenAddress`) — this is why bots can front-run within seconds of a launcher deploy.

## Quick Launch Preset (canonical, non-negotiable params)

From `quickLaunch.ts`:
- Duration: 14,400s (4h) — `QUICK_LAUNCH_DURATION_SECONDS`
- Supply: 1,000,000,000 @ 18 decimals = 1e27 raw
- 50% (5e26) → auction; 50% (5e26) → reserved for LP (seeded with 100% of raised proceeds)
- Raise currency: native ETH (`address(0)`)
- Floor FDV: $1,000; Graduation FDV: $10,000 (≈$5K raise since only 50% sold)
- LP fee: 2500 (0.25%); tick spacing 25 (post-2026-08-05 redeploy; older gen 50)
- LP range: CONCENTRATED_FULL_RANGE; lock mode default `buybackBurn`
- Allowed graduation FDVs: [$5K, $10K] ±10%; structurally permanent lock modes: `burn`, `creatorFees`

Important: "quick launch" is NOT a separate contract — it is a CCA with this exact parameter set. The SDK explicitly warns the classifier is cosmetic and "MUST NOT gate suppression of token-protection warnings — it is not a trust signal." Bot-launched tokens match the preset perfectly.

## CCA State Functions (verified ABI)

| Function | Selector | Meaning |
|----------|----------|---------|
| `endBlock()` | 0x083c6323 | auction finish block |
| `isGraduated()` | 0x9e5f2602 | met graduation criteria |
| `claimBlock()` | 0x37dfbc4b | winning bids become claimable |
| `currencyRaised()` | 0x998ba4fc | total currency raised so far |
| `remainingSupply()` | 0xda0239a6 | tokens not (yet) sold |
| `sweepUnsoldTokensBlock()` | 0x8a76bfe4 | 0 until creator sweeps (one-shot) |
| `tokensRecipient()` | 0x3c05e7bc | only address allowed to sweep |

## Outcome Model (what actually happens to a bidder)

- **Graduated auction** (`isGraduated() == true`): ALL bids settle to tokens at the clearing price. NO ETH refund. This is the "I bid $50, got full tokens" answer — the whole bid converts.
- **Failed auction** (`currentBlock >= endBlock && !isGraduated()`): creator may call `sweepUnsoldTokens()` — on a failed auction this returns the FULL deposited supply (not just unsold). Bidder recovery is claim-based; creator sweep competes for the value.
- **Partial fill / pro-rata**: when total committed bids exceed supply at clearing, allocation is proportional (e.g. 50% fill for everyone) and the excess bid is refundable — but settlement is claim-based, never automatic. A user who "does nothing" leaves funds stranded in the auction contract.

## Lock Recipients (post-migration)

LP position goes to a per-launch CREATE2 recipient until timelock expires. Modes:
- `timelock` — plain hold-until-block, then operator may move
- `feesForwarder` — LP fees claimable meanwhile
- `buybackBurn` — accrued currency buys back and burns the token
- `burn` / `creatorFees` — structurally permanent (timelock horizon 1000+ years)

## Real Case (verified 2026-08-05)

FROGE (`0x1dF1F09c4Dd65C76746d53467361D536cDfDC719`), launched via launcher
`0x0000FffFBE8efE702c8703aE3477FF5dE3d319C0`. User wallet bid 6x `submitBid` totaling
0.025671 ETH to auction `0xCf297C3eBD72Ec2207DFD216F20Ef7e14b654aCb`.
Auction state: `isGraduated = true`, `currencyRaised = 70.03 ETH`, `remainingSupply = 558`.
Outcome: user received 72.5 FROGE — full bid converted to tokens, no refund (graduated).

## Launchpad Comparison (CCA vs bonding curve)

| Aspect | CCA (pools.trade) | Bonding curve (Pump.fun) |
|--------|-------------------|--------------------------|
| Buy model | Commit bid → clearing | Instant swap |
| Fill | Pro-rata if oversubscribed | Full at curve price |
| Anti-snipe | Batch clearing, same price | Front-runnable |
| Settlement | Claim-based (claimBlock) | Immediate |
| LP | 50% reserved + proceeds, locked | Migrates after threshold |
| Failure | Creator sweep + claim-based refund | Curve stuck / dev rug |
