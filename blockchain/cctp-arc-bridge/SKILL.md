---
name: cctp-arc-bridge
description: Circle CCTP V2 bridge to ARC Mainnet — cross-chain USDC transfers via burn+mint, forwarding service, and NOXA trading on Arc (Uniswap V3).
version: 2.0.0
author: spring
license: Private
platforms: [linux]
metadata:
  hermes:
    tags: [CCTP, ARC, Bridge, USDC, Circle, Cross-Chain, Uniswap, NOXA, DeFi]
    related_skills: [web3-farmer-bot]
---

# CCTP V2 Bridge to ARC Mainnet

> **Note**: This skill overlaps with `cctp-bridge` (general CCTP V2 reference). Use `cctp-bridge` for general CCTP questions, cross-chain operations, and SDK usage. Use this skill for ARC-specific details, NOXA trading, and the spring-trade bot.

## Overview

Circle's **Cross-Chain Transfer Protocol (CCTP) V2** enables native USDC transfers across blockchains by burning on source and minting on destination.

> **Current route guard (2026-07-31):** Circle’s published CCTP supported-chain documentation labels domain `26` as **Arc testnet** and says Arc is the exception where CCTP supports testnet only. Therefore do **not** call a Base mainnet burn to a router’s internal “Arc” mapping complete—or assume it reaches Arc mainnet—until Iris returns a non-pending message/attestation and an independently verified destination receipt plus recipient USDC balance increase exists. Older local “ARC Mainnet domain 26” claims below are historical notes and require re-verification.

## Key Insight: Forwarding Service

The bot uses `depositForBurnWithHook` with **Forwarding Magic Bytes** (`cctp-forward` + zero padding to 32 bytes). This tells Circle to:
1. Burn USDC on source chain
2. Attest the burn via Iris API
3. **Auto-mint USDC on ARC** (Circle pays gas!)

Users don't need gas on ARC to receive USDC.

## ARC Mainnet Configuration

| Param | Value |
|-------|-------|
| Chain ID | 5042 |
| Domain | 26 |
| RPC | `https://real-pump-soon-trust-me-bro-again.poptyedev.com/` |
| RPC (backup) | `https://5042.rpc.thirdweb.com` |
| Explorer | `https://arc-mainnet.cloud.blockscout.com/` (offline) |
| Finality | Instant |

## Contract Addresses (Verified On-Chain)

### CCTP V2

| Contract | Address | Size |
|----------|---------|------|
| TokenMessengerV2 | `0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d` | 2175 bytes |
| MessageTransmitterV2 | `0x81D40F21F12A8F0E3252Bccb954D722d4c464B64` | 2175 bytes |
| TokenMinterV2 | `0xfd78EE919681417d192449715b2594ab58f5D002` | 9295 bytes |
| MessageV2 | `0xec546b6B005471ECf012e5aF77FBeC07e0FD8f78` | 281 bytes |

### USDC

| Token | Address | Decimals |
|-------|---------|----------|
| USDC (ARC) | `0x3600000000000000000000000000000000000000` | 6 |

### NOXA/Uniswap V3 (Trading)

| Contract | Address | Size |
|----------|---------|------|
| LaunchFactory | `0xE7d4E64079FE467A21801B36Ccc6D9B3F66BD372` | 22811 bytes |
| LaunchLocker | `0x630957Cf4582baDa8B583B5A9476a7108cFdE0A4` | 4823 bytes |
| V3Factory | `0xf0db7b58379503491d857dB50AC9ece64c653918` | 24535 bytes |
| SwapRouter | `0x53BF6B0684Ec7eF91e1387Da3D1a1769bC5A6F77` | 24497 bytes |
| Quoter | `0x7DfD4F31be6814D2906BDE155c3e1B146EAc1468` | 8273 bytes |
| PositionManager | `0x39654A85A4C05127f5Fd6ED22CAeC077A0fB1377` | 24384 bytes |
| Multicall3 | `0xcA11bde05977b3631167028862bE2a173976CA11` | 3808 bytes |

### Trading Config

| Param | Value |
|-------|-------|
| DefaultFeeTier | 10000 (1%) |
| GraduationTargetUSD | $7,500 |
| PairToken | USDC (`0x3600...0000`) |

