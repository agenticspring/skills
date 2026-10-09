# Worked Example: pools.trade / Uniswap Robinhood Launcher (Aug 2026)

Session case showing the full launch-claim-recon flow. Timeline: tweets claimed UNIFROG was "the first token launched via the address in Uniswap's GitHub" on Robinhood Chain.

## Key on-chain facts (verified)

- **Chain**: Robinhood Chain, ID 4663. RPC `https://rpc.mainnet.chain.robinhood.com`. Explorer `https://robinhoodchain.blockscout.com` (Blockscout v2 API).
- **Repo**: `Uniswap/sdks`, file `sdks/liquidity-launcher-sdk/src/addresses.ts` (672 lines, active commits daily).
- **Core addresses in GitHub** (all verified on-chain):
  - `LIQUIDITY_LAUNCHER` (old) = `0x00004c4ccc709Ef590F7C81102C0689F0263D4e9`
  - `LIQUIDITY_LAUNCHER_ROBINHOOD` (new) = `0x7A6C474b4DcD35b72203D2B569EAfE4C9b5C768e`
  - `UERC20_FACTORY` = `0x000000e200088D55C39a11F609E5F667729ad49b` (verified name "UERC20Factory")
  - `POSITION_MANAGER_ROBINHOOD` = `0x58daec3116aae6D93017bAAea7749052E8a04fA7` (verified "PositionManager")
  - `INSTANT_LAUNCH_STRATEGY_FEES_ON_ROBINHOOD_V311` = `0x3f556B542105D5EFBBefe7C766a4919C76B960Fb`
  - FeeSplitter FEES_ON = `0x7198C32a497c09497e04C86cf8F77A244A9E4b8F` (old gen) / `0x6CC1b74Fc1BE1ff373Fa07f3381856f38103e653` (v3.1.1)
  - Strategy `0xcE57498D3474DCC244dFb6710fFbE6D4441cD2b2` = `INSTANT_LAUNCH_STRATEGY_FEES_ON_ROBINHOOD_8E40A35` (used by POOLS launch)
- **Deployer wallet**: `0x32f4B2e69EbD7746596AF8699DAC1908F43107aD` — deployed launcher/factory via CREATE2 factory `0x4e59b44847b379578588920cA78FbF26c0B4956C`. PositionManager was created 2026-05-22; UERC20Factory 2026-07-08; new launcher 2026-08-04T23:40.
- **Launch timeline**:
  - $POOLS (`0x385b36Ff682Ab4C76E7c37A66b96aABC466471d5`, name `pools.trade`, symbol POOLS, supply 1B) — created 2026-07-30T16:41 UTC via OLD launcher + FEES_ON 8E40A35. Vol 24h $1.44M, +1130%.
  - $UNIFROG (`0xe702a01968800d6249522771fcc3f970f6a25403`) — created 2026-08-05T01:16 UTC via NEW launcher v3.1.1. Vol $207K, +2636%.
  - $FORK (`0x404a032297205d437dbafb39dab82474f18b95f0`) — 2026-08-05T06:05 UTC. Vol $378K.
  - $FRONG (`0x4c136180005a3c2659cd0151fa63ebcba37cc097`) — 2026-08-05T08:21 UTC. Vol $12K.
  - pools.trade frontend "Coming soon from Uniswap", go-live 16:00 UTC Aug 5. Teaser video `frong.mp4` on CloudFront (last-modified 2026-07-28, before any launch — demo existed a week prior).
- **Frontend authenticity signals**: NS `damian.ns.cloudflare.com` + `gemma.ns.cloudflare.com` identical to uniswap.org; JS bundle `VITE_ENTRY_GATEWAY_URL=https://entry-gateway.backend-prod.api.uniswap.org`; CSP connect-src includes Robinhood/ETH/Unichain/Base RPCs + WalletConnect; Datadog RUM app id `d9fb6f67-612a-44ea-80f9-df6a4ab10b06` env prod; WHOIS GoDaddy + DomainsByProxy, created 2026-07-17; dev/staging subdomains resolve to separate ELBs.

## Sybil cluster finding (the important part)

- Funder `0xf70da97812CB96acDF810712Aa562db8dfA3dbEF`: **652,558 txs, 3,188,885 token transfers** → automated bot, not a human dev wallet. Balance 133 ETH.
- Vanity-paired L1 wallet `0x081Ea97812CB96acdF810712aa562Db8dFA3ED00`: shares core `a97812CB96acDF810712Aa562db8dfA3` (32 of 40 chars) — same entity, deliberately generated addresses. Sent 50–112 ETH chunks ×25 via `submitRetryable` (Arbitrum bridge) to the funder.
- Funder funded BOTH $POOLS deployer (`0xbE4EbA417999C7269c6D631eaEf82Ad3f2bCdd9e`, +0.256 ETH @ 30 Jul 14:01, 2.5h before launch) AND $UNIFROG deployer (`0xD57772C610E571e2D16FA14836C319C43a9fB5d2`, +0.536 ETH @ 5 Aug 00:14, 1h before launch). FRONG/FORK deployers were NOT funded by this wallet — separate entities.
- POOLS/UNIFROG deployers called `collectFees` on the official FeeSplitter — configured as fee beneficiaries (launch creators), not team members.

## Verdict pattern applied

1. Infra = REAL (official Uniswap GitHub + verified on-chain + matching frontend NS/backend).
2. Tokens = launched through official permissionless infra, NOT team-endorsed.
3. Deployers = funded by a 652K-tx sybil bot exploiting first-mover narrative; POOLS+UNIFROG same operator, FRONG/FORK others.

## Reusable snippets

- Blockscout `addresses/<addr>/counters` for tx totals (fast bot tell).
- `transactions/<hash>/internal-transactions` to see create2 + strategy used.
- fxtwitter media: append `?name=orig` for full-res; OCR via ffmpeg frame + PIL autocontrast + tesseract `--psm 6`.
- Beware Blockscout: prefix hashes and `?page=N` both 422; RPC 403s on burst.
