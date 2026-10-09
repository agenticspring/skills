# $UNIFROG Case — "Deployed with addy in Uniswap GitHub" (2026-08-05)

Full worked example of the token-launch claim verification pattern.

## The Claim

Tweet by @0xDawggy ("journals of a researcher", 1.8K followers, verified), 2026-08-05 07:46 UTC:

> $UNIFROG
> 0xe702a01968800d6249522771fcc3f970f6a25403
> 1. This is UniSwap Github
> 2. Deployed with addy in GitHub
> 3. Launched earliest, this is first
> https://github.com/Uniswap/sdks/blob/main/sdks/liquidity-launcher-sdk/src/addresses.ts
> Image 1: Address shown in GitHub
> Image 2: Position Manager

## Verification Trail

### 1. Tweet + screenshots
- fxtwitter JSON: author verified individual, website t.me/dawggys, 10 likes / 2 RT / 802 views.
- Screenshots OCR'd with tesseract:
  - Image 1: `POSITION_MANAGER_ROBINHOOD = getAddress("0x58daec3116aae6D93017bAAea7749052E8a04fA7")` — REAL, matches repo line 87.
  - Image 2: transfer trace launcher (0x7A6C...768e) → 0x3f...60Fb → PositionManager → PoolManager, 1B/7B/1B UNIFROG, PositionManager NFT token 469916.

### 2. GitHub repo (real, active)
- `Uniswap/sdks` → `sdks/liquidity-launcher-sdk/src/addresses.ts` (672 lines), commits same-day (2026-08-05).
- Token address `0xe702...` NOT in file; NOT in any of 6 recent commits (checked raw file at each sha).
- Infra addresses that ARE in the file (verified on-chain):
  - `LIQUIDITY_LAUNCHER_ROBINHOOD = 0x7A6C474b4DcD35b72203D2B569EAfE4C9b5C768e` (line 55)
  - `POSITION_MANAGER_ROBINHOOD = 0x58daec3116aae6D93017bAAea7749052E8a04fA7` (line 87, Blockscout-verified "PositionManager")
  - `UERC20_FACTORY = 0x000000e200088D55C39a11F609E5F667729ad49b` (line 77, Blockscout-verified "UERC20Factory")
  - `USUPERC20_FACTORY = 0xeEeeEEE204Afb6BABb1287ffed52cCD6BA0b0fb2` (line 78)

### 3. Token on-chain (Robinhood Chain, 4663)
- name "Unifrog", symbol UNIFROG, decimals 18, totalSupply 0x33b2e3c9fd0803ce8000000 = 1e9 (1B).
- Code size 7154 bytes (real contract).
- Blockscout address endpoint: creator = UERC20_FACTORY (`0x000000e2...`), creation tx `0x074eb4b913f2a4474f10e0427512675f3211168c345e2a953fd1343f1325aa99`, created 2026-08-05T01:16:32Z, block 28360384.
- ⚠️ The creation tx's `created_contract` field shows `0x6340943622a02057AEDECed74B9eb1d52962144C` — NOT the token. Token was minted via factory internal call. Use token's own address endpoint for provenance.

### 4. Infra deployment timeline
- All infra deployed via deterministic CREATE2 deployer `0x4e59b44847b379578588920cA78FbF26c0B4956C` from wallet `0x32f4B2e69EbD7746596AF8699DAC1908F43107aD`.
- PositionManager: 2026-05-22 (block 9073) — old.
- UERC20Factory: 2026-07-08.
- LiquidityLauncher: 2026-08-04T23:40:12Z — launcher went live ~1.5h before UNIFROG created.
- Factory had earlier createToken txs (2026-07-31+) — so UNIFROG is NOT first-ever via factory; plausibly first via the NEW launcher. "First" needs qualification.

### 5. Deployer EOA
- `0xD57772C610E571e2D16FA14836C319C43a9fB5d2` — fresh wallet, only 5 txs, funded 0.536 ETH at 00:14:58 by `0xf70da97812CB96acDF810712Aa562db8dfA3dbEF` (active trader, 323 ETH balance, multicall/execute patterns). Not a team wallet.

### 6. Market state (Dexscreener)
- 3 pairs on robinhood/uniswap (v4). Main ETH pair: price $0.00016, MC $160K, liq $50K, vol24h $207K, **+2636% in 24h**. Pair created 1785892592000 = 2026-08-05 ~01:16 UTC — matches token creation exactly.

## Verdict

- ✅ VERIFIED: repo real; infra contracts real, on-chain verified; token created via the exact factory listed in the repo; among the first launches via the new Robinhood launcher.
- ⚠️ MISLEADING: token address itself NOT in GitHub (only infra is); factory is permissionless — anyone can createToken; deployer is a random funded EOA, not Uniswap team; "first" = first via new launcher, not first ever.
- 🎲 Risk: fresh memecoin, MC $160K, +2636% pump window. High risk / high reward narrative play, not an official Uniswap token.

## Reusable Artifacts

- RPC: `https://rpc.mainnet.chain.robinhood.com`
- Explorer: `https://robinhoodchain.blockscout.com`
- Tweet reader: `https://api.fxtwitter.com/i/status/<id>` (browser-free)