## Source Chains (Supported)

| Chain | Domain | USDC Address | Chain ID |
|-------|--------|--------------|----------|
| Ethereum | 0 | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` | 1 |
| Base | 6 | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | 8453 |
| Arbitrum | 3 | `0xaf88d065e77c8cC2239327C5EDb3A432268e5831` | 42161 |
| OP Mainnet | 2 | `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85` | 10 |
| Polygon | 7 | `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359` | 137 |
| Avalanche | 1 | `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E` | 43114 |

## Iris API (Forwarding Fees)

Base URL: `https://iris-api.circle.com`

**Endpoint**: `GET /v2/burn/USDC/fees/{sourceDomain}/26?forward=true`

| Source | forwardFee | minFee | finality |
|--------|------------|--------|----------|
| Ethereum → ARC | 16550 | 0.25 bps | 1000 (fast) |
| Base → ARC | 16550 | 0.325 bps | 1000 |
| Arbitrum → ARC | 16550 | 0.325 bps | 1000 |
| OP Mainnet → ARC | 16557 | 0.325 bps | 1000 |
| Polygon → ARC | 16557 | 0 bps | 1000 |
| Avalanche → ARC | 16557 | 0 bps | 1000 |

**Attestation**: `GET /v2/messages/{domain}?transactionHash={burnTx}`

## Forwarding Magic Bytes

```python
# "cctp-forward" + zero padding to 32 bytes
ForwardingMagicBytes = bytes.fromhex(
    "636374702d666f72776172640000000000000000000000000000000000000000"
)
# Verify: b'cctp-forward' + b'\x00' * 20
```

## Bridge Flow

```
Source Chain (ETH/ARB/BASE/etc)
    │
    ├─ 1. approve(TokenMessengerV2, amount)
    │
    ├─ 2. depositForBurnWithHook(
    │        amount,                    # USDC amount (6 decimals)
    │        26,                        # destinationDomain (ARC)
    │        mintRecipient,             # bytes32(recipient address)
    │        USDC,                      # burnToken address
    │        bytes32(0),                # destinationCaller (permissionless)
    │        maxFee,                    # max fee for forwarding
    │        minFinalityThreshold,      # 1000=fast, 2000=standard
    │        ForwardingMagicBytes       # hookData for gasless mint
    │    )
    │
    ├─ 3. Poll Iris API for attestation
    │      GET /v2/messages/{domain}?transactionHash={burnTx}
    │      Wait for forwardTxHash to appear
    │
    └─ 4. USDC minted on ARC (Circle pays gas!)
         Check balance on ARC
```

## CCTP V2 ABI

### TokenMessengerV2

```json
[
  {"type":"function","name":"depositForBurn","inputs":[
    {"name":"amount","type":"uint256"},{"name":"destinationDomain","type":"uint32"},
    {"name":"mintRecipient","type":"bytes32"},{"name":"burnToken","type":"address"},
    {"name":"destinationCaller","type":"bytes32"},{"name":"maxFee","type":"uint256"},
    {"name":"minFinalityThreshold","type":"uint32"}]},
  {"type":"function","name":"depositForBurnWithHook","inputs":[
    {"name":"amount","type":"uint256"},{"name":"destinationDomain","type":"uint32"},
    {"name":"mintRecipient","type":"bytes32"},{"name":"burnToken","type":"address"},
    {"name":"destinationCaller","type":"bytes32"},{"name":"maxFee","type":"uint256"},
    {"name":"minFinalityThreshold","type":"uint32"},{"name":"hookData","type":"bytes"}]}
]
```

### MessageTransmitterV2

```json
[
  {"type":"function","name":"receiveMessage","inputs":[
    {"name":"message","type":"bytes"},{"name":"attestation","type":"bytes"}]}
]
```

## Automation Completion Gate

For any downstream automation after forwarding (including SniperX buys), use the proof chain in [Forwarding Completion Gate](references/forwarding-completion-gate.md). **A live route, Iris indexing, `pending_confirmations`, an attestation, or `forwardTxHash` alone must never trigger a buy.** Require a successful canonical Arc forwarding receipt, confirmations, and an observed recipient USDC balance increase. Persist a one-shot bridge intent and per-burn/wallet/token buy claim so restarts cannot duplicate action.

