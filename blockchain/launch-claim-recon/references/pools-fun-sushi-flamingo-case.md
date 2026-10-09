# Worked example: pools.fun (Sushi) vs pools.trade (Uniswap) — FLAMINGO "first launch" debunk

Session: 2026-08-06. Full worked case for `launch-claim-recon` section D (event-scanning
"first launch" verification).

## Context

Uniswap launched **pools.trade** (Liquidity Launcher on Robinhood Chain 4663). The same
week, **pools.fun** appeared: "same pools, more fun", maskot flamingo 🦩, "coming soon on
Sushi". A viral tweet (Jeff @cfm_sol, 27.6K followers) claimed $FLAMINGO was the first
token on the new Sushi launchpad, echoing a Sushi "vampire attack" narrative.

## Recon pools.fun (teaser site)

- Title: "same pools, more fun." / "coming soon on Sushi"
- Hosting: Netlify (`server: Netlify`, `cache-status: "Netlify Edge"`), IP 75.2.60.5 =
  AWS Global Accelerator (anycast, Seattle)
- Domain: GoDaddy + domaincontrol NS, created 2026-08-05 (same day as pools.trade go-live)
- Assets: `teaser.mp4` (15s 720p h264), `sushi.svg` (real Sushi logo, Adobe Illustrator),
  `share.jpg` (1280x720), `poster.jpg`. JS = modulepreload + video handler only, no API.
- All routes 404; no active subdomains (app/api/dev/staging = 000).

## On-chain verification (the important part)

FLAMINGO CA `0x09fd8577a5d4a7202d41aa3040f4247df4ea2d98`:
- Creation tx `0xb8b50100...`, method `launchAndBuyNative`, to `0x104F1Ab42674565EC3DF0BFEbCcC4186f72fA7ED`
- That contract = **SushiLaunchpad** — verified, Solidity 0.8.36 (Blockscout smart-contracts)
- NOT the Uniswap LiquidityLauncher (`0x0000FffF...` / `0x7A6C474b...`). FLAMINGO is
  genuinely a Sushi-launchpad token.
- SushiLaunchpad deployed 2026-07-28T22:39Z (block 21,957,383), by `0x104Cf4b0...`
  (bridge-in wallet via RelayDepository/Symbiosis — bot-ish pattern, not conclusive alone)

### "First launch?" — debunked by event scan
- ABI event `TokenLaunched(address creator indexed, address token indexed, address pool indexed,
  address quoteToken, int24 startTick, string name, string symbol, uint16 reserveBps,
  uint256 reserveAmount, uint64 reserveUnlockAt, uint16 initialSushiFeeBps)`
- topic0 = keccak256 of full signature
- eth_getLogs launcher deploy block → FLAMINGO creation block (21,957,383 → 28,885,821):
  **922 TokenLaunched events before FLAMINGO** → FLAMINGO was #923, NOT first.
- Full scan deploy→latest = **1,170 launches** total.
- Launch #1 happened within hours of deploy (block 21,966,938).

## Volume/MC ranking across all launcher tokens

- SushiLaunchpad: 1,170 tokens → ~300 had dexscreener pairs. Top: MEOWSHI MC $598K,
  FLAMINGO MC $386K but vol $3.26M (highest volume), LONGCAT $320K, CAT $109K.
- pools.trade (Uniswap): TokenCreated(address) on both LiquidityLauncher deployments
  (`0x7A6C474b...` v3.1.1 = 391, `0x0000FffF...` FINAL = 22,484) → **22,875 tokens total**,
  only ~576 (2.5%) still had pairs. Top volume: FROGE $4.66M, BOW $1.26M, GOAT $1.19M.
- Insight: the "first token" and even "highest volume" are hype-driven, not legitimacy
  signals. 74–97.5% of permissionless-launchpad tokens die.

## Key technique notes

- Event log scan is THE reliable way to disprove "first launch" — a creation-tx-only
  check cannot show what came before.
- Always decode indexed topics from the ABI, not by guessing: topics[1]=creator,
  topics[2]=token, topics[3]=pool for TokenLaunched. The naive "topics[1] is the token"
  assumption gave a creator address as first result.
- eth_getLogs hard limit 10,000 logs per query → chunk ranges (100K blocks) + loop.
- Batch dexscreener multi-token endpoint handles ~25-30 addresses per call; 22K tokens
  = ~763 batches, finish in ~10s with ThreadPoolExecutor(10).
- Robinhood public RPC 403s on bursts; blockscout `/api/v2/smart-contracts/<addr>` gives
  verified ABI + functions/events lists — better than guessing selectors.
