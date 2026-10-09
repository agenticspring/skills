# pools.trade / Uniswap Robinhood Chain — 2026-08-05 case study

Full forensic path from the session that produced `token-launch-verify` and
`launchpad-contract-monitor`. Timeline and addresses are VERIFIED on-chain.

## Context

Uniswap's token-issuance platform `pools.trade` (Robinhood Chain, chain 4663)
was in stealth pre-launch ("Coming soon from Uniswap", go-live 4:00 PM UTC
2026-08-05). Twitter research accounts posted contract addresses claiming
"first launch" / "official launch contract". All turned out to be
front-running bot tokens on legit Uniswap infrastructure.

## Verified infrastructure (Robinhood Chain 4663)

RPC: `https://rpc.mainnet.chain.robinhood.com`
Explorer: `https://robinhoodchain.blockscout.com`

| Contract | Address | Role |
|---|---|---|
| UERC20Factory (constant) | `0x000000e200088D55C39a11F609E5F667729ad49b` | token factory, vanity, verified |
| LiquidityLauncher (old, v3.1.1) | `0x7A6C474b4DcD35b72203D2B569EAfE4C9b5C768e` | replaced |
| LiquidityLauncher (new, vanity) | `0x0000FffFBE8efE702c8703aE3477FF5dE3d319C0` | deployed 13:25:26 UTC, still not in GitHub at session end |
| PositionManager ROBINHOOD | `0x58daec3116aae6D93017bAAea7749052E8a04fA7` | verified, in GitHub |
| PoolManager | `0x8366a39CC670B4001A1121B8F6A443A643e40951` | v4 pool manager, holds LP positions |
| FeeSplitter FEES_ON v3.1.1 | `0x6CC1b74Fc1BE1ff373Fa07f3381856f38103e653` | in GitHub |
| Strategy FEES_ON v3.1.1 | `0x3f556B542105D5EFBBefe7C766a4919C76B960Fb` | in GitHub |
| New strategy (post-vanity-launcher) | `0x23f8209572b4a1C2AD88A42749E830791Fb027f1` | deployed 13:25:39, NOT in GitHub |
| Deployer (Uniswap team wallet) | `0x32f4B2e69EbD7746596AF8699DAC1908F43107aD` | deploys via CREATE2 factory `0x4e59b448...` |

Key GitHub repo: `Uniswap/sdks`, file `sdks/liquidity-launcher-sdk/src/addresses.ts`.
GitHub comments explicitly mention "the mined vanity salt" — the team mines
vanity CREATE2 salts for launchers/factories. Git history lags on-chain deploys
by ~1.5h (commit `dd0ea30b` at 15:02 UTC registered the 13:25 UTC redeploy).

## Tokens analyzed (all bot-launched, none official)

| Token | Address | Created (UTC) | Launcher | Notes |
|---|---|---|---|---|
| POOLS | `0x385b36Ff682Ab4C76E7c37A66b96aABC466471d5` | 07-30 16:41 | old 0x7A6C... | name = "pools.trade", vol $1.44M |
| UNIFROG | `0xe702a01968800d6249522771fcc3f970f6a25403` | 08-05 01:16 | old | "first fees coin" |
| FORK | `0x404a032297205d437dbafb39dab82474f18b95f0` | 08-05 06:05 | old | vol $378K |
| FRONG | `0x4c136180005a3c2659cd0151fa63ebcba37cc097` | 08-05 08:21 | old | name appears in teaser video `frong.mp4` |
| UNIFRONG (claim) | `0x87f1ed895B460C002E82075f1038E7f2ce4d51cD` | 08-05 13:25:55 | NEW vanity launcher | created 29s after launcher deploy; on-chain name is UNIFROG |

All 1B supply, 18 decimals, creator = UERC20Factory (permissionless).

## Bot cluster evidence

- `0xf70da97812CB96acDF810712Aa562db8dfA3dbEF` — funder, **652,558 txs /
  3,188,885 token transfers** = bot farm. Funded UNIFROG deployer (0.536 ETH
  @ 00:14, 1h pre-launch) and POOLS deployer (0.256 ETH @ 14:01, 2.5h pre-launch).
- `0x081Ea97812CB96acdF810712aa562Db8dFA3ED00` — L1 bridge wallet feeding the
  funder via `submitRetryable` (Arbitrum bridge), 25x deposits of 50-112 ETH.
  **Shares 32 of 40 address chars with the funder** = vanity-paired, one operator.
- `0xA5a5491bCa93dD4C076e4906e79E7673F4A5A142` — funded UNIFRONG deployer,
  114,284 txs = another bot.
- Deployer EOAs themselves are fresh (3-15 txs) — the bots stay behind them.

## Website recon (pools.trade)

- DNS: AWS ELB us-east-2 (3.20.124.161), CloudFront S3 origin, NS =
  damian/gemma.cloudflare.com — **same NS as uniswap.org** (strong ownership signal).
- WHOIS: GoDaddy + Domains By Proxy, created 2026-07-17 (2.5 weeks pre-launch).
- JS env: `VITE_TEASER_MODE:true`, backend
  `entry-gateway.backend-prod.api.uniswap.org` (live, `/health` → ok, WS 401),
  Datadog RUM prod, WalletConnect project id, CSP connect-src lists Robinhood +
  Ethereum + Unichain + Base RPCs.
- Subdomains `dev.pools.trade` / `staging.pools.trade` exist (ELB, restricted).
- Teaser video: `https://d29c45bs0h4ffe.cloudfront.net/rh-cca/frong.mp4`
  (24s, 720p, no audio, screen-recording timestamps 07-28-2026) — uploaded
  28 Jul, before any token existed. Suggests "frong" is an internal codename.

## Reusable commands

```bash
# Tweet fetch without X auth
curl -s "https://api.fxtwitter.com/i/status/<ID>"

# GitHub commits for a file path
curl -s "https://api.github.com/repos/Uniswap/sdks/commits?path=sdks/liquidity-launcher-sdk/src/addresses.ts&per_page=10"

# ERC-20 name via RPC
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":"<TOKEN>","data":"0x06fdde03"},"latest"]}' \
  "https://rpc.mainnet.chain.robinhood.com"

# Blockscout: creator + creation tx (FULL hash required)
curl -s "https://robinhoodchain.blockscout.com/api/v2/addresses/<TOKEN>"
curl -s "https://robinhoodchain.blockscout.com/api/v2/transactions/<FULL_HASH>"
curl -s "https://robinhoodchain.blockscout.com/api/v2/transactions/<FULL_HASH>/internal-transactions"

# Bot detection
curl -s "https://robinhoodchain.blockscout.com/api/v2/addresses/<ADDR>/counters"
```