## SniperX automation

For persistent user-configured bridge automation and optional destination buying, follow [references/sniperx-automation.md](references/sniperx-automation.md). The key invariant is that only a confirmed destination forwarding receipt **and** an observed recipient USDC balance increase may unlock an automated buy.

When a forwarding-fee endpoint remains live while attestation is stalled, use [Arc CCTP Mint-Burst Gate](references/arc-cctp-burst-gate.md): monitor verified global Arc `MessageReceived` plus same-receipt USDC zero-mints, keep bounded thresholds configurable per user, recheck burst freshness after source-route preflight, and atomically fire one intent. Treat the burst only as a probabilistic timing signal—never as proof that the user's burn will land.

- Auto Bridge must be an explicit durable one-shot intent containing its own source chain and fixed USDC amount. `ON` arms it and `OFF` only cancels an un-fired intent; never create a balance-draining loop.
- Auto Buy is globally toggled, but each explicit CA target owns its own positive `amount_usdc`; never apply one global amount to all targets. The UI should add `CA SYMBOL AMOUNT_USDC` and expose an edit control for each target.
- Snapshot every Auto Buy target and amount **atomically at burn creation**. Completion recovery must read the immutable per-burn snapshot, never the user's current toggle/target list; otherwise enabling Auto Buy later can retroactively trigger purchases from multiple historical completed bridges. Legacy burns without snapshots are ineligible.
- For WETH-quoted chains such as Base, QuoterV2 may quote WETH while buys must execute through native ETH `msg.value`, never a WETH approval/`transferFrom` path. Sells should unwrap WETH output to native ETH.
- `STF`/`SafeTransferFrom` is a transfer, allowance, balance, or router error—not slippage. Reserve slippage guidance for output-minimum errors such as `Too little received`.
- Gas configuration must be per trading chain. Expose an explicit `Auto Normal` mode in the token-card Gwei picker: query `eth_maxPriorityFeePerGas` at send time and use the live recommendation ×1.2. Do not describe manual `0` ambiguously as Auto.
- On every pasted-token card, display live RPC priority tiers: `Slow = recommendation`, `Normal = recommendation ×1.2`, and `Fast = recommendation ×1.5`. A manually selected Gwei/Custom value must switch the stored chain mode back to `custom`.
- A dev screen session alone is not liveness proof. Verify child PID, intended working directory, exact executable path, fresh startup log, and no startup errors before reporting that the bot runs.
- **Telegram identity is mandatory verification:** configuration loading preserves inherited environment values. Launch the dev binary under a clean environment (`env -i` with only minimal shell variables), source only that workspace `.env`, then execute the binary. Otherwise a valid dev binary can silently poll a different Telegram bot inherited from the parent screen/Hermes process.
- Keep bot stdout visible in `screen` via `tee` as well as in the durable log; a black screen is not acceptable evidence to the user. Include a visible launcher banner and a durable `DEV_BOT_EXIT` marker on exit.
- Verify `/start` end-to-end without competing with polling: confirm the intended identity via `getMe`, then observe the durable dispatch marker and that `getWebhookInfo.pending_update_count` falls. **Never call `getUpdates` while the bot is alive**—it competes with long polling and can evict the running poll.

See [Dev Bot and SniperX Safety](references/dev-bot-and-sniperx-safety.md) for the durable launch verification checklist and failure taxonomy.

## Finality Thresholds

| Mode | Threshold | Speed | Fee |
|------|-----------|-------|-----|
| Fast Transfer | 1000 | ~8-20 seconds | Small fee (0.25-0.325 bps) |
| Standard Transfer | 2000 | ~13-19 minutes | No fee |

**Note**: ARC has **instant finality**, so Standard Transfer is also fast (~8 seconds).

## User's Production Repo

**Repo**: `https://github.com/<HANDLE_REDACTED>/spring-trade.git` (PRIVATE)
**Location**: `/root/spring-trade/` (local)

