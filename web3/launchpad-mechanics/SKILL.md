---
name: launchpad-mechanics
description: Explain token-launchpad mechanisms and their trade-offs.
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Launchpad, CCA, Auction, Bonding Curve, DeFi]
---

# Launchpad Mechanics (CCA vs bonding curve vs LBP)

Explain how a token launchpad actually works — CCA (Continuous Clearing Auction), bonding curves (Pump.fun-style), and LBP (Liquidity Bootstrapping Pool) — including the buyer-side consequences users feel: partial fill, refunds, graduation, lock-ups. The reference case is Uniswap's pools.trade / Liquidity Launcher on Robinhood Chain (chain 4663), verified against the `Uniswap/sdks` liquidity-launcher-sdk source.

This is an EXPLAIN skill: when the user asks "gimana cara kerja", "kenapa gak full", "dari mana dapet token" — answer conceptually BEFORE coding or trading. Do NOT verify tokens here (see token-launch-verify for verification workflows).

## When to Use

- "Jelaskan mekanisme cara kerja [launchpad]" / "gimana cara kerja pools.trade"
- "Kenapa beli $20 tapi gak dapet full?" (partial fill / pro-rata)
- "Kalau waktu habis, sisanya refund?" (claim-based refunds)
- "Yang punya dana gede lebih banyak share?" (pro-rata nuance + sybil bypass)
- Comparing launchpads: pools.trade vs Pump.fun vs LBP platforms
- Recon of a NEW launchpad (e.g. Sushi's pools.fun / SushiLaunchpad on RH chain)
  — how to identify which launchpad launched a token: creation tx `to` contract
  → `/api/v2/smart-contracts/<launcher>` verified ABI → mechanism fingerprint.

> Reference: `references/sushi-launchpad-poolsfun.md` — full recon of Sushi's
> SushiLaunchpad + pools.fun teaser + $FLAMINGO (second launchpad on RH 4663,
> directly competing with pools.trade; verified Solidity 0.8.36 contract).

## Key Facts — Uniswap Liquidity Launcher (pools.trade)

- Launch = ONE `LiquidityLauncher.multicall`: `createToken`/`depositToken` → `distributeToken` into LBPStrategy → CCA auction → graduation migrates to a Uniswap v4 pool.
- New tokens: fixed 1B supply, 18 decimals, minted via `UERC20Factory` (CREATE2 → address predictable).
- Quick-launch preset: 4h (14,400s), 50% supply auctioned in native ETH, 50% reserved to seed LP, floor FDV $1K, graduation FDV $10K (~$5K raise), LP fee 0.25%, tick spacing 25, lock mode `buybackBurn`. "Quick launch" is a PARAMETER classifier, not a separate contract — and NOT a trust signal.
- Pool id = `keccak256(abi.encode(currency0, currency1, fee, tickSpacing, hook))`; reserved in `LBPStrategy.registeredPoolIds`; duplicate launch reverts `PoolIdOccupied`.
- Fees: FeeSplitter → UERC20BeneficiaryVault → autocompound (FEES_ON strategy); MPS denominator 1e7; MIN_LP_ALLOCATION_PERCENT = 25.
- Post-auction functions: `settle()` (bidder claims), `sweepUnsoldTokens()` (CREATOR, after endBlock), `migrate()` (permissionless, after graduation + migrationBlock).

## Buyer-Side Mental Model (explain these clearly)

1. **You BID, you don't swap.** ETH is committed to the auction contract; tokens come via settlement cycles — not instantly.
2. **Partial fill is pro-rata.** If total bids exceed supply at the clearing price, EVERY bidder fills at the same percentage; excess is refunded. Whale gets more TOKENS (bigger bid) but the same FILL % — not priority.
3. **Refunds are claim-based, NOT automatic.** Unfilled ETH stays in the auction contract until the bidder settles/claims. A bidder who does nothing can have funds stuck. "Refund" ≠ auto-return.
4. **Quiet auctions are a trap, not an opportunity.** Low participation → auction likely fails to graduate → no pool migration → tokens not liquid → creator can `sweepUnsoldTokens`. "Few buyers = full fill" is worthless if the token never graduates.
5. **Sybil bypasses pro-rata.** Splitting bids across wallets multiplies per-bidder allocation — the observed bot-farm pattern on pools.trade.

## Procedure

1. Identify the launch model from on-chain facts: auction params (duration, floor FDV, graduation FDV, fee tier) from SDK preset or contract reads.
2. Answer the buyer question with the mental model above; use a concrete worked example (e.g. $20 bid vs whale $500 bid) rather than abstractions.
3. If the user asks about a SPECIFIC token: check its graduation status (did bids reach threshold?), whether the auction ended, and whether the creator already swept — but keep verification work separate from the explanation.
4. Compare against other models (bonding curve = instant swap, price rises with buys; LBP = price starts high, declines; CCA = batch clearing, pro-rata) using the table below.

## Model Comparison

| Aspect | CCA (pools.trade) | Bonding curve (Pump.fun) | LBP |
|--------|-------------------|--------------------------|-----|
| Buy model | Bid + batch clearing | Instant swap | Bid + declining price |
| Full fill? | Pro-rata, may partial | Always full (price adjusts) | Pro-rata possible |
| Refund | Claim-based | N/A | Claim-based |
| Whale protection | Pro-rata (sybil bypasses) | None (front-run by speed) | Declining price |
| Graduation | FDV threshold gate | Curve → DEX migration | Threshold gate |

## Pitfalls

- Don't claim "refund otomatis" — it's claim/settle-based; state that explicitly.
- Don't imply whale gets worse fill % — same %, more tokens. The nuance users miss.
- Don't imply "sepi = untung" — quiet auctions often fail graduation and leave tokens stuck/swept.
- Don't conflate "infra is official" with "token is official" — the factory/launcher being Uniswap's doesn't make any particular token endorsed (bot farms launch through the same contracts within ~30s of deploy).

## Verification

Explain the pro-rata example to a fresh user and confirm they can restate it: same fill % for all bidders, token count proportional to bid, excess refunded on claim. If the explanation survives that restatement, the mental model is correct.
