# POOLS Token Analysis — 2026-08-05 (follow-up to unifrog case)

The same-day follow-up: while verifying $UNIFROG claims, Dez asked to analyze `0x385b36Ff682Ab4C76E7c37A66b96aABC466471d5` — the token named exactly like the platform. This case extended the skill with funding-cluster tracing and launcher-generation scoping.

## Token facts

| Field | Value |
|-------|-------|
| Address | `0x385b36Ff682Ab4C76E7c37A66b96aABC466471d5` |
| Name / Symbol | `pools.trade` / POOLS (name = exact platform domain!) |
| Decimals / Supply | 18 / 1B (`0x33b2e3c9fd0803ce8000000`) |
| Created | **2026-07-30T16:41:56Z** — 6 days BEFORE $UNIFROG (5 Aug 01:16) |
| Creation tx | `0xfbe305aa19b8c92d7a2c3577d71f102f8355ba9066d1b77f327ba46844bbe3b7` |
| Creator | `0x000000e200088D55C39a11F609E5F667729ad49b` (UERC20Factory — in Uniswap GitHub) |
| Launcher used | **OLD** `0x00004c4ccc709Ef590F7C81102C0689F0263D4e9` (LiquidityLauncher) — NOT the new Robinhood launcher |
| Strategy in trace | `0xcE57498D3474DC...` = INSTANT_LAUNCH_STRATEGY_FEES_ON_ROBINHOOD_8E40A35 (in GitHub) |
| Deployer EOA | `0xbE4EbA417999C7269c6D631eaEf82Ad3f2bCdd9e` (13.4 ETH) |
| Deployer pattern | active `collectFees` → `0x7198C32a...` = INSTANT_LAUNCH_FEE_SPLITTER_FEES_ON_ROBINHOOD_C3F9506 (in GitHub line 304) — fee beneficiary; also deployed own contract `0x7E6f2995...` (method `buy()`); calls proxy `0x65050A9b7E5075` (TransparentUpgradeableProxy → impl `0x20A9d3a9...`) with `0x4d819a2a` (~0.1 ETH each) |
| Funder | **`0xf70da97812CB96acDF810712Aa562db8dfA3dbEF`** — SAME wallet that funded the UNIFROG deployer (0.536 ETH → 0xD57772...). One operator cluster. |
| Top holder #1 | `0x8366a39...` = **PoolManager** (Uniswap v4 contract, 8.6%) — in-pool, not personal |
| Deployer still holds? | **NO** — absent from top-50 holders (already sold/moved) ⚠️ |
| Market (time of analysis) | vol 24h **$1.44M** (largest of all launcher tokens), FDV/MC ~$975K, liq $137K main pool, 7,188 buys / 5,608 sells, +1,130% 24h, 13 pairs (ETH/WETH/USDG) |

## Why this case matters (new technique)

1. **Funding-cluster trace links tokens no tweet mentions.** Incoming txs via `blockscout /api/v2/addresses/<deployer>/transactions?filter=to` (note: `filter=to` = incoming; default returns both directions). Both POOLS and UNIFROG deployers trace to funder `0xf70da978...` — one operator behind multiple tokens. Cross-token funder matching is the strongest link when shills disagree on ordering.
2. **Launcher generation scoping.** The repo pins OLD `LiquidityLauncher` AND NEW `LIQUIDITY_LAUNCHER_ROBINHOOD`. POOLS launched via the OLD one on 30 Jul; UNIFROG was "first via NEW launcher" on 5 Aug. Both "first" claims true — scope the claim to the launcher generation, check the creation tx `internal-transactions` for which launcher `delegatecall`'d.
3. **Name-match + pre-public-launch + fee-beneficiary = strongest candidate.** POOLS name == platform domain, launched pre-go-live, deployer collects from the official fees-on splitter. Still NOT confirmed team-issued — permissionless factory means anyone can pick the name. Report as highest-probability candidate, never confirmed.

## Verdict given to Dez

- POOLS = strongest "official/insider" candidate: earliest, platform-named, biggest volume, same funder cluster as UNIFROG, fee-beneficiary deployer.
- Red flags: deployer already out of top holders; no explicit team confirmation; +1,130% in 24h pump phase.
- Actionable: if pools.trade announces an official token at go-live (4 PM UTC 5 Aug), POOLS is the most likely candidate to compare against.