**Features**:
- Telegram bot with multi-user, multi-wallet support
- AES-256-GCM encrypted private keys
- Invite-only access system
- CCTP V2 bridge with Forwarding Service (gasless mint)
- NOXA token trading (Uniswap V3)
- PnL card generation (PNG)
- Admin panel
- Anti-MEV protection (priority fee + private RPC)
- TP/SL and auto-snipe

**Build**: `go build -o spring-trade ./cmd/bot` (Go 1.24+, NOT 1.25)

**⚠️ DO NOT commit/update to repo without user's explicit command.**

## NOXA Supported Chains

NOXA Fun (`fun.noxa.fi`) supports **8 chains**:

| Chain | URL | Status |
|-------|-----|--------|
| Arc | `fun.noxa.fi/arc` | ✅ Primary |
| Ethereum | `fun.noxa.fi/ethereum` | ✅ |
| Base | `fun.noxa.fi/base` | ✅ |
| Arbitrum | `fun.noxa.fi/arbitrum` | ✅ |
| OP Mainnet | `fun.noxa.fi/optimism` | ✅ |
| Polygon | `fun.noxa.fi/polygon` | ✅ |
| Avalanche | `fun.noxa.fi/avalanche` | ✅ |
| Robinhood | `fun.noxa.fi/robinhood` | ✅ |

**Bot currently supports Arc only.** Adding other chains requires updating contract addresses per chain.

## NOXA Trading Details

### Uniswap V3 on ARC

Bot uses Uniswap V3 exclusively (no V2, no V4). All NOXA tokens trade against USDC.

| Contract | Purpose |
|----------|---------|
| V3Factory | Find/create pools |
| SwapRouter02 | Execute swaps (exactInputSingle + multicall) |
| QuoterV2 | Price quotes (revert-based eth_call) |
| PositionManager | Liquidity management |

### Trade Flow

```
Paste CA → V3Factory.getPool(token, USDC, 10000) → QuoterV2.quoteExactInputSingle() → SwapRouter02.exactInputSingle()
```

### Key Functions

- **PoolPriceUSD** (exported): Reads slot0 + token0 from pool, returns USDC price per token. Used for fallback estimation, market cap calc, PnL card.
- **ComputeMinOut**: Quote → fallback pool price → slippage. Never returns 0 (anti-MEV).
- **ExactInputSingle**: Wrapped in multicall with deadline. Balance delta = received amount.

### Anti-MEV

- `amountOutMinimum` always non-zero
- Re-quote fresh before each swap
- Priority fee min 1.5 gwei when ANTI_MEV enabled
- Optional `ARC_PRIVATE_RPC` for submitting swaps

### Position Tracking

- `AddBuy()` — Record new position
- `ReducePosition()` — Update modal on partial sell (proportional)
- `ClosePosition()` — Mark closed on 100% sell

## PnL Card Templates (2026-07-07)

4 templates in Go using `fogleman/gg`:

| Template | Style | Best For |
|----------|-------|----------|
| **Classic** | PnL% big center | Quick share |
| **Compact** | Stats grid (3×2) | Detailed info |
| **Minimal** | Center-aligned clean | Aesthetic |
| **Pro** | Header bar + detail grid | Trader profile |

### Data Fields (PnLData struct)

Core: Symbol, PnLPct, ModalUSDC, NowUSDC, Wallet, When, BotName
Extended: EntryPrice, CurrentPrice, MarketCap, TokenLogoURL, TotalSupply, HoldDuration

### Features

- Token logo: Fetch from NOXA on-chain URL, render as circle clip
- Entry price: `modal / tokensOut`
- Current price: `PoolPriceUSD()` from slot0
- Market cap: `price × totalSupply`
- Hold duration: Auto from position CreatedAt
- Font selection: Bold, Regular, Mono (Go embedded fonts)
- 6 gradient presets: navy, ungu, hijau gelap, amber, dark, ocean
- Custom background: User upload (PNG, cover-fit center-crop)
- Card size: 1536×864 (16:9)

### Color Themes (2026-07-07)

5 color themes for PnL card:

| Theme | PnL+ | PnL- | Text | Style |
|-------|------|------|------|-------|
| `default` | Green | Red | White | Classic |
| `neon` | Neon green | Neon red | White | Bright |
| `gold` | Gold | Red-orange | Cream | Luxury |
| `ice` | Ice blue | Soft red | Ice white | Cool |
| `hacker` | Matrix green | Red | Green | Terminal |

```go
type ColorTheme struct {
    PnLPositive color.RGBA
    PnLNegative color.RGBA
    Text        color.RGBA
    Muted       color.RGBA
    Accent      color.RGBA
}
```

### Settings Menu

```
⚙️ Settings → 🎨 PnL Card
  ├── 📐 Template (Classic/Compact/Minimal/Pro)
  ├── 🖼 Background (6 presets + upload)
  ├── 🔤 Font (Bold/Regular/Mono)
  ├── 🎨 Color (Default/Neon/Gold/Ice/Hacker)
  └── 📸 Preview
```

### Layout Audit Process (2026-07-07)

When adding new elements to PnL card templates, always audit for overlaps:

1. **Calculate Y positions** — Each element has baseline + font height
2. **Check vertical gaps** — Minimum 10px between elements
3. **Check horizontal overflow** — Long text (prices, symbols) can overflow card width
4. **Test extreme values** — Use very long symbols, large PnL%, small prices
5. **Generate test PNGs** — Visual inspection for each template × font combination

**Common overlap patterns:**
- Stats row + Entry/Current price (Classic template)
- Symbol + Triangle arrow (Minimal template)
- PnL number + Stats below (Minimal template)
- Footer text + Detail grid (Pro template)

**Fix approach:** Use dynamic Y positioning based on previous element's bottom edge, not fixed coordinates.

## Sell Logic Audit (2026-07-07)

**Status**: Logic correct, 2 minor issues found.

### Issues

1. **Explorer URL wrong** (`trade_exec.go:21`):
   - Current: `https://explorer.arc.io`
   - Correct: `https://arc-mainnet.cloud.blockscout.com`

2. **Partial sell doesn't update position** (`trade_exec.go:164-168`):
   - Only closes position on 100% sell
   - 50% sell leaves position unchanged → PnL calculation wrong

### What's Correct

| Component | Status |
|-----------|--------|
| Sell amount calc (`pct% * balance`) | ✅ |
| MinOut calculation (quote → fallback → slippage) | ✅ |
| Balance delta (`after - before` USDC) | ✅ |
| Nonce lock (serial per-wallet) | ✅ |
| WaitMined (waits for receipt) | ✅ |
| Approve (max uint256, wait for allowance) | ✅ |

## Chain Source Quick Switch (2026-07-07)

Added quick chain switching buttons to bridge menu:

```go
// keyboard.go - bridgeMenu()
rows = append(rows, row(
    btn("🔵 ETH", "csrc:ethereum"),
    btn("⬛ Base", "csrc:base"),
    btn("🔷 ARB", "csrc:arbitrum"),
))
rows = append(rows, row(
    btn("🔴 OP", "csrc:optimism"),
    btn("🟣 POL", "csrc:polygon"),
    btn("🔺 AVAX", "csrc:avalanche"),
))
```

Callback handler:
```go
case strings.HasPrefix(data, "csrc:"):
    chainKey := strings.TrimPrefix(data, "csrc:")
    _ = a.St.SetSetting(userID, usercfg.KeySourceChain, chainKey)
    a.invalidateHome(userID)
    a.send(ctx, chatID, fmt.Sprintf("✅ Source chain diubah ke <b>%s</b>.", chainKey), nil)
    a.showBridgePlan(ctx, chatID, msgID, userID)
```

## ⚠️ Critical Bug: Manual Claim NOT IMPLEMENTED (2026-07-07 Audit)

The `arc-cctp` repo has a **critical gap** in the bridge claim flow:

### What Exists (Code)
| Function | File | Status |
|----------|------|--------|
| `SubmitReceiveMessage()` | `relay.go` | ✅ Defined |
| `GetAttestationOnce()` | `track.go` | ✅ Defined |
| `showClaim()` | `bridge.go` | ✅ Shows pending burns |

### What's Missing (Telegram UI)
| Component | Status | Impact |
|-----------|--------|--------|
| Claim button per burn | ❌ MISSING | User can't trigger claim |
| `doClaim()` execution function | ❌ MISSING | No code to execute claim |
| Callback handler `claim:<burnTx>` | ❌ MISSING | Button wouldn't work |

### The Bug Flow
```
User clicks "Claim" → showClaim() displays pending burns → ... → NOTHING HAPPENS!

Missing chain: Button → GetAttestationOnce() → SubmitReceiveMessage() → MarkCompleted()
```

### Why It Matters
- **Forwarding Service** handles most claims automatically (Circle pays gas)
- If Forwarding fails or is delayed, users are **STUCK** with no way to claim
- `SubmitReceiveMessage` is permissionless — anyone can call it (just needs gas on ARC)
- The function exists but is **NEVER CALLED** from the Telegram bot

### Fix Applied & Pushed (2026-07-07)

**1. Claim button + doClaim() added to `bridge.go`:**
- Each pending burn gets a "♻️ Klaim #N" button
- `doClaim()`: checks attestation → if already minted (forwarding) → MarkCompleted; if attestation ready → SubmitReceiveMessage; if not ready → notify status

**2. Callback handler added to `callbacks.go`:**
```go
case strings.HasPrefix(data, "claim:"):
    burnTx := strings.TrimPrefix(data, "claim:")
    a.doClaim(ctx, userID, chatID, burnTx)
```

**3. Anti double-bridge check REMOVED:**
- Original: skipped wallets with pending burns
- Fixed: users can bridge anytime, even with pending burns

**4. Arm snipe logic IMPROVED:**
- Added: 24h timeout (was infinite)
- Added: 3 retries on failure (was none)
- Added: success/failure notifications (was silent)

**Status**: All fixes pushed to `spring-trade` repo (commit `4ccba26`).

## Mainnet RPC provenance and chain-study workflow

When researching Arc Mainnet infrastructure, do not present a known seed, screenshot, or prior skill entry as independent discovery. Separate the workflow into:

```text
public source discovery → candidate hostname → DNS/HTTP observation → read-only JSON-RPC verification → provenance classification
```

Use independent public sources such as official Arc/Circle docs, public JS/config bundles, GitHub, registries, provider indexes, and Certificate Transparency logs. CT monitoring is passive hostname discovery; do not brute-force subdomains or probe unobserved infrastructure.

For every candidate, record:
- exact source/provenance (`official-doc`, `JS`, `GitHub`, `registry`, `CT`, `public-index`, or `social/search`);
- whether the endpoint is officially documented or merely publicly reachable;
- read-only verification results: `eth_chainId`, `net_version`, `web3_clientVersion`, `eth_blockNumber`, and optionally `eth_getBlockByNumber`;
- ownership/authorization as **unconfirmed** unless an authoritative source establishes it.

Current Arc study findings (verified read-only, not an endorsement):
- EVM Chain ID: `5042` (`0x13b2`); CCTP domain: `26`.
- `https://rpc.blockdaemon.mainnet.arc.io` and `https://5042.rpc.thirdweb.com` answered chain 5042.
- `https://real-pump-soon-trust-me-bro-again.poptyedev.com/` also answered chain 5042, but its ownership and intended authorization are unconfirmed; do not make it the default production endpoint.
- The DYORSwap X post `https://x.com/i/status/2065439940377477253` redirects to `https://dyorswap.org/?chainId=5042`; its public Next.js bundle independently contains `https://rpc.blockdaemon.mainnet.arc.io` for Arc Mainnet. Classify this as `public-JS-config` corroboration, not official Arc endorsement.
- DYORSwap's same bundle contains stale/mismatched Arc configuration: a configured multicall address `0x942Bd5BFdc5317C5507e326f8EB4BB6058AB5C10` returned no bytecode from the live RPC. Never copy a frontend's full chain config without checking every contract address via `eth_getCode`.
- Arc Docs currently publish Testnet connection details (`5042002`, `https://rpc.testnet.arc.network`) and state that mainnet endpoints/parameters are published separately when available. Therefore, a live mainnet endpoint must not automatically be described as officially documented.

For ecosystem reconnaissance, separate sources by evidence strength:
1. Direct RPC: recent blocks, transaction destinations/selectors, `eth_getCode`, and `eth_call`.
2. Explorer/indexer: token lists, verified source, indexed totals; useful but not a complete census.
3. Public frontend JS: configuration/provenance only; frontend entries may be stale or wrong.
4. Search/social: lead only, never verification.

A recent Arc RPC sample showed live but concentrated activity; do not infer mature TVL or major-protocol identity from a small block window. Public RPCs may prune historical logs (`pruned history unavailable`), so historical ecosystem scans require an archive endpoint or indexer.

See `references/arc-mainnet-study.md` for the condensed evidence record and verification matrix. See `references/dyor-mainnet-provenance.md` for the DYORSwap public-JS extraction and stale multicall-config verification.

## Field reconnaissance workflow

For Arc ecosystem and contract investigations, use `references/arc-mainnet-field-notes.md`. Start with direct read-only RPC and Iris; use explorers only as intermittent indexes. When counting factory deployments, test historical logs and stop at `pruned history unavailable`—do not invent a count from recent blocks.

## Pitfalls

1. **ARC Mainnet is new** — Explorer may be offline, RPC may be custom
2. **Do not conflate Chain ID and CCTP domain**: use `5042` for EVM/RPC configuration and `26` for CCTP parameters.
3. **Do not equate liveness with endorsement**: a successful JSON-RPC response proves reachability and chain identity, not ownership, permission, or Circle endorsement.
4. **Do not treat a third-party hostname as production-safe** without provenance and authorization.
5. **Arc uses USDC as native gas**: do not apply Ethereum/ETH assumptions to balance or fee logic.
6. **Go version**: Requires Go 1.24.x, NOT 1.25.x (runtime compatibility issues)
2. **Forwarding Service**: Must use `depositForBurnWithHook` with ForwardingMagicBytes, NOT `depositForBurn`
3. **bytes32 encoding**: Recipient address must be left-padded to 32 bytes
4. **Fee calculation**: Forwarding fee + protocol fee (bps) + buffer percentage
5. **Anti double-bridge**: Original code blocked bridging with pending burns — removed in local fix (now pushed)
6. **Attestation timeout**: Can take up to 75 minutes for Standard Transfer
7. **Thirdweb rate limiting**: poptyedev RPC preferred over thirdweb for eth_call
8. **Explorer offline**: ARC Mainnet blockscout explorer is down (as of 2026-07-07)
9. **USDC predeploy**: USDC at `0x3600...0000` is a predeploy, not a regular contract
10. **Instant finality**: ARC has instant finality, so Standard Transfer is also fast
11. **ARC view functions revert**: `localMessageTransmitter()` and `localDomain()` not in ARC bytecode. Core functions work.
12. **Manual claim gap**: `SubmitReceiveMessage` existed but was never wired to Telegram UI. Fixed and pushed.
13. **Arm snipe no timeout**: Original arm ran forever. Fixed with 24h timeout + 3 retries. Pushed.
14. **EDGE chain different addresses**: Domain 28 (EDGE) uses unique contract addresses, not standard ones. See `references/cctp-v2-all-chains.md`.
15. **Iris fee changes**: Forward fees change over time. Always fetch fresh before bridge.
16. **Repo rename**: Repo renamed from `arc-cctp` to `spring-trade`. Local path: `/root/spring-trade/`
17. **README**: Professional README with full documentation pushed to repo.
18. **New chains**: CCTP V2 now supports Monad(15), EDGE(28), Injective(29), Morph(30), Pharos(31), Cronos(32) — not yet in repo.
19. **Language preference**: User prefers English-only labels in UI. No mixed Indonesian/English. All card labels, button text, and messages should be in English.
20. **PnL card layout audit**: Always audit new template elements for overlaps. Use dynamic Y positioning, not fixed coordinates. Test with extreme values (long symbols, large PnL%, small prices).

## Repo Setup (Local)

```bash
cd /root/spring-trade

# Generate encryption key
./spring-trade -genkey >> .env

# Edit .env
nano .env
# Fill: TELEGRAM_BOT_TOKEN, ADMIN_IDS (MASTER_ENCRYPTION_KEY auto-filled)

# Run
./spring-trade
```

## Commands

```bash
# Build
cd /root/spring-trade
go build -o spring-trade ./cmd/bot

# Run tests
go test ./...

# Start bot
./spring-trade

# Start with env
source .env && ./spring-trade
```
